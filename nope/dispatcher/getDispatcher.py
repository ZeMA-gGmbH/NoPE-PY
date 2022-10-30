#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ..helpers import ensureDottedAccess
from ..modules import NopeGenericModule
from .nopeDispatcher import NopeDispatcher
from .baseServices import addAllBaseServices


def _perform_init(dispatcher: NopeDispatcher, options):
    """ Helper Function to initiaize the Dispatcher.

    Args:
        dispatcher (NopeDispatcher): The Dispatcher to initalize
        dispatcherOptions (dict-like): The Options of the Dispatcher.
    """

    async def creator(core, description):
        mod = NopeGenericModule(core)
        await mod.fromDescription(description, "overwrite")
        return mod

    # Register a default instance generator:
    # Defaultly generate a NopeGenericModule
    dispatcher.instanceManager.registerInternalWrapperGenerator(
        "*",
        creator
    )

    if (options.useBaseServices):
        addAllBaseServices(dispatcher)

    return dispatcher


class NopeDispatcherSingleton(object):
    _instance = None

    def __new__(cls, options):
        if cls._instance is None:
            # Assign a Class
            cls._instance = _perform_init(NopeDispatcher(options))

            # Put any initialization here.
        return cls._instance


def getDispatcher(
        dispatcherOptions,
        options=None):
    """Function, which woll return a nope-dispatcher
    """

    options = ensureDottedAccess(options)

    if options.singleton:
        return NopeDispatcherSingleton(dispatcherOptions)

    # Create the Dispatcher Instance.
    return _perform_init(NopeDispatcher(dispatcherOptions), options)
