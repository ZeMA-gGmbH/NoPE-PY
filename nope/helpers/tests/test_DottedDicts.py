import pytest

from ..dotted_dict import convert_to_dotted_dict
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def generate_dict():
    return {"hello_world": 1, "nested_data": {"hello": "world"}}


def test_convert_to_dotted_dict():
    d = generate_dict()
    item = convert_to_dotted_dict(d)

    assert item.hello_world == d["hello_world"]
    assert item.nested_data.hello == d["nested_data"]["hello"]
