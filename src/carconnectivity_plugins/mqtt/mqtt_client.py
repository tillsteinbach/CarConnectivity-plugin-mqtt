"""Module implements the MQTT client."""
from __future__ import annotations
from typing import TYPE_CHECKING

import logging

from enum import Enum
from datetime import datetime, timedelta

import paho.mqtt.client

from carconnectivity import errors
from carconnectivity import attributes
from carconnectivity import observable

if TYPE_CHECKING:
    from typing import Optional

    from carconnectivity.carconnectivity import CarConnectivity


LOG = logging.getLogger("carconnectivity-plugin-mqtt")


class CarConnectivityMQTTClient(paho.mqtt.client.Client):  # pylint: disable=too-many-instance-attributes
    def __init__(self, car_connectivity: CarConnectivity, client_id: Optional[str] = None, protocol=paho.mqtt.client.MQTTv311, transport: str = 'tcp',
                 prefix: Optional[str] = 'carconnectivity/0', ignore_for: int = 0, republish_on_update=False, topic_filter_regex=None, convert_timezone=None,
                 time_format=None, with_raw_json_topic=False) -> None:
        super().__init__(callback_api_version=paho.mqtt.client.CallbackAPIVersion.VERSION2, client_id=client_id, transport=transport, protocol=protocol)
        self.car_connectivity: CarConnectivity = car_connectivity
        self.prefix: str = prefix or 'carconnectivity/0'
        self.connected = False
        self.has_error = None
        self.ignore_for = ignore_for
        self.last_subscribe = None
        self.topics = []
        self.topics_changed = False
        self.writeable_topics = []
        self.writeable_topics_changed = False
        self.republish_on_update = republish_on_update
        self.topic_filter_regex = topic_filter_regex
        self.convert_timezone = convert_timezone
        self.time_format = time_format
        self.has_changes = False
        self.with_raw_json_topic = with_raw_json_topic

        self.on_connect = self.on_connect_callback
        self.on_message = self.on_message_callback
        self.on_disconnect = self.on_disconnect_callback
        self.on_subscribe = self.on_subscribe_callback

        if self.republish_on_update:
            flags = (observable.Observable.ObserverEvent.UPDATED
                     | observable.Observable.ObserverEvent.ENABLED
                     | observable.Observable.ObserverEvent.DISABLED)
        else:
            flags = (observable.Observable.ObserverEvent.VALUE_CHANGED
                     | observable.Observable.ObserverEvent.ENABLED
                     | observable.Observable.ObserverEvent.DISABLED)
        self.car_connectivity.add_observer(self.on_carconnectivity_event, flags, priority=observable.Observable.ObserverPriority.USER_MID)

        self.will_set(topic=f'{self.prefix}/mqtt/connected', qos=1, retain=True, payload=False)

    def _add_topic(self, topic, writeable=False):
        if topic not in self.topics:
            if writeable:
                self.writeable_topics.append(topic)
                self.writeable_topics.sort()
                self.writeable_topics_changed = True
            else:
                self.topics.append(topic)
                self.topics.sort()
                self.topics_changed = True

    def publish_topics(self):
        if self.topics_changed:
            self.topics_changed = False
            topicstopic = f'{self.prefix}/mqtt/topics'
            content = ',\n'.join(self.topics)
            self.publish(topic=topicstopic, qos=1, retain=True, payload=content)
            if topicstopic not in self.topics:
                self._add_topic(topicstopic)

        if self.writeable_topics_changed:
            self.writeable_topics_changed = False
            writeabletopicstopic = f'{self.prefix}/mqtt/writeable_topics'
            content = ',\n'.join(self.writeable_topics)
            self.publish(topic=writeabletopicstopic, qos=1, retain=True, payload=content)
            if writeabletopicstopic not in self.topics:
                self._add_topic(writeabletopicstopic)

    def disconnect(self, reasoncode=None, properties=None) -> paho.mqtt.client.MQTTErrorCode:
        try:
            disconect_publish = self.publish(topic=f'{self.prefix}/mqtt/connected', qos=1, retain=True, payload=False)
            disconect_publish.wait_for_publish()
        except RuntimeError:
            pass
        return super().disconnect(reasoncode, properties)

    def on_carconnectivity_event(self, element, flags):  # noqa: C901
        self.has_changes = True
        topic = f'{self.prefix}{element.get_absolute_path()}'
        if self.topic_filter_regex is not None and self.topic_filter_regex.match(topic):
            return

        if flags & observable.Observable.ObserverEvent.ENABLED:
            if isinstance(element, attributes.ChangeableAttribute):
                topic = topic + '_writetopic'
                LOG.debug('Subscribe for attribute %s%s', self.prefix, element.get_absolute_path())
                self.subscribe(topic, qos=1)
                if topic not in self.topics:
                    self._add_topic(topic, writeable=True)
            elif isinstance(element, attributes.GenericAttribute):
                if topic not in self.topics:
                    self._add_topic(topic)
        elif (flags & observable.Observable.ObserverEvent.VALUE_CHANGED) \
                or (self.republish_on_update and (flags & observable.Observable.ObserverEvent.UPDATED)):
            converted_value = self.convert_value(element.value)
            LOG.debug('%s%s, value changed: new value is: %s', self.prefix, element.get_absolute_path(), converted_value)
            self.publish(topic=f'{self.prefix}{element.get_absolute_path()}', qos=1, retain=True, payload=converted_value)
        elif flags & observable.Observable.ObserverEvent.DISABLED:
            LOG.debug('%s%s, value is diabled', self.prefix, element.get_absolute_path())
            self.publish(topic=f'{self.prefix}{element.get_absolute_path()}', qos=1, retain=True, payload='')

    def convert_value(self, value):
        if isinstance(value, (str, int, float)) or value is None:
            return value
        if isinstance(value, (list)):
            return ', '.join([str(item.value) if isinstance(item, Enum) else str(item) for item in value])
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            converted_time = value
            if self.convert_timezone is not None:
                converted_time = value.astimezone(self.convert_timezone)
            if self.time_format is not None:
                return converted_time.strftime(self.time_format)
            return str(converted_time)
        # if isinstance(value, Image.Image):
        #     if self.pictureFormat == PictureFormat.TXT or self.pictureFormat is None:
        #         return util.imgToASCIIArt(value, columns=120, mode=util.ASCIIModes.ASCII)
        #     if self.pictureFormat == PictureFormat.PNG:
        #         img_io = BytesIO()
        #         value.save(img_io, 'PNG')
        #         return img_io.getvalue()
        #     return util.imgToASCIIArt(value, columns=120, mode=util.ASCIIModes.ASCII)
        return str(value)

    def _set_connected(self, connected=True):
        if connected != self.connected:
            topic = f'{self.prefix}/mqtt/connected'
            self.publish(topic=topic, qos=1, retain=True, payload=connected)
            self.connected = connected
            if topic not in self.topics:
                self._add_topic(topic)

    def _set_error(self, code=None, message=''):
        if code is None:
            code = CarConnectivityErrors.SUCCESS
        if code != CarConnectivityErrors.SUCCESS or message != '' or self.has_error is None or self.has_error:
            topic = f'{self.prefix}/mqtt/error/code'
            self.publish(topic=topic, qos=1, retain=False, payload=code.value)
            if topic not in self.topics:
                self._add_topic(topic)
            topic = f'{self.prefix}/mqtt/error/message'
            self.publish(topic=topic, qos=1, retain=False, payload=message)
            if topic not in self.topics:
                self._add_topic(topic)
        if code != CarConnectivityErrors.SUCCESS:
            self.has_error = True
        else:
            self.has_error = False

    def on_connect_callback(self, mqttc, obj, flags, reason_code, properties):  # noqa: C901  # pylint: disable=too-many-branches
        del mqttc  # unused
        del obj  # unused
        del flags  # unused
        del properties
        if reason_code == 0:
            LOG.info('Connected to MQTT broker')
            force_update_topic: str = f'{self.prefix}/mqtt/carconnectivityForceUpdate_writetopic'
            self.subscribe(force_update_topic, qos=2)
            if force_update_topic not in self.topics:
                self._add_topic(force_update_topic, writeable=True)

            # Subscribe again to all writeable topics after a reconnect
            for writeable_topic in self.writeable_topics:
                self.subscribe(writeable_topic, qos=1)

            # Handle topics that are already there
            all_attributes = self.car_connectivity.get_attributes(recursive=True)
            for attribute in all_attributes:
                if attribute.enabled:
                    attribute_topic: str = f'{self.prefix}{attribute.get_absolute_path()}'
                    # Skip topics that are filtered
                    if self.topic_filter_regex is not None and self.topic_filter_regex.match(attribute_topic):
                        continue
                    # if attribute is changeable, subscribe to it and add it to the list of writeable topics
                    if isinstance(attribute, attributes.ChangeableAttribute):
                        LOG.debug('Subscribe for attribute %s%s', self.prefix, attribute.get_absolute_path())
                        self.subscribe(attribute_topic, qos=1)
                        if attribute_topic not in self.topics:
                            self._add_topic(attribute_topic, writeable=True)
                    # if attribute is not writeable, add it to the list of topics
                    elif isinstance(attributes, attributes.GenericAttribute):
                        if attribute_topic not in self.topics:
                            self._add_topic(attribute_topic)
                    # if attribute has a value, publish it
                    if attribute.value is not None:
                        converted_value = self.convert_value(attribute.value)
                        self.publish(topic=attribute_topic, qos=1, retain=True, payload=converted_value)

            self._set_connected()

        elif reason_code == 128:
            LOG.error('Could not connect (%s): Unspecified error', reason_code)
        elif reason_code == 129:
            LOG.error('Could not connect (%s): Malformed packet', reason_code)
        elif reason_code == 130:
            LOG.error('Could not connect (%s): Protocol error', reason_code)
        elif reason_code == 131:
            LOG.error('Could not connect (%s): Implementation specific error', reason_code)
        elif reason_code == 132:
            LOG.error('Could not connect (%s): Unsupported protocol version', reason_code)
        elif reason_code == 133:
            LOG.error('Could not connect (%s): Client identifier not valid', reason_code)
        elif reason_code == 134:
            LOG.error('Could not connect (%s): Bad user name or password', reason_code)
        elif reason_code == 135:
            LOG.error('Could not connect (%s): Not authorized', reason_code)
        elif reason_code == 136:
            LOG.error('Could not connect (%s): Server unavailable', reason_code)
        elif reason_code == 137:
            LOG.error('Could not connect (%s): Server busy. Retrying', reason_code)
        elif reason_code == 138:
            LOG.error('Could not connect (%s): Banned', reason_code)
        elif reason_code == 140:
            LOG.error('Could not connect (%s): Bad authentication method', reason_code)
        elif reason_code == 144:
            LOG.error('Could not connect (%s): Topic name invalid', reason_code)
        elif reason_code == 149:
            LOG.error('Could not connect (%s): Packet too large', reason_code)
        elif reason_code == 151:
            LOG.error('Could not connect (%s): Quota exceeded', reason_code)
        elif reason_code == 154:
            LOG.error('Could not connect (%s): Retain not supported', reason_code)
        elif reason_code == 155:
            LOG.error('Could not connect (%s): QoS not supported', reason_code)
        elif reason_code == 156:
            LOG.error('Could not connect (%s): Use another server', reason_code)
        elif reason_code == 157:
            LOG.error('Could not connect (%s): Server move', reason_code)
        elif reason_code == 159:
            LOG.error('Could not connect (%s): Connection rate exceeded', reason_code)
        else:
            LOG.error('Could not connect (%s)', reason_code)

    def on_disconnect_callback(self, client, userdata, flags, reason_code, properties):  # noqa: C901  # pylint: disable=too-many-branches,no-self-use
        del client
        del properties
        del flags

        if reason_code == 0:
            LOG.info('Client successfully disconnected')
        elif reason_code == 4:
            LOG.info('Client successfully disconnected: %s', userdata)
        elif reason_code == 137:
            LOG.error('Client disconnected: Server busy')
        elif reason_code == 139:
            LOG.error('Client disconnected: Server shutting down')
        elif reason_code == 160:
            LOG.error('Client disconnected: Maximum connect time')
        else:
            LOG.error('Client unexpectedly disconnected (%s), trying to reconnect', reason_code)

    def on_subscribe_callback(self, mqttc, obj, mid, reason_codes, properties):
        del mqttc  # unused
        del obj  # unused
        del mid  # unused
        del properties  # unused
        if any(x in [0, 1, 2] for x in reason_codes):
            self.last_subscribe = datetime.now()
            LOG.debug('sucessfully subscribed to topic')
        else:
            LOG.error('Subscribe was not successfull (%s)', ', '.join(reason_codes))

    def on_message_callback(self, mqttc, obj, msg):  # noqa: C901
        del mqttc  # unused
        del obj  # unused
        if self.ignore_for > 0 and self.last_subscribe is not None and (datetime.now() - self.last_subscribe) < timedelta(seconds=self.ignore_for):
            LOG.info('ignoring message from broker as it is within "ignore-for" delta of %ds', self.ignore_for)
        elif len(msg.payload) == 0:
            LOG.debug('ignoring empty message')
        elif msg.topic == f'{self.prefix}/mqtt/carconnectivityForceUpdate_writetopic':
            if msg.payload.lower() == b'True'.lower():
                LOG.info('Update triggered by MQTT message')
                self.publish(topic=f'{self.prefix}/mqtt/carconnectivityForceUpdate', qos=2, payload=True)
                self.car_connectivity.fetch_all()
                self.publish(topic=f'{self.prefix}/mqtt/carconnectivityForceUpdate', qos=2, payload=False)
        else:
            if msg.topic.startswith(self.prefix):
                address = msg.topic[len(self.prefix):]
                if address.endswith('_writetopic'):
                    address = address[:-len('_writetopic')]

                    attribute = self.car_connectivity.get_by_path(address)
                    if isinstance(attribute, attributes.ChangeableAttribute):
                        try:
                            attribute.value = msg.payload.decode()
                            self._set_error(code=CarConnectivityErrors.SUCCESS)
                            LOG.debug('Successfully set value')
                        except ValueError as value_error:
                            error_message: str = f'Error setting value: {value_error}'
                            self._set_error(code=CarConnectivityErrors.SET_FORMAT, message=error_message)
                            LOG.info(error_message)
                        except errors.SetterError as setter_error:
                            error_message = f'Error setting value: {setter_error}'
                            self._set_error(code=CarConnectivityErrors.SET_ERROR, message=error_message)
                            LOG.info(error_message)
                    else:
                        error_message = f'Trying to change item that is not a changeable attribute {msg.topic}: {msg.payload}'
                        self._set_error(code=CarConnectivityErrors.MESSAGE_NOT_UNDERSTOOD, message=error_message)
                        LOG.error(error_message)
                else:
                    attribute = self.car_connectivity.get_by_path(address)
                    if isinstance(attribute, attributes.ChangeableAttribute):
                        error_message = f'Trying to change item on not writeable topic {msg.topic}: {msg.payload}, please use {msg.topic}_writetopic instead'
                        self._set_error(code=CarConnectivityErrors.MESSAGE_NOT_UNDERSTOOD, message=error_message)
                        LOG.error(error_message)
                    else:
                        error_message = f'Trying to change item that is not a changeable attribute {msg.topic}: {msg.payload}'
                        self._set_error(code=CarConnectivityErrors.MESSAGE_NOT_UNDERSTOOD, message=error_message)
                        LOG.error(error_message)
            else:
                error_message = f'I don\'t understand message {msg.topic}: {msg.payload}'
                self._set_error(code=CarConnectivityErrors.ATTRIBUTE_NOT_CHANGEABLE, message=error_message)
                LOG.error(error_message)


class CarConnectivityErrors(Enum):
    SUCCESS = 0
    ATTRIBUTE_NOT_CHANGEABLE = -1
    MESSAGE_NOT_UNDERSTOOD = -2
    INTERVAL_NOT_A_NUMBER = -3
    INTERVAL_TOO_SMALL = -4
    INTERVAL_TOO_LARGE = -5
    RETRIEVAL_FAILED = -6
    API_COMPATIBILITY = -7
    AUTHENTIFICATION = -8
    SET_FORMAT = -9
    SET_ERROR = -10


class PictureFormat(Enum):
    TXT = 'txt'
    PNG = 'png'

    def __str__(self):
        return self.value
