#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import json
import logging

from ..helpers import dynamic_import, format_exception, keys_to_snake_nested
from ..logger import get_logger


def load_config(path_to_file: str):
    """ Load a config file.

        param: path_to_file: str File to load
    """
    config = {
        "functions": [],
        "packages": []
    }
    with open(path_to_file, 'r') as file:
        raw_data = file.read()
        config = json.loads(raw_data)

    return config


async def load_desired_packages(loader, packages_to_load, logger: logging.Logger = get_logger('load_desired_packages')):
    """ Load the Packages provided in the configuration
    """

    # Define the Return Array.
    packages = []

    # Scan for the Package-Files
    # And iterate over them.
    for item in packages_to_load:
        # Now Try to load a Package, to test whether is is an assembly.

        item = keys_to_snake_nested(item)

        try:
            loaded_package = dynamic_import(
                item["name_of_package"], item["path"]).DESCRIPTION

            loaded_package["autostart"] = item["autostart"]
            loaded_package["default_instances"] = item["default_instances"]

            # Add it to the list with elements.
            packages.append(loaded_package)
        except Exception as e:
            if logger is not None:
                logger.error("Failed Loading the Package " +
                             item["name_of_package"])
            else:
                print("Failed Loading the Package " +
                      item["name_of_package"])
                print(format_exception(e))

    await loader.dispatcher.ready.wait_for()

    # Iterate over the Packages
    for the_package_to_load in packages:
        try:
            await loader.add_package(the_package_to_load)
            if logger is not None:
                logger.info("Added Package " +
                            the_package_to_load["name_of_package"])

        except Exception as e:
            if logger is not None:
                logger.error("Failed add the Package " +
                             the_package_to_load["name_of_package"])
            else:
                print("Failed Loading the Package " +
                      item["name_of_package"])
                print(format_exception(e))

    # Generate the instances.
    await loader.generate_instances()
