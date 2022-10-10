#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ..eventEmitter import NopeEventEmitter
from ..helpers import DottedDict, ensureDottedAccess, generateId


class NopeObservable(NopeEventEmitter):
    """ An Observable storing the last value in `content`.
    """

    def __init__(self, options=None):

        if options is None:
            options = DottedDict()

        options.update({'showCurrent': True})
        super().__init__(options)
        self.id = generateId()
        self._value = None
        self._lastValue = None
        self._lastRest = None

    @property
    def emitter(self):
        return self._emitter

    def setContent(self, value, options=None):
        return self._emit(value, options)

    def _emit(self, value, options=None):
        options = ensureDottedAccess(options)
        if self.setter is not None and callable(self.setter):
            adapted = ensureDottedAccess(self.setter(value, options))
            if not adapted.valid:
                return False
            self._value = adapted.data
        else:
            self._value = value
        valueToPublish = self.getContent()
        if (not self.disablePublishing) and (
                options.forced or not (self._lastValue == valueToPublish)):
            return self._publish(valueToPublish, options)
        return False

    def emit(self, *args, **kwargs):
        raise NotImplementedError("Not implemeneted on an Observable.")

    def _informSpecificObserver(self, observer):
        if self._lastRest is not None:
            # Call the last rest
            observer(self._lastValue, self._lastRest)

    def _publish(self, value, options=None):
        options = ensureDottedAccess(options)
        if options.forced or not self.disablePublishing:
            options = self._updateSenderAndTimestamp(options)
            self._lastRest = options
            self._lastValue = value
            self._emitter.emit(data=ensureDottedAccess(
                {'value': value, **options}))
            return self.hasSubscriptions
        return False

    def forcePublish(self, options=None):
        options = ensureDottedAccess(options)
        options.forced = True
        return self._publish(self.getContent(), options)

    def getContent(self):
        if self.getter is not None:
            return self.getter(self._value)
        return self._value

    @property
    def content(self):
        return self.getContent()

    def subscribe(self, observer, options=None):
        if options is None:
            options = {'type': 'sync', 'mode': [
                'direct', 'sub', 'super'], 'skipCurrent': False}

        res = self._subscribe(observer, ensureDottedAccess(options))

        # Because we are an observerable -> we will send the update:
        self._informSpecificObserver(observer)

        return res
