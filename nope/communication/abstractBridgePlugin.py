# This is a reference Implementation for a Plugin:
class AbstractBridgePlugin:

    def __init__(self):
        self.options = ensureDottedAccess(dict(), False)
        self._id = generateId()

        # Must contain an obervalbe with the flag ready.
        self.ready = NopeObservable()
        self.ready.setContent(False)

    @property
    def id(self) -> str:
        return self._id

    async def transformData(self, eventName: str, data):
        # Must return the following data:
        # 1. eventName: str
        # 2. data: any
        # 3.

        # Example 1:
        #   return eventName, data, None

        # Example 2:
        #   return eventName, data, None
        raise Exception("Not Implemented")

    async def init(self) -> None:
        # Expected after calling init, the ready flag will be
        # called.

        # Example:
        #   self.ready.setContent(True)

        raise Exception("Not Implemented")

    def reset(self) -> None:
        # No return type is being used.
        raise Exception("Not Implemented")

    async def dispose(self, quiet=False):
        pass
