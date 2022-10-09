import pytest

from ..timestamp import getTimestamp
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_comparePatternAndPath():
    return type(getTimestamp()) is int
