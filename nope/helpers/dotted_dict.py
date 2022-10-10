from copy import deepcopy
from .hashable import hdict, unhash, hashable

DEFAULT_METHODS = dir(hdict)


class DottedDict(hdict):
    """dot.notation access to dictionary attributes. it is although hashable. but than it can not be edited."""

    def __getattr__(self, key):
        if key in DEFAULT_METHODS:
            return getattr(self, key)
        else:
            return self.get(key)

    def __setattr__(self, key, value):
        if key in DEFAULT_METHODS:
            raise Exception("This would overwrite the default behavior")
        hdict.__setitem__(self, key, value)

    def __delattr__(self, key):
        if key in DEFAULT_METHODS:
            raise Exception("This would overwrite the default behavior")
        hdict.__delitem__(self, key)

    def copy(self):
        # Manually copy the contained Dict.
        cp = {}
        for k, v in self.items():
            if hasattr(v, "copy") and callable(v.copy):
                cp[deepcopy(k)] = v.copy()
            else:
                cp[deepcopy(k)] = deepcopy(v)
        # use that to create a copy.
        return DottedDict(cp)


#DottedDict = hashable(DottedDict)


class NoneDottedDict(DottedDict):
    """dot.notation access to dictionary attributes"""

    def __getattr__(self, key):
        if key in DEFAULT_METHODS:
            return getattr(self, key)
        else:
            try:
                return self.get(key)
            except KeyError:
                return None

    def __getitem__(self, item):
        try:
            return hdict.__getitem__(self, item)
        except KeyError:
            return None

    def copy(self):
        # Manually copy the contained Dict.
        cp = {}
        for k, v in self.items():
            if hasattr(v, "copy") and callable(v.copy):
                cp[deepcopy(k)] = v.copy()
            else:
                cp[deepcopy(k)] = deepcopy(v)
        # use that to create a copy.
        return NoneDottedDict(cp)


#NoneDottedDict = hashable(NoneDottedDict)

def _convertItem(item, useNoneAsDefaultValue: bool):
    """ Helper that converts the items to the corresponding type

    Args:
        item: The item to return

    Returns:
        any: the adapted item
    """
    if type(item) in (dict, DottedDict, NoneDottedDict):
        return convertToDottedDict(item, useNoneAsDefaultValue)
    elif type(item) in (list, set):
        new_list = list()
        for i in item:
            new_list.append(_convertItem(i, useNoneAsDefaultValue))
        return new_list
    else:
        return item


def convertToDottedDict(d: dict | DottedDict |
                        NoneDottedDict, useNoneAsDefaultValue=True):
    """ Converts a dict to a dotted dict. Although, ensures,

    Args:
        d (dict): The dictionary.
        useNoneAsDefaultValue (bool): Flag to enable the default value 'none' instead of an KeyError
    """
    ret = NoneDottedDict() if useNoneAsDefaultValue else DottedDict()
    for k, v in d.items():
        ret[k] = _convertItem(v, useNoneAsDefaultValue)

    return ret


def ensureDottedAccess(d, useNoneAsDefaultValue=True):
    """ Ensure the given item is a dotted dict.

    Args:
        d (any): Item to convert
        useNoneAsDefaultValue (bool): A flag to enable default-nones.
    Returns:
        DottedDict: _description_
    """
    if d is None:
        return DottedDict()

    elif not isinstance(d, DottedDict):
        return convertToDottedDict(d, useNoneAsDefaultValue)

    return d
