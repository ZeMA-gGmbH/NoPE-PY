from ..eventEmitter import NopeEventEmitter
from ..helpers import DottedDict, extractUniqueValues, transform_dict, determineDifference
from ..observable import NopeObservable


class MergeData:

    def __init__(self, originalData, _extractData):
        self.originalData = originalData
        self._extractData = _extractData
        self.onChange = NopeEventEmitter()
        self.data = NopeObservable()
        self.data.setContent([])
        self.error = False

        self.update(force=True)

    def update(self, data=None, force=False):
        if data is not None:
            self.originalData = data
        after_adding = self._extractData(self.originalData)
        diff = determineDifference(self.data.getContent(), after_adding)
        if force or ((len(diff.removed) > 0) or len(diff.added) > 0):
            self.data.setContent(list(after_adding))
            self.onChange.emit(DottedDict(
                {'added': list(diff.added), 'removed': list(diff.removed)}))

    def dispose(self):
        self.data.dispose()
        self.onChange.dispose()


class DictBasedMergeData(MergeData):

    def __init__(self, originalData, _path='', _pathKey=None):
        def callback(m):
            return extractUniqueValues(m, _path, _pathKey)

        self._path = _path
        self._pathKey = _pathKey
        self.amountOf = dict()
        self.simplified = dict()
        self.keyMapping = dict()
        self.keyMappingreverse = dict()
        self.conflicts = dict()
        self.orgKeyToExtractedValue = dict()
        self.extracted_key = []
        self.extracted_value = []

        super().__init__(originalData, callback)

    def update(self, data=None, force=False):
        if data is not None:
            self.originalData = data
        result = transform_dict(self.originalData, self._path, self._pathKey)

        self.simplified = result.extracted_map
        self.amountOf = result.amountOf
        self.keyMapping = result.keyMapping
        self.keyMappingreverse = result.keyMappingreverse
        self.conflicts = result.conflicts
        self.orgKeyToExtractedValue = result.orgKeyToExtractedValue
        self.extracted_key = [*self.simplified.keys()]
        self.extracted_value = [*self.simplified.values()]

        super().update(data, force)
