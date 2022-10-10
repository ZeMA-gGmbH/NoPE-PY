#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import asyncio

from ..helpers import keysToCamelNested
from ..logger import getNopeLogger


class BaseModule(object):
    """A Base Class Describing a Module.
    """

    @property
    def type(self):
        """Type Idefintifier of the Element

        Returns:
            str: Type Idefintifier of the Element
        """
        return self._type

    def set_author(self, forename: str, surename: str, mail: str):
        """Custom Helper Function to generate an author

        Args:
            forename (str): Forename of the Author
            surename (str): Surename of the Author
            mail (str): Mail of the Author
        """
        self._author = {
            'forename': forename,
            'surename': surename,
            'mail': mail
        }

    @property
    def author(self):
        """Helper to return the Author

        Returns:
            dict: A Dict, describing the Author
        """
        return self._author

    def set_version(self, version: str, date):
        """Helper Function to set a Version of a Module.

        Args:
            version (str): The Version as String. E.G. 0.9.0
            date (date): The Date of the Version
        """
        self._version = {
            'version': version,
            'date': date
        }

    @property
    def version(self):
        """Getter for the Version

        Returns:
            dict: A Dict describing the Version
        """
        return self._version

    identifier: str
    description: str

    @property
    def functions(self) -> dict:
        """Helper to list the Functions

        Returns:
            dict: A List with all Functions available.
        """
        ret = {}

        for name, funcs in self._registered_functions.items():
            ret[name] = funcs["options"]

        return ret

    @property
    def properties(self) -> dict:
        """Helper to list all Properties.

        Returns:
            dict: [description]
        """

        ret = {}

        for name, prop in self._registered_properties.items():
            ret[name] = prop["options"]
        return ret

    def __init__(self, dispatcher):
        super().__init__()
        self._logger = getNopeLogger(self.__class__.__name__)

        self._dispatcher = dispatcher

        self.description = None
        self._author = None
        self._version = None
        self.identifier = None

        self._registered_functions = dict()
        self._registered_properties = dict()
        self._type = str(self.__class__.__name__)
        self.ui_links = []

    def export_property(self, name: str, observable, options):
        """ Function to export an Property. This will provide the Property in the NoPE-Environment. This
            can be used as decorator.

        Args:
            name (str): Name of the property, which should be used to forward the data
            observable (nope-observable): the property to use
            options ([type]): Options, used during sharing
        """
        # Create a Factory of the Element
        self._dispatcher.loop.run_until_complete(
            self.register_property(name, observable, options)
        )

    def get_identifier_of(self, prop_or_func, type=None):
        """ Helper to extract the identifier for the given function
            or property.
        """

        # To Extract the name of the Property or the Function, we will iterate over
        # the registered properties and the regiestered functions. If the prop or the
        # function matches ==> return the name otherwise we throw an error.

        for data in self._registered_properties.values():
            if data["observable"] == prop_or_func:
                # Extract the Topics, pipe and scope.
                _subTopic = data["options"]['topic'] if isinstance(
                    data["options"]['topic'], str) else data["options"]['topic'].get(
                    ['subscribe'], None)
                _pubTopic = data["options"]['topic'] if isinstance(
                    data["options"]['topic'], str) else data["options"]['topic'].get(
                    ['publish'], None)

                if type == "topic_to_subscribe":
                    if _subTopic is None:
                        raise Exception("No topic for subscribing defined")

                    return _subTopic

                elif type == "topic_to_publish":
                    if _pubTopic is None:
                        raise Exception("No topic for publishing defined")

                    return _pubTopic

                elif type == "both":
                    if not isinstance(data["options"]["topic"], str):
                        return data["options"]["topic"]

                    raise Exception(
                        "Prop uses the Same Element")

                else:
                    if isinstance(data["options"]["topic"], str):
                        return data["options"]["topic"]

                    raise Exception(
                        "Prop uses different name of Publishing an Subscribing")

        for data in self._registered_functions.values():
            if prop_or_func == data["func"]:
                return data["options"]["id"]

        raise Exception("Item not found. Is it registered?")

    async def register_property(self, name: str, observable, options):
        """ Function to register a property. This will provide the property in the NoPE-Environment.

        Args:
            name (str): Name of the property, which should be used to forward the data
            observable (nope-observable):  the property to use
            options (dict): options, to assign a different topic and options to select, whether the content of the property should be "published" and/or "subscribed"

        Returns:
            [type]: [description]
        """
        # Unregister Property
        await self.unregister_property(name)

        # Adapt the Topic:
        if isinstance(options['topic'], str):
            options['topic'] = self.identifier + '.prop.' + name
        else:
            if 'subscribe' in options['topic'] and not options['topic']['subscribe'].startswith(
                    self.identifier + '.prop.'):
                options['topic']['subscribe'] = self.identifier + \
                    '.prop.' + options['topic']['subscribe']

            if 'publish' in options['topic'] and not options['topic']['publish'].startswith(
                    self.identifier + '.prop.'):
                options['topic']['publish'] = self.identifier + \
                    '.prop.' + options['topic']['publish']

        observable = await self._dispatcher.register_observable(observable, options)

        # Register the new Property.
        self._registered_properties[name] = {
            'observable': observable,
            'options': options
        }

        return observable

    def export_function(self, name: str, func, options):
        """Helper Function, to export functions. This Function can be used as decorator
        """
        asyncio.ensure_future(
            self.register_function(name, func, options)
        )

    async def register_function(self, name: str, func, options):
        # Unregister the Function
        await self.unregister_function(name)

        # Adapt the Method ID
        options['id'] = self.identifier + '.method.' + name

        # Adapt the Topic:
        if isinstance(options['id'], str) and not options['id'].startswith(
                self.identifier + '.method.'):
            options['id'] = self.identifier + '.method.' + name
        elif not isinstance(options['id'], str):
            raise TypeError("Id must be provided")

        func = await self._dispatcher.register_function(func, options)

        # Register the new Function.
        self._registered_functions[name] = {
            'func': func,
            'options': options
        }

    async def unregister_function(self, name: str):
        # Test if the Method is already registerd,
        # If so => unregister it first.
        if name in self._registered_functions:
            await self._dispatcher.unregister_function(self._registered_functions[name]['func'], {
                'prevent_sending_to_registery': True
            })

    async def unregister_property(self, name: str):
        # Test if the Property is already registerd,
        # If so => unregister it first.
        if name in self._registered_properties:
            await self._dispatcher.unregister_observable(self._registered_properties[name]['observable'], {
                'prevent_sending_to_registery': True
            })

    async def listFunctions(self):
        return list(self._registered_functions.values())

    async def listProperties(self):
        return list(self._registered_properties.values())

    async def init(self):
        # In self base Implementation, check if every requried property is set
        # correctly. If not => raise an error.
        self._logger = getNopeLogger(
            self.__class__.__name__ + '<' + self.identifier + '>')

        if self.type is None:
            raise Exception(
                'Please Provide a Name for the Module before initializing')

        if self.description is None:
            raise Exception(
                'Please Provide a Description for the Module before initializing')

        if self.author is None:
            raise Exception(
                'Please Provide an Author for the Module before initializing')

        if self.version is None:
            raise Exception(
                'Please Provide a Version for the Module before initializing')

        if self.identifier is None:
            raise Exception(
                'Please Provide an Identifier for the Module before initializing')

    async def dispose(self):
        # Unregister all Methods and Functions
        for name in self._registered_functions.keys():
            await self.unregister_function(name)

        # Remove all known Functions
        self._registered_functions = dict()

        # Unregister all Properties.
        for name in self._registered_properties.keys():
            await self.unregister_property(name)

        # Remove all known Properties.
        self._registered_properties = dict()

    def to_description(self):
        ret = {
            'author': self.author,
            'description': self.description,
            'functions': self.functions,
            'identifier': self.identifier,
            'properties': self.properties,
            'type': self.type,
            'version': self.version,
            'uiLinks': self.ui_links
        }

        return keysToCamelNested(ret)
