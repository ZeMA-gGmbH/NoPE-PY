import nope
from nope import getLayer, EXECUTOR, getDispatcher
from nope.plugins import install, plugin

"""
This is an Example how to extend the behavior of any class inside of Nope.

Therefore we define a function (extend) which receives one Parameter, the
module which is located under the given path. This module must contain
the loaded class or function. We have to decorate the function with the
’plugin' decorator (which receives the path as parameter).

Inside of the function we are able to access the original class using the
module.*ACCESSOR*. In the example below we create an extra function
"hello_dynamic" which will just give us a simple hello world response.

Additional you are able to "store" functions into the module (see our
extend function).

If you want to manipulate specific vars --> please use a dict. for the
key use the name of the variable you want to edit.
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


install(nope, extend_1, plugin_dest="nope.dispatcher.rpcManager")


@plugin("nope.dispatcher.rpcManager")
def extend_2(module):
    "Extends `module` - rpcManager"

    class NopeRpcManager(module.NopeRpcManager):
        async def performCall(self, *args, **kwargs):
            """ Extend the original behavior """
            print("calling perform call - extend 2")
            try:
                return await module.NopeRpcManager.performCall(self, *args, **kwargs)
            except BaseException:
                print("Failed but we got the error")

    return NopeRpcManager


install(nope, [extend_1, extend_2], plugin_dest="nope.dispatcher.rpcManager")


async def main():
    dispatcher = getDispatcher({
        "communicator": await getLayer("event"),
        "logger": False,
    })
    manager = dispatcher.rpcManager
    await dispatcher.ready.waitFor()

    manager.hello_dynamic()
    await manager.performCall("test", ["should be logged"])

    # Now we are able to access our variable
    print(nope.dispatcher.rpcManager.hello)

    # and our new function, we injected into the module.
    nope.dispatcher.rpcManager.hello_dynamic()


EXECUTOR.loop.run_until_complete(main())
