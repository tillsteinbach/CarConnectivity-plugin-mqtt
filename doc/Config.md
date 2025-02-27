

# CarConnectivity Plugin for MQTT Config Options
The configuration for CarConnectivity is a .json file.
## General format
The general format is a `carConnectivity` section, followed by a list of connectors and plugins.
In the `carConnectivity` section you can set the global `log_level`.
Each connector or plugin needs a `type` attribute and a `config` section.
The `type` and config options specific to your connector or plugin can be found on their respective project page.
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
                "type": "mqtt", // Minimal definition for the MQTT Connection
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
### MQTT Plugin Options
These are the valid options for the MQTT plugin
```json
{
    "carConnectivity": {
        "connectors": [],
        "plugins": [
            {
                "type": "mqtt", // Definition for the MQTT plugin
                "disabled": false, // You can disable plugins without removing them from the config completely
                "config": {
                    "log_level": "error", // The log level for the plugin. Otherwise uses the global log level
                    "broker": "192.168.0.123", // Broker hostname or IP address
                    "port": 1883, // Broker network port
                    "username": "testuser", // Broker username to login
                    "password": "testuser", // Broker password to login
                    "netrc": "~/.netr", // netrc file if to be used for passwords
                    "clientid": "my_client", // Client id if should not be generated
                    "prefix": "carconnectivity/0", // prefix for published topics
                    "keepalive": 60, // MQTT keepalive value
                    "version": "3.1", // MQTT Protocol version to use ["3.1", "3.1.1", "5"]
                    "transport": "tcp", // Transport protocol ["tcp", "websockets", "unix"]
                    "tls": true, // User TLS (will change standard port to 8883)
                    "tls_insecure": true, // Allows TLS with insecure certificates
                    "tls_cafile": "ca.cert", // CA certificate file
                    "tls_certfile": "client.cert", // Client certificate file
                    "tls_keyfile": "client.key", // Client secret key
                    "tls_version": "tlsv1.2", // TLS Version used
                    "ignore_for": 20, // Ignore messages for first IGNORE seconds after subscribe to aviod retained messages from the broker to make changes to the car
                    "republish_on_update": true, // Republish all topics on every update, not just when the value changes.
                    "retain_on_disconnect": true, // Do not publish empty message on disconnect to keep last value in broker
                    "topic_filter_regex": "carconnectivity\.0\./garage/WVWAB312[0-9A-Z]+/.*",
                    "convert_timezone": "Europe/Berlin", // Timezone to convert when publishing times
                    "time_format": "%Y-%m-%dT%H:%M:%S%z", // Use custom time format 
                    "locale": "de_DE", // Locale for conversions
                    "homeassistant_discovery": true // Publish device auto discovery topic for home assistant
                }
            }
        ]
    }
}
```

### Connector Options
Valid Options for connectors can be found here:
* [CarConnectivity-connector-skoda Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-skoda/tree/main/doc/Config.md)
* [CarConnectivity-connector-volkswagen Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-volkswagen/tree/main/doc/Config.md)
* [CarConnectivity-connector-seatcupra Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-seatcupra/tree/main/doc/Config.md)
* [CarConnectivity-connector-tronity Config Options](https://github.com/tillsteinbach/CarConnectivity-connector-tronity/tree/main/doc/Config.md)
