from ..nope_data_pub_sub_system import DataPubSubSystem
import pytest

from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_pub_sub_system():
    pub_sub = DataPubSubSystem()

    pub_sub.pushData("", {"this": "is a test"})
    assert pub_sub.data == {"this": "is a test"}

    pub_sub.pushData("this", "is a test")
    assert pub_sub.data == {"this": "is a test"}

    pub_sub.pushData("test", {"a": 1337, "b": 1337})
    res = pub_sub.patternbasedPullData("test/+")

    assert len(res) == 2, "Failed with 'patternbasedPullData'"
    assert {"path": "test/a",
            "data": 1337} in res, "Failed with 'patternbasedPullData'"
    assert {"path": "test/b",
            "data": 1337} in res, "Failed with 'patternbasedPullData'"

    pub_sub.pushData("test", {"a": 1337, "b": {"c": 1337}})
    res = pub_sub.patternbasedPullData("test/+")

    assert len(res) == 2, "Failed with 'patternbasedPullData'"
    assert {"path": "test/a",
            "data": 1337} in res, "Failed with 'patternbasedPullData'"
    assert {"path": "test/b", "data": {"c": 1337}
            } in res, "Failed with 'patternbasedPullData'"

    res = pub_sub.patternbasedPullData("+/a")
    assert len(res) == 1, "Failed with 'patternbasedPullData'"
    assert {"path": "test/a",
            "data": 1337} in res, "Failed with 'patternbasedPullData'"

    res = pub_sub.patternbasedPullData("test/#")
    assert len(res) == 3, "Failed with 'patternbasedPullData'"
