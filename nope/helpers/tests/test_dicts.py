import pytest

from ..dict_methods import extract_unique_values
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_extract_unique_values():
    d = {
        "a": "b",
        "b": "b"
    }

    res = extract_unique_values(d)
    assert len(res) == 1, "Failed to determine the unique values correctly."
    assert list(res)[0] == "b", "Failed to determine the unique values correctly."

    d = {
        "a": {
            "a": "b"
        },
        "b": {
            "a": "b"
        },
    }

    res = extract_unique_values(d, "a")
    assert len(res) == 1, "Failed to determine the unique values correctly (nested)."
    assert list(res)[0] == "b", "Failed to determine the unique values correctly (nested)."

    d = {
        "a": {
            "a": ["b"]
        },
        "b": {
            "a": ["b"]
        },
    }

    res = extract_unique_values(d, "a/+")
    assert len(res) == 1, "Failed to determine the unique values correctly (using nested-arrays)."
    assert list(res)[0] == "b", "Failed to determine the unique values correctly (using nested-arrays)."

    d = {
        "a": ["a", "b"],
        "b": ["a"],
    }

    res = extract_unique_values(d, "+")
    assert len(res) == 2, "Failed to determine the unique values correctly (using flatted-arrays)."
    assert ("a" in res and "b" in res), "Failed to determine the unique values correctly (using flatted-arrays)."

    d = {
        "a": {
            "a": ["b"]
        },
        "b": {
            "a": ["a", "b"]
        },
    }

    res = extract_unique_values(d, "a/+")
    assert len(res) == 2, "Failed to determine the unique values correctly (using flatted-arrays)."
    assert ("a" in res and "b" in res), "Failed to determine the unique values correctly (using flatted-arrays)."

    d = {
        "a": {
            "a": [
                {
                    "content": "a",
                    "id": 1,
                },
                {
                    "content": "b",
                    "id": 2,
                },
            ], },
        "b": {
            "a": [
                {
                    "content": "c",
                    "id": 1,
                },
                {
                    "content": "d",
                    "id": 3,
                },
            ]
        }
    }
    res = extract_unique_values(d, "a/+/content", "a/+/id")

    assert len(res) == 3, "Failed to determine the unique values correctly (using flatted-arrays)."
    assert (
                "a" in res and "b" in res and "d" in res), "Failed to determine the unique values correctly (using flatted-arrays)."
