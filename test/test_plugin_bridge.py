import nope
from asyncio import sleep
from nope.plugins import install, plugin

"""
This is an Example how to extend the behavior of any class inside of Nope.

Therefore we want to load our sample plugin: "hello".
Therefore we know
"""

#install(nope, "nope.plugins.hello", plugin_dest="nope.dispatcher.rpcManager")
nope, _, __ = install(nope, "nope.plugins.ack_messages", plugin_dest="nope.communication.bridge")


from nope import getLayer, EXECUTOR, getDispatcher

async def main():

    dispatcher = getDispatcher({
        "communicator": await getLayer("event"),
        "logger": False,
    })

    await dispatcher.ready.waitFor()

    await dispatcher.communicator.emit("test", {"data":"test-data"} ,target="will never be there", timeout = 1000.0 )
    print("Failed")
    await sleep(1)
    pass

    


EXECUTOR.loop.run_until_complete(main())
