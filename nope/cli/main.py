#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import sys

from .run import run_cli
from .scan import scan_cli

help_message = '''
usage: nope-py [-h] mode

NoPE - Command Line Interface. Please select the option you want.

positional arguments:
    mode        mode of the cli-tool. Possible Options "run", "scan"          

optional arguments:
    -h, --help  show this help message and exit 
'''


def main_cli():
    if len(sys.argv) >= 2:
        if (sys.argv[1] == "run"):
            run_cli(True)
        elif (sys.argv[1] == "scan"):
            scan_cli(True)
        else:
            print(help_message)
    else:
        print(help_message)
