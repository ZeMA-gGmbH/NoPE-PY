#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import importlib
import sys


def dynamicImport(name: str, pathToFile: str):
    """ Helper to dynamically import content of a file.

    Args:
        name (str): name of the object to load
        pathToFile (str): the path to the file.

    Returns:
        any: the loaded module
    """
    spec = importlib.util.spec_from_file_location(
        name, pathToFile)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module
