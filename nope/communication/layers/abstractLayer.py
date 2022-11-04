from nope.helpers import generateId
from nope.logger import defineNopeLogger
from nope.observable import NopeObservable


class AbstractLayer:

    def __init__(self, uri: str, logger='info'):
        # Define the URI
        self.id = generateId()
        self.receivesOwnMessages = False

        self._logger = defineNopeLogger(logger, "core.mirror.io")

        self.connected = NopeObservable()
        self.connected.setContent(False)

    async def on(self, eventName: str, cb):
        raise Exception("Not implemented")

    async def off(self, eventName: str, cb):
        raise Exception("Not implemented")

    async def emit(self, eventName: str, data):
        raise Exception("Not implemented")

    async def dispose(self):
        raise Exception("Not implemented")

    def detailListeners(self, t, listeners):
        raise Exception("Not implemented")
