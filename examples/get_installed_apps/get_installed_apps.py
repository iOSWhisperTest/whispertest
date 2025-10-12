import sys
from os.path import dirname, abspath, join
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), '..')))

from whisper_test.device import WhisperTestDevice


device = WhisperTestDevice()
print(device.get_list_installed_apps())
