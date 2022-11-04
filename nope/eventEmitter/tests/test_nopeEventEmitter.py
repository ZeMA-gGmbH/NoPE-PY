import asyncio
from time import sleep

import pytest

from ..nopeEventEmitter import NopeEventEmitter
from ...helpers import EXECUTOR
from ...helpers import getTimestamp, formatException, DottedDict


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


def test_once():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    emitter = NopeEventEmitter()
    emitter.once(callback=callback)

    emitter.emit(getTimestamp())
    sleep(0.1)
    emitter.emit(getTimestamp())

    assert called == 1


async def test_wait_for_update():
    import asyncio
    emitter = NopeEventEmitter()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def emit_event():
        try:
            sleep(0.1)
            emitter.emit(True)
        except Exception as e:
            print(formatException(e))

    try:
        EXECUTOR.callParallel(emit_event)
        value = await emitter.waitForUpdate()
    except Exception as e:
        print(formatException(e))


async def test_wait_for():
    import asyncio
    emitter = NopeEventEmitter()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    counter = 0

    def emit_event():
        try:
            for i in range(6):
                sleep(0.01)
                emitter.emit(counter)
        except Exception as e:
            print(formatException(e))

    try:
        EXECUTOR.callParallel(emit_event)

        def test(value, *args):
            nonlocal counter
            counter += 1

            return value == 5

        value = await emitter.waitFor(test)
    except Exception as e:
        print(formatException(e))


def test_pausing():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    emitter = NopeEventEmitter()
    sub = emitter.subscribe(callback)

    emitter.emit(1)
    sub.pause()
    emitter.emit(2)
    sub.unpause()
    emitter.emit(3)

    assert called == 2, "Failed to pause the subscripion"

    sub.unsubscribe()
    emitter.emit(4)

    assert called == 2, "Failed to unsubscribe the subscription"


def test_setter():
    def callback(data, *args, **kwargs):
        assert data == "Hello World!"

    def setter(data, rest):
        return DottedDict({
            "valid": True,
            "data": f"Hello {data}!"
        })

    emitter = NopeEventEmitter()
    emitter.setter = setter
    sub = emitter.subscribe(callback)

    emitter.emit("World")


def test_getter():
    def callback(data, *args, **kwargs):
        assert data == "Hello World!"

    def getter(data):
        return f"{data}!"

    emitter = NopeEventEmitter()
    emitter.getter = getter
    sub = emitter.subscribe(callback)

    emitter.emit("Hello World")


def test_order():
    called = []

    def callback(data, *args, **kwargs):
        nonlocal called
        called.append(data)

    emitter = NopeEventEmitter()
    sub = emitter.subscribe(callback)

    emitter.emit(1)
    emitter.emit(2)
    emitter.emit(3)

    assert called == [1, 2, 3], "Failed to maintain the order"
