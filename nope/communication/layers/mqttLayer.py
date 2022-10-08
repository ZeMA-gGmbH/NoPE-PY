import json
from logging import Logger

import paho.mqtt.client as mqtt
from socket import gethostname
from ...helpers import replace_all, generate_id, format_exception, SPLITCHAR
from ...logger import get_logger, DEBUG, INFO
from ...observable import NopeObservable

HOSTNAME = gethostname()


def mqtt_match(subscription: str, offered: str):
    # Adapt the subscription and offered element to use the correct split char.
    subscription = replace_all(subscription, SPLITCHAR, '/')
    offered = replace_all(offered, SPLITCHAR, '/')

    # Perform the original method.
    res = mqtt.topic_matches_sub(subscription, offered)
    if res:
        return res

    if (len(offered.split('/')) > len(subscription.split('/'))) and subscription.index('+') == 1:
        # Adapt the offered Topic, that is max as long as the subscription
        offered = ('/').join(offered.split('/')[0:len(subscription.split('/'))])

        # Now we will use our default matcher again
        res = mqtt.topic_matches_sub(subscription, offered)

    elif (len(offered.split('/')) < len(subscription.split('/'))) and subscription.index('+') == 1:
        # Adapt the subscription Topic, that is max as long as the offered one
        subscription = ('/').join(subscription.split('/')[0:len(offered.split('/'))])

        # Now we will use our default matcher again
        res = mqtt.topic_matches_sub(subscription, offered)
    return res


class MQTTLayer:

    def __init__(self, uri, logger=INFO, pre_topic=HOSTNAME, qos=2, forward_to_custom_topics=True):

        self.uri = uri
        self.pre_topic = pre_topic
        self.qos = qos
        self.forward_to_custom_topics = forward_to_custom_topics
        self.uri = self.uri if self.uri.starts_with('mqtt://') else 'mqtt://' + self.uri
        self.connected = NopeObservable()
        self.connected.set_content(False)
        self._cbs = dict()
        self.logger: Logger = get_logger(logger, 'core.layer.mqtt')
        self.consider_connection = True
        self.allow_service_redundancy = False
        self._id = generate_id()
        self.receives_own_messages = True

        # Create a mqtt client
        self.client = mqtt.Client(self.id, clean_session=False)

        # Create a handler for mqtt.
        def on_connect(*args, **kwargs):
            self.connected.set_content(True)

        def on_disconnect(*args, **kwargs):
            self.connected.set_content(False)

        def on_message(client, user_data, msg):
            # call the messages
            self._on_message(msg.topic, msg.payload.decode())

        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message

        # Extract the Host and the Port based on the URI.
        _host = self.uri[len('mqtt://'):].split(":")[0]
        _port = self.uri[len('mqtt://'):].split(":")[1]

        self.client.connect(_host, int(_port))

        self.client.loop_start()

    @property
    def id(self):
        return self._id

    def _on(self, topic: str, callback):

        _topic = self._adapt_topic(topic)

        if _topic not in self._cbs:
            self._cbs[_topic] = set()
            self._logger.info("subscribing: " + _topic)
            self.client.subscribe(_topic, qos=self.qos)

        self._cbs[_topic].add(callback)

    def _off(self, topic: str, callback):
        """ Removes a callback from the item"""

        _topic = self._adapt_topic(topic)

        if _topic in self._cbs:
            self._cbs[_topic].remove(callback)

            if len(self._cbs[_topic]) == 0:
                self._logger.info("unsubscribing: " + _topic)
                self.client.unsubscribe(_topic)

    def _on_message(self, topic: str, content):

        try:
            # the parsed data
            data = json.loads(content)

            for subscription in self._cbs:
                if mqtt_match(subscription, topic):
                    if self.logger:
                        self.logger.debug(f'received message on "{topic}" with content={data}')

                    for cb in self._cbs[subscription]:
                        # perform the callback
                        cb(data)

        except Exception as E:
            self._logger.error("Something went wrong during handling: '" + topic + "'. That shouldn't be the case")
            self._logger.error(format_exception(E))

    def _emit(self, topic: str, data):

        _topic = self._adapt_topic()

        if not (_topic.startswith(HOSTNAME + "/nope/status_changed")):
            self._logger.debug("emitting on " + _topic)
        self.client.publish(_topic, json.dumps(data), qos=self.qos)

    async def on(self, event_name: str, cb):
        return self._on(f'+/nope/{event_name}', cb)

    async def emit(self, event_name: str, data):
        self._emit(f'{self.pre_topic}/nope/{event_name}', data)

        if self.forward_to_custom_topics:
            if event_name == 'DataChanged':
                topic = data.path
                topic = self._adapt_topic(topic)
                await self.emit(topic, data.data)

            elif event_name == 'Event':
                topic = data.path
                topic = self._adapt_topic(topic)
                await self.emit(topic, data.data)

            elif event_name == 'RpcRequest':
                topic = data.function_id
                topic = self._adapt_topic(topic)
                await self.emit(topic, data.params)

    def _adapt_topic(self, topic: str):
        return replace_all(topic, SPLITCHAR, '/')

    async def on(self, topic, callback):
        return self.on(topic, callback)

    async def off(self, topic, callback):
        return self.off(topic, callback)

    async def dispose(self):
        """ Kills the connection
        """
        self.client.disconnect()
