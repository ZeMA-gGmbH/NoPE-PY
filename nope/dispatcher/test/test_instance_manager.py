import asyncio
from asyncio import sleep

import pytest

from ..getDispatcher import getDispatcher
from ...communication import getLayer
from ...demo.instances import HelloWorldModule
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def test_register_instance():
    communicator = await getLayer("event")

    srv = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    client = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    async def createInstance(core, identifier):
        return HelloWorldModule(core)

    # Create an instance on the Server
    instance = HelloWorldModule(srv)

    await srv.ready.waitFor()
    await client.ready.waitFor()

    await srv.instanceManager.registerConstructor("hello_word", createInstance)

    await sleep(0.1)

    assert srv.instanceManager.getServiceName("hello_word","constructor") in client.instanceManager.constructors.data.getContent()
    assert len(client.instanceManager.constructors.data.getContent()) == 1

if __name__ == "__main__":
    EXECUTOR.loop.run_until_complete(test_register_instance())
