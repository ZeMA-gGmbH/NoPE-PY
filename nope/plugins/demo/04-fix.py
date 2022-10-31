import nope
from asyncio import sleep
from nope.plugins import install, plugin

"""
This is an Example how to extend the behavior of any class inside of Nope.

Therefore we define a function (extend) which receives one Parameter, the
module which is located under the given path. This module must contain
the loaded class or function. We have to decorate the function with the
’plugin' decorator (which receives the path as parameter).

Inside of the function we are able to access the original class using the
`module.*ACCESSOR*`. In the example below we create an extra function
"hello_dynamic" which will just give us a simple hello world response.

Additional you are able to "store" functions into the module (see our
extend function).

If you want to manipulate specific vars --> please use a dict. for the
key use the name of the variable you want to edit.
"""


@plugin("nope.helpers.timestamp")
def extend(module):
    "Extends `module` - rpcManager"
    def getTimestamp(options=None) -> str:
        return module.getTimestamp()+500
    return getTimestamp


# Now install our plugin
nope, _, __ = install(nope, extend, plugin_dest="nope.helpers.timestamp")

# The following main is just for clearification
print("ready")
print(nope.helpers.getTimestamp())
print("done")