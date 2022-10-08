#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

import asyncio

from ..connectivity_manager import NopeConnectivityManager
from ...communication import Bridge
from ...event_emitter import NopeEventEmitter
from ...helpers import generate_id, ensure_dotted_dict, is_async_function, \
    format_exception, DottedDict, SPLITCHAR, is_iterable, get_or_create_eventloop, is_list, EXECUTOR
from ...logger import define_nope_logger
from ...merging import DictBasedMergeData
from ...observable import NopeObservable

_DEFAULT_RESULT = object()


class WrappedFunction:

    def __init__(self, func, _id, unregister):
        self._func = func
        self._unregister = unregister
        self.id = _id
        self.is_async = is_async_function(func)

    def __call__(self, *args, **kwarg):
        return EXECUTOR.call_parallel(self._func, *args, **kwarg)


class NopeRpcManager:

    def __init__(self, options, default_selector, _id=None, _connectivity_manager=None, loop=None):

        options = ensure_dotted_dict(options)

        self.options = options
        self._default_selector = default_selector
        self._id = _id
        self._communicator: Bridge = options.communicator
        self._connectivity_manager: NopeConnectivityManager = _connectivity_manager
        self._loop = loop if loop is not None else get_or_create_eventloop()

        self._running_internal_requested_tasks = dict()
        self._registered_services = dict()

        if self._id is None:
            self._id = generate_id()

        if self._connectivity_manager is None:
            self._connectivity_manager = NopeConnectivityManager(options, self.id)

        self._logger = define_nope_logger(options.logger, 'core.rpc-manager')
        self.ready = NopeObservable()
        self.ready.set_content(False)

        self.__warned = False

        self._mapping_of_dispatchers_and_services = dict()
        self.services = DictBasedMergeData(self._mapping_of_dispatchers_and_services, 'services/+', 'services/+/id')
        self.on_cancel_task = NopeEventEmitter()

        if self._logger:
            self._logger.info(f'manager created id={self.id}')

        self._running_external_requested_tasks = dict()

        self.reset()
        asyncio.ensure_future(self._init())

    @property
    def id(self):
        return self._id

    def _generate_promise(self, task_id: str):
        """Function to create a Nope Promise (This is cancelable).


        Returns:
            Observable: A new Nope Promise.
        """

        future = self._loop.create_future()
        setattr(future, 'task_id', task_id)
        future.task_id = task_id

        def _cancel():
            pass

        setattr(future, 'cancel_callback', _cancel)

        return future

    def update_dispatcher(self, msg):
        self._mapping_of_dispatchers_and_services[msg.dispatcher] = msg
        self.services.update()

    async def _handle_external_request(self, data, func: WrappedFunction=None):
        try:
            if not callable(func):
                func = self._registered_services[data.function_id].get("func", None)

            if self._logger:
                self._logger.debug(
                    f'Dispatcher "{self.id}" received request: "{data.function_id}" -> task: "{data.task_id}"')

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
                    if reason.task_id == data.task_id:

                        for cb in cbs:
                            cb(reason)

                        observer.unsubscribe()
                        observer = None

                observer = self.on_cancel_task.subscribe(on_cancel)

                # extract the arguments etc.
                # create an empty list and fill it afterwards
                args = [None] * len(data.params)
                for item in data.params:
                    args[item.idx] = item.data

                _result = _DEFAULT_RESULT

                if not func.is_async and not self.__warned and self._logger:
                    self._logger.warn(
                        "!!! You have provided synchronous functions. They may break NoPE. Use them with care !!!")
                    self._logger.warn(
                        "Offloading function to a separate thread.")
                    # We only want to warn the user once.
                    self.__warned = True

                result_promise = func(*args)

                try:
                    if result_promise is not None and getattr(result_promise, 'cancel_callback', False):
                        def _cancel_main(reason):
                            result_promise.cancel_callback(reason)

                        cbs.append(_cancel_main)

                except Exception as error:
                    # The Cancel Function isn't available in
                    # the provided promise.
                    pass

                self._running_external_requested_tasks[data.task_id] = data.requested_by

                # Wait for the Result to finish.
                _result = await result_promise

                
                # Define the Result message
                result = {
                    'result': _result if _result is not _DEFAULT_RESULT else None,
                    'task_id': data.task_id,
                    'type': 'response'
                }

                if self._logger:
                    self._logger.debug(
                        'Internally executed requested Function for Task: ' + str(data['task_id']) + " - Function \"" +
                        data['function_id'] + '\". Sending result on ' + data['result_sink'])

                # Use the communicator to publish the result.
                await self._communicator.emit("rpc_response", result)

        except Exception as error:

            if self._logger:
                self._logger.error(f'Dispatcher "{self.id}" failed with request: "{data.task_id}"')
                self._logger.error(format_exception(error))

            self._running_external_requested_tasks.pop(data.requested_by,None)

            result = {
                'error': {
                    'error': str(error),
                    'msg': str(error)
                },
                'task_id': data.task_id,
                'type': 'response'
            }

            # Use the communicator to publish the result.
            await self._communicator.emit("rpc_response", result)

    async def _handle_external_response(self, data):
        try:
            # Extract the Task
            task: DottedDict = self._running_internal_requested_tasks.get(data.task_id, None)

            if task:

                # Based on the Result of the Remote => proceed.
                # Either throw an error or forward the result
                self._running_internal_requested_tasks.pop(data.task_id)

                if data.error:
                    if self._logger:
                        self._logger.error(
                            "Failed with task " + data['task_id'])
                        self._logger.error("Reason: " + data['error']['msg'])
                        self._logger.exception(data['error'])

                    # Reject the Error:
                    task.future.set_exception(Exception(data['error']))

                    if "timeout" in task and task.timeout is not None:
                        # Assume, that the timeout has been
                        # defined with set_timeout
                        task.timeout.cancel()

                    return True

                else:
                    if self._logger:
                        self._logger.debug('Got sucessfull result for Task: "' + str(
                            data['task_id']) + '". Forwarding Result to Future.')

                    task.future.set_result(data.result)

                    if self._logger:
                        self._logger.debug("Forwarded result to future")

                    if "timeout" in task and task.timeout is not None:
                        task.timeout.cancel()

                    return True

        except Exception as error:
            if self._logger:
                self._logger.error("Error during handling an external response")
                self._logger.error(format_exception(error))

        return False

    def _send_available_services(self):
        """ Function used to update the Available Services.
        """

        message = ensure_dotted_dict({
            "dispatcher": self.id,
            "services": list(map(lambda item: item.options, self._registered_services.values()))
        })

        if self._logger:
            self._logger.debug("sending available services")

        asyncio.ensure_future(
            self._communicator.emit("services_changed", message)
        )

    async def _init(self):
        self.ready.set_content(False)

        await self._communicator.connected.wait_for()
        await self._connectivity_manager.ready.wait_for()

        def on_services_changed(msg):
            try:
                self.update_dispatcher(msg)
            except Exception as error:
                if self._logger:
                    self._logger.error("Failed to add the new services")
                    self._logger.error(format_exception(error))

        await self._communicator.on("services_changed", on_services_changed)
        await self._communicator.on("rpc_request", lambda data: asyncio.ensure_future(self._handle_external_request(data)))
        await self._communicator.on("rpc_response", lambda data: asyncio.ensure_future(self._handle_external_response(data)))

        def on_cancelation(msg):
            if msg.dispatcher == self._id:
                self.on_cancel_task.emit(msg)

        await self._communicator.on("task_cancelation", on_cancelation)

        def on_unregister(msg):
            if msg.identifier in self._registered_services:
                self.unregister_service(msg.identifier)

        await self._communicator.on("rpc_unregister", on_unregister)

        def on_dispatchers_changed(changes, *args):
            if len(changes.added):
                # If there are dispatchers online,
                # We will emit our available services.
                self._send_available_services()
            if len(changes.removed):
                for rm in changes.removed:
                    self.remove_dispatcher(rm)

        self._connectivity_manager.dispatchers.on_change.subscribe(on_dispatchers_changed)

        if self._logger:
            self._logger.info(f"core.rpc-manager {self._id} initialized!")

        self.ready.set_content(True)

    def remove_dispatcher(self, dispatcher_id: str):
        self._mapping_of_dispatchers_and_services.pop(dispatcher_id)
        self.services.update()

        # Now we need to cancel every Task of the dispatcher,
        # which isnt present any more.
        self.cancel_running_tasks_of_dispatcher(dispatcher_id, Exception(
            "Dispatcher has been removed! Tasks cannot be executed any more."))
        # Stop executing the requested Tasks.
        self.cancel_requested_tasks_of_dispatcher(dispatcher_id, Exception(
            "Dispatcher has been removed! Tasks are not required any more."))

    async def cancel_task(self, task_id: str, reason, quiet=False):
        if task_id in self._running_internal_requested_tasks:
            task = self._running_internal_requested_tasks[task_id]

            # Delete the task
            self._running_internal_requested_tasks.pop(task_id)

            # Propagate the Cancellation (internally):
            task.future.set_exception(reason)

            # Propagate the Cancellation externally.
            # Therefore use the desired Mode.
            await self._communicator.emit("task_cancelation", ensure_dotted_dict({
                "dispatcher": self._id,
                "reason": reason,
                "task_id": task_id,
                "quiet": quiet
            }))

            return True
        # Task hasnt been found => Cancel the Task.
        return False

    async def cancel_running_tasks_of_service(self, service_name: str, reason):
        """ Helper Function, used to close all tasks with a specific service.
        """

        # List containing all Tasks, that has to be canceled
        tasks_to_cancel = []
        # Filter all Tasks that should be canceled.
        for task_id, task in self._running_internal_requested_tasks.items():
            if task.service_name == service_name:
                tasks_to_cancel.append(task_id)

        if len(tasks_to_cancel) > 0:
            for task_id in tasks_to_cancel:
                await self.cancel_task(task_id, reason)

    async def cancel_requested_tasks_of_dispatcher(self, dispatcher: str, reason):
        """ Helper to cancel all Tasks which have been requested by a Dispatcher.
        """

        # List containing all Tasks, that has to be canceled
        to_cancel = set()

        for task_id, requested_by in self._running_internal_requested_tasks.items():
            if requested_by == dispatcher:
                to_cancel.add(task_id)

        for task_id in to_cancel:
            await self.cancel_task(task_id, reason)

    async def cancel_running_tasks_of_dispatcher(self, dispatcher: str, reason):
        """ Cancels all Tasks of the given Dispatcher
        """
        tasks_to_cancel = []
        for task_id, task in self._running_internal_requested_tasks.items():
            if task.target == dispatcher:
                tasks_to_cancel.append(task_id)

        if len(tasks_to_cancel) > 0:
            for task_id in tasks_to_cancel:
                await self.cancel_task(task_id, reason)

    def service_exists(self, service_name: str):
        """ Function to test if a specific Service exists.
        """
        return service_name in self.services.amount_of and self.services.amount_of[service_name] > 0

    def _get_service_name(self, _id: str, _type: str):
        if _type in ("request", "response"):
            return _id if _id.startswith(f"{_type}/") else f"{_type}/{_id}"
        raise Exception("For the parameter 'type' the values: 'request' and 'response' are allowed!")

    def unregister_service(self, func):
        id_of_func: str = ""
        if type(func) is str:
            if self.options.force_using_valid_var_names:
                id_of_func = varify_path(func)
            else:
                id_of_func = func
        else:
            id_of_func = func.id

        self._send_available_services()

        if self._logger:
            self._logger.debug(f'Dispatcher "{self._id}" unregistered: "{id_of_func}"')
        return self._registered_services.pop(id)

    def adapt_service_id(self, service_name: str):
        if service_name.startswith(f'nope{SPLITCHAR}service{SPLITCHAR}'):
            return service_name
        return f'nope{SPLITCHAR}service{SPLITCHAR}{service_name}'

    def register_service(self, func, options):
        options = ensure_dotted_dict(options)

        # Define / Use the ID of the Function.
        id_of_func: str = options.id

        if id_of_func is None:
            id_of_func = generate_id()

        if self.options.add_nope_service_id_prefix:
            id_of_func = self.adapt_service_id(id_of_func)
        if self.options.force_using_valid_var_names:
            id_of_func = varify_path(id_of_func)

        options.id = id_of_func

        if not self.__warned and not is_async_function(func):
            self._logger.warn(
                "!!! You have provided synchronous functions. They may break NoPE. Use them with care !!!")
            self._logger.warn(
                f'The service "{id_of_func}" is synchronous!')
            # We only want to warn the user once.
            self.__warned = True

        # Unregister the Function:
        def unregister():
            self.unregister_service(id_of_func)

        # Create a Wrapper
        wrapped = WrappedFunction(func, id_of_func, unregister)

        self._registered_services[id_of_func] = ensure_dotted_dict({
            "options": options,
            "func": wrapped
        })

        self._send_available_services()

        if self._logger:
            self._logger.debug(f'Dispatcher "{self._id}" registered: "{id_of_func}"')

        return wrapped

    async def _perform_call(self, service_name, params, options=None):
        options_to_use = ensure_dotted_dict({
            "result_sink": self._get_service_name(service_name, "response"),
            "wait_for_result": True
        })
        options_to_use.update(ensure_dotted_dict(options))

        task_id = generate_id()

        # Create a Future of the Loop.
        future = self._generate_promise(task_id)

        def clear():
            if task_id in self._running_internal_requested_tasks:
                task = self._running_internal_requested_tasks[task_id]

                if task.timeout is not None:
                    task.timeout.cancel()

                self._running_internal_requested_tasks.pop(task_id)

            if self._logger:
                self._logger.debug('Clearing Callbacks from ' + task_id)

        try:
            task_request = ensure_dotted_dict({
                "future": future,
                "clear": clear,
                'service_name': service_name,
                'timeout': None,
            })

            # Store the Future as Task.
            self._running_internal_requested_tasks[task_id] = task_request

            # Define the packet to send:
            packet = {
                'function_id': service_name,
                'params': [],
                'task_id': task_id,
                'result_sink': options_to_use['result_sink'],
                'requested_by': self._id
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

            if not self.service_exists(service_name):
                error = Exception(f'No Service Provider known for "{service_name}"')
                if self._logger:
                    self._logger.error(f'No Service Provider known for "{service_name}"')
                    self._logger.error(format_exception(error))

                raise error

            if self.options.force_using_selectors or self.services.amount_of.get(service_name, 0) > 1:

                opts_for_selector = ensure_dotted_dict({
                    "rpc_manager": self,
                    "service_name": service_name
                })

                if type(options_to_use.target) is str:
                    task_request.target = options_to_use.target
                elif callable(options_to_use.selector):
                    task_request.target = await options.selector(opts_for_selector)
                elif type(options_to_use.selector) is str:
                    task_request.target = await self._default_selector(opts_for_selector)

            await self._communicator.emit("rpc_request", packet)

            if self._logger:
                self._logger.debug(
                    f'Dispatcher "${self._id}" putting task "${task_id}" on: "${self._get_service_name(task_request.function_id, "request")}"')

            if options_to_use.get("timeout", 0) > 0:
                async def on_timeout():
                    await self.cancel_task(
                        task_id,
                        TimeoutError(
                            f"TIMEOUT. The Service allowed execution time of {options_to_use.timeout} [ms] has been excided")
                    )

                # Create our timeout and store it.
                task_request.timeout = EXECUTOR.set_timeout(on_timeout, options_to_use.timeout)

        except Exception as err:
            self._logger.error('Something went wrong on calling')
            self._logger.exception(err)

            # Call the Clear Function
            clear()

            # Throw an error.
            future.set_exception(err)

        # Define a Function, which could be used for cancelation.
        def _cancel_task(reason):
            EXECUTOR.call_parallel(self.cancel_task,task_id,reason)

        future.cancel_callback = _cancel_task

        if not options_to_use.wait_for_result:
            asyncio.ensure_future(future)
            return future

        return await future

    async def perform_call(self, service_name, params, options=None):
        if is_list(service_name):
            if is_list(options) and len(service_name) != len(options):
                raise Exception("The length of the provided services and options does not match")

            options_to_use = [options] * len(service_name) if not is_iterable(options) else options

            futures = []

            for idx, srv in enumerate(service_name):
                futures.append(
                    self._perform_call(
                        srv,
                        params,
                        options_to_use[idx]
                    )
                )

            return await asyncio.gather(*futures)

        else:
            if is_list(options):
                raise Exception("The length of the provided services and options does not match")

            return await self._perform_call(service_name, params, options)

    def clear_tasks(self):
        self._running_internal_requested_tasks.clear()

    def unregister_all(self):
        to_unregister = list(self._registered_services.keys())
        for srv in to_unregister:
            self.unregister_service(srv)
        self._registered_services.clear()

    def reset(self):
        self.clear_tasks()
        self.unregister_all()
        self._send_available_services()
