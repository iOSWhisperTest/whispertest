from time import time, sleep
from whisper_test.common import logger, SLEEP_AFTER_CMD, SLEEP_AFTER_LAUNCH_APP
from whisper_test.utils import (
    get_timestamp, 
    read_processed_app_index, 
    save_processed_app_index, 
    is_app_already_processed,
    transfer_single_video
)
from whisper_test.app_utils import open_files_app_on_device, open_html_file_to_download_apps

class DataCollector:
    """Class responsible for collecting data from iOS apps.
    
    Args:
        device: WhisperTestDevice instance
        processed_apps_path: Path to file tracking processed apps
        failed_apps_path: Path to file tracking failed apps
    """
    def __init__(self, device, processed_apps_path='processed_appIDs.txt', 
                 failed_apps_path='failed_appIDs.txt'):
        print("🚀 Initializing DataCollector")
        self.device = device
        self.media_path = device.media_path
        self.processed_apps_path = processed_apps_path
        self.failed_apps_path = failed_apps_path
        self.failed_installed_apps_path = failed_apps_path.replace('failed_', 'failed_installed_')
        self.installed_apps_path = processed_apps_path.replace('processed_', 'installed_')
        self.installed_appids_path = processed_apps_path.replace('processed_appIDs', 'installed_appIDs')
        self.failed_installed_app_ids_path = failed_apps_path.replace('failed_appIDs', 'failed_installed_appIDs')

    def data_collection_by_app_url(self, urls_file_name: str):
        """Collect data from from list of url apps"""
        try:
            if not open_html_file_to_download_apps(self.device.tts, self.device.syslog, self.device.a11y, urls_file_name):
                logger.error("❌ Failed to open list of apps to download.")
                return
            sleep(2)
            screen_elements = self.device.get_screen_content_by_a11y(max_items=35)
            if not screen_elements:
                logger.error("❌ Failed to retrieve screen elements.")
                return

            app_indices = [element.split(',')[0].strip() for element in screen_elements if ', Link' in element]
            installed_apps = read_processed_app_index(self.processed_apps_path)
            failed_apps = read_processed_app_index(self.failed_apps_path)

            for app_index in app_indices:
                t0 = time()
                if is_app_already_processed(f"{app_index},{urls_file_name}", installed_apps) \
                    or is_app_already_processed(f"{app_index},{urls_file_name}", failed_apps):
                    continue

                app_id = self._install_app(app_index)
                if not app_id:
                    logger.error("❌ Failed to install the app.")
                    save_processed_app_index(self.failed_apps_path, f"{app_index},{urls_file_name}")
                    continue
                sleep(SLEEP_AFTER_CMD)

                if not self.start_screen_recording():
                    logger.error("❌ Failed to start screen recording.")
                    continue
                sleep(SLEEP_AFTER_LAUNCH_APP)

                if not self._manage_app_flow(app_id):
                    logger.error("❌ Failed to manage the app flow.")
                    save_processed_app_index(self.failed_apps_path, f"{app_index},{urls_file_name},{app_id}")
                    # continue
                if not self.uninstall_app(app_id):
                    logger.error("❌ Failed to uninstall and cleanup the app.")
                    save_processed_app_index(self.failed_apps_path, f"{app_index},{urls_file_name},{app_id}")

                if not self.stop_screen_recording():
                    save_processed_app_index(self.failed_apps_path, f"{app_index},{urls_file_name},{app_id}")
                    raise Exception("❌ Failed to stop screen recording.")

                logger.info(f"✅ Successfully processed app with ID: {app_id}")
                save_processed_app_index(self.processed_apps_path, f"{app_index},{urls_file_name},{app_id}")

                if not transfer_single_video(self.lockdown, local_path=self.media_path, new_file_name=f'{app_id}_{get_timestamp()}.mp4'):
                    logger.error("❌ Failed to transfer the video to the local directory.")

                if not open_files_app_on_device(self.tts, self.syslog, self.a11y):
                    # logger.warning("Failed to open Files app, (still in the app store)")
                    raise Exception("❌ Failed to open Files app.")

                logger.info("🚀 Finished data collection for %s", app_index)
                logger.info("🚀 Time taken to process app %s: %s seconds", app_index, time() - t0)
            logger.info("🚀 Finished data collection for %s", urls_file_name)

        except Exception as e:
            logger.error("🛑 An error occurred during data collection: %s", e)
            self.stop_screen_recording()
            pass

    def collect_data_by_ipa_file(self, ipa_file: str):
        """Collect data from the apps with ipa files"""
        installed_apps = read_processed_app_index(self.processed_apps_path)
        failed_apps = read_processed_app_index(self.failed_apps_path)

        # for ipa_file in os.listdir(ipa_files_path):
        try:
            app_id = ipa_file.split('/')[-1].split('_')[0]
            if is_app_already_processed(app_id, installed_apps) or is_app_already_processed(ipa_file, failed_apps):
                logger.info("🚀 App %s already processed", app_id)
                return
            t0 = time()
            logger.info("🚀 Installing app: %s", app_id)
            if not self.device.install_app_via_ipa(ipa_file):
                logger.error("❌ Failed to install the app.")
                save_processed_app_index(self.failed_installed_apps_path, f"{app_id}")
                return
            sleep(SLEEP_AFTER_CMD)

            if not self.device.start_screen_recording():
                logger.error("❌ Failed to start screen recording.")
                return
            sleep(SLEEP_AFTER_CMD)
            if not self._manage_app_flow(app_id):
                logger.error("❌ Failed to manage the app flow.")
                save_processed_app_index(self.failed_apps_path, f"{app_id}")
                # continue
            if not self.device.uninstall_app(app_id):
                logger.error("❌ Failed to uninstall and cleanup the app.")
                save_processed_app_index(self.failed_apps_path, f"{app_id}")

            if not self.device.stop_screen_recording():
                save_processed_app_index(self.failed_apps_path, f"{app_id}")
                raise Exception("❌ Failed to stop screen recording.")

            logger.info(f"✅ Successfully processed app with ID: {app_id}")
            save_processed_app_index(self.processed_apps_path, f"{app_id}")

            if not transfer_single_video(self.device.lockdown, local_path=self.device.media_path, new_file_name=f'{app_id}_{get_timestamp()}.mp4'):
                logger.error("❌ Failed to transfer the video to the local directory.")

            logger.info("🚀 Time taken to process app %s: %s seconds", app_id, time() - t0)

        except Exception as e:
            logger.error("🛑 An error occurred during data collection: %s", e)
            return
        return True

    def _install_app(self, app_index):
        """Install the app."""
        logger.info("Installing app: %s", app_index)
        app_id = self.device.vc_install_app_via_app_url(app_index=app_index)
        if not app_id:
            logger.error("❌ Failed to install the app.")
            if not open_files_app_on_device(self.device.tts, self.device.syslog, self.device.a11y):
                logger.warning("Failed to open Files app, (still in the app store)")
            return None
        return app_id

    def _manage_app_flow(self, app_id):
        """Manage the installation, launch, capture, and navigation of an app."""
        pcap_file_path = f"{self.media_path}/{app_id}_{get_timestamp()}.pcap"
        self.device.start_pcap_capture(pcap_file_path)

        if not self.device.launch_app(app_id):
            self.device.stop_pcap_capture()
            return False
        if self.device.check_app_background_status(app_id):
            logger.info("❌ App entered background, stopping navigation")
            self.device.stop_pcap_capture()
            return False

        sleep(SLEEP_AFTER_LAUNCH_APP)

        try:
            self.device.navigation.navigate_app_with_fallback(app_id=app_id)
        except Exception as e:
            logger.error("❌ Failed to navigate to the app: %s", e)
            self.device.stop_pcap_capture()
            return False

        self.device.stop_pcap_capture()
        return True
