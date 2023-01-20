from .stringMethods import replaceAll, camelToSnake, snakeToCamel
from typing import Literal

SPLITCHAR = '/'
SINGLE_LEVEL_WILDCARD = '+'
MULTI_LEVEL_WILDCARD = '#'


def pathToSnakeCase(path: str, splitchar=SPLITCHAR) -> str:
    # Join the splitchar with the adapted strings.
    return splitchar.join(
        map(
            lambda item: camelToSnake(item),
            path.split(splitchar)
        )
    )


def pathToCamelCase(path: str, splitchar=SPLITCHAR) -> str:
    # Join the splitchar with the adapted strings.
    return splitchar.join(
        map(
            lambda item: snakeToCamel(item),
            path.split(splitchar)
        )
    )


def convertPath(path: str) -> str:
    """ converts the path

    Args:
        path (str): The Path to adapt.

    Returns:
        str: The adapted Path
    """
    return replaceAll(path, ['.', '[', [']', '']], SPLITCHAR)


def _isNumber(item: str) -> bool:
    try:
        float(item)
        return True
    except BaseException:
        return False


def toPythonPath(path: str, style: Literal["dot", "bracket"] = "dot") -> str:
    """ converts the nope-path to a python path.

    Args:
        path (str): The Path to adapt.
        style (Literal["dot","bracket"], optional): The access-style (bracket or dotted.). Defaults to "dot".

    Returns:
        str: The adapted Path
    """

    ret = ""
    splitted = path.split(SPLITCHAR)

    for item in splitted:
        if len(ret) > 0:
            if _isNumber(ret):
                ret += f"[{item}]"
            elif style == "dot":
                ret += "." + item
            else:
                ret += f"[{item}]"
        else:
            ret = item
    return ret


def containsWildcards(str: str) -> bool:
    """ Determines, whether the given string contains a single level card or not.

    Args:
        str (str): String to check

    Returns:
        bool: Result
    """
    return SINGLE_LEVEL_WILDCARD in str or MULTI_LEVEL_WILDCARD in str


def getLeastCommonPathSegment(
        pathes, considerSingleLevel=False, considerMultiLevel=False):
    """ Returns the least common segmet of all pathes, included in the pathes array.

    Args:
        pathes (str[]): The Segments to compare.
        considerSingleLevel (bool): allows "singlelevel"-wildcards in the segments
        considerMultiLevel (bool): allows "multilevel"-wildcards in the segments

    Returns:
        (False | str): the least common segment of the pathes or False.
    """
    current_path = pathes.pop()
    while len(pathes) > 0:
        next = pathes.pop()
        current_path = _getLeastCommonPathSegment(
            current_path, next, considerSingleLevel=considerSingleLevel, considerMultiLevel=considerMultiLevel)

        # Only proceed, if there are elements included.
        if not current_path:
            # Return False
            return current_path

    # Return the least common segments.
    return current_path


def _getLeastCommonPathSegment(
        path01, path02, considerSingleLevel=False, considerMultiLevel=False):
    """_summary_

    Args:
        path01 (_type_): _description_
        path02 (_type_): _description_
        opts (_type_, optional): _description_. Defaults to dotted_dict({}).

    Returns:
        _type_: _description_
    """
    p1 = convertPath(path01).split(SPLITCHAR)
    p2 = convertPath(path02).split(SPLITCHAR)

    ret = []
    idx = 0

    l1 = len(p1)
    l2 = len(p2)

    _max = min(l1, l2)

    while idx < _max:

        if p1[idx] == p2[idx]:
            ret += [p1[idx]]
        elif considerSingleLevel:
            if p1[idx] == SINGLE_LEVEL_WILDCARD:
                ret += [p2[idx:]]
            elif p2[idx] == SINGLE_LEVEL_WILDCARD:
                ret += [p1[idx:]]
            else:
                break
        elif considerMultiLevel:
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


def patternIsValid(str: str) -> bool:
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
