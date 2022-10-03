from .dotted_dict import DottedDict
from .path import (MULTI_LEVEL_WILDCARD, SINGLE_LEVEL_WILDCARD, SPLITCHAR,
                   contains_wildcards, pattern_is_valid)


def generate_result(res=DottedDict({})):
    """ internal helper to generate the defined result.

    Args:
        res (dotted_dict, optional): The Result. Defaults to dotted_dict({}).

    Returns:
        dotted_dict: The Result
    """
    default_result = DottedDict({
        'affected': False,
        'affected_by_child': False,
        'affected_by_parent': False,
        'affected_on_same_level': False,
        'contains_wildcards': False,
        'pattern_to_extract_data': False,
        'pattern_length_compared_to_path_length': '=',
        'path_to_extract_data': False
    })

    default_result.update(res)
    default_result.affected = default_result.affected_by_child or default_result.affected_by_parent or default_result.affected_on_same_level

    return default_result


def compare_pattern_and_path(path_pattern: str, content_path: str, options={'match_topics_without_wildcards': False}):
    """ Matches the given path, with the pattern and determines, if the path might affect the given pattern.

        example: path = "a/b/c"; pattern = "a/#"; => totalPath = "a/b/c"; diffPath = "b/c"

    Args:
        path_pattern (str): The pattern to test
        content_path (str): The path to use as basis
        options (dotted_dict, optional): _description_. Defaults to dotted_dict({'match_topics_without_wildcards': False}).

    Returns:
        dotted_dict: The Result
    """

    options = DottedDict(options)

    if contains_wildcards(content_path):
        raise Exception(
            "The Path is invalid. The path should not contain pattern-related chars '#' or '+'.")
    if not pattern_is_valid(path_pattern):
        raise Exception('The Pattern is invalid.')
    if not pattern_is_valid(content_path):
        raise Exception('The Path is invalid.')

    _contains_wildcards = contains_wildcards(path_pattern)
    _pattern_segments = path_pattern.split(SPLITCHAR)
    _content_path_segments = content_path.split(SPLITCHAR)
    _pattern_length = len(_pattern_segments)
    _content_path_length = len(_content_path_segments)

    # Define the Char for the comparer
    pattern_length_compared_to_path_length = '='
    if _pattern_length > _content_path_length:
        pattern_length_compared_to_path_length = '>'
    elif _pattern_length < _content_path_length:
        pattern_length_compared_to_path_length = '<'

    # If both, the pattern and the path are equal => return the result.
    if path_pattern == content_path:
        return generate_result(
            DottedDict(
                {
                    'affected_on_same_level': True,
                    'path_to_extract_data': content_path,
                    'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length
                }
            )
        )

    # If the Path is not realy defined.
    if content_path == '':
        return generate_result(
            DottedDict({
                'affected_by_parent': True,
                'pattern_to_extract_data': path_pattern if _contains_wildcards else False,
                'path_to_extract_data': False if _contains_wildcards else path_pattern,
                'pattern_length_compared_to_path_length': '>',
                'contains_wildcards': _contains_wildcards
            })
        )
    if path_pattern == '':
        return generate_result(
            DottedDict({
                'affected_by_child': True,
                'path_to_extract_data': '',
                'pattern_length_compared_to_path_length': '<'
            })
        )
    if options.match_topics_without_wildcards:
        if content_path.startswith(path_pattern):
            # Path is longer then the Pattern;
            # => A Change is performed by "Child",
            if _contains_wildcards:
                return generate_result(
                    DottedDict({
                        'affected_by_child': True,
                        'path_to_extract_data': content_path,
                        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                        'contains_wildcards': _contains_wildcards
                    })
                )
            else:
                return generate_result(
                    DottedDict({
                        'affected_by_child': True,
                        'path_to_extract_data': path_pattern,
                        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                        'contains_wildcards': _contains_wildcards
                    })
                )
        elif path_pattern.startswith(content_path):
            # Pattern is longer then the path;
            # => A Change might be initated by
            # the super element

            # The PathToExtractData is allways false, if the path is smaller then the
            # pattern

            if _contains_wildcards:
                return generate_result(
                    DottedDict({
                        'affected_by_parent': True,
                        'pattern_to_extract_data': path_pattern,
                        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                        'contains_wildcards': _contains_wildcards
                    })
                )
            else:
                return generate_result(
                    DottedDict({
                        'affected_by_parent': True,
                        'path_to_extract_data': path_pattern,
                        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                        'contains_wildcards': _contains_wildcards
                    })
                )

    partial_path = ''
    i = 0

    # Iterate over the Segments.
    while i < _pattern_length:
        # Store the current Pattern Segment
        current_pattern = _pattern_segments[i]

        # We need to know, if there is SINGLE_LEVEL_WILDCARD or MULTI_LEVEL_WILDCARD
        # there fore we will extract the Wildlevels.
        pattern_char = current_pattern[0]
        current_path = _content_path_segments[i] if i < _content_path_length else None
        i = i + 1
        if current_path == None:
            # Our Pattern is larger then our contentPath.
            # So we dont know, whether we will get some
            # data. Therefore we have to perform a query
            # later ==> Set The Path / Pattern.

            if _contains_wildcards:
                # But we contain Patterns.
                # So we are not allowed to build a
                # diff object.
                return generate_result(
                    DottedDict({
                        'affected_by_parent': True,
                        'pattern_to_extract_data': path_pattern,
                        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                        'contains_wildcards': _contains_wildcards
                    })
                )
            else:
                raise Exception('Implementation Error! This should not happen')
        elif current_path == current_pattern:
            # The Patterns Match
            # We now store the correct path of our segment.
            partial_path = f'{partial_path}{SPLITCHAR}{current_path}' if len(
                partial_path) > 0 else current_path
        elif pattern_char == MULTI_LEVEL_WILDCARD:

            # We know, that MULTI_LEVEL_WILDCARDs are only at the end of the
            # pattern. So it might happen, that:
            # a)   our length of the pattern is the same length as the content path
            # b)   our length of the pattern is smaller then length as the content path
            #
            # Our statement before alread tested, that either case a) or b) fits. Otherwise
            # another ifstatement is valid and we wont enter this statement here.

            # # We add the segment to testedCorrectPath
            # testedCorrectPath = testedCorrectPath.length > 0 ? `{testedCorrectPath}{SPLITCHAR}{currentPath}` : currentPath;

            if pattern_length_compared_to_path_length == '=':
                # Case a)
                return generate_result(
                    DottedDict(
                        {
                            'affected_on_same_level': True,
                            'path_to_extract_data': content_path,
                            'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                            'contains_wildcards': _contains_wildcards
                        }
                    )
                )
            elif pattern_length_compared_to_path_length == '<':
                # Case b)
                return generate_result(DottedDict(
                    {
                        'affected_by_child': True,
                        'path_to_extract_data': content_path,
                        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                        'contains_wildcards': _contains_wildcards
                    }
                ))
            else:
                raise Exception('Implementation Error!')
        elif pattern_char == SINGLE_LEVEL_WILDCARD:
            # Store the correct path.
            partial_path = f'{partial_path}{SPLITCHAR}{current_path}' if len(
                partial_path) > 0 else current_path
        elif pattern_char != SINGLE_LEVEL_WILDCARD and current_pattern != current_path:
            return generate_result(DottedDict({
                'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
                'contains_wildcards': _contains_wildcards
            }))
    diff = content_path[len(partial_path):]
    return generate_result(DottedDict({
        'affected_on_same_level': len(diff) == 0,
        'affected_by_child': len(diff) > 1,
        'path_to_extract_data': partial_path,
        'pattern_length_compared_to_path_length': pattern_length_compared_to_path_length,
        'contains_wildcards': _contains_wildcards
    }))
