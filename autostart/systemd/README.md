# Install carconnectivitymqtt as a service on on operating systems providing systemd

## How to install
Open file carconnectivitymqtt.service and change the username and commandline parameters according to your needs

Copy the unit file to /etc/systemd/system and give it permissions:
```bash
sudo cp carconnectivitymqtt.service /etc/systemd/system/carconnectivitymqtt.service
sudo chmod 644 /etc/systemd/system/carconnectivitymqtt.service
```

## Reload daemons
```
sudo systemctl daemon-reload
```

## How to start
Once you have installed the file, you are ready to test the service:
```bash
sudo systemctl start carconnectivitymqtt
sudo systemctl status carconnectivitymqtt
```

The service can be stopped or restarted using standard systemd commands:
```bash
sudo systemctl stop carconnectivitymqtt
sudo systemctl restart carconnectivitymqtt
```

## How to enable autostart after boot
Finally, use the enable command to ensure that the service starts whenever the system boots:
```bash
sudo systemctl enable carconnectivitymqtt
```
