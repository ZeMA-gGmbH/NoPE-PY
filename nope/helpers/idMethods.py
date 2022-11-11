from uuid import uuid4

from .stringMethods import replaceAll


def generateId(use_as_var: bool = False, pre_string: str = None) -> str:
    """ Helper to generate an id.
        if "use_as_var" is provided in the Options => the id is converted to an id
        if "pre_string" is provided, this string will be added in front of the id.


    Args:
        options (dotted_dict, optional):    The options. May cotains "use_as_var" and "pre_string".
                                            Defaults to dotted_dict({}).

    Returns:
        str: The id.
    """

    _id = str(uuid4())
    if use_as_var:
        _id = replaceAll(_id, '-', '')
        pre_string = pre_string if pre_string else '_'
    if pre_string:
        _id = pre_string + _id
    return _id
