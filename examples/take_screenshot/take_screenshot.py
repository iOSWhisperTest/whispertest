import asyncio
from whisper_test.device import WhisperTestDevice

async def main():
    device = WhisperTestDevice()
    await device.take_screenshot("screenshot.png")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())