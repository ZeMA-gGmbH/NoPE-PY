import socketio
import time
from nope.communication.layers import EventCommunicationInterface
from nope.logger import defineNopeLogger
from nope.observable import NopeObservable
from nope.helpers import generateId, EXECUTOR


PROFILE = False
OPEN_REQUESTS = {}


def profile_task(mode: str, data):
    try:
        if mode == "new":
            OPEN_REQUESTS[data["taskId"]] = time.process_time()
        elif mode == "done":
            if data["taskId"] in OPEN_REQUESTS:
                start = OPEN_REQUESTS.pop(data["taskId"])
                end = time.process_time()
                delta = end - start

                print(
                    "Bearbeitung hat",
                    round(
                        delta * 1000,
                        2),
                    "[ms] gedauert")
    except BaseException as e:
        print(f"Failed with mdoe= {mode}, data={data} cause: '{str(e)}'")


class IoSocketClientLayer:

    def __init__(self, uri: str, logger='info'):
        # Define the URI
        self.id = generateId()
        self.receivesOwnMessages = False
        self.uri = uri
        self.uri = self.uri if self.uri.startswith(
            'http://') else 'http://' + self.uri

        self._logger = defineNopeLogger(logger, "core.mirror.io")

        self._client = socketio.AsyncClient()
        EXECUTOR.callParallel(self._client.connect, self.uri)

        self.connected = NopeObservable()
        self.connected.setContent(False)

        def onConnect():
            self.connected.setContent(True)

        def onDisconnect():
            self.connected.setContent(False)

        self._client.on("connect", onConnect)
        self._client.on("disconnect", onDisconnect())

    async def on(self, eventName: str, cb):
        if PROFILE:
            if eventName == "rpcRequest":
                def req(data, *args):
                    profile_task("new", data)
                    cb(data)
                self._client.on(eventName, req)
            elif eventName == "rpcResponse":
                def res(data, *args):
                    profile_task("done", data)
                    cb(data)
                self._client.on(eventName, res)
            else:
                self._client.on(eventName, cb)
        else:
            self._client.on(eventName, cb)

    async def off(self, eventName: str, cb):
        self._client.handlers['/'].pop(eventName)

    async def emit(self, eventName: str, data):

        if PROFILE:
            if eventName == "rpcRequest":
                profile_task("new", data)
            if eventName == "rpcResponse":
                profile_task("done", data)

        await self._client.emit(eventName, data)

    async def dispose(self):
        await self._client.disconnect()

    def detailListeners(self, t, listeners):
        raise Exception('Method not implemented.')
