import json
from os.path import join, dirname, exists
from pymobiledevice3.lockdown import DeviceClass
from whisper_test.logger_config import setup_logger

def load_config():
    """Load configuration from config.json or use defaults."""
    config_path = join(dirname(dirname(__file__)), 'config.json')
    if exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

SUPPORTED_DEVICE_CLASSES = (DeviceClass.IPHONE, DeviceClass.IPAD)

SUPPORTED_CONNECTION_TYPES = (
    "USB",
    # "WiFi"  # WiFi support requires additional testing
)

DEFAULT_TTS_LANGUAGE = 'en'  # used by gTTS
########### TTS Models ###########
# Piper models can be downloaded here: https://github.com/rhasspy/piper/blob/master/VOICES.md

TTS_PROVIDER_GTTS = 'gTTS'
TTS_PROVIDER_PIPER_EN_US_LESSAC_MEDIUM = 'piper_en_US-lessac-medium'
TTS_PROVIDER_PIPER_EN_GB_CORI_HIGH = 'piper_en_GB-cori-high'
TTS_PROVIDER_PIPER_EN_GB_ALAN_MEDIUM = 'piper_en_GB-alan-medium'
TTS_PROVIDER_PIPER_EN_US_RYAN_HIGH = 'piper_en_US-ryan-high'
TTS_PROVIDER_PIPER_EN_US_LJSPEECH_MEDIUM = 'piper_en_US-ljspeech-medium'
TTS_PROVIDER_PIPER_EN_US_HFC_FEMALE_MEDIUM = 'piper_en_US-hfc_female-medium'
TTS_PROVIDER_PIPER_EN_US_AMY_MEDIUM = 'piper_en_US-amy-medium'

PIPER_MODELS = {
    TTS_PROVIDER_PIPER_EN_US_LESSAC_MEDIUM,  # scroll and swipe are off
    TTS_PROVIDER_PIPER_EN_GB_CORI_HIGH,
    TTS_PROVIDER_PIPER_EN_GB_ALAN_MEDIUM,
    TTS_PROVIDER_PIPER_EN_US_RYAN_HIGH,
    TTS_PROVIDER_PIPER_EN_US_LJSPEECH_MEDIUM,
    TTS_PROVIDER_PIPER_EN_US_HFC_FEMALE_MEDIUM,
    TTS_PROVIDER_PIPER_EN_US_AMY_MEDIUM,
}
########### Load configuration ###########
_config = load_config()

########### TTS root dir to store the audio files ###########
TTS_AUDIO_ROOT_DIR = _config.get('tts_audio_root_dir', join(dirname(dirname(__file__)), 'vc_cmd_audio_files'))
########### Other TTS config ###########
DEFAULT_TTS_PROVIDER = TTS_PROVIDER_PIPER_EN_US_AMY_MEDIUM
MAX_N_VOICE_CMD_TRIES = 3  # max number of tries to send a voice command

########### LLM config ###########
MODEL_NAME = _config.get('model_name', "qwen2.5:14b")

########### Timeout for app navigation ###########
TIMEOUT_FOR_APP_NAVIGATION = _config.get('timeout_app_navigation', 200)

########### Timeout for app installation ###########
TIMEOUT_FOR_APP_INSTALLATION = _config.get('timeout_app_installation', 120)

########### Timeout for app installation ###########
SLEEP_AFTER_CMD = 5
SLEEP_AFTER_LAUNCH_APP = 18
SLEEP_AFTER_CMD = 5
SYSLOG_SCAN_AFTER_VOICE_CMD = 2
SLEEP_AFTER_CUSTOM_CMD = 10
SYSLOG_MSG_VOICE_CMD_RECOGNIZED = "Recognized text is a command"

########### Custom commands ###########
CUSTOM_CMD = "continue with password"

########### Default device info keys ###########
DEFAULT_DEVICE_INFO_KEYS = [
    'ActivationState',
    'BasebandVersion',
    'BrickState',
    'BuildVersion',
    'CPUArchitecture',
    'DeviceClass',
    'DeviceColor',
    'DeviceName',
    'HardwareModel',
    'HardwarePlatform',
    'HostAttached',
    'HumanReadableProductVersionString',
    'ModelNumber',
    'PasswordProtected',
    'ProductName',
    'ProductType',
    'ProductVersion',
    'ProductionSOC',
    'ProtocolVersion',
    'TelephonyCapability',
    'TimeIntervalSince1970',
    'TimeZone',
    'TimeZoneOffsetFromUTC',
    'Uses24HourClock'
]

########### System log search strings ###########
SYSLOG_SEARCH_STRINGS = [
    'Recognized text is a command',
    'Scene lifecycle state did change: Foreground',
    'Received install progress: 1.00', # to detect the installation progress
    'Starting purchase for client', # tap get button
    'Payment sheet has presented', # to detect the payment sheet presented, detect install button
    'Starting download progress for size', # to detect if the download process started
    'Coordinator completed successfully', # to detect if the app installed
    'Application was installed at', # to detect if the app installed
    'com.apple.WebKit.GPU entered background', # to close the html file that are already opened
    'sceneID:com.apple.DocumentsApp-C96C635D-0040-4EBD-9BF3-D4B3130B9A85" = 1', # to detect if the Files app is opened
    'com.apple.WebKit.GPU: Foreground: true', # to detect if the html file is opened
    'entered background', # to detect if the app entered background
    'com.apple.AppStore.ProductPageExtension entered foreground',
    'Handling application installation', # to detect if the app installed
    ": Foreground: false" # to detect if the app is closed
]

########### Installation log search strings ###########
INSTALLATION_LOG_SEARCH_STRINGS = [
    'Received install progress: 1.00', # to detect the installation progress
    'Application was installed at', # to detect if the app installed
    'Coordinator completed successfully', # to detect if the app installed
    'Handling application installation', # to detect if the app installed
]

logger = setup_logger()

########### Rule based action mappings to interact with native dialogs ###########
RULE_BASED_ACTION_MAPPINGS = {
    "accept": {
        "Ask App Not to Track": ["Allow"],
        "Notifications may include alerts": ["Allow"],
        "Headphones, Is this Lightning adapter": ["Headphones"],
        "Turn on Location Services, Cancel": ["Allow"],
        "Location, Allow while using app": ["Allow while using app"],
        "Would Like to, Don’t Allow": ["Allow"],
        "share information about you, Cancel": ["Allow"],
        "Security": ["Ok", "Continue to Use", "Quit"],
        "Turn on Notifications, Not now": ["Not now"],
        "Tap a star to rate": ["Not now"]
    },
    "reject": {
        "Ask App Not to Track": ["Ask App Not to Track"],
        "Notifications may include alerts": ["Don’t Allow"],
        "Headphones, Is this Lightning adapter": ["Headphones"],
        "Turn on Location Services, Cancel": ["Cancel"],
        "Location, Allow while using app": ["Don’t Allow"],
        "Would Like to, Don’t Allow": ["Don’t Allow"],
        "share information about you, Cancel": ["Don’t Allow"],
        "Security": ["Ok", "Continue to Use", "Quit"],
        "Turn on Notifications, Not now": ["Not now"],
        "Tap a star to rate": ["Not now"]
    }
}

########### Element types extracted from a11y data ###########
ELEMENT_TYPES = ['Button', 'Tab', 'Header', 'Image', 'Link', 'ap_ra_pc_password_missing_alert', 'Adjustable', 'Selected', 'Toggle', 'Taste', 'Einstellungen', 'Bild', 'Einstellbar']