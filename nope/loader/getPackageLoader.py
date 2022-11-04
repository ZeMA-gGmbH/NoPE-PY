#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import logging

from .nopePackkageLoader import NopePackageLoader
from ..dispatcher import getDispatcher


class NopePackageLoaderSingleton(object):
    _instance = None

    def __new__(cls, communicator, options={}, loop=None,
                logger: logging.Logger = None, level=logging.INFO):
        if cls._instance is None:
            cls._instance = NopePackageLoader(getDispatcher(
                communicator, options, loop, logger, level), logger, level)
        # Put any initialization here.
        return cls._instance


def getPackageLoader(communicator, options={}, loop=None,
                     logger: logging.Logger = None, level=logging.INFO):
    """ helper function, which will be used to create a package-loader
    """
    # Create the Dispatcher Instance.
    loader = NopePackageLoaderSingleton(
        communicator, options, loop, logger, level)
    return loader
