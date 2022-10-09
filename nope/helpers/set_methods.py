from .dotted_dict import DottedDict

def determine_difference(set01, set02):
    """ Determines the difference between the two sets.

    Args:
        set01 (set): original set
        set02 (set): adapted set

    Returns:
        DottedDict: containing `added` for the added elements and `removed` for the removed items. 
    """
    added = list()
    removed = list()
    for item in set01:
        if item not in set02:
            removed.append(item)
    for item in set02:
        if item not in set01:
            added.append(item)
    return DottedDict({'added': added, 'removed': removed})

def union(set01, set02):
    return set01 | set02

def difference(set01, set02):
    return set01 - set02