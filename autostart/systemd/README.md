# Install CarConnectivity-MQTT as a service on on operating systems providing systemd

## How to install
Open file carconnectivity-mqtt.service and change the username and commandline parameters according to your needs

Copy the unit file to /etc/systemd/system and give it permissions:
```bash
sudo cp carconnectivity-mqtt.service /etc/systemd/system/carconnectivity-mqtt.service
sudo chmod 644 /etc/systemd/system/carconnectivity-mqtt.service
```

## How to start
Once you have installed the file, you are ready to test the service:
```bash
sudo systemctl start carconnectivity-mqtt
sudo systemctl status carconnectivity-mqtt
```

The service can be stopped or restarted using standard systemd commands:
```bash
sudo systemctl stop carconnectivity-mqtt
sudo systemctl restart carconnectivity-mqtt
```

## How to enable autostart after boot
Finally, use the enable command to ensure that the service starts whenever the system boots:
```bash
sudo systemctl enable carconnectivity-mqtt
```
