#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ...helpers import ensureDottedAccess, generateId
from ...logger import getNopeLogger
from ...observable import NopeObservable
from ...pubSub import DataPubSubSystem, PubSubSystem
from ..connectivityManager import NopeConnectivityManager


class NopeCore:

    def __init__(self, _options, _id=None):

        _options = ensureDottedAccess(_options)

        def forwardEvent(item):
            if item.sender != rcvExternally:
                self.communicator.emit('Event', ensureDottedAccess(
                    {**item, 'sender': self._id}))

        def forwardData(item):
            if item.sender != rcvExternally:
                self.communicator.emit('DataChanged', ensureDottedAccess(
                    {**item, 'sender': self._id}))

        def is_ready():
            return self.connectivityManager.ready.getContent(
            ) and self.rpcManager.ready.getContent() and self.instanceManager.ready.getContent()

        def on_event(msg):
            msg = ensureDottedAccess(msg)
            if msg.sender != self._id:
                data = msg.get("data")
                path = msg.get("path")
                msg.sender = rcvExternally
                self.eventDistributor.emit(path, data, msg)

        def on_data(msg):
            msg = ensureDottedAccess(msg)
            if msg.sender != self._id:
                data = msg.get("data")
                name = msg.get("path")
                msg.sender = rcvExternally
                self.dataDistributor.pushData(name, data, msg)

        self._options = _options
        self._id = _id

        self.communicator = _options.communicator

        if _id is None:
            if _options.id:
                self._id = _options.id
            else:
                self._id = generateId()

        self.logger = getNopeLogger(_options.logger, 'core.rpc-manager')
        self.logger.info('setting up sub-systems.')

        self.eventDistributor = PubSubSystem()
        self.dataDistributor = DataPubSubSystem()

        # TODO: Ab hier:

        defaultSelector = generateSelector(
            _options.get("defaultSelector", "first"), self)

        self.connectivityManager = NopeConnectivityManager(_options, self._id)
        self.rpcManager = nope_rpcManager(
            _options, defaultSelector, self._id, self.connectivityManager)
        self.instanceManager = nope_instanceManager(_options,
                                                    defaultSelector, self._id, self.
                                                    connectivityManager, self.rpcManager, self)

        # TODO: bishier!

        self.ready = NopeObservable()

        self.ready.getter = is_ready
        rcvExternally = generateId()

        self.communicator.on('Event', on_event)
        self.eventDistributor.onIncrementalDataChange.subscribe(
            forwardEvent)
        self.communicator.on('DataChanged', on_data)
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
