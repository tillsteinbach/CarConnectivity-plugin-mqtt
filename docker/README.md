# CarConnectivity-MQTT
[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/latest)
[![GitHub](https://img.shields.io/github/license/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/issues)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/carconnectivity-mqtt?label=PyPI%20Downloads)](https://pypi.org/project/carconnectivity-plugin-mqtt/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/carconnectivity-plugin-mqtt)](https://pypi.org/project/carconnectivity-plugin-mqtt/)
[![Docker Image Size (latest semver)](https://img.shields.io/docker/image-size/tillsteinbach/carconnectivity-mqtt?sort=semver)](https://hub.docker.com/r/tillsteinbach/carconnectivity-mqtt)
[![Docker Pulls](https://img.shields.io/docker/pulls/tillsteinbach/carconnectivity-mqtt)](https://hub.docker.com/r/tillsteinbach/carconnectivity-mqtt)
[![Donate at PayPal](https://img.shields.io/badge/Donate-PayPal-2997d8)](https://www.paypal.com/donate?hosted_button_id=2BVFF5GJ9SXAJ)
[![Sponsor at Github](https://img.shields.io/badge/Sponsor-GitHub-28a745)](https://github.com/sponsors/tillsteinbach)

[MQTT](https://mqtt.org) Client that publishes data from several vehicle services


## What is the purpose?
If you want to integrate data from your car, a standard protocol such as [MQTT](https://mqtt.org) can be very helpful. This Client enables you to integrate with the [MQTT Broker](https://mqtt.org/software/) of your choice (e.g. your home automation solution such as [ioBroker](https://www.iobroker.net), [FHEM](https://fhem.de) or [Home Assistant](https://www.home-assistant.io))

## How to install
### Create config file
Create a carconnectivity.json config file like this (Example if you have a Volkswagen and a MySkoda account). A documentation of all possible config options can be found [here](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/tree/main/doc/Config.md).
```json
{
    "carConnectivity": {
        "log_level": "error", // set the global log level, you can set individual log levels in the connectors and plugins
        "connectors": [
            {
                "type": "skoda", // Definition for a MySkoda account
                "config": {
                    "interval": 600, // Interval in which the server is checked in seconds
                    "username": "test@test.de", // Username of your MySkoda Account
                    "password": "testpassword123" // Password of your MySkoda Account
                }
            },
            {
                "type": "volkswagen", // Definition for a Volkswagen account
                "config": {
                    "interval": 300, // Interval in which the server is checked in seconds
                    "username": "test@test.de", // Username of your Volkswagen Account
                    "password": "testpassword123" // Username of your Volkswagen Account
                }
            }
        ],
        "plugins": [
            {
                "type": "mqtt", // Definition for the MQTT Connection
                "config": {
                    "broker": "192.168.0.123", // Broker hostname or IP address
                    "username": "testuser", // Broker username to login
                    "password": "testuser", // Broker password to login
                }
            }
        ]
    }
}
```

### Using docker-compose
When using docker-compose configure CarConnectivity-MQTT like that:
```yml
services:
  carconnectivity-mqtt:
    image: "tillsteinbach/carconnectivity-mqtt:edge"
    volumes:
      - /path/to/your/config/carconnectivity.json:/carconnectivity.json
```

### Connectors & Plugins
CarConnectivity-MQTT comes with Skoda and Volkswagen connectors preinstalled. If you need support for further connectors you can use the `ADDITIONAL_INSTALLS` variable to install additional plugins at runtime, e.g.:
```yml
...
  carconnectivity-mqtt:
    image: "tillsteinbach/carconnectivity-mqtt:edge"
    environment:
      - ADDITIONAL_INSTALLS=carconnectivity-plugin-abrp
...
```

### Times
By default the times coming from the car are UTC isoformat. You can convert times to your local timezone by adding `convert-times` to your config. Convert times will use the timezone specified in `TZ` variable.
You can format times in your local format by adding `timeformat` to your config. This will use the default Date/Time format of your locale setting (`LC_ALL` variable). If you want to set a specific format add e.g. `timeformat '%a %d %b %Y %T'` to your config.
```yml
...
  carconnectivity-mqtt:
    image: "tillsteinbach/carconnectivity-mqtt:edge"
    environment:
      - TZ=Europe/Berlin
      - LANG=de_DE
      - LC_ALL=de_DE
...
```
### Using Miles or Farenheit
CarConnectivity will guess your desired temperature or range/speed unit based on the systems locale. If it does not match what you want, you can set a different locale in your `carconnectivity.json` json config.

### Without Docker
If you don't want to use docker you can obtain carconnectivity-mqtt also as a stand-alone application from [PyPI](https://pypi.org/project/carconnectivity-plugin-mqtt/). Just install instead using:
```bash
pip install carconnectivity-plugin-mqtt
carconnectivity-mqtt carconnectivity.json
```

## Tested with
- Volkswagen ID.3 Modelyear 2021
- Volkswagen Passat GTE Modelyear 2021
- Skoda Enyaq RD Modelyear 2025

## Reporting Issues
Please feel free to open an issue at [GitHub Issue page](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/issues) to report problems you found.

## More Questions?
Please see the wiki [Wiki](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/wiki) or start a [discussion](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/discussions).

### Known Issues
- The Tool is in alpha state and may change unexpectedly at any time!

## Related Projects:
- [CarConnectivity-cli](https://github.com/tillsteinbach/CarConnectivity-cli): Commandline Interface to interact with the CarConnectivity Services
- [CarConnectivity](https://github.com/tillsteinbach/carconnectivity-python): Python API to used in CarConnectivity-mqtt
