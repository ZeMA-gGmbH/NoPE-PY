#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from .baseModule import BaseModule
from ..helpers import ensureDottedAccess
from ..logger import getNopeLogger, DEBUG
from ..observable import NopeObservable
from ..eventEmitter import NopeEventEmitter


def _invertMode(options):
    _ret = options.copy()
    if isinstance(_ret.mode, list):
        if "subscribe" in _ret.mode:
            _ret.mode = ['publish', 'subscribe']
        else:
            _ret.mode = ['subscribe']
    elif _ret.mode == 'subscribe':
        _ret.mode = ['publish', 'subscribe']
    else:
        _ret.mode = ['subscribe']
    return _ret


class NopeGenericModule(BaseModule):
    def __init__(self, core):
        super().__init__(core)

        self._description = None
        self.dynamicInstanceMethods = dict()
        self.dynamicInstanceProperties = dict()
        self.dynamicInstanceEvents = dict()

    async def fromDescription(self, description, mode: str = 'overwrite'):
        """Initializes the Module, based on a Description.

        Args:
            description ([type]): [description]
            mode (str, optional): Defaults to 'overwrite'. Otherwise the data and Properties will be merged.

        Raises:
            Exception: [description]

        """

        # Adapt the Options:
        description = ensureDottedAccess(description)

        if mode == 'overwrite':
            await self.dispose()

            self.setAuthor(description.author.forename,
                           description.author.surename, description.author.mail)
            self.setVersion(description.version.version,
                            description.version.date)
            self.description = description.description
            self._type = description.type
            self.identifier = description.identifier

        if self.author is None:
            self._author = self._author = description.author

        if self.description is None:
            self.description = description.description

        if self.version is None:
            self._version = description.version

        if self.identifier is None:
            self.identifier = description.identifier
            self._logger = getNopeLogger(
                "generic-wrapper-" + self.identifier, DEBUG)

        for name, options in description.methods.items():

            self._logger.debug('Create function interface for "' + name + '"')

            async def _func(*args, _options=options):
                return await self._core.rpcManager.performCall(_options['id'], args, _options)

            if name in self.dynamicInstanceMethods:
                raise Exception(
                    'Name alread used. Not able to use the name twice')

            self.dynamicInstanceMethods[name] = _func

            # If the Function isnt dynamic, register it on the Object itself.
            if not options.get('isDynamic', False):
                if getattr(self, name, None) is not None:
                    raise Exception(
                        'Name alread used. Not able to use the name twice')

                setattr(self, name, _func)

            self._registeredMethods[name] = {
                'method': _func,
                'options': options
            }

        for name, options in description['properties'].items():

            self._logger.debug('Create property interface for "' + name + '"')

            # Add only elements, that are subscribed.
            # Properties, which are only publishing
            # should throw an error, if data is published
            # in a remote. self is done to maintain
            # consistency.
            if name in self.dynamicInstanceProperties:
                raise Exception(
                    'Name alread used. Not able to use the name twice')

            # Make shure it isnt published.
            # options.preventSendingToRegistery = true']

            # Register the Observable:
            self.dynamicInstanceProperties[name] = self._core.dataDistributor.register(
                # Assign a new Observable.
                NopeObservable(),
                # Use the provided Properties:
                _invertMode(options)
            )

            if not (options.get('isDynamic', False)):
                if getattr(self, name, None) is not None:
                    raise Exception(
                        'Name alread used. Not able to use the name twice')

                # Use the Same Element.
                setattr(self, name, self.dynamicInstanceProperties[name])

            self._registeredProperties[name] = {
                'observable': self.dynamicInstanceProperties[name],
                'options': options
            }

        for name, options in description['events'].items():

            self._logger.debug('Create event interface for "' + name + '"')

            # Add only elements, that are subscribed.
            # Properties, which are only publishing
            # should throw an error, if data is published
            # in a remote. self is done to maintain
            # consistency.
            if name in self.dynamicInstanceEvents:
                raise Exception(
                    'Name alread used. Not able to use the name twice')

            # Make shure it isnt published.
            # options.preventSendingToRegistery = true']

            # Register the Observable:
            self.dynamicInstanceEvents[name] = self._core.eventDistributor.register(
                # Assign a new Observable.
                NopeEventEmitter(),
                # Use the provided Properties:
                _invertMode(options)
            )

            if not (options.get('isDynamic', False)):
                if getattr(self, name, None) is not None:
                    raise Exception(
                        'Name alread used. Not able to use the name twice')

                # Use the Same Element.
                setattr(self, name, self.dynamicInstanceEvents[name])

            self._registeredEvents[name] = {
                'emitter': self.dynamicInstanceEvents[name],
                'options': options
            }

    async def registerProperty(self, *args):
        raise Exception('Function Should not be called on remote Instance!')

    async def registerMethod(self, *args):
        raise Exception('Function Should not be called on remote Instance!')

    async def unregisterMethod(self, *args):
        raise Exception('Function Should not be called on remote Instance!')

    async def unregisterProperty(self, *args):
        raise Exception('Function Should not be called on remote Instance!')

    async def init(self):
        try:
            await super().init()
        except BaseException:
            raise Exception('Call fromDescription before using')

    async def dispose(self):
        for name in self.dynamicInstanceProperties:
            self.dynamicInstanceProperties[name].dispose()
            # Remove Reference
            delattr(self, name)

        for name in self.dynamicInstanceEvents:
            self.dynamicInstanceEvents[name].dispose()
            # Remove Reference
            delattr(self, name)

        self.dynamicInstanceProperties = {}
        self.dynamicInstanceEvents = {}
        self.dynamicInstanceProperties = {}

        for name in self.dynamicInstanceMethods.keys():
            # Remove Reference
            delattr(self, name)

        self.dynamicInstanceMethods = {}
        self._registeredProperties = {}
        self._registeredEvents = {}
        self._registeredMethods = {}
