#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ..event_emitter import NopeEventEmitter
from ..helpers import DottedDict, ensure_dotted_dict, generate_id


class NopeObservable(NopeEventEmitter):
    """ An Observable storing the last value in `content`.
    """

    def __init__(self, options=None):

        if options is None:
            options = DottedDict()

        options.update({'show_current': True})
        super().__init__(options)
        self.id = generate_id()
        self._value = None
        self._last_value = None
        self._last_rest = None

    @property
    def emitter(self):
        return self._emitter

    def set_content(self, value, options=None):
        return self._emit(value, options)

    def _emit(self, value, options=None):
        options = ensure_dotted_dict(options)
        if self.setter is not None and callable(self.setter):
            adapted = ensure_dotted_dict(self.setter(value, options))
            if not adapted.valid:
                return False
            self._value = adapted.data
        else:
            self._value = value
        value_to_publish = self.get_content()
        if (not self.disable_publishing) and (options.forced or not (self._last_value == value_to_publish)):
            return self._publish(value_to_publish, options)
        return False

    def emit(self, *args, **kwargs):
        raise NotImplementedError("Not implemeneted on an Observable.")

    def _publish_specific(self, observer):
        if self._last_rest is not None:
            # Call the last rest
            observer(self._last_value, self._last_rest)

    def _publish(self, value, options=None):
        options = ensure_dotted_dict(options)
        if options.forced or not self.disable_publishing:
            options = self._update_sender_and_timestamp(options)
            self._last_rest = options
            self._last_value = value
            self._emitter.emit(data=ensure_dotted_dict({'value': value, **options}))
            return self.has_subscriptions
        return False

    def force_publish(self, options=None):
        options = ensure_dotted_dict(options)
        options.forced = True
        return self._publish(self.get_content(), options)

    def get_content(self):
        if self.getter is not None:
            return self.getter(self._value)
        return self._value

    @property
    def content(self):
        return self.get_content()

    def subscribe(self, observer, options=None):
        if options is None:
            options = {'type': 'sync', 'mode': [
                'direct', 'sub', 'super'], 'skip_current': False}

        res = self._subscribe(observer, ensure_dotted_dict(options))

        # Because we are an observerable -> we will send the update:
        self._publish_specific(observer)

        return res
