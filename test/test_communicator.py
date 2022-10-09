from asyncio import sleep

import pytest

from nope import get_layer, EXECUTOR, NopeConnectivityManager, DictBasedMergeData


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


_mapping_of_dispatchers_and_services = dict()
services = DictBasedMergeData(_mapping_of_dispatchers_and_services, 'services/+', 'services/+/id')


async def get_manager(_communicator=None, _id=None):
    if _communicator is None:
        _communicator = await get_layer("event", "", False)

    manager = NopeConnectivityManager({
        'communicator': _communicator,
        "logger": False
    }, _id)

    return _communicator, manager


async def test_configuration():
    _, manager = await get_manager()

    await manager.ready.wait_for()

    await manager.set_timings({
        "check_interval": 10,
        "dead": 25,
        "remove": 30,
        "send_alive_interval": 5,
        "slow": 15,
        "warn": 20,
    })

    assert manager.ready.get_content(), "Manager not ready"

    assert manager.is_master, "Didnt assing the communicator as master"
    manager.is_master = True
    assert manager.is_master, "Failed forcing the master"
    manager.is_master = False
    assert not manager.is_master, "Didnt removed the master flag"

    # Kill the manager.
    await manager.dispose()


async def main():
    _communicator, _first = await get_manager(None, "first")
    await _first.ready.wait_for()

    await sleep(0.1)

    _communicator, _second = await get_manager(_communicator, "second")
    await _second.ready.wait_for()

    # Wait for the first Handshake
    await sleep(1)

    assert _first.is_master, "First should be master"
    _second.is_master = True
    await sleep(0.01)
    assert not _first.is_master, "Second should be master"

    _second.is_master = None

    await sleep(0.01)
    assert _first.is_master, "First should be master"

    print(_first.master)

    await _first.dispose()

    print("ready")


EXECUTOR.loop.run_until_complete(test_configuration())
