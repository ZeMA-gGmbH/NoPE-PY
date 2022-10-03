from ...observables import NopeObservable
from ...helpers import Emitter, generate_id


class EventCommunicationInterface:

    def __init__(self, emitter, logger=None, receives_own_messages=True):
        self.emitter = emitter if emitter is not None else Emitter()
        self.logger = logger
        self.receives_own_messages = receives_own_messages
        self.connected = NopeObservable()
        self.connected.set_content(True)
        self.id = generate_id()

    async def on(self, event_name: str, cb):
        self.emitter.on(event_name, cb)

        if event_name != 'StatusChanged' and self.logger:
            def logging_callback(*args):
                self.logger.debug('received', "'" + event_name + "'", *args)

            self.emitter.on(event_name, logging_callback)

    async def emit(self, event_name: str, data):
        self.emitter.emit(event_name, data)

    async def dispose(self):
        self.emitter.close()

    def detail_listeners(self, t, listeners):
        raise Exception('Method not implemented.')
