from .DecoratedHelloWorld import DecoratedHelloWorldModule
from .HelloWorld import HelloWorldModule


async def _createHellowordModule(dispatcher, *args):
    """ Helper Function to Create the instance. """
    return HelloWorldModule(dispatcher)


async def helloWorldService(msg: str):
    return "Hello " + msg + "!"


# Define the Description:
DESCRIPTION = {
    'autostart': [],
    "defaultInstances": [
        {
            "identifier": "instance01",
            "type": "HelloWorldModule",
            "params": []
        }
    ],
    "nameOfPackage": "helloworldpackage",
    "providedClasses": [
        {
            "selector": "HelloWorldModule",
            "allowInstanceGeneration": True,
            "createInstance": _createHellowordModule
        }
    ],
    "provided_functions": [
        {
            "function": helloWorldService,
            "options": {
                "id": "helloWorldService",
                "schema": {

                }
            }
        }
    ],
    "required_packages": [],
}
