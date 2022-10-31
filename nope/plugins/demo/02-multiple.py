import nope
from nope import getLayer, EXECUTOR, getDispatcher
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


@plugin("nope.dispatcher.rpcManager")
def extend_2(module):
    "Extends `module` - rpcManager"
    class NopeRpcManager(module.NopeRpcManager):
        async def performCall(self, *args, **kwargs):
            """ Extend the original behavior """
            print("calling perform call - extend 2")
            try:
                return await module.NopeRpcManager.performCall(self, *args, **kwargs)
            except:
                print("Failed but we got the error")

    return NopeRpcManager


    
"""
In our case the plugin 1 is loaded first and then the second (extend_2)
In the method 'performCall' of the 'NopeRpcManager' this results in loading
the latest plugin first (extend_2) accessing the 'module.NopeRpcManager' inside
of 'extend_2' returns you the already modified 'NopeRpcManager' with plugin 1
(extend 1)

If we call the method
>>> await manager.performCall("hello_srv", ["reader"])
calling perform call - extend 2
calling perform call - extend 1
Failed but we got the error
"""

install(nope, [extend_1, extend_2], plugin_dest="nope.dispatcher.rpcManager")

# The following main is just for clearification


async def main():

    # Create our dispatcher
    dispatcher = getDispatcher({
        "communicator": await getLayer("event"),
        "logger": False,
    })

    manager = dispatcher.rpcManager
    await dispatcher.ready.waitFor()

    manager.hello_dynamic()
    await manager.performCall("hello_srv", ["reader"])
    # If we call the method
    # >>> await manager.performCall("hello_srv", ["reader"])
    # calling perform call - extend 2
    # calling perform call - extend 1
    # Failed but we got the error

    # Now we are able to access our variable
    print(nope.dispatcher.rpcManager.hello)

    # and our new function, we injected into the module.
    nope.dispatcher.rpcManager.hello_dynamic()


EXECUTOR.loop.run_until_complete(main())
