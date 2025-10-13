import time

import flask
import usb_gadget

# These are copied from Appendix E.6 and E.10 of the protocol specification respectively:
# https://www.usb.org/sites/default/files/hid1_11.pdf
# The commented out keyboard bytes are for LEDs, which are not relevant to us
KEYBOARD_DESCRIPTOR = (
    "05 01"
    "09 06"
    "a1 01"
    "05 07"
    "19 e0"
    "29 e7"
    "15 00"
    "25 01"
    "75 01"
    "95 08"
    "81 02"
    "95 01"
    "75 08"
    "81 01"
#   "95 05"
#   "75 01"
#   "05 08"
#   "19 01"
#   "29 05"
#   "91 02"
#   "95 01"
#   "75 03"
#   "91 01"
    "95 06"
    "75 08"
    "15 00"
    "25 65"
    "05 07"
    "19 00"
    "29 65"
    "81 00"
    "c0"
)
MOUSE_DESCRIPTOR = (
    "05 01"
    "09 02"
    "a1 01"
    "09 01"
    "a1 00"
    "05 09"
    "19 01"
    "29 03"
    "15 00"
    "25 01"
    "95 03"
    "75 01"
    "81 02"
    "95 01"
    "75 05"
    "81 01"
    "05 01"
    "09 30"
    "09 31"
    "15 81"
    "25 7f"
    "75 08"
    "95 02"
    "81 06"
    "c0"
    "c0"
)

# A mapping from characters that require shift to their corresponding base characters
SHIFT_MAP = {
    "~": "`",
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    "\"": "'",
    "<": ",",
    ">": ".",
    "?": "/"
}

# The amount of mouse units it takes to move from one side of the screen to the other
# TODO: Make sure that this works on all iOS devices
X_MOUSE_UNITS = 1000
Y_MOUSE_UNITS = 1000

# How long to wait for the USB connection to be established
# Not waiting long enough results in a BrokenPipeError
INIT_WAIT = 1 # seconds

app = flask.Flask(__name__)

# --- Helpers ---

def to_mouse_units(coordinates, screen_size):
    x_in, y_in = coordinates
    x_screen, y_screen = screen_size
    x_out = (x_in * X_MOUSE_UNITS) // x_screen
    y_out = (y_in * Y_MOUSE_UNITS) // y_screen
    return x_out, y_out

def to_pixels(coordinates, screen_size):
    x_in, y_in = coordinates
    x_screen, y_screen = screen_size
    x_out = (x_in * x_screen) // X_MOUSE_UNITS
    y_out = (y_in * y_screen) // Y_MOUSE_UNITS
    return x_out, y_out

def format(success=None, message=None, **kwargs):
    output = {}
    if success is not None:
        output["success"] = success
    if message:
        output["message"] = message
    output.update(kwargs)
    return output # Flask automatically converts dicts to JSON

def _open():
    # If Flask was previously stopped without calling close(), this cleans up the old data
    old_gadget = usb_gadget.USBGadget("usb_control")
    old_gadget.destroy()

    gadget = usb_gadget.USBGadget("usb_control")
    gadget.idVendor = "0x1d6b" # 0x1d6b -> The Linux Foundation
    gadget.idProduct = "0x0104" # 0x0104 -> Multifunction Composite Gadget

    strings = gadget["strings"]["0x409"] # 0x409 -> English
    strings.serialnumber = "1"
    strings.manufacturer = "WhisperTest"
    strings.product = "USB control"

    config = gadget["configs"]["c.1"]
    config["strings"]["0x409"].configuration = "USB control config"

    keyboard_function = usb_gadget.HIDFunction(gadget, "keyboard0")
    keyboard_function.report_desc = bytes.fromhex(KEYBOARD_DESCRIPTOR) # Identifies the USB device to the host
    keyboard_function.report_length = "8" # Data length, in this case 1B modifiers + 1B reserved + 6B keys
    gadget.link(keyboard_function, config)

    mouse_function = usb_gadget.HIDFunction(gadget, "mouse0")
    mouse_function.report_desc = bytes.fromhex(MOUSE_DESCRIPTOR)
    mouse_function.report_length = "3" # 1B mouse buttons + 1B mouse X + 1B mouse Y
    gadget.link(mouse_function, config)

    gadget.activate()
    time.sleep(INIT_WAIT)

    keyboard = usb_gadget.KeyboardGadget(keyboard_function.device, key_count=6, auto_update=True)
    mouse = usb_gadget.MouseGadget(mouse_function.device, resolution=1, buttons=3, wheels=0, auto_update=True)

    return gadget, keyboard, mouse

def _keyboard_type(keyboard, text):
    # We assume a clean environment (no Caps Lock, no keys being pressed)
    shift = False

    for char in text:
        if (mapped := SHIFT_MAP.get(char)) or char.isupper():
            if not shift:
                keyboard.press("SHIFT_LEFT")
                shift = True
        elif shift:
            keyboard.release("SHIFT_LEFT")
            shift = False
        if mapped:
            char = mapped
        keyboard.press(char)
        keyboard.release(char)

    if shift:
        keyboard.release("SHIFT_LEFT")

def _mouse_reset_coordinates(mouse, mouse_coordinates):
    _mouse_move(mouse, -X_MOUSE_UNITS, -Y_MOUSE_UNITS)
    mouse_coordinates[0] = 0
    mouse_coordinates[1] = 0

def _mouse_move(mouse, x, y, mouse_coordinates=None):
    if mouse_coordinates:
        x_start, y_start = mouse_coordinates
        dx = x - x_start
        dy = y - y_start
    else:
        dx, dy = x, y
    steps = max(abs(dx), abs(dy))
    if not steps:
        return
    dx_step = dx / steps
    dy_step = dy / steps
    x_cur = 0 # x_cur and y_cur are relative to the start coordinates
    y_cur = 0
    for _ in range(steps):
        x_new = x_cur + dx_step
        y_new = y_cur + dy_step
        mouse.move(round(x_new) - round(x_cur), round(y_new) - round(y_cur))
        x_cur = x_new
        y_cur = y_new

# --- Parsers ---

def parse_open(json):
    screen_size = json.get("screen_size")
    if type(screen_size) != list or len(screen_size) != 2:
        raise ValueError("Invalid value for screen_size")
    x_screen, y_screen = screen_size
    if type(x_screen) != int or type(y_screen) != int:
        raise ValueError("screen_size must be integers")

    return x_screen, y_screen

def parse_keyboard_key(json):
    key = json.get("key")
    if type(key) != str:
        raise ValueError("Invalid value for key")
    # Design choice: We accept A for a but not ! for 1
    if key in SHIFT_MAP:
        raise ValueError("Character requires shift, specify the corresponding base character instead")

    return key.upper()

def parse_keyboard_type(json):
    text = json.get("text")
    if type(text) != str:
        raise ValueError("Invalid value for text")
    if not text.isascii():
        raise ValueError("text must be ASCII")

    return text

def parse_mouse_move(json, screen_size):
    absolute = True
    match json.get("mode"):
        case "absolute":
            absolute = True
        case "relative":
            absolute = False
        case None:
            pass
        case _:
            raise ValueError("Invalid value for mode")

    target_coordinates = json.get("target_coordinates")
    if type(target_coordinates) != list or len(target_coordinates) != 2:
        raise ValueError("Invalid value for target_coordinates")
    x_target, y_target = target_coordinates
    if type(x_target) != int or type(x_target) != int:
        raise ValueError("target_coordinates must be integers")
    x_screen, y_screen = screen_size
    # TODO: Bound checks for relative mode
    if absolute and (not 0 <= x_target < x_screen or not 0 <= y_target < y_screen):
        raise ValueError("target_coordinates are out of bounds")
    x, y = to_mouse_units(target_coordinates, screen_size)

    return absolute, x, y

def parse_mouse_button(json):
    button = 0
    match json.get("button"):
        case "left":
            button = 0
        case "right":
            button = 1
        case "middle":
            button = 2
        case None:
            pass
        case _:
            raise ValueError("Invalid value for button")

    return button

# --- Generic endpoints ---

@app.get("/")
def info():
    return "WhisperTest USB control HTTP API"

@app.get("/status")
def status():
    connected = hasattr(app, "gadget")
    if not connected:
        return format(connected=False)
    mouse_coordinates = to_pixels(app.mouse_coordinates, app.screen_size)
    return format(connected=True, mouse_coordinates=mouse_coordinates)

@app.post("/open")
def open():
    if hasattr(app, "gadget"):
        return format(False, "USB connection already open")

    try:
        json = flask.request.json
        x_screen, y_screen = parse_open(json)
        gadget, keyboard, mouse = _open()
        app.gadget = gadget
        app.keyboard = keyboard
        app.mouse = mouse
        app.mouse_coordinates = [None, None]
        app.screen_size = [x_screen, y_screen]
        _mouse_reset_coordinates(app.mouse, app.mouse_coordinates)
        return format(True)
    except ValueError as e:
        return format(False, str(e))
    except BrokenPipeError:
        # This is a specific common case of OSError
        return format(False, "USB connection was not open when we tried to send data, "
            "either the devices cannot see each other or the USB handshake took too long")
    except OSError as e:
        return format(False, repr(e))

@app.post("/close")
def close():
    if not hasattr(app, "gadget"):
        return format(False, "USB connection not open")

    try:
        app.gadget.destroy()
        del app.gadget
        del app.keyboard
        del app.mouse
        del app.mouse_coordinates
        del app.screen_size
        return format(True)
    except OSError as e:
        return format(False, repr(e))

# --- Keyboard endpoints ---

@app.post("/keyboard/down")
def keyboard_down():
    if not hasattr(app, "keyboard"):
        return format(False, "Keyboard not initialized")

    try:
        json = flask.request.json
        key = parse_keyboard_key(json)
        app.keyboard.press(key)
        return format(True)
    except ValueError as e:
        return format(False, str(e))
    except AttributeError as e:
        return format(False, "Unknown key")
    except OSError as e:
        return format(False, repr(e))

@app.post("/keyboard/up")
def keyboard_up():
    if not hasattr(app, "keyboard"):
        return format(False, "Keyboard not initialized")

    try:
        json = flask.request.json
        key = parse_keyboard_key(json)
        app.keyboard.release(key)
        return format(True)
    except ValueError as e:
        return format(False, str(e))
    except AttributeError as e:
        return format(False, "Unknown key")
    except OSError as e:
        return format(False, repr(e))

@app.post("/keyboard/type")
def keyboard_type():
    if not hasattr(app, "keyboard"):
        return format(False, "Keyboard not initialized")

    try:
        json = flask.request.json
        text = parse_keyboard_type(json)
        _keyboard_type(app.keyboard, text)
        return format(True)
    except ValueError as e:
        return format(False, str(e))
    except OSError as e:
        return format(False, repr(e))

# --- Mouse endpoints ---

@app.post("/mouse/reset_coordinates")
def mouse_reset_coordinates():
    if not hasattr(app, "mouse"):
        return format(False, "Mouse not initialized")

    try:
        _mouse_reset_coordinates(app.mouse, app.mouse_coordinates)
        return format(True)
    except OSError as e:
        return format(False, repr(e))

@app.post("/mouse/move")
def mouse_move():
    if not hasattr(app, "mouse"):
        return format(False, "Mouse not initialized")

    try:
        json = flask.request.json
        absolute, x, y = parse_mouse_move(json, app.screen_size)
        _mouse_move(app.mouse, x, y, app.mouse_coordinates if absolute else None)
        if absolute:
            app.mouse_coordinates[0] = x
            app.mouse_coordinates[1] = y
        else:
            app.mouse_coordinates[0] += x
            app.mouse_coordinates[1] += y
        mouse_coordinates = to_pixels(app.mouse_coordinates, app.screen_size)
        return format(True, mouse_coordinates=mouse_coordinates)
    except ValueError as e:
        return format(False, str(e))
    except OSError as e:
        return format(False, repr(e))

@app.post("/mouse/down")
def mouse_down():
    if not hasattr(app, "mouse"):
        return format(False, "Mouse not initialized")

    try:
        json = flask.request.json
        button = parse_mouse_button(json)
        app.mouse.set_button(button, True)
        return format(True)
    except ValueError as e:
        return format(False, str(e))
    except OSError as e:
        return format(False, repr(e))

@app.post("/mouse/up")
def mouse_up():
    if not hasattr(app, "mouse"):
        return format(False, "Mouse not initialized")

    try:
        json = flask.request.json
        button = parse_mouse_button(json)
        app.mouse.set_button(button, False)
        return format(True)
    except ValueError as e:
        return format(False, str(e))
    except OSError as e:
        return format(False, repr(e))
