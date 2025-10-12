import asyncio
import json
import os
import threading

from queue import Empty
from time import time, sleep
import pymobiledevice3
import pymobiledevice3.exceptions
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.pcapd import PcapdService
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.services.screenshot import ScreenshotService

from whisper_test.exceptions import (
    ConnectionFailedToUsbmuxdError, NoActiveTunnelConnection)
from whisper_test.syslog_monitor import SyslogMonitor
from whisper_test.common import (
    logger, DEFAULT_TTS_PROVIDER, SYSLOG_SEARCH_STRINGS,
    TIMEOUT_FOR_APP_INSTALLATION, CUSTOM_CMD, SLEEP_AFTER_CMD,
    SYSLOG_SCAN_AFTER_VOICE_CMD, SLEEP_AFTER_CUSTOM_CMD,
    SYSLOG_MSG_VOICE_CMD_RECOGNIZED)

from whisper_test.utils import (
    get_active_tunnel_conn, take_screenshot_dvt, save_processed_app_index,
    read_processed_app_index,is_app_already_processed, is_text_in_syslog,
    remove_media_dir_on_device)
from whisper_test.app_utils import (
    launch_app, install_app_via_ipa,
    install_app_from_app_store, open_files_app_on_device,
    open_app_url, open_html_file_to_download_apps)
from whisper_test.a11y_utils import axServices
from whisper_test.tts import TTSController
from whisper_test.ocr_utils import (
    ocr_img_by_ez_ocr, ocr_img_by_omniparser, get_matching_grid_number)
from whisper_test.rule_based_app_navigation import find_next_action_rule_based
from whisper_test.navigation import NavigationController


def get_media_path():
    """Get media path from config or use default."""
    from whisper_test.common import _config
    media_path = _config.get('media_path', 'media_output')
    if not os.path.exists(media_path):
        os.makedirs(media_path)
    return media_path

MEDIA_PATH = get_media_path()

class WhisperTestDevice():
    """Class to interact with the connected iOS device."""

    def __init__(self, consent_mode: str = "accept", connect_to_device: bool = True, tts_provider: str = DEFAULT_TTS_PROVIDER) -> None:
        print("🚀 Initializing WhisperTestDevice")
        print("🚀 consent_mode: ", consent_mode)
        self.consent_mode = consent_mode
        self.lockdown: LockdownClient = None
        self.syslog: SyslogMonitor = None
        self.tts_provider: str = tts_provider
        self.collected_pkts: list = []  # pcap packets
        self.details: dict = {}
        self._connect_to_device: bool = connect_to_device
        self.pcap_path: str = None
        self.pcapd_service: PcapdService = None
        self.pcap_thread: threading.Thread = None
        self.tts = TTSController(tts_provider=self.tts_provider, verify_func=self.confirm_voice_cmd_in_syslog)
        if not connect_to_device:
            return
        self.connect_to_device()
        self.syslog = SyslogMonitor(self.lockdown, syslog_search_strings=SYSLOG_SEARCH_STRINGS)
        self.pcap_stop_event: threading.Event = threading.Event()
        self.a11y: axServices = axServices()
        self.populate_device_info()
        self.service_provider: LockdownClient = asyncio.run(self.get_service_provider())
        self.media_path = MEDIA_PATH
        self.navigation = NavigationController(self, MEDIA_PATH)


    def connect_to_device(self):
        """Connect to the device using usbmuxd."""
        try:
            self.lockdown = create_using_usbmux()
        except (FileNotFoundError,
                ConnectionRefusedError,
                pymobiledevice3.exceptions.ConnectionFailedToUsbmuxdError) as e:
            logger.error("❌ Error while connecting to device.\
                         Make sure the device is attached: %s", e)
            raise ConnectionFailedToUsbmuxdError() from e

    @property
    def product_version(self) -> str:
        return self.lockdown.product_version

    @property
    def major_os_version(self) -> int:
        return int(self.product_version.split('.')[0])

    @property
    def display_name(self) -> str:
        return self.lockdown.display_name

    @property
    def hardware_model(self) -> str:
        return self.lockdown.hardware_model

    @property
    def device_class(self) -> str:
        return self.lockdown.device_class

    @property
    def device_name(self) -> str:
        return self.lockdown.all_values['DeviceName']

    @property
    def paired(self) -> bool:
        return self.lockdown.paired

    @property
    def connection_type(self) -> str:
        return self.lockdown.short_info['ConnectionType']

    @property
    def a11y_features(self) -> bool:
        """The enabled/disabled status of some limited a11y features:
            'ClosedCaptioningEnabledByiTunes', 'InvertDisplayEnabledByiTunes',
            'MonoAudioEnabledByiTunes', 'SpeakAutoCorrectionsEnabledByiTunes',
            'VoiceOverTouchEnabledByiTunes', 'ZoomTouchEnabledByiTunes'
        """
        return self.lockdown.get_value('com.apple.Accessibility')

    @property
    def wifi_mac_address(self) -> str:
        return self.lockdown.wifi_mac_address

    async def get_service_provider(self):
        """Get the service provider for the connected device based on the iOS version.
        For >=17.4 use the available faster lockdown tunnel.
        For <17.4 use the regular lockdown connection.
        """

        if self.major_os_version < 17:
            return self.lockdown
        else:
            return await get_active_tunnel_conn()

    def collect_packets(self, packet_generator):
        """Add packets to the collected packets list."""
        for packet in packet_generator:
            if self.pcap_stop_event.is_set():
                break
            self.collected_pkts.append(packet)

    def start_pcap_capture(self, pcap_path, packets_count=-1,
                           process=None, interface_name=None) -> bool:
        """Start capturing packets using pcapd service."""
        try:
            # Reset any existing pcap state
            if self.pcap_thread and self.pcap_thread.is_alive():
                self.stop_pcap_capture()

            self.pcap_path = pcap_path
            self.collected_pkts = []  # Reset packets
            self.pcap_stop_event.clear()  # Reset the stop event

            # Using the existing usbmux lockdown connection causes errors
            self.pcapd_service = PcapdService(create_using_usbmux())
            packets_generator = self.pcapd_service.watch(
                packets_count, process, interface_name)
            self.pcap_thread = threading.Thread(target=self.collect_packets, args=[
                                         packets_generator], daemon=True)
            self.pcap_thread.start()
            logger.info("🚀 Pcap capture started")
            print(f"📥 starting pcap capture, collecting pkts: {len(self.collected_pkts)}")
            return True
        except Exception as e:
            logger.error(f"❌ Error starting pcap capture: {e}")
            # Clean up any partially initialized resources
            self.pcapd_service = None
            self.pcap_thread = None
            return False

    def stop_pcap_capture(self) -> bool:
        """Stop capturing packets using pcapd service."""
        if not self.pcap_thread or not self.pcapd_service:
            logger.warning("🛑 No active pcap capture to stop")
            return False

        try:
            logger.info("🚀 Will stop the pcap capture")
            print(f"📥 collecting pkts: {len(self.collected_pkts)}")
            self.pcap_stop_event.set()

            # Wait for thread with timeout
            self.pcap_thread.join(timeout=5.0)
            if self.pcap_thread.is_alive():
                logger.error("🛑 Pcap thread failed to stop within timeout")
                return False
                
            # Write to pcap file (includes header even if no packets)
            logger.info(f"📥 Writing {len(self.collected_pkts)} packets to pcap file")
            with open(self.pcap_path, 'wb') as pcap_out:
                self.pcapd_service.write_to_pcap(pcap_out, self.collected_pkts)

            # Cleanup
            self.pcap_thread = None
            self.pcapd_service = None
            self.collected_pkts = []
            logger.info("✅ Pcap capture stopped successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error stopping pcap capture: {e}")
            return False

    def get_installed_apps(self, app_type: str = 'Any',
                           calculate_sizes: bool = False,
                           fail_silently=False) -> list:
        """Get installed apps on the device."""

        if self.service_provider:
            return InstallationProxyService(lockdown=self.service_provider).\
                get_apps(application_type=app_type,
                        calculate_sizes=calculate_sizes)
        else:
            logger.error("❌ Cannot get the installed apps. No active tunnel connection.")
            if fail_silently:
                return []
            else:
                raise NoActiveTunnelConnection()

    def populate_device_info(self, print_device_info=False):
        """Get device information from the lockdown service."""
        ld_all_values = self.lockdown.all_values
        for key in ld_all_values:
            value = ld_all_values.get(key)
            try:  # discard non-serializable values
                json.dumps(value)
            except TypeError:
                # BasebandRegionSKU
                # BasebandSerialNumber
                # CarrierBundleInfoArray
                # ChipSerialNo
                # NonVolatileRAM
                # PkHash
                # ProximitySensorCalibration
                # SIMGID1
                # SIMGID2
                # SoftwareBehavior
                continue
            self.details[key] = value
        self.details['AccessibilitySettings'] = self.a11y.get_ax_settings()
        if print_device_info:
            logger.info(f"Device info: {json.dumps(self.details, indent=4)}")

    def take_screenshot(self, screenshot_path, fail_silently=False):
        """Requires developer disk image to be mounted and the developer mode enabled."""

        if self.major_os_version < 17:  # should we check for 17.4?
            with open(screenshot_path, 'wb') as out:
                out.write(ScreenshotService(
                    lockdown=self.lockdown).take_screenshot())
        elif self.service_provider:
            # requires developer disk image to be mounted and developer mode enabled
            take_screenshot_dvt(screenshot_path, self.service_provider)
        else:
            logger.error("❌ Cannot take screenshot. No active tunnel connection or lockdown.")
            if not fail_silently:
                raise NoActiveTunnelConnection()
        # logger.info("🚀 Took screenshot successfully")

    # TODO: implement
    # def take_screenshot_as_b64(self):
    #     pass

    def get_device_syslogs(self):
        try:
            return self.syslog.queue.get(timeout=2)
        except Empty:
            logger.error("❌ No more syslog entries in the queue.")
            return None
        except Exception as e:
            logger.error("❌ Error getting syslog entries: %s", e)
            return None

    def install_app_via_ipa(self, ipa_path: str, fail_silently: bool = False):
        """Install an app from the given ipa path"""
        if self.service_provider:
            return install_app_via_ipa(ipa_path, self.service_provider)
        else:
            logger.error("❌ Cannot install app. No active tunnel connection.")
            if not fail_silently:
                raise NoActiveTunnelConnection()

    def vc_install_app_via_app_url(self, app_index: str, html_file_name: str=None):
        """Install the app with the specified bundle ID."""
        screen_elements = self.get_screen_content_by_a11y(max_items=30)
        if not open_app_url(self.tts, self.syslog, screen_elements, self.a11y, app_index, html_file_name):
            logger.info("❌ Failed to open the app URL.")
            return False
        sleep(SLEEP_AFTER_CMD)
        screen_elements = self.get_screen_content_by_a11y(max_items=10)

        result = install_app_from_app_store(screen_elements, self.tts, self.syslog, timeout=TIMEOUT_FOR_APP_INSTALLATION)

        if isinstance(result, dict):
            # Installation failed with status info
            if result["reason"] == "already_installed":
                logger.info(f"App is already installed")
                # Do something with already installed app
            elif result["reason"] == "not_available":
                logger.info("App is not available in the App Store")
                # Handle not available case
            elif result["reason"] == "installation_failed":
                logger.info("App installation failed")
                # Handle general installation failure
            # save result to a file
            with open(self.failed_installed_app_ids_path, "a") as f:
                result["app_index"] = app_index
                json.dump(result, f)
                f.write("\n")
            return False
        else:
            # Successful installation - result is the app_id string
            app_id = result
            logger.info(f"Successfully installed app with ID: {app_id}")
            # save installed app id to a file
            with open(self.installed_appids_path, "a") as f:
                f.write(app_id)
                f.write("\n")
            return app_id

    def vc_install_app_via_url_file(self, html_file_name: str, app_url_index: str) -> bool:
        """Install app via its App Store URL saved in an HTML file on the device using voice commands."""
        if not open_html_file_to_download_apps(self.tts, self.syslog, self.a11y, html_file_name):
            return False

        screen_elements = self.get_screen_content_by_a11y(max_items=30)
        link_indices = [element.split(',')[0] for element in screen_elements if 'Link' in element]
        if app_url_index not in link_indices:
            logger.error("❌ App URL index not found in screen elements.")
            return False

        return self.vc_install_app_via_app_url(app_url_index, html_file_name)

    def vc_install_apps_via_urls_file(self, urls_file_name: str):
        """Install a list of apps through opening the HTML file including app URLs in the device."""
        if not open_html_file_to_download_apps(self.tts, self.syslog, self.a11y, urls_file_name):
            logger.info("❌ Failed to open list of apps to download.")
            return False
        logger.info(f"🚀 Processing HTML file: {urls_file_name}")
        screen_elements = self.get_screen_content_by_a11y(max_items=30)
        installed_apps = read_processed_app_index(self.installed_apps_path)
        failed_apps = read_processed_app_index(self.failed_installed_apps_path)

        if not screen_elements:
            logger.info("❌ Failed to open list of apps to download.")
            return False
        app_indexs = [element.split(',')[0].strip() for element in screen_elements if ', Link' in element]
        for app_index in app_indexs:
            if is_app_already_processed(f"{app_index},{urls_file_name}", installed_apps) or \
                is_app_already_processed(f"{app_index},{urls_file_name}", failed_apps):
                continue
            screen_elements = self.get_screen_content_by_a11y(max_items=30)
            if not open_app_url(self.tts, self.syslog, screen_elements, self.a11y, app_index, urls_file_name):
                logger.info("❌ Failed to open the app URL.")
                return False
            app_id = self.vc_install_app_via_app_url(app_index, urls_file_name)
            if app_id:
                save_processed_app_index(self.installed_apps_path, f"{app_index},{urls_file_name},{app_id}")
            else:
                save_processed_app_index(self.failed_installed_apps_path, f"{app_index},{urls_file_name}")
            if not open_files_app_on_device(self.tts, self.syslog, self.a11y):
                logger.info("❗️Failed to open Files app, (still in the app store)")
                return False
        logger.info("🚀 Successfully installed all apps.")
        return True

    def vc_install_apps_via_urls_files(self, urls_file_names: list):
        """Install a list of apps through opening the HTML files including app URLs in the device."""
        logger.info("🚀 Installing apps via URLs files: %s", urls_file_names)
        for urls_file_name in urls_file_names:
            self.vc_install_apps_via_urls_file(urls_file_name)

    def uninstall_app(self, bundle_id):
        """ Uninstall the app with the specified bundle ID """
        try:
            logger.info("Uninstalling %s", bundle_id)
            InstallationProxyService(
                lockdown=self.lockdown).uninstall(bundle_id)
            logger.info("🚀 Uninstalled %s", bundle_id)
            return True
        except Exception:
            logger.error("❌ Failed to uninstall %s.", bundle_id)
            return False

    def launch_app(self, bundle_id: str, fail_silently=False) -> None:
        """Launch the app with the specified bundle ID."""
        if self.service_provider:
            return launch_app(bundle_id, self.service_provider)
        else:
            logger.error("❌ Cannot launch app. No active tunnel connection.")
            if not fail_silently:
                raise NoActiveTunnelConnection("Cannot launch apps. No active tunnel connection.")

    def get_screen_content_by_a11y(self, max_items=20):
        """Get the screen content using the Accessibility Audit service."""
        return self.a11y.get_ax_list_items(max_items=max_items)

    def get_screen_content_by_ocr(self, img_path: str, ocr_service: str = "omniparser"):
        """Get the screen content using OCR."""
        if ocr_service == "ez_ocr":
            try:
                ocr_results = ocr_img_by_ez_ocr(img_path)
            except Exception as e:
                logger.error("❌ Error in OCR using ez_ocr: %s", e)
                return None
        elif ocr_service == "omniparser":
            try:
                ocr_results = ocr_img_by_omniparser(img_path)
            except Exception as e:
                logger.error("❌ Error in OCR using omniparser: %s", e)
                return None
        else:
            logger.error("❌ Invalid OCR service: %s", ocr_service)
            return None
        return ocr_results

    def iter_syslog(self, timeout=5):
        """Iterate over syslog messages."""
        start_time = time()
        while time() - start_time < timeout:
            try:
                yield self.get_device_syslogs()
            except Empty:
                continue
        return

    def _get_screen_data(self, app_id, sc_name=None, use_ocr=False, ocr_service=None, timestamp=None):
        """Retrieve screen data based on the selected mode (accessibility or OCR (omniparser))."""
        if use_ocr:
            screen_data = self.get_screen_content_by_ocr(sc_name, ocr_service=ocr_service)
            # Convert the list format to a more readable dictionary format
            if screen_data and isinstance(screen_data, list):
                formatted_data = []
                for item in screen_data:
                    # omniparse data format
                    if len(item) >= 8:
                        formatted_data.append({
                            "id": item[0],
                            "type": item[1],
                            "text": item[2],
                            "interactive": item[3],
                            "x": item[4],
                            "y": item[5],
                            "width": item[6],
                            "height": item[7]
                        })
                    else:
                        # Handle any items that don't match the expected format
                        formatted_data.append({"raw_data": item})
            else:
                formatted_data = screen_data
            with open(f"{MEDIA_PATH}/{app_id}_ocr_{timestamp}.json", "w") as f:
                json.dump(formatted_data, f, indent=2)
            return screen_data  # Return original data to avoid breaking existing functionality
        else:
            screen_elements = self.get_screen_content_by_a11y(max_items=15)
            with open(f"{MEDIA_PATH}/{app_id}_a11y_{timestamp}.txt", "w") as f:
                f.write(str(screen_elements))
            return screen_elements

    def click_coordinates(self, interaction_coordinates, sc_path=None):
        """Click on specific coordinates using grid method.
        
        Args:
            interaction_coordinates: Tuple of (x, y, width, height) coordinates
            sc_path: Optional path to screenshot for grid calculation
            
        Returns:
            bool: True if click was successful, False otherwise
        """
        if sc_path is None:
            sc_path = "grid_ocr_screenshot.png"
            self.take_screenshot(sc_path)
        matching_number, matching_sub_cell, matching_finer_sub_cell, landscape = get_matching_grid_number(sc_path, interaction_coordinates)
        grid_command = "Show grid with 15 columns and 10 rows" if landscape else "show grid with 10 columns and 15 rows"

        if not self.tts.say(grid_command):
            logger.error("❌ Failed to execute grid command: %s", grid_command)
            return False

        if matching_number is None:
            logger.error("❌ No matching number found for grid cell.")
            return False

        if not self.tts.say(f"{matching_number}"):
            logger.error("❌ Failed to execute command for matching number: %s", matching_number)
            return False

        if matching_sub_cell is not None and not self.tts.say(f"{matching_sub_cell}"):
            logger.error("❌ Failed to execute command for matching sub-cell: %s", matching_sub_cell)
            return False

        if matching_finer_sub_cell is not None and not self.tts.say(f"Tap, {matching_finer_sub_cell}"):
            logger.error("❌ Failed to execute command for matching finer sub-cell: %s", matching_finer_sub_cell)
            return False

        logger.info("🔄 Grid clicked successfully: %s", matching_finer_sub_cell)
        return True

    def execute_custom_command(self, custom_cmd):
        """Execute the custom command."""
        custom_cmd_executed = self.tts.say(custom_cmd)
        if custom_cmd_executed:
            logger.info("🚀 Custom command executed successfully.")
            sleep(SLEEP_AFTER_CUSTOM_CMD)
        return custom_cmd_executed

    def execute_navigation_command(self, command, coordinates, sc_name=None):
        """Execute the given command and return success status."""
        logger.info("🕹️ Executing command: %s", command)
        if not command or command.lower() == "no option available" or command == "None" or command is None:
            return False

        if command.lower() == CUSTOM_CMD:
            return self.execute_custom_command(command)

        if command.lower().startswith("type"):
            success = self.tts.say(command)
        elif coordinates is not None:
            print(f"🔄 Clicking coordinates: {coordinates}")
            success = self.click_coordinates(coordinates, sc_name)
        else:
            success = self.tts.say(command)

        if success:
            logger.info(f"🚀 Command executed successfully: {command}")
            sleep(SLEEP_AFTER_CMD)
        else:
            logger.error(f"❌ Failed to execute command: {command}")

        return success

    def check_app_background_status(self, app_id):
        """Check if the app has entered the background.
        
        Args:
            app_id: Bundle identifier of the app to check
            
        Returns:
            bool: True if app entered background, False otherwise
        """
        logger.info("💡 Checking app background status for %s", app_id)
        search_string = [f"{app_id} entered background",
                        "com.apple.AppStore.ProductPageExtension entered foreground",
                        f"{app_id}: Foreground: false"]
        if is_text_in_syslog(search_string, self.syslog):
            logger.info("❗️ App entered background")
            return True
        return False

    def start_screen_recording(self):
        """
        Start screen recording.
        There is a custom command to start screen recording on the device.
        """
        # remove the media directory on the device
        remove_media_dir_on_device(self.lockdown)
        return self.tts.say("start screen recording")

    def cleanup_screen_from_native_dialog(self):
        """Clean the screen from native dialog."""
        screen_data = self.get_screen_content_by_a11y()
        rule_based_element, coordinates = find_next_action_rule_based(screen_data, self.consent_mode, handle_native=True)
        if rule_based_element:
            self.execute_navigation_command(f"tap, {rule_based_element}", coordinates)

    def stop_screen_recording(self):
        """
        Stop screen recording.
        There is a custom command to stop screen recording on the device.
        """
        try:
            # clean the screen from native dialog before stopping screen recording
            # self.cleanup_screen_from_native_dialog()
            if not self.tts.say("go home"):
                raise RuntimeError("Failed to go home (stop screen recording).")
            if not self.tts.say("show grids with 10 columns and 15 rows"):
                raise RuntimeError("Failed to show 10x15 grid (stop screen recording).")
            if not self.tts.say("tap 2"):
                raise RuntimeError("Failed to tap 2.")
            if not self.tts.say("tap stop"):
                raise RuntimeError("Failed to tap stop.")
            logger.info("✅ Screen recording stopped")
            return True
        except RuntimeError as e:
            logger.error("❌ %s", e)
            raise RuntimeError("Failed to stop screen recording.")

    def confirm_voice_cmd_in_syslog(self, command : str = "", print_syslog=False):
        """Wait for the syslog message that confirms the voice command worked.
        
        Args:
            command: The voice command that was executed
            print_syslog: Whether to print syslog entries for debugging
            
        Returns:
            bool: True if command was recognized, False otherwise
            
        Note:
            On iOS 18.1.1+, "Matched Grammar" can also be used as confirmation
        """
        sleep(SLEEP_AFTER_CMD)
        t0 = time()
        while time() - t0 < SYSLOG_SCAN_AFTER_VOICE_CMD:
            try:
                syslog_entry = self.get_device_syslogs()
                if print_syslog:
                    logger.info("syslog_entry: %s", syslog_entry)
                    if "Matched Grammar" in syslog_entry:
                        logger.info("✅🗣🗣 Matched Grammar in syslog for command '%s': %s",
                                    command, syslog_entry)
                if syslog_entry and (SYSLOG_MSG_VOICE_CMD_RECOGNIZED in syslog_entry):
                    logger.info("✅🗣🗣 '%s' found in syslog for command '%s': %s",
                                SYSLOG_MSG_VOICE_CMD_RECOGNIZED, command, syslog_entry)
                    return True
                if syslog_entry is None:
                    logger.error("❌ '%s' not found in syslog for command '%s'.",
                                 SYSLOG_MSG_VOICE_CMD_RECOGNIZED, command)
                    return False
            except Empty:
                logger.error("🛑 No more syslog entries in the queue for command '%s'.", command)
                break
        return False


    def close(self):
        """Clean up device related resources."""
        print("Closing the device.")
        if self.syslog:
            self.syslog.stop()
        if self.lockdown:
            self.lockdown.close()

    def __del__(self):
        print("Cleaning up resources.")
        self.close()
