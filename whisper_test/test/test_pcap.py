"""Tests for pcap capture on the device."""
from tempfile import NamedTemporaryFile

from time import sleep
from os.path import isfile, getsize
from pymobiledevice3.lockdown import create_using_usbmux

from whisper_test.device import WhisperTestDevice


RM_TMP_PCAP_FILE = True
CREATE_TRAFFIC_VIA_LOCKDOWN = False
PCAP_CAP_DURATION = 0.5  # in seconds
PCAP_PREAMBLE_SIZE = 140  # pcaps with no packets have this size
EXPECTED_PCAP_STRS = [  # strings in the pcap file preamble
    "artificial", "pymobiledevice3", "iOS Packet Capture"]

class TestPcapCapture:
    """Tests for pcap capture on the device."""

    def test_pcap(self, test_device: WhisperTestDevice):
        """Run pcap capture on the device and check the pcap file."""


        with NamedTemporaryFile(
                suffix='.pcap', delete=RM_TMP_PCAP_FILE) as pcap_file:
            pcap_file_path = pcap_file.name
            dev = test_device

            # start pcap capture
            dev.start_pcap_capture(pcap_file_path)

            if CREATE_TRAFFIC_VIA_LOCKDOWN:
                # this creates some traffic on the device so the pcap is not empty
                # tests pass even if this is not done
                _lockdown = create_using_usbmux()
                _lockdown.close()

            sleep(PCAP_CAP_DURATION)
            dev.stop_pcap_capture()

            assert isfile(pcap_file_path), f"PCAP file {pcap_file_path} not found"
            assert getsize(pcap_file_path) > 0, f"PCAP file {pcap_file_path} is empty"

            preamble = pcap_file.read(PCAP_PREAMBLE_SIZE)
            for s in EXPECTED_PCAP_STRS:
                assert s.encode() in preamble, \
                    f"Expected string {s} not found in PCAP file {pcap_file_path}"

        # TODO: consider parsing the pcap with scapy and checking the contents
        if RM_TMP_PCAP_FILE:
            assert not isfile(pcap_file_path),\
                f"PCAP file {pcap_file_path} not deleted"
