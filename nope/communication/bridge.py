from ..helpers import Emitter, generate_id, keys_to_camel_nested, format_exception, keys_to_snake_nested, ensure_dotted_dict, snake_to_camel, camel_to_snake, path_to_camel_case, path_to_snake_case
from ..logger import define_nope_logger
from ..observable import NopeObservable
import asyncio


class Bridge:

    def __init__(self, _id=generate_id(), logger=False):

        def getter(stored_value):
            for data in self._layers.values():
                if (data.consider_connection and not data.layer.connected.
                        get_content()):
                    return False
            return True

        self.consider_connection = True
        self.allows_service_redundancy = False
        self._internal_emitter = Emitter()
        self._callbacks = dict()
        self._layers = dict()
        self._id = _id
        self._logger = define_nope_logger(logger, 'nope.bridge')
        self._use_internal_emitter = True

        self.connected = NopeObservable()
        self.connected.set_content(False)
        self.connected.getter = getter


    @property
    def receives_own_messages(self):
        for layer in self._layers.values():
            if not layer.layer.receives_own_messages:
                return False
        return True

    @property
    def id(self):
        return self._id

    async def on(self, event_name: str, cb):

        def convert_data(data):
            if len(self._layers) == 0:
                return cb(data)
            adapted_data = keys_to_snake_nested(data)
            return cb(adapted_data)

        return self._on(path_to_camel_case(event_name), convert_data)

    async def emit(self, event_name: str, data):

        event_name_to_use = path_to_camel_case(event_name)

        if len(self._layers) == 0:
            return self._emit(event_name_to_use, None, ensure_dotted_dict(data))

        try:
            adapted_data = keys_to_camel_nested(data)
            return self._emit(event_name_to_use, None, adapted_data)
        except Exception as error:
            if self._logger:
                self._logger.error("Failed to parse the data")
                self._logger.error(format_exception(error))
            else:
                print(format_exception(error))

    def detail_listeners(self, t, listeners):
        pass

    async def dispose(self):
        for item in self._layers.values():
            await item.layer.dispose()

    def check_internal_emitter(self):
        self._use_internal_emitter = True
        for layer in self._layers.values():
            if layer.layer.receives_own_messages:
                self._use_internal_emitter = False
                break

    def _subscribe_to_callback(self, layer, event, forward_data):

        def adapted_callback(data):
            if forward_data:
                self._emit(event, layer, data)
            else:
                self._internal_emitter.emit(event, data)

        asyncio.ensure_future(layer.on(event, adapted_callback))

    def _on(self, event, cb):

        # if required we will add a logger for the events.
        if self._logger and event != 'StatusChanged':
            def debug_callback(data):
                self._logger.debug('received', event, data)
                self._logger.debug('subscribe to', event)

            self._internal_emitter.on(event, debug_callback)

        self._internal_emitter.on(event, cb)

        # We now store the callback.
        if event not in self._callbacks:
            self._callbacks[event] = [cb]
        else:
            self._callbacks[event].append(cb)

        # Now we try to add the callback to the connected layers.
        for data in self._layers.values():
            if data.layer.connected.get_content():
                self._subscribe_to_callback(data.layer, event, data.forward_data)

    def _emit(self, event, to_exclude, data_to_send=None, force=False):
        if self._logger and event != 'StatusChanged':
            self._logger.debug(f'emitting {str(event)} {str(data_to_send)}')
        if self._use_internal_emitter or force:
            self._internal_emitter.emit(event, data_to_send)

        for data in self._layers.values():
            if data.layer != to_exclude and data.layer.connected.get_content():

                async def emit_on_layer():
                    try:
                        await data.layer.emit(event, data_to_send)
                    except Exception as error:
                        if self._logger:
                            self._logger.error('failed to emit the event "${event}"')
                            self._logger.error(error)
                        else:
                            print(format_exception(error))

                asyncio.ensure_future(emit_on_layer())

    async def add_communication_layer(self, layer, forward_data=False, consider_connection=False):
        if layer.id not in self._layers:

            def on_connected(*args):
                self.connected.force_publish()

            self._layers[layer.id] = ensure_dotted_dict({
                'layer': layer,
                'consider_connection': consider_connection,
                'forward_data': forward_data
            })
            layer.connected.subscribe(on_connected)

            await layer.connected.wait_for()

            for iter_item in self._callbacks.items():
                event = iter_item[0]
                cbs = iter_item[1]
                for callback in cbs:
                    layer.on(event, callback)
                    self.check_internal_emitter()

    async def remove_communication_layer(self, layer):
        if layer.id in self._layers:
            self._layers.pop(layer.id)
            self.check_internal_emitter()
