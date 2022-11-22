from dataclasses import is_dataclass, asdict
from inspect import isfunction, getsource
from json import dumps as _dumps, loads as _loads, JSONEncoder, JSONDecoder
from typing import Any

FUNC_BEGIN = "__FUNCTION_BEGIN__"
FUNC_END = "__FUNCTION_END__"


class EnhancedJSONEncoder(JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isfunction(o):
            code = getsource(o)

            if code.startswith("def"):

                code = code.replace("\n", "\\n")

                return f"{FUNC_BEGIN}{code}{FUNC_END}{o.__name__}"

            elif "lambda" in code:
                idx = code.index("lambda")
                return f"{FUNC_BEGIN}{code[idx:]}{FUNC_END}"
        return super().default(o)

class SimpleJSONEncoder(JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        elif isfunction(o):
            return None
        return super().default(o)


class EnhancedJSONDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        JSONDecoder.__init__(
            self,
            object_hook=self.object_hook,
            *args,
            **kwargs)

    def object_hook(self, o):
        if isinstance(o, dict):

            to_adapt = dict()

            for key, value in o.items():
                if isinstance(value, str):
                    if value.startswith(FUNC_BEGIN) and FUNC_END in value:
                        code = value[len(FUNC_BEGIN):value.index(FUNC_END)]
                        if code.startswith("def"):
                            exec(code)
                            name = value[value.index(
                                FUNC_END) + len(FUNC_END):]
                            o[key] = eval(name)
                        else:
                            o[key] = eval(code)
                        continue
        return o


def dumps(o: Any, indent: int = 4, parse_functions=True, **kwargs) -> str:
    """ Helper function, to dump data to JSON and serialize
        python functions.


    Args:
        o (Any): The Object to start
        indent (int, optional): The indent. Defaults to 4.
        parse_functions (bool, optional): Flag to enable storing Python Functions. Defaults to True.

    Returns:
        str: The parsed object.
    """
    if parse_functions:
        kwargs.pop("cls", None)
        return _dumps(o, indent=indent, cls=EnhancedJSONEncoder, **kwargs)
    return _dumps(o, indent=indent, cls=SimpleJSONEncoder, **kwargs)


def loads(s: str, parse_functions=True, **kwargs) -> Any:
    if parse_functions:        
        kwargs.pop("cls", None)
        return _loads(s, cls=EnhancedJSONDecoder, **kwargs)
    return _loads(s, **kwargs)
