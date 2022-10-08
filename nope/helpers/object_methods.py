#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from copy import deepcopy

from .dotted_dict import DottedDict
from .path import (MULTI_LEVEL_WILDCARD, SPLITCHAR, contains_wildcards,
                   get_least_common_path_segment)
from .path_matching_methods import compare_pattern_and_path

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
                    except:
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


def rquery_attr(data, query):
    if not contains_wildcards(query):
        extracted_data = rgetattr(data, query, SENTINEL_2)
        if extracted_data == SENTINEL_2:
            return []

        return [
            DottedDict({
                'path': query,
                'data': extracted_data
            })
        ]

    ret = []
    multi_level = MULTI_LEVEL_WILDCARD in query
    # Determine the max depth
    max_depth = None if multi_level else len(query.split(SPLITCHAR))

    # get the flatten object
    _dict = flatten_object(
        data,
        max_depth=max_depth,
        only_path_to_simple_value=False
    )

    # Iterate over the items and use our path matcher to extract the matching items.
    for iter_item in _dict.items():
        path = iter_item[0]
        value = iter_item[1]
        r = compare_pattern_and_path(query, path)

        if r.affected_on_same_level or (multi_level and r.affected_by_child):
            ret.append(
                DottedDict({
                    'path': path,
                    'data': value
                })
            )

    return ret


def convert_data(data, props):
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
        result = convert_data(data, [
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

        ==> result = [{"a": 0, "b": "a"}, {"a": 1, "b": "a"}]

    Args:
        data (any): The data
        props (dotted_dict[]): The query to use.
    """

    ret = DottedDict({})

    common_pattern = get_least_common_path_segment(
        list(
            map(
                lambda _item: _item.get("query"),
                props
            )
        )
    )

    for prop in props:
        ret[prop.get("key")] = rquery_attr(data, prop.get("query"))

    helper = DottedDict({})

    for prop in props:
        items = ret[prop.get("key")]

        for idx, item in enumerate(items):

            if type(common_pattern) is str:
                result = compare_pattern_and_path(common_pattern, item["path"])
                if result.path_to_extract_data:
                    if not (result.path_to_extract_data in helper):
                        helper[result.path_to_extract_data] = DottedDict()
                    helper[result.path_to_extract_data][prop.get(
                        "key")] = item.data
            else:
                if idx not in helper:
                    helper[idx] = DottedDict()

                helper[idx][prop.get("key")] = item.data

    return list(helper.values())


def rsetattr(data, path: str, value, _SPLITCHAR: str = SPLITCHAR):
    """ unction to Set recursely a Attribute of an Object

    Args:
        data (any):  The Object, where the data should be stored
        path (str): The Path of the Attribute. All are seprated by a the splitchar. (Defaults to'.' => For Instance 'a/b/0/a/c')
        value (any): The Value which should be Stored in the Attribute.
        _SPLITCHAR (str, optional): The Splitchar to use. Defaults to "/". Defaults to SPLITCHAR.
    """

    obj = data

    ptrs = path.split(_SPLITCHAR)

    for idx, attr in enumerate(ptrs[0:-1]):
        # Adapt the Object by going through a loop
        sub = None

        accessor = int(attr) if is_int(attr) else attr

        try:
            sub = obj[accessor]
        except:
            pass

        if type(obj) is list:
            length = len(obj)
            while length <= accessor:
                obj.append(None)
                length = len(obj)

        if sub == None:
            # _obj is an Array and it doesnt contain the index
            # Extract the Next Element:
            next_accessor = ptrs[idx + 1]

            next_is_int = is_int(next_accessor)

            if type(obj) is list:
                if next_is_int:
                    obj[accessor] = [None] * (int(next_accessor) + 1)
                else:
                    obj[accessor] = DottedDict({})
            else:
                if next_is_int:
                    obj[accessor] = [None] * (int(next_accessor) + 1)
                else:
                    obj[accessor] = DottedDict({})

            sub = obj[accessor]

        obj = sub

    obj[ptrs[len(ptrs) - 1]] = value


def is_int(value) -> bool:
    """ Checks whether the Value is an Integer

    Args:
        value: Value to be checked
    """
    if type(value) is int:
        return True

    try:
        int(value)
        return True
    except:
        return False


def is_float(value) -> bool:
    """ Checks whether the Value is a Float

    Args:
        value: Value to be checked
    """
    if type(value) is float:
        return True

    try:
        float(value)
        return True
    except:
        return False


def is_number(value) -> bool:
    return is_float(value) or is_int(value)


def object_to_dict(obj):
    """ Function Converts a Object to a dict.

    Args:
        obj: The Object which should be converted.
    """

    ret = dict
    # Iterate through all properties of the Object
    for prop in obj:
        if not callable(obj):
            ret.set(prop, obj[prop])

    return ret


def is_object_like(obj) -> bool:
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
    >>> is_object_like({1: 2})
    True
    >>> is_object_like([1, 2, 3])
    False
    >>> is_object_like(dict)
    False
    >>> is_object_like(dict())
    True
    """
    attributes_to_check = ("__getitem__")

    for attr in attributes_to_check:
        if not hasattr(obj, attr):
            return False

    # Prevent returning Classes:
    return not isinstance(obj, type)


def allows_subscripton(obj):
    return hasattr(obj, "__getitem__")


def flatten_object(data, prefix = "", splitchar = SPLITCHAR, only_path_to_simple_value = False, max_depth = None):

    ret = DottedDict()

    # Check if we are ae to access the items using an subscription.
    if allows_subscripton(data):
        def callback(path, data, *args):
            ret[path] = data

        recursive_for_each(
            data,
            callback,
            prefix,
            splitchar,
            only_path_to_simple_value,
            max_depth
        )

    return ret


def deflatten_object(flatten_object, options):
    _options = DottedDict({'prefix': '', 'splitchar': SPLITCHAR})
    _options.update(options)

    ret = DottedDict({})

    for key, val in flatten_object.items():
        if _options.prefix != '':
            key = key[len(_options.prefix):]
        rsetattr(ret, key, val, _options.splitchar)

    return ret


def get_keys(obj):
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
            except:
                pass

    return keys


def deep_assign(target, source):
    """ Deeply assigns the items given in the dict, whereas the 
        keys of the source will be used as path, its value as value
        to assign.
    Args:
        target (any): original object.
        source (dict | dict-like): _description_

    Returns:
        any: the manipulated target
    """
    flattend = flatten_object(source)
    for iter_item in flattend.entries():
        path = iter_item[0]
        value = iter_item[1]
        rsetattr(target, path, value)
    return target


def recursive_for_each(obj, data_callback=None, prefix="", _SPLITCHAR=SPLITCHAR, call_only_on_values=True,
                       max_depth=None, parent='', level=0):
    """ Function, that will iterate over an object.

    Args:
        obj: The Object to iterate
        prefix (_type_): A prefix for the Path.
        data_callback (callable, optional): Callback, that will be called.. Defaults to None.
        _SPLITCHAR (_type_, optional): The Splitchar to use, to generate the path. Defaults to SPLITCHAR.
        call_only_on_values (bool, optional): A Flag, to call the Function only on Values. Defaults to True.
        max_depth (_type_, optional): Determine the max Depth, after which the Iteration will be stopped.. Defaults to None.
        parent (str, optional): For Recursive call only. Defaults to ''.
        level (int, optional): For Recursive call only. Defaults to 0.
    """
    if is_int(max_depth) and level > max_depth:
        # Break the Loop
        return

    # No try to extrac the Keys.
    keys = get_keys(obj)

    called = False
    if not call_only_on_values and callable(data_callback):
        data_callback(prefix, obj, parent, level)
        called = True

    # If there exits some keys:
    if len(keys) > 0:
        # We will iterate over the and
        for key in keys:
            # Define the variable, containing the path
            path = str(key) if '' == prefix else prefix + _SPLITCHAR + str(key)

            if obj[key] != None:
                if hasattr(obj[key], "to_json") and callable(obj[key].to_json):
                    data = obj[key].to_json()
                    recursive_for_each(
                        data,
                        data_callback,
                        path,
                        _SPLITCHAR,
                        call_only_on_values,
                        max_depth,
                        prefix,
                        level + 1
                    )

                else:

                    recursive_for_each(
                        obj[key],
                        data_callback,
                        path,
                        _SPLITCHAR,
                        call_only_on_values,
                        max_depth,
                        prefix,
                        level + 1
                    )
    elif not called:
        data_callback(prefix, obj, prefix, level)


def keep_properties_of_object(obj, properties):
    if allows_subscripton(obj):
        ret = DottedDict({})
        default_obj = DottedDict({'error': True})

        for key in get_keys(obj):
            value = rgetattr(obj, key, default_obj)
            value_to_assign = value
            if value != default_obj:
                value_to_assign = copy(value)
            else:
                value_to_assign = properties[key]()
            rsetattr(ret, key, value_to_assign)

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
    except:
        try: 
            return obj.copy()
        except:            
            global WARNED
            if not WARNED:
                WARNED = True
                print("Failed to create a copy using orignal value.")

            return obj
    