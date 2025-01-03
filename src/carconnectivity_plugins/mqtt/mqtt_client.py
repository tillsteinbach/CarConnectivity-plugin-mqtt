"""Module implements the MQTT client."""
from __future__ import annotations
from typing import TYPE_CHECKING

import logging

from enum import Enum
from datetime import datetime, timedelta, tzinfo

from paho.mqtt.client import Client
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.properties import Properties
from paho.mqtt.enums import MQTTProtocolVersion, CallbackAPIVersion, MQTTErrorCode

from carconnectivity import errors
from carconnectivity import attributes
from carconnectivity import observable

if TYPE_CHECKING:
    from typing import Optional, Literal, List

    from carconnectivity.carconnectivity import CarConnectivity


LOG = logging.getLogger("carconnectivity.plugins.mqtt")


class CarConnectivityMQTTClient(Client):  # pylint: disable=too-many-instance-attributes
    """
    MQTT client for car connectivity.
    """
    def __init__(self, car_connectivity: CarConnectivity, plugin_id: str, client_id: Optional[str] = None,
                 protocol: MQTTProtocolVersion = MQTTProtocolVersion.MQTTv311,
                 transport: Literal["tcp", "websockets", "unix"] = 'tcp',
                 prefix: Optional[str] = 'carconnectivity/0', ignore_for: int = 0, republish_on_update=False, retain_on_disconnect=False,
                 topic_filter_regex=None, convert_timezone=None, time_format=None, with_raw_json_topic=False) -> None:
        super().__init__(callback_api_version=CallbackAPIVersion.VERSION2, client_id=client_id, transport=transport, protocol=protocol)
        self.car_connectivity: CarConnectivity = car_connectivity
        self.plugin_id: str = plugin_id
        self.prefix: str = prefix or 'carconnectivity/0'
        self.has_error: Optional[bool] = None
        self.ignore_for: int = ignore_for
        self.last_subscribe: Optional[datetime] = None
        self.topics: List[str] = []
        self.topics_changed = False
        self.writeable_topics: List[str] = []
        self.writeable_topics_changed = False
        self.republish_on_update: bool = republish_on_update
        self.retain_on_disconnect: bool = retain_on_disconnect
        self.topic_filter_regex = topic_filter_regex
        self.convert_timezone: Optional[tzinfo] = convert_timezone
        self.time_format: Optional[str] = time_format
        self.has_changes = False
        self.with_raw_json_topic = with_raw_json_topic

        self.on_connect = self._on_connect_callback
        self.on_message = self._on_message_callback
        self.on_disconnect = self._on_disconnect_callback
        self.on_subscribe = self._on_subscribe_callback

        if self.republish_on_update:
            flags = (observable.Observable.ObserverEvent.UPDATED
                     | observable.Observable.ObserverEvent.ENABLED
                     | observable.Observable.ObserverEvent.DISABLED)
        else:
            flags = (observable.Observable.ObserverEvent.VALUE_CHANGED
                     | observable.Observable.ObserverEvent.ENABLED
                     | observable.Observable.ObserverEvent.DISABLED)
        self.car_connectivity.add_observer(self._on_carconnectivity_event, flags, priority=observable.Observable.ObserverPriority.USER_MID)

        self.will_set(topic=f'{self.prefix}/plugins/{self.plugin_id}/connected', qos=1, retain=True, payload=False)

    def _add_topic(self, topic: str, writeable: bool = False) -> None:
        """
        Add a topic to the list of topics and writeable topics.

        Args:
            topic (str): The topic to be added.
            writeable (bool, optional): If True, the topic will be added to the list of writeable topics. Defaults to False.

        Returns:
            None
        """
        if writeable:
            if topic not in self.writeable_topics:
                self.writeable_topics.append(topic)
                self.writeable_topics.sort()
                self.writeable_topics_changed = True
        else:
            if topic not in self.topics:
                self.topics.append(topic)
                self.topics.sort()
                self.topics_changed = True

    def publish_topics(self) -> None:
        """
        Publish the list of topics and writeable topics to the broker.
        Will only publish if the list of topics has changed.

        Args:
            None

        Returns:
            None
        """
        # Publish the list of topics if it has changed
        if self.topics_changed:
            # Topic to publish topics to
            topicstopic = f'{self.prefix}/plugins/{self.plugin_id}/topics'
            # If this topic itself is not in the list of topics, add it
            if topicstopic not in self.topics:
                self._add_topic(topicstopic)
            content = ',\n'.join(self.topics)
            self.publish(topic=topicstopic, qos=1, retain=True, payload=content)
            self.topics_changed = False

        # Publish the list of writeable topics if it has changed
        if self.writeable_topics_changed:
            # Topic to publish writable topics to
            writeabletopicstopic = f'{self.prefix}/plugins/{self.plugin_id}/writeable_topics'
            # If this topic itself is not in the list of topics, add it
            if writeabletopicstopic not in self.topics:
                self._add_topic(writeabletopicstopic)
            content = ',\n'.join(self.writeable_topics)
            self.publish(topic=writeabletopicstopic, qos=1, retain=True, payload=content)
            self.writeable_topics_changed = False

    def disconnect(self, reasoncode: Optional[ReasonCode] = None, properties: Optional[Properties] = None) -> MQTTErrorCode:
        """
        Disconnect from the MQTT broker while setting connected topic to false.

        Args:
            reasoncode (int, optional): The reason code for the disconnect. Defaults to None.
            properties (dict, optional): The properties for the disconnect. Defaults to None.

        Returns:
            paho.mqtt.client.MQTTErrorCode: The result of the disconnect
        """
        try:
            disconect_publish = self.publish(topic=f'{self.prefix}/plugins/{self.plugin_id}/connected', qos=1, retain=True, payload=False)
            disconect_publish.wait_for_publish()
        except RuntimeError:
            pass
        return super().disconnect(reasoncode, properties)

    def _on_carconnectivity_event(self, element, flags) -> None:
        """
        Callback for car connectivity events.
        On enable of an attribute it will add the topic to the list of topics.
        for changeable Attributes it will subscribe to the topic and add it to the list of writeable topics.

        On value change it will publish the new value to the topic.
        if republish_on_update is set it will also publish the value on update.

        On disable of an attribute it will publish an empty message to the topic to remove it.

        Args:
            element (Observable): The element that triggered the event.
            flags (Observable.ObserverEvent): The event flags.

        Returns:
            None
        """
        self.has_changes = True
        topic = f'{self.prefix}{element.get_absolute_path()}'
        # Skip topics that are filtered
        if self.topic_filter_regex is not None and self.topic_filter_regex.match(topic):
            return

        # An attribute is enabled
        if flags & observable.Observable.ObserverEvent.ENABLED:
            # For ChangeableAttributes, subscribe to the topic and add it to the list of writeable topics
            if isinstance(element, attributes.ChangeableAttribute):
                topic = topic + '_writetopic'
                LOG.debug('Subscribe for attribute %s%s', self.prefix, element.get_absolute_path())
                self.subscribe(topic, qos=1)
                if topic not in self.topics:
                    self._add_topic(topic, writeable=True)
            # For GenericAttributes, add it to the list of topics
            elif isinstance(element, attributes.GenericAttribute):
                if topic not in self.topics:
                    self._add_topic(topic)
        # If the value of an attribute has changed or the attribute was updated and republish_on_update is set publish the new value
        elif (flags & observable.Observable.ObserverEvent.VALUE_CHANGED) \
                or (self.republish_on_update and (flags & observable.Observable.ObserverEvent.UPDATED)):
            converted_value = self.convert_value(element.value)
            LOG.debug('%s%s, value changed: new value is: %s', self.prefix, element.get_absolute_path(), converted_value)
            # We publish with retain=True to make sure that the value is there even if no client is connected to the broker
            self.publish(topic=f'{self.prefix}{element.get_absolute_path()}', qos=1, retain=True, payload=converted_value)
        # When an attribute is disabled and retain_on_disconnect is not set, publish an empty message to the topic to remove it
        elif flags & observable.Observable.ObserverEvent.DISABLED and not self.retain_on_disconnect \
                and isinstance(element, attributes.GenericAttribute):
            LOG.debug('%s%s, value is diabled', self.prefix, element.get_absolute_path())
            self.publish(topic=f'{self.prefix}{element.get_absolute_path()}', qos=1, retain=True, payload='')

    def convert_value(self, value):
        """
        Convert the value to a format that is usable in MQTT.

        Args:
            value: The value to convert.

        Returns:
            str: The converted value.
        """
        if isinstance(value, (str, int, float)) or value is None:
            return value
        if isinstance(value, (list)):
            return ', '.join([str(item.value) if isinstance(item, Enum) else str(item) for item in value])
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            converted_time: datetime = value
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

    def _set_error(self, code: Optional[CarConnectivityErrors] = None, message: str = '') -> None:
        """
        Set an error code and message.

        Args:
            code (CarConnectivityErrors, optional): The error code. Defaults to None.
            message (str, optional): The error message. Defaults to ''.

        Returns:
            None
        """
        if code is None:
            code = CarConnectivityErrors.SUCCESS
        if code != CarConnectivityErrors.SUCCESS or message != '' or self.has_error is None or self.has_error:
            topic = f'{self.prefix}/plugins/{self.plugin_id}/error/code'
            self.publish(topic=topic, qos=1, retain=False, payload=code.value)
            if topic not in self.topics:
                self._add_topic(topic)
            topic = f'{self.prefix}/plugins/{self.plugin_id}/error/message'
            self.publish(topic=topic, qos=1, retain=False, payload=message)
            if topic not in self.topics:
                self._add_topic(topic)
        if code != CarConnectivityErrors.SUCCESS:
            self.has_error = True
        else:
            self.has_error = False

    def _on_connect_callback(self, mqttc, obj, flags, reason_code, properties) -> None:  # noqa: C901  # pylint: disable=too-many-branches
        """
        Callback for connection to the MQTT broker.
        On successful connection it will subscribe to the force update topic and all writeable topics.
        It will also publish all topics that are already there.

        Args:
            mqttc (paho.mqtt.client.Client): unused
            obj (Any): unused
            flags (Any): unused
            reason_code (int): unused
            properties (Any): unused

        Returns:
            None
        """
        del mqttc  # unused
        del obj  # unused
        del flags  # unused
        del properties
        # reason_code 0 means success
        if reason_code == 0:
            LOG.info('Connected to MQTT broker')
            # subsribe to the force update topic
            force_update_topic: str = f'{self.prefix}/plugins/{self.plugin_id}/carconnectivityForceUpdate_writetopic'
            self.subscribe(force_update_topic, qos=2)
            if force_update_topic not in self.topics:
                self._add_topic(force_update_topic, writeable=True)

            # Subscribe again to all writeable topics after a reconnect
            for writeable_topic in self.writeable_topics:
                self.subscribe(writeable_topic, qos=1)

            # Handle topics that are already there to prevent clients from missing them
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
                        # We publish with retain=True to make sure that the value is there even if no client is connected to the broker
                        self.publish(topic=attribute_topic, qos=1, retain=True, payload=converted_value)
        # Handle different reason codes
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

    def _on_disconnect_callback(self, client, userdata, flags, reason_code, properties) -> None:  # noqa: C901  # pylint: disable=too-many-branches,no-self-use
        """
        Callback for disconnection from the MQTT broker.

        Args:
            client (paho.mqtt.client.Client): unused
            userdata (Any): unused
            flags (Any): unused
            reason_code (int): The reason for the disconnection
            properties (Any): unused

        Returns:
            None
        """
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

    def _on_subscribe_callback(self, mqttc, obj, mid, reason_codes, properties) -> None:
        """
        Callback for subscribing to a topic.

        Args:
            mqttc (paho.mqtt.client.Client): unused
            obj (Any): unused
            mid (int): message id
            reason_codes (List[int]): unused
            properties (Any): unused

        Returns:
            None
        """
        del mqttc  # unused
        del obj  # unused
        del properties  # unused
        if any(x in [0, 1, 2] for x in reason_codes):
            self.last_subscribe = datetime.now()
            LOG.debug('sucessfully subscribed to topic of id %d', mid)
        else:
            LOG.error('Subscribe was not successfull (%s)', ', '.join(reason_codes))

    def _on_message_callback(self, mqttc, obj, msg) -> None:  # noqa: C901
        """
        Callback for receiving a message from the MQTT broker.

        It will ignore empty messages and messages
        if ignore_for is set it will ignore messages that are within the ignore_for delta of the last subscribe. This helps to prevent
        receiving messages that are sent by the client itself and relayed by the broker due to the retain flag.

        If the message is a force update message it will trigger a fetch_all on the car connectivity object.

        If the message is a write message it will try to set the value of the attribute that is addressed in the message.
        If the attribute is not changeable it will set an error.
        If the attribute is not found it will set an error.
        If the value is not in the correct format it will set an error.
        If the value could not be set it will set an error.

        Args:
            mqttc (paho.mqtt.client.Client): unused
            obj (Any): unused
            msg (paho.mqtt.client.MQTTMessage): The message received from the broker.

        Returns:
            None
        """
        del mqttc  # unused
        del obj  # unused
        # Ignore messages that are within the ignore_for delta of the last subscribe if ignore_for is set
        if self.ignore_for > 0 and self.last_subscribe is not None and (datetime.now() - self.last_subscribe) < timedelta(seconds=self.ignore_for):
            LOG.info('ignoring message from broker as it is within "ignore-for" delta of %ds', self.ignore_for)
        # Ignore empty messages
        elif len(msg.payload) == 0:
            LOG.debug('ignoring empty message')
        # handle force upate message
        elif msg.topic == f'{self.prefix}/plugins/{self.plugin_id}/carconnectivityForceUpdate_writetopic':
            if msg.payload.lower() == b'True'.lower():
                LOG.info('Update triggered by MQTT message')
                self.publish(topic=f'{self.prefix}/plugins/{self.plugin_id}/carconnectivityForceUpdate', qos=2, payload=True)
                self.car_connectivity.fetch_all()
                self.publish(topic=f'{self.prefix}/plugins/{self.plugin_id}/carconnectivityForceUpdate', qos=2, payload=False)
        # handle any other message
        else:
            if msg.topic.startswith(self.prefix):
                address = msg.topic[len(self.prefix):]
                # message to _writetopic are for setting values
                if address.endswith('_writetopic'):
                    address = address[:-len('_writetopic')]

                    attribute = self.car_connectivity.get_by_path(address)
                    # Writing can be only to changeable attributes
                    if isinstance(attribute, attributes.ChangeableAttribute):
                        try:
                            # Set the value of the attribute
                            attribute.value = msg.payload.decode()
                            self._set_error(code=CarConnectivityErrors.SUCCESS)
                            LOG.debug('Successfully set value')
                        # If the value is not in the correct format set an error
                        except ValueError as value_error:
                            error_message: str = f'Error setting value: {value_error}'
                            self._set_error(code=CarConnectivityErrors.SET_FORMAT, message=error_message)
                            LOG.info(error_message)
                        # If the value could not be set set an error
                        except errors.SetterError as setter_error:
                            error_message = f'Error setting value: {setter_error}'
                            self._set_error(code=CarConnectivityErrors.SET_ERROR, message=error_message)
                            LOG.info(error_message)
                    # Set error when attribute is not found or not changeable
                    else:
                        error_message = f'Trying to change item that is not a changeable attribute {msg.topic}: {msg.payload}'
                        self._set_error(code=CarConnectivityErrors.MESSAGE_NOT_UNDERSTOOD, message=error_message)
                        LOG.error(error_message)
                # writing to non _writetopic topics is not allowed, give some hints in the error message
                else:
                    attribute = self.car_connectivity.get_by_path(address)
                    # If trying to set a value on a changeable attribute but not with the writeable topic
                    if isinstance(attribute, attributes.ChangeableAttribute):
                        error_message = f'Trying to change item on not writeable topic {msg.topic}: {msg.payload}, please use {msg.topic}_writetopic instead'
                        self._set_error(code=CarConnectivityErrors.MESSAGE_NOT_UNDERSTOOD, message=error_message)
                        LOG.error(error_message)
                    # Set error when attribute is not found or not changeable
                    else:
                        error_message = f'Trying to change item that is not a changeable attribute {msg.topic}: {msg.payload}'
                        self._set_error(code=CarConnectivityErrors.MESSAGE_NOT_UNDERSTOOD, message=error_message)
                        LOG.error(error_message)
            # Only react to messages that start with the prefix
            else:
                error_message = f'I don\'t understand message {msg.topic}: {msg.payload}'
                self._set_error(code=CarConnectivityErrors.ATTRIBUTE_NOT_CHANGEABLE, message=error_message)
                LOG.error(error_message)


class CarConnectivityErrors(Enum):
    """
    Enum for error codes.

    Attributes:
        SUCCESS: No error
        ATTRIBUTE_NOT_CHANGEABLE: Attribute is not changeable
        MESSAGE_NOT_UNDERSTOOD: Message not understood
        SET_FORMAT: Set format
        SET_ERROR: Set error
    """
    SUCCESS = 0
    ATTRIBUTE_NOT_CHANGEABLE = -1
    MESSAGE_NOT_UNDERSTOOD = -2
    SET_FORMAT = -3
    SET_ERROR = -4


class PictureFormat(Enum):
    """
    Enum for picture formats.

    Attributes:
        TXT: ASCII format
        PNG: PNG format
    """
    TXT = 'txt'
    PNG = 'png'

    def __str__(self):
        return self.value
