from whisper_test.utils import levenshtein_similarity, read_text_file, filter_element_types
from whisper_test.ocr_utils import process_ocr_data, get_coords_from_ocr
from whisper_test.common import logger, RULE_BASED_ACTION_MAPPINGS, KEYWORDS_FILE_PATH

def is_dialog_present_from_mappings(screen_text_list, dialog_mappings):
    """Check if any dialog from the mappings is present in the elements_text."""
    for search_terms, button_names in dialog_mappings.items():
        # Split the string back into a list if it contains a comma
        terms = search_terms.split(', ') if ', ' in search_terms else [search_terms]
        if all(any(term.lower() in screen_text.lower() for screen_text in screen_text_list) for term in terms):
            # Check for any of the possible button names
            for button_name in button_names:
                if any(button_name.lower() in screen_text.lower() for screen_text in screen_text_list):
                    return button_name
    return None

def is_dialog_present(search_strings, screen_text_list):
    """Check if all search strings are present in the elements_text."""
    if isinstance(search_strings, str):
        search_strings = [search_strings]
    for search_string in search_strings:
        for screen_text in screen_text_list:
            if search_string.lower() in screen_text.lower():
                return screen_text  # Return the matching screen_text
        logger.info(f"{search_string} is not present.")
        return False
    return False

def handle_apple_authentication(screen_text_list):
    """Handle authentication dialogs such as 'Continue with Apple'"""
    # Check for 'Continue with Password'
    if screen_text:=is_dialog_present("Continue with Password", screen_text_list):
        return "continue with password"
    # Check for 'Continue with Apple' or 'Sign in with Apple'
    if screen_text:=is_dialog_present("Continue with Apple", screen_text_list):
        return screen_text
    elif screen_text:=is_dialog_present("Sign in with Apple", screen_text_list):
        return screen_text
    elif screen_text:=is_dialog_present("Apple sign-in", screen_text_list):
        return screen_text
    return None

def handle_cookie_dialog(screen_text_list, keywords_file_path, consent_mode="accept"):
    """Handle the cookie dialog by identifying the most appropriate action."""
    if consent_mode == "accept":
        keywords = read_text_file(keywords_file_path)
    elif consent_mode == "reject":
        return None
    if not keywords:
        logger.error("🚨 No keywords found in the file.")
        return None
    for screen_text in screen_text_list:
        lower_screen_text = screen_text.lower().replace(',', '').strip()
        for keyword in keywords:
            if levenshtein_similarity(keyword.lower().replace(',', '').strip(), lower_screen_text):
                return f"{lower_screen_text}"
    logger.error("No suitable action found for cookie dialog.")
    return None

def click_single_button(screen_text_list):
    """Check elements_text for a single button with 'Cancel' or 'OK' and return the button text."""
    # Filter out button elements_text
    buttons = [screen_text for screen_text in screen_text_list if 'button' in screen_text.lower()]
    # Check if there is exactly one button
    if len(buttons) == 1:
        button_text = buttons[0].split(',')[0].strip()  # Get the button text before ', Button' and strip any whitespace
        # Check if the button is either 'Cancel' or 'OK', case-insensitively
        if button_text.lower() in ['cancel', 'ok']:
            logger.info(f"Button '{button_text}' identified.")
            return button_text.capitalize()  # Return the button text with the first letter capitalized
        else:
            logger.info(f"The single button is not 'Cancel' or 'OK': {button_text}")
            return None
    else:
        logger.info("There is not exactly one button.")
        return None

def find_next_action_rule_based(data, consent_mode='accept', handle_native=False,
                    handle_cookie=False, handle_apple=False, is_ocr=False):
    """Decide what action to take based on the elements_text or OCR data."""
    if is_ocr:
        text_coords_list, screen_text_list = process_ocr_data(data)
    else:
        screen_text_list = data
        text_coords_list = None

    if not screen_text_list or screen_text_list == ['Direct Interaction']:
        logger.info("No accessibility data found, skipping the rest of the processing.")
        return (None, None)

    for screen_text in screen_text_list:
        if "not enabled" in screen_text.lower():
            logger.warning("❌ Not enabled element found, skipping the rest of the processing.")
            continue

    dialog_mappings = RULE_BASED_ACTION_MAPPINGS
    if consent_mode not in dialog_mappings:
        logger.error(f"Invalid action type: {consent_mode}")
        return (None, None)

    selected_mappings = dialog_mappings[consent_mode]

    if handle_native:
        command = is_dialog_present_from_mappings(screen_text_list, selected_mappings)
        if command:
            # command = f"Tap, {command}"
            logger.info(f"Command identified: {command}")
            if is_ocr:
                coords = get_coords_from_ocr(command, text_coords_list)
                return command, coords
            return (command, None)

    if handle_cookie:
        command = handle_cookie_dialog(filter_element_types(screen_text_list), KEYWORDS_FILE_PATH, consent_mode)
        if command:
            # command = f"Tap, {command}"
            logger.info(f"Command identified: {command}")
            if is_ocr:
                coords = get_coords_from_ocr(command, text_coords_list)
                return command, coords
            return (command, None)

    if handle_apple:
        command = handle_apple_authentication(filter_element_types(screen_text_list))
        if command:
            logger.info(f"Command identified: {command}")
            # if is_ocr:
            #     coords = get_coords_from_ocr(command, text_coords_list)
            #     return command, coords
            return (command, None)

    click_button = click_single_button(screen_text_list)
    if click_button:
        if is_ocr:
            coords = get_coords_from_ocr(click_button, text_coords_list)
            return click_button, coords
        return (click_button, None)

    return (None, None)

def create_rule_based_command(rule_based_element):
    """Create a rule-based command."""
    if rule_based_element == "continue with password":
        rule_based_command = "continue with password"
    else:
        rule_based_command = f"tap, {rule_based_element}"
    return rule_based_command
