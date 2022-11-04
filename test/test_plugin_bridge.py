import asyncio
from asyncio import sleep

import pytest

import nope
from nope.plugins import install

"""
This is an Example how to extend the behavior of any class inside of Nope.

Therefore we want to load our sample plugin: "hello".
Therefore we know
"""


# install(nope, "nope.plugins.hello", plugin_dest="nope.dispatcher.rpcManager")


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    nope.EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def test_bridge_plugin():
    nope, _, __ = install(nope, "nope.plugins.ack_messages")

    dispatcher = nope.getDispatcher({
        "communicator": await nope.getLayer("event"),
        "logger": False,
    })

    # To make our Plugin work -> we have to manually assign the id
    # dispatcher.communicator.ackReplyId = dispatcher.id

    await dispatcher.ready.waitFor()

    def sub(*args):
        print(*args)

    await dispatcher.communicator.on("test", sub)
    dispatcher.dataDistributor.patternbasedPullData("test/+/a/#")
    await dispatcher.communicator.emit("test", {"data": "test-data-1"}, target=dispatcher.id, timeout=1.0)
    await sleep(1)
    ex = Exception("Failed")
    try:
        await dispatcher.communicator.emit("test", {"data": "test-data-2"}, target="Wont possible", timeout=1.0)
        raise ex
    except Exception as e:
        if e == ex:
            raise ex

    print(dispatcher.connectivityManager.info)


if __name__ == "__main__":
    nope.EXECUTOR.loop.run_until_complete(test_bridge_plugin())
