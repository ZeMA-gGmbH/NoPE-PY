#!\\usr\\bin\\env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import json
import os

from nope.helpers import dynamicImport, formatException, dumps, loads
from nope.logger import getNopeLogger

from .run import getDefaultParameters

LOGGER = getNopeLogger("config-scanner")


def list_packages(path: str):
    """ Function to scan for packages. Therefore a given has been provided
    """

    packages = []

    for root, directories, files in os.walk(path):
        for name in files:
            if name == "__init__.py":
                # Determine the Path to the File.
                pathToFile = os.path.abspath(os.path.join(root, name))

                try:
                    # Dynamically load the File.
                    module = dynamicImport(
                        name, pathToFile)

                    # Add the Path:
                    description = module.DESCRIPTION.__dict__
                    description["path"] = pathToFile

                    description = loads(
                        dumps(
                            description,
                            parse_functions=False))

                    # Add it to the packages
                    packages.append(description)
                except ModuleNotFoundError as E:
                    LOGGER.error(formatException(E))
                except ImportError as e:
                    if e.msg == "attempted relative import with no known parent package":
                        pass
                    else:
                        print("Failed to load", pathToFile)
                        print(formatException(e))
                except AttributeError as E:
                    LOGGER.error(formatException(E))
                except Exception as e:
                    LOGGER.error(f"Failed to load '{pathToFile}'")
                    LOGGER.error(formatException(e))
                    pass

    return packages


def create_config(path_to_scan: str, dest_dir: str, name_of_file: str):
    """ Create a configuration """

    LOGGER.info(f"Starting to find files in '{path_to_scan}'")
    packages = list_packages(path_to_scan)

    try:
        os.makedirs(dest_dir)
    except OSError as e:
        pass  # already exists

    # Define the File
    path_to_config_file = os.path.join(dest_dir, name_of_file)

    for package in packages:
        for cl in package["providedClasses"]:
            cl.pop("createInstance", None)

        for func in package["providedServices"]:
            func.pop("function", None)

    config = {
        "packages": packages,
        "config": getDefaultParameters(),
        "connections": []
    }

    with open(path_to_config_file, "w") as file:
        file.write(json.dumps(config, indent=4))


def scan_cli(add_mode=True):
    import argparse
    parser = argparse.ArgumentParser(description='Module-Scanner')

    if add_mode:
        parser.add_argument('mode', type=str, default="scan",
                            help='option, used to scan for modules')

    parser.add_argument('--input', type=str, default="./", dest='input',
                        help='folder to scan for modules')
    parser.add_argument('--name', type=str, default="settings.json", dest='name',
                        help='name of the configuration file')
    parser.add_argument('--output', type=str, default="config", dest='output',
                        help='output directory for the configuration file')

    args = parser.parse_args()

    create_config(
        os.path.dirname(os.path.join(os.getcwd(), args.input)),
        os.path.join(os.getcwd(), args.output),
        args.name
    )


if __name__ == "__main__":
    scan_cli(False)
