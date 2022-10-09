from ..event_emitter import NopeEventEmitter
from ..helpers import compare_pattern_and_path, copy, generate_id, DottedDict, ensure_dotted_dict, rgetattr, \
    contains_wildcards, get_timestamp, is_iterable, rsetattr, flatten_object
from ..merging import DictBasedMergeData

DEFAULT_OBJ = object()


def _memoized_compare(match_topics_without_wildcards: bool):
    """ Helper to memoize the 

    Args:
        options (bool): Flag to match topics with or without a wildcard

    Returns:
        callable: a Function that stores the results.
    """
    cache = {}

    def ret(pattern, path):
        nonlocal cache
        nonlocal match_topics_without_wildcards

        key = f'{pattern}-{path}'

        if key not in cache:
            cache[key] = compare_pattern_and_path(pattern, path, {
                'match_topics_without_wildcards': match_topics_without_wildcards
            })

        return cache[key]

    return ret


def _extract_pub_and_sub_topic(options: DottedDict):
    """ Helper to extract the pub and sub topic based on the provided options

    Args:
        options (DottedDict): the emitter options

    Returns:
        sub_topic, pub_topic: the strings.
    """
    pub_topic = None
    if type(options.topic) is str:
        pub_topic = options.topic
    else:
        pub_topic = options.topic.publish

    sub_topic = None
    if type(options.topic) is str:
        sub_topic = options.topic
    else:
        sub_topic = options.topic.subscribe

    return sub_topic, pub_topic


class PubSubSystem:

    def __init__(self, options={}):

        # Adapt the Options
        options = ensure_dotted_dict(options)

        # Assign the Default values.
        self._options = ensure_dotted_dict({
            'mqtt_based_pattern_subscriptions': True,
            'forward_child_data': True,
            'forward_parent_data': True,
            'match_topics_without_wildcards': True
        })
        self._options.update(options)

        self.send_current_data_on_subscription = False
        self.id = generate_id()

        self._emitters = dict()
        self._emitters_to_observers = dict()

        self._matched = dict()
        self.disposing = False

        self._compare_pattern_and_path = _memoized_compare(options)
        self.subscriptions = DictBasedMergeData(self._emitters, 'subTopic')
        self.publishers = DictBasedMergeData(self._emitters, 'pubTopic')
        self.on_incremental_data_change = NopeEventEmitter()

        self._data = ensure_dotted_dict({})

    @property
    def options(self):
        return self._options.copy()

    def register(self, emitter, options):

        options = ensure_dotted_dict(options)

        if options.topic is None:
            raise Exception("A Topic must be provided")

        if emitter not in self._emitters:
            # Now we will assign the pub and sub topic.
            # this is defined in the options.

            pub_topic = None
            if type(options.topic) is str:
                pub_topic = options.topic
            else:
                pub_topic = options.topic.publish

            sub_topic = None
            if type(options.topic) is str:
                sub_topic = options.topic
            else:
                sub_topic = options.topic.subscribe

            if options.mode is None or not ("publish" in options.mode):
                pub_topic = False
            if options.mode is None or not ("subscribe" in options.mode):
                sub_topic = False

            observer = None
            callback = None

            if pub_topic:

                def callback_to_assign(content, opts):
                    # Internal Data-Update of the pub-sub-system
                    # we wont push the data again. Otherwise, we
                    # risk an recursive endloop.
                    if opts.pub_sub_update:
                        return

                    # We use this callback to forward the data into the system:
                    self._push_data(pub_topic, pub_topic,
                                    content, opts, False, emitter)

                callback = callback_to_assign

            # Register the emitter. This will be used during topic matching.
            self._emitters[emitter] = ensure_dotted_dict(
                {'options': options, 'pub_topic': pub_topic, 'sub_topic': sub_topic, 'callback': callback,
                 'observer': observer})

            # Update the Matching Rules.
            self._partial_matching_update('add', emitter, pub_topic, sub_topic)

            if callback:
                # If necessary. Add the Callback.
                observer = emitter.subscribe(callback, ensure_dotted_dict(
                    {'skip_current': not self.send_current_data_on_subscription}))
                # Now lets store our binding.
                self._emitters_to_observers[emitter] = observer

            if sub_topic and self.send_current_data_on_subscription:
                if contains_wildcards(sub_topic):

                    for item in self._patternbased_pull_data(sub_topic, None):
                        # We check if the content is available
                        if item.get("data", False):
                            emitter.emit(
                                item.data,
                                ensure_dotted_dict({
                                    'sender': self.id,
                                    'topic_of_content': item["path"],
                                    'topic_of_change': item["path"],
                                    'topic_of_subscription': sub_topic
                                })
                            )
                else:
                    current_content = self._pull_data(sub_topic, None)
                    if current_content != None:
                        emitter.emit(
                            item.data,
                            ensure_dotted_dict({
                                'sender': self.id,
                                'topic_of_content': sub_topic,
                                'topic_of_change': sub_topic,
                                'topic_of_subscription': sub_topic
                            })
                        )
        else:
            raise Exception('Already registered Emitter!')
        return emitter

    def update_options(self, emitter, options):
        # We will adapat the Options, for dotted access.
        options = ensure_dotted_dict(options)
        if emitter in self._emitters:
            sub_topic, pub_topic = _extract_pub_and_sub_topic(options)
            data = self._emitters.get(emitter)
            self._partial_matching_update(
                'remove', emitter, data.pub_topic, data.sub_topic)

            data.options = options
            data.sub_topic = sub_topic
            data.pub_topic = pub_topic

            self._emitters.set(emitter, data)
            self._partial_matching_update('add', emitter, pub_topic, sub_topic)
        else:
            raise Exception('Emitter is not registered')

    def unregister(self, emitter):
        if emitter in self._emitters:
            tmp_cp = copy(self._emitters.get(emitter))
            sub_topic = tmp_cp.pop(sub_topic)
            pub_topic = tmp_cp.pop(pub_topic)
            self._emitters.delete(emitter)
            self._partial_matching_update(
                'remove', emitter, pub_topic, sub_topic)
            return True
        return False

    def register_subscription(self, topic, subscription):
        emitter = NopeEventEmitter()
        observer = emitter.subscribe(subscription)
        self.register(emitter, {'mode': 'subscribe',
                                'schema': {}, 'topic': topic})
        return observer

    @property
    def emitters(self):
        pass

    def update_matching(self):
        self._matched.clear()
        for emitter, item in self._emitters.items():
            # Extract the topic
            sub_topic = item.get("sub_topic", False)
            pub_topic = item.get("pub_topic", False)

            if pub_topic:
                self._update_matching_for_topic(pub_topic)

            if sub_topic:
                self._add_matching_entry_if_required(sub_topic, sub_topic, emitter)
                self.publishers.update()

            self.subscriptions.update()

    def _delete_matching_entry(self, pub_topic, sub_topic, emitter):
        if pub_topic in self._matched:
            data = self._matched.get(pub_topic)
            if pub_topic in data.data_pull:
                data.data_pull.get(sub_topic).pop(emitter)
            if sub_topic in data.data_query:
                data.data_query.get(sub_topic).delete(emitter)

    def _add_matching_entry_if_required(self, pub_topic, sub_topic, emitter):
        result = self._compare_pattern_and_path(sub_topic, pub_topic)
        if result.affected:
            if not result.contains_wildcards and ((result.affected_by_child and
                                                   not self.options.forward_child_data) or
                                                  (result.affected_by_parent and not self.options.forward_parent_data)
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
            if result.contains_wildcards:
                if self.options.mqtt_based_pattern_subscriptions:
                    if result.pattern_to_extract_data:
                        self._add_to_matching_structure(
                            'data_query', pub_topic, result.pattern_to_extract_data, emitter)
                    elif result.path_to_extract_data:
                        self._add_to_matching_structure(
                            'data_pull', pub_topic, result.path_to_extract_data, emitter)
                    else:
                        raise Exception(
                            'Implementation Error. Either the patternToExtractData or the pathToExtractData must be provided')
                else:
                    self._add_to_matching_structure(
                        'data_query', pub_topic, pub_topic, emitter)
            else:
                if result.affected_by_child and not self.options.forward_child_data or result.affected_by_parent and not self.options.forward_parent_data:
                    return
                if result.path_to_extract_data:
                    self._add_to_matching_structure(
                        'data_pull', pub_topic, result.path_to_extract_data, emitter)
                else:
                    raise Exception(
                        "Implementation Error. The 'pathToExtractData' must be provided")

    def _partial_matching_update(self, mode, emitter, pub_topic, sub_topic):
        for item in self._emitters.values():
            pub_topic = item.pub_topic
            if mode == 'remove' and pub_topic and sub_topic:
                self._delete_matching_entry(pub_topic, sub_topic, emitter)
            elif mode == 'add' and pub_topic and sub_topic:
                self._add_matching_entry_if_required(
                    pub_topic, sub_topic, emitter)
        if mode == 'add':
            if pub_topic:
                self._update_matching_for_topic(pub_topic)
            if sub_topic and not contains_wildcards(sub_topic):
                self._add_matching_entry_if_required(
                    sub_topic, sub_topic, emitter)
        elif mode == 'remove':
            if sub_topic:
                self._delete_matching_entry(sub_topic, sub_topic, emitter)
                self.publishers.update()
                self.subscriptions.update()

    def emit(self, event_name, data, options=None):
        return self._push_data(event_name, event_name, data, ensure_dotted_dict(options))

    def dispose(self):
        self.disposing = True

        for emitter in self._emitters:
            self.unregister(emitter)

        self.on_incremental_data_change.dispose()
        self.publishers.dispose()
        self.subscriptions.dispose()

    def _add_to_matching_structure(self, entry, topic_of_change, path_or_pattern, emitter):
        if topic_of_change not in self._matched:
            self._matched[topic_of_change] = ensure_dotted_dict(
                {'data_pull': {}, 'data_query': {}})
        if path_or_pattern not in self._matched[topic_of_change][entry]:
            self._matched[topic_of_change][entry][path_or_pattern] = set()

        self._matched.get(topic_of_change)[entry].get(
            path_or_pattern).add(emitter)

    def _update_matching_for_topic(self, topic_of_change):
        if topic_of_change not in self._matched:
            self._matched[topic_of_change] = ensure_dotted_dict(
                {'data_pull': {}, 'data_query': {}})
        for emitter, item in self._emitters.items():
            if item.sub_topic:
                self._add_matching_entry_if_required(
                    topic_of_change, item.sub_topic, emitter)

    def notify(self, topic_of_content, topic_of_change, options, _emitter=None):
        """ Internal Function to notify all subscribers

        Args:
            topic_of_content (_type_): _description_
            topic_of_change (_type_): _description_
            options (_type_): _description_
            _emitter (_type_, optional): _description_. Defaults to None.
        """
        if self.disposing:
            return

        # Check whether a Matching exists for this
        # Topic, if not add it.
        if topic_of_content not in self._matched:
            self._update_matching_for_topic(topic_of_content)

        reference_to_match = self._matched[topic_of_content]

        for path_to_pull, emitters in reference_to_match.data_pull.items():

            for emitter in emitters:
                data = self._pull_data(path_to_pull, None)

                # Only if we want to notify an exclusive emitter we
                # have to continue, if our emitter isnt matched.
                if _emitter is not None and _emitter == emitter:
                    continue

                emitter.emit(
                    data,
                    ensure_dotted_dict({
                        **options,
                        'topic_of_change': topic_of_change,
                        'topic_of_content': topic_of_content,
                        'topic_of_subscription': self._emitters[emitter].sub_topic
                    })
                )

        for pattern, emitters in reference_to_match.data_query.items():

            for emitter in emitters:
                data = self._pull_data(pattern, None)
                if emitter != None and emitter != emitter:
                    continue
                emitter.emit(
                    data,
                    ensure_dotted_dict({
                        **options,
                        'mode': 'direct',
                        'topic_of_change': topic_of_change,
                        'topic_of_content': topic_of_content,
                        'topic_of_subscription': self._emitters.get(emitter).sub_topic
                    })
                )

    def _update_options(self, options):
        if not options.timestamp:
            options.timestamp = get_timestamp()
        if type(options.forced) is not bool:
            options.forced = False
        if not is_iterable(options.args):
            options.args = []
        if not options.sender:
            options.sender = self.id
        return options

    def _push_data(self, path_of_content: str, path_of_change: str, data, options={}, quite=False, emitter=None):
        """ Internal helper to push data to the data property. This results in informing the subscribers.

        Args:
            path_of_content (str): Path, that is used for pushing the data.
            path_of_change (str): The path, which caused the change.
            data (any): The data to push
            options (dict, optional): Options used during pushing. Defaults to {}.
            quite (bool, optional): _description_. Defaults to False.
            emitter (_type_, optional): _description_. Defaults to None.
        """

        options = self._update_options(options)
        options.pub_sub_update = True
        if contains_wildcards(path_of_content):
            raise 'The Path contains wildcards. Please use the method "patternbasedPullData" instead'
        elif path_of_content == '':
            self._data = copy(data)
            self.notify(path_of_content, path_of_change, options, emitter)
        else:
            rsetattr(self._data, path_of_content, copy(data))
            self.notify(path_of_content, path_of_change, options, emitter)
        if not quite:
            self.on_incremental_data_change.emit(ensure_dotted_dict({
                'path': path_of_content,
                'data': data,
                **options
            }))

    def _pull_data(self, topic, default=None):
        if contains_wildcards(topic):
            raise 'The Path contains wildcards. Please use the method "patternbasedPullData" instead'
        return copy(rgetattr(self._data, topic, default))

    def _patternbased_pull_data(self, pattern: str, default=None):
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
        if not contains_wildcards(pattern):
            # Its not a pattern so we will speed up
            # things.
            global DEFAULT_OBJ
            data = self._pull_data(pattern, DEFAULT_OBJ)

            if data is not DEFAULT_OBJ:
                return [
                    ensure_dotted_dict({
                        'path': pattern,
                        'data': data
                    })
                ]
            elif default is not None:
                return [
                    ensure_dotted_dict({
                        'path': pattern,
                        'data': default
                    })
                ]

            return []

        # Now we know, we have to work with the query,
        # for that purpose, we will adapt the data object
        # to the following form:
        # {path: value}
        flatten_data = flatten_object(self._data)
        ret = []

        # We will use our alternative representation of the
        # object to compare the pattern with the path item.
        # only if there is a direct match => we will extract it.
        # That corresponds to a direct level extraction and
        # prevents to grap multiple items.
        for path, data in flatten_data.items():
            result = self._compare_pattern_and_path(pattern, path)
            if result.affected_on_same_level or result.affected_by_child:
                ret.append(ensure_dotted_dict({
                    'path': path,
                    'data': data
                }))

        # Now we just return our created element.
        return ret
