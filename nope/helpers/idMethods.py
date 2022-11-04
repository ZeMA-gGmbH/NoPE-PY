from uuid import uuid4

from .dottedDict import ensureDottedAccess
from .stringMethods import replaceAll


def generateId(options=None) -> str:
    """ Helper to generate an id.
        if "useAsVar" is provided in the Options => the id is converted to an id
        if "preString" is provided, this string will be added in front of the id.


    Args:
        options (dotted_dict, optional):    The options. May cotains "useAsVar" and "preString".
                                            Defaults to dotted_dict({}).

    Returns:
        str: The id.
    """
    options = ensureDottedAccess(options)

    _id = str(uuid4())
    if options.useAsVar:
        _id = replaceAll(_id, '-', '')
        options.preString = options.preString if options.preString else '_'
    if options.preString:
        _id = options.preString + _id
    return _id
