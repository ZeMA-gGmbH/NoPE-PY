#!/usr/bin/env python
# Author: Martin Karkowski


from distutils.core import setup

import setuptools

try:
    long_description = open("README").read()
except:
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
          install_requires=['observable', 'paho-mqtt',
                            'python-socketio[client]', 'psutil'],
          url="https://github.com/anti-held-333/nope-py.git",
          packages=["nope",
                    "nope.communication",
                    "nope.communication.layers",
                    "nope.dispatcher",
                    "nope.dispatcher.connectivity_manager",
                    "nope.eventEmitter",
                    "nope.helpers",
                    "nope.observable",
                    "nope.logger",
                    "nope.merging",
                    "nope.pub_sub"
                    ],
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
