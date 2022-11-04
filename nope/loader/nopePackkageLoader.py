#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de
import asyncio
import itertools
import logging

from nope.dispatcher.nope_dispatcher import NopeDispatcher

from ..helpers import formatException, getNopeLogger


class NopePackageLoader():
    def __init__(self, dispatcher: NopeDispatcher,
                 logger=None, level=logging.INFO):
        self.packages = {}
        self.dispatcher = dispatcher
        self._instances = {}
        self._dispose_default_instance = []

        # Determine if a Logger is provided. If not create one.
        if logger is not None:
            self._logger = logger
        else:
            self._logger = getNopeLogger('NopePackageLoader', level)

    async def addPackage(self, package):
        """ Loader Function. self function will register all provided functions,
            create the desired instances. Additionally it will add all descriptors.

            param package: The Package to add.
        """
        if package["nameOfPackage"] in self.packages:
            raise Exception(
                "Already loaded a Package with the name \"" +
                package["nameOfPackage"] +
                "\" !"
            )

        self._logger.warn("loading package \"" +
                          package["nameOfPackage"] + "\"")

        # Store the Package:
        self.packages[package["nameOfPackage"]] = package

        # Based on the provided settings register a generator Function for the
        # Instances:
        for cl in package["providedClasses"]:
            # Get the Settings
            allowInstanceGeneration = cl.get(
                "allowInstanceGeneration", False)
            max_amountOf_instance = cl.get(
                "max_amountOf_instance", -1)

            # Get the "create instance" function
            async def _not_provided(dispatcher, identifier):
                raise Exception(
                    "A function to create the function must be provided")

            createInstance = cl.get("createInstance", _not_provided)
            selector = cl.get("selector", None)

            if selector is not None and allowInstanceGeneration:
                # Create a Function that will generate functions
                async def _generate_instance(dispatcher, identifier):
                    current_amount = self._instances.get(selector, 0)

                    if max_amountOf_instance == -1 or current_amount < max_amountOf_instance:
                        # Define the Instance:
                        instance = await createInstance(dispatcher, identifier)
                        # Assign the Name
                        instance.identifier = identifier
                        # Update the Used Instance
                        self._instances[selector] = current_amount + 1
                        # return the instance
                        return instance

                    raise Exception("Not allowed to create instances")

                await self.dispatcher.provide_instance_generator_for_externalDispatchers(
                    selector,
                    _generate_instance
                )

        for func in package["provided_functions"]:
            await self.dispatcher.registerMethod(func["function"], func["options"])

    async def generateInstances(self, test_requirements=True):
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
            definitions = package["defaultInstances"]

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

                # Store the Function, that the instance will be disposed on
                # leaving.
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
                        print(formatException(e))

        self._logger.info("generated all defined Instances")
