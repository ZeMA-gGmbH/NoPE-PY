from asyncio import sleep
import time
from ..connectivity_manager import NopeConnectivityManager
from ...communication import get_layer


async def get_manager(_communicator=None, _id=None):
    if _communicator is None:
        _communicator = await get_layer("event", "", False)

    manager = NopeConnectivityManager({
        'communicator': _communicator,
        "logger": False
    }, _id)

    time.sleep(0.5)

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


async def test_communication():
    _communicator, _first = await get_manager(_id="first")

    await _first.ready.wait_for()

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

    sub = _first.dispatchers.on_change.subscribe(detect_change)
    _communicator, _second = await get_manager(_communicator, "second")

    await _second.ready.wait_for()

    await sleep(0.5)

    await _second.dispose()

    await sleep(0.5)
    await _first.dispose()


async def test_sync():
    _communicator, _first = await get_manager()
    await _first.ready.wait_for()

    # Now we want to simulate an delay.
    start = _first.now
    await sleep(0.1)
    end = _first.now

    # We have waited something like 100 ms (+-)
    # thats our delay. Now if we use that delay,
    # we are able sync our time.
    diff = end - start
    _first.sync_time(start, diff)

    adapted_time = _first.now

    assert (end - adapted_time) < 10, "failed to sync the time."

    await _first.dispose()


async def test_master_selection():
    _communicator, _first = await get_manager(None, "first")
    await _first.ready.wait_for()
    await sleep(0.1)

    _communicator, _second = await get_manager(_communicator, "second")
    await _second.ready.wait_for()

    # Wait for the first Handshake
    await sleep(1)

    assert _first.is_master, "First should be master"
    assert not _second.is_master, "First should be master"
    assert _first.master.id == _first.id, "First should be master"
    assert _second.master.id == _first.id, "First should be master"

    # Manually assign a new master

    _first.is_master = False
    await sleep(0.1)

    assert _second.is_master, "Second should be autoselected as master"
    assert not _first.is_master, "Second should be autoselected as master"
    assert _second.master.id == _second.id, "Second should be autoselected as master"
    assert _second.master.id == _second.id, "Second should be autoselected as master"

    # release the assignment

    _first.is_master = None
    await sleep(0.1)

    assert _first.is_master, "First should be master again"
    assert not _second.is_master, "First should be master again"
    assert _first.master.id == _first.id, "First should be master again"
    assert _second.master.id == _first.id, "First should be master again"

    await _first.dispose()
    await _second.dispose()
