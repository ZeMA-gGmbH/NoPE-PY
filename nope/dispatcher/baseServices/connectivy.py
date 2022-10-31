

import asyncio

from nope.helpers import avgOfArray, ensureDottedAccess, maxOfArray, minOfArray
from nope.logger import getNopeLogger

logger = getNopeLogger('baseService')


async def generatePingServices(dispatcher):

    async def ping():
        return ensureDottedAccess({
            'dispatcherId': dispatcher.id,
            'timestamp': dispatcher.connectivityManager.now
        })

    serviceName = 'nope/baseService/ping'

    await dispatcher.rpcManager.registerService(
        ping,
        ensureDottedAccess({
            'id': serviceName,
            'schema': {
                'inputs': [],
                'outputs': {
                    'type': 'object',
                    'properties': {
                        'dispatcherId': {
                            'type': 'string',
                            'description': 'Id of the responding Dispatcher'
                        },
                        'timestamp': {
                            'type': 'number',
                            'description': 'UTC-Timestamp of the system which is responding'
                        }
                    }
                }
            },
            'type': 'function',
            'description': 'Ping'
        })
    )
    return await generatePingAccessors(dispatcher)


async def generatePingAccessors(dispatcher):

    serviceName = 'nope/baseService/ping'

    # Function to determine the ping in the services.
    async def determinePing(target: str):
        # Call the Pings
        start = dispatcher.connectivityManager.now
        result = await dispatcher.rpcManager.performCall(serviceName, [], {target})
        delay = dispatcher.connectivityManager.now

        ping = delay - start

        return ensureDottedAccess({
            "ping": ping,
            ** result,
        })

    # Function to Ping all Services

    async def pingAll():
        dispatchers = list(
            dispatcher.connectivityManager.dispatchers.keyMappingReverse.get(
                serviceName
            )
        )

        promises = []
        for target in dispatchers:
            promises.append(determinePing(target))

        if promises:
            pings = await asyncio.gather(*promises)

        avg = avgOfArray(pings, "ping")
        max = maxOfArray(pings, "ping")
        min = minOfArray(pings, "ping")

        return ensureDottedAccess({
            "pings": pings,
            "avg": avg,
            "max": max,
            "min": min,
        })

    return ensureDottedAccess({
        "determinePing": determinePing,
        "pingAll": pingAll
    })
