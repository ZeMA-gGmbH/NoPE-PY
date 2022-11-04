import asyncio
from asyncio import sleep

import pytest

from nope import getLayer, EXECUTOR, NopeConnectivityManager, DictBasedMergeData


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


_mappingOfDispatchersAndServices = dict()
services = DictBasedMergeData(
    _mappingOfDispatchersAndServices,
    'services/+',
    'services/+/id')


async def get_manager(_communicator=None, _id=None):
    if _communicator is None:
        _communicator = await getLayer("event", "", False)

    manager = NopeConnectivityManager({
        'communicator': _communicator,
        "logger": False
    }, _id)

    return _communicator, manager


async def test_configuration():
    _, manager = await get_manager()

    await manager.ready.waitFor()

    await manager.setTimings({
        "checkInterval": 10,
        "dead": 25,
        "remove": 30,
        "sendAliveInterval": 5,
        "slow": 15,
        "warn": 20,
    })

    assert manager.ready.getContent(), "Manager not ready"

    assert manager.isMaster, "Didnt assing the communicator as master"
    manager.isMaster = True
    assert manager.isMaster, "Failed forcing the master"
    manager.isMaster = False
    assert not manager.isMaster, "Didnt removed the master flag"

    # Kill the manager.
    await manager.dispose()


async def main():
    _communicator, _first = await get_manager(None, "first")
    await _first.ready.waitFor()

    await sleep(0.1)

    _communicator, _second = await get_manager(_communicator, "second")
    await _second.ready.waitFor()

    # Wait for the first Handshake
    await sleep(1)

    assert _first.isMaster, "First should be master"
    _second.isMaster = True
    await sleep(0.01)
    assert not _first.isMaster, "Second should be master"

    _second.isMaster = None

    await sleep(0.01)
    assert _first.isMaster, "First should be master"

    print(_first.master)

    await _first.dispose()

    print("ready")


EXECUTOR.loop.run_until_complete(test_configuration())
