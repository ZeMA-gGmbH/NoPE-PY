import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial

from .prints import formatException


def isAsyncFunction(func) -> bool:
    """ Test whether the function is defined async or not.

    Args:
        func (_type_): _description_

    Returns:
        bool: _description_
    """
    return asyncio.iscoroutinefunction(func)


def getOrCreateEventloop():
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
        else:
            raise ex


class NopeExecutor:

    def __init__(self, loop: asyncio.AbstractEventLoop = None,
                 executor: ThreadPoolExecutor | ProcessPoolExecutor = None):
        self._loop: asyncio.AbstractEventLoop = loop
        self._executor: ThreadPoolExecutor | ProcessPoolExecutor = executor
        if self._loop is None:
            self._loop = getOrCreateEventloop()

        self.logger = None
        self._todos = set()

        # asyncio.set_event_loop(self._loop)

    def assignLoop(self, loop, forceDefaultToBeDefaultLoop=False):
        """ Helper to assign a event loop.

        Args:
            loop (_type_): _description_
            forceDefaultToBeDefaultLoop (bool, optional): _description_. Defaults to False.
        """
        self._loop = loop

        if self.logger:
            self.logger.warn("Use this function with care!")

        if forceDefaultToBeDefaultLoop:
            asyncio.set_event_loop(self._loop)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def useThreadPool(self, max_workers=None):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def useMultiProcessPool(self, max_workers=None):
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

    def generatePromise(self, **kwargs):
        """ Helper to create an Future.

            The keys and values of the future are df

        Returns:
            asyncio.Future: A Future
        """

        future = self.loop.create_future()

        def _cancel():
            pass

        setattr(future, 'cancelCallback', _cancel)

        for k, v in kwargs.items():
            if not hasattr(future, k):
                setattr(future, k, v)
            else:
                raise Exception(
                    f"You cant use the name {k}. It is predefined by the original Future.")

        return self.ensureExecution(future)

    def ensureExecution(self, todo):
        if isinstance(todo, (asyncio.Task, asyncio.Future)):
            self._todos.add(todo)

            def remove(*args, **kwargs):
                self._todos.remove(todo)

            todo.add_done_callback(remove)

        return todo

    def setTimeout(self, func, timeout_ms: int, *args, **kwargs):
        function_to_use = self._wrapFuncIfRequired(func)

        async def timeout():
            try:
                await asyncio.sleep(timeout_ms / 1000.0)
                await function_to_use(*args, **kwargs)
            except Exception as error:
                if self.logger:
                    self.logger.error(
                        "Exception raised during executing 'setTimeout'")
                    self.logger.error(formatException(error))
                else:
                    print(formatException(error))

        task = self.loop.create_task(timeout())

        return self.ensureExecution(task)

    def setInterval(self, func, timeout_ms: int, *args, **kwargs):
        function_to_use = self._wrapFuncIfRequired(func)

        async def interval():
            try:
                while True:
                    await asyncio.sleep(timeout_ms / 1000.0)
                    await function_to_use(*args, **kwargs)
            except Exception as error:
                if self.logger:
                    self.logger.error(
                        "Exception raised during executing 'interval'")
                    self.logger.error(formatException(error))
                else:
                    print(formatException(error))

        task = self.loop.create_task(interval())

        return self.ensureExecution(task)

    def callParallel(self, func, *args, **
                     kwargs) -> asyncio.Task | asyncio.Future:
        function_to_use = self._wrapFuncIfRequired(func)
        task = self.loop.create_task(function_to_use(*args, **kwargs))
        return self.ensureExecution(task)

    def _wrapFuncIfRequired(self, func):
        if not callable(func):
            raise TypeError("The parameter 'func' is not callable")

        if not asyncio.iscoroutinefunction(func):
            async def run(*args, **kwargs):
                pfunc = partial(func, *args, **kwargs)
                try:
                    return await self.loop.run_in_executor(self._executor, pfunc)
                except Exception as error:
                    if self.logger:
                        self.logger.error(
                            "Exception raised during executing a wrapped sync method '_wrapFuncIfRequired'")
                        self.logger.error(formatException(error))
                    else:
                        print(formatException(error))

            return run
        else:
            return func


EXECUTOR = NopeExecutor()
EXECUTOR.useThreadPool()


def Promise(callback):
    """ Creates a NodeJS like Promise

    Args:
        callback (function or coroutine): The function receiving resolve and reject. Best to be sync.

    Returns:
        Future: The awaitable Future.
    """
    future = EXECUTOR.loop.create_future()

    def reject(error):
        if future.done():
            print(formatException(Exception("Called 'reject' multiple times")))
            return
        future.set_exception(error)

    def resolve(value):
        if future.done():
            print(formatException(Exception("Called 'resolve' multiple times")))
            return
        future.set_result(value)

    # Now we want call the callback in an extra thread.
    EXECUTOR.callParallel(callback, resolve, reject)

    return future
