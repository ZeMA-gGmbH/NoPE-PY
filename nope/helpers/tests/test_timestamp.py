import pytest

from ..timestamp import getTimestamp
from ...helpers import EXECUTOR


import asyncio


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


def test_comparePatternAndPath():
    return isinstance(getTimestamp(), int)
