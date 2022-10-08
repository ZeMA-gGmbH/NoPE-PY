#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de


from functools import reduce
from collections.abc import Iterable
from .object_methods import rgetattr
from .dotted_dict import DottedDict


def extract_list_element(_list, _path: str):
    def extract(_prop):
        ret = rgetattr(_prop, _path)
        if ret:
            return ret

    return map(extract, _list)


def get_element(_list, operand, _path=''):
    for element in _list:
        if operand == rgetattr(element, _path):
            return element
    return None


def avg_of_array(_list, _path: str, default_value=0):
    if len(_list) == 0:
        return default_value

    values = map(lambda item: rgetattr(item, _path, default_value), _list)
    value = reduce(lambda prev, curr: prev + curr, values)
    return value / len(_list)


def min_of_array(_list, _path, default_value=float("inf")):
    if len(_list) == 0:
        return DottedDict({'min': default_value, 'index': None})

    values = list(map(lambda item: rgetattr(item, _path, default_value), _list))
    min_value = min(values)
    return DottedDict({'min': min_value, 'index': values.index(min_value)})


def max_of_array(_list, _path, default_value=-float("inf")):
    if len(_list) == 0:
        return DottedDict({'max': default_value, 'index': None})

    values = list(map(lambda item: rgetattr(item, _path, default_value), _list))
    max_value = max(values)
    return DottedDict({'max': max_value, 'index': values.index(max_value)})


def is_iterable(_list_like):
    """ Helper to test if an objec is iterable.
    """

    if type(_list_like) is str:
        return False
    return isinstance(_list_like, Iterable)

def is_list(obj) -> bool:
    return type(obj) in (list,)
