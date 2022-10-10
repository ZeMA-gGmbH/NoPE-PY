from .dotted_dict import ensureDottedAccess, DottedDict
from .path import (MULTI_LEVEL_WILDCARD, SINGLE_LEVEL_WILDCARD, SPLITCHAR,
                   containsWildcards, patternIsValid)


def generateResult(res=DottedDict({})):
    """ internal helper to generate the defined result.

    Args:
        res (dotted_dict, optional): The Result. Defaults to dotted_dict({}).

    Returns:
        dotted_dict: The Result
    """
    defaultResult = DottedDict({
        'affected': False,
        'affectedByChild': False,
        'affectedByParent': False,
        'affectedOnSameLevel': False,
        'containsWildcards': False,
        'patternToExtractData': False,
        'patternLengthComparedToPathLength': '=',
        'pathToExtractData': False
    })

    defaultResult.update(res)
    defaultResult.affected = defaultResult.affectedByChild or defaultResult.affectedByParent or defaultResult.affectedOnSameLevel

    return defaultResult


def comparePatternAndPath(pathPattern: str, contentPath: str, _options=None):
    """ Matches the given path, with the pattern and determines, if the path might affect the given pattern.

        example: path = "a/b/c"; pattern = "a/#"; => totalPath = "a/b/c"; diffPath = "b/c"

    Args:
        pathPattern (str): The pattern to test
        contentPath (str): The path to use as basis
        options (dotted_dict, optional): _description_. Defaults to dotted_dict({'matchTopicsWithoutWildcards': False}).

    Returns:
        dotted_dict: The Result
    """
    options = ensureDottedAccess({'matchTopicsWithoutWildcards': False})
    options.update(ensureDottedAccess(_options))

    if containsWildcards(contentPath):
        raise Exception(
            "The Path is invalid. The path should not contain pattern-related chars '#' or '+'.")
    if not patternIsValid(pathPattern):
        raise Exception('The Pattern is invalid.')
    if not patternIsValid(contentPath):
        raise Exception('The Path is invalid.')

    _containsWildcards = containsWildcards(pathPattern)
    _patternSegments = pathPattern.split(SPLITCHAR)
    _contentPathSegments = contentPath.split(SPLITCHAR)
    _patternLength = len(_patternSegments)
    _contentPathLength = len(_contentPathSegments)

    # Define the Char for the comparer
    patternLengthComparedToPathLength = '='
    if _patternLength > _contentPathLength:
        patternLengthComparedToPathLength = '>'
    elif _patternLength < _contentPathLength:
        patternLengthComparedToPathLength = '<'

    # If both, the pattern and the path are equal => return the result.
    if pathPattern == contentPath:
        return generateResult(
            DottedDict(
                {
                    'affectedOnSameLevel': True,
                    'pathToExtractData': contentPath,
                    'patternLengthComparedToPathLength': patternLengthComparedToPathLength
                }
            )
        )

    # If the Path is not realy defined.
    if contentPath == '':
        return generateResult(
            DottedDict({
                'affectedByParent': True,
                'patternToExtractData': pathPattern if _containsWildcards else False,
                'pathToExtractData': False if _containsWildcards else pathPattern,
                'patternLengthComparedToPathLength': '>',
                'containsWildcards': _containsWildcards
            })
        )
    if pathPattern == '':
        return generateResult(
            DottedDict({
                'affectedByChild': True,
                'pathToExtractData': '',
                'patternLengthComparedToPathLength': '<'
            })
        )
    if options.matchTopicsWithoutWildcards:
        if contentPath.startswith(pathPattern):
            # Path is longer then the Pattern;
            # => A Change is performed by "Child",
            if _containsWildcards:
                return generateResult(
                    DottedDict({
                        'affectedByChild': True,
                        'pathToExtractData': contentPath,
                        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                        'containsWildcards': _containsWildcards
                    })
                )
            else:
                return generateResult(
                    DottedDict({
                        'affectedByChild': True,
                        'pathToExtractData': pathPattern,
                        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                        'containsWildcards': _containsWildcards
                    })
                )
        elif pathPattern.startswith(contentPath):
            # Pattern is longer then the path;
            # => A Change might be initated by
            # the super element

            # The PathToExtractData is allways false, if the path is smaller then the
            # pattern

            if _containsWildcards:
                return generateResult(
                    DottedDict({
                        'affectedByParent': True,
                        'patternToExtractData': pathPattern,
                        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                        'containsWildcards': _containsWildcards
                    })
                )
            else:
                return generateResult(
                    DottedDict({
                        'affectedByParent': True,
                        'pathToExtractData': pathPattern,
                        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                        'containsWildcards': _containsWildcards
                    })
                )

    partialPath = ''
    i = 0

    # Iterate over the Segments.
    while i < _patternLength:
        # Store the current Pattern Segment
        currentPattern = _patternSegments[i]

        # We need to know, if there is SINGLE_LEVEL_WILDCARD or MULTI_LEVEL_WILDCARD
        # there fore we will extract the Wildlevels.
        patternChar = currentPattern[0]
        currentPath = _contentPathSegments[i] if i < _contentPathLength else None
        i = i + 1
        if currentPath is None:
            # Our Pattern is larger then our contentPath.
            # So we dont know, whether we will get some
            # data. Therefore we have to perform a query
            # later ==> Set The Path / Pattern.

            if _containsWildcards:
                # But we contain Patterns.
                # So we are not allowed to build a
                # diff object.
                return generateResult(
                    DottedDict({
                        'affectedByParent': True,
                        'patternToExtractData': pathPattern,
                        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                        'containsWildcards': _containsWildcards
                    })
                )
            else:
                raise Exception('Implementation Error! This should not happen')
        elif currentPath == currentPattern:
            # The Patterns Match
            # We now store the correct path of our segment.
            partialPath = f'{partialPath}{SPLITCHAR}{currentPath}' if len(
                partialPath) > 0 else currentPath
        elif patternChar == MULTI_LEVEL_WILDCARD:

            # We know, that MULTI_LEVEL_WILDCARDs are only at the end of the
            # pattern. So it might happen, that:
            # a)   our length of the pattern is the same length as the content path
            # b)   our length of the pattern is smaller then length as the content path
            #
            # Our statement before alread tested, that either case a) or b) fits. Otherwise
            # another ifstatement is valid and we wont enter this statement
            # here.

            # # We add the segment to testedCorrectPath
            # testedCorrectPath = testedCorrectPath.length > 0 ?
            # `{testedCorrectPath}{SPLITCHAR}{currentPath}` : currentPath;

            if patternLengthComparedToPathLength == '=':
                # Case a)
                return generateResult(
                    DottedDict(
                        {
                            'affectedOnSameLevel': True,
                            'pathToExtractData': contentPath,
                            'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                            'containsWildcards': _containsWildcards
                        }
                    )
                )
            elif patternLengthComparedToPathLength == '<':
                # Case b)
                return generateResult(DottedDict(
                    {
                        'affectedByChild': True,
                        'pathToExtractData': contentPath,
                        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                        'containsWildcards': _containsWildcards
                    }
                ))
            else:
                raise Exception('Implementation Error!')
        elif patternChar == SINGLE_LEVEL_WILDCARD:
            # Store the correct path.
            partialPath = f'{partialPath}{SPLITCHAR}{currentPath}' if len(
                partialPath) > 0 else currentPath
        elif patternChar != SINGLE_LEVEL_WILDCARD and currentPattern != currentPath:
            return generateResult(DottedDict({
                'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
                'containsWildcards': _containsWildcards
            }))
    diff = contentPath[len(partialPath):]
    return generateResult(DottedDict({
        'affectedOnSameLevel': len(diff) == 0,
        'affectedByChild': len(diff) > 1,
        'pathToExtractData': partialPath,
        'patternLengthComparedToPathLength': patternLengthComparedToPathLength,
        'containsWildcards': _containsWildcards
    }))
