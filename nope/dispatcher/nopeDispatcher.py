from nope.helpers.pathMatchingMethods import comparePatternAndPath, ensureDottedAccess
from nope.dispatcher.core import NopeCore


class NopeDispatcher(NopeCore):
    """  A Dispatcher to perform a function on a Remote Dispatcher. Therefore a Task is created and forwarded to the remote.
    """

    @property
    def masterExists(self):
        return self.connectivityManager.master.isMasterForced

    def pushData(self, path: str, content, options=None) -> None:
        """ Pushs the desired data into the system.
        Args:
            path (str): The path to the Data.
            content (any): The Content to Push
            options (dict-like, optional): The Options during pushing. Defaults to None.
        """
        options = ensureDottedAccess(options)
        return self.dataDistributor.pushData(path, content, options)

    def pullData(self, path: str, _default=None):
        """ Helper to pull some data from the system.

        Args:
            path (str): The path to the Data.
            _default (any, optional): The value to use if no data has been found. If not provided an error is thrown. Defaults to None.

        Returns:
            any: The data or default type (if set)
        """
        return self.dataDistributor.pullData(path, _default)

    def subscribeToEvent(self, event: str, callback):
        """ Helper to subscribe to specific events.

        Args:
            event (str): Name of the event to listen to.
            callback (callable): the Callback to use. Must receive *args.

        Returns:
            Observer: Observer for the Subcription. contains the methods "pause", "unpause" and "unsubscribe"
        """
        return self.eventDistributor.registerSubscription(event, callback)

    def emitEvent(self, eventName, data, options=None):
        """ Emits an event with the given name. All event-subscriber, where the topic matches will receive this notification.

        Args:
            event (str): Name of the event to emii.
            data (any): The data to emit.
            options (dict-like): will be added to the event (for instance timestamp, sender, etc.)
        """
        options = ensureDottedAccess(options)
        self.eventDistributor.emit(eventName, data, options)

    def query(self, pattern: str, type: str) -> list:
        """ Receive the "instances" | "services" | "properties" | "events"
            which matches with the given pattern. Therefore the user provides
            the pattern and type.
            @return {string[]} List of the matching items.

        Args:
            pattern (str): pattern Pattern to query the provided type.
            type (str): type which should be querried. Allowed values are: "instances" | "services" | "properties" | "events"
        """

        items = []

        if type == 'instances':

            def callback_0(item):
                return item.identifier
            items = map(callback_0, self.instanceManager.
                        instances.data.getContent())
        elif type == 'services':
            items = list(self.rpcManager.services.simplified.keys())
        elif type == 'properties':
            items = self.dataDistributor.publishers.data.getContent()
        elif type == 'events':
            items = self.eventDistributor.publishers.data.getContent()
        else:
            raise Exception('Invalid Type-Parameter')

        return list(filter(lambda item: comparePatternAndPath(
            pattern, item).affected, items))

    def getAllHosts(self):
        hosts = set()
        for info in self.connectivityManager.dispatchers.originalData.values():
            hosts.add(info.host.name)
        return list(hosts)

    def toDescription(self):

        ret = self.connectivityManager.info.copy()
        ret.update(
            ensureDottedAccess({
                'isMaster': self.connectivityManager.isMaster,
                'instances': self.instanceManager.instances.data.getContent(),
                'services': self.rpcManager.services.data.getContent(),
                'events': self.eventDistributor.emitters,
                'properties': self.dataDistributor.emitters,
                'data': self.dataDistributor.pullData('', dict())
            })
        )

        return ret
