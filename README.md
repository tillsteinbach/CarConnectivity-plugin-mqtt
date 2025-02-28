

# CarConnectivity Plugin for MQTT
[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/latest)
[![GitHub](https://img.shields.io/github/license/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/issues)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/carconnectivity-plugin-mqtt?label=PyPI%20Downloads)](https://pypi.org/project/carconnectivity-plugin-mqtt/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/carconnectivity-plugin-mqtt)](https://pypi.org/project/carconnectivity-plugin-mqtt/)
[![Docker Image Size (latest semver)](https://img.shields.io/docker/image-size/tillsteinbach/carconnectivity-mqtt?sort=semver)](https://hub.docker.com/r/tillsteinbach/carconnectivity-mqtt)
[![Docker Pulls](https://img.shields.io/docker/pulls/tillsteinbach/carconnectivity-mqtt)](https://hub.docker.com/r/tillsteinbach/carconnectivity-mqtt)
[![Donate at PayPal](https://img.shields.io/badge/Donate-PayPal-2997d8)](https://www.paypal.com/donate?hosted_button_id=2BVFF5GJ9SXAJ)
[![Sponsor at Github](https://img.shields.io/badge/Sponsor-GitHub-28a745)](https://github.com/sponsors/tillsteinbach)

## CarConnectivity will become the successor of [WeConnect-python](https://github.com/tillsteinbach/WeConnect-python) in 2025 with similar functionality but support for other brands beyond Volkswagen!

[CarConnectivity](https://github.com/tillsteinbach/CarConnectivity) is a python API to connect to various car services. If you want to publish the data collected from your vehicle in a standard protocol such as [MQTT](https://mqtt.org) this plugin will help you. This Client enables you to integrate with the [MQTT Broker](https://mqtt.org/software/) of your choice (e.g. your home automation solution such as [ioBroker](https://www.iobroker.net), [FHEM](https://fhem.de) or [Home Assistant](https://www.home-assistant.io))

## How to install

### Install using PIP
If you want to use CarConnectivity-mqtt, the easiest way is to obtain it from [PyPI](https://pypi.org/project/carconnectivity-plugin-mqtt/). Just install instead using:
```bash
pip3 install carconnectivity-plugin-mqtt
```

#### Connectors & Plugins
In order to connect vehciles from various brands, you need to install connector, e.g. with:
```bash
pip3 install carconnectivity-connector-volkswagen
pip3 install carconnectivity-connector-skoda
pip3 install carconnectivity-connector-seatcupra
```

### Install using pipx (alternative)
[pipx](https://github.com/pypa/pipx) is a tool to help you install and run end-user applications written in Python. [pipx](https://github.com/pypa/pipx) creates an isolated environment for each application and its associated packages.
```bash
pipx install carconnectivity-plugin-mqtt
```
#### Important
When using [pipx](https://github.com/pypa/pipx), connectors and plugins need to be explicitly installed in the carconnectivity-mqtt environment. Otherwise the connectors or plugins will not be found due to the isolation. You can do that with e.g.:
```bash
pipx inject carconnectivity-plugin-mqtt carconnectivity-connector-volkswagen
```

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
                    "password": "testuser" // Broker password to login
                }
            }
        ]
    }
}
```

### Startup
When using docker-compose configure CarConnectivity-MQTT like that:
```bash
carconnectivity-mqtt carconnectivity.json
```
If you face challenges the WebUI can help you find the problems: [CarConnectivity-plugin-webui](https://github.com/tillsteinbach/CarConnectivity-plugin-webui). Install it with:
```bash
pip3 install carconnectivity-plugin-webui
```
and add a plugin of `"type": "webui"` to your configuration.

### Updates
If you want to update, the easiest way is:
```bash
pip3 install carconnectivity-plugin-mqtt --upgrade
pip3 install carconnectivity-connector-volkswagen --upgrade
pip3 install carconnectivity-connector-skoda --upgrade
pip3 install carconnectivity-connector-seatcupra --upgrade
```

## With Docker
There is also a Docker image to easily host CarConnectivity-MQTT: [See on Dockerhub](https://hub.docker.com/r/tillsteinbach/carconnectivity-mqtt)

## Other
### Home Assistant
To make Auto Discovery and further features available in Home Assistant also install[CarConnectivity-plugin-mqtt_homeassistant](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt_homeassistant)
```bash
pip3 install carconnectivity-plugin-mqtt_homeassistant
```
and add it to your config:
```json
            {
                "type": "mqtt", // Definition for the MQTT Connection
                "config": {
                    "broker": "192.168.0.123", // Broker hostname or IP address
                    "username": "testuser", // Broker username to login
                    "password": "testuser" // Broker password to login
                }
            },
            {
                "type": "mqtt_homeassistant", // Definition for the MQTT Home Assistant Compatibility
                "config": {}
            }
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

### Credentials
If you do not want to provide your username or password inside the configuration you have to create a ".netrc" file at the appropriate location (usually this is your home folder):
```
# For MQTT broker
machine mymqttbroker
login test@test.de
password testpassword123
```
In this case the configuration needs to look like this:
```
{
    "carConnectivity": {
        "connectors": [
            ...
        ]
        "plugins": [
            {
                "type": "mqtt",
                "config": {
                    "broker": "mymqttbroker"
                }
            }
        ]
    }
}
```

You can also provide the location of the netrc file in the configuration.
```
{
    "carConnectivity": {
        "connectors": [
            ...
        ]
        "plugins": [
            {
                "type": "mqtt",
                "config": {
                    "broker": "mymqttbroker"
                    "netrc": "/some/path/on/your/filesystem"
                }
            }
        ]
    }
}
```
