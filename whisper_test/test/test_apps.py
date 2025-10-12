import pytest
from os.path import join, dirname, exists
from whisper_test.device import WhisperTestDevice

class TestApps:
    """Tests for apps on the device."""

    def test_launch_apps(self, test_device: WhisperTestDevice):
        """Test whether we can launch apps."""
        if not test_device.service_provider:
            pytest.skip("Tunnel not available.")
        test_device.launch_app("com.apple.Preferences")
        test_device.launch_app("com.apple.weather")
        # TODO: check if the apps are launched

    def test_get_installed_apps(self, test_device: WhisperTestDevice):
        """Test whether we can get the list of installed apps."""
        if not test_device.service_provider:
            pytest.skip("Tunnel not available.")
        installed_apps = test_device.get_installed_apps()
        print_app_list = False
        if print_app_list:
            for k, v in installed_apps.items():
                print(k)
        assert len(installed_apps) > 0, "No apps found on the device"
        assert "com.apple.Preferences" in installed_apps
        assert "com.apple.weather" in installed_apps

    def test_install_app_via_ipa(self, test_device: WhisperTestDevice):
        """Test installation of an app via an ipa file."""
        # Ensure you have a real device connected and configured
        service_provider = test_device.service_provider
        ipa_filename = "com.adidas.app_1266591536_5.39.ipa"
        ipa_path = join(dirname(__file__), "../../ipa_files", ipa_filename)
        bundle_id = ipa_filename.split('_')[0]
        assert exists(ipa_path), "ipa file not found"

        if not service_provider:
            pytest.skip("No service provider available. Ensure a device is connected.")

        result = test_device.install_app_via_ipa(ipa_path, service_provider)
        assert result is True, "Failed to install the app on the device"
        installed_apps = test_device.get_installed_apps()
        assert bundle_id in installed_apps, "App not installed"
        test_device.uninstall_app(bundle_id)
        installed_apps = test_device.get_installed_apps()
        assert bundle_id not in installed_apps, "App not uninstalled"

    def test_vc_install_app_via_app_url(self, test_device: WhisperTestDevice):
        """Test installing an app via its App Store URL."""
        # Ensure the HTML file and app URL are set up correctly in your test environment
        html_file_name = "url 1"
        app_url_index = "1"
        app_id = "com.tarboosh.collectemall"

        result = test_device.vc_install_app_via_url_file(html_file_name, app_url_index)
        assert result == app_id, "Failed to install the app via app URL"
        installed_apps = test_device.get_installed_apps()
        assert app_id in installed_apps, "App not installed via app URL"
        assert test_device.uninstall_app(app_id) is True, "Failed to uninstall the app"
