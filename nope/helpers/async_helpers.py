import asyncio
from .prints import format_exception


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


def create_interval_in_event_loop(func, interval_ms, *args, **kwargs):
    """ Helper, which creates an

    """

    coroutine = func if is_async_function(func) else sync_function_to_async_function(func)

    async def interval(timeout):
        while True:
            await asyncio.sleep(timeout)
            await coroutine(*args, **kwargs)

    task = asyncio.create_task(interval(interval_ms / 1000.0))

    return lambda: task.cancel()


def create_timeout_in_event_loop(func, timeout_ms, *args, **kwargs):
    """ Helper, which creates a delayed call of the function.

    """

    coroutine = func if is_async_function(func) else sync_function_to_async_function(func)

    async def delay(timeout):
        await asyncio.sleep(timeout)
        await coroutine(*args, **kwargs)

    task = asyncio.create_task(delay(timeout_ms / 1000.0))

    return lambda: task.cancel()


def sync_function_to_async_function(func):
    """ Helper to convert a synchronous function to an async function (coroutine) in an extra thread.
    """
    return lambda *args, **kwargs: asyncio.to_thread(func, *args, **kwargs)


def offload_function_to_event_loop(func, *args, **kwargs):
    """ Helper Function to perform a Method in a separate Thread,
        Therefore you will receive an async function which will be
        called in the background.
    """

    asyncio.ensure_future(sync_function_to_async_function(func)(*args, **kwargs))


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

    if not is_async_function(callback):
        offload_function_to_event_loop(callback, resolve, reject)
    else:
        asyncio.ensure_future(callback(resolve, reject))

    return future
