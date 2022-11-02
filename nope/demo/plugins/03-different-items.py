import nope
from asyncio import sleep
from nope.plugins import install, plugin

"""
You can although combine different plugins for 1 element.

Therefore the install method will receive instead of a plugin
a list of plugins. The tool will apply the installation using
the provided order.

"""


@plugin("nope.dispatcher.rpcManager")
def extend_1(module):
    "Extends `module` - rpcManager"
    class NopeRpcManager(module.NopeRpcManager):
        async def performCall(self, *args, **kwargs):
            """ Extend the original behavior """
            print("calling perform call - extend 1")
            return await module.NopeRpcManager.performCall(self, *args, **kwargs)

        def hello_dynamic(self):
            "Ask the plugin to say hello"
            print("Hello from the Dynamic Plugin")

    def hello_dynamic():
        "Ask the plugin to say hello"
        print("Hello from the Dynamic Plugin")

    hello_dynamic_vars = {"hello": "Hello from the Dynamic Plugin"}
    return NopeRpcManager, hello_dynamic, hello_dynamic_vars


@plugin("nope.dispatcher.nopeDispatcher")
def extend_2(module):
    "Extends `module` - NopeDispatcher"
    class NopeDispatcher(module.NopeDispatcher):
        async def performCall(self, *args, **kwargs):
            """ Extend the original behavior """
            print("calling perform call - from ")
            try:
                return await self.rpcManager.performCall(self, *args, **kwargs)
            except BaseException:
                print("Failed but we got the error")

    return NopeDispatcher


"""
In our case the plugin 1 is loaded first and then the second (extend_2)
In the method 'performCall' of the 'NopeRpcManager' this results in loading
the latest plugin first (extend_2) accessing the 'module.NopeRpcManager' inside
of 'extend_2' returns you the already modified 'NopeRpcManager' with plugin 1
(extend 1)

If we call the method
>>> await manager.performCall("hello_srv", ["reader"])
calling perform call - extend 1
Failed but we got the error
"""

nope, updated, skipped = install(nope, extend_1)
nope, updated, skipped = install(nope, extend_2)

print(updated, skipped)

# The following main is just for clearification


async def main():

    # Create our dispatcher
    dispatcher = nope.getDispatcher({
        "communicator": await nope.getLayer("event"),
        "logger": False,
    })

    manager = dispatcher.rpcManager

    async def hello_srv(greetings):
        print("Hello", greetings, "!")

    await dispatcher.ready.waitFor()
    await dispatcher.rpcManager.registerService(hello_srv, {"id": "hello_srv"})

    await sleep(0.1)

    # manager.hello_dynamic()
    await manager.performCall("hello_srv", ["reader"])
    await dispatcher.performCall("hello_srv", ["reader"])
    # If we call the method
    # >>> await dispatcher.performCall("hello_srv", ["reader"])
    # calling perform call - extend 2
    # calling perform call - extend 1
    # Failed but we got the error

    # Now we are able to access our variable

    # and our new function, we injected into the module.
    nope.dispatcher.rpcManager.hello_dynamic()


nope.EXECUTOR.loop.run_until_complete(main())
