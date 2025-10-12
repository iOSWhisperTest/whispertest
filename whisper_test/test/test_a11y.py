"""Accessibility tests."""
from whisper_test.device import WhisperTestDevice

class TestA11y:
    """Tests for accessibility-based scraping."""

    def test_a11y(self, test_device: WhisperTestDevice):
        """Test getting screen items using a11y audits."""
        dev = test_device
        dev.tts.say("Go home")
        a11y_items = dev.a11y.get_ax_list_items()
        print(a11y_items)
        assert len(a11y_items) > 0, "Accessibility items not found"
        a11y_items = dev.a11y.get_ax_list_items()
        print(a11y_items)
        assert len(a11y_items) > 0, "Accessibility items not found"

    def test_a11y_2(self, test_device: WhisperTestDevice):
        """Test getting screen items using a11y audits."""
        dev = test_device
        # TODO: launch an app with known items without TTS
        dev.tts.say("Go home")
        a11y_items = dev.a11y.get_ax_list_items2()
        print(a11y_items)
        assert len(a11y_items) > 0, "Accessibility items not found"
        a11y_items = dev.a11y.get_ax_list_items2()
        print(a11y_items)
        assert len(a11y_items) > 0, "Accessibility items not found"

    def test_a11y_features(self, test_device: WhisperTestDevice):
        """Test getting screen items using a11y audits."""
        assert len(
            test_device.a11y_features) > 0, "Accessibility features not found"
