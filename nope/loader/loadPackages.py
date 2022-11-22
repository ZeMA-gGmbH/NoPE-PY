#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import json
import logging

from ..helpers import dynamicImport, formatException, ensureDottedAccess
from ..logger import getNopeLogger


def loadConfig(pathToFile: str):
    """ Load a config file.

        param: pathToFile: str File to load
    """
    config = {
        "functions": [],
        "packages": []
    }
    with open(pathToFile, 'r') as file:
        raw_data = file.read()
        config = json.loads(raw_data)

    return config


async def loadDesiredPackages(loader, packages_to_load, logger: logging.Logger = getNopeLogger('loadDesiredPackages')):
    """ Load the Packages provided in the configuration
    """

    # Define the Return Array.
    pkgs = []

    # Scan for the Package-Files
    # And iterate over them.
    for item in packages_to_load:
        # Now Try to load a Package, to test whether is is an assembly.

        try:
            loadedPackage = dynamicImport(
                item["nameOfPackage"], item["path"]).DESCRIPTION

            loadedPackage = ensureDottedAccess(loadedPackage)

            loadedPackage["autostart"] = item["autostart"]
            loadedPackage["defaultInstances"] = item["defaultInstances"]

            # Add it to the list with elements.
            pkgs.append(loadedPackage)
        except Exception as e:
            if logger is not None:
                logger.error("Failed Loading the Package " +
                             item["nameOfPackage"])
            else:
                print("Failed Loading the Package " +
                      item["nameOfPackage"])
                print(formatException(e))

    await loader.dispatcher.ready.waitFor()

    # Iterate over the Packages
    for pkgToLoad in pkgs:
        try:
            await loader.addPackage(pkgToLoad)
            if logger is not None:
                logger.info("Added Package " +
                            pkgToLoad["nameOfPackage"])

        except Exception as e:
            if logger is not None:
                logger.error("Failed add the Package " +
                             pkgToLoad["nameOfPackage"])
            else:
                print("Failed Loading the Package " +
                      item["nameOfPackage"])
                print(formatException(e))

    # Generate the instances.
    await loader.generateInstances()
