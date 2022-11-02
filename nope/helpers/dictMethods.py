from collections.abc import Iterable

from .dottedDict import DottedDict, ensureDottedAccess
from .objectMethods import convertData, rgetattr, rqueryAttr, flattenObject, rsetattr
from .path import SPLITCHAR, getLeastCommonPathSegment, pathToCamelCase, pathToSnakeCase
from .stringMethods import camelToSnake, snakeToCamel
from .prints import formatException

__SENTINENTAL = object()


def keysToSnake(d: dict, adaptStrValues=False):
    """ helperfunction, which will change the keys to
        snake case.
    """
    ret = {}
    for key, value in d.items():
        if adaptStrValues and isinstance(value, str):
            ret[camelToSnake(key)] = camelToSnake(value)
        else:
            ret[camelToSnake(key)] = value

    return ret


def keysToSnakeNested(d: dict, adaptStrValues=False):
    """ helper function, which will change the keys to
        snake case. this will work with nested dicts as well
    """

    flatten = flattenObject(d, onlyPathToBaseValue=True)

    ret = ensureDottedAccess({})

    for k, v in flatten.items():
        if adaptStrValues and isinstance(v, str):
            rsetattr(ret, pathToSnakeCase(k), camelToSnake(v))
        else:
            rsetattr(ret, pathToSnakeCase(k), v)

    return ret


def keysToCamel(d: dict, adaptStrValues=False):
    """ helperfunction, which will change the options to
        camel case.
    """
    ret = {}
    for key, value in d.items():
        if adaptStrValues and isinstance(value, str):
            ret[snakeToCamel(key)] = snakeToCamel(value)
        else:
            ret[snakeToCamel(key)] = value

    return ret


def keysToCamelNested(d: dict, adaptStrValues=False):
    """ helperfunction, which will change the options to
        camel case. this will work with nested dicts as well
        (expecting every key contains a dict again.)
    """
    flatten = flattenObject(d, onlyPathToBaseValue=True)

    ret = ensureDottedAccess({})

    for k, v in flatten.items():
        if adaptStrValues and isinstance(v, str):
            rsetattr(ret, pathToCamelCase(k), snakeToCamel(v))
        else:
            rsetattr(ret, pathToCamelCase(k), v)

    return ret


def extractUniqueValues(d, path='', pathKey: str = None):
    """ Extracts the unique values of an map.

    Args:
        d (dict-like): The dict-like object that should be transformed.
        path (str, optional): The path of the attribute of that should be extracted of the value. Defaults to ''.
        pathKey (str, optional):   The Path of the unique key. If set to `None` -> The Item is selected directly.
                                    Defaults to None.

    Returns:
        set: A set containing the unique values.
    """
    if pathKey is None:
        pathKey = path
    if path != pathKey:
        _commonSegment = getLeastCommonPathSegment([path, pathKey], DottedDict(
            {'considerSingleLevel': False, 'considerMultiLevel': False}))

        # Assign the Value
        _commonSegment = _commonSegment if _commonSegment is not False else ""

        # Determine the Length of the common segment, to determine the relative
        # pathes
        _commonSegmentLength = len(_commonSegment.split(
            SPLITCHAR)) if _commonSegment != "" else 0

        _relPathContent = SPLITCHAR.join(
            path.split(SPLITCHAR)[_commonSegmentLength:])
        _relPathKey = SPLITCHAR.join(pathKey.split(SPLITCHAR)[
                                     _commonSegmentLength:])
        _items = extractValues(d, _commonSegment)
        _keysToUse = set()
        ret = []
        for item in _items:
            # Extract key and data:
            key = rgetattr(item, _relPathKey) if _relPathKey else item
            data = rgetattr(item, _relPathContent) if _relPathContent else item
            if key not in _keysToUse:
                # Only if the Key has not been used we are allowed to add
                # the data.
                _keysToUse.add(key)
                if data not in ret:
                    ret.append(data)
        return ret
    return extractValues(d, path, unique=True)


def extractValues(d, path='', unique=False):
    """ Helper to extract values of the map. Therefore the path must be provided.

    Example:
        >> d = {1:{"a": 0}, 2:{"a": 1}}
        >> r = extractValues(d,"a")

        r = [0,1]

    Args:
        d (dict-like): The dict-like object that should be transformed.
        path (str, optional): The path of the attribute of that should be extracted of the value. Defaults to ''.
        unique (bool, optional): Performs a check to extract only unique values.

    Returns:
        list: containing the element.
    """
    s = list()
    for v in d.values():
        if path:
            for item in rqueryAttr(v, path):
                if not unique or (unique and (item.data not in s)):
                    s.append(item.data)
        elif not unique or (unique and (v not in s)):
            s.append(v)
    return s


def transform_dict(d, pathExtractedValue: str,
                   pathExtractedKey: str, logger=None):
    """_summary_

    Args:
        d (_type_): _description_
        pathExtractedValue (str): _description_
        pathExtractedKey (str): _description_

    Returns:
        _type_: _description_
    """

    # Initialize all values:
    keyMapping = dict()
    reverseKeyMapping = dict()
    conflicts = dict()
    extractedDict = dict()
    orgKeyToExtractedValue = dict()
    amountOf = dict()
    props = []
    onlyValidProps = True

    if isinstance(pathExtractedKey, str):
        props.append(DottedDict({'key': 'key', 'query': pathExtractedKey}))
        onlyValidProps = onlyValidProps and (len(pathExtractedKey) > 0)
    else:
        onlyValidProps = False

    if isinstance(pathExtractedValue, str):
        props.append(DottedDict(
            {'key': 'value', 'query': pathExtractedValue}))
        onlyValidProps = onlyValidProps and (len(pathExtractedValue) > 0)
    else:
        onlyValidProps = False

    keyIsHashable = True
    valueIsHashable = True

    __warned = False

    # Iterate over the items of the dict,
    # then we will extract the data stored in the Value.
    for k, v in d.items():
        extracted = []

        if onlyValidProps:
            extracted = convertData(v, props)

            for element in extracted:
                # Try to convert the data:
                try:
                    hash(element.key)
                    element.keyIsHashable = True
                except BaseException:
                    element.keyIsHashable = False
                    keyIsHashable = False

                # Try to convert the data:
                try:
                    hash(element.value)
                    element.valueIsHashable = True
                except BaseException:
                    element.valueIsHashable = False
                    valueIsHashable = False

        else:

            data = DottedDict({
                'key': None,
                'value': None,
                'keyIsHashable': True,
                'valueIsHashable': True
            })

            # We migt adapt the key and the Value. Therefore we will use
            # the next if statements

            if isinstance(pathExtractedKey, str):
                if len(pathExtractedKey) > 0:
                    data.key = rgetattr(v, pathExtractedKey)
                else:
                    data.key = v
            else:
                data.key = k

            if isinstance(pathExtractedValue, str):
                if len(pathExtractedValue) > 0:
                    data.value = rgetattr(v, pathExtractedValue)
                else:
                    data.value = v
            else:
                data.value = v

            # Try to convert the data:
            try:
                hash(data.key)
            except BaseException:
                data.keyIsHashable = False
                keyIsHashable = False

            # Try to convert the data:
            try:
                hash(data.value)
            except BaseException:
                data.valueIsHashable = False
                valueIsHashable = False

            extracted.append(data)

        # Create the entries for the following dicts.
        keyMapping[k] = set()
        orgKeyToExtractedValue[k] = set() if valueIsHashable else list()

        for item in extracted:

            if not item.keyIsHashable:
                error = Exception(
                    f"Can not hash the new key='{item.key}' (type={type(item.key)}) from path='{pathExtractedKey}'")

                if logger:
                    logger.error(error)
                else:
                    print(formatException(error))

                raise error

            if item.key in extractedDict:
                # If the extracted new key has already been defined,
                # we have to determine whether the stored item matches
                # the allready provided definition.
                if not (extractedDict.get(item.key) == item.value):
                    # Conflict detected -> Store it

                    if item.key not in conflicts:
                        conflicts[item.key] = set(
                        ) if valueIsHashable else list()

                    getattr(conflicts.get(item.key),
                            "add" if valueIsHashable else "append")(item.value)
                    getattr(conflicts.get(item.key), "add" if valueIsHashable else "append")(
                        extractedDict.get(item.key))
                else:
                    # No conflict -> just store the amount
                    amountOf[item.key] = amountOf.get(item.key, 0) + 1
            else:
                # Store the item and amount
                extractedDict[item.key] = item.value
                amountOf[item.key] = amountOf.get(item.key, 0) + 1

            #  If the reverse haven't been set ==> create it.
            if not (item.key in reverseKeyMapping):
                reverseKeyMapping[item.key] = set()

            # Store the mapping of new-key --> org-key.
            reverseKeyMapping[item.key].add(k)

            # Store the mapping of org-key --> new-key.
            keyMapping[k].add(item.key)

            # Now store the item.
            getattr(orgKeyToExtractedValue[k], "add" if valueIsHashable else "append")(
                item.value)

    return DottedDict({
        'extracted_map': extractedDict,
        'keyMapping': keyMapping,
        'conflicts': conflicts,
        'keyMappingreverse': reverseKeyMapping,
        'orgKeyToExtractedValue': orgKeyToExtractedValue,
        'amountOf': amountOf
    })


def reverse(d, path='', pathKey: str = None):
    """ Reverses the given map.

        If the path is provided, the Data is extracted based on the given path.
        If the `pathKey`, a different Key is used.

    Args:
        d (dict): The dict used as source.
        path (str, optional): The path for the attributes in the value. Defaults to ''.
        pathKey (str, optional): The path of the key, which will be provided in the `value`. Defaults to None.

    Returns:
        dict: The reversed Dict.
    """
    ret = dict()
    if pathKey is None:
        pathKey = path
    for k, v in d.items():
        keyToUse = k

        if pathKey:
            keyToUse = rgetattr(v, pathKey, __SENTINENTAL)
        valueToUse = v
        if path:
            valueToUse = rgetattr(v, path, __SENTINENTAL)
        if isinstance(valueToUse, Iterable):
            for _v in valueToUse:
                if _v not in ret:
                    ret[_v] = set()
                ret.get(_v).add(keyToUse)
        else:
            if valueToUse not in ret:
                ret[valueToUse] = set()
            ret.get(valueToUse).add(keyToUse)
    return ret
