
"""An example plugin that allows instances of `NopeRpcManager` to
say hello. The source code can be used as a starting example."""

import nope.plugins


@nope.plugins.plugin("nope.dispatcher.rpcManager")
def extend(module):
    "Extends `module`"
    class NopeRpcManager(module.NopeRpcManager):
        def hello(self):
            "Ask the plugin to say hello"
            print("Hello from the Plugin")
    return NopeRpcManager
