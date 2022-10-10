from .dotted_dict import DottedDict


def determineDifference(iter01, iter02):
    """ Determines the difference between the two sets.

    Args:
        iter01 (iterable): original set
        iter02 (iterable): adapted set

    Returns:
        DottedDict: containing `added` for the added elements and `removed` for the removed items.
    """
    added = list()
    removed = list()
    for item in iter01:
        if item not in iter02:
            removed.append(item)
    for item in iter02:
        if item not in iter01:
            added.append(item)
    return DottedDict({'added': added, 'removed': removed})


def union(set01: set, set02: set):
    return set01 | set02


def difference(set01: set, set02: set):
    return set01 - set02
