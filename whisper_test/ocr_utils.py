import base64
import cv2
import json
import os
import requests
import time
import numpy as np
from easyocr import Reader
from io import BytesIO
from os.path import basename
from PIL import Image
from whisper_test.common import logger
from whisper_test.utils import levenshtein_similarity, fuzzy_jaccard_similarity, normalize_text, are_images_different


RESIZE_MAX_IMG_DIM = 800

def get_omniparser_url():
    """Get Omniparser API URL from config or use default."""
    from whisper_test.common import _config
    return _config.get('omniparser_api_url', "http://0.0.0.0:5003/process")

# API endpoint for the Omniparser OCR service
OMNIPARSER_OCR_API_URL = get_omniparser_url()

def resize_image(img, max_dim=RESIZE_MAX_IMG_DIM):
    """Resize the image to have at most max_dim in any dimension."""
    print(f"Original image dims: {img.shape}")
    logger.info(f"Original image dims: {img.shape}")
    scale = max_dim / max(img.shape[:2])
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale)
        print(f"Resized image dims: {img.shape}")
        logger.info(f"Resized image dims: {img.shape}")
    else:
        print(f"Image dims are already within max_dim: {img.shape}")
        logger.info(f"Image dims are already within max_dim: {img.shape}")
    return img


def get_detection_bounding_box(detection):
    """Return the bounding box of the detected text."""
    # this assumes that the bounding box is a rectangle
    x1 = detection[0][0][0]
    x2 = detection[0][1][0]
    y1 = detection[0][0][1]
    y2 = detection[0][2][1]
    w = x2 - x1
    h = y2 - y1

    # assertions will fail for non-rectangular bounding boxes
    assert len(detection[0]) == 4, f"Detection: {detection}"
    assert len(detection[0][0]) == 2, f"Detection: {detection}"

    return x1, y1, w, h

def draw_bounding_box(img, detection):
    """Draw a bounding box around the detected text."""
    pts = np.array([detection[0]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(img, [pts], True, (0, 255, 0), 2)

def ocr_image(img_path, reader, draw_bbox=False, out_prefix='out'):
    """Read text from an image and draw bounding boxes around the detected text."""
    results = []
    img_name = os.path.basename(img_path)
    print("============================")
    print(f"Processing image: {img_name}")
    logger.info(f"Processing image: {img_name}")

    img = cv2.imread(img_path)
    # Check image orientation
    height, width = img.shape[:2]
    if width > height:
        print("Image is in landscape orientation")
        logger.info("Image is in landscape orientation")
        # Add landscape-specific processing here if needed
    else:
        print("Image is in portrait orientation")
        logger.info("Image is in portrait orientation")
        # Add portrait-specific processing here if needed

    t0 = time.time()
    detections = reader.readtext(img)
    ocr_duration = time.time() - t0
    print(f"OCR call took: {ocr_duration:.2f} s")
    logger.info(f"OCR call took: {ocr_duration:.2f} s")

    for detection in detections:
        x1, y1, w, h = get_detection_bounding_box(detection)
        text = detection[1]
        print("============================")
        print(f"Bounding box: {x1, y1, w, h}")
        print(f"Text: {text}")
        logger.info(f"Bounding box: {x1, y1, w, h}")
        logger.info(f"Text: {text}")
        draw_bounding_box(img, detection)
        results.append((text, x1, y1, w, h))

    print("write image with bounding boxes to file")
    logger.info("write image with bounding boxes to file")
    out_img_path = img_path.replace('.png', f'-{out_prefix}.png')
    cv2.imwrite(out_img_path, img)
    # write detection results to json file
    return results

def ocr_img_by_ez_ocr(img_path: str):
    """Read text from all images in a directory and write the results to a json file."""
    results = {}
    # initialize the OCR reader
    reader = Reader(['en'])

    results[img_path] = ocr_image(img_path, reader, draw_bbox=True)
    # Write the results to a json file
    result_json_path = img_path.replace(".png", "") + "ez_ocr.json"
    with open(result_json_path, 'w') as f:
        f.write(json.dumps(results, indent=4, default=str))
    return results

def ocr_img_by_omniparser(img_path: str):
    """Read text from an image using the Omniparser OCR service."""
     # Path to the image you want to send
    image_name = basename(img_path)
    # Send the image as a POST request
    with open(img_path, 'rb') as image_file:
        response = requests.post(
            OMNIPARSER_OCR_API_URL,
            files={'image': image_file},  # Send the image file here
            data={'img_name': image_name}  # Send additional form data here
        )
    # Check the response
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        # Get the base64 image from the response
        base64_image = data['based64_image']

        # Decode the image
        image_data = base64.b64decode(base64_image)
        image = Image.open(BytesIO(image_data))

        # Optionally, save the image locally
        # image.save("processed_image.png")
        return data["structured_results"]
    else:
        print(f"Failed to get a response. Status code: {response.status_code}")
        print(response.text)
        return None

def has_screen_changed(sc_name_before: str, sc_name_after: str, threshold: float = 0.85) -> bool:
    """Check if the screen has changed and return True if it has."""
    logger.info("🚀 Checking if screen has changed")
    try:
        screen_data_before = ocr_img_by_omniparser(sc_name_before)
        screen_data_after = ocr_img_by_omniparser(sc_name_after)
        if screen_text_changed(screen_data_before, screen_data_after, threshold=threshold) and are_images_different(sc_name_before, sc_name_after):
            logger.info("✅ Screen has changed")
            return True
        logger.info("❌ Screen has not changed")
        return False
        # screen_elements_after = self.get_screen_content_by_a11y(max_items=15)
        # sc_name_after = f"{MEDIA_PATH}/{app_id}_after_{get_timestamp()}.png"
        # self.take_screenshot(sc_name_after)

        # a11y_similarity = calculate_elements_similarity(screen_elements, screen_elements_after)
        # images_different = are_images_different(sc_name_before, sc_name_after)
        # return images_different
        # if a11y_similarity is not None:
        #     if images_different and a11y_similarity < SIMILARITY_A11Y_THRESHOLD:
        #         return True
        # else:
        #     logger.info("❌ No similarity found between screen elements, returning images_different: %s", images_different)
        #     return images_different

    except Exception as e:
        logger.error("❌ Error checking if screen has changed: %s", e)
        return False

def screen_text_changed(screen_data_before, screen_data_after, threshold=0.85):
    """Compare the screen data before and after clicking."""
    text1, icon1 = (extract_texts_from_ocr(screen_data_before))
    text2, icon2 = (extract_texts_from_ocr(screen_data_after))
    print(f"💡 Text1: {text1}")
    print(f"💡 Text2: {text2}")
    if len(text1) == 0 and len(text2) == 0:
        return False
    distance = fuzzy_jaccard_similarity(normalize_text(text1), normalize_text(text2))
    return distance < threshold

def extract_texts_from_ocr(data_list):
    """Separate 'Text' and 'icon' entries into different lists."""
    text_entries = []
    icon_entries = []

    for item in data_list:
        category = item[1]
        text_value = item[2]

        if category.lower() == "text":
            text_entries.append(text_value)
        elif category.lower() == "icon":
            icon_entries.append(text_value)

    return text_entries, icon_entries

def process_ocr_data(ocr_data):
    """Process OCR data to extract text and coordinates."""
    text_coords_list = []
    captions = []
    # Determine the data format based on the first element
    if isinstance(ocr_data, dict):
        # ez_ocr format: {'ocr_test.png': [('text', x1, y1, x2, y2), ...]}
        for value in ocr_data.values():
            for item in value:
                text, coords = item[0], item[1:]
                lower_text = text.lower().replace(',', '').strip()
                text_coords_list.append((lower_text, coords))
                captions.append(lower_text)
    elif isinstance(ocr_data, list):
        # Check if this is the new dictionary format or the old list format
        if ocr_data and isinstance(ocr_data[0], dict) and "text" in ocr_data[0]:
            # New dictionary format
            for item in ocr_data:
                text = item["text"]
                coords = (int(item["x"]), int(item["y"]), int(item["width"]), int(item["height"]))
                lower_text = text.lower().replace(',', '').strip()
                text_coords_list.append((lower_text, coords))
                captions.append(lower_text)
        else:
            # Old Omniparser format: [['index', 'type', 'text', 'interactivity' x1, y1, x2, y2], ...]
            for item in ocr_data:
                text, coords = item[2], tuple(map(int, item[4:]))
                lower_text = text.lower().replace(',', '').strip()
                text_coords_list.append((lower_text, coords))
                captions.append(lower_text)

    return text_coords_list, captions

def get_coords_from_ocr(command, screen_data):
    print(f"💡 Command: {command}")
    print(f"💡 Screen data: {screen_data}")
    text_coords_list, _ = process_ocr_data(screen_data)
    for lower_text, coords in text_coords_list:
        if levenshtein_similarity(lower_text, command):
            return coords
    return None

######################## grid method utils #########################
def get_matching_grid_number(image_path, detection_coordinates):
    """ Find the matching grid number and draw the grid on the image """
    # Define the grid dimensions
    portrait_rows = 15
    portrait_columns = 10
    landscape_rows = 10
    landscape_columns = 15
    matching_number, matching_sub_cell, matching_finer_sub_cell = None, None, None
    # Get the screen dimensions
    width, height = get_image_dimensions(image_path)
    # Determine if the screen is in landscape mode
    if width > height:
        rows, columns = landscape_rows, landscape_columns
        landscape = True
    else:
        rows, columns = portrait_rows, portrait_columns
        landscape = False
    # Calculate the grid coordinates
    grid_coordinates = calculate_grid_coordinates(width, height, rows, columns, landscape)
    # Draw the grid on the image
    # draw_grid_on_image(image_path, grid_coordinates, output_path)
    # Convert grid coordinates to (x1, y1, w, h) format
    xywh_grid_coordinates = convert_to_xywh_format(grid_coordinates)
    # Find the best matching cell
    matching_number = find_best_matching_cell(xywh_grid_coordinates, detection_coordinates, landscape)
    if matching_number:
        print(f"Initial matching grid cell: {matching_number}")
        # Subdivide the matching cell into smaller cells
        target_cell_coordinates = grid_coordinates[matching_number]
        print(f"Initial target cell coordinates: {target_cell_coordinates}")
        sub_cells = subdivide_cell(target_cell_coordinates, subdivision_factor=3)
        sub_xywh_grid_coordinates = convert_to_xywh_format(sub_cells)
        # Find the best matching sub cell
        matching_sub_cell = find_best_matching_cell(sub_xywh_grid_coordinates, detection_coordinates, landscape)
        print(f"Matching sub-cell: {matching_sub_cell} within grid cell {matching_number}")
        if matching_sub_cell:
            # Further subdivide the matching sub-cell into even smaller cells (3*3)
            target_sub_cell_coordinates = sub_cells[matching_sub_cell]
            print(f"Target sub cell coordinates: {target_sub_cell_coordinates}")
            finer_sub_cells = subdivide_cell(target_sub_cell_coordinates, subdivision_factor=3)
            finer_xywh_grid_coordinates = convert_to_xywh_format(finer_sub_cells)
            # Find the best matching finer sub cell
            matching_finer_sub_cell = find_best_matching_cell(finer_xywh_grid_coordinates, detection_coordinates, landscape)
            print(f"Finer sub cell coordinates: {finer_sub_cells[matching_finer_sub_cell]}")
            print(f"Matching finer sub-cell: {matching_finer_sub_cell} within sub-cell {matching_sub_cell}")
    else:
        print("No matching grid cell found.")

    return matching_number, matching_sub_cell, matching_finer_sub_cell, landscape

def get_image_dimensions(image_path):
    """ Find the dimensions of the image """
    image = Image.open(image_path)
    return image.size

def calculate_grid_coordinates(image_width, image_height, rows, columns, landscape=False):
    """ Calculate the coordinates of the grid cells on the mobile screen """
    cell_width = image_width / columns
    cell_height = image_height / rows
    coordinates = {}
    for row in range(rows):
        for col in range(columns):
            if landscape:
                num = row * columns + col + 1
            else:
                num = row * columns + col + 1
            x1 = round(col * cell_width)
            y1 = round(row * cell_height)
            x2 = round(x1 + cell_width)
            y2 = round(y1 + cell_height)
            coordinates[num] = (x1, y1, x2, y2)
    return coordinates

def convert_to_xywh_format(coordinates):
    """ Convert the coordinates to the xywh format """
    xywh_coordinates = {}
    for num, (x1, y1, x2, y2) in coordinates.items():
        w = x2 - x1
        h = y2 - y1
        xywh_coordinates[num] = (x1, y1, w, h)
    return xywh_coordinates

def find_best_matching_cell(xywh_coordinates, detection_coordinates, landscape=False):
    """ Find the best matching cell """
    best_match = None
    smallest_difference = float('inf')
    for num, coord in xywh_coordinates.items():
        x1_diff = abs(coord[0] - detection_coordinates[0])
        y1_diff = abs(coord[1] - detection_coordinates[1])
        w_diff = abs(coord[2] - detection_coordinates[2])
        h_diff = abs(coord[3] - detection_coordinates[3])
        x2_diff = abs(coord[0] + coord[2] - detection_coordinates[0] - detection_coordinates[2])
        y2_diff = abs(coord[1] + coord[3] - detection_coordinates[1] - detection_coordinates[3])
        total_difference = x1_diff + y1_diff + w_diff + h_diff + x2_diff + y2_diff
        if total_difference < smallest_difference:
            smallest_difference = total_difference
            best_match = num
    return best_match

def subdivide_cell(cell_coordinates, subdivision_factor=3):
    """ Subdivide the cell into smaller cells """
    x1, y1, x2, y2 = cell_coordinates
    cell_width = (x2 - x1) / subdivision_factor
    cell_height = (y2 - y1) / subdivision_factor
    sub_cells = {}
    sub_cell_num = 1
    for row in range(subdivision_factor):
        for col in range(subdivision_factor):
            sub_x1 = round(x1 + col * cell_width)
            sub_y1 = round(y1 + row * cell_height)
            sub_x2 = round(sub_x1 + cell_width)
            sub_y2 = round(sub_y1 + cell_height)
            sub_cells[sub_cell_num] = (sub_x1, sub_y1, sub_x2, sub_y2)
            sub_cell_num += 1
    return sub_cells

def is_within_screen(detection_coordinates, screen_width, screen_height):
    x1, y1, w, h = detection_coordinates
    x2 = x1 + w
    y2 = y1 + h
    return 0 <= x1 < screen_width and 0 <= y1 < screen_height and 0 <= x2 <= screen_width and 0 <= y2 <= screen_height

