import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

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
