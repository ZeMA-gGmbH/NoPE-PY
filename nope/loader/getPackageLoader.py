#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import logging

from .nopePackkageLoader import NopePackageLoader
from ..dispatcher import getDispatcher


class NopePackageLoaderSingleton(object):
    _instance = None

    def __new__(cls, **settings):
        if cls._instance is None:
            cls._instance = NopePackageLoader(
                getDispatcher(settings, settings),
                **settings
            )
        # Put any initialization here.
        return cls._instance


def getPackageLoader(**settings):
    """ helper function, which will be used to create a package-loader
    """
    # Create the Dispatcher Instance.
    loader = NopePackageLoaderSingleton(**settings)
    return loader
