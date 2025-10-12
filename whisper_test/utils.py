import re
import os
import json
from time import sleep
from datetime import datetime
from typing import Set
from whisper_test.common import logger

try:
    import imagehash
except ImportError:
    logger.error("❌ imagehash package not found. Install it using 'pip install imagehash'")
    imagehash = None

try:
    from Levenshtein import distance as levenshtein_distance
except ImportError:
    logger.error("❌ Levenshtein package not found. Install it using 'pip install levenshtein'")
    levenshtein_distance = None

try:
    from PIL import Image
except ImportError:
    logger.error("❌ Pillow package not found. Install it using 'pip install Pillow'")
    Image = None

try:
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    # Ensure necessary resources are downloaded
    # nltk.download('punkt')
    # nltk.download('stopwords')
    # nltk.download('wordnet')
    ########################################################
    # to download before running the script:
    # python -m nltk.downloader punkt stopwords wordnet

    # Initialize stopwords and lemmatizer
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
except ImportError:
    logger.error("❌ nltk package not found. Install it using 'pip install nltk'")
    stop_words = None
    lemmatizer = None
    WordNetLemmatizer = None
try:
    from pymobiledevice3.tunneld.api import async_get_tunneld_devices
except ImportError:
    # fallback for older versions of pymobiledevice3
    from pymobiledevice3.tunneld import async_get_tunneld_devices

from pymobiledevice3.services.afc import AfcService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.screenshot import Screenshot
from whisper_test.common import logger, ELEMENT_TYPES
from whisper_test.exceptions import NoDeviceConnectedError, MultipleDevicesConnectedError



def take_screenshot_dvt(screenshot_path, dvt):
    """ Take a screenshot and save it to the specified file name """
    try:
        with DvtSecureSocketProxyService(dvt) as dvt:
            with open(screenshot_path, 'wb') as out:
                out.write(Screenshot(dvt).get_screenshot())
        logger.info("Screenshot saved to %s", screenshot_path)
    except Exception as e:
        logger.error("Failed to take screenshot. Error: %s", e)

async def get_active_tunnel_conn():
    """Return the active tunnel to the connected iOS device.

    Requires an rsd connection set up with:
    sudo -E pymobiledevice3 remote tunneld
    """
    try:
        rsds = await async_get_tunneld_devices()
    except Exception as tce:
        logger.error("❌ Cannot find an active connection.\
                     Please start a tunnel first: %s", tce)
        return None

    if len(rsds) == 0:
        raise NoDeviceConnectedError("Device not connected or tunnel not established.")
    elif len(rsds) > 1:
        raise MultipleDevicesConnectedError("Does not support multiple devices")
    return rsds[0]

def is_text_in_syslog(texts, syslog, timeout=3):
    """Check if any of the specified texts are present in the syslog."""
    try:
        while True:
            syslog_entry = syslog.queue.get(timeout=timeout)
            if any(text in syslog_entry for text in texts):
                logger.info(f"✅ {texts} found in syslog: {syslog_entry}")
                return syslog_entry
    except Exception as e:
        logger.info(f"❌ Text not found in syslog. Error: {e}")
        pass
    return False

def save_processed_app_index(file_path, processed_file):
    """Save the processed app index and URL file to a text file."""
    with open(file_path, 'a') as file:
        file.write(processed_file + '\n')

def read_processed_app_index(file_path):
    """Read the processed apps from a text file."""
    try:
        with open(file_path, 'r') as file:
            return {line.strip() for line in file.readlines()}
    except FileNotFoundError:
        return set()

def is_app_already_processed(app_id: str, processed_apps: Set[str]) -> bool:
    """Check if the app is already processed by comparing first and second elements."""
    return any(entry.startswith(app_id) for entry in processed_apps)

def levenshtein_similarity(text1, text2, threshold=2):
    """Check if two texts are similar within a given Levenshtein distance threshold."""
    text2 = text2.lower().replace("tap, ","").replace("type, ","").replace('[', '').replace(']', '')
    if len(text1) <= 3 or len(text2) <= 3:
        return text1 == text2
    return levenshtein_distance(text1, text2) < threshold

def read_text_file(file_path):
    """Read text from a file and return a list of text."""
    if not file_path:
        logger.error("File path is None or empty.")
        return None
    try:
        with open(file_path, 'r') as file:
            text = file.readlines()
        text = [line.strip() for line in text]
        return text
    except Exception as e:
        logger.error(f"An error occurred while reading the file: {e}")
        return None

def load_json_file(file_path):
    """Load a JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

def filter_element_types(captions):
    """ Filters out the element types and any text following them in the elements list """
    filtered_elements = []
    for text in captions:
        parts = text.split(',')
        # Find the first occurrence of an element type and truncate the list
        for i, part in enumerate(parts):
            if part.strip() in ELEMENT_TYPES:
                parts = parts[:i]
                break
        cleaned_text = ', '.join(part.strip() for part in parts)
        filtered_elements.append(cleaned_text)
    return filtered_elements

def are_images_different(image1_path, image2_path, hashfunc=imagehash.average_hash, hash_size=32):
    """ Check if two images are different """
    try:
        print("💡 image1_path:", image1_path)
        print("💡 image2_path:", image2_path)
        hash1 = hashfunc(Image.open(image1_path), hash_size=hash_size)
        hash2 = hashfunc(Image.open(image2_path), hash_size=hash_size)
    except Exception as e:
        print('Problem:', e)
        return False
    return hash1 != hash2

def get_timestamp():
    """Get the current timestamp."""
    return datetime.now().strftime('%Y%m%d_%H%M%S%f')

def calculate_elements_similarity(elements_before, elements_after):
    """ Calculate the similarity percentage between two sets of a11y labels. """
    try:
        common_elements = set(elements_before) & set(elements_after)
        total_elements = set(elements_before) | set(elements_after)
        return (len(common_elements) / len(total_elements)) * 100
    except Exception as e:
        logger.error(f"An error occurred while calculating similarity: {e}")
        return None

def is_app_index_in_links(app_index, element_list):
    """Check if the app_index is present as a number in any 'Link' element of the element_list."""
    for element in element_list:
        parts = element.split(', ')
        if len(parts) == 2 and parts[1] == 'Link':
            if parts[0] == app_index:
                return True
    return False

def normalize_text(text_list, remove_stopwords=False, apply_lemmatization=True):
    """
    Systematically normalizes a list of texts:
    - Lowercase
    - Remove punctuation
    - Tokenize words
    - Optionally remove stopwords
    - Optionally apply lemmatization
    - Remove words containing symbols
    - Remove words containing digits
    - Remove words with only one character
    """
    cleaned_tokens = []

    for text in text_list:
        text = str(text).lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        tokens = word_tokenize(text)

        processed_tokens = []
        for token in tokens:
            # Skip tokens containing symbols, digits, or with only one character
            if re.search(r'\W|\d', token) or len(token) == 1:
                continue
            if remove_stopwords and token in stop_words:
                continue
            if apply_lemmatization:
                token = lemmatizer.lemmatize(token)
            processed_tokens.append(token)

        cleaned_tokens.extend(processed_tokens)

    return set(cleaned_tokens)

def fuzzy_jaccard_similarity(set1, set2, threshold=2):
    """
    Compute Jaccard similarity with fuzzy word matching.
    Words are considered a match if their levenshtein distance is above the threshold.
    """
    print("💡 set1:", set1)
    print("💡 set2:", set2)
    matched_words = set()

    for word1 in set1:
        for word2 in set2:
            if levenshtein_distance(word1, word2) <= threshold:
                matched_words.add(word1)  # Count as a match

    intersection = len(matched_words)
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0

def check_last_action_history(action_history, command):
    """Check if the last action is in the action history."""
    for element in action_history:
        screen_element = element.get("screen_element")
        if screen_element == command:
            return True
    return False

def add_action_to_history(action_history, command=None, deduplicate=True, command_success=False):
    """Add an action to the action history."""
    if command is not None:
        if not isinstance(command, dict) or "action" not in command:
            command = {"action": "tap", "screen_element": command}

        if deduplicate:
            if not check_last_action_history(action_history, command.get("screen_element")):
                action_history.append(command)
        else:
            if command_success:
                action_history.append((command, "success"))
            else:
                action_history.append((command, "failure"))

    return action_history, None

def transfer_single_video(lockdown, dcim_path='/DCIM/101APPLE/', local_path='videos/', new_file_name='renamed_video.mp4'):
    """Transfer a single video file from the iPhone to the local directory.
    
    Args:
        lockdown: pymobiledevice3 lockdown client
        dcim_path: Path to DCIM directory on device (may vary by device)
        local_path: Local directory to save video
        new_file_name: Filename for the transferred video
        
    Returns:
        bool: True if transfer successful, False otherwise
        
    Note:
        The dcim_path may need adjustment based on device configuration.
        Common paths: /DCIM/100APPLE/, /DCIM/101APPLE/
    """

    # Create the AfcService object
    afc = AfcService(lockdown)

    # Ensure the local directory exists
    os.makedirs(local_path, exist_ok=True)

    try:
        # List files in the DCIM directory
        sleep(4)
        files = afc.listdir(dcim_path)

        # Filter for video files (e.g., .mp4 or .mov)
        video_files = [file for file in files if file.lower().endswith(('.mp4', '.mov'))]
        print(video_files, 'video files')

        if not video_files:
            logger.info('No video files found in the specified directory.')
            return

        # Assuming there's only one video file
        original_file_name = video_files[-1]
        original_file_path = os.path.join(dcim_path, original_file_name)
        new_file_path = os.path.join(dcim_path, new_file_name)

        # Rename the file on the iPhone
        afc.rename(original_file_path, new_file_path)
        logger.info(f'Renamed {original_file_name} to {new_file_name} on device')

        # Define the local file path
        local_file_path = os.path.join(local_path, new_file_name)

        # Transfer the renamed file to the local directory
        afc.pull(new_file_path, local_file_path)
        logger.info(f'Transferred {new_file_name} to local directory')

        files = afc.listdir(dcim_path)
        test = [file for file in files if file.lower().endswith(('.mp4', '.mov'))]
        print(test)

        # Delete the renamed file from the iPhone
        undeleted_files = afc.rm(new_file_path, force=True)
        if undeleted_files:
            logger.error(f'Failed to delete the following files: {undeleted_files}')
        else:
            logger.info(f'Deleted {new_file_name} from device')

        return True

    except Exception as e:
        logger.error(f'An error occurred: {e}')
        return False

def remove_media_dir_on_device(lockdown, media_dir='/DCIM/'):
    """Remove a directory on the device."""
    try:
        afc = AfcService(lockdown)
        afc.rm(media_dir, force=True)
        logger.info(f'Deleted {media_dir} from device')
    except Exception as e:
        logger.error(f'An error occurred: {e}')
