import pytest

from ..timestamp import get_timestamp
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_compare_pattern_and_path():
    return type(get_timestamp()) is int
