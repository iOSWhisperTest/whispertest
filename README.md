# WhisperTest: A Voice-Control-based Library for iOS UI Automation
This repository contains the code for the paper titled ["WhisperTest: A Voice-Control-based Library for iOS UI Automation"](moti-et-al-whispertest-ccs-2025-expanded.pdf) ([ACM CCS 2025](https://www.sigsac.org/ccs/CCS2025/)).

<img width="805" height="395" alt="image" src="https://github.com/user-attachments/assets/3a6c4bde-7cee-487b-854c-540d2584e8dc" />

WhisperTest uses Apple's [Voice Control](https://support.apple.com/en-us/111778) accessibility feature and [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) library to interact with iOS apps and devices.

## 🌟 Features

**🗣️ Text-to-Speech + Voice Control**:
Automates app and OS interaction using Apple's native Voice Control and spoken commands.

**💻 Cross-platform**:
Runs on macOS, Linux, and Windows.

**🍏 Works on the latest iOS versions without requiring jailbreak**:
Compatible with iOS 17 and above. Jailbreaking is not necessary.

**📱 Testing of third-party apps and OS features**:
Enables automation of any iOS app without developer access or modifications. Also enables automating iOS system apps, menus and features.

**🧩 Modular and extensible architecture**:
Easily integrate new features or navigation strategies (i.e., how to interact with a given app).

**🔍 Comprehensive Data Collection**:
- 🖼️ **Screenshots:** Captured at each interaction step
- 🎥 **Screen recordings:** Full session video (MP4)
- 🌐 **Network traffic:** PCAP files for traffic and tracker analysis
- ♿ **Accessibility data:** UI tree dumps and element metadata
- 🔤 **OCR output:** Extracted on-screen text and icons (via OmniParser)

## 📋 Prerequisites

### iOS Device Setup

> [!WARNING]
> For security reasons we strongly recommend using a test phone rather than your personal device with sensitive data, apps and settings. See the Safety and Security section of [our paper](moti-et-al-whispertest-ccs-2025-expanded.pdf) for potential risks.

1. **Enable Voice Control**:
   - Go to Settings → Accessibility → Voice Control
   - Toggle on Voice Control

2. **Enable Developer Mode** (Perform developer operations (Requires enable of Developer-Mode)):
   - Settings → Privacy & Security → Developer Mode

3. **Trust Computer**:
   - Connect device via USB
   - Tap "Trust" when prompted on device

4. **Start Remote Service Tunnel** (iOS 17.4+):
   ```bash
   # Start the tunneld service (keeps running in background)
   sudo -E pymobiledevice3 remote tunneld

   # Or use the provided helper script
   ./whisper_test/scripts/start_tunnel.sh
   ```

> **Note**: The `tunneld` service must be running for the framework to communicate with your device. Run it in a separate terminal window or as a background process.

### 🔌 External Services

- **Omniparser OCR Service**:
  WhisperTest integrates with a REST-based version of [OmniParser](https://github.com/zahra7394/OmniParser) — a FastAPI service that performs OCR and visual element detection on screenshots.
  The service can run locally or remotely and returns structured detection results and a labeled image.

  **Quick start:**
  ```bash
  git clone https://github.com/zahra7394/OmniParser.git
  cd OmniParser
  pip install -r requirements.txt
  python app.py
  ```
  The API will start at http://localhost:5000/process.
  WhisperTest connects automatically if omniparser_api_url in config.json is set to this endpoint.

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/whispertest.git
cd whispertest
```

### 2. Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install System Dependencies

#### Piper TTS (Recommended for better voice quality)

```bash
# Download from releases: https://github.com/rhasspy/piper/releases
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
tar -xvf piper_amd64.tar.gz
sudo mv piper /usr/local/bin/
```

**Download Voice Models**:
1. Visit [Piper Voices](https://github.com/rhasspy/piper/blob/master/VOICES.md)
2. Download desired models (e.g., `en_US-amy-medium`)
3. Place `.onnx` and `.onnx.json` files in the `piper/` directory

#### NLTK Data

```bash
python -m nltk.downloader punkt stopwords wordnet
```

### 4. Verify Installation

```bash
# Check if pymobiledevice3 can see your device
pymobiledevice3 usbmux list

# Should show your connected iOS device
```

### 5. Configure the Framework

Create a `config.json` file in the root directory to customize settings:

```json
{
  "media_path": "media_output",
  "tts_provider": "piper_en_US-amy-medium",
  "piper_root_dir": "piper",
  "consent_mode": "accept",
  "timeout_app_navigation": 200,
  "timeout_app_installation": 120,
  "omniparser_api_url": "api_url",
  "llm_api_url": "api_url"
}
```

**Configuration Options**:
- `media_path`: Directory to save screenshots, videos, and data
- `tts_provider`: TTS engine (`piper_en_US-amy-medium` or `gTTS`)
- `piper_root_dir`: Directory containing Piper voice models
- `consent_mode`: How to handle dialogs (`accept` or `reject`)
- `timeout_app_navigation`: Maximum time (seconds) for app navigation
- `omniparser_api_url`: URL for OmniParser OCR service (optional)
- `llm_api_url`: URL for LLM-based navigation service (optional)

## 📖 Usage

### Quick Start Example

```python
from whisper_test.device import WhisperTestDevice

# Initialize device connection
device = WhisperTestDevice()

# Optinalli install an app from IPA file
device.install_app_via_ipa("path/to/app.ipa")

# Launch the app
app_bundle_id = "com.example.myapp"
device.launch_app(app_bundle_id)

# Take a screenshot and get screen content
screenshot, _ = device.take_screenshots(app_bundle_id)
a11y_data = device.get_screen_content_by_a11y()

# Issue voice commands
device.say("Tap Continue")
device.say("Scroll down")

# Clean up
device.uninstall_app(app_bundle_id)
device.close()
```


## 🏗️ Architecture

### Core Components

- **`device.py`**: Main device interface and control
- **`navigation.py`**: App navigation
- **`tts.py`**: Text-to-speech controller with multi-provider support
- **`data_collector.py`**: Automated data collection
- **`rule_based_app_navigation.py`**: Rule-based dialog and permission handling
- **`llm_based_app_navigation.py`**: LLM-powered intelligent navigation
- **`ocr_utils.py`**: OCR and visual element detection (OmniParser integration)
- **`a11y_utils.py`**: Accessibility and UI element extraction
- **`app_utils.py`**: App installation, launch, and management
- **`syslog_monitor.py`**: Real-time system log monitoring
- **`utils.py`**: General utility functions
- **`common.py`**: Configuration management and shared constants
- **`exceptions.py`**: Custom exception classes
- **`logger_config.py`**: Logging configuration

### Directory Structure

```
whispertest/
├── examples/                   # Example scripts
│   ├── data_collection/        # Data collection
│   ├── get_installed_apps/     # List installed apps
│   ├── launch_app/             # App launching
│   ├── pcap/                   # Network capture
│   ├── syslog/                 # Log monitoring
│   ├── take_screenshot/        # Screenshot examples
│   └── web_automation/         # Web crawling
├── whisper_test/               # Main library
│   ├── test/                   # Test suite
│   └── scripts/                # Helper scripts
├── raspberry_pi/               # Scripts and docs for the Pi
├── requirements.txt
└── README.md
```

### USB microphone and mouse/keyboard emulation

The `raspberry_pi/` directory contains scripts and documentation to enable USB microphone emulation and USB mouse and keyboard emulation by connecting a Raspberry Pi to the iOS device. This functionality is currently not integrated with the rest of the repository. See `raspberry_pi/README.md` for more details.

## 🔧 Configuration

### TTS Providers

- **Piper** (Recommended): Offline, high-quality voices
- **gTTS**: Online, requires internet connection and may be rate-limited (use at your own risk)

Configure in `config.json`:

```json
{
  "tts_provider": "piper_en_US-amy-medium",
  "piper_root_dir": "piper"
}
```

### Consent Mode
Control how the library handles permission dialogs:

- `"accept"`: Accept all permissions (cookies, tracking, location, etc.)
- `"reject"`: Reject all permissions

### LLM Configuration
TBD

## 📊 Data Collection

WhisperTest automatically collects comprehensive data during app navigation:

- **Screenshots**: PNG images at each navigation step
- **Accessibility Data**: UI and screen element information
- **OCR Results**: Text and element positions from screens
- **Videos**: Screen recordings of entire app sessions
- **Network Traffic**: PCAP files of network activity

Output structure (one app generates multiple files at each navigation step):

```
media_output/
├── com.example.app_20240101_120000.png
├── com.example.app_ocr_20240101_120000.json
├── com.example.app_a11y_20240101_120000.txt
├── com.example.app_20240101_120030.png
├── com.example.app_ocr_20240101_120030.json
├── com.example.app_a11y_20240101_120030.txt
├── ...
├── com.example.app_20240101_120000.pcap    # One per session
└── com.example.app_20240101_120000.mp4     # One per session

```

## 🧪 Testing

Run the test suite:

```bash
pytest -sv whisper_test/test/
```

## 🐛 Troubleshooting

**Problem**: `Cannot connect to device` or `No devices found`

**Solutions**:
1. Check physical connection:
   ```bash
   pymobiledevice3 usbmux list
   ```
2. Ensure tunneld is running (iOS 17+):
   ```bash
   sudo -E pymobiledevice3 remote tunneld
   ```
3. Verify device trust:
   - Disconnect and reconnect USB cable
   - Look for "Trust This Computer?" prompt on device
   - Enter device passcode


**Problem**: Voice commands not working or being ignored

**Solutions**:
1. Verify Voice Control is active
2. Test audio playback
3. Check TTS configuration
4. Adjust device volume
5. Try alternative TTS provider


## 📝 Reference

```bibtex
@inproceedings{moti_whispertest_25,
 author = {Moti, Zahra and Janssen-Groesbeek, Tom and Monteiro, Steven and Continella, Andrea and Acar, Gunes},
 booktitle = {Proceedings of the ACM Conference on Computer and Communications Security (CCS)},
 month = {October},
 title = {WhisperTest: A Voice-Control-based Library for iOS UI Automation},
 year = {2025}
}

```

## 🤝 Contributing

We welcome contributions! Whether it's bug fixes, new features, documentation improvements, your help is appreciated.

## 🙏 Acknowledgments

- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - The foundation of this library.

- **[Piper](https://github.com/rhasspy/piper)** - High-quality neural text-to-speech engine that enables natural voice commands with minimal latency.

- **[OmniParser](https://github.com/microsoft/OmniParser)** - Advanced OCR and UI element detection.

### Contact

For any questions, suggestions, or issues regarding this project or our paper, please contact:

| **Author**         | **Email**                     |
|--------------------|-------------------------------|
| [Zahra Moti](https://www.ru.nl/en/people/moti-jeshveghani-z)      | zahra.moti@ru.nl   |
| [Tom Janssen-Groesbeek](https://tomjanssengroesbeek.nl/)    | tom.janssen-groesbeek@ru.nl   |
| Steven Monteiro   | s.c.monteiro@student.utwente.nl   |
| [Gunes Acar](https://gunesacar.net/)     | g.acar@cs.ru.nl   |
| [Andrea Continella](https://conand.me/) | a.continella@utwente.nl |





