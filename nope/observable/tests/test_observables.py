import asyncio

import pytest

from ..nopeObservable import NopeObservable
from ...helpers import EXECUTOR
from ...helpers import formatException


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

    observable = NopeObservable()
    observable.once(callback)

    observable.setContent(1)

    assert called == 1


def test_inital_value():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.setContent("This is a Test!")
    observable.subscribe(callback)
    observable.setContent(1)

    assert called == 2
    assert observable.getContent() == 1


def test_change_detection():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.setContent(1)
    observable.subscribe(callback)
    observable.setContent(1)
    observable.setContent(1)
    observable.setContent(1)
    observable.setContent(2)

    assert called == 2
    assert observable.getContent() == 2


def test_setter():
    def callback(data, *args, **kwargs):
        assert data == "Hello World!"

    def setter(data, rest):
        return {
            "valid": True,
            "data": f"Hello {data}!"
        }

    observable = NopeObservable()
    observable.setter = setter
    observable.subscribe(callback)

    observable.setContent("World")


def test_getter():
    def callback(data, *args, **kwargs):
        assert data == "Hello World!"

    def getter(data):
        return f"{data}!"

    observable = NopeObservable()
    observable.getter = getter
    sub = observable.subscribe(callback)

    observable.setContent("Hello World")


def test_options():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.setContent(1)
    sub = observable.subscribe(callback, {"skipCurrent": True})
    observable.setContent(2)

    assert called == 1, "Failed to skip the current value"


async def test_waitFor():
    import asyncio
    import time

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    obs = NopeObservable()
    obs.setContent(True)

    await obs.waitFor()

    obs.setContent(False)

    def change_value():
        try:
            time.sleep(0.1)
            obs.setContent(True)
        except Exception as e:
            print(formatException(e))

    try:
        EXECUTOR.callParallel(change_value)

        await obs.waitFor()
    except Exception as e:
        print(formatException(e))
