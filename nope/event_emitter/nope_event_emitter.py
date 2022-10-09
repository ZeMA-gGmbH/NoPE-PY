from asyncio import Future

from ..helpers import generate_id, DottedDict, Emitter, ensure_dotted_dict, is_async_function, get_timestamp, Promise


# from ..logger.getLogger import getNopeLogger
# logger = getNopeLogger('obervable')


class NopeEventEmitter:

    def __init__(self, options=DottedDict({'generate_timestamp': True})):
        self.id = generate_id()
        self.options = ensure_dotted_dict(options)
        self.setter = None
        self.getter = None
        self._subscriptions = set()
        self.disable_publishing = False
        self._emitter = Emitter()

    def emit(self, value, options=None):
        return self._emit(value, ensure_dotted_dict(options))

    def _emit(self, value, options=None):

        options = ensure_dotted_dict(options)

        _value = value
        if self.setter != None:
            adapted = ensure_dotted_dict(self.setter(value, options))
            if not adapted.valid:
                return False
            _value = adapted.data
        # Assign the Value (either use it directly or use the getter)
        _value = self.getter(_value) if self.getter is not None else _value
        if options.forced or (self.disable_publishing == False):
            options = self._update_sender_and_timestamp(options)
            self._emitter.emit(data=DottedDict({'value': _value, **options}))
            return self.has_subscriptions
        return False

    def _update_sender_and_timestamp(self, options: DottedDict):
        if not options.sender:
            options.sender = self.id
        if self.options.generate_timestamp:
            options.timestamp = options.get("timestamp", get_timestamp())
        return options

    def dispose(self):
        for _unsubscribe in self._subscriptions:
            _unsubscribe()
        self._subscriptions.clear()
        self._emitter.close()

    def subscribe(self, callback,
                  options: dict | DottedDict = DottedDict({'type': 'sync', 'mode': ['direct', 'sub', 'super']})):
        options = ensure_dotted_dict(options)
        options.skip_current = self.options.show_current and not self.options.play_History
        return self._subscribe(callback, options)

    def _subscribe(self, callback, options):

        active = True
        first = True

        def adapted_callback(_data: DottedDict):
            nonlocal active
            nonlocal first

            data = _data.copy()

            if first and options.skip_current:
                first = False
                return

            first = False

            if active and data != None:
                # Pop the value
                value = data.pop("value")
                # Now we call value, ... rest
                callback(value, data)

        return self._emitter.on(callback=adapted_callback)

    def once(self, callback, options=None):
        ret = None

        def adapted_callback(data, rest):
            ret.unsubscribe()
            callback(data, rest)

        ret = self.subscribe(adapted_callback, options)
        return ret

    def wait_for(self, test_callback=None, options=DottedDict({'test_current': True})):

        # Convert our Options.
        options = ensure_dotted_dict(options)

        if test_callback is None:
            # Define a Test Callback
            def test(value, *args):
                return value == True

            test_callback = test

        subscription = None

        def callback(resolve, reject):
            nonlocal subscription

            first = True
            resolved = False

            def finish(err, sucessfull, data):
                nonlocal first
                nonlocal resolved
                nonlocal subscription

                if err:
                    reject(err)
                elif sucessfull:
                    if subscription:
                        subscription.unsubscribe()
                        subscription = None
                    if not resolved:
                        resolved = True
                        resolve(data)

            def check_data(value, rest):
                nonlocal first
                nonlocal resolved
                nonlocal subscription

                if (first and options.test_current) or not first:
                    if is_async_function(test_callback):
                        # Try to offload the Function
                        prom: Future = Promise.cast(test_callback(value, rest))

                        def done(p: Future):
                            if p.done():
                                print("HERE")
                            if p.exception():
                                print("Error")

                        # prom.add_done_callback(lambda result: finish(False, result.result(), value))
                        prom.add_done_callback(done)
                        # prom.catch(lambda err: finish(err, None, None))                        
                    else:
                        result = test_callback(value, rest)
                        finish(False, result, value)

                first = False

            try:
                subscription = self.subscribe(check_data)
            except:
                reject(Exception("Failed to subscribe"))

        return Promise(callback)

    def wait_for_update(self, options=DottedDict({'test_current': True})):
        # Define a Callback
        def callback(resolve, reject):
            def cb(value, rest):
                print(value, rest)
                resolve(value)

            self.once(cb, options)

        return Promise(callback)

    @property
    def has_subscriptions(self):
        return self._emitter.has_subscriptions()

    @property
    def observer_length(self):
        return self._emitter.amount_subscriptions()
