import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

from whisper_test.device import WhisperTestDevice


device = WhisperTestDevice()
print(device.get_list_installed_apps())
