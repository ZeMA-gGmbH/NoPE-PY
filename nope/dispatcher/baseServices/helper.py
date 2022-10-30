from ...helpers import ensureDottedAccess
from .connectivy import generatePingServices
from ..nopeDispatcher import NopeDispatcher

SERVICES_NAME = {
    # "defineMaster": generateDefineMaster,
    "pingService": generatePingServices,
    # "timeSyncingService": enableTimeSyncing,
    # "syncingDataService": enablingSyncingData,
}


async def addAllBaseServices(dispatcher: NopeDispatcher, opts=None):
    """ Adds Bases Services to the Dispatcher.

    Args:
        dispatcher (Nope): _description_
        opts (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """

    await dispatcher.ready.waitFor()
    services = ensureDottedAccess(None)

    if (opts.services):
        for name in opts.services:
            services.update(await SERVICES_NAME[name])

    else:
        for name in SERVICES_NAME:
            services.update(await SERVICES_NAME[name])

    return services
