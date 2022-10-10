import pytest

from ..nopePubSubSystem import PubSubSystem
from ...eventEmitter import NopeEventEmitter
from ...helpers import EXECUTOR

import asyncio


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


def test_pub_sub_system():
    called = 0

    pub_sub = PubSubSystem()

    publisher = NopeEventEmitter()
    subscriber = NopeEventEmitter()

    pub_sub.register(publisher, {
        "mode": "publish",
        "schema": {},
        "topic": "this/is/a/test",
    })

    pub_sub.register(subscriber, {
        "mode": "subscribe",
        "schema": {},
        "topic": "this/#",
    })

    def callback(data, rest):
        nonlocal called
        called += 1
        assert data == "Hello World"

    subscriber.subscribe(callback)
    publisher.emit("Hello World")

    assert called == 1


def test_pub_sub_system_smaller_topic():
    called = 0

    pub_sub = PubSubSystem()

    publisher = NopeEventEmitter()
    subscriber = NopeEventEmitter()

    pub_sub.register(publisher, {
        "mode": "publish",
        "schema": {},
        "topic": "this/is/a/test",
    })

    pub_sub.register(subscriber, {
        "mode": "subscribe",
        "schema": {},
        "topic": "this/is/#",
    })

    def callback(data, rest):
        nonlocal called
        called += 1
        assert data == "Hello World"

    subscriber.subscribe(callback)
    publisher.emit("Hello World")

    assert called == 1


def test_pub_sub_system_subTopic():
    called = 0

    pub_sub = PubSubSystem()

    publisher = NopeEventEmitter()
    subscriber = NopeEventEmitter()

    pub_sub.register(publisher, {
        "mode": "publish",
        "schema": {},
        "topic": "this/is/a/test",
    })

    pub_sub.register(subscriber, {
        "mode": "subscribe",
        "schema": {},
        "topic": "this/is",
    })

    def callback(data, rest):
        nonlocal called
        called += 1
        assert data == {
            "a": {
                "test": "Hello World"
            }
        }

    subscriber.subscribe(callback)
    publisher.emit("Hello World")

    assert called == 1


def test_pub_sub_multiple_wildcards():
    called = 0

    pub_sub = PubSubSystem()

    publisher = NopeEventEmitter()
    subscriber_01 = NopeEventEmitter()
    subscriber_02 = NopeEventEmitter()

    pub_sub.register(publisher, {
        "mode": "publish",
        "schema": {},
        "topic": "this/is/a/test",
    })

    pub_sub.register(subscriber_01, {
        "mode": "subscribe",
        "schema": {},
        "topic": "this/is/+/#",
    })

    pub_sub.register(subscriber_02, {
        "mode": "subscribe",
        "schema": {},
        "topic": "this/is/a/test",
    })

    def callback(data, rest):
        nonlocal called
        called += 1
        assert data == "Hello World"

    subscriber_01.subscribe(callback)
    subscriber_02.subscribe(callback)
    publisher.emit("Hello World")

    assert called == 2

    pub_sub.emit("this/is/a/test", "Hello World", {})

    assert called == 4

    # Now we will test, whether we receive an error on subscribing multiple
    # times.

    NOT_THROWN = True
    try:
        pub_sub.register(subscriber_01, {
            "mode": "subscribe",
            "schema": {},
            "topic": "this/is/+/#",
        })
        NOT_THROWN = False
    except BaseException:
        pass

    assert NOT_THROWN, "Failed to raise an error"
