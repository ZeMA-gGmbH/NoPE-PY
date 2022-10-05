from ..helpers import Emitter, generate_id, DottedDict
from ..logger import define_nope_logger
from ..observable import NopeObservable
import asyncio


class Bridge:

    def __init__(self, _id=generate_id(), logger=False):

        def getter(stored_value):
            for data in self.layers.values():
                if (data.consider_connection and not data.layer.connected.
                        get_content()):
                    return False
            return True

        self.consider_connection = True
        self.allows_service_redundancy = False
        self.internal_emitter = Emitter()
        self.callbacks = dict()
        self.layers = dict()
        self._id = _id
        self.logger = define_nope_logger(logger, 'nope.bridge')
        self.use_internal_emitter = True

        self.connected = NopeObservable()
        self.connected.set_content(False)
        self.connected.getter = getter

    @property
    def receives_own_messages(self):
        for layer in self.layers.values():
            if not layer.layer.receives_own_messages:
                return False
        return True

    @property
    def id(self):
        return self._id

    async def on(self, event_name: str, cb):
        return self._on(event_name, cb)

    async def emit(self, event_name: str, data):
        return self._emit(event_name, None, data)

    def detail_listeners(self, t, listeners):
        pass

    async def dispose(self):
        for item in self.layers.values():
            await item.layer.dispose()

    def check_internal_emitter(self):
        self.use_internal_emitter = True
        for layer in self.layers.values():
            if layer.layer.receives_own_messages:
                self.use_internal_emitter = False
                break

    def _subscribe_to_callback(self, layer, event, forward_data):

        def adapted_callback(data):
            if forward_data:
                self._emit(event, layer, data)
            else:
                self.internal_emitter.emit(event, data)

        asyncio.ensure_future(layer.on(event, adapted_callback))

    def _on(self, event, cb):

        # if required we will add a logger for the events.
        if self.logger and event != 'StatusChanged':
            def debug_callback(data):
                self.logger.debug('received', event, data)
                self.logger.debug('subscribe to', event)

            self.internal_emitter.on(event, debug_callback)

        self.internal_emitter.on(event, cb)

        # We now store the callback.
        if event not in self.callbacks:
            self.callbacks[event] = [cb]
        else:
            self.callbacks[event].append(cb)

        # Now we try to add the callback to the connected layers.
        for data in self.layers.values():
            if data.layer.connected.get_content():
                self._subscribe_to_callback(data.layer, event, data.forward_data)

    def _emit(self, event, to_exclude, data_to_send=None, force=False):
        if self.logger and event != 'StatusChanged':
            self.logger.debug(f'emitting {str(event)} {str(data_to_send)}')
        if self.use_internal_emitter or force:
            self.internal_emitter.emit(event, data_to_send)

        for data in self.layers.values():
            if data.layer != to_exclude and data.layer.connected.get_content():

                def callback_4(error):
                    if self.logger:
                        self.logger.error('failed to emit the event "${event}"')
                        self.logger.error(error)

                data.layer.emit(event, data_to_send).catch(callback_4)

    async def add_communication_layer(self, layer, forward_data=False, consider_connection=False):
        if layer.id not in self.layers:

            def on_connected():
                self.connected.force_publish()

            self.layers[layer.id] = DottedDict({
                'layer': layer,
                'consider_connection': consider_connection,
                'forward_data': forward_data
            })
            layer.connected.subscribe(on_connected)

            await layer.connected.wait_for()

            for iter_item in self.callbacks.items():
                event = iter_item[0]
                cbs = iter_item[1]
                for callback in cbs:
                    layer.on(event, callback)
                    self.check_internal_emitter()

    async def remove_communication_layer(self, layer):
        if layer.id in self.layers:
            self.layers.pop(layer.id)
            self.check_internal_emitter()
