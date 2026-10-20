Espruino Home Assistant Integration
=====================================

An integration for [Home Assistant](https://www.home-assistant.io/) that allows devices running the [Espruino JavaScript Interpreter](http://espruino.com/)
to be controlled and programmed directly from Home Assistant, from anywhere in the world!

## Prerequisites

Ensure that your Home Assistant installation has the ability to scan for bluetooth devices. We'd recommend adding a few ESP32 devices running https://esphome.io/

## Installation

**NOTE:** We're [waiting to be submitted to HACS](https://github.com/hacs/default/pull/10513) and there appears to be a long waiting list. Until submission, only `Manual Installation` will work. 

[![](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=espruino&repository=homeassistant-espruino&category=Integration)

Via [HACS](https://hacs.xyz/) or manually copy `espruino` folder from [latest release](https://github.com/espruino/homeassistant-espruino) to `custom_components` folder in your config folder.

### Manual installation

* Download the [latest release](https://github.com/espruino/homeassistant-espruino/releases) as a zip
* Extract `custom_components/espruino` from that `zip` into your Home Assistant `config` folder - eg `homeassistant/config/custom_components/espruino`
* Restart Home Assistant!

## Setup

* Install this Integration
* Go to `Settings` -> `Devices and Services`
* Click `+ Add Integration` and choose `Espruino`

You should now have any Espruino device that advertises the 0x0590 manufacturer data (eg any with up to date firmware) listed in `Settings` -> `Devices and Services` under `Discovered`

* Click `Add` next to the newly discovered device. If yours isn't listed, click on the `Espruino` integration below, then `Add device`, `Set up another instance of Espruino` and you can select from any discovered Bluetooth device. Note that for it to work, it must be connectable and have the `Nordic UART` Bluetooth Service that Espruino devices have by default.
* In `Name and assign` you can set up your device name and where in your house it is.

## Usage

Once added, each device has a text entity, for instance `text.jolt_js_c904`. If you set this to a JavaScript command, that command will be sent to the device to be executed immediately. For example if you set it to `LED.set()` the LED should get lit up.

However the main feature of the Espruino Integration is the IDE. Once installed, Home Assistant will have a new tab called `Espruino`. Click on it and you'll get the Espruino IDE. If you click the connect icon in the top left of the IDE, you'll see the usual `Web Bluetooth` connection icon, but also every device that's been added to the Espruino integration. Crucially you're connecting to these devices through Home Assistant's own Bluetooth, so you can program your devices at home from anywhere in the world.

We'd recommend that you set up your Espruino devices with BTHome (https://www.espruino.com/BTHome) as it provides a great way for them to transfer data back as entities that appear in Home Assistant. The BTHome library for Espruino will work alongside the Espruino integration as long as you leave your device as `connectable:true` in `NRF.setAdvertising`.
