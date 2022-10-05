import asyncio
import os
import platform
import re
import subprocess
from enum import Enum
from socket import gethostname

import psutil

from ...helpers import get_timestamp, ensure_dotted_dict, generate_id, DottedDict, create_interval_in_event_loop, \
    offload_function_to_event_loop, min_of_array, format_exception
from ...logger import define_nope_logger
from ...merging import DictBasedMergeData
from ...observable import NopeObservable


class ENopeDispatcherStatus(Enum):
    HEALTHY = 0
    SLOW = 1
    WARNING = 2
    DEAD = 3


def _get_processor_name():
    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command = "sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip().decode()
        for line in all_info.split("\n"):
            if "model name" in line:
                return re.sub(".*model name.*:", "", line, 1)
    return ""


PROCESSOR_NAME = _get_processor_name()


class NopeConnectivityManager:

    def __init__(self, options, _id=None):

        options = ensure_dotted_dict(options, False)

        self.options = options
        self._id = _id if _id is not None else generate_id()
        self._delta_time = 0
        self._cancel_check_status_task = None
        self._cancel_send_status_task = None

        self._communicator = options.communicator
        self._connected_since = get_timestamp()
        self._is_master = options.is_master if type(options.is_master) is int else None

        self._logger = define_nope_logger(options.logger, 'core.connectivity-manager')

        self.ready = NopeObservable()
        self.ready.set_content(False)
        self._external_dispatchers = dict()
        self.dispatchers = DictBasedMergeData(self._external_dispatchers, 'id')

        if self._logger:
            self._logger.info('core.connectivity-manager', self.id, 'is ready')

        self.reset()
        asyncio.ensure_future(self.set_timings(options.timeouts))
        asyncio.ensure_future(self.init())

    @property
    def id(self):
        return self._id

    @property
    def info(self):

        # Helper for the Memory.
        virtual_memory = psutil.virtual_memory()

        return ensure_dotted_dict({
            'id': self.id,
            'env': 'python',
            'version': '0.9.6',
            'isMaster': self.is_master,
            'isMasterForced': type(self._is_master) is bool,
            'host': {
                'cores': os.cpu_count(),
                'cpu': {
                    'model': PROCESSOR_NAME,
                    'speed': psutil.cpu_freq().max,
                    'usage': psutil.cpu_percent(0)
                },
                'os': str(platform.system()) + " " + str(platform.release()),
                'ram': {
                    'usedPerc': virtual_memory.percent,
                    'free': round(virtual_memory.free / 1048576),
                    'total': round(virtual_memory.total / 1048576)
                },
                'name': gethostname()
            },
            'pid': os.getpid(),
            'timestamp': self.now,
            'connectedSince': self.connected_since,
            'status': ENopeDispatcherStatus.HEALTHY.value
        })

    @property
    def up_time(self):
        return get_timestamp() - self.connected_since

    @property
    def connected_since(self):
        return self._connected_since + self._delta_time

    @property
    def is_master(self):
        if self._is_master is None:
            try:
                return self.id == self.master.id
            except Exception as e:
                return False
        return self._is_master

    @is_master.setter
    def is_master(self, value):
        self._is_master = value
        asyncio.ensure_future(self._async_send_status())

    def _get_possible_master_candidates(self):
        possible_masters = []
        for info in self.dispatchers.original_data.values():
            # In here we have to use Camel-Case because we are considering
            # Camel-Case in the entire system.
            if info.isMasterForced and not info.isMaster:
                continue
            possible_masters.append(info)
        return possible_masters

    @property
    def master(self):
        # TODO: Check implementation

        def check_if_master(item):
            return item.isMaster and item.isMasterForced

        candidates = self._get_possible_master_candidates()
        masters = list(filter(check_if_master, candidates))
        if len(masters) != 1:
            if len(masters) > 1 and self._logger:
                self._logger.warn(
                    f"Found {len(masters)}. We now will select the one which has been online for the longest time.")
            idx = min_of_array(candidates, 'connectedSince').index
            if idx is not None:
                return candidates[idx]
            raise Exception('No Master has been found !')
        return masters[0]

    @property
    def now(self):
        return get_timestamp() + self._delta_time

    async def init(self):

        self.ready.set_content(False)

        def on_connect(connected, rest):
            if connected:
                self._connected_since = get_timestamp()

        self._communicator.connected.subscribe(on_connect)
        await self._communicator.connected.wait_for()

        def on_status_changed(info):
            self._external_dispatchers[info.id] = ensure_dotted_dict(info)
            if info.id != self.id:
                # TODO: Why is this step required?
                self._external_dispatchers[self.id] = self.info
                self.dispatchers.update()

        await self._communicator.on('StatusChanged', on_status_changed)

        def on_bonjour(opts):
            if self.id != opts.dispatcher_id:
                if self._logger:
                    self._logger.debug('Remote Dispatcher "' + opts.dispatcher_id + '" went online')
                    self._async_send_status()

        await self._communicator.on('Bonjour', on_bonjour)

        def on_aurevoir(msg):
            self._external_dispatchers.pop(msg.dispatcherId)
            self.dispatchers.update()

        await self._communicator.on('Aurevoir', on_aurevoir)

        await self._async_send_status()

        if self._logger:
            self._logger.info('core.connectivity-manager', self.id, 'initialized')

        await self.emit_bonjour()
        await self._async_send_status()
        self.ready.set_content(True)

    def _check_dispachter_health(self):
        """ Checks the health of dispatcher. If some changes like their connection
            are determined, an update is transmitted via the attribute `dispatchers`

        """
        current_time = self.now

        changes = False

        for status in list(self._external_dispatchers.values()):
            # determine the Difference
            diff = current_time - status['timestamp']

            # Based on the Difference Determine the Status
            if diff > self._timeouts['remove']:
                # remove the Dispatcher. But be quite.
                # Perhaps more dispatchers will be removed
                self._remove_dispatcher(status['id'], True)
                changes = True
            elif diff > self._timeouts['dead'] and status['status'] != ENopeDispatcherStatus.DEAD:
                status['status'] = ENopeDispatcherStatus.DEAD
                changes = True
            elif self._timeouts['warn'] < diff <= self._timeouts['dead'] and status[
                'status'] != ENopeDispatcherStatus.WARNING:
                status['status'] = ENopeDispatcherStatus.WARNING
                changes = True
            elif self._timeouts['slow'] < diff <= self._timeouts['warn'] and status[
                'status'] != ENopeDispatcherStatus.SLOW:
                status['status'] = ENopeDispatcherStatus.SLOW
                changes = True
            elif diff <= self._timeouts['slow'] and status['status'] != ENopeDispatcherStatus.HEALTHY:
                status['status'] = ENopeDispatcherStatus.HEALTHY
                changes = True

        if changes:
            # Execute the following function parallel.
            offload_function_to_event_loop(lambda: self.dispatchers.update())

    def _remove_dispatcher(self, dispatcher: str, quite=False):
        """ Removes a dispatcher.
        """
        dispatcher_info = self._external_dispatchers.pop(dispatcher, None)
        if not quite:
            self.dispatchers.update()
        if self._logger and dispatcher_info:
            self._logger.warn(
                f'a dispatcher on {dispatcher_info.host.name} went offline. ID of the Dispatcher: "{dispatcher}"')

    async def _async_send_status(self):
        if self._communicator.connected.get_content():
            try:
                info = self.info
                self._external_dispatchers[self.id] = info
                await self._communicator.emit('StatusChanged', info)
            except Exception as e:
                if self._logger:
                    self._logger.error('Failled to send the status')
                    self._logger.error(e)

                else:
                    print(format_exception(e))

    def sync_time(self, timestamp, delay=0):
        internal_timestamp = get_timestamp()
        self._delta_time = internal_timestamp - (timestamp - delay)

    def get_status(self, _id: str):
        return self._external_dispatchers[_id]

    async def emit_bonjour(self):
        await self._communicator.emit('Bonjour',
                                      DottedDict({'dispatcher_id': self.id}))

    def reset(self):
        self._external_dispatchers.clear()
        self.dispatchers.update(self._external_dispatchers)

    async def set_timings(self, options):

        options = ensure_dotted_dict(options)

        await self.dispose(True)
        self._timeouts = ensure_dotted_dict({
            'send_alive_interval': 500,
            'check_interval': 250,
            'slow': 1000,
            'warn': 2000,
            'dead': 5000,
            'remove': 10000
        })

        if options:
            self._timeouts.update(options)

        # Setup Test Intervals:
        if self._timeouts.check_interval > 0:
            # Define a Checker, which will test the status
            # of the external Dispatchers.
            self._cancel_check_status_task = create_interval_in_event_loop(
                self._check_dispachter_health,
                self._timeouts["check_interval"]
            )

        if self._timeouts["send_alive_interval"] > 0:
            # Define a Timer, which will emit Status updates with
            # the desired delay.
            self._cancel_send_status_task = create_interval_in_event_loop(
                self._async_send_status,
                self._timeouts["send_alive_interval"]
            )

    @property
    def all_hosts(self):
        hosts = set()
        for info in self.dispatchers.original_data.values():
            hosts.add(info.host.name)
        return list(hosts)

    async def dispose(self, quite=False):
        if self._cancel_send_status_task:
            self._cancel_send_status_task()
        if self._cancel_check_status_task:
            self._cancel_check_status_task()
        if not quite:
            await self._communicator.emit('Aurevoir', DottedDict({'dispatcherId': self.id}))
