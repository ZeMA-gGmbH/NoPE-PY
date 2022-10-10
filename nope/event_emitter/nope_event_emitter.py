from asyncio import Future

from ..helpers import generateId, DottedDict, Emitter, ensureDottedAccess, isAsyncFunction, getTimestamp, Promise


# from ..logger.getLogger import getNopeLogger
# logger = getNopeLogger('obervable')


class NopeEventEmitter:

    def __init__(self, options=None):
        self.id = generateId()
        self.options = ensureDottedAccess({'generateTimestamp': True})
        self.options.update(ensureDottedAccess(options))
        self.setter = None
        self.getter = None
        self._subscriptions = set()
        self.disablePublishing = False
        self._emitter = Emitter()

    def emit(self, value, options=None):
        return self._emit(value, ensureDottedAccess(options))

    def _emit(self, value, options=None):

        options = ensureDottedAccess(options)

        _value = value
        if self.setter is not None:
            adapted = ensureDottedAccess(self.setter(value, options))
            if not adapted.valid:
                return False
            _value = adapted.data
        # Assign the Value (either use it directly or use the getter)
        _value = self.getter(_value) if self.getter is not None else _value
        if options.forced or (self.disablePublishing == False):
            options = self._updateSenderAndTimestamp(options)
            self._emitter.emit(data=ensureDottedAccess(
                {'value': _value, **options}))
            return self.hasSubscriptions
        return False

    def _updateSenderAndTimestamp(self, options: DottedDict):
        if not options.sender:
            options.sender = self.id
        if self.options.generateTimestamp:
            options.timestamp = options.get("timestamp", getTimestamp())
        return options

    def dispose(self):
        for _unsubscribe in self._subscriptions:
            _unsubscribe()
        self._subscriptions.clear()
        self._emitter.close()

    def subscribe(self, callback,
                  options: dict | DottedDict = DottedDict({'type': 'sync', 'mode': ['direct', 'sub', 'super']})):
        options = ensureDottedAccess(options)
        options.skipCurrent = self.options.showCurrent and not self.options.playHistory
        return self._subscribe(callback, options)

    def _subscribe(self, callback, options):

        active = True
        first = True

        def adaptedCallback(_data: DottedDict):
            nonlocal active
            nonlocal first

            data = _data.copy()

            if first and options.skipCurrent:
                first = False
                return

            first = False

            if active and data is not None:
                # Pop the value
                value = data.pop("value")
                # Now we call value, ... rest
                callback(value, data)

        return self._emitter.on(callback=adaptedCallback)

    def once(self, callback, options=None):
        ret = None

        def adaptedCallback(data, rest):
            ret.unsubscribe()
            callback(data, rest)

        ret = self.subscribe(adaptedCallback, options)
        return ret

    def waitFor(self, testCallback=None, _options=None):

        # Convert our Options.

        options = ensureDottedAccess({'testCurrent': True})
        options.update(ensureDottedAccess(_options))

        if testCallback is None:
            # Define a Test Callback
            def test(value, *args):
                return value == True

            testCallback = test

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

                if (first and options.testCurrent) or not first:
                    if isAsyncFunction(testCallback):
                        # Try to offload the Function
                        prom: Future = Promise.cast(testCallback(value, rest))

                        def done(p: Future):
                            if p.done():
                                print("HERE")
                            if p.exception():
                                print("Error")

                        # prom.add_done_callback(lambda result: finish(False, result.result(), value))
                        prom.add_done_callback(done)
                        # prom.catch(lambda err: finish(err, None, None))
                    else:
                        result = testCallback(value, rest)
                        finish(False, result, value)

                first = False

            try:
                subscription = self.subscribe(check_data)
            except BaseException:
                reject(Exception("Failed to subscribe"))

        return Promise(callback)

    def waitForUpdate(self, options=DottedDict({'testCurrent': True})):
        # Define a Callback
        def callback(resolve, reject):
            def cb(value, rest):
                resolve(value)

            self.once(cb, options)

        return Promise(callback)

    @property
    def hasSubscriptions(self):
        return self._emitter.hasSubscriptions()

    @property
    def observerLength(self):
        return self._emitter.amountOfSubscriptions()
