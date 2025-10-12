"""Screen recording tests."""

from time import sleep
from whisper_test.device import WhisperTestDevice
class TestScreenRecording:
    """Tests for screen recording."""

    def test_screen_recording(self, test_device: WhisperTestDevice):
        """Test screen recording."""
        assert test_device.start_screen_recording() is True
        sleep(5)
        assert test_device.stop_screen_recording() is True
