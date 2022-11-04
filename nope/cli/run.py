#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de


import argparse
import asyncio
import json
import logging
import sys

from nope.loader import getPackageLoader, loadConfig, loadDesiredPackages
from ..communication import getLayer, LAYER_DEFAULT_PARAMETERS
from ..helpers import ensureDottedAccess


def get_args(add_mode=True):
    """ Helper Function to extract the Arguments
    """
    parser = argparse.ArgumentParser(description='cli-tool to run the backend')
    if add_mode:
        parser.add_argument('mode', type=str, default="run",
                            help='option, used to run the code')
    parser.add_argument('--file', type=str, default="config/settings.json", dest='file',
                        help='configuration file to use. This File contains the defined packages.')
    parser.add_argument('-c', type=str, default="event", dest='channel',
                        help='name of the communication layer to use. Possible values are: ' + ', '.join(
                            [key for key in LAYER_DEFAULT_PARAMETERS.keys()]))
    parser.add_argument('-l', type=str, default="debug", dest='log',
                        help='Level of the Logger. Valid values are "debug", "info"')
    parser.add_argument('-s', dest='skip_loading_config', action='store_true',
                        help='Skips the Configuration File.')
    parser.add_argument('--params', type=str, default=None, dest='params',
                        help='Paramas for the Channel, to connect to. The Following Default-Values are used: ' + json.dumps(
                            LAYER_DEFAULT_PARAMETERS))
    parser.add_argument('--force-emit', default=False, dest='force_emit', action='store_true',
                        help='Forces emitting the events of the system')

    args = parser.parse_args()

    if args.channel in [key for key in LAYER_DEFAULT_PARAMETERS.keys()]:
        pass
    else:
        print("invalid communication-layer has been selected")
        return

    if args.params is not None:
        try:
            try:
                args.params = json.loads(args.params)
                print(args.params)
            except Exception as E:
                "".startswith
                if not (args.params.startswith(
                        "{") or args.params.startswith("[")):
                    args.params = json.loads('"' + args.params + '"')
                else:
                    print(E)
                    raise Exception("Please provide valid JSON")
        except BaseException:
            print("Please provide valid JSON")
            sys.exit()

    return args


def get_default_parameters():
    return {
        "file": "config/settings.json",
        "channel": "event",
        "log": "debug",
        "skip_loading_config": False,
        "params": None
    }


def generate_nope_backend(args: dict):
    """ Helper Function, which will create a Nope Instance.
    """

    args = get_default_parameters().update(args)

    # Test if we need to parse the Data.
    if isinstance(args, dict):
        args = ensureDottedAccess(args)

    # Create an Event Loop.
    loop = asyncio.get_event_loop()

    if getattr(args, "channel", "event") in [
            key for key in LAYER_DEFAULT_PARAMETERS.keys()]:
        pass
    else:
        print("invalid communication-layer has been selected")
        return

    level = logging.INFO
    if getattr(args, "log", "info") == "debug":
        level = logging.DEBUG
    elif getattr(args, "log", "info") == "error":
        level = logging.ERROR
    elif getattr(args, "log", "info") == "fatal":
        level = logging.FATAL

    # Get a Communicator
    communicator = getLayer(
        loop, getattr(args, "channel", "event"), getattr(
            args, "params", None), level
    )
    # Get the Loader
    loader = getPackageLoader(
        communicator, {
            'force_emitting_updates': getattr(args, "force_emit", False)
        }, loop, level=level
    )

    def __run():

        try:
            if not getattr(args, "skip_loading_config", False):
                # Load all Packages
                loop.run_until_complete(
                    loadDesiredPackages(
                        loader, loadConfig(args.file)
                    )
                )

            # Try to start our dispatcher
            loader.dispatcher.run()
        except KeyboardInterrupt as error:
            loader.dispatcher.stop()
            # Now we have to run our loop,
            # until the bridge has been disposed.
            loop.run_until_complete(
                communicator.dispose()
            )
        except FileNotFoundError:
            print("Configuration-File not Found")

    return loader, loader.dispatcher, communicator, __run


def run_cli(add_mode=True):
    args = get_args(add_mode)
    _, __, ___, run = generate_nope_backend(args)

    # Now spool up the Loop
    run()


if __name__ == "__main__":
    run_cli(False)
