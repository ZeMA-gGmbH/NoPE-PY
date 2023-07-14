from nope.communication.bridge import Bridge
from nope.communication.layers import MQTTLayer, IoSocketClientLayer
from nope.helpers import generateId, DottedDict

VALID_LAYERS = DottedDict({
    'event': Bridge,
    'io-client': IoSocketClientLayer,
    'mqtt': MQTTLayer
})

LAYER_DEFAULT_PARAMETERS = DottedDict({
    'io-client': 'http://127.0.0.1:7000',
    'mqtt': 'mqtt://localhost:1883'
})


async def addLayer(bridge: Bridge, layer: str, parameter=None, logger=False, considerConnection = False, forwardData = False):
    """ Adds a Layer to the Bridge.

    Args:
        bridge (Bridge): The Bridge used to add the layer to
        layer (str): Name of the Layer. Must match the VALID_LAYERS elements
        parameter (Any, optional): The Parameter used for the Layer. Defaults to None.
        logger (bool, optional): A Definition for a Logger for the Layer. Defaults to False.
        considerConnection (bool, optional): Flag to consinder that connection for the connected flag. Defaults to False.
        forwardData (bool, optional): Enables or Disables the forwarding of the data. Defaults to False.
    """
    params = parameter if parameter is not None else LAYER_DEFAULT_PARAMETERS.get(layer, False)
    
    if layer == 'event':
        pass
    elif layer == 'io-client':
        await bridge.addCommunicationLayer(IoSocketClientLayer(params, logger), forwardData, considerConnection)
    elif layer == 'mqtt':
        await bridge.addCommunicationLayer(MQTTLayer(params, logger), forwardData, considerConnection)
    else:
        raise Exception("Wrong Layer provided!")

    bridge.connected.forcePublish()