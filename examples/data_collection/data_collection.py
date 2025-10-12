import sys
import os
from os.path import dirname, abspath, join
sys.path.insert(0, abspath(join(dirname(dirname(__file__)), '..')))
from whisper_test.device import WhisperTestDevice
from whisper_test.data_collector import DataCollector

def process_ipa_files(ipa_files_path):
    device = None
    try:
        device = WhisperTestDevice(consent_mode="reject")
        collector = DataCollector(device)
        
        for ipa_file in os.listdir(ipa_files_path):
            print(f"🚀 Processing IPA file: {ipa_file}")
            try:
                collector.collect_data_by_ipa_file(join(ipa_files_path, ipa_file))
            except Exception as e:
                print(f"❌ Error processing {ipa_file}: {e}")
                # Attempt to reset device state
                if device:
                    device.stop_pcap_capture()
    finally:
        if device:
            device.close()

if __name__ == "__main__":
    ipa_files_path = "path/to/ipa_files"
    process_ipa_files(ipa_files_path)
