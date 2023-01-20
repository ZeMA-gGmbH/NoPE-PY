#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de


from collections.abc import Iterable
from functools import reduce

from .dottedDict import DottedDict
from .objectMethods import rgetattr


def extractListElements(_list, _path: str):
    def extract(_prop):
        ret = rgetattr(_prop, _path)
        if ret:
            return ret

    return map(extract, _list)


def getElement(_list, operand, _path=''):
    for element in _list:
        if operand == rgetattr(element, _path):
            return element
    return None


def avgOfArray(_list, _path: str, defaultValue=0):
    if len(_list) == 0:
        return defaultValue

    values = map(lambda item: rgetattr(item, _path, defaultValue), _list)
    value = reduce(lambda prev, curr: prev + curr, values)
    return value / len(_list)


def minOfArray(_list, _path, defaultValue=float("inf")):
    if len(_list) == 0:
        return DottedDict({'min': defaultValue, 'index': None})

    values = list(map(lambda item: rgetattr(item, _path, defaultValue), _list))
    minValue = min(values)
    return DottedDict({'min': minValue, 'index': values.index(minValue)})


def maxOfArray(_list, _path, defaultValue=-float("inf")):
    if len(_list) == 0:
        return DottedDict({'max': defaultValue, 'index': None})

    values = list(map(lambda item: rgetattr(item, _path, defaultValue), _list))
    maxValue = max(values)
    return DottedDict({'max': maxValue, 'index': values.index(maxValue)})


def isIterable(obj):
    """ Helper to test if an objec is iterable.
    """

    if isinstance(obj, str):
        return False
    return isinstance(obj, Iterable)


def isList(obj) -> bool:
    """ Helper to check if the item is a list.

    Args:
        obj (any): The item to check

    Returns:
        bool: Result. If `True` => List
    """
    return type(obj) in (list,)


def flattenDeep(l: list) -> list:
    """ Helper to flatten a list of elements:

    Example:
        >>> l = [1, [2,3,[4,5]]]
        >>> flatten_deep(l)
        [1,2,3,4,5]

    Args:
        l (list): A nested list.

    Returns:
        list: A flattend list. (1 Dimension)
    """
    if len(l) == 0:
        return l
    if isinstance(l[0], list):
        return flattenDeep(l[0]) + flattenDeep(l[1:])
    return l[:1] + flattenDeep(l[1:])
