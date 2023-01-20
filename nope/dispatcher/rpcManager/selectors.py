#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from nope.helpers import maxOfArray, minOfArray


ValidDefaultSelectors = [
    "master",
    "first",
    "dispatcher",
    "host",
    "free-ram",
    "cpu-usage",
]


def generateSelector(selector, core):
    """ A Helper Function, to generate the Basic selector Functions.

    params:
        selector (master|first|dispatcher|host|cpu-usage)

    """

    if selector == 'master':

        # Define a function, which will select the same master.
        async def masterSelector(opts):
            masterId = core.connectivityManager.master.id
            data = core.rpcManager.services.keyMappingreverse
            if opts.serviceName in data:
                arr = list(data[opts.serviceName])
                if masterId in arr:
                    return masterId
            raise Exception('No matching dispatcher present.')

        return masterSelector

    elif selector == 'first':

        async def firstFound(opts):
            data = core.rpcManager.services.keyMappingreverse
            if opts.serviceName in data:
                arr = list(data[opts.serviceName])
                if len(arr) > 0:
                    return arr[0]
            raise Exception('No matching dispatcher present.')

        return firstFound

    elif selector == 'dispatcher':

        async def ownDispatcher(opts):
            ids = core.connectivityManager.dispatchers.data.getContent()
            if core.id in ids:
                return core.id
            raise Exception('No matching dispatcher present.')

        return ownDispatcher

    elif selector == 'host':

        host = core.connectivityManager.info.host.name

        async def sameHost(opts):
            data = core.rpcManager.services.keyMappingreverse
            if opts.serviceName in data:
                items = list(data[opts.serviceName])
                hosts = list(
                    map(
                        lambda item: core.connectivityManager.dispatchers.originalData[
                            item].host.name,
                        items
                    )
                )

                if host in hosts:
                    return items[hosts.index(host)]

            raise Exception('No matching dispatcher present.')

        return sameHost

    elif selector == 'cpu-usage':

        async def cpuUsage():
            dispatchers = core.connectivityManager.dispatchers.data.getContent()
            best_option = minOfArray(dispatchers, 'host.cpu.usage')
            if best_option.index >= 0:
                return dispatchers[best_option.index]
            raise Exception('No matching dispatcher present.')

        return cpuUsage

    elif selector == 'free-ram':

        async def ramUsage():
            dispatchers = core.connectivityManager.dispatchers.data.getContent()
            best_option = maxOfArray(dispatchers, 'host.ram.free')
            if best_option.index >= 0:
                return dispatchers[best_option.index]

            raise Exception('No matching dispatcher present.')

        return ramUsage

    else:
        raise Exception('Please use a valid selector')
