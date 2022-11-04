# @author Martin Karkowski
# @email m.karkowski@zema.de
# @desc [description]

import asyncio
import threading
import time
from asyncio import iscoroutinefunction

from .asyncHelpers import getOrCreateEventloop


class setInterval:
    """ Starts an interval, on which the function will be called.
    """

    def __init__(self, func, interval, *args):
        self.interval = interval / 1000
        self._is_coroutine = iscoroutinefunction(func)
        self._loop = None if not self._is_coroutine else getOrCreateEventloop()
        self.func = func
        self.args = args
        self.stop_event = threading.Event()
        self._thread = threading.Thread(target=self.__run)
        self._thread.start()

    def __run(self):
        next_time = time.time() + self.interval
        if self._is_coroutine:
            loop = getOrCreateEventloop()
            asyncio.set_event_loop(loop)

            while not self.stop_event.wait(next_time - time.time()):
                next_time += self.interval
                asyncio.run_coroutine_threadsafe(self.func(*self.args))

        else:
            while not self.stop_event.wait(next_time - time.time()):
                next_time += self.interval
                self.func(*self.args)

    def cancel(self):
        self.stop_event.set()


def setTimeout(func, msec, *args):
    """ Calls the function delayed.
    """
    if iscoroutinefunction(func):
        def func_wrapper():
            loop = getOrCreateEventloop()
            asyncio.set_event_loop(loop)
            asyncio.run_coroutine_threadsafe(func(*args))

        t = threading.Timer(msec / 1000.0, func_wrapper)
        t.start()
        return t
    else:
        def func_wrapper():
            func(*args)

        t = threading.Timer(msec / 1000.0, func_wrapper)
        t.start()
        return t
