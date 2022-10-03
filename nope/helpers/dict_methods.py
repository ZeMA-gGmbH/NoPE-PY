from collections.abc import Iterable

from .dotted_dict import DottedDict
from .object_methods import convert_data, rgetattr, rquery_attr
from .path import SPLITCHAR, get_least_common_path_segment
from .string_methods import camel_to_snake, snake_to_camel

__SENTINENTAL = object()


def keys_to_snake(d: dict):
    """ helperfunction, which will change the keys to 
        snake case.
    """
    ret = {}
    for key, value in d.items():
        ret[camel_to_snake(key)] = value

    return ret


def keys_to_snake_nested(d: dict):
    """ helperfunction, which will change the keys to 
        snake case. this will work with nested dicts as well
    """
    ret = keys_to_snake(d)

    for key, value in ret.items():
        if type(value) is dict:
            ret[key] = keys_to_snake_nested(value)

    return ret


def keys_to_camel(d: dict):
    """ helperfunction, which will change the options to 
        camel case.
    """
    ret = {}
    for key, value in d.items():
        ret[snake_to_camel(key)] = value

    return ret


def keys_to_camel_nested(options: dict):
    """ helperfunction, which will change the options to 
        camel case. this will work with nested dicts as well
        (expecting every key contains a dict again.)
    """
    ret = keys_to_camel(options)

    for key, value in ret.items():
        if type(value) is dict:
            ret[key] = keys_to_camel_nested(value)

    return ret


def extract_unique_values(d, path='', path_key: str = None):
    """ Extracts the unique values of an map.

    Args:
        d (dict-like): The dict-like object that should be transformed.
        path (str, optional): The path of the attribute of that should be extracted of the value. Defaults to ''.
        path_key (str, optional):   The Path of the unique key. If set to `None` -> The Item is selected directly.
                                    Defaults to None.

    Returns:
        set: A set containing the unique values.
    """
    if path_key is None:
        path_key = path
    if path != path_key:
        _common_segment = get_least_common_path_segment([path, path_key], DottedDict(
            {'consider_single_level': False, 'consider_multi_level': False}))

        # Assign the Value
        _common_segment = _common_segment if _common_segment is not False else ""

        # Determine the Length of the common segment, to determine the relative pathes
        _common_segment_length = len(_common_segment.split(SPLITCHAR)) if _common_segment != "" else 0

        _rel_path_content = SPLITCHAR.join(path.split(SPLITCHAR)[_common_segment_length:])
        _rel_path_key = SPLITCHAR.join(path_key.split(SPLITCHAR)[_common_segment_length:])
        _items = extract_values(d, _common_segment)
        _items_keys = set()
        ret = []
        for item in _items:
            # Extract key and data:
            key = rgetattr(item, _rel_path_key) if _rel_path_key else item
            data = rgetattr(item, _rel_path_content) if _rel_path_content else item
            if key not in _items_keys:
                # Only if the Key has not been used we are allowed to add
                # the data.
                _items_keys.add(key)
                ret.append(data)
        return set(ret)
    return set(extract_values(d, path))


def extract_values(d, path=''):
    """ Helper to extract values of the map. Therefore the path must be provided.

    Example:
        >> d = {1:{"a": 0}, 2:{"a": 1}}
        >> r = extract_values(d,"a")

        r = [0,1]

    Args:
        d (dict-like): The dict-like object that should be transformed.
        path (str, optional): The path of the attribute of that should be extracted of the value. Defaults to ''.

    Returns:
        list: containing the element.
    """
    s = list()
    for v in d.values():
        if path:
            for item in rquery_attr(v, path):
                s.append(item.data)
        else:
            s.append(v)
    return s


def transform_dict(d, path_extracted_value, path_extracted_key):
    """_summary_

    Args:
        d (_type_): _description_
        path_extracted_value (_type_): _description_
        path_extracted_key (_type_): _description_

    Returns:
        _type_: _description_
    """

    # Initialize all values:
    key_mapping = dict()
    reverse_key_mapping = dict()
    conflicts = dict()
    extracted_dict = dict()
    org_key_to_extracted_value = dict()
    amount_of = dict()
    props = []
    only_valid_props = True

    if type(path_extracted_key) == 'string':
        props.append(DottedDict({'key': 'key', 'query': path_extracted_key}))
        only_valid_props = only_valid_props and (len(path_extracted_key) > 0)
    else:
        only_valid_props = False

    if type(path_extracted_value) == 'string':
        props.append(DottedDict(
            {'key': 'value', 'query': path_extracted_value}))
        only_valid_props = only_valid_props and (len(path_extracted_value) > 0)
    else:
        only_valid_props = False

    # Iterate over the items of the dict,
    # then we will extract the data stored in the Value.
    for k, v in d.items():
        extracted = []

        if only_valid_props:
            extracted = convert_data(v, props)
        else:

            data = DottedDict({'key': None, 'value': None})

            # We migt adapt the key and the Value. Therefore we will use
            # the next if statements

            if type(path_extracted_key) is str:
                if len(path_extracted_key) > 0:
                    data.key = rgetattr(v, path_extracted_key)
                else:
                    data.key = v
            else:
                data.key = k

            if type(path_extracted_value) is str:
                if len(path_extracted_value) > 0:
                    data.value = rgetattr(v, path_extracted_value)
                else:
                    data.value = v
            else:
                data.value = v

            extracted.append(data)

        # Create the entries for the following dicts.
        key_mapping[k] = set()
        org_key_to_extracted_value[k] = set()

        for item in extracted:
            if item.key in extracted_dict:
                # If the extracted new key has already been defined,
                # we have to determine whether the stored item matches
                # the allready provided definition.
                if not (extracted_dict.get(item.key) == item.value):

                    # Conflict detected -> Store it

                    if item.key not in conflicts:
                        conflicts[item.key] = set()

                    conflicts.get(item.key).add(item.value)
                    conflicts.get(item.key).add(extracted_dict.get(item.key))
                else:
                    # No conflict -> just store the amount
                    amount_of[item.key] = amount_of.get(item.key, 0) + 1
            else:
                # Store the item and amount
                extracted_dict[item.key] = item.value
                amount_of[item.key] = amount_of.get(item.key, 0) + 1

            #  If the reverse haven't been set ==> create it.
            if not (item.key in reverse_key_mapping):
                reverse_key_mapping[item.key] = set()

            # Store the mapping of new-key --> org-key.
            reverse_key_mapping[item.key].add(k)
            # Store the mapping of org-key --> new-key.
            key_mapping[k].add(item.key)

            org_key_to_extracted_value[k].add(item.value)

    return DottedDict({
        'extracted_map': extracted_dict,
        'key_mapping': key_mapping,
        'conflicts': conflicts,
        'key_mapping_reverse': reverse_key_mapping,
        'org_key_to_extracted_value': org_key_to_extracted_value,
        'amount_of': amount_of
    })


def reverse(d, path='', path_key: str = None):
    """ Reverses the given map.

        If the path is provided, the Data is extracted based on the given path.
        If the `pathKey`, a different Key is used.

    Args:
        d (dict): The dict used as source.
        path (str, optional): The path for the attributes in the value. Defaults to ''.
        path_key (str, optional): The path of the key, which will be provided in the `value`. Defaults to None.

    Returns:
        dict: The reversed Dict.
    """
    ret = dict()
    if path_key is None:
        path_key = path
    for k, v in d.items():
        key_to_use = k

        if path_key:
            key_to_use = rgetattr(v, path_key, __SENTINENTAL)
        value_to_use = v
        if path:
            value_to_use = rgetattr(v, path, __SENTINENTAL)
        if isinstance(value_to_use, Iterable):
            for _v in value_to_use:
                if _v not in ret:
                    ret[_v] = set()
                ret.get(_v).add(key_to_use)
        else:
            if value_to_use not in ret:
                ret[value_to_use] = set()
            ret.get(value_to_use).add(key_to_use)
    return ret
