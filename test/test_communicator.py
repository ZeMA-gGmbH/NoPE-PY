from nope.communication import  get_layer
from nope.dispatcher import NopeConnectivityManager
from nope.helpers import get_or_create_eventloop


def get_manager(_communicator=None, _id=None):
    if _communicator is None:
        _communicator = get_layer("event", "", False)

    manager = NopeConnectivityManager({
        'communicator': _communicator,
        "logger": False
    }, _id)

    return _communicator, manager


async def main():
    _, m = get_manager()

    await m.ready.wait_for()
    

    print("ready")

loop = get_or_create_eventloop()
loop.run_until_complete(main())
