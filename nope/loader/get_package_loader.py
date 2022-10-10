#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import logging

from ..dispatcher import get_dispatcher
from .nope_packkage_loader import NopePackageLoader


class NopePackageLoaderSingleton(object):
    _instance = None

    def __new__(cls, communicator, options={}, loop=None,
                logger: logging.Logger = None, level=logging.INFO):
        if cls._instance is None:
            cls._instance = NopePackageLoader(get_dispatcher(
                communicator, options, loop, logger, level), logger, level)
        # Put any initialization here.
        return cls._instance


def get_package_loader(communicator, options={}, loop=None,
                       logger: logging.Logger = None, level=logging.INFO):
    """ helper function, which will be used to create a package-loader
    """
    # Create the Dispatcher Instance.
    loader = NopePackageLoaderSingleton(
        communicator, options, loop, logger, level)
    return loader
