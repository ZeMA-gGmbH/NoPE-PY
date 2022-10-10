import pytest

from ..path_matching_methods import comparePatternAndPath, generateResult
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


def test_comparePatternAndPath():
    function_tests_1 = [
        {
            "desc": "simple matching topics",
            'pattern': "test",
            "path": "test",
            "expected_result": generateResult({
                "pathToExtractData": "test",
                "affectedOnSameLevel": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "topics should match",
            'pattern': "test1",
            "path": "test2",
            "expected_result": generateResult({
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "simple root topic compare topics",
            'pattern': "test",
            "path": "",
            "expected_result": generateResult({
                "pathToExtractData": "test",
                "affectedByParent": True,
                "patternLengthComparedToPathLength": ">",
            }),
        },
        {
            "desc": "match with multilevel wildcard",
            'pattern': "test/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedByChild": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard and same length",
            'pattern': "test/test/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard",
            'pattern': "test/+/test",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as first element in 'pattern'",
            'pattern': "+/test/test",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as last element in 'pattern'",
            'pattern': "test/test/+",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with multiple singlelevel wildcards in 'pattern'",
            'pattern': "test/+/+",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel and multilevel wildcard in 'pattern'",
            'pattern': "+/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedByChild": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard in 'pattern'",
            'pattern': "test/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedByChild": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "<",
            }),
        },
        {
            "desc": "'pattern' is longer than path",
            'pattern': "test/test/test/#",
            "path": "test",
            "expected_result": generateResult({
                "patternToExtractData": "test/test/test/#",
                "affectedByParent": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": ">",
            }),
        },

    ]

    for idx, test in enumerate(function_tests_1):
        result = comparePatternAndPath(test["pattern"], test["path"])
        desc = test["desc"]
        expected = test["expected_result"]
        assert result == test[
            "expected_result"], f"1.{idx} went wrong: '{desc}'\nresult:\t{result}\nexpected:\t{expected}"

    errorTests = [
        {
            "desc": "invalid pattern",
            "pattern": "test//",
            "path": "test",
        },
        {
            "desc": "invalid pattern",
            "pattern": "test/#/a",
            "path": "test",
        },
        {
            "desc": "invalid path",
            "pattern": "test/a",
            "path": "test//a",
        },
        {
            "desc": "invalid path",
            "pattern": "test/a",
            "path": "test/+",
        },
        {
            "desc": "invalid path",
            "pattern": "test/a",
            "path": "test/#",
        },
        {
            "desc": "invalid path",
            "pattern": "test/a",
            "path": "test/+/#",
        },
    ]

    for test in errorTests:
        err = KeyboardInterrupt()
        try:
            result = comparePatternAndPath(test["pattern"], test["path"])
            raise err
        except KeyboardInterrupt:
            raise Exception("There should be an error!")
        except BaseException:
            pass

    function_tests_2 = [
        {
            "desc": "simple matching topics",
            "pattern": "test",
            "path": "test",
            "expected_result": generateResult({
                "pathToExtractData": "test",
                "affectedOnSameLevel": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "topics should match",
            "pattern": "test1",
            "path": "test2",
            "expected_result": generateResult({
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "simple root topic compare topics",
            "pattern": "test",
            "path": "",
            "expected_result": generateResult({
                "pathToExtractData": "test",
                "affectedByParent": True,
                "patternLengthComparedToPathLength": ">",
            }),
        },
        {
            "desc": "match with multilevel wildcard",
            "pattern": "test/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedByChild": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard and same length",
            "pattern": "test/test/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard",
            "pattern": "test/+/test",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as first element in pattern",
            "pattern": "+/test/test",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as last element in pattern",
            "pattern": "test/test/+",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with multiple singlelevel wildcards in pattern",
            "pattern": "test/+/+",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedOnSameLevel": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "=",
            }),
        },
        {
            "desc": "match with singlelevel and multilevel wildcard in pattern",
            "pattern": "+/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedByChild": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard in pattern",
            "pattern": "test/#",
            "path": "test/test/test",
            "expected_result": generateResult({
                "pathToExtractData": "test/test/test",
                "affectedByChild": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": "<",
            }),
        },
        {
            "desc": "pattern is longer than path",
            "pattern": "test/test/test/#",
            "path": "test",
            "expected_result": generateResult({
                "patternToExtractData": "test/test/test/#",
                "affectedByParent": True,
                "containsWildcards": True,
                "patternLengthComparedToPathLength": ">",
            }),
        },
        # Now the specific Tests start:
        {
            "desc": "pattern is longer than path",
            "pattern": "a/b",
            "path": "a",
            "expected_result": generateResult({
                "pathToExtractData": "a/b",
                "affectedByParent": True,
                "containsWildcards": False,
                "patternLengthComparedToPathLength": ">",
            }),
        },
        {
            "desc": "path is longer than pattern",
            "pattern": "a/b",
            "path": "a/b/c",
            "expected_result": generateResult({
                "pathToExtractData": "a/b",
                "affectedByChild": True,
                "patternLengthComparedToPathLength": "<",
            }),
        }
    ]

    for idx, test in enumerate(function_tests_2):
        result = comparePatternAndPath(test["pattern"], test["path"], {
            "matchTopicsWithoutWildcards": True,
        })
        desc = test["desc"]
        expected = test["expected_result"]
        assert result == test[
            "expected_result"], f"2.{idx} went wrong: '{desc}'\nresult:\t{result}\nexpected:\t{expected}\n\n{test}"
