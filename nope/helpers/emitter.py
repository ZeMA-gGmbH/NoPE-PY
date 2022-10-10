from .dotted_dict import ensureDottedAccess


class Emitter:
    """ A Event Emitter. This event emitter is used to listen to specific events and emit events.
        Therefore callbacks are registered with the method `on` and can be removed with `off`.
        An event is emitted using `emit`. To close the emitter -> no event will be forwarded

    """

    def __init__(self) -> None:
        """ Creates the Emitter.
        """
        self._subscribers = dict()
        self._paused = set()

    def on(self, event: str = None, callback=None):
        """ Adds a callback to the emitter. If fire event is emitted, the subscriber (callback) will be called.
        Args:
            event (str, optional): The event under which the callback is listening. Defaults to None.
            callback (callable, optional):  The callback to be called. Defaults to None.
                                            The Callback needs to receive `*args` and `**kwargs`

        Raises:
            TypeError: Raised, if the callback isnt callable.
        """
        if event not in self._subscribers:
            self._subscribers[event] = set()

        if not callable(callback):
            raise TypeError("The parameter 'callback', must be callable!")

        self._subscribers[event].add(callback)

        ret = ensureDottedAccess({
            'pause': lambda: self._pause(callback),
            'unpause': lambda: self._unpause(callback),
            'unsubscribe': lambda: self.off(event=event, callback=callback)
        })

        return ret

    def off(self, event: str = None, callback=None) -> bool:
        """ Removes the callback. Then it wont be called if an event has been emitted.

        Args:
            event (str, optional): The event under which the callback is subscribed. Defaults to None.
            callback (callable, optional): The Callback to remove. Defaults to None.
        Returns:
            bool:   True -> removed (has been present); False -> could not remove the callback (was not
                    subscribed for that event)
        """

        try:
            self._paused.remove(callback)
        except BaseException:
            pass

        if event in self._subscribers:
            try:
                self._subscribers[event].remove(callback)
                return True
            except BaseException:
                return False
        return False

    def _pause(self, callback):
        self._paused.add(callback)

    def _unpause(self, callback):
        try:
            self._paused.remove(callback)
        except BaseException:
            pass

    def emit(self, event: str = None, data=None, *args, **kwargs):
        """ Emits an event on with the given data.

        Args:
            event (str, optional): _description_. Defaults to None.
            data (optional): _description_. Defaults to None.
        """
        if event in self._subscribers:
            items = list(self._subscribers[event])
            for sub in items:
                if sub not in self._paused:
                    sub(data, *args, **kwargs)

    def close(self):
        """ Deletes all Subscribers.
        """
        self._subscribers = dict()
        self._paused = set()

    def amountOfSubscriptions(self, event=None) -> int:
        """ Returns, whether there are some subscribers listening.

        Returns:
            bool: _description_
        """

        if event is None:

            amount = 0

            for subs in self._subscribers.values():
                amount = amount + len(subs)

            return amount

        elif event in self._subscribers:
            return len(self._subscribers[event])
        return 0

    def hasSubscriptions(self, event=None) -> bool:
        return self.amountOfSubscriptions(event) > 0
