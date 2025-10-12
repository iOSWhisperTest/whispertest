import logging
from time import time
from typing import List, Tuple, Optional, Dict, Any

try:
    from ad_template_matching.template_matching import perform_template_matching
except ImportError:
    print("❌ ad_template_matching not found.")
    perform_template_matching = None

from whisper_test.common import TIMEOUT_FOR_APP_NAVIGATION
from whisper_test.rule_based_app_navigation import find_next_action_rule_based, create_rule_based_command
from whisper_test.llm_based_app_navigation import find_next_action_llm_based
from whisper_test.ocr_utils import get_coords_from_ocr, has_screen_changed
from whisper_test.utils import get_timestamp, add_action_to_history, check_last_action_history

logger = logging.getLogger(__name__)

class NavigationController:
    """Class to handle app navigation using various methods (rule-based, LLM-based, etc.)"""

    def __init__(self, device, media_path: str):
        print("🚀 Initializing NavigationController")
        self.device = device
        self.media_path = media_path
        self.consent_mode = device.consent_mode
        print(f"💡 Consent mode: {self.consent_mode}")

    def process_rule_based_commands(self, screen_data, use_ocr: bool, 
                                  sc_name_before: str, sc_name_after: str,
                                  handle_native: bool = True, handle_cookie: bool = False, 
                                  handle_apple: bool = False, action_history: List[Any] = None) -> Tuple[bool, Optional[str]]:
        """Process rule-based commands for navigation."""
        if action_history is None:
            action_history = []

        if screen_data is None or len(screen_data) < 1 or 'Direct Interaction' in screen_data:
            logger.error("❌ Failed to get screen data")
            return False, None

        rule_based_element, coordinates = find_next_action_rule_based(
            screen_data, self.consent_mode, handle_native=handle_native, 
            handle_cookie=handle_cookie, handle_apple=handle_apple, is_ocr=use_ocr)

        if rule_based_element is None or check_last_action_history(action_history, rule_based_element):
            return False, rule_based_element

        rule_based_command = create_rule_based_command(rule_based_element)

        if not self.device.execute_navigation_command(rule_based_command, coordinates, sc_name=sc_name_before):
            return False, rule_based_element

        self.device.take_screenshot(sc_name_after)
        if has_screen_changed(sc_name_before, sc_name_after):
            logger.info("🚀 Screen changed")
            return True, rule_based_element
        logger.info("🚀 Screen did not change")
        return False, rule_based_element

    def process_llm_based_commands(self, app_id: str, screen_data: List[Any], 
                                 sc_name_before: str, sc_name_after: str,
                                 use_accessibility: bool, use_ocr: bool, 
                                 llm_based_commands: List[str], action_history: List[Any],
                                 use_image: bool = False) -> Tuple[bool, List[str], Optional[Dict]]:
        """Process LLM-based commands for navigation."""
        if (not use_image) and (screen_data is None or len(screen_data) < 1 or 'Direct Interaction' in screen_data):
            llm_based_command, llm_output = "no option available", None
        else:
            llm_based_command, llm_output = find_next_action_llm_based(
                screen_data, app_id, use_accessibility=use_accessibility,
                use_ocr=use_ocr, use_image=use_image, image=sc_name_before,
                action_history=action_history, consent_mode=self.consent_mode)

        if llm_based_command is not None and llm_based_command.lower() != "no option available" and llm_based_command != 'None':
            if llm_output and 'bbox_2d' in llm_output:
                coordinates = llm_output['bbox_2d']
                logger.info(f"🔄 Bbox 2d coordinates: {coordinates}")
            elif use_ocr:
                coordinates = get_coords_from_ocr(llm_based_command, screen_data)
                logger.info(f"🔄 OCR coordinates: {coordinates}")
            else:
                coordinates = None

            if not self.device.execute_navigation_command(llm_based_command, coordinates, sc_name=sc_name_before):
                logger.error("❌ Failed to execute LLM-based command: %s", llm_based_command)
                return False, llm_based_commands, llm_output

            self.device.take_screenshot(sc_name_after)
            if has_screen_changed(sc_name_before, sc_name_after):
                logger.info("💡 Screen number changed!")
                return True, llm_based_commands, llm_output

        return False, llm_based_commands, llm_output

    def take_screenshots(self, app_id: str) -> str:
         """Take a screenshot of the app screen."""
         timestamp = get_timestamp()
         sc_name = f"{self.media_path}/{app_id}_{timestamp}.png"
         self.device.take_screenshot(sc_name)
         return sc_name, timestamp

    def navigate_app(self, app_id: str, ocr_service: str = "omniparser",
                    use_accessibility: bool = True, use_ocr: bool = False, 
                    use_image: bool = False) -> bool:
        """Navigate through an app using specified methods."""
        if not self.device.service_provider:
            logger.error("❌ Cannot navigate to app. No active tunnel connection.")
            return False

        llm_based_commands = [""]
        start_time = time()
        action_history = []
        llm_success_flag = None

        while True:
            elapsed_time = time() - start_time
            if elapsed_time >= TIMEOUT_FOR_APP_NAVIGATION:
                logger.info("⚠️⌛️ Timeout for app navigation reached.")
                break

            sc_name_before, timestamp = self.take_screenshots(app_id)
            screen_data = self.device._get_screen_data(app_id, sc_name_before, 
                                                     use_ocr=use_ocr, 
                                                     ocr_service=ocr_service, 
                                                     timestamp=timestamp)
            sc_name_after = f"{self.media_path}/{app_id}_{get_timestamp()}.png"

            # Handle native dialogs
            logger.info("Handling native dialogs...")
            rule_native_success, _ = self.process_rule_based_commands(
                screen_data, False, sc_name_before, sc_name_after, handle_native=True)
            if rule_native_success:
                logger.info("✅ Rule-based (accessibility) command executed")
                continue

            # Handle Apple authentication and cookies
            logger.info("Handling Apple authentication and cookies...")
            rule_a11y_success, _ = self.process_rule_based_commands(
                screen_data, False, sc_name_before, sc_name_after, 
                handle_native=False, handle_cookie=True, handle_apple=True)
            if rule_a11y_success:
                logger.info("✅ Rule-based (accessibility) command executed")
                continue

            # Try LLM-based approach
            logger.error("❗️Failed to find the next action using rule-based approach, trying LLM-based approach...")
            llm_success_flag, llm_based_commands, llm_output = self.process_llm_based_commands(
                app_id, screen_data, sc_name_before, sc_name_after,
                use_accessibility=use_accessibility, use_ocr=use_ocr,
                llm_based_commands=llm_based_commands, action_history=action_history,
                use_image=use_image)

            if self.device.check_app_background_status(app_id):
                logger.info("❌ App entered background, stopping navigation")
                break

            action_history, llm_output = add_action_to_history(
                action_history, llm_output, deduplicate=False,
                command_success=llm_success_flag)

            if not llm_success_flag:
                logger.error("❌ Failed to find the next action using LLM-based approach")

        logger.info(f"🚀 Finished navigating to app: {app_id} in {time() - start_time} seconds")
        return True

    def navigate_app_with_fallback(self, app_id: str, ocr_service: str = "omniparser") -> bool:
        """Navigate through an app using multiple fallback methods."""
        logger.info(f"💡 Consent mode: {self.consent_mode}")
        llm_based_commands = [""]
        start_time = time()
        action_history_rule_based = []
        action_history_llm_based = []
        action_history_image_based = []
        llm_success_flag = None

        logger.info(f"🚀 Start navigating to app: {app_id}")
        while True:
            elapsed_time = time() - start_time
            if elapsed_time >= TIMEOUT_FOR_APP_NAVIGATION:
                logger.info("⚠️⌛️ Timeout for app navigation reached.")
                break

            # Try rule-based approach with accessibility
            sc_name_before, timestamp = self.take_screenshots(app_id)
            sc_name_after = f"{self.media_path}/{app_id}_{get_timestamp()}.png"

            logger.info("🚀 Navigating to app: %s using rule-based approach (a11y)", app_id)
            a11y_data = self.device._get_screen_data(app_id, use_ocr=False, timestamp=timestamp)

            # Handle native dialogs with accessibility
            logger.info("Handling native dialogs (a11y)...")
            rule_native_success, _ = self.process_rule_based_commands(
                a11y_data, False, sc_name_before, sc_name_after, handle_native=True)
            if rule_native_success:
                logger.info("✅ Rule-based (a11y-native) command executed")
                continue

            # Try rule-based approach with OCR
            logger.error("❌ Failed to find the next action using rule-based (a11y) approach, trying OCR-based (ocr) data")
            sc_name_before, timestamp = self.take_screenshots(app_id)
            ocr_data = self.device._get_screen_data(app_id, sc_name_before,
                                                  use_ocr=True, ocr_service=ocr_service,
                                                  timestamp=timestamp)
            sc_name_after = f"{self.media_path}/{app_id}_{get_timestamp()}.png"

            rule_ocr_success, rule_ocr_element = self.process_rule_based_commands(
                ocr_data, True, sc_name_before, sc_name_after, 
                handle_native=True, handle_cookie=False, handle_apple=True,
                action_history=action_history_rule_based)

            action_history_rule_based, rule_ocr_element = add_action_to_history(
                action_history_rule_based, rule_ocr_element)

            if rule_ocr_success:
                logger.info("✅ Rule-based (ocr) command executed")
                continue

            # Try image-based LLM approach
            logger.error("💡 Trying image-based LLM approach...")
            sc_name_before, timestamp = self.take_screenshots(app_id)
            sc_name_after = f"{self.media_path}/{app_id}_{get_timestamp()}.png"

            ocr_data = self.device.get_screen_content_by_ocr(
                sc_name_before, ocr_service=ocr_service)

            llm_success_flag, llm_based_commands, llm_output = self.process_llm_based_commands(
                app_id, ocr_data, sc_name_before, sc_name_after,
                use_accessibility=False, use_ocr=False,
                llm_based_commands=llm_based_commands,
                action_history=action_history_llm_based,
                use_image=True)

            if self.device.check_app_background_status(app_id):
                logger.info("❌ App entered background, stopping navigation")
                break

            action_history_image_based, llm_output = add_action_to_history(
                action_history_image_based, llm_output,
                deduplicate=False, command_success=llm_success_flag)

            if llm_success_flag:
                logger.info("✅ LLM-based (image) command executed")
                found, points = perform_template_matching(sc_name_after)
                if found:
                    logger.info("✅ Template matching found at points %s for appID: %s", points, app_id)
                continue
            else:
                logger.error("❌ Failed to find the next action using image-based LLM-based approach")

            # Try accessibility-based LLM approach
            logger.error("💡 Trying A11y-based LLM approach...")
            sc_name_before, timestamp = self.take_screenshots(app_id)
            sc_name_after = f"{self.media_path}/{app_id}_{get_timestamp()}.png"

            a11y_data = self.device._get_screen_data(app_id, use_ocr=False, timestamp=timestamp)
            if a11y_data is not None and 'Direct Interaction' not in a11y_data:
                logger.info("🚀 Navigating to app: %s using LLM-based approach (a11y)", app_id)
                llm_success_flag, llm_based_commands, llm_output = self.process_llm_based_commands(
                    app_id, a11y_data, sc_name_before, sc_name_after,
                    use_accessibility=True, use_ocr=False,
                    llm_based_commands=llm_based_commands,
                    action_history=action_history_llm_based)

                if self.device.check_app_background_status(app_id):
                    logger.info("❌ App entered background, stopping navigation")
                    break

                action_history_llm_based, llm_output = add_action_to_history(
                    action_history_llm_based, llm_output,
                    deduplicate=False, command_success=llm_success_flag)

                if llm_success_flag:
                    logger.info("✅ LLM-based (a11y) command executed")
                    found, points = perform_template_matching(sc_name_after)
                    if found:
                        logger.info("✅ Template matching found at points %s for appID: %s", points, app_id)
                    continue
                else:
                    logger.error("❌ Failed to find the next action using LLM-based (a11y) approach")
            else:
                logger.error("❌ A11y data is not available for appID: %s", app_id)

            # Try OCR-based LLM approach
            logger.error("💡 Trying OCR-based LLM approach...")
            sc_name_before, timestamp = self.take_screenshots(app_id)
            ocr_data = self.device._get_screen_data(app_id, sc_name_before,
                                                  use_ocr=True, ocr_service=ocr_service,
                                                  timestamp=timestamp)
            sc_name_after = f"{self.media_path}/{app_id}_{get_timestamp()}.png"

            llm_success_flag, llm_based_commands, llm_output = self.process_llm_based_commands(
                app_id, ocr_data, sc_name_before, sc_name_after,
                use_accessibility=False, use_ocr=True,
                llm_based_commands=llm_based_commands,
                action_history=action_history_llm_based)

            if self.device.check_app_background_status(app_id):
                logger.info("❌ App entered background, stopping navigation")
                break

            action_history_llm_based, llm_output = add_action_to_history(
                action_history_llm_based, llm_output,
                deduplicate=False, command_success=llm_success_flag)

            if llm_success_flag:
                logger.info("✅ LLM-based (ocr) command executed")
                found, points = perform_template_matching(sc_name_after)
                if found:
                    logger.info("✅ Template matching found at points %s for appID: %s", points, app_id)
            else:
                logger.error("❌ Failed to find the next action using LLM-based (ocr) approach")

        logger.info(f"🚀 Finished navigating to app: {app_id} in {time() - start_time} seconds")
        return True
