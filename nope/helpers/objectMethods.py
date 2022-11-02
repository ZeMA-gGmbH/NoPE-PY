#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from copy import deepcopy

from .dottedDict import DottedDict, ensureDottedAccess
from .path import (MULTI_LEVEL_WILDCARD, SPLITCHAR, containsWildcards,
                   getLeastCommonPathSegment)
from .pathMatchingMethods import comparePatternAndPath

SENTINEL_1 = object()
SENTINEL_2 = object()


def rgetattr(data, path, default=SENTINEL_1, _SPLITCHAR=SPLITCHAR):
    """ Helper to recursively get an value.

    Args:
        data (any): The data to extract the value from
        path (str): The path to extract the data from.
        default (any, optional): The Default value which will be return if no value has been found. If not provided None is returned
        _SPLITCHAR (str, optional): _description_. Defaults to SPLITCHAR.

    Returns:
        any: The found data.
    """
    obj = data
    if len(path) > 0:
        if _SPLITCHAR in path:
            for attr in path.split(_SPLITCHAR):
                if type(obj) in (dict, DottedDict):
                    obj = obj.get(attr)
                else:
                    try:
                        obj = obj[attr]
                    except BaseException:
                        if default == SENTINEL_1:
                            return None
                        return default
        else:
            try:
                return obj[path]
            except KeyError:
                if default == SENTINEL_1:
                    return None
                return default

    return obj


def rqueryAttr(data, query):
    if not containsWildcards(query):
        extractedData = rgetattr(data, query, SENTINEL_2)
        if extractedData == SENTINEL_2:
            return []

        return [
            DottedDict({
                'path': query,
                'data': extractedData
            })
        ]

    ret = []
    multi_level = MULTI_LEVEL_WILDCARD in query
    # Determine the max depth
    max_depth = None if multi_level else len(query.split(SPLITCHAR))

    # get the flatten object
    _dict = flattenObject(
        data,
        max_depth=max_depth,
        onlyPathToBaseValue=False
    )

    # Iterate over the items and use our path matcher to extract the matching
    # items.
    for iter_item in _dict.items():
        path = iter_item[0]
        value = iter_item[1]
        r = comparePatternAndPath(query, path)

        if r.affectedOnSameLevel or (multi_level and r.affectedByChild):
            ret.append(
                DottedDict({
                    'path': path,
                    'data': value
                })
            )

    return ret


def convertData(data, props):
    """ Helper to query data from an object.

        props is defined as followed:
        ```typescript
        props: {
            key: string;
            query: string;
        }[]
        ```

        Example 1:

        data = { "deep": { "nested": "test" } }
        result = convertData(data, [
            {
                "key": "result",
                "query": "deep/nested",
            },
        ])

        ==> result = [{"result": "test"}]

        Example 2:

        data = {
            "array": [
            {
                "data1": 0,
                "data2": "a",
            },
            {
                "data1": 1,
                "data2": "a",
            },
            ],
            "not": { "nested": "hello" }
        }

        result = convertData(data, [
            {
                "key": "a",
                "query": "array/+/data1",
            },
            {
                "key": "b",
                "query": "array/+/data2",
            },
        ])

        ==> result = [{"a": 0, "b": "a"}, {"a": 1, "b": "a"}]

    Args:
        data (any): The data
        props (dotted_dict[]): The query to use.
    """

    ret = DottedDict({})

    commonPattern = getLeastCommonPathSegment(
        list(
            map(
                lambda _item: _item.get("query"),
                props
            )
        )
    )

    for prop in props:
        ret[prop.get("key")] = rqueryAttr(data, prop.get("query"))

    helper = DottedDict({})

    for prop in props:
        items = ret[prop.get("key")]

        for idx, item in enumerate(items):

            if isinstance(commonPattern, str):
                result = comparePatternAndPath(commonPattern, item["path"])
                if result.pathToExtractData:
                    if not (result.pathToExtractData in helper):
                        helper[result.pathToExtractData] = DottedDict()
                    helper[result.pathToExtractData][prop.get(
                        "key")] = item.data
            else:
                if idx not in helper:
                    helper[idx] = DottedDict()

                helper[idx][prop.get("key")] = item.data

    return list(helper.values())


def _set(obj, accessor: str, value):
    try:
        obj[accessor] = value
    except BaseException as E:
        try:
            setattr(obj, accessor, value)
        except BaseException as E:
            raise E


def _get(obj, accessor, return_none=False):
    try:
        return obj[accessor]
    except BaseException as E:
        try:
            return getattr(obj, accessor)
        except BaseException as E:
            if return_none:
                return None
            raise E


def rsetattr(data, path: str, value, splitchar: str = SPLITCHAR):
    """ unction to Set recursely a Attribute of an Object

    Args:
        data (any):  The Object, where the data should be stored
        path (str): The Path of the Attribute. All are seprated by a the splitchar. (Defaults to'.' => For Instance 'a/b/0/a/c')
        value (any): The Value which should be Stored in the Attribute.
        _SPLITCHAR (str, optional): The Splitchar to use. Defaults to "/". Defaults to SPLITCHAR.
    """

    obj = data

    ptrs = path.split(splitchar)

    for idx, attr in enumerate(ptrs[0:-1]):
        # Adapt the Object by going through a loop

        accessor = int(attr) if isInt(attr) else attr

        sub = _get(obj, accessor, return_none=True)

        if isinstance(obj, list):
            length = len(obj)
            while length <= accessor:
                obj.append(None)
                length = len(obj)

        if sub is None:
            # _obj is an Array and it doesnt contain the index
            # Extract the Next Element:
            nextAccessor = ptrs[idx + 1]

            nextIsInt = isInt(nextAccessor)

            if nextIsInt:
                _set(obj, accessor, [None] * (int(nextAccessor) + 1))
            else:
                _set(obj, accessor, DottedDict({}))

            sub = _get(obj, accessor)

        obj = sub

    try:
        obj[ptrs[len(ptrs) - 1]] = value
    except BaseException as E:
        try:
            sub = setattr(obj, ptrs[len(ptrs) - 1], value)
        except BaseException as E:
            raise E


def isInt(value) -> bool:
    """ Checks whether the Value is an Integer

    Args:
        value: Value to be checked
    """
    if isinstance(value, int):
        return True

    try:
        int(value)
        return True
    except BaseException:
        return False


def isFloat(value) -> bool:
    """ Checks whether the Value is a Float

    Args:
        value: Value to be checked
    """
    if isinstance(value, float):
        return True

    try:
        float(value)
        return True
    except BaseException:
        return False


def isNumber(value) -> bool:
    return isFloat(value) or isInt(value)


def objectToDict(obj):
    """ Function Converts a Object to a dict.

    Args:
        obj: The Object which should be converted.
    """

    ret = dict
    # Iterate through all properties of the Object
    for prop in obj:
        if not callable(obj):
            ret[prop] = obj[prop]

    return ret


def isDictLike(obj) -> bool:
    """
    Check if the object is dict-like.
    Parameters
    ----------
    obj : The object to check
    Returns
    -------
    is_dict_like : bool
        Whether `obj` has dict-like properties.
    Examples
    --------
    >>> isDictLike({1: 2})
    True
    >>> isDictLike([1, 2, 3])
    False
    >>> isDictLike(dict)
    False
    >>> isDictLike(dict())
    True
    """
    attributes_to_check = ("__getitem__")

    for attr in attributes_to_check:
        if not hasattr(obj, attr):
            return False

    # Prevent returning Classes:
    return not isinstance(obj, type)


def allowsSubscripton(obj):
    return hasattr(obj, "__getitem__")


def flattenObject(data, prefix="", splitchar=SPLITCHAR,
                  onlyPathToBaseValue=False, max_depth=None):

    ret = DottedDict()

    # Check if we are ae to access the items using an subscription.
    if allowsSubscripton(data):
        def callback(path, data, *args):
            ret[path] = data

        recursiveForEach(
            data,
            callback,
            prefix,
            splitchar,
            onlyPathToBaseValue,
            max_depth
        )

    return ret


def deflattenObject(flattenObject, options=None):
    _options = ensureDottedAccess({'prefix': '', 'splitchar': SPLITCHAR})
    _options.update(ensureDottedAccess(options))

    ret = ensureDottedAccess({})

    for key, val in flattenObject.items():
        if _options.prefix != '':
            key = key[len(_options.prefix):]
        rsetattr(ret, key, val, _options.splitchar)

    return ret


def getKeys(obj):
    """ Helper, to get keys of an array, dict etc.

    Args:
        obj: The considered Object.

    Returns:
        list: List of Keys
    """
    keys = list()
    t_obj = type(obj)
    if not (t_obj is str) and not (callable(obj)):
        if t_obj in (list, set):
            # For list, we will use the index
            keys = range(0, len(obj))
        elif hasattr(obj, "keys"):
            # We are working with a dict.
            keys = list(obj.keys())
        else:
            try:
                # For all other items, we will use the vars as key.
                keys = list(vars(obj))
            except BaseException:
                pass

    return keys


def deepAssign(target, source):
    """ Deeply assigns the items given in the dict, whereas the
        keys of the source will be used as path, its value as value
        to assign.
    Args:
        target (any): original object.
        source (dict | dict-like): _description_

    Returns:
        any: the manipulated target
    """
    flattend = flattenObject(source)
    for iter_item in flattend.entries():
        path = iter_item[0]
        value = iter_item[1]
        rsetattr(target, path, value)
    return target


def recursiveForEach(obj, callback=None, prefix="", _SPLITCHAR=SPLITCHAR, callOnlyOnBaseValues=True,
                     max_depth=None, parent='', level=0):
    """ Function, that will iterate over an object.

    Args:
        obj: The Object to iterate
        prefix (_type_): A prefix for the Path.
        callback (callable, optional): Callback, that will be called.. Defaults to None.
        _SPLITCHAR (_type_, optional): The Splitchar to use, to generate the path. Defaults to SPLITCHAR.
        callOnlyOnBaseValues (bool, optional): A Flag, to call the Function only on Values. Defaults to True.
        max_depth (_type_, optional): Determine the max Depth, after which the Iteration will be stopped.. Defaults to None.
        parent (str, optional): For Recursive call only. Defaults to ''.
        level (int, optional): For Recursive call only. Defaults to 0.
    """
    if isInt(max_depth) and level > max_depth:
        # Break the Loop
        return

    # No try to extrac the Keys.
    keys = getKeys(obj)

    called = False
    if not callOnlyOnBaseValues and callable(callback):
        callback(prefix, obj, parent, level)
        called = True

    # If there exits some keys:
    if len(keys) > 0:
        # We will iterate over the and
        for key in keys:
            # Define the variable, containing the path
            path = str(key) if '' == prefix else prefix + _SPLITCHAR + str(key)

            if obj[key] is not None:
                if hasattr(obj[key], "to_json") and callable(obj[key].to_json):
                    data = obj[key].to_json()
                    recursiveForEach(
                        data,
                        callback,
                        path,
                        _SPLITCHAR,
                        callOnlyOnBaseValues,
                        max_depth,
                        prefix,
                        level + 1
                    )

                else:

                    recursiveForEach(
                        obj[key],
                        callback,
                        path,
                        _SPLITCHAR,
                        callOnlyOnBaseValues,
                        max_depth,
                        prefix,
                        level + 1
                    )
    elif not called:
        callback(prefix, obj, prefix, level)


def keepProperties(obj, properties):
    if allowsSubscripton(obj):
        ret = DottedDict({})
        default_obj = DottedDict({'error': True})

        for key in getKeys(obj):
            value = rgetattr(obj, key, default_obj)
            valueToAssign = value
            if value != default_obj:
                valueToAssign = copy(value)
            else:
                valueToAssign = properties[key]()
            rsetattr(ret, key, valueToAssign)

        return ret
    raise Exception('Function can only create Objects')


WARNED = False


def copy(obj):
    """ A Helper, which can be used to receive a copy.

    Args:
        obj (any): The Object to copy

    Returns:
        bool, any: A flag, to show whether it succeeded or failed; the copy (or if failed the object) itself.
    """
    try:
        return deepcopy(obj)
    except BaseException:
        try:
            return obj.copy()
        except BaseException:
            global WARNED
            if not WARNED:
                WARNED = True
                print("Failed to create a copy using orignal value.")
            return obj
