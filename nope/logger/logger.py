#!/usr/bin/env python

import logging
import sys

DEBUG = logging.DEBUG
INFO = logging.INFO
ERROR = logging.ERROR
WARNING = logging.WARNING
CRITICAL = logging.CRITICAL

LEVELS = {'info': INFO, 'debug': DEBUG, 'warn': WARNING, 'error': ERROR}

_LOGGERS = {}


class ColorizedFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def getNopeLogger(name: str, level=logging.DEBUG):
    """ Helper to return a specific logger.

    """

    if name not in _LOGGERS:

        nameToUse = name
        length = 30

        if len(nameToUse) > length:
            nameToUse = nameToUse[:length - 3] + "..."

        _logger = logging.getLogger(nameToUse)
        # Define  a Logging Format

        _format = ColorizedFormatter(
            '%(asctime)s - %(levelname)-8s - %(name)-' + str(length) + 's - %(message)s')

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

        _LOGGERS[name] = _logger

    return _LOGGERS[name]


def defineNopeLogger(param, default_name: str):
    """ Helper to define a Logger. The parameter 'param' is either a logger, None, or a Logger-Level

    """
    if not param:
        return None
    if isinstance(param, str):
        return getNopeLogger(default_name, LEVELS[param])
    return param
