#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de
import itertools
import logging
import sys
import asyncio

from nope.dispatcher.nope_dispatcher import NopeDispatcher
from ..helpers import format_exception, get_logger


class NopePackageLoader():
    def __init__(self, dispatcher: NopeDispatcher, logger=None, level=logging.INFO):
        self.packages = {}
        self.dispatcher = dispatcher
        self._instances = {}
        self._dispose_default_instance = []

        # Determine if a Logger is provided. If not create one.
        if logger is not None:
            self._logger = logger
        else:
            self._logger = get_logger('NopePackageLoader',level)

    async def add_package(self, package):
        """ Loader Function. self function will register all provided functions,
            create the desired instances. Additionally it will add all descriptors.

            param package: The Package to add.
        """
        if package["name_of_package"] in self.packages:
            raise Exception(
                "Already loaded a Package with the name \"" +
                package["name_of_package"] +
                "\" !"
            )

        self._logger.warn("loading package \"" +
                          package["name_of_package"] + "\"")

        # Store the Package:
        self.packages[package["name_of_package"]] = package

        # Based on the provided settings register a generator Function for the Instances:
        for cl in package["provided_classes"]:
            # Get the Settings
            allow_instance_generation = cl.get(
                "allow_instance_generation", False)
            max_amount_of_instance = cl.get(
                "max_amount_of_instance", -1)

            # Get the "create instance" function
            async def _not_provided(dispatcher, identifier):
                raise Exception(
                    "A function to create the function must be provided")

            create_instance = cl.get("create_instance", _not_provided)
            selector = cl.get("selector", None)

            if selector is not None and allow_instance_generation:
                # Create a Function that will generate functions
                async def _generate_instance(dispatcher, identifier):
                    current_amount = self._instances.get(selector, 0)

                    if max_amount_of_instance == -1 or current_amount < max_amount_of_instance:
                        # Define the Instance:
                        instance = await create_instance(dispatcher, identifier)
                        # Assign the Name
                        instance.identifier = identifier
                        # Update the Used Instance
                        self._instances[selector] = current_amount + 1
                        # return the instance
                        return instance

                    raise Exception("Not allowed to create instances")
                await self.dispatcher.provide_instance_generator_for_external_dispatchers(
                    selector,
                    _generate_instance
                )

        for func in package["provided_functions"]:
            await self.dispatcher.register_function(func["function"], func["options"])

    async def generate_instances(self, test_requirements=True):
        """ Function to initialize all the instances.
        """
        self._logger.info("Package Loader generates the instances.")

        if test_requirements:
            # First extract all required Packages
            reuqired_packages = set(
                itertools.chain(
                    *map(lambda package: package["required_packages"], self.packages.values()))
            )

            # Now check if the required packages are present or not.
            for req in reuqired_packages:
                if req not in self.packages:
                    raise Exception("Packages are not known")

        # Now iterate over the Packages and define the defined instances.
        for package in self.packages.values():
            definitions = package["default_instances"]

            # Iterate over the Defined Instances.
            for definition in definitions:
                self._logger.info("Requesting Generating Instance \"" +
                                  definition["identifier"] +
                                  "\" of type \"" +
                                  definition["type"] +
                                  "\"")

                instance = await self.dispatcher.generate_instance(
                    definition
                )

                # Store the Function, that the instance will be disposed on leaving.
                async def _dispose():
                    await instance.dispose()
                self._dispose_default_instance.append(_dispose)

                self._logger.info("Generated Instance" +
                                  definition["identifier"])

                # Perform the autostart:
                if definition["identifier"] in package["autostart"]:

                    self._logger.info(
                        "Trying to perform autostart Instance" + definition["identifier"])

                    try:
                        for task in package["autostart"][definition["identifier"]]:
                            if "delay" in task and task["delay"] > 0:
                                await asyncio.sleep(task["delay"])

                            func = getattr(instance, task["name"])
                            await func(*task["params"])
                    except Exception as e:
                        self._logger.error(
                            "Failed performing autostart for " + definition["identifier"])
                        self._logger.error(e)
                        print(format_exception(e))

        self._logger.info("generated all defined Instances")
