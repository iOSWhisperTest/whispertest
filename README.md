# WhisperTest: A Voice-Control-based Library for iOS UI Automation

This repository contains the code for the paper titled ["WhisperTest: A Voice-Control-based Library for iOS UI Automation"](moti-et-al-whispertest-ccs-2025-expanded.pdf) ([ACM CCS 2025](https://www.sigsac.org/ccs/CCS2025/)).

<img width="805" height="395" alt="image" src="https://github.com/user-attachments/assets/3a6c4bde-7cee-487b-854c-540d2584e8dc" />

WhisperTest uses Apple's [Voice Control](https://support.apple.com/en-us/111778) accessibility feature and [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) library to interact with iOS apps and devices.

## 🌟 Features

- **Text-to-Speech + Voice Control**:
Automates app and OS interaction using Apple's native Voice Control and spoken commands.
- **Cross-platform**:
Runs on macOS, Linux, and Windows.
- **Works on the latest iOS versions without requiring jailbreak**:
Compatible with iOS 17 and above. Jailbreaking is not necessary.
- **Testing of third-party apps and OS features**:
Enables automation of any iOS app without developer access or modifications. Also enables automating iOS system apps, menus and features.
- **Modular and extensible architecture**:
Easily integrate new features or navigation strategies (i.e., how to interact with a given app).
-**Comprehensive Data Collection**:

   - **Screenshots:** Captured at each interaction step
   - **Screen recordings:** Full session video (MP4)
   - **Network traffic:** PCAP files for traffic and tracker analysis
   - **Accessibility data:** UI tree dumps and element metadata
   - **OCR output:** Extracted on-screen text and icons (via OmniParser)

## 🎥 Demo

https://github.com/user-attachments/assets/7d0d6bf4-4f18-487a-8352-f10e818ae2e8

## 📋 Prerequisites

### iOS Device Setup

> [!WARNING]
> For security reasons we strongly recommend using a test phone rather than your personal device with sensitive data, apps and settings. See the Safety and Security section of [our paper](moti-et-al-whispertest-ccs-2025-expanded.pdf) for potential risks.

1. **Enable Voice Control**:

   - Go to Settings → Accessibility → Voice Control
   - Toggle on Voice Control

2. **Enable Developer Mode** (Required for most library functions):

   - Settings → Privacy & Security → Developer Mode

3. **Trust Computer**:

   - Connect device via USB
   - Tap "Trust" when prompted on the device

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/iOSWhisperTest/whispertest.git
cd whispertest
```

### 2. Install Python Dependencies

> **Requires Python 3.10 or higher.** pymobiledevice3 and several other dependencies no longer support Python 3.9.

```bash
# Create a virtual environment (recommended)
python3.13 -m venv venv          # or python3.12, python3.11, python3.10
source venv/bin/activate          # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install System Dependencies

#### Piper TTS (Recommended for better voice quality)

WhisperTest uses [Piper](https://github.com/rhasspy/piper) for local text-to-speech. The default voice model is `en_US-amy-medium`. You can install Piper via pip or as a standalone binary.

**Option A: Install via pip**

```bash
pip install piper-tts
```

This installs the `piper` command into your virtual environment. Verify with `piper --version`.

**Option B: Install from binary release**

Download the correct binary for your platform from [Piper releases](https://github.com/rhasspy/piper/releases/tag/2023.11.14-2) and place it in `~/piper/`:

```bash
mkdir -p ~/piper

# macOS (Apple Silicon / Intel — use the aarch64 or amd64 build respectively)
# Linux — use the amd64 or armv7 build
# Extract the downloaded archive and move the piper binary into ~/piper/
```

**Download a voice model:**

Each model requires an `.onnx` file and its `.onnx.json` config. The default model is `en_US-amy-medium`:

```bash
# Download the default model into ~/piper/
cd ~/piper
curl -OL "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx"
curl -OL "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
```

Browse all available voices at [Piper Voices](https://github.com/rhasspy/piper/blob/master/VOICES.md) or on [Hugging Face](https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0).

> **Tip**: You can change the model directory by setting `piper_root_dir` in `config.json`. The default is `~/piper/`.

#### NLTK Data

```bash
python -m nltk.downloader punkt stopwords wordnet punkt_tab
```

### 4. macOS Audio Playback (macOS only)

The `playsound` library requires PyObjC to play audio on macOS:

```bash
pip install pyobjc-framework-Cocoa
```

> **Note**: This is only needed on macOS. Linux users can skip this step.

### 5. Verify Installation

```bash
# Check if pymobiledevice3 can see your device
pymobiledevice3 usbmux list

# Should show your connected iOS device
```

## 🔗 Device Connection Setup

After installing, connect pymobiledevice3 to your iOS device. The steps depend on your iOS version.

### Mount Developer Disk Image (iOS < 17.0)

For iOS 14, 15, and 16 devices, developer features (screenshots, accessibility audit, process management) require mounting the DeveloperDiskImage. No tunnel is needed.

```bash
pymobiledevice3 mounter auto-mount
```

> **Note**: This step is not needed for iOS 17.0+, where developer services are accessed through a tunnel instead.

### Start Remote Service Tunnel (iOS 17.0+)

Starting at iOS 17.0, Apple requires a tunnel for developer services. The `tunneld` daemon automatically detects connected devices and uses the best available connection method.

```bash
# Start the tunneld service (keeps running in background)
sudo -E pymobiledevice3 remote tunneld

# Or use the provided helper script
./whisper_test/scripts/start_tunnel.sh
```
**Alternative: `lockdown start-tunnel`** (iOS 17.4+)

If `remote tunneld` is unavailable (e.g. dependency issues on older Python), you can use the lockdown-based tunnel instead:

```bash
sudo pymobiledevice3 lockdown start-tunnel
```

This prints an RSD address and port. Pass them to the framework via environment variables or `config.json`:

```bash
# Environment variables (update address/port from the command output)
export RSD_ADDRESS=""
export RSD_PORT=""
```

Or set `rsd_address` and `rsd_port` in `config.json`. The framework tries `tunneld` first, then falls back to a direct RSD connection.

> **Note**: The `tunneld` service must be running for the framework to communicate with iOS 17+ devices. Run it in a separate terminal window or as a background process. For iOS < 17.0, the framework communicates directly via USB (lockdown) and no tunnel is needed.

## 🔌 External Services

WhisperTest can be extended with external services for OCR and LLM-based navigation. These are **not required** for the core functionality (screenshots, accessibility, voice commands).

### OmniParser OCR Service (grid method)

WhisperTest integrates with a REST-based version of [OmniParser](https://github.com/zahra7394/OmniParser) — a FastAPI service that performs OCR and visual element detection on screenshots. The service can run locally or remotely and returns structured detection results and a labeled image.

```bash
git clone https://github.com/zahra7394/OmniParser.git
cd OmniParser
pip install -r requirements.txt
python app.py
```

The API will start at http://localhost:5003/process.
Set `omniparser_api_url` in `config.json` to connect WhisperTest to this endpoint.

### LLM-based Navigation Service

WhisperTest can use local or remote Large Language Models (LLMs) for navigation decisions via the companion package [`wtmi`](https://github.com/iOSWhisperTest/whispertest-model-interface) (WhisperTest Model Interface), which:

- Receives **accessibility (A11Y) data**, **OCR detections**, or **screenshots** from the iOS app under test.
- Formats this data into structured prompts for an LLM (through a REST API endpoint).
- Optionally performs a **consent-dialog classification** pass (accept/reject).
- Returns a single **next action** (e.g. _Tap_, _Type_) that WhisperTest can execute on the device.

```bash
git clone https://github.com/iOSWhisperTest/whispertest-model-interface.git
cd whispertest-model-interface
pip install -r requirements.txt
pip install -e .
```

The package expects an LLM REST server with endpoints like `http://<server-ip>:5000/query_ollama` or `http://<server-ip>:5000/query_transformers`. An example Flask-based REST API can be found [here](https://github.com/iOSWhisperTest/llm-rest-api).


## ⚙️ Configuration

### Configure the Framework

Create a `config.json` file in the root directory to customize settings:

```json
{
  "media_path": "media_output",
  "tts_provider": "piper_en_US-amy-medium",
  "tts_audio_root_dir": "vc_cmd_audio_files",
  "piper_root_dir": "~/piper",
  "consent_mode": "accept",
  "model_name": "qwen2.5:14b",
  "timeout_app_navigation": 200,
  "timeout_app_installation": 120,
  "omniparser_api_url": "http://0.0.0.0:5003/process",
  "processed_apps_path": "processed_appIDs.txt",
  "failed_apps_path": "failed_appIDs.txt",
  "rsd_address": "",
  "rsd_port": ""
}
```

**Configuration Options**:

| Key | Default | Description |
|---|---|---|
| `media_path` | `"media_output"` | Directory for screenshots, videos, and collected data |
| `tts_provider` | `"piper_en_US-amy-medium"` | TTS engine to use (see available [Piper models](#piper-tts-recommended-for-better-voice-quality) or `"gTTS"`) |
| `tts_audio_root_dir` | `"vc_cmd_audio_files"` | Directory for cached TTS audio files |
| `piper_root_dir` | `"~/piper"` | Directory containing the Piper binary and voice models |
| `consent_mode` | `"accept"` | How to handle permission/cookie dialogs (`"accept"` or `"reject"`) |
| `model_name` | `"qwen2.5:14b"` | LLM model name for navigation decisions (used by [wtmi](https://github.com/iOSWhisperTest/whispertest-model-interface)) |
| `timeout_app_navigation` | `200` | Maximum time in seconds for navigating a single app |
| `timeout_app_installation` | `120` | Maximum time in seconds for installing an app |
| `omniparser_api_url` | `"http://0.0.0.0:5003/process"` | URL for the OmniParser OCR service |
| `processed_apps_path` | `"processed_appIDs.txt"` | File tracking successfully processed apps |
| `failed_apps_path` | `"failed_appIDs.txt"` | File tracking failed apps |
| `rsd_address` | `""` | RSD tunnel address (from `lockdown start-tunnel` output, used when `tunneld` is unavailable) |
| `rsd_port` | `""` | RSD tunnel port (from `lockdown start-tunnel` output) |

## 📖 Usage

### Quick Start Example

```python
from whisper_test.device import WhisperTestDevice

# Connect to device
device = WhisperTestDevice()
print(f"Connected to {device.device_name} (iOS {device.product_version})")

# Take a screenshot
device.take_screenshot("screenshot.png")

# Read screen via accessibility
a11y_data = device.get_screen_content_by_a11y(max_items=5)
for item in a11y_data:
    print(item)

# Issue voice commands via TTS (Voice Control must be ON)
device.tts.say("Open Safari", verify=False)   # play without syslog check
device.tts.say("Go Home")                      # play and verify via syslog

# Install, launch, and clean up an app
device.install_app_via_ipa("path/to/app.ipa")
device.launch_app("com.example.myapp")
device.uninstall_app("com.example.myapp")

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

The `raspberry_pi/` directory contains scripts and documentation to enable USB microphone emulation
and USB mouse and keyboard emulation by connecting a Raspberry Pi to the iOS device,
as described in sections 3.1.5 and 3.1.6 of our paper.
This functionality is experimental and is currently not integrated with the rest of the repository.
See `raspberry_pi/README.md` for more details.

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

**Problem**: `No module named 'AppKit'` when playing audio (macOS)

**Solution**: Install PyObjC:
```bash
pip install pyobjc-framework-Cocoa
```

**Problem**: Accessibility scan hangs or `move_focus_next` blocks indefinitely

**Solution**: This is a bug in pymobiledevice3 **7.7.0 – 7.8.x** where `move_focus_next()` blocks forever after the last focusable element (instead of wrapping around). Versions **≤ 7.6.0** and **≥ 8.0.0** are not affected.
If you're on an affected version, install the pinned safe version:
```bash
pip install pymobiledevice3==7.6.0
```
> **Note**: Version 8.x rewrites the entire API to async and is not yet compatible with this project.

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

We welcome contributions! Whether it's bug fixes, new features, or documentation improvements, your help is appreciated.

## 🙏 Acknowledgments

- **[pymobiledevice3](https://github.com/doronz88/pymobiledevice3)** - The foundation of this library.

- **[Piper](https://github.com/rhasspy/piper)** - High-quality neural text-to-speech engine that enables natural voice commands with minimal latency.

- **[OmniParser](https://github.com/microsoft/OmniParser)** - Advanced OCR and UI element detection.

### Contact

For any questions, suggestions, or issues regarding this project or our paper, please contact:

| **Author**                                                   | **Email**                       |
| ------------------------------------------------------------ | ------------------------------- |
| [Zahra Moti](https://www.ru.nl/en/people/moti-jeshveghani-z) | zahra.moti@ru.nl                |
| [Tom Janssen-Groesbeek](https://tomjanssengroesbeek.nl/)     | tom.janssen-groesbeek@ru.nl     |
| Steven Monteiro                                              | s.c.monteiro@student.utwente.nl |
| [Gunes Acar](https://gunesacar.net/)                         | g.acar@cs.ru.nl                 |
| [Andrea Continella](https://conand.me/)                      | a.continella@utwente.nl         |
