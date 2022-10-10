import pytest

from ..dottedDict import convertToDottedDict
from ...helpers import EXECUTOR


import asyncio


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


def generate_dict():
    return {"hello_world": 1, "nested_data": {"hello": "world"}}


def test_convertToDottedDict():
    d = generate_dict()
    item = convertToDottedDict(d)

    assert item.hello_world == d["hello_world"]
    assert item.nested_data.hello == d["nested_data"]["hello"]
