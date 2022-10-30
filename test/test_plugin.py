from nope import getLayer, EXECUTOR, getDispatcher
import nope.plugins as plugins
nope_extended = plugins.load('hello', 'nope.dispatcher')

async def main():

    dispatcher = getDispatcher({
        "communicator": await getLayer("event"),
        "logger": False,
    })
    manager = dispatcher.rpcManager
    manager.hello()



EXECUTOR.loop.run_until_complete(main())

