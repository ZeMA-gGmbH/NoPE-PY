#!/usr/bin/env python

import logging
import sys

DEBUG = logging.DEBUG
INFO = logging.INFO
ERROR = logging.ERROR
WARNING = logging.WARNING
CRITICAL = logging.CRITICAL

LEVELS = {'info': INFO, 'debug': DEBUG, 'warn': WARNING, 'error': ERROR}


def getNopeLogger(name: str, level=logging.INFO):
    """ Helper to return a specific logger.

    """
    _logger = logging.getLogger(name)
    # Define  a Logging Format
    _format = _format = logging.Formatter('%(asctime)s - %(levelname)s - ' + name + ' - %(message)s')
    # Create Console Output
    _handler = logging.StreamHandler(sys.stdout)
    # Add the Format to the Handler
    _handler.setFormatter(_format)
    # Set Loglevel to the Desired One.
    _handler.setLevel(level)

    # Finally add the Handler to the Logger:
    _logger.addHandler(_handler)

    # Set the Log Level of the Logger.
    _logger.setLevel(level)
    return _logger


def defineNopeLogger(param, default_name: str):
    """ Helper to define a Logger. The parameter 'param' is either a logger, None, or a Logger-Level

    """
    if not param:
        return None
    if type(param) is str:
        return getNopeLogger(default_name, LEVELS[param])
    return param
