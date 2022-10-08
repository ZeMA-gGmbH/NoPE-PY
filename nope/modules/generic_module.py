#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ..helpers import keys_to_snake_nested
from .base_module import BaseModule


class NopeGenericModule(BaseModule):
    def __init__(self, dispatcher):
        super().__init__(dispatcher)

        self._description = None
        self.dynamic_instance_methods = dict()
        self.dynamic_instance_properties = dict()
        self.__attributes = dict()

    async def from_description(self, description, mode: str = 'overwrite'):
        """Initializes the Module, based on a Description.

        Args:
            description ([type]): [description]
            mode (str, optional): Defaults to 'overwrite'. If set, updating.

        Raises:
            Exception: [description]

        """

        # Adapt the Options:
        description = keys_to_snake_nested(description)

        if mode == 'overwrite':
            await self.dispose()

            self.set_author(description['author']['forename'],
                            description['author']['surename'], description['author']['mail'])
            self.set_version(
                description['version']['version'], description['version']['date'])
            self.description = description['description']
            self._type = description['type']
            self.identifier = description['identifier']

        else:

            if self.author == None:
                self._author = description['author']

            if self.description == None:
                self.description = description['description']

            if self.version == None:
                self._version = description['version']

            if self.identifier == None:
                self.identifier = description['identifier']

        for name, options in description['functions'].items():

            async def _func(*args, _options=options):
                return await self._dispatcher.perform_call(_options['id'], args, _options)

            if name in self.dynamic_instance_methods:
                raise Exception(
                    'Name alread used. Not able to use the method name twice')

            self.dynamic_instance_methods[name] = _func

            # If the Function isnt dynamic, register it on the Object itself.
            if not options.get('is_dynamic', False):
                if getattr(self, name, None) is not None:
                    raise Exception(
                        'Name alread used. Not able to use the method name twice')

                setattr(self, name, _func)

            self._registered_functions[name] = {
                'func': _func,
                'options': options
            }

        for name, options in description['properties'].items():

            # Add only elements, that are subscribed.
            # Properties, which are only publishing
            # should throw an error, if data is published
            # in a remote. self is done to maintain
            # consistency.
            if name in self.dynamic_instance_properties:
                raise Exception(
                    'Name alread used. Not able to use the method name twice')

            # Make shure it isnt published.
            # options.preventSendingToRegistery = true']

            # Register the Observable:
            self.dynamic_instance_properties[name] = await self._dispatcher.register_observable(
                # Assign a new Observable.
                self._dispatcher.generate_observable(),
                # Use the provided Properties:
                options
            )

            if not(options.get('is_dynamic', False)):
                if getattr(self, name, None) is not None:
                    raise Exception(
                        'Name alread used. Not able to use the method name twice')

                # Use the Same Element.
                setattr(self, name, self.dynamic_instance_properties[name])

            self._registered_properties[name] = {
                'observable': self.dynamic_instance_properties[name],
                'options': options
            }

    async def register_property(self, *args):
        raise Exception('Function Should not be called on remote!')

    async def register_function(self, *args):
        raise Exception('Function Should not be called on remote!')

    async def unregisterFunction(self, *args):
        raise Exception('Function Should not be called on remote!')

    async def unregisterProperty(self, *args):
        raise Exception('Function Should not be called on remote!')

    async def init(self):
        try:
            await super().init()
        except:
            raise Exception('Call fromDescription before using')

    async def dispose(self):
        for name in self.dynamic_instance_properties:
            self.dynamic_instance_properties[name].dispose()
            # Remove Reference
            delattr(self, name)

        self.dynamic_instance_properties = {}

        self._registered_functions = {}

        self.dynamic_instance_properties = {}

        for name in self.dynamic_instance_methods.keys():
            # Remove Reference
            delattr(self, name)

        self.dynamic_instance_methods = {}
        self._registered_properties = {}
