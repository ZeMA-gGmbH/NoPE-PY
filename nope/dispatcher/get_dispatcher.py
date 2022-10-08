#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de
# @create date 2021-01-22 09:22:55
# @modify date 2021-01-26 17:22:03
# @desc [description]

import asyncio
import logging

from ..modules import NopeGenericModule
from .nope_dispatcher import NopeDispatcher


class NopeDispatcherSingleton(object):
    _instance = None

    def __new__(cls, communicator, options={}, loop=None, logger: logging.Logger = None, level=logging.INFO):
        if cls._instance is None:
            # Create an Event Loop.
            if loop is None:
                loop = asyncio.get_event_loop()

            # Assign a Class
            cls._instance = NopeDispatcher(
                communicator, loop, options, logger, level)

            # Put any initialization here.
        return cls._instance


def get_dispatcher(communicator, options={}, loop=None, logger: logging.Logger = None, level=logging.INFO):
    """Function, which woll return a nope-dispatcher
    """

    # Create the Dispatcher Instance.
    dispatcher = NopeDispatcherSingleton(
        communicator, options, loop, logger, level)
    return dispatcher
