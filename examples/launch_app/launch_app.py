"""Example of launching an app on an iOS device."""

from whisper_test.device import WhisperTestDevice


def main():
    """Launch the Settings app."""
    device = WhisperTestDevice()
    device.launch_app("com.apple.Preferences")

# Run the main function
if __name__ == "__main__":
    main()
