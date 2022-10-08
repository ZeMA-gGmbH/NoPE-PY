import asyncio
from .prints import format_exception
from functools import partial
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def is_async_function(func) -> bool:
    """ Test whether the function is defined async or not.

    Args:
        func (_type_): _description_

    Returns:
        bool: _description_
    """
    return asyncio.iscoroutinefunction(func)


def get_or_create_eventloop():
    """ Creates or gets the default Eventloop.

    Returns:
        EventLoop: The determine Eventloop
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

def get_or_create_eventloop():
    """ Creates or gets the default Eventloop.

    Returns:
        EventLoop: The determine Eventloop
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


class NopeExecutor:

    def __init__(self, loop: asyncio.AbstractEventLoop = None, executor: ThreadPoolExecutor | ProcessPoolExecutor = None):
        self._loop: asyncio.AbstractEventLoop = loop
        self._executor: ThreadPoolExecutor | ProcessPoolExecutor = executor
        if self._loop is None:
            self._loop = get_or_create_eventloop()

        asyncio.set_event_loop(self._loop)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def use_thread_pool(self, max_workers = None):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def use_multi_process_pool(self, max_workers = None):
        self._executor = ProcessPoolExecutor(max_workers=max_workers)

    def dispose(self, wait=True, cancel_futures=False):
        if self._executor:
            self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

        self.loop.stop()
        self.loop.close()

    def run(self):
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.dispose()

    def set_timeout(self, func, timeout_ms: int, *args, **kwargs):
        function_to_use = self._wrap_func_if_required(func)

        async def timeout():
            await asyncio.sleep(timeout_ms / 1000.0)
            await function_to_use(*args, **kwargs)

        task = asyncio.ensure_future(timeout())

        return task

    def set_interval(self, func, timeout_ms: int, *args, **kwargs):
        function_to_use = self._wrap_func_if_required(func)

        async def interval():
            while True:
                await asyncio.sleep(timeout_ms/1000.0)
                print("here")
                await function_to_use(*args, **kwargs)

        task = asyncio.ensure_future(interval())

        return task

    def call_parallel(self, func, *args, **kwargs) -> asyncio.Task | asyncio.Future:
        function_to_use = self._wrap_func_if_required(func)
        task = asyncio.ensure_future(function_to_use(*args, **kwargs))
        return task

    def _wrap_func_if_required(self, func):
        if not callable(func):
            raise TypeError("The parameter 'func' is not callable")

        if not asyncio.iscoroutinefunction(func):
            async def run(*args, **kwargs):
                pfunc = partial(func, *args, **kwargs)
                return await self._loop.run_in_executor(self._executor, pfunc)
            return run
        else:
            return func


EXECUTOR = NopeExecutor()
EXECUTOR.use_thread_pool()

def Promise(callback):
    """ Creates a NodeJS like Promise

    Args:
        callback (function or coroutine): The function receiving resolve and reject. Best to be sync.

    Returns:
        Future: The awaitable Future.
    """
    future = asyncio.Future()

    def reject(error):
        if future.done():
            print(format_exception(Exception("Called 'reject' multiple times")))
            return
        future.set_exception(error)

    def resolve(value):
        if future.done():
            print(format_exception(Exception("Called 'resolve' multiple times")))
            return
        future.set_result(value)

    # Now we want call the callback in an extra thread.
    EXECUTOR.call_parallel(callback,resolve, reject)

    return future
