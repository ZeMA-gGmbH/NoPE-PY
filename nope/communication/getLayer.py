from nope.helpers import generateId, DottedDict
from nope.communication.bridge import Bridge
from nope.communication.layers import MQTTLayer, IoSocketClientLayer

VALID_LAYERS = DottedDict({
    'event': Bridge,
    'io-client': IoSocketClientLayer,
    'mqtt': MQTTLayer
})

LAYER_DEFAULT_PARAMETERS = DottedDict({
    'io-client': 'http://localhost:7000',
    'mqtt': 'mqtt://localhost:1883'
})


async def getLayer(layer: str, parameter=None, logger=False):
    bridge = Bridge(generateId(), logger)
    params = parameter if parameter is not None else LAYER_DEFAULT_PARAMETERS.get(
        layer, False)
    if layer == 'event':
        pass
    elif layer == 'io-client':
        await bridge.addCommunicationLayer(IoSocketClientLayer(params, logger), True)
    elif layer == 'mqtt':
        await bridge.addCommunicationLayer(MQTTLayer(params, logger))

    bridge.connected.forcePublish()
    return bridge
