from ..eventEmitter import NopeEventEmitter
from ..helpers import comparePatternAndPath, copy, generateId, DottedDict, ensureDottedAccess, rgetattr, \
    containsWildcards, getTimestamp, isIterable, rsetattr, flattenObject
from ..merging import DictBasedMergeData

DEFAULT_OBJ = object()


def _memoizedCompare(matchTopicsWithoutWildcards: bool):
    """ Helper to memoize the

    Args:
        options (bool): Flag to match topics with or without a wildcard

    Returns:
        callable: a Function that stores the results.
    """
    cache = {}

    def ret(pattern, path):
        nonlocal cache
        nonlocal matchTopicsWithoutWildcards

        key = f'{pattern}-{path}'

        if key not in cache:
            cache[key] = comparePatternAndPath(pattern, path, {
                'matchTopicsWithoutWildcards': matchTopicsWithoutWildcards
            })

        return cache[key]

    return ret


def _extractPubAndSubTopic(options: DottedDict):
    """ Helper to extract the pub and sub topic based on the provided options

    Args:
        options (DottedDict): the emitter options

    Returns:
        subTopic, pubTopic: the strings.
    """
    pubTopic = None
    if isinstance(options.topic, str):
        pubTopic = options.topic
    else:
        pubTopic = options.topic.publish

    subTopic = None
    if isinstance(options.topic, str):
        subTopic = options.topic
    else:
        subTopic = options.topic.subscribe

    return subTopic, pubTopic


class PubSubSystem:

    def __init__(self, mqttPatternBasedSubscriptions=True, forwardChildData=True,
                 forwardParentData=True, matchTopicsWithoutWildcards=True, **kwargs):

        # Adapt the Options
        self._options = ensureDottedAccess({
            'mqttPatternBasedSubscriptions': mqttPatternBasedSubscriptions,
            'forwardChildData': forwardChildData,
            'forwardParentData': forwardParentData,
            'matchTopicsWithoutWildcards': matchTopicsWithoutWildcards
        })

        self._sendCurrentDataOnSubscription = False
        self.id = generateId()

        self._emitters = dict()
        self._emittersToObservers = dict()

        self._matched = dict()
        self._disposing = False

        self._comparePatternAndPath = _memoizedCompare(self._options)
        self.subscriptions = DictBasedMergeData(self._emitters, 'subTopic')
        self.publishers = DictBasedMergeData(self._emitters, 'pubTopic')
        self.onIncrementalDataChange = NopeEventEmitter()

        self._data = ensureDottedAccess({}, useNoneAsDefaultValue=False)

    @property
    def options(self):
        return self._options.copy()

    def register(self, emitter, options):

        options = ensureDottedAccess(options)

        if options.topic is None:
            raise Exception("A Topic must be provided")

        if emitter not in self._emitters:
            # Now we will assign the pub and sub topic.
            # this is defined in the options.

            pubTopic = None
            if isinstance(options.topic, str):
                pubTopic = options.topic
            else:
                pubTopic = options.topic.publish

            subTopic = None
            if isinstance(options.topic, str):
                subTopic = options.topic
            else:
                subTopic = options.topic.subscribe

            if options.mode is None or not ("publish" in options.mode):
                pubTopic = False
            if options.mode is None or not ("subscribe" in options.mode):
                subTopic = False

            observer = None
            callback = None

            if pubTopic:

                def callbackToAssign(content, opts):
                    # Internal Data-Update of the pub-sub-system
                    # we wont push the data again. Otherwise, we
                    # risk an recursive endloop.
                    if opts.pubSubUpdate:
                        return

                    # We use this callback to forward the data into the system:
                    self._pushData(pubTopic, pubTopic,
                                   content, opts, False, emitter)

                callback = callbackToAssign

            # Register the emitter. This will be used during topic matching.
            self._emitters[emitter] = ensureDottedAccess(
                {'options': options, 'pubTopic': pubTopic, 'subTopic': subTopic, 'callback': callback,
                 'observer': observer})

            # Update the Matching Rules.
            self._updatePartialMatching('add', emitter, pubTopic, subTopic)

            if callback:
                # If necessary. Add the Callback.
                observer = emitter.subscribe(callback, ensureDottedAccess(
                    {'skipCurrent': not self._sendCurrentDataOnSubscription}))
                # Now lets store our binding.
                self._emittersToObservers[emitter] = observer

            if subTopic and self._sendCurrentDataOnSubscription:
                if containsWildcards(subTopic):

                    for item in self._patternbasedPullData(subTopic, None):
                        # We check if the content is available
                        if item.get("data", False):
                            emitter.emit(
                                item.data,
                                ensureDottedAccess({
                                    'sender': self.id,
                                    'topicOfContent': item["path"],
                                    'topicOfChange': item["path"],
                                    'topicOfSubscription': subTopic
                                })
                            )
                else:
                    currentContent = self._pullData(subTopic, None)
                    if currentContent is not None:
                        emitter.emit(
                            currentContent,
                            ensureDottedAccess({
                                'sender': self.id,
                                'topicOfContent': subTopic,
                                'topicOfChange': subTopic,
                                'topicOfSubscription': subTopic
                            })
                        )
        else:
            raise Exception('Already registered Emitter!')
        return emitter

    def updateOptions(self, emitter, options):
        # We will adapat the Options, for dotted access.
        options = ensureDottedAccess(options)
        if emitter in self._emitters:
            subTopic, pubTopic = _extractPubAndSubTopic(options)
            data = self._emitters.get(emitter)
            self._updatePartialMatching(
                'remove', emitter, data.pubTopic, data.subTopic)

            data.options = options
            data.subTopic = subTopic
            data.pubTopic = pubTopic

            self._emitters[emitter] = data
            self._updatePartialMatching('add', emitter, pubTopic, subTopic)
        else:
            raise Exception('Emitter is not registered')

    def unregister(self, emitter):
        if emitter in self._emitters:
            options = self._emitters.pop(emitter)
            subTopic, pubTopic = _extractPubAndSubTopic(options["options"])

            self._updatePartialMatching('remove', emitter, pubTopic, subTopic)
            return True
        return False

    def registerSubscription(self, topic, subscription):
        emitter = NopeEventEmitter()
        observer = emitter.subscribe(subscription)
        self.register(emitter, {'mode': 'subscribe',
                                'schema': {}, 'topic': topic})
        return observer

    @property
    def emitters(self):
        # TODO:
        pass

    def updateMatching(self):
        self._matched.clear()
        for emitter, item in self._emitters.items():
            # Extract the topic
            subTopic = item.get("subTopic", False)
            pubTopic = item.get("pubTopic", False)

            if pubTopic:
                self._updateMatchingForTopic(pubTopic)

            if subTopic:
                self._addMatchingEntryIfRequired(subTopic, subTopic, emitter)
                self.publishers.update()

            self.subscriptions.update()

    def _deleteMatchingEntry(self, pubTopic, subTopic, emitter):
        if pubTopic in self._matched:
            data = self._matched.get(pubTopic)
            if subTopic in data.dataPull:
                data.dataPull.get(subTopic).remove(emitter)
            if subTopic in data.dataQuery:
                data.dataQuery.get(subTopic).remove(emitter)

    def _addMatchingEntryIfRequired(self, pubTopic, subTopic, emitter):
        result = self._comparePatternAndPath(subTopic, pubTopic)
        if result.affected:
            if not result.containsWildcards and ((result.affectedByChild and not self.options.forwardChildData) or
                                                 (
                result.affectedByParent and not self.options.forwardParentData)
            ):
                return

            # We now have match the topic as following described:
            # 1) subscription contains a pattern
            #    - dircet change (same-level) => content
            #    - parent based change => content
            #    - child based change => content
            # 2) subscription doesnt contains a pattern:
            #    We more or less want the data on the path.
            #    - direct change (topic = path) => content
            #    - parent based change => a super change
            if result.containsWildcards:
                if self.options.mqttPatternBasedSubscriptions:
                    if result.patternToExtractData:
                        self._addToMatchingStructure(
                            'dataQuery', pubTopic, result.patternToExtractData, emitter)
                    elif result.pathToExtractData:
                        self._addToMatchingStructure(
                            'dataPull', pubTopic, result.pathToExtractData, emitter)
                    else:
                        raise Exception(
                            'Implementation Error. Either the patternToExtractData or the pathToExtractData must be provided')
                else:
                    self._addToMatchingStructure(
                        'dataQuery', pubTopic, pubTopic, emitter)
            else:
                if result.affectedByChild and not self.options.forwardChildData or result.affectedByParent and not self.options.forwardParentData:
                    return
                if result.pathToExtractData:
                    self._addToMatchingStructure(
                        'dataPull', pubTopic, result.pathToExtractData, emitter)
                else:
                    raise Exception(
                        "Implementation Error. The 'pathToExtractData' must be provided")

    def _updatePartialMatching(
            self, mode: str, _emitter, _pubTopic: str, _subTopic: str):
        for item in self._emitters.values():
            pubTopic = item.pubTopic
            if mode == 'remove' and pubTopic and _subTopic:
                self._deleteMatchingEntry(pubTopic, _subTopic, _emitter)
            elif mode == 'add' and pubTopic and _subTopic:
                self._addMatchingEntryIfRequired(
                    pubTopic, _subTopic, _emitter)
        if mode == 'add':
            if _pubTopic:
                self._updateMatchingForTopic(_pubTopic)
            if _subTopic and not containsWildcards(_subTopic):
                self._addMatchingEntryIfRequired(
                    _subTopic, _subTopic, _emitter)
        elif mode == 'remove':
            if _subTopic:
                self._deleteMatchingEntry(_subTopic, _subTopic, _emitter)

        self.publishers.update()
        self.subscriptions.update()

    def emit(self, eventName, data, options=None):
        return self._pushData(eventName, eventName, data,
                              ensureDottedAccess(options))

    async def dispose(self):
        self._disposing = True

        for emitter in self._emitters:
            self.unregister(emitter)

        self.onIncrementalDataChange.dispose()
        self.publishers.dispose()
        self.subscriptions.dispose()

    def _addToMatchingStructure(
            self, entry, topicOfChange, path_or_pattern, emitter):
        if topicOfChange not in self._matched:
            self._matched[topicOfChange] = ensureDottedAccess(
                {'dataPull': {}, 'dataQuery': {}})
        if path_or_pattern not in self._matched[topicOfChange][entry]:
            self._matched[topicOfChange][entry][path_or_pattern] = set()

        self._matched.get(topicOfChange)[entry].get(
            path_or_pattern).add(emitter)

    def _updateMatchingForTopic(self, topicOfChange):
        if topicOfChange not in self._matched:
            self._matched[topicOfChange] = ensureDottedAccess(
                {'dataPull': {}, 'dataQuery': {}})
        for emitter, item in self._emitters.items():
            if item.subTopic:
                self._addMatchingEntryIfRequired(
                    topicOfChange, item.subTopic, emitter)

    def _notify(self, topicOfContent: str, topicOfChange: str,
                options, emitterCausingUpdate=None):
        """ Internal Function to _notify all subscribers

        Args:
            topicOfContent (str): _description_
            topicOfChange (str): _description_
            options (dict-like): _description_
            _emitter (Emitter, optional): _description_. Defaults to None.
        """
        if self._disposing:
            return

        # Check whether a Matching exists for this
        # Topic, if not add it.
        if topicOfContent not in self._matched:
            self._updateMatchingForTopic(topicOfContent)

        referenceToMatch = self._matched[topicOfContent]

        for path_to_pull, emitters in referenceToMatch.dataPull.items():

            for emitter in emitters:
                data = self._pullData(path_to_pull, None)

                # Only if we want to _notify an exclusive emitter we
                # have to continue, if our emitter isnt matched.
                if emitterCausingUpdate is not None and emitterCausingUpdate == emitter:
                    continue

                emitter.emit(
                    data,
                    ensureDottedAccess({
                        **options,
                        'topicOfChange': topicOfChange,
                        'topicOfContent': topicOfContent,
                        'topicOfSubscription': self._emitters[emitter].subTopic
                    })
                )

        for pattern, emitters in referenceToMatch.dataQuery.items():

            for emitter in emitters:
                data = self._pullData(pattern, None)
                if emitter is not None and emitter != emitter:
                    continue
                emitter.emit(
                    data,
                    ensureDottedAccess({
                        **options,
                        'mode': 'direct',
                        'topicOfChange': topicOfChange,
                        'topicOfContent': topicOfContent,
                        'topicOfSubscription': self._emitters.get(emitter).subTopic
                    })
                )

    def _updateOptions(self, options):
        if not options.timestamp:
            options.timestamp = getTimestamp()
        if not isinstance(options.forced, bool):
            options.forced = False
        if not isIterable(options.args):
            options.args = []
        if not options.sender:
            options.sender = self.id
        return options

    def _pushData(self, pathOfContent: str, pathOfChange: str,
                  data, options={}, quiet=False, emitter=None):
        """ Internal helper to push data to the data property. This results in informing the subscribers.

        Args:
            pathOfContent (str): Path, that is used for pushing the data.
            pathOfChange (str): The path, which caused the change.
            data (any): The data to push
            options (dict, optional): Options used during pushing. Defaults to {}.
            quiet (bool, optional): _description_. Defaults to False.
            emitter (_type_, optional): _description_. Defaults to None.
        """

        options = self._updateOptions(options)
        options.pubSubUpdate = True
        if containsWildcards(pathOfContent):
            raise 'The Path contains wildcards. Please use the method "patternbasedPullData" instead'
        elif pathOfContent == '':
            self._data = copy(data)
            self._notify(pathOfContent, pathOfChange, options, emitter)
        else:
            rsetattr(self._data, pathOfContent, copy(data))
            self._notify(pathOfContent, pathOfChange, options, emitter)
        if not quiet:
            self.onIncrementalDataChange.emit(ensureDottedAccess({
                'path': pathOfContent,
                'data': data,
                **options
            }))

    def _pullData(self, topic, default=None):
        if containsWildcards(topic):
            raise 'The Path contains wildcards. Please use the method "patternbasedPullData" instead'
        return copy(rgetattr(self._data, topic, default))

    def _patternbasedPullData(self, pattern: str, default=None):
        """ Helper, which enable to perform a pattern based pull.
            The code receives a pattern, and matches the existing content
            (by using there path attributes) and return the corresponding data.

        Args:
            pattern (str): the pattern
            default (any, optional): The default-value. Defaults to None.

        Returns:
            list:
        """

        # To extract the data based on a Pattern,
        # we firstly, we check if the given pattern
        # is a pattern.
        if not containsWildcards(pattern):
            # Its not a pattern so we will speed up
            # things.
            global DEFAULT_OBJ
            data = self._pullData(pattern, DEFAULT_OBJ)

            if data is not DEFAULT_OBJ:
                return [
                    ensureDottedAccess({
                        'path': pattern,
                        'data': data
                    })
                ]
            elif default is not None:
                return [
                    ensureDottedAccess({
                        'path': pattern,
                        'data': default
                    })
                ]

            return []

        # Now we know, we have to work with the query,
        # for that purpose, we will adapt the data object
        # to the following form:
        # {path: value}
        flatten = flattenObject(self._data)
        ret = []

        # We will use our alternative representation of the
        # object to compare the pattern with the path item.
        # only if there is a direct match => we will extract it.
        # That corresponds to a direct level extraction and
        # prevents to grap multiple items.
        for path, data in flatten.items():
            result = self._comparePatternAndPath(pattern, path)
            if result.affectedOnSameLevel or result.affectedByChild:
                ret.append(ensureDottedAccess({
                    'path': path,
                    'data': data
                }))

        # Now we just return our created element.
        return ret
