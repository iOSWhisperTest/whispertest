"""Voice command tests."""

from time import sleep
from whisper_test.device import WhisperTestDevice
class TestVoiceCommand:
    """Tests for sending voice commands."""

    def test_voice_command(self, test_device: WhisperTestDevice):
        """Test sending a basic voice command."""
        assert test_device.tts.say("Go, Home"), "Voice command failed"
        assert test_device.tts.say("Open, Settings"), "Voice command failed"
        assert test_device.tts.say("Go, Home"), "Voice command failed"

    def test_say_swipe(self, test_device: WhisperTestDevice):
        """Test sending a tap voice command."""
        for direction in ("left", "right", "up", "down"):
            assert test_device.tts.say_swipe(direction)  # move this to a class
            sleep(1)

    def test_say_scroll(self, test_device: WhisperTestDevice):
        """Test sending a tap voice command."""
        for direction in ("left", "right", "up", "down"):
            assert test_device.tts.say_scroll(direction)
            sleep(1)

    def test_say_scroll_without_verify(self, test_device: WhisperTestDevice):
        """Test sending a tap voice command."""
        for direction in ("left", "right", "up", "down"):
            assert test_device.tts.say_scroll(direction, verify=False)

    def test_say_tap_item(self, test_device: WhisperTestDevice):
        """Test sending a tap voice command."""
        assert test_device.tts.say_tap("1")
