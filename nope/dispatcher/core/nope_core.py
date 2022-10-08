#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ...helpers import ensure_dotted_dict, generate_id
from ...logger import get_logger
from ...observable import NopeObservable
from ...pub_sub import DataPubSubSystem, PubSubSystem
from ..connectivity_manager import NopeConnectivityManager


class NopeCore:

    def __init__(self, _options, _id=None):

        _options = ensure_dotted_dict(_options)

        def forward_event(item):
            if item.sender != rcv_externally:
                self.communicator.emit('Event', ensure_dotted_dict(
                    {**item, 'sender': self._id}))

        def forward_data(item):
            if item.sender != rcv_externally:
                self.communicator.emit('DataChanged', ensure_dotted_dict(
                    {**item, 'sender': self._id}))

        def is_ready():
            return self.connectivity_manager.ready.get_content() and self.rpc_manager.ready.get_content() and self.instance_manager.ready.get_content()

        def on_event(msg):
            msg = ensure_dotted_dict(msg)
            if msg.sender != self._id:
                data = msg.get("data")
                path = msg.get("path")
                msg.sender = rcv_externally
                self.event_distributor.emit(path, data, msg)

        def on_data(msg):
            msg = ensure_dotted_dict(msg)
            if msg.sender != self._id:
                data = msg.get("data")
                name = msg.get("path")
                msg.sender = rcv_externally
                self.data_distributor.push_data(name, data, msg)

        self._options = _options
        self._id = _id

        self.communicator = _options.communicator

        if _id == None:
            if _options.id:
                self._id = _options.id
            else:
                self._id = generate_id()

        self.logger = get_logger(_options.logger, 'core.rpc-manager')
        self.logger.info('setting up sub-systems.')

        self.event_distributor = PubSubSystem()
        self.data_distributor = DataPubSubSystem()

        # TODO: Ab hier:

        default_selector = generate_selector(
            _options.get("default_selector", "first"), self)

        self.connectivity_manager = NopeConnectivityManager(_options, self._id)
        self.rpc_manager = nope_rpc_manager(
            _options, default_selector, self._id, self.connectivity_manager)
        self.instance_manager = nope_instance_manager(_options,
                                                      default_selector, self._id, self.
                                                      connectivity_manager, self.rpc_manager, self)


        # TODO: bishier!

        self.ready = NopeObservable()

        self.ready.getter = is_ready
        rcv_externally = generate_id()

        self.communicator.on('Event', on_event)
        self.event_distributor.on_incremental_data_change.subscribe(
            forward_event)
        self.communicator.on('DataChanged', on_data)
        self.data_distributor.on_incremental_data_change.subscribe(
            forward_data)

        # Forward the Ready items.
        self.connectivity_manager.ready.subscribe(
            lambda *args: self.ready.force_publish())
        self.rpc_manager.ready.subscribe(
            lambda *args: self.ready.force_publish())
        self.instance_manager.ready.subscribe(
            lambda *args: self.ready.force_publish())

        self.disposing = False

    async def dispose(self):
        self.disposing = True
        await self.ready.dispose()
        await self.event_distributor.dispose()
        await self.data_distributor.dispose()
        await self.connectivity_manager.dispose()
        await self.rpc_manager.dispose()
        await self.instance_manager.dispose()
