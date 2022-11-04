import inspect
import json
from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Any, Callable, List, Dict


@dataclass
class providedClass:
    selector: str
    createInstance: Callable[[Any, str], Any]
    allowInstanceGeneration: bool = True


@dataclass
class DefaultInstance:
    identifier: str
    type: str
    params: List[Any] = field(default_factory=list)


@dataclass
class ProvidedFunctions:
    function: Callable[Any, Any]


@dataclass
class Autostart:
    name: str
    params: List[Any] = field(default_factory=list)


@dataclass
class NopePackage:
    nameOfPackage: str
    autostart: Dict[str, Autostart] = field(default_factory=dict)
    defaultInstances: List[DefaultInstance] = field(default_factory=list)
    providedFunctions: List[ProvidedFunctions] = field(default_factory=list)
    providedClasses: List[providedClass] = field(default_factory=list)
    requiredPackages: List[str] = field(default_factory=list)


n = NopePackage(
    nameOfPackage="test",
    autostart=Autostart(name="test"),
    defaultInstances=[
        DefaultInstance(
            "test",
            "test-type"
        )
    ],
    providedClasses=[
        providedClass(
            "test-type",
            lambda core, name: item
        )
    ]
)


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if inspect.isfunction(o):
            return f"__FUNCTION_BEGIN__{inspect.getsource(o)}__FUNCTION_END__"
        return super().default(o)


print(json.dumps(n, cls=EnhancedJSONEncoder))
