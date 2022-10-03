from .dotted_dict import DottedDict
from .string_methods import replace_all

SPLITCHAR = '/'
SINGLE_LEVEL_WILDCARD = '+'
MULTI_LEVEL_WILDCARD = '#'


def convert_path(path: str) -> str:
    """ converts the path 

    Args:
        path (str): The Path to adapt.

    Returns:
        str: The adapted Path
    """
    return replace_all(path, ['.', '[', [']', '']], SPLITCHAR)


def contains_wildcards(str: str) -> bool:
    """ Determines, whether the given string contains a single level card or not.

    Args:
        str (str): String to check

    Returns:
        bool: Result
    """
    return SINGLE_LEVEL_WILDCARD in str or MULTI_LEVEL_WILDCARD in str


def get_least_common_path_segment(pathes, opts=DottedDict({})):
    """ Returns the least common segmet of all pathes, included in the pathes array.

        The Following options are available.

        "considerSingleLevel":boolean -> allows "singlelevel"-wildcards in the segments
        "considerMultiLevel":boolean -> allows "multilevel"-wildcards in the segments

    Args:
        pathes (str[]): The Segments to compare. 
        opts (dotted_dict, optional): the options. Defaults to dotted_dict({}).

    Returns:
        (False | str): the least common segment of the pathes or False.
    """
    current_path = pathes.pop()
    while len(pathes) > 0:
        next = pathes.pop()
        current_path = _get_least_common_path_segment(current_path, next, opts)

        # Only proceed, if there are elements included.
        if not current_path:
            # Return False
            return current_path

    # Return the least common segments.
    return current_path


def _get_least_common_path_segment(path01, path02, opts=DottedDict({})):
    """_summary_

    Args:
        path01 (_type_): _description_
        path02 (_type_): _description_
        opts (_type_, optional): _description_. Defaults to dotted_dict({}).

    Returns:
        _type_: _description_
    """
    p1 = convert_path(path01).split(SPLITCHAR)
    p2 = convert_path(path02).split(SPLITCHAR)

    ret = []
    idx = 0

    _max = max(len(p1), len(p2))

    while idx < _max:
        if p1[idx] == p2[idx]:
            ret += [p1[idx]]
        elif opts.consider_single_level:
            if p1[idx] == SINGLE_LEVEL_WILDCARD:
                ret += [p2[idx:]]
            elif p2[idx] == SINGLE_LEVEL_WILDCARD:
                ret += [p1[idx:]]
            else:
                break
        elif opts.consider_multi_level:
            if p1[idx] == MULTI_LEVEL_WILDCARD:
                ret += [p2[idx:]]
                break
            elif p2[idx] == MULTI_LEVEL_WILDCARD:
                ret += [p1[idx:]]
                break
            else:
                break
        else:
            break
        idx = idx + 1
    if len(ret):
        return SPLITCHAR.join(ret)
    return False


def pattern_is_valid(str: str) -> bool:
    """ Function to test if a pattern is valid

    Args:
        str (str): The pattern to test

    Returns:
        bool: The result.
    """

    if str == "":
        return True

    splitted = str.split(SPLITCHAR)
    last_index = len(splitted) - 1

    for idx, segment in enumerate(splitted):
        if segment:
            if segment == MULTI_LEVEL_WILDCARD:
                return idx == last_index
        else:
            return False

    return True
