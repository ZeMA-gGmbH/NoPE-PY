#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import asyncio
import json

from nope.communication.bridge import Bridge
from nope.dispatcher.connectivityManager import NopeConnectivityManager
from nope.dispatcher.rpcManager import NopeRpcManager
from nope.helpers import SPLITCHAR, ensureDottedAccess, generateId, isIterable, EXECUTOR, waitFor, varifyPath, formatException
from nope.logger import defineNopeLogger
from nope.merging import DictBasedMergeData
from nope.modules import NopeGenericModule
from nope.observable import NopeObservable


class NopeInstanceManager:

    def __init__(self, options, _defaultSelector, _id=None,
                 _connectivityManager=None, _rpcManager=None, _core=None):

        self.options = options
        self._defaultSelector = _defaultSelector
        self._id = _id
        self._connectivityManager = _connectivityManager
        self._rpcManager = _rpcManager
        self._core = _core
        self._communicator: Bridge = options.communicator
        self.__disposed = False

        if _id is None:
            self._id = generateId()
        if _connectivityManager is None:
            self._connectivityManager = NopeConnectivityManager(
                options, id=self._id)
        if _rpcManager is None:
            self._rpcManager = NopeRpcManager(
                options,
                self._defaultSelector,
                id=self._id,
                connectivityManager=self._connectivityManager
            )

        self._logger = defineNopeLogger(
            options.logger, 'core.instance-manager')

        # Flag to indicate, that the system is ready.
        self.ready = NopeObservable()
        self.ready.setContent(False)

        self._mappingOfRemoteDispatchersAndGenerators = dict()
        # Overview of the available Constructors in the network.
        self.constructors = DictBasedMergeData(
            self._mappingOfRemoteDispatchersAndGenerators, '+', '+')
        self._mappingOfRemoteDispatchersAndInstances = dict()

        # Overview of the available instances in the network.
        #   - OriginalKey = DispatcherID (string);
        #   - OriginalValue = Available Instance Messages (IAvailableInstancesMsg);
        #   - ExtractedKey = The name of the Instance (string);
        #   - ExtractedValue = instance-description (INopeModuleDescription);
        self.instances = DictBasedMergeData(
            self._mappingOfRemoteDispatchersAndInstances, 'instances/+', 'instances/+/identifier')

        self._internalWrapperGenerators = dict()
        self._registeredConstructors = dict()
        self._instances = dict()
        self._externalInstances = dict()
        self._internalInstances = set()
        self._initializingInstance = dict()
        self._externalInstancesNames = set()

        # Contains the identifiers of the instances, which are hosted in the
        # provided dispatcher.
        self.internalInstances = NopeObservable()
        self.internalInstances.setContent([])

        self.constructorServices = NopeObservable()
        self.constructorServices.setContent([])

        _ctorStart = f'nope{SPLITCHAR}core{SPLITCHAR}constructor{SPLITCHAR}'

        def _extractGenerators(*args):

            constructorServices = set()

            self._mappingOfRemoteDispatchersAndGenerators.clear()
            for dispatcher, services in self._rpcManager.services.originalData.items():
                def _filterMatchingServices(svc):
                    if "id" in svc and svc.id.startswith(_ctorStart):
                        constructorServices.add(svc["id"])
                        return True
                    return False

                generators = list(
                    map(
                        lambda item: item.id[len(_ctorStart):],
                        filter(
                            _filterMatchingServices,
                            services.services
                        )
                    )
                )

                if len(generators):
                    self._mappingOfRemoteDispatchersAndGenerators[dispatcher] = generators

            self.constructorServices.setContent(list(constructorServices))
            self.constructors.update()

        # Subscribe to changes.
        self._rpcManager.services.data.subscribe(_extractGenerators)

        if self._logger:
            self._logger.info('core.instance-manager online')

        self.reset()
        EXECUTOR.callParallel(self._init)

    async def _sendAvailableInstances(self):
        # Update the Instances provided by this module.
        await self._communicator.emit(
            "instancesChanged",
            {
                "dispatcher": self._id,
                # We will send the descriptions.
                # Generate the Module Description for every identifier:
                "instances": list(
                    map(lambda item: self._instances[item]["instance"].toDescription(), self._internalInstances))
            }
        )

        # Update the Instances
        self.internalInstances.setContent(list(self._internalInstances))

    async def _init(self):

        await self._communicator.connected.waitFor()
        await self._connectivityManager.ready.waitFor()
        await self._rpcManager.ready.waitFor()

        async def _generateWrapper(dispather, description):
            mod = NopeGenericModule(
                dispather,
                # self._generateEmitter,
                # self._generateObservable
            )
            await mod.fromDescription(description, "overwrite")
            return mod

        self.registerInternalWrapperGenerator(
            "*",
            _generateWrapper
        )

        def _onDispatchersChanged(changes, *args):
            """ Callback which will handle new and offline Dispatchers.
            """

            if len(changes.added):
                # If there are dispatchers online,
                # We will emit our available services.
                EXECUTOR.callParallel(self._sendAvailableInstances)

            if len(changes.removed):
                # Remove the dispatchers.
                for removedId in changes.removed:
                    self.removeDispatcher(removedId)

        # We will use our status-manager to listen to changes.
        self._connectivityManager.dispatchers.onChange.subscribe(
            _onDispatchersChanged)

        # Make shure we are emitting the instances provided.
        await self._communicator.on("bonjour", lambda *args: EXECUTOR.callParallel(self._sendAvailableInstances))

        def _onInstancesChanged(message, *args):
            """ Callback which will be called if the commincator receives a Message
                that some instances has been changed.

            Args:
                message: The Message from the System.
            """
            # Store the instance.
            self._mappingOfRemoteDispatchersAndInstances[message.dispatcher] = message

            # Update the Mapping
            self.instances.update()

            if self._logger:
                self._logger.debug(
                    'Remote Dispatcher "' + str(message.dispatcher) + '" updated its available instances')

        # Listen to the Changes.
        await self._communicator.on("instancesChanged", _onInstancesChanged)

        if self._logger:
            self._logger.debug("core.instance-manager " +
                               str(self._id) + " initialized")

        self.ready.setContent(True)

    def getServiceName(self, name: str, type: str) -> str:
        """ Helper to get the corresponding Service name

        Args:
            name (str): Name of the Service
            _type (str): The desired type of the requested service name. Could be "dispose" or "constructor"

        Returns:
            str: The Adapted Name
        """
        if type == "constructor":
            return f"nope{SPLITCHAR}core{SPLITCHAR}constructor{SPLITCHAR}{name}"
        elif type == "dispose":
            return f"nope{SPLITCHAR}core{SPLITCHAR}destructor{SPLITCHAR}{name}"
        else:
            raise Exception("The given type is not correct.")

    def _getInstanceInfo(self, identifier: str):
        """ Function, that will extract the information of the instance and the providing dispatcher.

        Args:
            identifier (str): The identifier of instance
        """
        # First check if the instance exists.
        if not self.instanceExists(identifier, False):
            return None

        ret = ensureDottedAccess({})

        # First we check if we are taking care of an internal instance, if so
        # we will use this instance to enrich the description, otherwise, we
        # will look in the external instances.
        if identifier in self._instances:
            ret.description = self._instances[identifier].instance.toDescription(
            )
        else:
            for item in self._mappingOfRemoteDispatchersAndInstances.values():
                instances = item.instances

                for instance in instances:
                    if instance.identifier == identifier:
                        ret.description = instance
                        break

        ret.dispatcher = self.getManagerOfInstance(identifier)

        return ret

    def removeDispatcher(self, dispatcher: str):
        """  Helper to remove a dispatcher.

        Args:
            dispatcher (str): The Id of the Dispatcher
        """
        if self._mappingOfRemoteDispatchersAndInstances.pop(dispatcher, False):
            self.instances.update()

    async def registerConstructor(self, identifier: str, cb):
        """ Registers a Constructor, that enables other NopeInstanceManagers to create an instance of the given type. Therefore a callback "cb" is registered with the given "typeIdentifier"

        Args:
            identifier (str): The identifier for the Constructor (Like a service)
            cb (function): The callback used, to create an instance. The Callback receives the following parameters (NopeCore, identifier:str)
        """

        if self._logger:
            self._logger.debug(
                'Adding instance generator for "' + (identifier +
                                                     '" to external Generators. Other Elements can now create instances of self type.'
                                                     ))

        async def createInstance(data):

            # Check if an instance exists or not.
            # if not => create an instance an store it.

            if data.identifier not in self._instances:
                hashableData = [data.identifier, data.params, data.type]
                try:
                    hashed = hash(hashableData)
                except BaseException as E:
                    hashed = json.dumps(hashableData)

                # It might happen, that an instance is requested multiple times.
                # therefore we have to make shure, we wont create them multiple times:
                # We will test it by using the "_internalInstances" set

                if data.identifier not in self._initializingInstance:

                    try:

                        # Mark the Instance as available.
                        self._initializingInstance[data.identifier] = hashed

                        # Create the Instance
                        _instance = await cb(self._core, data.identifier)
                        _instance.identifier = data.identifier

                        # Make shure the Data is expressed as Array.
                        if not isIterable(data.params):
                            data.params = [data.params]

                        # Initialize the instance with the parameters.
                        await _instance.init(*data.params)

                        async def disposeInstance(_data):
                            """ A Function is registered, taking care of removing
                                an instances, if it isnt needed any more.

                            Args:
                                _data (msg): The message containing the dispatcher id.
                            """

                            _data = ensureDottedAccess(_data)

                            if self._instances.get(data.identifier).usedBy:
                                try:

                                    if _data.dispatcherId in self._instances.get(
                                            data.identifier).usedBy:
                                        # Pop the dispatcher if it is present:
                                        idx = self._instances.get(
                                            data.identifier).usedBy.index(
                                            _data.dispatcherId)
                                        self._instances.get(
                                            data.identifier).usedBy.pop(idx)

                                    if len(self._instances.get(
                                            data.identifier).usedBy) == 0:
                                        # Unmark as internal instance
                                        self._internalInstances.remove(
                                            data.identifier)
                                        # Remove the Instance.
                                        await _instance.dispose()
                                        # Removes the instances
                                        self._instances.pop(data.identifier)
                                        # Remove the Function itself
                                        await self._rpcManager.unregisterService(self.getServiceName(data.identifier, 'dispose'))
                                        # Emit the instances again
                                        await self._sendAvailableInstances()

                                except ValueError:
                                    pass

                        # A Function is registered, taking care of removing
                        # an instances, if it isnt needed any more.
                        await self._rpcManager.registerService(
                            disposeInstance,
                            ensureDottedAccess({
                                'id': self.getServiceName(data.identifier, 'dispose'),
                                'schema': ensureDottedAccess({
                                    'description': f'Service, which will destructor for the instance "{data.identifier}". This function will be called internal only.',
                                    'type': 'function'})
                            })
                        )

                        # Store the Instance.
                        self._instances[data.identifier] = ensureDottedAccess({
                            'instance': _instance,
                            'usedBy': [data.dispatcherId]
                        })

                        self._internalInstances.add(data.identifier)

                        # Update the available instances:
                        await self._sendAvailableInstances()

                        # Make shure, we remove this instance.hash
                        self._initializingInstance.pop(data.identifier)

                    except BaseException as E:
                        # Make shure, we remove this instance.hash
                        self._initializingInstance.pop(data.identifier)

                        raise E

                elif self._initializingInstance.get(data.identifier) != hashed:
                    raise Exception(
                        'Providing different Parameters for the same Identifier'
                    )
                else:
                    # Check if the Instance is ready.
                    firstHint = True

                    def checker():
                        nonlocal firstHint
                        if firstHint:
                            self._logger.warn(
                                f'Parallel request for the same Instance "{data.identifier}" => Waiting until the Instance has been initialized')
                            firstHint = False
                        return data.identifier in self._instances

                    await waitFor(
                        checker,
                        ensureDottedAccess({
                            'testFirst': True,
                            'delay': 100
                        })
                    )
            else:
                # If an Element exists => Add the Element.
                self._instances.get(data.identifier).usedBy.append(
                    data.dispatcherId)

            # Define the Response.
            response = ensureDottedAccess({
                'description': self._instances.get(data.identifier).instance.toDescription(),
                'type': data.type
            })

            # Send the Response
            return response

        _cb = await self._rpcManager.registerService(
            createInstance,
            ensureDottedAccess({
                # We will add the Name to our service.
                'id': self.getServiceName(identifier, 'constructor'),
                # We dont want to have a Prefix for construcors
                'addNopeServiceIdPrefix': False,
                'schema': ensureDottedAccess({
                    'description': f'Service, which will create an construtor for the type "{identifier}".',
                    'type': 'function'
                })
            })
        )

        # Store a generator
        self._registeredConstructors[identifier] = _cb

    async def unregisterConstructor(self, identifier: str):
        """ Unregisters a present Constructor. After this, created instances are still valid, the user isnt able to create new ones.

        Args:
            identifier (str): The identifier for the Constructor (Like a service)
        """
        if identifier in self._registeredConstructors:
            if self._logger:
                self._logger.debug('Removing instance generator for "' + identifier +
                                   '" from external Generators. Other Elements cant create instances of self type anymore.')

            # We will just unregister the service from our
            # system. Therefore we just use the rpcManager

            await self._rpcManager.unregisterService(self._registeredConstructors.get(identifier))
            self._registeredConstructors.pop(identifier)

    def registerInternalWrapperGenerator(self, identifier: str, cb):
        """ Defaultly a generic wrapper will be returned, when an instance is created. you
            can specifiy specific wrapper type for different "typeIdentifier" with this method.

        Args:
            identifier (str): The identifier for the Constructor (Like a service)
            cb (function): The Callback which creates the specific wrapper.
        """
        if self._logger:
            self._logger.debug('Adding instance generator for "' + identifier +
                               '" as internal Generator. This Generator wont be used externally.')

        self._internalWrapperGenerators[identifier] = cb

    def unregisterInternalWrapperGenerator(self, identifier: str):
        """ Removes a specific generator for for a wrapper.

        Args:
            identifier (str): The identifier for the Constructor (Like a service)
        """
        if self._logger:
            self._logger.debug('Rmoving instance generator for "' + identifier +
                               '" from internal Generator. The sytem cant create elements of self type any more.')

        self._internalWrapperGenerators.pop(identifier)

    def instanceExists(self, identifier: str, externalOnly=True) -> bool:
        """  Helper, to test if an instance with the given identifier exists or not.

        Args:
            identifier (str):  identifier of the instance.
            externalOnly (bool, optional): If set to true we will only look for external instances in the external dispatchers. Defaults to True.

        Returns:
            bool: The Testresult
        """
        if identifier not in self.instances.simplified:
            return False

        if externalOnly:
            manager = self.getManagerOfInstance(identifier)
            return manager["id"] != self._id

        return True

    def getManagerOfInstance(self, identifier: str):
        """ Returns the hosting dispatcher for the given instance.

        Args:
            identifier (str): The identifier for instance (its name)

        Returns:
            INopeStatusInfo | False: The Status or false if not present.
        """
        # First we will check if the instance is available internally
        if identifier in self._internalInstances:
            return self._connectivityManager.info

        # If that isnt the case, we will check all dispatchers and search the
        # instance.
        for iter_item in self._mappingOfRemoteDispatchersAndInstances.items():
            dispatcher = iter_item[0]
            msg = iter_item[1]
            for instance in msg.instances:
                if instance.identifier == identifier:
                    return self._connectivityManager.getStatus(dispatcher)

        return None

    def getInstanceDescription(self, instanceIdentifier: str):
        """ Returns the instance Description for a specific instance. It is just a simplified wrapper
            for the "instances"-property.

        Args:
            instanceIdentifier (str): The identifier for instance (its name)

        Returns:
            INopeModuleDescription | False: The Description or False if not found.
        """
        if instanceIdentifier in self._instances:
            return self._instances.get(
                instanceIdentifier).instance.toDescription()

        for data in self._mappingOfRemoteDispatchersAndInstances.values():
            instances = data.get("instances", [])
            for instance in instances:
                if instance["identifier"] == instanceIdentifier:
                    return instance

        return False

    def constructorExists(self, typeIdentifier: str) -> bool:
        """ Helper to test if a constructor linkt to the provided "typeIdentifier" exists or not.

        Args:
            typeIdentifier (str): The identifier for the Constructor (Like a service)

        Returns:
            bool: _description_
        """
        return typeIdentifier in self.constructors.data.getContent()

    async def createInstance(self, description, options=None):
        """ Allows to create an instance. This might be the case on remote dispatchers or
            on the same element. Only a wrapper is returned, which communicates with a
            dispatcher, because we dont know where the element is provided. You can use the
            method "getDispatcherForInstance" to determine the dispatcher running the instance.

            The returned wrapper acts like a normal "internal" class.

        Args:
            description (dict-like): Description of the instance to be created
            options (dict-like, optional): Options used during creating the instance.. Defaults to None.


        Returns:
            NopeGenericModule | Registered Wrapper: An Generic Nope Module as Wrapper or a custom wrapper for the class.
        """

        # Define the Default Description
        # which will lead to an error.

        options = ensureDottedAccess(options)
        description = ensureDottedAccess(description)

        # Assign the provided Description
        _description = ensureDottedAccess({
            'dispatcherId': self._id,
            'identifier': 'error',
            'params': [],
            'type': 'unkown'
        })
        _description.update(description)
        _description.update({'dispatcherId': self._id})

        # Check if the Description is complete
        if (_description.type == 'unkown' or _description.identifier) == 'error':
            raise Exception(
                'Please Provide at least a "type" and "identifier" in the paremeters')

        # Use the varified Name (removes the invalid chars.)
        _description.identifier = varifyPath(
            _description.identifier) if self.options.forceUsingValidVarNames else _description.identifier
        if self._logger:
            self._logger.debug('Requesting an Instance of type: "' + _description.type +
                               '" with the identifier: "' + str(_description.identifier) + '"')

        try:
            _type = _description.type
            if _type not in self._internalWrapperGenerators:
                _type = '*'

            if not self.constructorExists(_description.type):
                # No default type is present for a remote
                # => assing the default type which is "*""
                raise Exception('Generator "' + _description.type +
                                '" isnt present in the network!')
            if _type in self._internalWrapperGenerators:
                if self._logger:
                    self._logger.debug('No instance with the identifiert: "' + str(_description.identifier) +
                                       '" found, but an internal generator is available. Using the internal one for creating the instance and requesting the "real" instance externally')

                # Now test if there is allready an instance with this name and type.
                # If so, we check if we have the correct type etc. Additionally we
                # try to extract its dispatcher-id and will use that as selector
                # to allow the function be called.

                _instanceDetails = self._getInstanceInfo(
                    _description.identifier)

                usedDispatcher = None

                if _instanceDetails is not None and _instanceDetails.description.type != _description.type:
                    raise Exception(
                        "There exists an Instance named: '" + str(_description.identifier) + "' but it uses a different type. Requested type: '" +
                        _description.type + "', given type: '" + str(_instanceDetails.description.type) + "'")

                elif _instanceDetails is not None:
                    usedDispatcher = _instanceDetails.dispatcher.id

                if usedDispatcher and options.assignmentValid:

                    # If we have an dispatcher, which was been used to create the instance,
                    # we have to check, the selected Dispatcher Matches our
                    # criteria.

                    if not await options.assignmentValid(_instanceDetails.description, _instanceDetails.dispatcher):
                        raise Exception('Assignment is invalid.')

                definedInstance = await self._rpcManager.performCall(
                    self.getServiceName(_description.type, 'constructor'),
                    [
                        _description
                    ],
                    options
                )

                if self._logger:
                    self._logger.debug(
                        f'Received a description for the instance "{definedInstance.description.identifier}"')

                # Create the Wrapper for our instance.
                wrapper = await self._internalWrapperGenerators.get(_type)(self._core, definedInstance.description)
                if self._logger:
                    self._logger.debug(
                        f'Created a Wrapper for the instance "{definedInstance.description.identifier}"')

                originalDispose = wrapper.dispose

                async def dispose():
                    await self.deleteInstance(wrapper.identifier)

                    await originalDispose()

                setattr(wrapper, "dispose", dispose)

                self._instances[_description.identifier] = ensureDottedAccess({
                    'instance': wrapper,
                    'usedBy': [
                        _description.dispatcherId
                    ]
                }
                )

                return wrapper

            raise Exception('No internal generator Available!')

        except Exception as e:

            if self._logger:
                self._logger.error(
                    'During creating an Instance, the following error Occurd')
                self._logger.error(formatException(e))

            raise e

    async def generateWrapper(self, description):
        # Define the Default Description
        # which will lead to an error.
        description = ensureDottedAccess(description)

        # Assign the provided Description
        _description = ensureDottedAccess({
            'dispatcherId': self._id,
            'identifier': 'error',
            'params': [],
            'type': 'unkown'
        })
        _description.update(description)
        _description.update({'dispatcherId': self._id})

        # Check if the Description is complete
        if (_description.type == 'unkown' or _description.identifier) == 'error':
            raise Exception(
                'Please Provide at least a "type" and "identifier" in the paremeters')

        # Use the varified Name (removes the invalid chars.)
        _description.identifier = varifyPath(
            _description.identifier) if self.options.forceUsingValidVarNames else _description.identifier
        if self._logger:
            self._logger.debug('Requesting an Instance of type: "' + _description.type +
                               '" with the identifier: "' + str(_description.identifier) + '"')

        try:
            _type = _description.type
            if _type not in self._internalWrapperGenerators:
                _type = '*'

            if not self.constructorExists(_description.type):
                # No default type is present for a remote
                # => assing the default type which is "*""
                raise Exception('Generator "' + _description.type +
                                '" isnt present in the network!')
            if _type in self._internalWrapperGenerators:
                if self._logger:
                    self._logger.debug('No instance with the identifiert: "' + str(_description.identifier) +
                                       '" found, but an internal generator is available. Using the internal one for creating the instance and requesting the "real" instance externally')

                # Now test if there is allready an instance with this name and type.
                # If so, we check if we have the correct type etc. Additionally we
                # try to extract its dispatcher-id and will use that as selector
                # to allow the function be called.

                _instanceDetails = self._getInstanceInfo(
                    _description.identifier)

                if _instanceDetails is not None and _instanceDetails.description.type != _description.type:
                    raise Exception(
                        "There exists an Instance named: '" + str(_description.identifier) + "' but it uses a different type. Requested type: '" +
                        _description.type + "', given type: '" + str(_instanceDetails.description.type) + "'")

                elif _instanceDetails is None:
                    raise Exception(
                        'No instance known with the idenfitier "' + str(_description.identifier) + '" !')

                definedInstance = _instanceDetails.description

                # Create the Wrapper for our instance.
                wrapper = await self._internalWrapperGenerators.get(_type)(self._core, definedInstance.description)
                if self._logger:
                    self._logger.debug(
                        f'Created a Wrapper for the instance "{definedInstance.description.identifier}"')

                originalDispose = wrapper.dispose

                async def dispose():
                    await self.deleteInstance(wrapper.indentifier)

                    await originalDispose()

                setattr(wrapper, "dispose", dispose)

                self._instances[_description.identifier] = ensureDottedAccess({
                    'instance': wrapper,
                    'usedBy': [
                        _description.dispatcherId
                    ]
                }
                )

                return wrapper

            raise Exception('No internal generator Available!')

        except Exception as e:

            if self._logger:
                self._logger.error(
                    'During creating an Instance, the following error Occurd')
                self._logger.error(formatException(e))

            raise e

    async def registerInstance(self, instance):
        """ Option, to statically register an instance, without using an specific generator etc.
            This instance is just present in the network.

        Args:
            instance (INopeInstance): The Instnce to register

        Returns:
            INopeInstance: The instance.
        """
        self._instances[instance.identifier] = ensureDottedAccess({
            'instance': instance,
            'usedBy': [],
            'manual': True
        }
        )

        self._internalInstances.add(instance.identifier)

        await self._sendAvailableInstances()

        return instance

    async def deleteInstance(self, instance, preventSendingUpdate=False) -> bool:
        """ Disposes an instance and removes it. Thereby the Instance wont be available for other
            InstanceManagers in the system.

        Args:
            instance (any): The Instance to consider
            preventSendingUpdate (bool, optional): If set to True the other systems wont be notified. This is for internal purpose only. Defaults to False.

        Returns:
            bool: The success
        """
        # Block to find the instance.
        # Based on the property (string or instance)
        # the corresponding instance object has to be select.

        _instance = None
        _identifier = None

        if isinstance(instance, str):
            _instance = self._instances.get(instance)
            _identifier = instance
        else:
            for data in self._instances.values():
                if instance == data.instance:
                    _instance = data
                    _identifier = data.instance.identifier
                    break
        try:
            params = ensureDottedAccess({
                'dispatcherId': self._id,
                'identifier': _identifier
            })

            # Call the corresponding Dispose Function for the "real" instance
            # All other elements are just accessors.
            await self._rpcManager.performCall(
                self.getServiceName(_identifier, "dispose"),
                [
                    params
                ]
            )
        except BaseException as E:
            # Only if it is an internal
            # Instance, we do not want to
            # throw that error, otherwise
            # we want that error to be
            # present.
            if _instance:
                pass
            else:
                raise E

        # if the instance has been found => delete the instance.
        if _instance:
            _instance.usedBy.pop()
            if len(_instance.usedBy) == 0:

                # Delete the Identifier
                self._instances.pop(_instance.instance.identifier)

                # Check if an update should be emitted or not.
                if not preventSendingUpdate:
                    # Update the Instances provided by this module.
                    await self._sendAvailableInstances()

            return True
        return False

    async def getInstancesOfType(self, typeToGet: str):
        """ Creates Wrappers for the Type of the given element.

        Args:
            typeToGet (str): Type of the instances to get the wrappers for.

        Returns:
            list: List containing all kown Elements of the given type.
        """

        indentifier = map(lambda item: item.identifier, filter(
            lambda item: item.type == typeToGet, self.instances.data.getContent()))

        promises = []

        for identifier in indentifier:
            promises.append(
                self.createInstance(
                    ensureDottedAccess({
                        'identifier': identifier,
                        'type': typeToGet,
                        'params': []
                    })
                )
            )

        # Wait to generate all Instances.
        if promises:
            result = await asyncio.gather(*promises)
        return result

    def reset(self):
        self._mappingOfRemoteDispatchersAndGenerators.clear()
        self._mappingOfRemoteDispatchersAndInstances.clear()
        self.constructors.update()
        self.instances.update()
        self._internalWrapperGenerators = dict()
        self._registeredConstructors = dict()

        # If Instances Exists => Delete them.
        if self._instances:

            promises = []

            # Dispose all Instances.
            for name, instance in self._instances.items():

                def onDone(p):
                    if p.exception() and self._logger:
                        self._logger.error(
                            'Failed Removing Instance "' + name + '"')
                        self._logger.error(formatException(e))

                promise: asyncio.Future = self.deleteInstance(name, True)
                promise.add_done_callback(onDone)

                if self._logger:
                    self._logger.warn('Disposing instance "' + name + '"')

                promises.append(promise)

            EXECUTOR.callParallel(asyncio.gather, *promises)

        self._instances = dict()
        self._externalInstances = dict()
        self._internalInstances = set()
        self._initializingInstance = dict()
        self._externalInstancesNames = set()
        self.internalInstances.setContent([])

        if self._communicator.connected.getContent():
            EXECUTOR.callParallel(self._sendAvailableInstances)

    async def dispose(self):
        self.reset()
        self.instances.dispose()
        self.__disposed = True

    def __del__(self):
        if not self.__disposed:
            EXECUTOR.callParallel(self.dispose)
