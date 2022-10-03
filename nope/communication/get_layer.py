from ..helpers import generate_id, DottedDict
from .bridge import Bridge
from .layers import MQTTLayer, IoSocketClientLayer

VALID_LAYERS = DottedDict({
    'event': Bridge,
    'io-client': IoSocketClientLayer,
    'mqtt': MQTTLayer
})

LAYER_DEFAULT_PARAMETERS = DottedDict({
    'io-client': 'http://localhost:7000',
    'mqtt': 'mqtt://localhost:1883'
})


def get_layer(layer: str, parameter=None, logger=False):
    bridge = Bridge(generate_id(), logger)
    params = parameter if parameter is not None else LAYER_DEFAULT_PARAMETERS.get(layer, False)
    if layer == 'event':
        pass
    # elif layer == 'io-client':
    #    bridge.add_communication_layer(IoSocketClientLayer(params, logger), True)
    elif layer == 'mqtt':
        bridge.add_communication_layer(MQTTLayer(params, logger))

    bridge.connected.force_publish()
    return bridge
