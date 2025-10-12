import pytest
from whisper_test.device import WhisperTestDevice

class TestApps:
    """Tests for apps on the device."""

    @pytest.fixture
    def test_device(self):
        # Setup code for creating a test device instance
        return WhisperTestDevice()

    @pytest.mark.parametrize("screen_text_list, consent_mode, handle_native, handle_cookie, handle_apple, is_ocr, expected_command", [
        (['“ntv” Would Like to Send You Notifications', 'Notifications may include alerts, sounds and icon badges. These can be configured in Settings.', 'Don’t Allow, Button', 'Allow, Button'],
         "accept", True, False, False, False, "Allow"),
        ([["1", "Text", "We need your permission to use your data and provide", "39", "456", "1029", "48"],
          ["2", "Text", "you with a personalized experience. With your consent,", "39", "506", "1032", "48"],
          ["20", "Text", "Accept", "701", "1431", "133", "55"],
          ["21", "Text", "Reject", "917", "1435", "122", "46"]],
         "accept", False, True, True, True, "accept")
    ])
    def test_find_next_action_rule_based(self, test_device, screen_text_list, consent_mode, handle_native, handle_cookie, handle_apple, is_ocr, expected_command):
        """Test app navigation using rule-based method."""
        command, _ = test_device.find_next_action_rule_based(screen_text_list, consent_mode, handle_native, handle_cookie, handle_apple, is_ocr)
        assert command == expected_command, f"Expected command to be '{expected_command}', but got {command}"

    @pytest.mark.parametrize("screen_text_list, screen_number, screen_name, consent_mode, use_accessibility, use_ocr, expected_command", [
        (['“ntv” Would Like to Send You Notifications', 'Notifications may include alerts, sounds and icon badges. These can be configured in Settings.', 'Don’t Allow, Button', 'Allow, Button'],
         1, "Notifications", "accept", True, False, "Allow"),
        ([["1", "Text", "We need your permission to use your data and provide", "39", "456", "1029", "48"],
          ["2", "Text", "you with a personalized experience. With your consent,", "39", "506", "1032", "48"],
          ["20", "Text", "Accept", "701", "1431", "133", "55"],
          ["21", "Text", "Reject", "917", "1435", "122", "46"]],
         1, "Notifications", "accept", False, True, "Accept")
    ])
    def test_find_next_action_llm_based(self, test_device, screen_text_list, screen_number, screen_name, consent_mode, use_accessibility, use_ocr, expected_command):
        """Test app navigation using LLM-based method."""
        command = test_device.find_next_action_llm_based(screen_text_list, screen_number, screen_name, consent_mode, use_accessibility, use_ocr)
        assert command == expected_command, f"Expected command to be '{expected_command}', but got {command}"
