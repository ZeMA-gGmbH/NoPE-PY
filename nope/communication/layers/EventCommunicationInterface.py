from ...helpers import Emitter, generateId
from ...observable import NopeObservable

import time

PROFILE = True
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

                print("Bearbeitung hat", round(delta*1000,2), "[ms] gedauert")
    except:
        print(f"Failed in 'profile_task' mode={mode}, data={data}, type={type(data)}")


class EventCommunicationInterface:

    def __init__(self, emitter, logger=None, receivesOwnMessages=True):
        self._emitter = emitter if emitter is not None else Emitter()
        self._logger = logger
        self.receivesOwnMessages = receivesOwnMessages
        self.connected = NopeObservable()
        self.connected.setContent(True)
        self.id = generateId()

    async def on(self, eventName: str, cb):
        

        if PROFILE:
            if eventName == "rpcRequest":     
                def req(data,*args):
                    profile_task("new", data)
                    cb(data)           
                self._emitter.on(eventName, req)
            elif eventName == "rpcResponse":  
                def res(data, *args):
                    profile_task("done", data)
                    cb(data)                 
                self._emitter.on(eventName, res)
            else:
                self._emitter.on(eventName, cb)
        else: 
            self._emitter.on(eventName, cb)

        if eventName != 'statusChanged' and self._logger:
            def loggingCallback(*args):
                self._logger.debug('received', "'" + eventName + "'", *args)

            self._emitter.on(eventName, loggingCallback)

    async def emit(self, eventName: str, data):

        if PROFILE:
            if eventName == "rpcRequest":
                profile_task("new", data)
            if eventName == "rpcResponse":                
                profile_task("done", data)

        self._emitter.emit(eventName, data)

    async def dispose(self):
        self._emitter.close()

    def detailListeners(self, t, listeners):
        raise Exception('Method not implemented.')
