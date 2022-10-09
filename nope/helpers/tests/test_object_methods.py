import pytest

from ..object_methods import (convert_data, flatten_object, rgetattr, rquery_attr)
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def generate_dict():
    return {
        "hello_world": 1,
        "nested_data": {
            "hello": "world"
        }
    }


def test_rgetattr():
    data = generate_dict()

    result = rgetattr(data, "test", "default")
    assert result == "default"

    result = rgetattr(data, "test", None)
    assert result == None

    result = rgetattr(data, "hello_world", None)
    assert result == 1

    result = rgetattr(data, "nested_data/hello", None)
    assert result == "world"

    result = rgetattr(data, "nested_data/hello2", None)
    assert result == None


def test_flatten_object():
    data = {"deep": {"nested": "test"}}
    result = flatten_object(data)

    assert "deep/nested" in result
    assert result["deep/nested"] == "test"

    result = flatten_object(data, max_depth=1, only_path_to_simple_value=False)
    assert "deep" in result
    print(result)
    assert not ("deep/nested" in result)

    result = flatten_object(data, max_depth=1, only_path_to_simple_value=True)
    assert len(result) == 0

    result = flatten_object(data, prefix="test")
    assert "test/deep/nested" in result


def test_convert():
    data = {}
    result = convert_data(data, [
        {
            "key": "result",
            "query": "a/b",
        },
    ])
    assert len(result) == 0, "we expected 0 entries"

    data = {"deep": {"nested": "test"}}
    result = convert_data(data, [
        {
            "key": "result",
            "query": "deep/nested",
        },
    ])
    assert len(result) == 1, "we expected 1 entries"
    assert result[0].result == "test", "Expected result to be 'test'"

    result = convert_data(data, [
        {
            "key": "result",
            "query": "deep/+",
        },
    ])
    assert len(result) == 1, "we expected 1 entries"
    assert result[0].result == "test", "Expected result to be 'test'"

    data = {
        "array": [
            {
                "data1": 0,
                "data2": "a",
            },
            {
                "data1": 1,
                "data2": "b",
            },
        ],
        "not": {"nested": "hello"},
    }
    result = convert_data(data, [
        {
            "key": "a",
            "query": "array/+/data1",
        },
        {
            "key": "b",
            "query": "array/+/data2",
        },
    ]
                          )
    assert len(result) == 2, "we expected 2 entries"
    items = map(lambda item: item.a, result)

    assert (0 in items) and (1 in items)

    try:
        result = convert_data(data, [
            {
                "key": "a",
                "query": "array/+/data1",
            },
            {
                "key": "b",
                "query": "array/+/data2",
            },
        ])
        raise Exception("This should not be happend")
    except:
        pass


def test_query():
    data = {}
    result = rquery_attr(data, "test/+")
    assert len(result) == 0, "we expected 0 entries"

    data = {"deep": {"nested": "test"}}
    result = rquery_attr(data, "deep/+")
    assert len(result) == 1, "we expected 1 entries"
    assert result[0].path == "deep/nested", "we expected the path to be 'deep/nested'"
    assert result[0].data == "test", "we expected the data to be 'test'"

    data = {
        "deep": {"nested_01": {"nested_02": "test_01"}, "nested_03": "test_02"},
        "not": {"nested": "hello"},
    }
    result = rquery_attr(data, "deep/+")
    assert len(result) == 2, "we expected 2 entries"

    pathes = map(lambda item: item.path, result)
    assert (
                "deep/nested_01" in pathes and "deep/nested_03" in pathes), 'we expected the "deep/nested_01" and "deep/nested_03" have been found'

    data = {
        "array": [
            {
                "data": 0,
            },
            {
                "data": 1,
            },
        ],
        "not": {"nested": "hello"},
    }

    result = rquery_attr(data, "array/+/data")
    assert len(result) == 2, "we expected 2 entries"
    items = map(lambda item: item.data, result)
    assert (0 in items and 1 in items), 'we expected the "1" and "1" have been found'

    data = {
        "deep": {"nested_01": {"nested_02": "test_01"}, "nested_03": "test_02"},
        "not": {"nested": "hello"},
    }
    result = rquery_attr(data, "deep/#")
    assert len(result) == 3, "we expected 2 entries"
    pathes = map(lambda item: item.path, result)
    assert (
                "deep/nested_01" in pathes and "deep/nested_01/nested_02" in pathes and "deep/nested_03" in pathes), 'we expected the "deep/nested_01", "deep/nested_01/nested_02" and "deep/nested_03" have been found'
