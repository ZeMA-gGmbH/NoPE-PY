from dataclasses import dataclass, field
from typing import Any, Callable, List, Dict, Union


@dataclass
class ServiceUi:
    """ Definition of an ui.

        parameters:
            file =                          An additional file (javascript) -> defining the ui. Defaults to False -> No extra File is required.
            autoGenBySchema =               Autogenerates the ui to configure the service based on the given schema
            requiredProvidersForRendering = Defined items (service), that must be present in the network, to define the ui-file.
    """

    file: str | bool = False
    """ An additional file (javascript) -> defining the ui. Defaults to False -> No extra File is required.
    """

    autoGenBySchema: bool = False
    """ Autogenerates the ui to configure the service based on the given schema
    """

    requiredProvidersForRendering: List[str] = field(default_factory=list)
    """ Defined items, that must be present in the network,
        to define the ui-file.
    """


@dataclass
class CallOptions:
    """ Options used in an RPC-Call

        parameters:
            resultSink  = Desired result sink. If implemented, the result will be published on this topic as well.
            timeout     = A User Provided Timeout of the call. After the timeout has been ellapsed, the task is
                          cancelled with a timeout error. The Time is given in **ms**
    """
    resultSink: str = None
    """ Desired result sink. If implemented, the result will be published on this topic as well. """

    timeout: int = -1
    """ A User Provided Timeout of the call. After the timeout has been ellapsed, the task is
        cancelled with a timeout error. The Time is given in **ms**
    """


@dataclass
class ServiceOptions:

    schema: Any
    """ Schmea describing the Function.
    """

    resultSink: str = None
    """ Desired result sink. If implemented, the result will be published on this topic as well. """

    timeout: int = -1
    """ A User Provided Timeout of the call. After the timeout has been ellapsed, the task is
        cancelled with a timeout error. The Time is given in **ms**
    """

    id: str | bool = False
    """ Instead of generating a uuid an id could be provided
    """

    ui: ServiceUi = field(default_factory=ServiceUi)
    """ Defintion of the UI.
    """

    isDynamic: bool = False
    """ Flag to mark the Function as Dynamically created
    """


@dataclass
class ProvidedClass:
    selector: str
    createInstance: Callable[Any, Any]
    allowInstanceGeneration: bool = True
    maxAmountOfInstance: int = -1


@dataclass
class DefaultInstance:
    identifier: str
    type: str
    params: List[Any] = field(default_factory=list)


@dataclass
class ProvidedService:
    function: Callable[Any, Any]
    options: ServiceOptions


@dataclass
class Autostart:
    name: str
    params: List[Any] = field(default_factory=list)
    delay: int = -1


@dataclass
class NopePackage:
    nameOfPackage: str
    autostart: Dict[str, List[Autostart]] = field(default_factory=dict)
    defaultInstances: List[DefaultInstance] = field(default_factory=list)
    providedServices: List[ProvidedService] = field(default_factory=list)
    providedClasses: List[ProvidedClass] = field(default_factory=list)
    requiredPackages: List[str] = field(default_factory=list)
