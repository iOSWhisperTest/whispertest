"""Test device module."""
from tempfile import NamedTemporaryFile
from os.path import isfile, getsize
from queue import Empty
from time import time

import pytest

from whisper_test.device import WhisperTestDevice
from whisper_test.common import SUPPORTED_DEVICE_CLASSES, SUPPORTED_CONNECTION_TYPES


N_SYSLOG_MESSAGES = 5
PRINT_SYSLOG_MESSAGES = False


class TestWhisperDevice:

    def test_syslog(self, test_device: WhisperTestDevice):
        """Make sure we can read syslog messages."""
        dev = test_device
        assert dev.syslog is not None
        assert dev.syslog.queue is not None
        for __ in range(N_SYSLOG_MESSAGES):
            try:
                msg = dev.syslog.queue.get(timeout=5)
                if PRINT_SYSLOG_MESSAGES:
                    print("Syslog", msg)
            except Empty:
                pytest.fail("Not enough syslog messages received.")
                break

    def test_screenshot(self, test_device: WhisperTestDevice):
        """Test taking a screenshot."""
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

    def test_device_properties(self, test_device: WhisperTestDevice):
        """Test device properties."""
        dev = test_device
        assert dev.lockdown is not None, "Device is not connected."

        assert dev.paired, "Device is not paired."
        assert dev.connection_type in SUPPORTED_CONNECTION_TYPES,\
            "Device connection type not supported."

        assert dev.device_name, "Device name is empty."
        assert dev.device_class in SUPPORTED_DEVICE_CLASSES,\
            f"Device class {dev.device_class} is not supported."
        assert dev.display_name, "Device display name is empty."
        assert dev.hardware_model, "Device hardware model is empty."

        assert dev.major_os_version>= 13, f"OS {dev.major_os_version} is not supported."
        product_version = dev.product_version
        major_version = int(product_version.split('.')[0])
        assert major_version == dev.major_os_version,\
            f"Major OS versions does not match {major_version} != {dev.major_os_version}."
        assert dev.details, "Device info is empty."
        assert dev.details['TrustedHostAttached'], "Trusted host is not attached."
        assert dev.a11y_features, "Assistive touch is not enabled."
        assert 'VoiceOverTouchEnabledByiTunes' in dev.a11y_features
        print_device_info = True
        if print_device_info:
            print("Device name:", dev.device_name)
            print("Device class:", dev.device_class)
            print("Display name:", dev.display_name)
            print("Major OS version:", dev.major_os_version)
            print("a11y_features keys", dev.a11y_features.keys())
