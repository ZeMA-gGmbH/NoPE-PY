import socketio
from .EventCommunicationInterface import EventCommunicationInterface
from ...logger import defineNopeLogger
from ...observable import NopeObservable


class SocketIoEmitter:

    def __init__(self, uri: str, logger='info'):
        # Define the URI
        self.uri = uri
        self.uri = self.uri if self.uri.startswith('http://') else 'http://' + self.uri

        self._logger = defineNopeLogger(logger, "core.mirror.io")

        self._client = socketio.Client()
        self._client.connect(self.uri)

        self.connected = NopeObservable()
        self.connected.setContent(False)

        def onConnect():
            self.connected.setContent(True)

        def onDisconnect():
            self.connected.setContent(False)

        self._client.on("connect", onConnect)
        self._client.on("disconnect", onDisconnect())

    def on(self, eventName: str, cb):
        self._client.on(eventName, cb)

    def off(self, eventName: str, cb):
        pass

    def emit(self, eventName: str, data):
        self._client.emit(eventName, data)

    def close(self):
        self._client.disconnect()


class IoSocketClientLayer(EventCommunicationInterface):

    def __init__(self, uri, logger='info'):
        client = SocketIoEmitter(uri, logger)
        super().__init__(client)
