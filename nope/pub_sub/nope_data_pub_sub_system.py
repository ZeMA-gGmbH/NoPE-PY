from .nope_pub_sub_system import PubSubSystem
from ..helpers import copy, containsWildcards, ensureDottedAccess, MULTI_LEVEL_WILDCARD, flattenObject, \
    comparePatternAndPath


class DataPubSubSystem(PubSubSystem):

    def __init__(self, options={}):
        super().__init__(options)
        self._sendCurrentDataOnSubscription = True

    @property
    def data(self):
        # A Getter to return a COPY of the item. Outside of the system,
        # you'll never receive the original object.
        return copy(self._data)

    def pushData(self, path: str, content, options=None):
        """ Function, to push data. Every subscriber will be informed, if pushing the data on the
            given path will affect the subscribers.

        Args:
            path (str): The Path, on which the data should be changed
            content (any): The content to store in the given path.
            options (dict-like, optional): The Options, that will be forwarded to subscribers. Defaults to None.
        """
        options = ensureDottedAccess(options)
        return self._pushData(path, path, content, options)

    def pullData(self, path: str, default=None):
        """ Pull some Data of System. You will allways receive a just a copy. This method prevents you
            to use a pattern like path. If you want to use patterns please use the "patternbasedPullData"

        Args:
            path (str): The Path to pull the data.
            default (any, optional): If no data is found => return the default data. Defaults to None.

        Returns:
            any: The data.
        """

        return self._pullData(path, default)

    def patternbasedPullData(self, pattern: str, default=None):
        """ A Pattern based Pull. You can provide a mqtt based pattern and receive an array which contains
            all the data which matches the topic.

        Args:
            topic (str): The path to pull the data from
            default (any, optional): A Default value to use. If set to None we will skip this items. Defaults to None.

        Returns:
            list: the list containing an dict, with the keys: `path` = the matching path, `data` = the contained data.
        """
        return self._patternbasedPullData(pattern, default)

    def patternBasedPush(self, pattern: str, data, options=None, fast=False):
        """ 

        Args:
            pattern (str): The P
            data (any): _description_
            options (dict-like, optional): Additional Event-Date like `timestamp`, `sender`, ... . Defaults to None.
            fast (bool, optional):  Flag to emit single changes or all changes. Defaults to False.

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """

        options = ensureDottedAccess(options)

        # To extract the data based on a Pattern,
        # we firstly, we check if we would affect the data.
        if not containsWildcards(pattern):
            return self.pushData(pattern, pattern, data, options)
        if MULTI_LEVEL_WILDCARD in pattern:
            raise Exception('You can only use single-level wildcards in self action')
        flatten_data = flattenObject(self.data)
        options = self.updateOptions(options)
        for path in flatten_data.keys():
            if comparePatternAndPath(pattern, path).affectedOnSameLevel:
                self.pushData(path, pattern, data, options, fast)

        if fast:
            # Its better for us, to just store the incremental changes
            # with the pattern
            self.onIncrementalDataChange.emit(ensureDottedAccess({'path': pattern, 'data': data, **options}))
