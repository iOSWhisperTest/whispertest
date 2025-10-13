import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

from whisper_test.device import WhisperTestDevice


device = WhisperTestDevice()

n_entries_to_print = 100
for __ in range(n_entries_to_print):
    print(device.syslog.queue.get(timeout=2))
