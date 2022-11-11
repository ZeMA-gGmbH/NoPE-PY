from asyncio import Future

from ..helpers import generateId, DottedDict, Emitter, ensureDottedAccess, isAsyncFunction, getTimestamp, Promise, \
    EXECUTOR


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
        return self._subscribe(self._adaptCallback(callback, options))

    def _adaptCallback(self, callback, options):
        first = True

        def adaptedCallback(_data: DottedDict):
            nonlocal first

            data = _data.copy()

            if first and options.skipCurrent:
                first = False
                return

            first = False

            if data is not None:
                # Pop the value
                value = data.pop("value")
                # Now we call value, ... rest
                callback(value, data)

        return adaptedCallback

    def _subscribe(self, callback):

        return self._emitter.on(callback=callback)

    def once(self, callback, options=None):
        ret = None

        def adaptedCallback(data, rest):
            ret.unsubscribe()
            callback(data, rest)

        ret = self.subscribe(adaptedCallback, options)
        return ret

    def waitFor(self, testCallback=None, options=None):

        # Convert our Options.

        _options = ensureDottedAccess({
            'testCurrent': True,
            "timeout": 0
        })
        _options.update(ensureDottedAccess(options))

        if testCallback is None:
            # Define a Test Callback
            def test(value, *args):
                return value == True

            testCallback = test

        subscription = None
        timeout = None

        def callback(resolve, reject):
            nonlocal subscription
            nonlocal timeout

            first = True
            resolved = False

            def finish(err, sucessfull, data, timedout):
                nonlocal first
                nonlocal resolved
                nonlocal subscription
                nonlocal timeout

                if err:
                    reject(err)

                    if subscription:
                        subscription.unsubscribe()
                        subscription = None

                    if timeout and not timedout:
                        timeout.cancel()
                elif sucessfull:
                    if subscription:
                        subscription.unsubscribe()
                        subscription = None
                    if not resolved:
                        resolved = True
                        resolve(data)

                    if timeout and not timedout:
                        timeout.cancel()

            def check_data(value, rest):
                nonlocal first
                nonlocal resolved
                nonlocal subscription

                if (first and _options.testCurrent) or not first:
                    if isAsyncFunction(testCallback):
                        # Try to offload the Function
                        prom: Future = Promise.cast(testCallback(value, rest))

                        def done(p: Future):
                            nonlocal first
                            first = False

                            if p.done():
                                finish(False, True, p.result(), False)
                            if p.exception():
                                finish(p.exception(), False, False, False)

                        prom.add_done_callback(done)
                    else:
                        result = testCallback(value, rest)
                        finish(False, result, value, False)

                        first = False

            try:
                if _options.timeout > 0:
                    timeout = EXECUTOR.setTimeout(
                        finish, _options.timeout, TimeoutError("Time elapsed"), False, False, True)

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
