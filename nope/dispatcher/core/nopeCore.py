#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from nope.dispatcher.connectivityManager import NopeConnectivityManager
from nope.dispatcher.instanceManager import NopeInstanceManager
from nope.dispatcher.rpcManager import generateSelector, NopeRpcManager
from nope.helpers import ensureDottedAccess, generateId, EXECUTOR, Promise
from nope.logger import defineNopeLogger
from nope.observable import NopeObservable
from nope.pubSub import DataPubSubSystem, PubSubSystem


class NopeCore:

    def __init__(self, _options, id=None):

        _options = ensureDottedAccess(_options)

        def forwardEvent(item, rest):
            if item.sender != rcvExternally:
                EXECUTOR.callParallel(
                    self.communicator.emit,
                    'event',
                    ensureDottedAccess({
                        **item,
                        'sender': self._id
                    })
                )

        def forwardData(item, rest):
            if item.sender != rcvExternally:
                EXECUTOR.callParallel(
                    self.communicator.emit,
                    'dataChanged',
                    ensureDottedAccess({
                        **item,
                        'sender': self._id
                    })
                )

        def isReady(_):
            return self.connectivityManager.ready.getContent() \
                and self.rpcManager.ready.getContent() \
                and self.instanceManager.ready.getContent()

        def onEvent(msg):
            msg = ensureDottedAccess(msg)
            if msg.sender != self._id:
                data = msg.get("data")
                path = msg.get("path")
                msg.sender = rcvExternally
                self.eventDistributor.emit(path, data, msg)

        def onData(msg):
            msg = ensureDottedAccess(msg)
            if msg.sender != self._id:
                data = msg.get("data")
                name = msg.get("path")
                msg.sender = rcvExternally
                self.dataDistributor.pushData(name, data, msg)

        self._options = _options
        self._id = id
        self._disposed = EXECUTOR.generatePromise()

        self.communicator = _options.communicator

        if self._id is None:
            if _options.id:
                self._id = _options.id
            else:
                self._id = generateId()

        self.logger = defineNopeLogger(_options.logger, 'core')
        if self.logger:
            self.logger.info('setting up sub-systems.')

        self.eventDistributor = PubSubSystem()
        self.eventDistributor.id = self._id
        self.dataDistributor = DataPubSubSystem()
        self.dataDistributor.id = self._id

        defaultSelector = generateSelector(
            _options.get("defaultSelector", "first"), self)

        self.connectivityManager = NopeConnectivityManager(
            _options,
            self._id
        )
        self.rpcManager = NopeRpcManager(
            _options,
            defaultSelector,
            self._id,
            self.connectivityManager
        )
        self.instanceManager = NopeInstanceManager(
            _options,
            defaultSelector,
            self._id,
            self.connectivityManager,
            self.rpcManager,
            self
        )

        self.ready = NopeObservable()

        self.ready.getter = isReady
        rcvExternally = generateId()

        EXECUTOR.callParallel(
            self.communicator.on,
            'event',
            onEvent
        )

        self.eventDistributor.onIncrementalDataChange.subscribe(
            forwardEvent)

        EXECUTOR.callParallel(
            self.communicator.on,
            'dataChanged',
            onData
        )

        self.dataDistributor.onIncrementalDataChange.subscribe(
            forwardData)

        # Forward the Ready items.
        self.connectivityManager.ready.subscribe(
            lambda *args: self.ready.forcePublish())
        self.rpcManager.ready.subscribe(
            lambda *args: self.ready.forcePublish())
        self.instanceManager.ready.subscribe(
            lambda *args: self.ready.forcePublish())

        self.disposing = False

    @property
    def id(self):
        return self._id

    async def dispose(self):
        self.disposing = True
        self.ready.dispose()

        if self.logger:
            self.logger.warn('Removing Dispatcher. Shutting down.')

        await self.eventDistributor.dispose()
        await self.dataDistributor.dispose()
        await self.connectivityManager.dispose()
        await self.rpcManager.dispose()
        await self.instanceManager.dispose()

        if not self._disposed.cancelled() and not self._disposed.done():
            self._disposed.set_result(True)

    async def runEndless(self):
        await self._disposed
