from uuid import uuid4
from .string_methods import replace_all
from .dotted_dict import ensure_dotted_dict


def generate_id(options=None) -> str:
    """ Helper to generate an id.
        if "use_as_var" is provided in the Options => the id is converted to an id
        if "prestring" is provided, this string will be added in front of the id.


    Args:
        options (dotted_dict, optional):    The options. May cotains "use_as_var" and "prestring".
                                            Defaults to dotted_dict({}).

    Returns:
        str: The id.
    """
    options = ensure_dotted_dict(options)

    _id = str(uuid4())
    if options.use_as_var:
        _id = replace_all(_id, '-', '')
        options.prestring = options.prestring if options.prestring else '_'
    if options.prestring:
        _id = options.prestring + _id
    return _id
