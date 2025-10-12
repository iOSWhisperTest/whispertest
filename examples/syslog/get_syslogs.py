import sys
from os.path import dirname, abspath, join
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), '..')))

from whisper_test.device import WhisperTestDevice


device = WhisperTestDevice()

n_entries_to_print = 100
for __ in range(n_entries_to_print):
    print(device.syslog.queue.get(timeout=2))
