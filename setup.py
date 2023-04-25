#!/usr/bin/env python
# Author: Martin Karkowski


from setuptools import setup

try:
    long_description = open("./README.md").read()
except BaseException:
    long_description = """NOPE-Python Backend. A Generic Backend for Python"""

if __name__ == "__main__":
    setup(name="nope_py",
          version="1.7.1rc3",
          description="NOPE-Lib represents the No Programming Environment Library for python.",
          long_description=long_description,
          long_description_content_type="text/markdown",
          author="Martin Karkowski",
          author_email="m.karkowski@zema.de",
          maintainer="Martin Karkowski",
          maintainer_email="m.karkowski@zema.de",
          install_requires=['paho-mqtt',
                            'python-socketio[asyncio_client]',
                            'psutil'],
          url="https://github.com/ZeMA-gGmbH/NoPE-PY.git",
          packages=["nope",
                    "nope.cli",
                    "nope.communication",
                    "nope.communication.layers",
                    "nope.decorators",
                    "nope.demo",
                    "nope.demo.instances",
                    "nope.demo.plugins",
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
                    "nope.loader",
                    "nope.merging",
                    "nope.modules",
                    "nope.plugins",
                    "nope.pubSub",
                    "nope.types"
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
            entry_points={
                'console_scripts': [
                    'nope-py = nope.cli:main_cli',
                ],
            },
          )
