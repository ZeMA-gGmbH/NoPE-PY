import socketio
from .EventCommunicationInterface import EventCommunicationInterface
from ...logger import define_nope_logger
from ...observables import NopeObservable


class SocketIoEmitter:

    def __init__(self, uri: str, logger='info'):
        # Define the URI
        self.uri = uri
        self.uri = self.uri if self.uri.startswith('http://') else 'http://' + self.uri

        self.logger = define_nope_logger(logger, "core.mirror.io")

        self._client = socketio.Client()
        self._client.connect(self.uri)

        self.connected = NopeObservable()
        self.connected.set_content(False)

        def on_connect():
            self.connected.set_content(True)

        def on_disconnect():
            self.connected.set_content(False)

        self._client.on("connect", on_connect)
        self._client.on("disconnect", on_disconnect())

    def on(self, event_name: str, cb):
        self._client.on(event_name, cb)

    def off(self, event_name: str, cb):
        pass

    def emit(self, event_name: str, data):
        self._client.emit(event_name, data)

    def close(self):
        self._client.disconnect()


class IoSocketClientLayer(EventCommunicationInterface):

    def __init__(self, uri, logger='info'):
        client = SocketIoEmitter(uri, logger)
        super().__init__(client)
