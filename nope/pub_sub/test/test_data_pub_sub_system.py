from cmath import exp
from ..nope_data_pub_sub_system import DataPubSubSystem
from ...eventEmitter import NopeEventEmitter


def test_pub_sub_system():
    pub_sub = DataPubSubSystem()

    pub_sub.push_data("", {"this": "is a test"})
    assert pub_sub.data == {"this": "is a test"}

    pub_sub.push_data("this", "is a test")
    assert pub_sub.data == {"this": "is a test"}

    pub_sub.push_data("test", {"a": 1337, "b": 1337})
    res = pub_sub.patternbased_pull_data("test/+")

    assert len(res) == 2, "Failed with 'patternbased_pull_data'"
    assert {"path": "test/a",
            "data": 1337} in res, "Failed with 'patternbased_pull_data'"
    assert {"path": "test/b",
            "data": 1337} in res, "Failed with 'patternbased_pull_data'"

    pub_sub.push_data("test", {"a": 1337, "b": {"c": 1337}})
    res = pub_sub.patternbased_pull_data("test/+")

    assert len(res) == 2, "Failed with 'patternbased_pull_data'"
    assert {"path": "test/a",
            "data": 1337} in res, "Failed with 'patternbased_pull_data'"
    assert {"path": "test/b", "data":  {"c": 1337}
            } in res, "Failed with 'patternbased_pull_data'"

    res = pub_sub.patternbased_pull_data("+/a")
    assert len(res) == 1, "Failed with 'patternbased_pull_data'"
    assert {"path": "test/a",
            "data": 1337} in res, "Failed with 'patternbased_pull_data'"

    res = pub_sub.patternbased_pull_data("test/#")    
    assert len(res) == 3, "Failed with 'patternbased_pull_data'"

