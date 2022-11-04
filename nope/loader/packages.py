from dataclasses import dataclass, field
from typing import Any, Callable, List, Dict


@dataclass
class ProvidedClass:
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
    providedClasses: List[ProvidedClass] = field(default_factory=list)
    requiredPackages: List[str] = field(default_factory=list)
