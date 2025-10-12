import json
import numpy as np
from whisper_test.common import logger
try:
    from wtmi.interface import model_query_interface, model_query_classification
except ImportError:
    logger.error("❌ Error importing from wtmi.interface."
        "Please make sure the wtmi package is installed if you need it.")

def find_next_action_llm_based(screen_text_list,
                                app_id,
                                ocr_type="OMNIPARSER",
                                use_accessibility=True,
                                use_ocr=True,
                                action_history=[],
                                request_coordinates=True,
                                consent_mode="accept",
                                model_name="qwen2.5:14b",
                                use_image=False,
                                image=None):
    """Navigate to the app with the specified bundle ID using LLM.
    """
    # call find_screen_class to get the screen class
    if use_image:
        screen_class = find_screen_class(screen_text_list, use_accessibility=False, use_ocr=True)
        if screen_class == "yes":
            logger.info("❗️Consent detected, image-based approach cannot be used!")
            return None, None

    data = {
        # "screen_number": screen_number,
        "model_name": model_name,
        "verbose": True,
        "action_history": action_history,
        "request_coordinates": request_coordinates,
        "consent_mode": consent_mode,
    }
    def convert_types(obj):
        if isinstance(obj, np.int64):
            return int(obj)
        raise TypeError

    # Handle image-based input for vision models
    if use_accessibility:
        data["screen_data"] = screen_text_list
        data["data_type"] = "accessibility"
    elif use_ocr and ocr_type == "EASYOCR":
        ocr_json_str = json.dumps(screen_text_list, default=convert_types)
        data["screen_data"] = ocr_json_str
        data["data_type"] = "ocr"
    elif use_ocr and ocr_type == "OMNIPARSER":
        data["screen_data"] = json.dumps(screen_text_list)#(json.loads(screen_text_list))
        data["data_type"] = "ocr"
    elif use_image:
        data["image"] = image
        data["data_type"] = "image"
    logger.info(f"🚨 Data sent to LLM: {data}")
    try:
        response, screen_class = model_query_interface(data)
        logger.info(f"💡 LLM response navigation: {response}")
        if screen_class and screen_class=="yes":
            logger.info("✅ Consent detected for appID: %s", app_id)
    except Exception as e:
        logger.error("❌ Connection error occurred: %s", e)
        return None, None
    # try:
    #     response = requests.post(API_URL, json=data)
    # except requests.exceptions.ConnectionError as e:
    #     logger.error("❌ Connection error occurred: %s", e)
    #     return None, None
    if response:
        logger.info("LLM response: %s", response)
        try:
            llm_output = response
            action = llm_output.get('action')
            element = llm_output.get('screen_element') or llm_output.get('value')
            if element is not None:
                final_command = f"{action}, {element.replace('[', '').replace(']', '')}"
            else:
                final_command = f"{action}"
            return final_command, llm_output
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error("Failed to extract command: %s", e)
            return None, None
    else:
        logger.error("Error: %s", response)
        return None, None

def find_screen_class(screen_text_list,
                      ocr_type="OMNIPARSER",
                      use_accessibility=True,
                      use_ocr=False,
                      verbose=False):
    """Navigate to the app with the specified bundle ID using LLM.
    """
    data ={}
    data["verbose"] = verbose
    def convert_types(obj):
        if isinstance(obj, np.int64):
            return int(obj)
        raise TypeError

    # Handle image-based input for vision models
    if use_accessibility:
        data["screen_data"] = screen_text_list
        data["data_type"] = "accessibility"
    elif use_ocr and ocr_type == "EASYOCR":
        ocr_json_str = json.dumps(screen_text_list, default=convert_types)
        data["screen_data"] = ocr_json_str
        data["data_type"] = "ocr"
    elif use_ocr and ocr_type == "OMNIPARSER":
        data["screen_data"] = json.dumps(screen_text_list)
        data["data_type"] = "ocr"
    logger.info(f"🚨 Data sent to LLM: {data}")
    try:
        response = model_query_classification(data)
    except Exception as e:
        logger.error("❌ Connection error occurred: %s", e)
        return None
    return response
