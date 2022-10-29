#!/usr/bin/env python
# Author: Martin Karkowski


from distutils.core import setup

import setuptools

try:
    long_description = open("README").read()
except BaseException:
    long_description = """NOPE-Python Backend. A Generic Backend for Python"""

if __name__ == "__main__":
    setup(name="nope",
          version=open("VERSION").read().strip(),
          description="NOPE-Lib represents the No Programming Environment Library for python.",
          long_description=long_description,
          long_description_content_type="text/markdown",
          author="Martin Karkowski",
          author_email="m.karkowski@zema.de",
          maintainer="Martin Karkowski",
          maintainer_email="m.karkowski@zema.de",
          install_requires=['paho-mqtt',
                            'python-socketio[asyncio_client]',
                            'aiohttp',
                            'psutil'],
          url="https://github.com/anti-held-333/nope-py.git",
          packages=["nope",
                    "nope.communication",
                    "nope.communication.layers",
                    "nope.decorators",
                    "nope.dispatcher",
                    "nope.dispatcher.baseServices",
                    "nope.dispatcher.connectivityManager",
                    "nope.dispatcher.core",
                    "nope.dispatcher.instanceManager",
                    "nope.dispatcher.rpcManager",
                    "nope.eventEmitter",
                    "nope.helpers",
                    "nope.observable",
                    "nope.logger",
                    "nope.merging",
                    "nope.pubSub"
                    ],
          package_data={'': ['VERSION']},
          include_package_data=True,
          classifiers=[
              #   "Development Status :: 4 - Production/Stable",
              "Operating System :: OS Independent",
              "Programming Language :: Python",
              "Topic :: Scientific/Engineering",
              "Topic :: Software Development :: Libraries :: Python Modules",
          ],
          #   entry_points={
          #       'console_scripts': [
          #           'nope-py = nope.cli:main_cli',
          #       ],
          #   },
          )
