import nope
from asyncio import sleep
from nope import getLayer, EXECUTOR, getDispatcher
from nope.plugins import install

"""
This is an Example how to extend the behavior of any class inside of Nope.

Therefore we want to load our sample plugin: "hello".
Therefore we know
"""

#install(nope, "nope.plugins.hello", plugin_dest="nope.dispatcher.rpcManager")
install(nope, "nope.plugins.hello")


async def main():

    dispatcher = getDispatcher({
        "communicator": await getLayer("event"),
        "logger": False,
    })

    manager = dispatcher.rpcManager

    async def hello_srv(greetings):
        print("Hello", greetings, "!")

    await dispatcher.ready.waitFor()
    await dispatcher.rpcManager.registerService(hello_srv, {"id": "hello_srv"})

    await sleep(0.1)

    manager.hello()

    await manager.performCall("hello_srv", ["reader"])

    await dispatcher.dispose()


EXECUTOR.loop.run_until_complete(main())
