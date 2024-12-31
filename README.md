

# CarConnectivity Plugin for MQTT
[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/releases/latest)
[![GitHub](https://img.shields.io/github/license/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/tillsteinbach/CarConnectivity-plugin-mqtt)](https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt/issues)
[![Donate at PayPal](https://img.shields.io/badge/Donate-PayPal-2997d8)](https://www.paypal.com/donate?hosted_button_id=2BVFF5GJ9SXAJ)
[![Sponsor at Github](https://img.shields.io/badge/Sponsor-GitHub-28a745)](https://github.com/sponsors/tillsteinbach)

## CarConnectivity will become the successor of [WeConnect-python](https://github.com/tillsteinbach/WeConnect-python) in 2025 with similar functionality but support for other brands beyond Volkswagen!

[CarConnectivity](https://github.com/tillsteinbach/CarConnectivity) is a python API to connect to various car services. If you want to publish the data collected from your vehicle in a standard protocol such as [MQTT](https://mqtt.org) this plugin will help you. This Client enables you to integrate with the [MQTT Broker](https://mqtt.org/software/) of your choice (e.g. your home automation solution such as [ioBroker](https://www.iobroker.net), [FHEM](https://fhem.de) or [Home Assistant](https://www.home-assistant.io))

## Configuration
In your carconnectivity.json configuration add a section for the mqtt plugin like this:
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
                    "username": "test@test.de",
                    "password": "testpassword123"
                }
            }
        ]
    }
}
```
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