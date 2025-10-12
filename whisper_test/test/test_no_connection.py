"""Test device module."""
import unittest
from whisper_test.device import WhisperTestDevice


class WhisperDeviceNotConnected(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.device = WhisperTestDevice(connect_to_device=False)

    @classmethod
    def tearDownClass(cls):
        if cls.device:
            cls.device.close()

    def test_device_properties(self):
        """Make sure the connection and syslog is None."""
        assert self.device.lockdown is None
        assert self.device.syslog is None

    def test_voice_command(self):
        """Make sure sending voice commands works without connection."""
        assert self.device.tts.say("Go, Home", verify=False)
