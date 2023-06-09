from .path import SPLITCHAR


def getPropertyPath(identifier, name):
    return f'{identifier}{SPLITCHAR}properties{SPLITCHAR}{name}'


def isPropertyPathCorrect(identifier, path):
    return path.startswith(f'{identifier}{SPLITCHAR}properties{SPLITCHAR}')


def getMethodPath(identifier, name):
    return f'{identifier}{SPLITCHAR}methods{SPLITCHAR}{name}'


def isMethodPathCorrect(identifier, path):
    return path.startswith(f'{identifier}{SPLITCHAR}methods{SPLITCHAR}')


def getEmitterPath(identifier, name):
    return f'{identifier}{SPLITCHAR}events{SPLITCHAR}{name}'


def isEmitterPathCorrect(identifier, path):
    return path.startswith(f'{identifier}{SPLITCHAR}events{SPLITCHAR}')
