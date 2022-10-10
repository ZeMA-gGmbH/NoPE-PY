import json
from logging import Logger

import paho.mqtt.client as mqtt
from socket import gethostname
from ...helpers import replaceAll, generateId, formatException, SPLITCHAR
from ...logger import getNopeLogger, DEBUG, INFO
from ...observable import NopeObservable

HOSTNAME = gethostname()


def mqttMatch(subscription: str, offered: str):
    # Adapt the subscription and offered element to use the correct split char.
    subscription = replaceAll(subscription, SPLITCHAR, '/')
    offered = replaceAll(offered, SPLITCHAR, '/')

    # Perform the original method.
    res = mqtt.topic_matches_sub(subscription, offered)
    if res:
        return res

    if (len(offered.split('/')) > len(subscription.split('/'))
        ) and subscription.index('+') == 1:
        # Adapt the offered Topic, that is max as long as the subscription
        offered = ('/').join(offered.split('/')
                             [0:len(subscription.split('/'))])

        # Now we will use our default matcher again
        res = mqtt.topic_matches_sub(subscription, offered)

    elif (len(offered.split('/')) < len(subscription.split('/'))) and subscription.index('+') == 1:
        # Adapt the subscription Topic, that is max as long as the offered one
        subscription = ('/').join(subscription.split('/')
                                  [0:len(offered.split('/'))])

        # Now we will use our default matcher again
        res = mqtt.topic_matches_sub(subscription, offered)
    return res


class MQTTLayer:

    def __init__(self, uri, logger=INFO, preTopic=HOSTNAME,
                 qos=2, forwardToCustomTopics=True):

        self.uri = uri
        self.preTopic = preTopic
        self.qos = qos
        self.forwardToCustomTopics = forwardToCustomTopics
        self.uri = self.uri if self.uri.starts_with(
            'mqtt://') else 'mqtt://' + self.uri
        self.connected = NopeObservable()
        self.connected.setContent(False)
        self._cbs = dict()
        self.logger: Logger = getNopeLogger(logger, 'core.layer.mqtt')
        self.considerConnection = True
        self.allowServiceRedundancy = False
        self._id = generateId()
        self.receivesOwnMessages = True

        # Create a mqtt client
        self._client = mqtt.Client(self.id, clean_session=False)

        # Create a handler for mqtt.
        def onConnect(*args, **kwargs):
            self.connected.setContent(True)

        def onDisconnect(*args, **kwargs):
            self.connected.setContent(False)

        def onMessage(client, user_data, msg):
            # call the messages
            self._onMessage(msg.topic, msg.payload.decode())

        self._client.onConnect = onConnect
        self._client.onDisconnect = onDisconnect
        self._client.onMessage = onMessage

        # Extract the Host and the Port based on the URI.
        _host = self.uri[len('mqtt://'):].split(":")[0]
        _port = self.uri[len('mqtt://'):].split(":")[1]

        self._client.connect(_host, int(_port))

        self._client.loop_start()

    @property
    def id(self):
        return self._id

    def _on(self, topic: str, callback):

        _topic = self._adaptTopic(topic)

        if _topic not in self._cbs:
            self._cbs[_topic] = set()
            self._logger.info("subscribing: " + _topic)
            self._client.subscribe(_topic, qos=self.qos)

        self._cbs[_topic].add(callback)

    def _off(self, topic: str, callback):
        """ Removes a callback from the item"""

        _topic = self._adaptTopic(topic)

        if _topic in self._cbs:
            self._cbs[_topic].remove(callback)

            if len(self._cbs[_topic]) == 0:
                self._logger.info("unsubscribing: " + _topic)
                self._client.unsubscribe(_topic)

    def _onMessage(self, topic: str, content):

        try:
            # the parsed data
            data = json.loads(content)

            for subscription in self._cbs:
                if mqttMatch(subscription, topic):
                    if self.logger:
                        self.logger.debug(
                            f'received message on "{topic}" with content={data}')

                    for cb in self._cbs[subscription]:
                        # perform the callback
                        cb(data)

        except Exception as E:
            self._logger.error(
                "Something went wrong during handling: '" + topic + "'. That shouldn't be the case")
            self._logger.error(formatException(E))

    def _emit(self, topic: str, data):

        _topic = self._adaptTopic()

        if not (_topic.startswith(HOSTNAME + "/nope/statusChanged")):
            self._logger.debug("emitting on " + _topic)
        self._client.publish(_topic, json.dumps(data), qos=self.qos)

    async def _on(self, eventName: str, cb):
        return self._on(f'+/nope/{eventName}', cb)

    async def emit(self, eventName: str, data):
        self._emit(f'{self.preTopic}/nope/{eventName}', data)

        if self.forwardToCustomTopics:
            if eventName == 'DataChanged':
                topic = data.path
                topic = self._adaptTopic(topic)
                await self.emit(topic, data.data)

            elif eventName == 'Event':
                topic = data.path
                topic = self._adaptTopic(topic)
                await self.emit(topic, data.data)

            elif eventName == 'RpcRequest':
                topic = data.functionId
                topic = self._adaptTopic(topic)
                await self.emit(topic, data.params)

    def _adaptTopic(self, topic: str):
        return replaceAll(topic, SPLITCHAR, '/')

    async def on(self, topic, callback):
        return self._on(topic, callback)

    async def off(self, topic, callback):
        return self._off(topic, callback)

    async def dispose(self):
        """ Kills the connection
        """
        self._client.disconnect()
