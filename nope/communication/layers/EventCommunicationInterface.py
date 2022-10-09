from ...helpers import Emitter, generateId
from ...observable import NopeObservable


class EventCommunicationInterface:

    def __init__(self, emitter, logger=None, receivesOwnMessages=True):
        self._emitter = emitter if emitter is not None else Emitter()
        self._logger = logger
        self.receivesOwnMessages = receivesOwnMessages
        self.connected = NopeObservable()
        self.connected.setContent(True)
        self.id = generateId()

    async def on(self, eventName: str, cb):
        self._emitter.on(eventName, cb)

        if eventName != 'statusChanged' and self._logger:
            def loggingCallback(*args):
                self._logger.debug('received', "'" + eventName + "'", *args)

            self._emitter.on(eventName, loggingCallback)

    async def emit(self, eventName: str, data):
        self._emitter.emit(eventName, data)

    async def dispose(self):
        self._emitter.close()

    def detailListeners(self, t, listeners):
        raise Exception('Method not implemented.')
