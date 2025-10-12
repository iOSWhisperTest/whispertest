"""Test device module."""
from tempfile import NamedTemporaryFile
from os.path import isfile, getsize
from time import time

import pytest

from whisper_test.device import WhisperTestDevice


class TestWhisperDevice:

    def test_ocr(self, test_device: WhisperTestDevice):
        """Test OCR by taking a screenshot and OCRing it."""
        dev = test_device

        if not dev.service_provider:
            pytest.skip("Tunnel not available.")

        with NamedTemporaryFile(
                suffix='.png', delete=False) as png_file:
            png_path = png_file.name
            t0 = time()
            dev.take_screenshot(png_path)
            print(f"Time taken to take screenshot: {time() - t0}")
            assert isfile(png_path), "Screenshot file not found"
            assert getsize(png_path) > 0, f"Screenshot file {png_path} is empty"

            ocr_results = dev.get_screen_content_by_ocr(png_path, ocr_service="omniparser")
            assert ocr_results is not None, "OCR results are None"
            assert len(ocr_results) > 0, "OCR results are empty"

            ocr_results = dev.get_screen_content_by_ocr(png_path, ocr_service="ez_ocr")
            assert ocr_results is not None, "OCR results are None"
            assert len(ocr_results) > 0, "OCR results are empty"
