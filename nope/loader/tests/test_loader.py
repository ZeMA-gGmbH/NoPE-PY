from ..nopePackkageLoader import NopePackageLoader
from ...communication import getLayer
from ...demo.instances import DESCRIPTION
from ...dispatcher import getDispatcher


async def test_loading():
    communicator = await getLayer("event")

    dispatcher = getDispatcher({
        "communicator": communicator,
        "logger": False,
    })

    loader = NopePackageLoader(dispatcher)

    loader.addPackage(DESCRIPTION)
    loader.generateInstances()
