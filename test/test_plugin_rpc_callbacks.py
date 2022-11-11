import asyncio
from asyncio import sleep

import pytest

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
    import nope
    nope, _, __ = install(nope, "nope.plugins.rpc_with_callbacks")

    dispatcher = nope.getDispatcher({
        "communicator": await nope.getLayer("event"),
        "logger": False,
    })

    # To make our Plugin work -> we have to manually assign the id
    # dispatcher.communicator.ackReplyId = dispatcher.id
    await dispatcher.ready.waitFor()

    async def funcWithCallback(p, cb1, cb2):
        return await cb1(p,cb2)

    await dispatcher.rpcManager.registerService(funcWithCallback, {
        "id": "funcWithCallback"
    })

    async def cb(p,cb2):
        print("inside of callback")
        await cb2()

    await dispatcher.rpcManager.performCall("funcWithCallback", ["jeah", cb, lambda *args: print("Here")], {
        "calledOnce": [1]
    })


if __name__ == "__main__":
    import nope
    nope.EXECUTOR.loop.run_until_complete(test_bridge_plugin())
