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
    """ Helper for async execution. The executor helps you to run sync functions in extra threads
        in a compatible manner to NoPE.
    """

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
        """ Returns the used loop

        Returns:
            asyncio.AbstractEventLoop: The internally used loop
        """
        return self._loop

    def useThreadPool(self, max_workers=None):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def useMultiProcessPool(self, max_workers=None):
        self._executor = ProcessPoolExecutor(max_workers=max_workers)

    def dispose(self, wait=True, cancel_futures=False):
        """ Disposes the Executor """
        if self._executor:
            self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

        self.loop.stop()
        self.loop.close()

    def run(self):
        """ Starts the eventloop and runs it forever """
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
        """ Make shure, the future / task is being executed. The user do not need to store the
            item to prevent the garbage collector to remove it.

        Args:
            todo (Future | Task): The item to take care of

        Returns:
            Future | Task: The item.
        """
        if isinstance(todo, (asyncio.Task, asyncio.Future)):

            self._todos.add(todo)

            def remove(*args, **kwargs):
                self._todos.remove(todo)

            todo.add_done_callback(remove)

        return todo

    def setTimeout(self, func, timeout_ms: int, *args, **kwargs):
        """ Function to call the function after the delay.

        Args:
            func (function): The function to call.
            timeout_ms (int): Delay in ms.

        Returns:
            asyncio.Task: The task, executing the timeout.
        """
        function_to_use = self.wrapFuncIfRequired(func)

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

    def setInterval(self, func, interval_ms: int, *args,
                    **kwargs) -> asyncio.Task:
        """ Creates an interval which will be called

        Args:
            func (function): The function to call.
            interval_ms (int): Interval in ms.

        Returns:
            asyncio.Task: The task, executing the interval.
        """
        function_to_use = self.wrapFuncIfRequired(func)

        async def interval():
            try:
                while True:
                    await asyncio.sleep(interval_ms / 1000.0)
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
        """ Helper, which will call the function in the Background.


        Args:
            func (function): The function, which should be called in parallel

        Returns:
            asyncio.Task | asyncio.Future: The Task for the Function.
        """
        function_to_use = self.wrapFuncIfRequired(func)
        task = self.loop.create_task(function_to_use(*args, **kwargs))
        return self.ensureExecution(task)

    def wrapFuncIfRequired(self, func):
        """ Helper to asyncify a the provided function if requried. If it is already a coroutine,
            we will return this, otherwise the function will be wrapped into an async function.

        Args:
            func (function): The function, which must be will be wrapped

        Returns:
            corutine: The function as async function
        """
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
# EXECUTOR.useThreadPool()


def Promise(callback):
    """ Creates a NodeJS like Promise

    Args:
        callback (function or coroutine): The function receiving resolve and reject. Best to be sync.

    Returns:
        Future: The awaitable Future.
    """
    future = EXECUTOR.generatePromise()

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
    callback(resolve, reject)    

    return future


async def waitFor(callback, initalWaitInMs: int = None, testFirst: bool = True, maxRetries: int = float("inf"), delay: int = 50, maxTimeout: int = None, additionalDelay: int = None):
    """ Function which will wait for the callback to return true

    Args:
        callback (function): The Callback which will be checkt with the given delay. The Function must return a boolean value. It can be a coroutine.
        initalWaitInMs (int, optional): First amount of time to wait. Defaults to None.
        testFirst (bool, optional): Flag to enable Testing directly (after the intial wait time). Defaults to True.
        maxRetries (int, optional): Number of allowed retries. Defaults to float("inf").
        delay (int, optional): The delay in *ms* after which the elements are tested again. Defaults to 50 [ms].
        maxTimeout (int, optional): The max Time to wait. Throws an error if reached. Defaults to None.
        additionalDelay (int, optional): _description_. Defaults to None.

    Returns:
        Promise: A Promise which can be awaited.
    """

    # Ensure our callback is async.
    asyncCallback = EXECUTOR.wrapFuncIfRequired(callback)

    # Define our callback, that we will hand over to our Promise.

    async def cb(resolve, reject):

        if initalWaitInMs:
            # We will wait
            await asyncio.sleep(initalWaitInMs / 1000.0)

        try:
            if testFirst and await asyncCallback():
                if additionalDelay:
                    await asyncio.sleep(additionalDelay / 1000.0)

                resolve(True)
                return
            else:
                retryCounter = 0

                timeout: asyncio.Task = None
                interval: asyncio.Task = None

                # If there is a Timeout, define a Timeout Function, which will
                # Throw an Error on Timeout.

                if maxTimeout:
                    def onTimeout():
                        if interval:
                            interval.cancel()

                        reject(TimeoutError("Timed out!"))

                    timeout = EXECUTOR.setTimeout(onTimeout, maxTimeout)

                # Define a Testfunction, which will periodically test whether the condition is
                # fullfield or not. Internally it counts the number of retries, if the max allowed
                # number of retries has been reached => Throw an Error

                async def inInterval():
                    try:
                        nonlocal retryCounter
                        if maxRetries and maxRetries > retryCounter:
                            # Stop the interval
                            interval.cancel()

                            if timeout:
                                timeout.cancel()

                            reject(Exception("Max Retries has been reached!"))
                        elif await asyncCallback():
                            # Stop the interval
                            interval.cancel()

                            if timeout:
                                timeout.cancel()

                            if additionalDelay:
                                await asyncio.sleep(additionalDelay / 1000.0)

                            resolve(True)

                        retryCounter += 1

                    except Exception as e:
                        # Stop the interval
                        interval.cancel()

                        if timeout:
                            timeout.cancel()

                        # Forward the Error.
                        reject(e)

                interval = EXECUTOR.setInterval(inInterval, delay)

        except Exception as e:
            reject(e)

    return Promise(cb)
