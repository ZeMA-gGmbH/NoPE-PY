import asyncio

from ...helpers import getTimestamp, ensureDottedAccess, generateId, DottedDict, minOfArray, formatException, \
    EXECUTOR
from ...logger import defineNopeLogger
from ...merging import DictBasedMergeData
from ...observable import NopeObservable
from ...eventEmitter import NopeEventEmitter


class NopeTransportManager:

    def __init__(self, options, _id=None):

        options = ensureDottedAccess(options, False)

        self.options = options
        self._id = _id if _id is not None else generateId()

        self._communicator = options.communicator

        self._logger = defineNopeLogger(
            options.logger, 'core.connectivity-manager')

        self.ready = NopeObservable()
        self.ready.setContent(False)
        self.onTransportError = NopeEventEmitter()

        if self._logger:
            self._logger.info('core.connectivity-manager', self.id, 'is ready')

        # Dict containing the Messages, that have been send as key and containign the
        # still open respones (dispatcher ids) as set as value
        self._openMessages = {}

        self.reset()
        EXECUTOR.callParallel(self.init)

    @property
    def id(self):
        return self._id

    async def transformData(self, eventName, data):
        if eventName != "ackMessage":
            messageId = generateId()
            data["messageId"] = messageId

            # Store the Message

        return eventName, data, None

    async def init(self):

        self.ready.setContent(False)
        await self._communicator.connected.waitFor()

        def onAckMessage(msg):
            messageId = data.pop("messageId", None)
            if messageId and messageId in self._openMessages:
                self._openMessages[messageId].toReceive.delete(msg.get())

        await self._communicator.on('ackMessage', onAckMessage)

        if self._logger:
            self._logger.info('core.transport-manager',
                              self.id, 'initialized')

        self.ready.setContent(True)

    def reset(self):
        self._openMessages = dict()

    async def dispose(self, quiet=False):
        pass
