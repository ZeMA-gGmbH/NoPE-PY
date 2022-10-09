import pytest

from ..merge_data import DictBasedMergeData, MergeData
from ...helpers import EXECUTOR
from ...helpers.dict_methods import extractUniqueValues


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_merge_data_general():
    d = dict()
    merge = MergeData(d, extractUniqueValues)

    d["a"] = "b"
    d["b"] = "b"

    merge.update()

    r = merge.data.getContent()
    assert len(r) == 1, "Failed to convert the data"
    assert r[0] == "b", "Extracted and stored the correct value"

    d = dict()
    merge = MergeData(d, extractUniqueValues)

    called = 0

    def callback_01(data, *args, **kwargs):
        nonlocal called
        called += 1

    merge.data.subscribe(callback_01)

    d["a"] = "b"
    d["b"] = "b"

    merge.update()
    merge.update()

    r = merge.data.getContent()
    assert called == 2, "Called the subscription to many times"

    d = dict()
    merge = MergeData(d, extractUniqueValues)

    called = 0

    def callback_02(data, *args, **kwargs):
        nonlocal called
        called += 1
        assert len(data.added) == 1
        assert len(data.removed) == 0
        assert list(data.added)[0] == "b"

    merge.onChange.subscribe(callback_02)

    d["a"] = "b"
    d["b"] = "b"

    merge.update()
    merge.update()

    assert called == 1, "Called the subscription to many times"


def test_dict_based_merge_data():
    d = dict()
    merge = DictBasedMergeData(d)

    d["a"] = "b"
    d["b"] = "b"

    merge.update()
    assert "b" in merge.keyMappingreverse

    d = {
        "a": {"key": "keyA", "data": "dataA"},
        "b": {"key": "keyB", "data": "dataB"}
    }
    merge = DictBasedMergeData(d, "data", "key")
    merge.update()
    assert "keyA" in merge.keyMappingreverse
    assert "a" in merge.keyMapping
    assert "dataA" in merge.data.getContent()
    assert "keyA" in merge.simplified
