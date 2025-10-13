# Raspberry Pi Scripts and Documentation

The Raspberry Pi functionality currently consists of two separate control methods:
USB microphone emulation, and USB mouse and keyboard emulation.
Each method allows access to the entire iOS device,
including screens that might normally be considered privileged such as Settings or the App Store.

## USB Microphone Emulation

In USB microphone emulation, the Raspberry Pi pretends to be a USB microphone
that is connected to the iOS device via a real cable.
This allows arbitrary audio to be played that is processed by the iOS device as if were real microphone input.
It is intended to be used with Voice Control as an alternative to transmitting sound over a speaker.

A guide to set up the emulated USB microphone is available in `microphone_guide.md`.
No custom code is provided since
all required software features are part of the Linux kernel and only need to be enabled.
However, the functionality is currently not integrated with the rest of the repository.

## USB Mouse and Keyboard Emulation

In USB mouse and keyboard emulation, the Raspberry Pi pretends to be a "multifunction gadget"
that is connected to the iOS device via a real cable.
The gadget is multifunction because it is simultaneously a mouse and a keyboard,
which is allowed by the USB standard and supported by iOS.
Using the emulated mouse and keyboard,
the iOS device can be controlled programmatically as if physical devices were connected.

For this control method, we provide a Python script in `mouse_keyboard.py`.
This script is meant to be run on a Raspberry Pi that is connected to the iOS device via a cable.
It starts a simple HTTP API server that allows various mouse and keyboard commands to be sent.
The intention is that the computer running the main library, connected to the same LAN as the Pi,
can send mouse and keyboard commands without the USB emulation itself having to run on that computer.
This integration is however currently not part of the repository.

Documentation for the HTTP API is available in `mouse_keyboard_api.md`.
Note that `mouse_keyboard.py` does not have a main function due to being a Flask application.
See the Flask documentation for details.
