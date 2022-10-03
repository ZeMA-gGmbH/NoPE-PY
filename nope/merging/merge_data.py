from ..eventEmitter import NopeEventEmitter
from ..observables import NopeObservable
from ..helpers import DottedDict, extract_unique_values, transform_dict, determine_difference


class MergeData:

    def __init__(self, original_data, _extract_data):
        self.original_data = original_data
        self._extract_data = _extract_data
        self.on_change = NopeEventEmitter()
        self.data = NopeObservable()
        self.data.set_content([])
        
        self.update(force=True)

    def update(self, data=None, force=False):
        if data != None:
            self.original_data = data
        after_adding = self._extract_data(self.original_data)
        diff = determine_difference(set(self.data.get_content()), after_adding)
        if force or ((len(diff.removed) > 0) or len(diff.added) > 0):
            self.data.set_content(list(after_adding))
            self.on_change.emit(DottedDict({'added': list(diff.added), 'removed': list(diff.removed)}))

    def dispose(self):
        self.data.dispose()
        self.on_change.dispose()


class DictBasedMergeData(MergeData):

    def __init__(self, original_data, _path='', _path_key=None):

        def callback(m):
            return extract_unique_values(m, _path, _path_key)

        self._path = _path
        self._path_key = _path_key
        self.amount_of = dict()
        self.simplified = dict()
        self.key_mapping = dict()
        self.key_mapping_reverse = dict()
        self.conflicts = dict()
        self.org_key_to_extracted_value = dict()
        self.extracted_key = []
        self.extracted_value = []

        super().__init__(original_data,callback)

    def update(self, data=None, force = False):
        if data != None:
            self.original_data = data
        result = transform_dict(self.original_data, self._path, self._path_key)
        
        self.simplified = result.extracted_map
        self.amount_of = result.amount_of
        self.key_mapping = result.key_mapping
        self.key_mapping_reverse = result.key_mapping_reverse
        self.conflicts = result.conflicts
        self.org_key_to_extracted_value = result.org_key_to_extracted_value
        self.extracted_key = [*self.simplified.keys()]
        self.extracted_value = [*self.simplified.values()]
        
        super().update(data, force)
