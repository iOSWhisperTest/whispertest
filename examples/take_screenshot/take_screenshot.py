import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

import asyncio
from whisper_test.device import WhisperTestDevice

async def main():
    device = WhisperTestDevice()
    await device.take_screenshot("screenshot.png")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())