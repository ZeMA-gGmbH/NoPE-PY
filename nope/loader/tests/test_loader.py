import asyncio
from asyncio import sleep

import pytest

from nope.loader import NopePackageLoader
from nope.communication import getLayer
from nope.demo.instances import DESCRIPTION
from nope.dispatcher import getDispatcher
from nope.helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def test_loading():
    communicator = await getLayer("event")

    dispatcher = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    loader = NopePackageLoader(dispatcher)

    await dispatcher.ready.waitFor()

    await loader.addPackage(DESCRIPTION)

    await sleep(0.5)

    await loader.generateInstances()

    instances = dispatcher.instanceManager.instances.data.getContent()

if __name__ == "__main__":
    EXECUTOR.loop.run_until_complete(test_loading())
