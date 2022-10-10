import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial


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


class NopeExecutor:

    def __init__(self, loop: asyncio.AbstractEventLoop = None,
                 executor: ThreadPoolExecutor | ProcessPoolExecutor = None):
        self._loop: asyncio.AbstractEventLoop = loop
        self._executor: ThreadPoolExecutor | ProcessPoolExecutor = executor
        if self._loop is None:
            self._loop = getOrCreateEventloop()

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

    def setTimeout(self, func, timeout_ms: int, *args, **kwargs):
        function_to_use = self._wrapFuncIfRequired(func)

        async def timeout():
            await asyncio.sleep(timeout_ms / 1000.0)
            await function_to_use(*args, **kwargs)

        task = self.loop.create_task(timeout())

        return task

    def setInterval(self, func, timeout_ms: int, *args, **kwargs):
        function_to_use = self._wrapFuncIfRequired(func)

        async def interval():
            while True:
                await asyncio.sleep(timeout_ms / 1000.0)
                await function_to_use(*args, **kwargs)

        task = self.loop.create_task(interval())

        return task

    def callParallel(self, func, *args, **
                     kwargs) -> asyncio.Task | asyncio.Future:
        function_to_use = self._wrapFuncIfRequired(func)

        task = self.loop.create_task(function_to_use(*args, **kwargs))
        return task

    def _wrapFuncIfRequired(self, func):
        if not callable(func):
            raise TypeError("The parameter 'func' is not callable")

        if not asyncio.iscoroutinefunction(func):
            async def run(*args, **kwargs):
                pfunc = partial(func, *args, **kwargs)
                try:
                    # return await
                    # asyncio.run_coroutine_threadsafe(func(*args,**kwargs),self.loop)
                    return await self.loop.run_in_executor(self._executor, pfunc)
                except Exception as error:
                    print(error)

            return run
        else:
            return func


EXECUTOR = NopeExecutor()
EXECUTOR.useThreadPool()


def long_sync():
    import time
    print("in call")
    time.sleep(1)
    print("done")


for i in range(10):
    EXECUTOR.callParallel(long_sync)

t = EXECUTOR.setInterval(print, 100, "hello world")
EXECUTOR.setTimeout(lambda *args: t.cancel(), 500)

EXECUTOR.run()
