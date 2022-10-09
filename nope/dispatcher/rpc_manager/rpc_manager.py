#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import asyncio

from ..connectivity_manager import NopeConnectivityManager
from ...communication import Bridge
from ...event_emitter import NopeEventEmitter
from ...helpers import generateId, ensureDottedAccess, isAsyncFunction, \
    formatException, DottedDict, SPLITCHAR, isIterable, getOrCreateEventloop, isList, EXECUTOR
from ...logger import defineNopeLogger
from ...merging import DictBasedMergeData
from ...observable import NopeObservable

_DEFAULT_RESULT = object()


class WrappedFunction:

    def __init__(self, func, _id, unregister):
        self._func = func
        self._unregister = unregister
        self.id = _id
        self.isAsync = isAsyncFunction(func)

    def __call__(self, *args, **kwarg):
        return EXECUTOR.callParallel(self._func, *args, **kwarg)


class NopeRpcManager:

    def __init__(self, options, defaultSelector, _id=None, _connectivityManager=None):

        options = ensureDottedAccess(options)

        self.options = options
        self._defaultSelector = defaultSelector
        self._id = _id
        self._communicator: Bridge = options.communicator
        self._connectivityManager: NopeConnectivityManager = _connectivityManager

        self._runningInternalRequestedTasks = dict()
        self._registeredServices = dict()

        if self._id is None:
            self._id = generateId()

        if self._connectivityManager is None:
            self._connectivityManager = NopeConnectivityManager(options, self.id)

        self._logger = defineNopeLogger(options.logger, 'core.rpc-manager')
        self.ready = NopeObservable()
        self.ready.setContent(False)

        self.__warned = False

        self._mappingOfDispatchersAndServices = dict()
        self.services = DictBasedMergeData(self._mappingOfDispatchersAndServices, 'services/+', 'services/+/id')
        self.onCancelTask = NopeEventEmitter()

        if self._logger:
            self._logger.info(f'manager created id={self.id}')

        self._runningExternalRequestedTasks = dict()

        self.reset()
        EXECUTOR.callParallel(self._init)

    @property
    def id(self):
        return self._id

    def _generatePromise(self, taskId: str):
        """Function to create a Nope Promise (This is cancelable).


        Returns:
            Observable: A new Nope Promise.
        """

        future = EXECUTOR.loop.create_future()
        setattr(future, 'taskId', taskId)
        future.taskId = taskId

        def _cancel():
            pass

        setattr(future, 'cancelCallback', _cancel)

        return future

    def updateDispatcher(self, msg):
        self._mappingOfDispatchersAndServices[msg.dispatcher] = msg
        self.services.update()

    async def _handleExternalRequest(self, data, func: WrappedFunction=None):
        try:
            if not callable(func):
                if data.functionId not in self._registeredServices:
                    return
                func = self._registeredServices[data.functionId].get("func", None)

            if self._logger:
                self._logger.debug(
                    f'Dispatcher "{self.id}" received request: "{data.functionId}" -> task: "{data.taskId}"')

            if callable(func):
                # Now we check, if we have to perform test, whether
                # we are allowed to execute the task:
                if data.get("target", self.id) != self.id:
                    return
                
                # Define a list containing callbacks:
                cbs = []

                observer = None

                def on_cancel(reason, *args):
                    nonlocal observer
                    if reason.taskId == data.taskId:

                        for cb in cbs:
                            cb(reason)

                        observer.unsubscribe()
                        observer = None

                observer = self.onCancelTask.subscribe(on_cancel)

                # extract the arguments etc.
                # create an empty list and fill it afterwards
                args = [None] * len(data.params)
                for item in data.params:
                    args[item.idx] = item.data

                _result = _DEFAULT_RESULT

                if not func.isAsync and not self.__warned and self._logger:
                    self._logger.warn(
                        "!!! You have provided synchronous functions. They may break NoPE. Use them with care !!!")
                    self._logger.warn(
                        "Offloading function to a separate thread.")
                    # We only want to warn the user once.
                    self.__warned = True

                resultPromise = func(*args)

                try:
                    if resultPromise is not None and getattr(resultPromise, 'cancelCallback', False):
                        def _cancel_main(reason):
                            resultPromise.cancelCallback(reason)

                        cbs.append(_cancel_main)

                except Exception as error:
                    # The Cancel Function isn't available in
                    # the provided promise.
                    pass

                self._runningExternalRequestedTasks[data.taskId] = data.requestedBy

                # Wait for the Result to finish.
                _result = await resultPromise

                
                # Define the Result message
                result = {
                    'result': _result if _result is not _DEFAULT_RESULT else None,
                    'taskId': data.taskId,
                    'type': 'response'
                }

                if self._logger:
                    self._logger.debug(
                        'Internally executed requested Function for Task: ' + str(data['taskId']) + " - Function \"" +
                        data['functionId'] + '\". Sending result on ' + data['resultSink'])

                # Use the communicator to publish the result.
                await self._communicator.emit("rpc_response", result)

        except Exception as error:

            if self._logger:
                self._logger.error(f'Dispatcher "{self.id}" failed with request: "{data.taskId}"')
                self._logger.error(formatException(error))            
            else:
                print(formatException(error))

            self._runningExternalRequestedTasks.pop(data.requestedBy,None)

            result = {
                'error': {
                    'error': str(error),
                    'msg': str(error)
                },
                'taskId': data.taskId,
                'type': 'response'
            }

            # Use the communicator to publish the result.
            await self._communicator.emit("rpc_response", result)

    async def _handle_external_response(self, data):
        try:
            # Extract the Task
            task: DottedDict = self._runningInternalRequestedTasks.get(data.taskId, None)

            if task:

                # Based on the Result of the Remote => proceed.
                # Either throw an error or forward the result
                self._runningInternalRequestedTasks.pop(data.taskId)

                if data.error:
                    if self._logger:
                        self._logger.error(
                            "Failed with task " + data['taskId'])
                        self._logger.error("Reason: " + data['error']['msg'])
                        self._logger.exception(data['error'])

                    # Reject the Error:
                    task.future.set_exception(Exception(data['error']))

                    if "timeout" in task and task.timeout is not None:
                        # Assume, that the timeout has been
                        # defined with setTimeout
                        task.timeout.cancel()

                    return True

                else:
                    if self._logger:
                        self._logger.debug('Got sucessfull result for Task: "' + str(
                            data['taskId']) + '". Forwarding Result to Future.')

                    task.future.set_result(data.result)

                    if self._logger:
                        self._logger.debug("Forwarded result to future")

                    if "timeout" in task and task.timeout is not None:
                        task.timeout.cancel()

                    return True

        except Exception as error:
            if self._logger:
                self._logger.error("Error during handling an external response")
                self._logger.error(formatException(error))            
            else:
                print(formatException(error))

        return False

    def _sendAvailableServices(self):
        """ Function used to update the Available Services.
        """

        message = ensureDottedAccess({
            "dispatcher": self.id,
            "services": list(map(lambda item: item.options, self._registeredServices.values()))
        })

        if self._logger:
            self._logger.debug("sending available services")

        EXECUTOR.callParallel(self._communicator.emit,"services_changed", message)

    async def _init(self):
        self.ready.setContent(False)

        await self._communicator.connected.waitFor()
        await self._connectivityManager.ready.waitFor()

        def onServicesChanged(msg):
            try:
                self.updateDispatcher(msg)
            except Exception as error:
                if self._logger:
                    self._logger.error("Failed to add the new services")
                    self._logger.error(formatException(error))
                else:
                    print(formatException(error))

        await self._communicator.on("services_changed", onServicesChanged)
        await self._communicator.on("rpc_request", lambda data: EXECUTOR.callParallel(self._handleExternalRequest,data))
        await self._communicator.on("rpc_response", lambda data: EXECUTOR.callParallel(self._handle_external_response,data))

        def on_cancelation(msg):
            if msg.dispatcher == self._id:
                self.onCancelTask.emit(msg)

        await self._communicator.on("task_cancelation", on_cancelation)

        def on_unregister(msg):
            if msg.identifier in self._registeredServices:
                self.unregisterService(msg.identifier)

        await self._communicator.on("rpc_unregister", on_unregister)

        def onDispatchersChanged(changes, *args):
            if len(changes.added):
                # If there are dispatchers online,
                # We will emit our available services.
                self._sendAvailableServices()
            if len(changes.removed):
                for rm in changes.removed:
                    self.removeDispatcher(rm)

        self._connectivityManager.dispatchers.onChange.subscribe(onDispatchersChanged)

        if self._logger:
            self._logger.info(f"core.rpc-manager {self._id} initialized!")

        self.ready.setContent(True)

    def removeDispatcher(self, dispatcherId: str):
        self._mappingOfDispatchersAndServices.pop(dispatcherId)
        self.services.update()

        # Now we need to cancel every Task of the dispatcher,
        # which isnt present any more.
        self.cancelRunningTasksOfDispatcher(dispatcherId, Exception(
            "Dispatcher has been removed! Tasks cannot be executed any more."))
        # Stop executing the requested Tasks.
        self.cancelRequestedTasksOfDispatcher(dispatcherId, Exception(
            "Dispatcher has been removed! Tasks are not required any more."))

    async def cancelTask(self, taskId: str, reason, quiet=False):
        if taskId in self._runningInternalRequestedTasks:
            task = self._runningInternalRequestedTasks[taskId]

            # Delete the task
            self._runningInternalRequestedTasks.pop(taskId)

            # Propagate the Cancellation (internally):
            task.future.set_exception(reason)

            # Propagate the Cancellation externally.
            # Therefore use the desired Mode.
            await self._communicator.emit("task_cancelation", ensureDottedAccess({
                "dispatcher": self._id,
                "reason": str(reason),
                "taskId": taskId,
                "quiet": quiet
            }))

            return True
        # Task hasnt been found => Cancel the Task.
        return False

    async def _cancelHelper(self, tasksToCancel: set, reason):
        """ Helper Function, used to close all tasks with a specific service.
        """
        if len(tasksToCancel) > 0:
            for taskId in tasksToCancel:
                await self.cancelTask(taskId, reason)

    async def cancelRunningTasksOfService(self, serviceName: str, reason):
        """ Helper Function, used to close all tasks with a specific service.
        """
        # Set containing all Tasks, that has to be canceled
        toCancel = set()

        # Filter all Tasks that should be canceled.
        for taskId, task in self._runningInternalRequestedTasks.items():
            if task.serviceName == serviceName:
                toCancel.add(taskId)

        return await self._cancelHelper(toCancel, reason)

    async def cancelRequestedTasksOfDispatcher(self, dispatcher: str, reason):
        """ Helper to cancel all Tasks which have been requested by a Dispatcher.
        """
        # Set containing all Tasks, that has to be canceled
        toCancel = set()

        for taskId, requestedBy in self._runningExternalRequestedTasks.items():
            if requestedBy == dispatcher:
                toCancel.add(taskId)

        return await self._cancelHelper(toCancel, reason)


    async def cancelRunningTasksOfDispatcher(self, dispatcher: str, reason):
        """ Cancels all Tasks of the given Dispatcher
        """
        toCancel = set()
        for taskId, task in self._runningExternalRequestedTasks.items():
            if task.target == dispatcher:
                toCancel.add(taskId)

        return await self._cancelHelper(toCancel, reason)

    def serviceExists(self, serviceName: str):
        """ Function to test if a specific Service exists.
        """
        return serviceName in self.services.amountOf and self.services.amountOf[serviceName] > 0

    def _getServiceName(self, _id: str, _type: str):
        if _type in ("request", "response"):
            return _id if _id.startswith(f"{_type}/") else f"{_type}/{_id}"
        raise Exception("For the parameter 'type' the values: 'request' and 'response' are allowed!")

    def unregisterService(self, func):
        idOfFunc: str = ""
        if type(func) is str:
            if self.options.forceUsingValidVarNames:
                idOfFunc = varifyPath(func)
            else:
                idOfFunc = func
        else:
            idOfFunc = func.id

        self._sendAvailableServices()

        if self._logger:
            self._logger.debug(f'Dispatcher "{self._id}" unregistered: "{idOfFunc}"')
        return self._registeredServices.pop(id)

    def _adaptServiceId(self, serviceName: str):
        if serviceName.startswith(f'nope{SPLITCHAR}service{SPLITCHAR}'):
            return serviceName
        return f'nope{SPLITCHAR}service{SPLITCHAR}{serviceName}'

    def registerService(self, func, options):
        options = ensureDottedAccess(options)

        # Define / Use the ID of the Function.
        idOfFunc: str = options.id

        if idOfFunc is None:
            idOfFunc = generateId()

        if self.options.addNopeServiceIdPrefix:
            idOfFunc = self._adaptServiceId(idOfFunc)
        if self.options.forceUsingValidVarNames:
            idOfFunc = varifyPath(idOfFunc)

        options.id = idOfFunc

        if not self.__warned and not isAsyncFunction(func):
            self._logger.warn(
                "!!! You have provided synchronous functions. They may break NoPE. Use them with care !!!")
            self._logger.warn(
                f'The service "{idOfFunc}" is synchronous!')
            # We only want to warn the user once.
            self.__warned = True

        # Unregister the Function:
        def unregister():
            self.unregisterService(idOfFunc)

        # Create a Wrapper
        wrapped = WrappedFunction(func, idOfFunc, unregister)

        self._registeredServices[idOfFunc] = ensureDottedAccess({
            "options": options,
            "func": wrapped
        })

        self._sendAvailableServices()

        if self._logger:
            self._logger.debug(f'Dispatcher "{self._id}" registered: "{idOfFunc}"')

        return wrapped

    async def _performCall(self, serviceName, params, options=None):
        optionsToUse = ensureDottedAccess({
            "resultSink": self._getServiceName(serviceName, "response"),
            "waitFor_result": True
        })
        optionsToUse.update(ensureDottedAccess(options))

        taskId = generateId()

        # Create a Future of the Loop.
        future = self._generatePromise(taskId)

        def clear():
            if taskId in self._runningInternalRequestedTasks:
                task = self._runningInternalRequestedTasks[taskId]

                if task.timeout is not None:
                    task.timeout.cancel()

                self._runningInternalRequestedTasks.pop(taskId)

            if self._logger:
                self._logger.debug('Clearing Callbacks from ' + taskId)

        try:
            tastRequest = ensureDottedAccess({
                "future": future,
                "clear": clear,
                'serviceName': serviceName,
                'timeout': None,
            })

            # Store the Future as Task.
            self._runningInternalRequestedTasks[taskId] = tastRequest

            # Define the packet to send:
            packet = {
                'functionId': serviceName,
                'params': [],
                'taskId': taskId,
                'resultSink': optionsToUse['resultSink'],
                'requestedBy': self._id,
                'target': None
            }

            # Iterate over all Parameters and
            # Determin Callbacks. Based on the Parameter-
            # Type assign it either to packet.params (
            # for parsable Parameters) and packet.callbacks
            # (for callback Parameters)
            for idx, param in enumerate(params):
                packet['params'].append({
                    'idx': idx,
                    'data': param
                })

            if not self.serviceExists(serviceName):
                error = Exception(f'No Service Provider known for "{serviceName}"')
                if self._logger:
                    self._logger.error(f'No Service Provider known for "{serviceName}"')
                    self._logger.error(formatException(error))

                raise error

            if self.options.forceUsingSelectors or self.services.amountOf.get(serviceName, 0) > 1:

                optionsForSelector = ensureDottedAccess({
                    "rpcManager": self,
                    "serviceName": serviceName
                })

                if type(optionsToUse.target) is str:
                    tastRequest.target = optionsToUse.target
                elif callable(optionsToUse.selector):
                    tastRequest.target = await options.selector(optionsForSelector)
                elif type(optionsToUse.selector) is str:
                    tastRequest.target = await self._defaultSelector(optionsForSelector)
                
            else:
                tastRequest.target = list(self.services.keyMappingreverse[serviceName])[0]

            packet["target"] = tastRequest.target

            await self._communicator.emit("rpc_request", packet)

            if self._logger:
                self._logger.debug(
                    f'Dispatcher "${self._id}" putting task "${taskId}" on: "${self._getServiceName(tastRequest.functionId, "request")}"')

            if optionsToUse.get("timeout", 0) > 0:
                async def onTimeout():
                    await self.cancelTask(
                        taskId,
                        TimeoutError(
                            f"TIMEOUT. The Service allowed execution time of {optionsToUse.timeout} [ms] has been excided")
                    )

                # Create our timeout and store it.
                tastRequest.timeout = EXECUTOR.setTimeout(onTimeout, optionsToUse.timeout)

        except Exception as err:
            if self._logger:
                self._logger.error('Something went wrong on calling')
                self._logger.exception(formatException(err))
            else:
                print(formatException(err))

            # Call the Clear Function
            clear()

            # Throw an error.
            future.set_exception(err)

        # Define a Function, which could be used for cancelation.
        def _cancelTask(reason):
            EXECUTOR.callParallel(self.cancelTask,taskId,reason)

        future.cancelCallback = _cancelTask

        if not optionsToUse.waitFor_result:
            EXECUTOR.loop.create_task(future)
            return future

        return await future

    async def performCall(self, serviceName, params, options=None):
        if isList(serviceName):
            if isList(options) and len(serviceName) != len(options):
                raise Exception("The length of the provided services and options does not match")

            optionsToUse = [options] * len(serviceName) if not isIterable(options) else options

            futures = []

            for idx, srv in enumerate(serviceName):
                futures.append(
                    self._performCall(
                        srv,
                        params,
                        optionsToUse[idx]
                    )
                )

            return await asyncio.gather(*futures)

        else:
            if isList(options):
                raise Exception("The length of the provided services and options does not match")

            return await self._performCall(serviceName, params, options)

    def clearTasks(self):
        self._runningInternalRequestedTasks.clear()

    def unregisterAll(self):
        toUnregister = list(self._registeredServices.keys())
        for srv in toUnregister:
            self.unregisterService(srv)
        self._registeredServices.clear()

    def reset(self):
        self.clearTasks()
        self.unregisterAll()
        self._sendAvailableServices()
