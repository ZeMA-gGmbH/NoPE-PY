import pytest

from ..emitter import Emitter
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_subscribe_without_eventname():
    emitter = Emitter()

    done = False

    def callback(data, *args, **kwargs):
        nonlocal done
        done = True

    emitter.on(callback=callback)
    emitter.emit(data="test")

    if not done:
        raise Exception("Failed Test")


def test_subscribe_without_eventname_multiple():
    emitter = Emitter()

    call_01 = 0
    call_02 = 0

    def callback_01(data, *args, **kwargs):
        nonlocal call_01
        call_01 += 1

    def callback_02(data, *args, **kwargs):
        nonlocal call_02
        call_02 += 1

    emitter.on(callback=callback_01)
    emitter.on(callback=callback_02)
    emitter.emit(data="test")

    if (call_01 != 1 and call_02 != 1):
        raise Exception("Failed Test")

    # Call again
    emitter.emit(data="test")

    if (call_01 != 2 and call_02 != 2):
        raise Exception("Failed Test")


def test_subscribe_with_eventname():
    emitter = Emitter()

    call_01 = 0
    call_02 = 0

    def callback_01(data, *args, **kwargs):
        nonlocal call_01
        call_01 += 1

    def callback_02(data, *args, **kwargs):
        nonlocal call_02
        call_02 += 1

    emitter.on(event="01", callback=callback_01)

    assert emitter.hasSubscriptions(), "Failed to count recognize the listener"
    assert emitter.amountOfSubscriptions() == 1, "Failed to count recognize the listener"

    emitter.on(event="02", callback=callback_02)

    assert emitter.hasSubscriptions(), "Failed to count recognize the listener"
    assert emitter.amountOfSubscriptions() == 2, "Failed to count recognize the listener"
    assert emitter.amountOfSubscriptions("01") == 1, "Failed to count recognize the listener correctly"

    emitter.emit(event="01", data="test")

    if call_01 != 1 and call_02 != 0:
        raise Exception("Failed Test")

    # Now test, whether we are able to call the items multiple times
    emitter.emit(event="01", data="test")
    if call_01 != 2 and call_02 != 0:
        raise Exception("Failed calling multiple times")

    # Now test whether it will unsubscribe
    emitter.off("01", callback_01)
    emitter.emit(event="01", data="test")
    if call_01 != 2 and call_02 != 0:
        raise Exception("Failed to unsubscribe")
