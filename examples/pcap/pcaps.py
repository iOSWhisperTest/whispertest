"""Example of launching an app on an iOS device."""
import sys
from os.path import dirname, abspath, join
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), '..')))

from whisper_test.device import WhisperTestDevice

def main():
    device = WhisperTestDevice()
    pcap_path = "whisper_test.pcap"
    device.start_pcap_capture(pcap_path)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        device.stop_pcap_capture()
        print(f"PCAP capture saved to {pcap_path}")


if __name__ == "__main__":
    main()
