from ..helpers import Emitter, generateId, keysToCamelNested, formatException, keysToSnakeNested, ensureDottedAccess, snakeToCamel, camelToSnake, pathToCamelCase, EXECUTOR ,pathToSnakeCase
from ..logger import defineNopeLogger
from ..observable import NopeObservable
import asyncio


class Bridge:

    def __init__(self, _id=generateId(), logger=False):

        def getter(storedValue):
            for data in self._layers.values():
                if (data.considerConnection and not data.layer.connected.
                        getContent()):
                    return False
            return True

        self.considerConnection = True
        self.allowServiceRedundancy = False
        self._internalEmitter = Emitter()
        self._callbacks = dict()
        self._layers = dict()
        self._id = _id
        self._logger = defineNopeLogger(logger, 'nope.bridge')
        self._useInternalEmitter = True

        self.connected = NopeObservable()
        self.connected.setContent(False)
        self.connected.getter = getter


    @property
    def receivesOwnMessages(self):
        for layer in self._layers.values():
            if not layer.layer.receivesOwnMessages:
                return False
        return True

    @property
    def id(self):
        return self._id

    async def on(self, eventName: str, cb):
        return self._on(eventName, lambda data: cb(ensureDottedAccess(data)))

    async def emit(self, eventName: str, data):
        return self._emit(eventName, None, ensureDottedAccess(data))

    def detailListeners(self, t, listeners):
        raise Exception('Method not implemented.')

    async def dispose(self):
        for item in self._layers.values():
            await item.layer.dispose()

    def _checkInternalEmitter(self):
        self._useInternalEmitter = True
        for layer in self._layers.values():
            if layer.layer.receivesOwnMessages:
                self._useInternalEmitter = False
                break

    def _subscribeToCallback(self, layer, event, forwardData):
        def adaptedCallback(data):
            if forwardData:
                self._emit(event, layer, data)
            else:
                self._internalEmitter.emit(event, data)

        EXECUTOR.callParallel(layer.on, event, adaptedCallback)

    def _on(self, event, cb):

        # if required we will add a logger for the events.
        if self._logger and event != 'StatusChanged':
            def debug_callback(data):
                if self._logger:
                    self._logger.debug(f'received "{event}", data={data}')
                    self._logger.debug(f'subscribe to "{event}"')

            self._internalEmitter.on(event, debug_callback)

        self._internalEmitter.on(event, cb)

        # We now store the callback.
        if event not in self._callbacks:
            self._callbacks[event] = [cb]
        else:
            self._callbacks[event].append(cb)

        # Now we try to add the callback to the connected layers.
        for data in self._layers.values():
            if data.layer.connected.getContent():
                self._subscribeToCallback(data.layer, event, data.forwardData)

    def _emit(self, event, toExclude, dataToSend=None, force=False):
        if self._logger and event != 'StatusChanged':
            self._logger.debug(f'emitting {str(event)} {str(dataToSend)}')
        if self._useInternalEmitter or force:
            self._internalEmitter.emit(event, dataToSend)

        for data in self._layers.values():
            if data.layer != toExclude and data.layer.connected.getContent():

                async def emitOnLayer():
                    try:
                        await data.layer.emit(event, dataToSend)
                    except Exception as error:
                        if self._logger:
                            self._logger.error('failed to emit the event "${event}"')
                            self._logger.error(error)
                        else:
                            print(formatException(error))

                EXECUTOR.callParallel(emitOnLayer)

    async def addCommunicationLayer(self, layer, forwardData=False, considerConnection=False):
        if layer.id not in self._layers:

            def onConnected(*args):
                self.connected.forcePublish()

            self._layers[layer.id] = ensureDottedAccess({
                'layer': layer,
                'considerConnection': considerConnection,
                'forwardData': forwardData
            })
            layer.connected.subscribe(onConnected)

            await layer.connected.waitFor()

            for event,cbs in self._callbacks.items():
                for callback in cbs:
                    layer.on(event, callback)
                    self._checkInternalEmitter()

    async def removeCommunicationLayer(self, layer):
        if layer.id in self._layers:
            self._layers.pop(layer.id)
            self._checkInternalEmitter()
