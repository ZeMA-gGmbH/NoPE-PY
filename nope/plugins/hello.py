""" An example plugin that allows instances of `NopeRpcManager` to
    say hello. The source code can be used as a starting example.

    Please visist: nope/plugins/demo and "checkout" the examples.
"""


# @plugin("nope.dispatcher.rpcManager")
def extend(module):
    "Extends `module` - RPC-Manager"

    class NopeRpcManager(module.NopeRpcManager):
        def hello(self):
            "Ask the plugin to say hello"
            print("Hello from the Plugin")

        async def performCall(self, *args, **kwargs):
            """ Extend the original behavior """
            print("calling 'performCall' inside of our addon")
            return await module.NopeRpcManager.performCall(self, *args, **kwargs)

    def hello_func(self):
        "Ask the plugin to say hello"
        print("Hello from the Plugin")

    hello_vars = {"hello": "Hello from the Plugin"}
    return NopeRpcManager, hello_func, hello_vars
