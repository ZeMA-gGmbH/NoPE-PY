#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de


import argparse
import asyncio
import json
import logging
import sys

from nope.loader import getPackageLoader, loadConfig, loadDesiredPackages
from nope.communication import getLayer, LAYER_DEFAULT_PARAMETERS, VALID_LAYERS
from nope.dispatcher.rpcManager.selectors import ValidDefaultSelectors
from nope.helpers import ensureDottedAccess, generateId, EXECUTOR


def getArgs(add_mode=True):
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
    parser.add_argument('-p', '--channelParams', type=str, default="not-provided", dest='channelParams',
                        help='name of the communication layer to use. Possible values are: ' + ', '.join(
                            [key for key in LAYER_DEFAULT_PARAMETERS.keys()]))
    parser.add_argument('-s', '--skip-loading-config', dest='skipLoadingConfig', action='store_true',
                        help='Skips the Configuration File.')

    parser.add_argument("--default-selector", default="first", dest="defaultSelector",
                        help="The default-selector to select the service providers. Possible Values are: " +
                        ", ".join(ValidDefaultSelectors)
                        )

    parser.add_argument("--log-to-file", help="Log will be stored in a logfile.",
                        action="store_true", dest='logToFile')

    parser.add_argument('-l', '--log', type=str, default="debug", dest='log',
                        help='Level of the Logger. Valid values are "debug", "info"')

    parser.add_argument('--id', type=str, default=generateId(use_as_var=True, pre_string="_dispatcher"), dest='id',
                        help="Define a custom id to the Dispatcher",)

    parser.add_argument('--dispatcher-log', type=str, default="info", dest='dispatcherLogLevel',
                        help='Specify the Logger Level of the Dispatcher. Defaults to "info"')

    parser.add_argument('--communication-log', type=str, default="info", dest='communicationLogLevel',
                        help='Specify the Logger Level of the Communication. Defaults to "info"')

    parser.add_argument('--noBaseServices', default=False, dest='noBaseServices', action='store_true',
                        help='Flag to enable prevent the base Services to be loaded')

    args = parser.parse_args()

    if args.channel in [key for key in VALID_LAYERS.keys()]:
        pass
    else:
        print("invalid communication-layer has been selected")
        raise Exception("invalid communication-layer has been selected")

    if args.channelParams == "not-provided":
        args.channelParams = None

    if args.channelParams is not None:
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


def getDefaultParameters():
    return {
        "file": "./config/settings.json",
        "channel": "event",
        "skipLoadingConfig": False,
        "channelParams": "not-provided",
        "log": "debug",
        "dispatcherLogLevel": "info",
        "communicationLogLevel": "info",
        "delay": 2,
        "timings": {},
        "defaultSelector": "first",
        "forceUsingSelectors": False,
        "preventVarifiedNames": False,
        # "logToFile": False,
        "id": generateId(),
        "profile": False,
        "noBaseServices": False,
    }


async def generateNopeBackend(_args: dict):
    """ Helper Function, which will create a Nope Instance.
    """
    args = getDefaultParameters()    
    args.update(_args if isinstance(_args, dict) else _args.__dict__)

    # Test if we need to parse the Data.
    if isinstance(args, dict):
        args = ensureDottedAccess(args)

    if getattr(args, "channel", "event") in VALID_LAYERS:
        pass
    else:
        print("invalid communication-layer has been selected")
        return

    # Get a Communicator
    communicator = await getLayer(
        args["channel"],
        args.get("params", None),
        args["communicationLogLevel"]
    )
    # Get the Loader
    loader = getPackageLoader(
        communicator=communicator,
        **args
    )

    def __run():

        try:
            if not getattr(args, "skip_loading_config", False):
                # Load all Packages
                EXECUTOR.callParallel(
                    loadDesiredPackages,
                    loader,
                    loadConfig(args.file)
                )
        except KeyboardInterrupt as error:
            loader.dispatcher.stop()
            # Now we have to run our loop,
            # until the bridge has been disposed.
            EXECUTOR.loop.run_until_complete(
                communicator.dispose()
            )
        except FileNotFoundError:
            print("Configuration-File not Found")

    return loader, loader.dispatcher, communicator, __run


async def run(add_mode):
    args = getArgs(add_mode)
    _, __, ___, run = await generateNopeBackend(args)
    run()


def run_cli(add_mode=True):
    task = EXECUTOR.callParallel(run,add_mode)
    # Try to start our dispatcher
    EXECUTOR.run()


if __name__ == "__main__":
    import sys
    import os
    import io

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.dirname(SCRIPT_DIR))

    run_cli(False)
