from nope.communication.bridge import Bridge
from nope.communication.layers import MQTTLayer, IoSocketClientLayer
from nope.helpers import generateId, DottedDict

from .addLayer import addLayer


async def getLayer(layer: str, parameter=None, logger=False):
    # Add the Bridge
    bridge = Bridge(generateId(), logger)

    # Add the Layer
    await addLayer(bridge, layer, parameter, logger, True, True)

    # Return the Bridge
    return bridge
