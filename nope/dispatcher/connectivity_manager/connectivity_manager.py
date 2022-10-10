import asyncio
import os
import platform
import re
import subprocess
from enum import Enum
from socket import gethostname

import psutil

from ...helpers import getTimestamp, ensureDottedAccess, generateId, DottedDict, minOfArray, formatException, \
    EXECUTOR
from ...logger import defineNopeLogger
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


_PROCESSOR_NAME = _get_processor_name()

# We want to load the file containing the current version.
_VERSION = "1.4.1"
try:
    _PATH = os.path.join(os.path.dirname(__file__), "..", "..", "VERSION")
    _VERSION = open(_PATH).read().strip()
except:
    pass


class NopeConnectivityManager:

    def __init__(self, options, _id=None):

        options = ensureDottedAccess(options, False)

        self.options = options
        self._id = _id if _id is not None else generateId()
        self._deltaTime = 0
        self._checkStatusTask = None
        self._sendStatusTask = None

        self._timeouts = ensureDottedAccess({})

        self._communicator = options.communicator
        self._connectedSince = getTimestamp()
        self._isMaster = options.isMaster if type(options.isMaster) is int else None

        self._logger = defineNopeLogger(options.logger, 'core.connectivity-manager')

        self.ready = NopeObservable()
        self.ready.setContent(False)
        self._externalDispatchers = dict()
        self.dispatchers = DictBasedMergeData(self._externalDispatchers, 'id')

        if self._logger:
            self._logger.info('core.connectivity-manager', self.id, 'is ready')

        self.reset()
        EXECUTOR.callParallel(self.init)

    @property
    def id(self):
        return self._id

    @property
    def info(self):

        # Helper for the Memory.
        _virtual_memory = psutil.virtual_memory()

        return ensureDottedAccess({
            'id': self.id,
            'env': 'python',
            'version': _VERSION,
            'isMaster': self.isMaster,
            'isMasterForced': type(self._isMaster) is bool,
            'host': {
                'cores': os.cpu_count(),
                'cpu': {
                    'model': _PROCESSOR_NAME,
                    'speed': psutil.cpu_freq().max,
                    'usage': psutil.cpu_percent(0)
                },
                'os': str(platform.system()) + " " + str(platform.release()),
                'ram': {
                    'used_perc': _virtual_memory.percent,
                    'free': round(_virtual_memory.free / 1048576),
                    'total': round(_virtual_memory.total / 1048576)
                },
                'name': gethostname()
            },
            'pid': os.getpid(),
            'timestamp': self.now,
            'connectedSince': self.connectedSince,
            'status': ENopeDispatcherStatus.HEALTHY.value
        })

    @property
    def up_time(self):
        return getTimestamp() - self.connectedSince

    @property
    def connectedSince(self):
        return self._connectedSince + self._deltaTime

    @property
    def isMaster(self):
        if self._isMaster is None:
            try:
                return self.id == self.master.id
            except Exception as e:
                return False
        return self._isMaster

    @isMaster.setter
    def isMaster(self, value):
        self._isMaster = value
        EXECUTOR.callParallel(self._asyncSendStatus)

    def _getPossibleMasterCandidates(self):
        possibleMasters = []
        for info in self.dispatchers.originalData.values():
            # In here we have to use Camel-Case because we are considering
            # Camel-Case in the entire system.
            if info.isMasterForced and not info.isMaster:
                continue
            possibleMasters.append(info)
        return possibleMasters

    @property
    def master(self):
        def checkIfIsMaster(item):
            return item.isMaster and item.isMasterForced

        candidates = self._getPossibleMasterCandidates()
        masters = list(filter(checkIfIsMaster, candidates))
        if len(masters) != 1:
            if len(masters) > 1 and self._logger:
                self._logger.warn(
                    f"Found {len(masters)}. We now will select the one which has been online for the longest time.")
            idx = minOfArray(candidates, 'connectedSince').index
            if idx is not None:
                return candidates[idx]
            raise Exception('No Master has been found !')
        return masters[0]

    @property
    def now(self):
        return getTimestamp() + self._deltaTime

    async def init(self):

        self.ready.setContent(False)

        await self.setTimings(self.options.timeouts)

        def onConnect(connected, _rest):
            if connected:
                self._connectedSince = getTimestamp()

        self._communicator.connected.subscribe(onConnect)
        await self._communicator.connected.waitFor()

        def onStatusChanged(info):
            self._externalDispatchers[info.id] = ensureDottedAccess(info)
            if info.id != self.id:
                self._externalDispatchers[self.id] = self.info
                self.dispatchers.update()

        await self._communicator.on('statusChanged', onStatusChanged)

        def onBonjour(opts):
            if self.id != opts.dispatcherId:
                if self._logger:
                    self._logger.debug('Remote Dispatcher "' + opts.dispatcherId + '" went online')
                    self._asyncSendStatus()

        await self._communicator.on('bonjour', onBonjour)

        def onAurevoir(msg):
            # We try to pop the item. If it fails we wont update the elements
            item = self._externalDispatchers.pop(msg.dispatcherId, False)
            if item:
                self.dispatchers.update()

        await self._communicator.on('aurevoir', onAurevoir)

        await self._asyncSendStatus()

        if self._logger:
            self._logger.info('core.connectivity-manager', self.id, 'initialized')

        await self.emitBonjour()
        await self._asyncSendStatus()
        self.ready.setContent(True)

    def _checkDispachterHealth(self):
        """ Checks the health of dispatcher. If some changes like their connection
            are determined, an update is transmitted via the attribute `dispatchers`

        """
        currentTime = self.now

        changes = False

        for status in list(self._externalDispatchers.values()):
            # determine the Difference
            diff = currentTime - status['timestamp']

            # Based on the Difference Determine the Status
            if diff > self._timeouts['remove']:
                # remove the Dispatcher. But be quiet.
                # Perhaps more dispatchers will be removed
                self._removeDispatcher(status['id'], True)
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
            EXECUTOR.callParallel(lambda: self.dispatchers.update)

    def _removeDispatcher(self, dispatcher: str, quiet=False):
        """ Removes a dispatcher.
        """
        dispatcherInfo = self._externalDispatchers.pop(dispatcher, None)
        if not quiet:
            self.dispatchers.update()
        if self._logger and dispatcherInfo:
            self._logger.warn(
                f'a dispatcher on {dispatcherInfo.host.name} went offline. ID of the Dispatcher: "{dispatcher}"')

    async def _asyncSendStatus(self):
        if self._communicator.connected.getContent():
            try:
                info = self.info
                self._externalDispatchers[self.id] = info
                await self._communicator.emit('statusChanged', info)
            except Exception as e:
                if self._logger:
                    self._logger.error('Failled to send the status')
                    self._logger.error(e)

                else:
                    print(formatException(e))

    def sync_time(self, timestamp, delay=0):
        internalTimestamp = getTimestamp()
        self._deltaTime = internalTimestamp - (timestamp - delay)

    def getStatus(self, _id: str):
        return self._externalDispatchers[_id]

    async def emitBonjour(self):
        await self._communicator.emit('bonjour',
                                      ensureDottedAccess({'dispatcherId': self.id}))

    def reset(self):
        self._externalDispatchers.clear()
        self.dispatchers.update(self._externalDispatchers)

    async def setTimings(self, options):

        options = ensureDottedAccess(options)

        await self.dispose(True)

        self._timeouts = ensureDottedAccess({
            'sendAliveInterval': 500,
            'checkInterval': 250,
            'slow': 1000,
            'warn': 2000,
            'dead': 5000,
            'remove': 10000
        })

        if options:
            self._timeouts.update(options)

        # Setup Test Intervals:
        if self._timeouts.checkInterval > 0:
            # Define a Checker, which will test the status
            # of the external Dispatchers.
            self._checkStatusTask = EXECUTOR.setInterval(
                self._checkDispachterHealth,
                self._timeouts["checkInterval"]
            )

        if self._timeouts.sendAliveInterval > 0:
            # Define a Timer, which will emit Status updates with
            # the desired delay.
            self._sendStatusTask = EXECUTOR.setInterval(
                self._asyncSendStatus,
                self._timeouts["sendAliveInterval"]
            )

    @property
    def all_hosts(self):
        hosts = set()
        for info in self.dispatchers.originalData.values():
            hosts.add(info.host.name)
        return list(hosts)

    async def dispose(self, quiet=False):
        if self._sendStatusTask:
            self._sendStatusTask.cancel()
        if self._checkStatusTask:
            self._checkStatusTask.cancel()
        if not quiet:
            await self._communicator.emit('aurevoir', DottedDict({'dispatcherId': self.id}))
