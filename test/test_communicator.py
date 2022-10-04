from nope.communication import  get_layer
from nope.dispatcher import NopeConnectivityManager
from nope.helpers import get_or_create_eventloop
from asyncio import sleep

def get_manager(_communicator=None, _id=None):
    if _communicator is None:
        _communicator = get_layer("event", "", False)

    manager = NopeConnectivityManager({
        'communicator': _communicator,
        "logger": False
    }, _id)

    return _communicator, manager


async def main():
    _communicator, _first = get_manager(None, "first")
    await _first.ready.wait_for()

    await sleep(0.1)

    _communicator, _second = get_manager(_communicator, "second")
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


    

    print("ready")

loop = get_or_create_eventloop()
loop.run_until_complete(main())
