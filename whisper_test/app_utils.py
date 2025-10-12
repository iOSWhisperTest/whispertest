import time
import re
import pymobiledevice3
from pymobiledevice3.services.dvt.instruments.process_control import ProcessControl
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.application_listing import ApplicationListing
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from whisper_test.common import logger
from whisper_test.common import INSTALLATION_LOG_SEARCH_STRINGS
from whisper_test.utils import is_text_in_syslog, is_app_index_in_links
from whisper_test.rule_based_app_navigation import find_next_action_rule_based, create_rule_based_command


def launch_app(bundle_id: str, service_provider) -> None | int:
    """ Launch an app with the given bundle id."""
    logger.info("🚀 Launching app with bundle ID: %s", bundle_id)
    try:
        with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
            process_control = ProcessControl(dvt)
            pid = process_control.launch(bundle_id=bundle_id)
            logger.info("Process launched with pid %d", pid)
            return pid
    except pymobiledevice3.exceptions.DvtException as e:
        logger.error("❌ Failed to launch app: %s. Error: %s", bundle_id, e)
        return None

def get_installed_apps(service_provider) -> list:
    """ Get the list of installed apps """
    try:
        with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
            apps = ApplicationListing(dvt).applist()
            logger.info(apps)
            return apps
    except pymobiledevice3.exceptions.DvtException as e:
        logger.error("❌ Failed to get the list of installed apps. Error: %s", e)
        return None

def install_app_via_ipa(ipa_path, service_provider):
    """ Install an app from the given ipa path """
    start_time = time.time()
    try:
        InstallationProxyService(service_provider).install_from_local(ipa_path)
        logger.info(f"✅ {ipa_path} installed successfully.")
    except Exception as e:
        if "DeviceOSVersionTooLow" in str(e):
            logger.error(f"Failed to install {ipa_path} due to incompatible OS version: {e}")
            return False
        else:
            logger.error(f"Installation failed with an unexpected error: {e}")
        return False  # Indicate failure
    elapsed_time = time.time() - start_time
    logger.info(f"⏱️ Installation took {elapsed_time:.2f} seconds.")
    return True

def install_app_from_app_store(screen_elements, tts, syslog, timeout=30):
    """
    Install an app from its App Store page using voice command.
    This function checks for the presence of specific buttons on the App Store page
    and uses voice commands to interact with them. It monitors the installation process
    through syslog entries and returns the app ID if successful.
    
    Returns:
        - app_id (str): The installed app's ID if installation was successful
        - dict: A dictionary with 'status' (False) and 'reason' (str) if installation failed
    """
    # Check if app is already installed
    if any('Open, Button' in element for element in screen_elements):
        app_name = next((element.split(',')[0] for element in screen_elements 
                      if 'Open, Button' in element), "Unknown app")
        logger.info(f"🚀 App '{app_name}' already installed.")
        return {"status": False, "reason": "already_installed", "app_name": app_name}
    
    # Check if app is not available
    if any('app not available' in element.lower() for element in screen_elements):
        logger.error("❌ App not available.")
        return {"status": False, "reason": "not_available"}
    
    # Try to install the app
    if handle_get_button(screen_elements, tts, syslog) and (app_id := monitor_app_installation(syslog, timeout=timeout)):
        return app_id
    elif handle_redownload_button(screen_elements, tts, syslog) and (app_id := monitor_app_installation(syslog, timeout=timeout)):
        return app_id
    elif handle_update_button(screen_elements, tts, syslog) and (app_id := monitor_app_installation(syslog, timeout=timeout)):
        return app_id
    
    # If we reach here, installation failed for an unknown reason
    return {"status": False, "reason": "installation_failed"}

def handle_get_button(captions, tts, syslog):
    """
    Manage the 'Get' button scenario in the App Store.

    This function checks if the 'Get' button is present on the screen.
    If found, it simulates a tap on the 'Get' button using voice commands.
    It then monitors the syslog for specific entries indicating the start of a purchase process.
    If the expected syslog entry is not found, it retries the command.
    Once the purchase process is confirmed, it checks for the presence of the 'Install' button and simulates a tap on it.
    The function returns the app ID if the process is successful, otherwise it returns False.
    """
    if not any('Get, Button' in caption for caption in captions):
        return False
    logger.info("🚀 Handling the 'Get' button scenario.")
    if tts.say("Tap Get"):
        syslog_entry = is_text_in_syslog(['Starting purchase for client'], syslog)
        if not syslog_entry:
            app_id = handle_button_retry("Tap Get", "Tap one", ["Starting purchase for client"], tts, syslog)
        else:
            app_id = get_app_id(syslog_entry, "Starting purchase for client")
    else:
        return False
    # handle install button
    if not is_text_in_syslog(['Payment sheet has presented'], syslog):
        return False
    logger.info("🚀 Install Button present.")
    if not tts.say("Tap Install"):
        return False
    return app_id

def handle_redownload_button(captions, tts, syslog):
    """Manage the 're-download' button scenario in the App Store."""
    if not any('re-download, Button' in caption for caption in captions):
        return False
    logger.info("🚀 Handling the 're-download' button scenario.")
    if tts.say("Tap re-download"):
        syslog_entry = is_text_in_syslog(['Starting purchase for client'], syslog)
        if not syslog_entry:
            app_id = handle_button_retry("Tap re-download", "Tap one", ["Starting purchase for client"], tts, syslog)
        else:
            app_id = get_app_id(syslog_entry, "Starting purchase for client")
        return app_id
    return False

def handle_update_button(captions, tts, syslog):
    """Manage the 'update' button scenario in the App Store."""
    if not any('Update, Button' in caption for caption in captions):
        return False
    logger.info("🚀 Handling the 'update' button scenario.")
    if tts.say("Tap update"):
        syslog_entry = is_text_in_syslog(['Starting purchase for client'], syslog)
        if not syslog_entry:
            app_id = handle_button_retry("Tap update", "Tap one", ["Starting purchase for client"], tts, syslog)
        else:
            app_id = get_app_id(syslog_entry, "Starting purchase for client")
        return app_id
    return False

def handle_button_retry(initial_command, retry_command, match_text, tts, syslog):
    """
    Retry the command if the expected syslog entry is not found.
    This function is used when there are multiple buttons on the screen, and selecting a button requires two steps:
    1. The first step involves issuing a voice command to display numbers on the buttons.
    2. The second step involves issuing another voice command to tap the number corresponding to the desired button.
    """
    tts.say(retry_command)
    syslog_entry = is_text_in_syslog(match_text, syslog)
    if syslog_entry:
        app_id = get_app_id(syslog_entry, match_text)
        return app_id
    else:
        return False

def monitor_app_installation(syslog, app_id = None, timeout=30):
    """Monitor the download and installation of apps from the App Store."""
    logger.info("🚀 Monitoring app installation for %s", app_id)
    start_time = time.time()
    while time.time() - start_time < timeout:
        installation_log = is_text_in_syslog(INSTALLATION_LOG_SEARCH_STRINGS, syslog)
        if installation_log:
            if 'Received install progress: 1.00' in installation_log:
                if app_id is None:
                    app_id = get_app_id(installation_log, 'Received install progress: 1.00')
                logger.info(f"🚀 App with bundleId {app_id} installed successfully.")
                return app_id
            if  'Coordinator completed successfully' in installation_log:
                if app_id is None:
                    app_id = get_app_id(installation_log, 'Coordinator completed successfully')
                logger.info(f"🚀 App with bundleId {app_id} installed successfully.")
                return app_id
            if 'Application was installed at' in installation_log:
                if app_id is None:
                    app_id = get_app_id(installation_log, 'Application was installed at')
                logger.info(f"🚀 App with bundleId {app_id} installed successfully.")
                return app_id
            if 'Handling application installation' in installation_log:
                if app_id is None:
                    app_id = get_app_id(installation_log, 'Handling application installation')
                logger.info(f"🚀 App with bundleId {app_id} installed successfully.")
                return app_id
    logger.info("🚨 Timeout: Installation failed.")
    return False

def get_app_id(log_line, match):
    """Extract the app id from the log line."""
    logger.info("🚀 Getting app ID from log line: %s", log_line)
    if not log_line:
        return None
    match_str = rf'\[.*?/(.*?):\d+\]: {match}'
    match = re.search(match_str, log_line)
    if match:
        app_id = match.group(1)
        logger.info(f"🚀 Extracted app ID: {app_id}")
        return app_id
    elif 'Install Successful for' in log_line:
        match = re.search(r'Install Successful for \(Placeholder:(.*?)\)', log_line)
        if match:
            app_id = match.group(1)
            logger.info(f"🚀 Extracted app ID: {app_id}")
            return app_id
    elif 'Starting purchase for client' in log_line:
        match = re.search(r'\[.*?/(.*?):\d+\] Starting purchase for client', log_line)
        if match:
            app_id = match.group(1)
            logger.info(f"🚀 Extracted app ID: {app_id}")
            return app_id
    elif 'Scene lifecycle state did change' in log_line:
        match = re.search(r'sceneID:([^]]+)', log_line)
        if match:
            app_id = match.group(1).split('-')[0]
            logger.info(f"🚀 Extracted app ID: {app_id}")
            return app_id
    elif 'Coordinator completed successfully' in log_line:
        match = re.search(r'<Notice>: ([^/]+)/', log_line)
        if match:
            app_id = match.group(1)
            logger.info(f"🚀 Extracted app ID: {app_id}")
            return app_id
    return None

def open_files_app_on_device(tts, syslog, a11y) -> bool:
    """Open the Files app on the device."""
    tts.say("Open Files")
    if not is_text_in_syslog(['sceneID:com.apple.DocumentsApp-C96C635D-0040-4EBD-9BF3-D4B3130B9A85" = 1'], syslog):
        logger.error("❌ 'Files app not opened.")
        return False
    time.sleep(2)
    _cleanup_screen(tts, a11y)
    logger.info("🚀 Files app opened successfully.")
    time.sleep(2)
    return True

def _cleanup_screen(tts, a11y, consent_mode="accept"):
    """Cleanup the screen from native dialogs."""
    command = _get_cleanup_command(a11y, consent_mode)
    while command is not None:
        v_command = create_rule_based_command(command)
        tts.say(v_command)
        time.sleep(2)
        command = _get_cleanup_command(a11y, consent_mode)

def _get_cleanup_command(a11y, consent_mode="accept"):
    """Get the cleanup command for the screen."""
    a11y_data = a11y.get_ax_list_items()
    command, _ = find_next_action_rule_based(a11y_data, consent_mode, handle_native=True)
    if command is None:
        if any('Cancel, Button' in element for element in a11y_data):
            command = "cancel"
    return command

def open_html_file_to_download_apps(tts, syslog, a11y, html_file_name: str) -> bool:
    """Open the HTML file on the device using voice commands."""
    if not open_files_app_on_device(tts, syslog, a11y):
        return False
    screen_elements = a11y.get_ax_list_items()
    if not any('HTML file' in element for element in screen_elements) and any('Cancel, Button' in element for element in screen_elements) \
        and tts.say("Tap cancel"):
        screen_elements = a11y.get_ax_list_items()
    # check if the previous html file is closed
    if any('Done, Button' in element for element in screen_elements) and not tts.say("Tap done") \
        and not is_text_in_syslog(['com.apple.WebKit.GPU entered background'], syslog):
        logger.error("❌ Failed to tap done and close the previous html file.")
        return False
    screen_elements = a11y.get_ax_list_items()
    if screen_elements and any(f'{html_file_name}, HTML file' in element for element in screen_elements):
        if tts.say(f"Tap, {html_file_name}") and is_text_in_syslog(['com.apple.WebKit.GPU: Foreground: true'], syslog):
            logger.info("🚀 Opened the html file.")
            return True
        else:
            logger.error("❌ Failed to open the html file.")
            return False
    else:
        logger.error("❌ Failed to find the html file.")
        return False

def open_app_url(tts, syslog, screen_elements, a11y, app_index: str, html_file_name: str) -> bool:
    """Open the app URL saved in the HTML file on the device using voice commands."""
    if not screen_elements:
        logger.error("❌ No screen elements found.")
        return False
    # check if there is no "Link" element in the screen elements
    if not any('Link' in element for element in screen_elements):
        logger.error(f"❌ No 'Link' element found in screen elements, reopening the html file.{html_file_name}")
        open_html_file_to_download_apps(tts, syslog, a11y, html_file_name)
    if not is_app_index_in_links(app_index, screen_elements):
        logger.error("❌ App index not found in screen elements.")
        return False
    if not tts.say(f"Tap, {app_index}"):
        return False
    if not tts.say("Tap Open"):
        return False
    if not is_text_in_syslog(['Scene lifecycle state did change'], syslog):
        return False
    logger.info(f"🚀 Tapped on the app URL")
    time.sleep(2)
    return True
