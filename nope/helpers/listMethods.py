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
    return type(obj) in (list,)
