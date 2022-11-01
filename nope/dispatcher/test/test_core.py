from asyncio import sleep


from ...communication import getLayer
from ...demo import HelloWorldModule, DecoratedHelloWorldModule
from ..getDispatcher import getDispatcher

from ...helpers import EXECUTOR

import pytest
import asyncio


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()

async def test_dispose():
    communicator = await getLayer("event")

    srv = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    await srv.ready.waitFor()
    await srv.dispose()

async def test_events():
    communicator = await getLayer("event")

    srv = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    client = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })
    
    await srv.ready.waitFor()
    await client.ready.waitFor()

    sub = None
    called = 0

    async def done():
        nonlocal sub

        # Remove the Subscription
        sub.unsubscribe()

        await srv.dispose()
        await client.dispose()

    def callback(data,rest):
        nonlocal called 
        called += 1

        assert data == "test"
        
        done()
    
    sub = client.eventDistributor.registerSubscription("event", callback)

    await sleep(0.1)
    try:
        srv.eventDistributor.emit("event", "test")
    except Exception as E:
        pass
    await sleep(0.1)

    assert called == 1


async def test_properties_clean():
    communicator = await getLayer("event")

    srv = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    client = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })
    
    await srv.ready.waitFor()
    await client.ready.waitFor()

    await sleep(1)

    srv.dataDistributor.pushData("data", "test")
    await sleep(1)
    
    assert client.dataDistributor.pullData("data", False) == "test"
    
    await srv.dispose()
    await client.dispose()

async def test_properties_dirty():
    communicator = await getLayer("event")

    srv = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    
    
    await srv.ready.waitFor()
    srv.dataDistributor.pushData("data", "test")

    client = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    await client.ready.waitFor()    
    await sleep(1)
    
    assert client.dataDistributor.pullData("data", False) == False
    
    await srv.dispose()
    await client.dispose()

if __name__ == "__main__":
    EXECUTOR.callParallel(func)

# async def test_register_instance():

#     communicator = await getLayer("event")

#     srv = getDispatcher({
#         "communicator": communicator,
#         "logger": False,
#     })

#     client = getDispatcher({
#         "communicator": communicator,
#         "logger": False,
#     })

#     # Create an instance on the Server
#     instance = HelloWorldModule(srv)


    

#     srv.instanceManager.registerInstance(instance)


#     manager = srv.rpcManager
#     await srv.ready.waitFor()

#     manager.hello_dynamic()
#     await manager.performCall("test", ["should be logged"])

#     # Now we are able to access our variable
#     print(nope.dispatcher.rpcManager.hello)

#     # and our new function, we injected into the module.
#     nope.dispatcher.rpcManager.hello_dynamic()