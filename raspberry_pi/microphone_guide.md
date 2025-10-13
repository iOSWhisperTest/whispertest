# Emulating a USB microphone for iOS using a Raspberry Pi

This guide shows how to use a Raspberry Pi to emulate a USB microphone
and connect it to an iOS device to allow arbitrary audio files to be sent as microphone input.
In our use case, this setup is used to activate Voice Control,
but it can be used in any situation where microphone input is necessary on iOS.

The main advantages of this method are:
* No jailbreak or developer mode required
* No loss of audio quality
* Does not depend on app-specific support

## Hardware requirements

* iOS device with a Lightning port. USB-C is untested.
* Apple Lightning to USB 3 Camera Adapter / A1619 / MK0W2AM/A / MK0W2ZM/A.
  This adapter might seem redundant but is in fact required.
  * We recommend the original adapter from Apple to avoid compatibility issues.
* Raspberry Pi 4, Raspberry Pi 5, or any model of Raspberry Pi Zero. Raspberry Pi 1/2/3 *do not work*.
  * Specifically, the device must support USB OTG or Device Mode.
    The majority of desktop and laptop USB ports do not, but other embedded boards might work.
* Only if your Raspberry Pi is a full-size model (credit card format): An externally powered USB hub
  that can be connected to the host device via USB-A, i.e. *not* a model with a non-detachable USB-C cable.

## Setting up

### Hardware setup

> [!IMPORTANT]
> Read this section carefully, the cables can be somewhat confusing.

1. Use the male Lightning connector of the A1619 adapter to connect it your iOS device.
   If you are plugging it in for the first time, you may be prompted for a firmware update.
<!-->
2. If your Pi is a full-size model:
   1. Connect the power port of the USB hub to a power source as you normally would.
   2. Connect the USB-A port of the A1619 adapter to the host side of the USB hub.
   3. Connect the USB-C power port of the Pi to one of the device ports on the USB hub.
<!-->
2. If your Pi is a Zero model:
   1. Connect the USB-Micro-B power port to a power source as you normally would.
   2. Connect the USB-Micro-B OTG port to the USB-A port of the A1619 adapter.
<!-->
3. Optional: Connect the female Lightning port of the A1619 adapter to a power source to charge the iOS device.
   The iOS device cannot be charged through the USB-A port even when connected to a powered USB hub.

### Software setup

1. Install Raspberry Pi OS onto your Pi. This tutorial was tested with Bookworm (Debian 12).
2. Enable the DWC2 Device Tree overlay:\
   `echo dtoverlay=dwc2 | sudo tee -a /boot/firmware/config.txt`
3. Enable the DWC2 kernel module on boot:\
   `echo dwc2 | sudo tee -a /etc/modules`
4. Enable the Audio Gadget kernel module on boot:\
   `echo g_audio | sudo tee -a /etc/modules`
5. Reboot the Pi. If the hardware setup described above is already in place,
   the iOS device should automatically detect the microphone when the Pi boots.

## Testing

If the Audio Gadget has been initialized successfully,
it should show up as `UAC2Gadget` in the list of audio PCMs, possibly multiple times:
```
$ aplay -L | grep UAC2Gadget
hw:CARD=UAC2Gadget,DEV=0
plughw:CARD=UAC2Gadget,DEV=0
default:CARD=UAC2Gadget
sysdefault:CARD=UAC2Gadget
dmix:CARD=UAC2Gadget,DEV=0
usbstream:CARD=UAC2Gadget
```
These identifiers can also be used to select the Audio Gadget if it is not the default playback device.

To test the setup,
you can use the Voice Memos app on the iOS device to record from the microphone while playing a sample file on the Pi:
```
aplay -D plughw:CARD=UAC2Gadget,DEV=0 sample.wav
```
If you get white noise, make sure that the file you're trying to play is actually `.wav`.
