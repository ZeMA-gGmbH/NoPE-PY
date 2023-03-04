from .connectivy import generatePingServices
from ...helpers import ensureDottedAccess

SERVICES_NAME = {
    # "defineMaster": generateDefineMaster,
    "pingService": generatePingServices,
    # "timeSyncingService": enableTimeSyncing,
    # "syncingDataService": enablingSyncingData,
}


async def addAllBaseServices(dispatcher, opts=None):
    """ Adds Bases Services to the Dispatcher.

    Args:
        dispatcher (Nope): _description_
        opts (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """

    await dispatcher.ready.waitFor()
    services = ensureDottedAccess(None)

    if (opts and opts.services):
        for name in opts.services:
            services.update(await SERVICES_NAME[name](dispatcher))

    else:
        for name in SERVICES_NAME:
            services.update(await SERVICES_NAME[name](dispatcher))

    return services
