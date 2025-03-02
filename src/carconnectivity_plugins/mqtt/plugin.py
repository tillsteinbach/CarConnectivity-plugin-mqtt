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
from carconnectivity.attributes import EnumAttribute
from carconnectivity.enums import ConnectionState

from carconnectivity_plugins.base.plugin import BasePlugin
from carconnectivity_plugins.mqtt.mqtt_client import CarConnectivityMQTTClient, TopicFormat, ImageFormat
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
        BasePlugin.__init__(self, plugin_id=plugin_id, car_connectivity=car_connectivity, config=config, log=LOG)

        self.connection_state: EnumAttribute = EnumAttribute(name="connection_state", parent=self, value_type=ConnectionState,
                                                             value=ConnectionState.DISCONNECTED, tags={'plugin_custom'})

        self._background_connect_thread: Optional[threading.Thread] = None
        self._background_publish_topics_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        LOG.info("Loading mqtt plugin with config %s", config_remove_credentials(config))

        if 'topic_format' in config and config['topic_format'] is not None:
            if config['topic_format'].lower() not in [e.value for e in TopicFormat]:
                raise ConfigurationError(f'Invalid topic format ("topic_format" must be one of {[e.value for e in TopicFormat]})')
            self.active_config['topic_format'] = TopicFormat(config['topic_format'].lower())
        else:
            self.active_config['topic_format'] = TopicFormat.SIMPLE

        if 'broker' not in config or not config['broker']:
            raise ConfigurationError('No MQTT broker specified in config ("broker" missing)')
        self.active_config['broker'] = config['broker']

        if 'port' in config and config['port'] is not None:
            self.active_config['port'] = config['port']
            if not self.active_config['port'] or self.active_config['port'] < 1 or self.active_config['port'] > 65535:
                raise ConfigurationError('Invalid port specified in config ("port" out of range, must be 1-65535)')
        else:
            self.active_config['port'] = 0

        if 'clientid' in config:
            self.active_config['clientid'] = config['clientid']
        else:
            self.active_config['clientid'] = None

        if 'prefix' in config:
            self.active_config['prefix'] = config['prefix']
        else:
            self.active_config['prefix'] = 'carconnectivity/0'

        if 'keepalive' in config and config['keepalive'] is not None:
            self.active_config['keepalive'] = config['keepalive']
        else:
            self.active_config['keepalive'] = 60

        if 'username' in config:
            self.active_config['username'] = config['username']
        else:
            self.active_config['username'] = None

        if 'password' in config:
            self.active_config['password'] = config['password']
        else:
            self.active_config['password'] = None

        if self.active_config['username'] is None or self.active_config['password'] is None:
            if 'netrc' in config:
                self.active_config['netrc'] = config['netrc']
            else:
                self.active_config['netrc'] = os.path.join(os.path.expanduser("~"), ".netrc")
            try:
                secrets = netrc.netrc(file=self.active_config['netrc'])
                authenticator = secrets.authenticators(self.active_config['broker'])
                if authenticator is not None:
                    self.active_config['username'], _, self.active_config['password'] = authenticator
                else:
                    raise ConfigurationError(f'No credentials found for {self.active_config["broker"]} in netrc-file {self.active_config["netrc"]}')
            except FileNotFoundError as exc:
                raise ConfigurationError(f'{self.active_config["netrc"]} netrc-file was not found. Create it or provide'
                                         ' username and password in the config.') from exc

        mqttversion_choices: list[str] = ['3.1', '3.1.1', '5']
        if 'version' in config:
            if config['version'] == '3.1':
                self.active_config['version'] = '3.1'
                self.mqttversion = paho.mqtt.client.MQTTv31
            elif config['version'] == '3.1.1':
                self.active_config['version'] = '3.1.1'
                self.mqttversion = paho.mqtt.client.MQTTv311
            elif config['version'] == '5':
                self.active_config['version'] = '5'
                self.mqttversion = paho.mqtt.client.MQTTv5
            else:
                raise ConfigurationError(f'Invalid MQTT version specified in config ("version" must be one of {mqttversion_choices})')

        else:
            self.active_config['version'] = '3.1.1'
            self.mqttversion = paho.mqtt.client.MQTTv311

        transport_choices: list[Literal["tcp", "websockets", "unix"]] = ['tcp', 'websockets', 'unix']
        if 'transport' in config:
            if config['transport'] not in transport_choices:
                raise ConfigurationError(f'Invalid MQTT transport specified in config ("transport" must be one of {transport_choices})')
            self.active_config['transport'] = config['transport']
        else:
            self.active_config['transport'] = 'tcp'

        if 'tls' in config:
            self.active_config['tls'] = config['tls']
            if self.active_config['tls'] and self.active_config['port'] == 0:
                self.active_config['port'] = 8883
        else:
            self.active_config['tls'] = False
            if self.active_config['port'] == 0:
                self.active_config['port'] = 1883

        if 'tls_insecure' in config:
            self.active_config['tls_insecure'] = config['tls_insecure']
        else:
            self.active_config['tls_insecure'] = False

        if 'tls_cafile' in config:
            self.active_config['tls_cafile'] = config['tls_cafile']
        else:
            self.active_config['tls_cafile'] = None

        if 'tls_certfile' in config:
            self.active_config['tls_certfile'] = config['tls_certfile']
        else:
            self.active_config['tls_certfile'] = None

        if 'tls_keyfile' in config:
            self.active_config['tls_keyfile'] = config['tls_keyfile']
        else:
            self.active_config['tls_keyfile'] = None

        mqtttls_version_choices: list[str] = ['tlsv1.2', 'tlsv1.1', 'tlsv1']
        if 'tls_version' in config and config['tls_version'] is not None:
            if config['tls_version'] == "tlsv1.2":
                self.active_config['tls_version'] = "tlsv1.2"
                self.mqtttls_version: ssl._SSLMethod = ssl.PROTOCOL_TLSv1_2
            elif config['tls_version'] == "tlsv1.1":
                self.active_config['tls_version'] = "tlsv1.1"
                self.mqtttls_version = ssl.PROTOCOL_TLSv1_1
            elif config['tls_version'] == "tlsv1":
                self.active_config['tls_version'] = "tlsv1"
                self.mqtttls_version = ssl.PROTOCOL_TLSv1
            else:
                raise ConfigurationError(f'Invalid MQTT TLS version specified in config ("tls_version" must be one of {mqtttls_version_choices})')
        else:
            self.active_config['tls_version'] = "tlsv1.2"
            self.mqtttls_version: ssl._SSLMethod = ssl.PROTOCOL_TLSv1_2

        if 'ignore_for' in config and config['ignore_for-for'] is not None:
            self.active_config['ignore_for'] = config['ignore_for-for']
        else:
            self.active_config['ignore_for'] = 5

        if 'republish_on_update' in config and config['republish_on_update'] is not None:
            self.active_config['republish_on_update'] = config['republish_on_update']
        else:
            self.active_config['republish_on_update'] = False

        if 'retain_on_disconnect' in config and config['retain_on_disconnect'] is not None:
            self.retain_on_disconnect: bool = config['retain_on_disconnect']
        else:
            self.retain_on_disconnect: bool = False

        if 'topic_filter_regex' in config and config['topic_filter_regex'] is not None:
            self.active_config['topic_filter_regex'] = config['topic_filter_regex']
        else:
            self.active_config['topic_filter_regex'] = None

        if 'convert_timezone' in config and config['convert_timezone'] is not None:
            self.convert_timezone: Optional[tzinfo] = tz.gettz(config['convert_timezone'])
        else:
            self.convert_timezone: Optional[tzinfo] = datetime.now().astimezone().tzinfo
        self.active_config['convert_timezone'] = str(self.convert_timezone)

        if 'time_format' in config and config['time_format'] is not None:
            self.active_config['time_format'] = config['time_format']
        else:
            self.active_config['time_format'] = None

        if 'locale' in config and config['locale'] is not None:
            self.active_config['locale'] = config['locale']
            try:
                locale.setlocale(locale.LC_ALL, self.active_config['locale'])
                if self.active_config['time_format'] is None or self.active_config['time_format'] == '':
                    self.active_config['time_format'] = locale.nl_langinfo(locale.D_T_FMT)
            except locale.Error as err:
                raise ConfigurationError('Invalid locale specified in config ("locale" must be a valid locale)') from err
        else:
            self.active_config['locale'] = locale.getlocale()[0]

        if 'image_format' in config and config['image_format'] is not None:
            if config['image_format'] in ImageFormat:
                self.image_format: ImageFormat = ImageFormat(config['image_format'])
            else:
                raise ConfigurationError(f'Invalid image format specified in config ("image_format" must be one of {[e.value for e in ImageFormat]})')
        else:
            self.image_format: ImageFormat = ImageFormat.PNG
        self.active_config['image_format'] = self.image_format.value

        if 'with_full_json' in config and config['with_full_json'] is not None:
            self.active_config['with_full_json'] = config['with_full_json']
        else:
            self.active_config['with_full_json'] = False

        self.mqtt_client = CarConnectivityMQTTClient(plugin=self,
                                                     car_connectivity=self.car_connectivity,
                                                     client_id=self.active_config['clientid'],
                                                     protocol=self.mqttversion,
                                                     transport=self.active_config['transport'],
                                                     prefix=self.active_config['prefix'],
                                                     ignore_for=self.active_config['ignore_for'],
                                                     republish_on_update=self.active_config['republish_on_update'],
                                                     retain_on_disconnect=self.retain_on_disconnect,
                                                     topic_filter_regex=self.active_config['topic_filter_regex'],
                                                     convert_timezone=self.convert_timezone,
                                                     time_format=self.active_config['time_format'],
                                                     with_raw_json_topic=False,
                                                     topic_format=self.active_config['topic_format'],
                                                     locale=self.active_config['locale'],
                                                     image_format=self.image_format,
                                                     with_full_json=self.active_config['with_full_json'])
        if self.active_config['tls']:
            if self.active_config['tls_insecure']:
                cert_required: ssl.VerifyMode = ssl.CERT_NONE
            else:
                cert_required: ssl.VerifyMode = ssl.CERT_REQUIRED

            self.mqtt_client.tls_set(ca_certs=self.active_config['tls_cafile'], certfile=self.active_config['tls_certfile'],
                                     keyfile=self.active_config['tls_keyfile'], cert_reqs=cert_required,
                                     tls_version=self.mqtttls_version)
            if self.active_config['tls_insecure']:
                self.mqtt_client.tls_insecure_set(True)
        if self.active_config['username'] is not None:
            self.mqtt_client.username_pw_set(username=self.active_config['username'], password=self.active_config['password'])

    def startup(self) -> None:
        LOG.info("Starting MQTT plugin")
        self._stop_event.clear()
        self._background_connect_thread = threading.Thread(target=self._background_connect_loop, daemon=False)
        self._background_connect_thread.name = 'carconnectivity.plugins.mqtt-background_connect'
        self._background_connect_thread.start()
        self.mqtt_client.loop_start()
        self._background_publish_topics_thread = threading.Thread(target=self._background_publish_topics_loop, daemon=False)
        self._background_publish_topics_thread.name = 'carconnectivity.plugins.mqtt-background_publish_topics'
        self._background_publish_topics_thread.start()
        self.healthy._set_value(value=True)  # pylint: disable=protected-access
        LOG.debug("Starting MQTT plugin done")

    def _background_connect_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                LOG.info('Connecting to MQTT-Server %s:%d', self.active_config['broker'], self.active_config['port'])
                self.mqtt_client.connect(self.active_config['broker'], self.active_config['port'], self.active_config['keepalive'])
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

    def get_type(self) -> str:
        return "carconnectivity-plugin-mqtt"

    def get_name(self) -> str:
        return "MQTT Plugin"
