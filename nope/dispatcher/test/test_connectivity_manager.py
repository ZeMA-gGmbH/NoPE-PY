import time
from asyncio import sleep

from ..connectivityManager import NopeConnectivityManager
from ...communication import getLayer
from ...helpers import EXECUTOR

import pytest
import asyncio


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def get_manager(_communicator=None, _id=None):
    if _communicator is None:
        _communicator = await getLayer("event")

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


async def test_communication():
    _communicator, _first = await get_manager(_id="first")

    await _first.ready.waitFor()

    sub = None

    called = 0

    def detect_change(data, *args, **kwargs):
        nonlocal called
        called += 1

        if called == 1 and len(data.added) != 1:
            raise Exception("Failed to detect the new master.")
        elif called == 2 and len(data.removed) != 1:
            raise Exception("Failed to detect aurevoir")
        elif called == 2:
            nonlocal sub
            sub.unsubscribe()

    sub = _first.dispatchers.onChange.subscribe(detect_change)
    _communicator, _second = await get_manager(_communicator, "second")

    await _second.ready.waitFor()

    await sleep(0.5)

    await _second.dispose()

    await sleep(0.5)
    await _first.dispose()


async def test_sync():
    _communicator, _first = await get_manager()
    await _first.ready.waitFor()

    # Now we want to simulate an delay.
    start = _first.now
    await sleep(0.1)
    end = _first.now

    # We have waited something like 100 ms (+-)
    # thats our delay. Now if we use that delay,
    # we are able sync our time.
    diff = end - start
    _first.syncTime(start, diff)

    adapted_time = _first.now

    assert (end - adapted_time) < 10, "failed to sync the time."

    await _first.dispose()


async def test_master_selection():
    _communicator, _first = await get_manager(None, "first")
    await _first.ready.waitFor()
    await sleep(0.1)

    _communicator, _second = await get_manager(_communicator, "second")
    await _second.ready.waitFor()

    # Wait for the first Handshake
    await sleep(1)

    assert _first.isMaster, "First should be master"
    assert not _second.isMaster, "First should be master"
    assert _first.master.id == _first.id, "First should be master"
    assert _second.master.id == _first.id, "First should be master"

    # Manually assign a new master

    _first.isMaster = False
    await sleep(0.1)

    assert _second.isMaster, "Second should be autoselected as master"
    assert not _first.isMaster, "Second should be autoselected as master"
    assert _second.master.id == _second.id, "Second should be autoselected as master"
    assert _second.master.id == _second.id, "Second should be autoselected as master"

    # release the assignment

    _first.isMaster = None
    await sleep(0.1)

    assert _first.isMaster, "First should be master again"
    assert not _second.isMaster, "First should be master again"
    assert _first.master.id == _first.id, "First should be master again"
    assert _second.master.id == _first.id, "First should be master again"

    await _first.dispose()
    await _second.dispose()
