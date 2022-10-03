from ..path_matching_methods import compare_pattern_and_path, generate_result


def test_compare_pattern_and_path():
    function_tests_1 = [
        {
            "desc": "simple matching topics",
            'pattern': "test",
            "path": "test",
            "expected_result": generate_result({
                "path_to_extract_data": "test",
                "affected_on_same_level": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "topics should match",
            'pattern': "test1",
            "path": "test2",
            "expected_result": generate_result({
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "simple root topic compare topics",
            'pattern': "test",
            "path": "",
            "expected_result": generate_result({
                "path_to_extract_data": "test",
                "affected_by_parent": True,
                "pattern_length_compared_to_path_length": ">",
            }),
        },
        {
            "desc": "match with multilevel wildcard",
            'pattern': "test/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_by_child": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard and same length",
            'pattern': "test/test/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard",
            'pattern': "test/+/test",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as first element in 'pattern'",
            'pattern': "+/test/test",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as last element in 'pattern'",
            'pattern': "test/test/+",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with multiple singlelevel wildcards in 'pattern'",
            'pattern': "test/+/+",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel and multilevel wildcard in 'pattern'",
            'pattern': "+/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_by_child": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard in 'pattern'",
            'pattern': "test/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_by_child": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        },
        {
            "desc": "'pattern' is longer than path",
            'pattern': "test/test/test/#",
            "path": "test",
            "expected_result": generate_result({
                "pattern_to_extract_data": "test/test/test/#",
                "affected_by_parent": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": ">",
            }),
        },

    ]

    for idx,test in enumerate(function_tests_1):
        result = compare_pattern_and_path(test["pattern"], test["path"])
        desc = test["desc"]
        expected = test["expected_result"]
        assert result == test["expected_result"], f"1.{idx} went wrong: '{desc}'\nresult:\t{result}\nexpected:\t{expected}"

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
            result = compare_pattern_and_path(test["pattern"], test["path"])
            raise err
        except KeyboardInterrupt:
            raise Exception("There should be an error!")
        except:
            pass

    function_tests_2 = [
        {
            "desc": "simple matching topics",
            "pattern": "test",
            "path": "test",
            "expected_result": generate_result({
                "path_to_extract_data": "test",
                "affected_on_same_level": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "topics should match",
            "pattern": "test1",
            "path": "test2",
            "expected_result": generate_result({
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "simple root topic compare topics",
            "pattern": "test",
            "path": "",
            "expected_result": generate_result({
                "path_to_extract_data": "test",
                "affected_by_parent": True,
                "pattern_length_compared_to_path_length": ">",
            }),
        },
        {
            "desc": "match with multilevel wildcard",
            "pattern": "test/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_by_child": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard and same length",
            "pattern": "test/test/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard",
            "pattern": "test/+/test",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as first element in pattern",
            "pattern": "+/test/test",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel wildcard as last element in pattern",
            "pattern": "test/test/+",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with multiple singlelevel wildcards in pattern",
            "pattern": "test/+/+",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_on_same_level": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "=",
            }),
        },
        {
            "desc": "match with singlelevel and multilevel wildcard in pattern",
            "pattern": "+/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_by_child": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        },
        {
            "desc": "match with multilevel wildcard in pattern",
            "pattern": "test/#",
            "path": "test/test/test",
            "expected_result": generate_result({
                "path_to_extract_data": "test/test/test",
                "affected_by_child": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        },
        {
            "desc": "pattern is longer than path",
            "pattern": "test/test/test/#",
            "path": "test",
            "expected_result": generate_result({
                "pattern_to_extract_data": "test/test/test/#",
                "affected_by_parent": True,
                "contains_wildcards": True,
                "pattern_length_compared_to_path_length": ">",
            }),
        },
        # Now the specific Tests start:
        {
            "desc": "pattern is longer than path",
            "pattern": "a/b",
            "path": "a",
            "expected_result": generate_result({
                "path_to_extract_data": "a/b",
                "affected_by_parent": True,
                "contains_wildcards": False,
                "pattern_length_compared_to_path_length": ">",
            }),
        },
        {
            "desc": "path is longer than pattern",
            "pattern": "a/b",
            "path": "a/b/c",
            "expected_result": generate_result({
                "path_to_extract_data": "a/b",
                "affected_by_child": True,
                "pattern_length_compared_to_path_length": "<",
            }),
        }
    ]

    for idx, test in enumerate (function_tests_2):
        result = compare_pattern_and_path(test["pattern"], test["path"], {
            "match_topics_without_wildcards": True,
        })
        desc = test["desc"]
        expected = test["expected_result"]
        assert result == test["expected_result"], f"2.{idx} went wrong: '{desc}'\nresult:\t{result}\nexpected:\t{expected}\n\n{test}"
