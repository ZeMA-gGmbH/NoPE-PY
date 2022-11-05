from .DecoratedHelloWorld import DecoratedHelloWorldModule
from .HelloWorld import HelloWorldModule
from ...types import ProvidedClass, NopePackage, DefaultInstance, ProvidedService, ServiceOptions


async def _createHellowordModule(dispatcher, *args):
    """ Helper Function to Create the instance. """
    return HelloWorldModule(dispatcher)


async def helloWorldService(msg: str):
    return "Hello " + msg + "!"


DESCRIPTION = NopePackage("helloWorld",
                          defaultInstances=[
                              DefaultInstance("instance01", "HelloWorldModule")
                          ],
                          providedClasses=[
                              ProvidedClass(
                                  "HelloWorldModule", _createHellowordModule)
                          ],
                          providedServices=[
                              ProvidedService(
                                helloWorldService,
                                ServiceOptions(
                                    id="helloWorldService",
                                    schema={}
                                )
                              )
                          ])
