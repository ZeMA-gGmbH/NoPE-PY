#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ..helpers import keysToCamelNested, getPropertyPath, isPropertyPathCorrect, isMethodPathCorrect, getMethodPath, \
    getEmitterPath, isEmitterPathCorrect, ensureDottedAccess, EXECUTOR

from ..logger import getNopeLogger


class BaseModule(object):
    """A Base Class Describing a Module.
    """

    decoratedItems = list()

    @property
    def type(self):
        """Type Idefintifier of the Element

        Returns:
            str: Type Idefintifier of the Element
        """
        return self._type

    def setAuthor(self, forename: str, surename: str, mail: str):
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

    def setVersion(self, version: str, date):
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
    def methods(self) -> dict:
        """Helper to list the Functions

        Returns:
            dict: A List with all Functions available.
        """
        ret = {}

        for name, funcs in self._registeredMethods.items():
            ret[name] = funcs["options"]

        return ret

    @property
    def properties(self) -> dict:
        """Helper to list all Properties.

        Returns:
            dict: [description]
        """

        ret = {}

        for name, prop in self._registeredProperties.items():
            ret[name] = prop["options"]
        return ret

    @property
    def events(self) -> dict:
        """Helper to list all Properties.

        Returns:
            dict: [description]
        """

        ret = {}

        for name, prop in self._registeredEvents.items():
            ret[name] = prop["options"]
        return ret

    def __init__(self, core):
        super().__init__()

        if not hasattr(self, "decoratedItems"):
            setattr(self, "decoratedItems", [])

        self._logger = getNopeLogger(self.__class__.__name__)

        self._core = core

        self.description = None
        self._author = None
        self._version = None
        self.identifier = None

        self._registeredMethods = dict()
        self._registeredProperties = dict()
        self._registeredEvents = dict()
        self._type = str(self.__class__.__name__)
        self.uiLinks = []

        # Helper for the Decorator
        self._markedElements = dict()

    async def registerProperty(self, name: str, observable, options=None):
        """ Function to register a property. This will provide the property in the NoPE-Environment.

        Args:
            name (str): Name of the property, which should be used to forward the data
            observable (nope-observable):  the property to use
            options (dict): options, to assign a different topic and options to select, whether the content of the property should be "published" and/or "subscribed"

        Returns:
            [type]: [description]
        """

        options = ensureDottedAccess(options)

        # Unregister Property
        await self.unregisterProperty(name)

        # Adapt the Topic:
        if not "topic" in options:
            # Raise an error, because we expect and dict or an string
            options.topic = getPropertyPath(self.identifier, name)

        if not "mode" in options:
            options.mode = ["publish", "subscrie"]

        if isinstance(options.topic, str) and not isPropertyPathCorrect(
                self.identifier, options.topic):
            # Adapt the name.
            options.topic = getPropertyPath(self.identifier, options.topic)
        else:
            if 'subscribe' in options.topic and not isPropertyPathCorrect(
                    self.identifier, options.topic.subscribe):
                options.topic.subscribe = getPropertyPath(
                    self.identifier, options.topic.subscribe)

            if 'publish' in options.topic and not isPropertyPathCorrect(
                    self.identifier, options.topic.publish):
                options.topic.publish = getPropertyPath(
                    self.identifier, options.topic.publish)

        observable = self._core.dataDistributor.register(observable, options)

        # Register the new Property.
        self._registeredProperties[name] = {
            'observable': observable,
            'options': options
        }

    async def registerEvent(self, name: str, emitter, options=None):
        """ Function to register an emitter as property. This will provide the emitter in the NoPE-Environment.

        Args:
            name (str): Name of the property, which should be used to forward the data
            emitter (nope-emitter): the property to use
            options (dict): options, to assign a different topic and options to select, whether the content of the property should be "published" and/or "subscribed"

        Returns:
            [type]: [description]
        """
        options = ensureDottedAccess(options)

        # Unregister Property
        await self.unregisterEvent(name)

        # Adapt the Topic:
        if not "topic" in options:
            # Raise an error, because we expect and dict or an string
            options.topic = getEmitterPath(self.identifier, name)
        elif isinstance(options.topic, str) and not isEmitterPathCorrect(self.identifier, options.topic):
            # Adapt the name.
            options.topic = getEmitterPath(self.identifier, options.topic)
        else:
            if 'subscribe' in options.topic and not isEmitterPathCorrect(
                    self.identifier, options.topic.subscribe):
                options.topic.subscribe = getEmitterPath(
                    self.identifier, options.topic.subscribe)

            if 'publish' in options.topic and not isEmitterPathCorrect(
                    self.identifier, options.topic.publish):
                options.topic.publish = getEmitterPath(
                    self.identifier, options.topic.publish)

        emitter = await self._core.eventDistributor.register(emitter, options)

        # Register the new Property.
        self._registeredEvents[name] = {
            'emitter': emitter,
            'options': options
        }

    async def registerMethod(self, name: str, method, options=None):

        options = ensureDottedAccess(options)

        # Unregister the Function
        await self.unregisterMethod(name)

        # Adapt the Method ID
        if options.id is not None:
            if not isMethodPathCorrect(self.identifier, options.id):
                options.id = getMethodPath(self.identifier, options.id)
        else:
            options.id = getMethodPath(self.identifier, name)

        method = await self._core.rpcManager.registerService(method, options)

        # Register the new Function.
        self._registeredMethods[name] = {
            'method': method,
            'options': options
        }

    async def unregisterMethod(self, name: str):
        """ Unregister a method. (This is the case if the class provides dynamic classes)


        Args:
            name (str): Name of the function used during registering.
        """
        # Test if the Method is already registerd,
        # If so => unregister it first.
        if name in self._registeredMethods:
            await self._core.rpcManager.unregisterService(self._registeredMethods[name]['method'])

    async def unregisterProperty(self, name: str):
        """ Helper Function to unregister an Observable (a Property.)

        Args:
            name (str): Name of the Property used during registering.
        """
        # Test if the Property is already registerd,
        # If so => unregister it first.
        if name in self._registeredProperties:
            await self._core.dataDistributor.unregister(self._registeredProperties[name]['observable'])

    async def unregisterEvent(self, name: str):
        """ Helper Function to unregister an Eventbased Property

        Args:
            name (str):  Name of the Property used during registering.
        """
        # Test if the Property is already registerd,
        # If so => unregister it first.
        if name in self._registeredProperties:
            await self._core.eventDistributor.unregister(self._registeredProperties[name]['emitter'])

    async def listFunctions(self):
        return list(self._registeredMethods.values())

    async def listProperties(self):
        return list(self._registeredProperties.values())

    async def listEvents(self):
        return list(self._registeredEvents.values())

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

        # TODO: Test the Implementation with decorators.
        if self.decoratedItems:
            for item in self.decoratedItems:

                # Currently our decorators will add the information to all
                # classes...
                if item.owner != self.__class__:
                    # FIX
                    continue

                if item.type == "method":
                    await self.registerMethod(item.accessor, getattr(self, item.accessor), item.options)
                elif item.type == "property":
                    await self.registerProperty(item.accessor, getattr(self, item.accessor), item.options)
                elif item.type == "event":
                    await self.registerEvent(item.accessor, getattr(self, item.accessor), item.options)

    def exportProperty(self, name: str, observable, options):
        """ Function to export an Property. This will provide the Property (emits and receives events on change, and contains the current value.)
            in the NoPE-Environment.

        Args:
            name (str): Name of the property, which should be used to forward the data
            observable (nope-observable): the property to use
            options (dict-like): Options, used during sharing
        """
        # Create a Factory of the Element
        EXECUTOR.callParallel(self.registerProperty, name, observable, options)

    def exportMethod(self, name: str, func, options):
        """ Helper Function, to export method and provided it in the NoPE-Environment. Executes "registerMethod" in the background

        Args:
            name (str): Name of the property, which should be used as service name.
            func (callable): The method itself
            options (dict-like): Options, used during sharing
        """
        EXECUTOR.callParallel(self.registerMethod, name, func, options)

    def exportEvent(self, name: str, emitter, options):
        """ Function to export an Property as Event-Emitter (which emits en receives events). This will provide the Property in the NoPE-Environment.

        Args:
            name (str): Name of the property, which should be used to forward the data
            emitter (nope-emitter): the property to use
            options (dict-like): Options, used during sharing
        """
        # Create a Factory of the Element
        EXECUTOR.callParallel(self.registerProperty, name, emitter, options)

    async def dispose(self):
        """ Disposes the instance. This results in unregistering the properties, functions etc.
        """
        # Unregister all Methods and Functions
        for name in self._registeredMethods.keys():
            await self.unregisterMethod(name)

        # Remove all known Functions
        self._registeredMethods = dict()

        # Unregister all Properties.
        for name in self._registeredProperties.keys():
            await self.unregisterProperty(name)

        # Remove all known Properties.
        self._registeredProperties = dict()

        # Unregister all Properties.
        for name in self._registeredEvents.keys():
            await self.unregisterEvent(name)

        # Remove all known Properties.
        self._registeredEvents = dict()

    def getIdentifierOf(self, prop_event_or_method, type=None):
        """ Helper to extract the identifier for the given method, event or proterty
            or property.
        """

        # To Extract the name of the Property or the Function, we will iterate over
        # the registered properties and the regiestered functions. If the prop or the
        # function matches ==> return the name otherwise we throw an error.

        for data in self._registeredProperties.values():
            if data["observable"] == prop_event_or_method:
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

        for data in self._registeredEvents.values():
            if data["emitter"] == prop_event_or_method:
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

        for data in self._registeredMethods.values():
            if prop_event_or_method == data["func"]:
                return data["options"]["id"]

        raise Exception("Item not found. Is it registered?")

    def toDescription(self):
        ret = {
            'author': self.author,
            'description': self.description,
            'methods': self.methods,
            'events': self.events,
            'identifier': self.identifier,
            'properties': self.properties,
            'type': self.type,
            'version': self.version,
            'uiLinks': self.uiLinks
        }

        return ret
