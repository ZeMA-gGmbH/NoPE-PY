#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from nope.dispatcher.baseServices import addAllBaseServices
from nope.dispatcher.nopeDispatcher import NopeDispatcher
from nope.helpers import ensureDottedAccess, EXECUTOR
from nope.modules import NopeGenericModule


def _performInit(dispatcher: NopeDispatcher, options):
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
        async def addServices():
            services = await addAllBaseServices(dispatcher)
            setattr(dispatcher, "baseServices", services)

        EXECUTOR.callParallel(addServices)

    return dispatcher


class NopeDispatcherSingleton(object):
    _instance = None

    def __new__(cls, options, id=None):
        if cls._instance is None:
            # Assign a Class
            cls._instance = _performInit(
                NopeDispatcher(options, id=id), options)

            # Put any initialization here.
        return cls._instance


def getDispatcher(
        dispatcherOptions,
        options=None):
    """Function, which woll return a nope-dispatcher
    """

    options = ensureDottedAccess(options, useNoneAsDefaultValue=True)
    dispatcherOptions = ensureDottedAccess(dispatcherOptions)

    # id = dispatcherOptions.communicator.id
    id = None

    dispatcherOptions["logger"] = dispatcherOptions["dispatcherLogLevel"]

    if options.singleton:
        return NopeDispatcherSingleton(dispatcherOptions, id)

    # Create the Dispatcher Instance.
    return _performInit(NopeDispatcher(dispatcherOptions, id=id), options)
