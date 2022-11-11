""" An example how to modify the Behavior of multiple elements using a Plugin.

    In This case the Plugin allows the implementation of an ackknowledgement
    message if required.
"""

import asyncio

from nope.eventEmitter import NopeEventEmitter
from nope.helpers import generateId, EXECUTOR, ensureDottedAccess, formatException, isAsyncFunction
from nope.plugins import plugin

_DEFAULT_RESULT = object()


@plugin([
    "nope.dispatcher.rpcManager",
    "nope.dispatcher.connectivityManager"
],
    name="rpcCallbacks")
def extend(rpcMod, conManagerMod):
    "Extends the Bridge and adds the functionality of ack knowlededing messages."

    class NopeRpcManager(rpcMod.NopeRpcManager):
        def __init__(self, *args, **kwargs):
            rpcMod.NopeRpcManager.__init__(self, *args, **kwargs)
            self.defaultKeepAlive = kwargs.get(
                "defaultKeepAlive", 60 * 60 * 1000)

        async def _handleExternalRequest(self, data, func=None):
            try:
                if not callable(func):
                    if data.functionId not in self._registeredServices:
                        return
                    func = self._registeredServices[data.functionId].get(
                        "func", None)

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
                    args = [None] * (len(data.params) + len(data.callbacks))

                    for item in data.params:
                        args[item.idx] = item.data

                    for optionsOfCallback in data.callbacks:

                        async def callback(*args, id=optionsOfCallback.id, opts=optionsOfCallback, **kwargs):
                            nonlocal cbs

                            servicePromise = self.performCall(id, args, opts)

                            def cancelCallback(reason):
                                # The Main Task has been canceled =>
                                # We are allowed to canel the Subtask as well.
                                if servicePromise is not None and getattr(
                                        servicePromise, 'cancelCallback', False):
                                    servicePromise.cancelCallback(reason)

                            idx = len(cbs)
                            cbs.append(cancelCallback)

                            # Await the Result. If an Task is canceled => The
                            # Error is Thrown.
                            result = await servicePromise

                            # Remove the Index
                            cbs.pop(idx)

                            return result

                        args[optionsOfCallback.idx] = callback

                    # Perform the Task it self.
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
                        if resultPromise is not None and getattr(
                                resultPromise, 'cancelCallback', False):
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
                    await self._communicator.emit("rpcResponse", result)

            except Exception as error:

                if self._logger:
                    self._logger.error(
                        f'Dispatcher "{self.id}" failed with request: "{data.taskId}"')
                    self._logger.error(formatException(error))
                else:
                    print(formatException(error))

                self._runningExternalRequestedTasks.pop(data.requestedBy, None)

                result = {
                    'error': {
                        'error': str(error),
                        'msg': str(error)
                    },
                    'taskId': data.taskId,
                    'type': 'response'
                }

                # Use the communicator to publish the result.
                await self._communicator.emit("rpcResponse", result)

        async def _performCall(self, serviceName, params, options=None):
            optionsToUse = ensureDottedAccess({
                "resultSink": self._getServiceName(serviceName, "response"),
                "waitForResult": True,
                "callbackOptions": [],
                "timeToLifeAfterCall": self.defaultKeepAlive,
                "calledOnce": [],
            })
            optionsToUse.update(ensureDottedAccess(options))

            taskId = generateId()

            _registeredCallbacks = []

            # Create a Future of the Loop.
            future = EXECUTOR.generatePromise(taskId=taskId)

            def clear():
                if taskId in self._runningInternalRequestedTasks:

                    if self._logger:
                        self._logger.debug('Clearing Callbacks from ' + taskId)

                    for cb in _registeredCallbacks:
                        EXECUTOR.callParallel(self.unregisterService, cb)

                    task = self._runningInternalRequestedTasks[taskId]

                    if task.timeout is not None:
                        task.timeout.cancel()

                    self._runningInternalRequestedTasks.pop(taskId)

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
                    'target': None,
                    'callbacks': []
                }

                callbackOptions = {
                    item.idx: item for item in optionsToUse.callbackOptions}

                # Iterate over all Parameters and
                # Determin Callbacks. Based on the Parameter-
                # Type assign it either to packet.params (
                # for parsable Parameters) and packet.callbacks
                # (for callback Parameters)
                for idx, contentOfParameter in enumerate(params):
                    if not callable(contentOfParameter):
                        # The parameter isnt callable:
                        packet['params'].append({
                            'idx': idx,
                            'data': contentOfParameter
                        })
                    else:

                        if not self.__warned and not isAsyncFunction(contentOfParameter):
                            if self._logger:
                                self._logger.warn(
                                    "!!! You have provided synchronous functions. They may break NoPE. Use them with care !!!")
                                self._logger.warn(
                                    f'The service of parameter {idx} is synchronous!')
                            else:
                                print("!!! You have provided synchronous functions. They may break NoPE. Use them with care !!!")
                                print(f'The service of parameter {idx} is synchronous!')
                            # We only want to warn the user once.
                            self.__warned = True

                        _functionAsAsync = EXECUTOR.wrapFuncIfRequired(contentOfParameter)

                        _timeToLifeAfterCall = callbackOptions.get(
                            idx, {"timeToLifeAfterCall": optionsToUse.timeToLifeAfterCall})["timeToLifeAfterCall"]
                        _calledOnce = callbackOptions.get(
                            idx, {"calledOnce": idx in optionsToUse.calledOnce})["calledOnce"]

                        # The Parameter is a Callback => store a
                        # Description of the Callback and register
                        # the callback inside of the Dispatcher

                        _id = ""
                        _timeout: asyncio.Task = None

                        def removeCallback():
                            nonlocal _id
                            EXECUTOR.callParallel(self.unregisterService, _id)

                        async def cbWithTimeout(*args, f=_functionAsAsync, t=_timeToLifeAfterCall, **kwargs):
                            nonlocal _timeout

                            if _timeout:
                                _timeout.cancel()

                            if t > 0:
                                _timeout = EXECUTOR.setTimeout(removeCallback, t)

                            return await f(*args,**kwargs)

                        async def cbOnce(*args, f=_functionAsAsync, **kwargs):

                            res = await f(*args, **kwargs)
                            await self.unregisterService(_id)
                            return res

                        if _timeToLifeAfterCall > 0:
                            _timeout = EXECUTOR.setTimeout(
                                removeCallback, _timeToLifeAfterCall)

                        _func = await self.registerService(cbOnce if _calledOnce else cbWithTimeout, {
                            "schema": {},
                            "id": generateId(pre_string="callback")
                        })

                        # Assign the used id.
                        _id = _func.id

                        _registeredCallbacks.append(_func.id)

                        # Register the Callback itself in the params object.
                        packet['callbacks'].append(
                            # Convert the Options to
                            # Camel Case
                            {
                                "id": _id,
                                "idx": idx
                            }
                        )

                if not self.serviceExists(serviceName):
                    error = Exception(
                        f'No Service Provider known for "{serviceName}"')
                    if self._logger:
                        self._logger.error(
                            f'No Service Provider known for "{serviceName}"')
                        self._logger.error(formatException(error))

                    raise error

                if self.options.forceUsingSelectors or self.services.amountOf.get(
                        serviceName, 0) > 1:

                    optionsForSelector = ensureDottedAccess({
                        "rpcManager": self,
                        "serviceName": serviceName
                    })

                    if isinstance(optionsToUse.target, str):
                        tastRequest.target = optionsToUse.target
                    elif callable(optionsToUse.selector):
                        tastRequest.target = await options.selector(optionsForSelector)
                    elif isinstance(optionsToUse.selector, str):
                        tastRequest.target = await self._defaultSelector(optionsForSelector)

                else:
                    tastRequest.target = list(
                        self.services.keyMappingreverse[serviceName])[0]

                packet["target"] = tastRequest.target

                await self._communicator.emit("rpcRequest", packet)

                if self._logger:
                    self._logger.debug(
                        f'Dispatcher "{self._id}" putting task "{taskId}" on: "{self._getServiceName(serviceName, "request")}"')

                if optionsToUse.get("timeout", 0) > 0:
                    async def onTimeout():
                        await self.cancelTask(
                            taskId,
                            TimeoutError(
                                f"TIMEOUT. The Service allowed execution time of {optionsToUse.timeout} [ms] has been excided")
                        )

                    # Create our timeout and store it.
                    tastRequest.timeout = EXECUTOR.setTimeout(
                        onTimeout, optionsToUse.timeout)

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
                EXECUTOR.callParallel(self.cancelTask, taskId, reason)

            future.cancelCallback = _cancelTask

            if not optionsToUse.waitForResult:
                EXECUTOR.callParallel(future)
                return future

            return await future

    class NopeConnectivityManager(conManagerMod.NopeConnectivityManager):
        def _info(self):
            ret = conManagerMod.NopeConnectivityManager._info(self)
            ret.plugins.append("rpcCallbacks")
            return ret

    return NopeRpcManager, NopeConnectivityManager
