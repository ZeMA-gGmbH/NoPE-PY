#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ...helpers import ensureDottedAccess, generateId
from ...logger import getNopeLogger, defineNopeLogger
from ...observable import NopeObservable
from ...pubSub import DataPubSubSystem, PubSubSystem
from ..connectivityManager import NopeConnectivityManager
from ..rpcManager import generateSelector, NopeRpcManager
from ..instanceManager import generateAssignmentChecker, NopeInstanceManager


class NopeCore:

    def __init__(self, _options, id=None):

        _options = ensureDottedAccess(_options)

        def forwardEvent(item):
            if item.sender != rcvExternally:
                self.communicator.emit('Event', ensureDottedAccess(
                    {**item, 'sender': self._id}))

        def forwardData(item):
            if item.sender != rcvExternally:
                self.communicator.emit('DataChanged', ensureDottedAccess(
                    {**item, 'sender': self._id}))

        def isReady(_):
            return self.connectivityManager.ready.getContent(
            ) and self.rpcManager.ready.getContent() and self.instanceManager.ready.getContent()

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
        self.dataDistributor = DataPubSubSystem()

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

        self.communicator.on('Event', onEvent)
        self.eventDistributor.onIncrementalDataChange.subscribe(
            forwardEvent)
        self.communicator.on('DataChanged', onData)
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

    async def dispose(self):
        self.disposing = True
        await self.ready.dispose()
        await self.eventDistributor.dispose()
        await self.dataDistributor.dispose()
        await self.connectivityManager.dispose()
        await self.rpcManager.dispose()
        await self.instanceManager.dispose()
