# /**
#  * @author Martin Karkowski
#  * @email m.karkowski@zema.de
#  * @create date 2021-06-14 08:16:07
#  * @modify date 2021-06-14 08:35:51
#  * @desc [description]
#  */

import asyncio
import threading
from asyncio.coroutines import iscoroutinefunction


class FuncThread(threading.Thread):

    def __init__(self, target: callable, *args, **kwargs):
        threading.Thread.__init__(self)

        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        self._target(*self._args)


def offload_function_to_thread(func, loop):
    """ Helper Function to perform a Method in a separate Thread,
        Therefore you will receive an async function which will be
        called in the background.
    """

    loop = asyncio.get_event_loop()

    promise = loop.create_future()

    if iscoroutinefunction(func):
        # Not implemented Jet
        raise TypeError("You only are allowed to offload sync-functions")
    else:
        def _parallel(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                promise.set_result(result)
            except Exception as E:
                promise.set_exception(E)

        async def _func(*args, **kwargs):
            _main_thread = FuncThread(target=_parallel, *args, **kwargs)
            _main_thread.run()
            return await promise

        return _func
