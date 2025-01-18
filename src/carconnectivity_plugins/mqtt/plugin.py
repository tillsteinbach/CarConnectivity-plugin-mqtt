"""Module implements the plugin to connect with MQTT brokers."""
from __future__ import annotations
from typing import TYPE_CHECKING

import os
import threading
import logging
import netrc
import locale
import ssl
from datetime import datetime, tzinfo
from dateutil import tz

import paho.mqtt.client

from carconnectivity.errors import ConfigurationError
from carconnectivity.util import config_remove_credentials
from carconnectivity_plugins.base.plugin import BasePlugin
from carconnectivity_plugins.mqtt.mqtt_client import CarConnectivityMQTTClient, TopicFormat
from carconnectivity_plugins.mqtt._version import __version__

if TYPE_CHECKING:
    from typing import Dict, Optional, Literal
    from carconnectivity.carconnectivity import CarConnectivity

LOG: logging.Logger = logging.getLogger("carconnectivity.plugins.mqtt")


class Plugin(BasePlugin):  # pylint: disable=too-many-instance-attributes
    """
    Plugin class for MQTT connectivity.
    Args:
        car_connectivity (CarConnectivity): An instance of CarConnectivity.
        config (Dict): Configuration dictionary containing connection details.
    """
    def __init__(self, plugin_id: str, car_connectivity: CarConnectivity, config: Dict) -> None:  # pylint: disable=too-many-branches, too-many-statements
        BasePlugin.__init__(self, plugin_id=plugin_id, car_connectivity=car_connectivity, config=config)

        self._background_connect_thread: Optional[threading.Thread] = None
        self._background_publish_topics_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Configure logging
        if 'log_level' in config and config['log_level'] is not None:
            config['log_level'] = config['log_level'].upper()
            if config['log_level'] in logging._nameToLevel:
                LOG.setLevel(config['log_level'])
                self.log_level._set_value(config['log_level'])  # pylint: disable=protected-access
            else:
                raise ConfigurationError(f'Invalid log level: "{config["log_level"]}" not in {list(logging._nameToLevel.keys())}')
        LOG.info("Loading mqtt plugin with config %s", config_remove_credentials(self.config))

        if 'topic_format' in self.config and self.config['topic_format'] is not None:
            if self.config['topic_format'].lower() not in [e.value for e in TopicFormat]:
                raise ConfigurationError(f'Invalid topic format ("topic_format" must be one of {[e.value for e in TopicFormat]})')
            self.topic_format: TopicFormat = TopicFormat(self.config['topic_format'].lower())
        else:
            self.topic_format: TopicFormat = TopicFormat.SIMPLE

        if 'broker' not in self.config or not self.config['broker']:
            raise ConfigurationError('No MQTT broker specified in config ("broker" missing)')
        self.mqttbroker: str = self.config['broker']

        if 'port' in self.config and self.config['port'] is not None:
            self.mqttport: int = self.config['port']
            if not self.mqttport or self.mqttport < 1 or self.mqttport > 65535:
                raise ConfigurationError('Invalid port specified in config ("port" out of range, must be 1-65535)')
        else:
            self.mqttport: int = 0

        if 'clientid' in self.config:
            self.mqttclientid: Optional[str] = self.config['clientid']
        else:
            self.mqttclientid: Optional[str] = None

        if 'prefix' in self.config:
            self.mqttprefix: Optional[str] = self.config['prefix']
        else:
            self.mqttprefix: Optional[str] = 'carconnectivity/0'

        if 'keepalive' in self.config and self.config['keepalive'] is not None:
            self.mqttkeepalive: int = self.config['keepalive']
        else:
            self.mqttkeepalive: int = 30

        if 'username' in self.config:
            self.mqttusername: Optional[str] = self.config['username']
        else:
            self.mqttusername: Optional[str] = None

        if 'password' in self.config:
            self.mqttpassword: Optional[str] = self.config['password']
        else:
            self.mqttpassword: Optional[str] = None

        if self.mqttusername is None or self.mqttpassword is None:
            if 'netrc' in self.config and self.config['netrc'] is not None:
                netrc_file: str = self.config['netrc']
            else:
                netrc_file: str = os.path.join(os.path.expanduser("~"), ".netrc")
            try:
                secrets = netrc.netrc(file=netrc_file)
                authenticator = secrets.authenticators(self.mqttbroker)
                if authenticator is not None:
                    self.mqttusername, _, self.mqttpassword = authenticator
                else:
                    raise ConfigurationError(f'No credentials found for {self.mqttbroker} in netrc-file {netrc_file}')
            except FileNotFoundError as exc:
                raise ConfigurationError(f'{netrc_file} netrc-file was not found. Create it or provide username and password in the config.') from exc

        mqttversion_choices: list[str] = ['3.1', '3.1.1', '5']
        if 'version' in self.config:
            if self.config['version'] == '3.1':
                self.mqttversion = paho.mqtt.client.MQTTv31
            elif self.config['version'] == '3.1.1':
                self.mqttversion = paho.mqtt.client.MQTTv311
            elif self.config['version'] == '5':
                self.mqttversion = paho.mqtt.client.MQTTv5
            else:
                raise ConfigurationError(f'Invalid MQTT version specified in config ("version" must be one of {mqttversion_choices})')

        else:
            self.mqttversion = paho.mqtt.client.MQTTv311

        transport_choices: list[Literal["tcp", "websockets", "unix"]] = ['tcp', 'websockets', 'unix']
        if 'transport' in self.config:
            if self.config['transport'] not in transport_choices:
                raise ConfigurationError(f'Invalid MQTT transport specified in config ("transport" must be one of {transport_choices})')
            self.mqtttransport: Literal["tcp", "websockets", "unix"] = self.config['transport']
        else:
            self.mqtttransport: Literal["tcp", "websockets", "unix"] = 'tcp'

        if 'tls' in self.config:
            self.mqtttls: Optional[bool] = self.config['tls']
            if self.mqtttls and self.mqttport == 0:
                self.mqttport = 8883
        else:
            self.mqtttls: Optional[bool] = False
            if self.mqttport == 0:
                self.mqttport = 1883

        if 'tls_insecure' in self.config:
            self.mqtttls_insecure: Optional[bool] = self.config['tls_insecure']
        else:
            self.mqtttls_insecure: Optional[bool] = False

        if 'tls_cafile' in self.config:
            self.mqtttls_cafile: Optional[str] = self.config['tls_cafile']
        else:
            self.mqtttls_cafile: Optional[str] = None

        if 'tls_certfile' in self.config:
            self.mqtttls_certfile: Optional[str] = self.config['tls_certfile']
        else:
            self.mqtttls_certfile: Optional[str] = None

        if 'tls_keyfile' in self.config:
            self.mqtttls_keyfile: Optional[str] = self.config['tls_keyfile']
        else:
            self.mqtttls_keyfile: Optional[str] = None

        mqtttls_version_choices: list[str] = ['tlsv1.2', 'tlsv1.1', 'tlsv1']
        if 'tls_version' in self.config and self.config['tls_version'] is not None:
            if self.config['tls_version'] == "tlsv1.2":
                self.mqtttls_version: ssl._SSLMethod = ssl.PROTOCOL_TLSv1_2
            elif self.config['tls_version'] == "tlsv1.1":
                self.mqtttls_version = ssl.PROTOCOL_TLSv1_1
            elif self.config['tls_version'] == "tlsv1":
                self.mqtttls_version = ssl.PROTOCOL_TLSv1
            else:
                raise ConfigurationError(f'Invalid MQTT TLS version specified in config ("tls_version" must be one of {mqtttls_version_choices})')
        else:
            self.mqtttls_version: ssl._SSLMethod = ssl.PROTOCOL_TLSv1_2

        if 'ignore_for' in self.config and self.config['ignore_for-for'] is not None:
            self.ignore_for: int = self.config['ignore_for-for']
        else:
            self.ignore_for: int = 5

        if 'republish_on_update' in self.config and self.config['republish_on_update'] is not None:
            self.republish_on_update: bool = self.config['republish_on_update']
        else:
            self.republish_on_update: bool = False

        if 'retain_on_disconnect' in self.config and self.config['retain_on_disconnect'] is not None:
            self.retain_on_disconnect: bool = self.config['retain_on_disconnect']
        else:
            self.retain_on_disconnect: bool = False

        if 'topic_filter_regex' in self.config and self.config['topic_filter_regex'] is not None:
            self.topic_filter_regex: Optional[str] = self.config['topic_filter_regex']
        else:
            self.topic_filter_regex: Optional[str] = None

        if 'convert_timezone' in self.config and self.config['convert_timezone'] is not None:
            self.convert_timezone: Optional[tzinfo] = tz.gettz(self.config['convert_timezone'])
        else:
            self.convert_timezone: Optional[tzinfo] = datetime.now().astimezone().tzinfo

        if 'time_format' in self.config and self.config['time_format'] is not None:
            self.time_format: Optional[str] = self.config['time_format']
        else:
            self.time_format: Optional[str] = None

        if 'locale' in self.config and self.config['locale'] is not None:
            self.locale: Optional[str] = self.config['locale']
            try:
                locale.setlocale(locale.LC_ALL, self.locale)
                if self.time_format is None or self.time_format == '':
                    self.time_format = locale.nl_langinfo(locale.D_T_FMT)
            except locale.Error as err:
                raise ConfigurationError('Invalid locale specified in config ("locale" must be a valid locale)') from err
        else:
            self.locale: Optional[str] = locale.getlocale()[0]

        self.mqtt_client = CarConnectivityMQTTClient(car_connectivity=self.car_connectivity,
                                                     plugin_id=plugin_id,
                                                     client_id=self.mqttclientid,
                                                     protocol=self.mqttversion,
                                                     transport=self.mqtttransport,
                                                     prefix=self.mqttprefix,
                                                     ignore_for=self.ignore_for,
                                                     republish_on_update=self.republish_on_update,
                                                     retain_on_disconnect=self.retain_on_disconnect,
                                                     topic_filter_regex=self.topic_filter_regex,
                                                     convert_timezone=self.convert_timezone,
                                                     time_format=self.time_format,
                                                     with_raw_json_topic=False,
                                                     topic_format=self.topic_format,
                                                     locale=self.locale)
        if self.mqtttls:
            if self.mqtttls_insecure:
                cert_required: ssl.VerifyMode = ssl.CERT_NONE
            else:
                cert_required: ssl.VerifyMode = ssl.CERT_REQUIRED

            self.mqtt_client.tls_set(ca_certs=self.mqtttls_certfile, certfile=self.mqtttls_certfile, keyfile=self.mqtttls_keyfile, cert_reqs=cert_required,
                                     tls_version=self.mqtttls_version)
            if self.mqtttls_insecure:
                self.mqtt_client.tls_insecure_set(True)
        if self.mqttusername is not None:
            self.mqtt_client.username_pw_set(username=self.mqttusername, password=self.mqttpassword)

    def startup(self) -> None:
        LOG.info("Starting MQTT plugin")
        self._stop_event.clear()
        self._background_connect_thread = threading.Thread(target=self._background_connect_loop, daemon=False)
        self._background_connect_thread.start()
        self.mqtt_client.loop_start()
        self._background_publish_topics_thread = threading.Thread(target=self._background_publish_topics_loop, daemon=False)
        self._background_publish_topics_thread.start()
        LOG.debug("Starting MQTT plugin done")

    def _background_connect_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                LOG.info('Connecting to MQTT-Server %s:%d', self.mqttbroker, self.mqttport)
                self.mqtt_client.connect(self.mqttbroker, self.mqttport, self.mqttkeepalive)
                break
            except ConnectionRefusedError as e:
                LOG.error('Could not connect to MQTT-Server: %s, will retry in 10 seconds', e)
                self._stop_event.wait(10)

    def _background_publish_topics_loop(self) -> None:
        while not self._stop_event.is_set():
            self.mqtt_client.publish_topics()
            self._stop_event.wait(10)

    def shutdown(self) -> None:
        """
        Shuts down the connector by persisting current state, closing the session,
        and cleaning up resources.

        This method performs the following actions:
        1. Persists the current state.
        2. Closes the session.
        3. Sets the session and manager to None.
        4. Calls the shutdown method of the base connector.
        """
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()
        self._stop_event.set()
        if self._background_connect_thread is not None:
            self._background_connect_thread.join()
        return super().shutdown()

    def get_version(self) -> str:
        return __version__
