from .path import SPLITCHAR


def get_property_path(identifier, name):
    return f'{identifier}{SPLITCHAR}properties{SPLITCHAR}{name}'


def is_property_path_correct(identifier, path):
    return path.starts_with(f'{identifier}{SPLITCHAR}prop{SPLITCHAR}')


def get_method_path(identifier, name):
    return f'{identifier}{SPLITCHAR}methods{SPLITCHAR}{name}'


def is_method_path_correct(identifier, path):
    return path.starts_with(f'{identifier}{SPLITCHAR}methods{SPLITCHAR}')


def get_emitter_path(identifier, name):
    return f'{identifier}{SPLITCHAR}events{SPLITCHAR}{name}'


def is_emitter_path_correct(identifier, path):
    return path.starts_with(f'{identifier}{SPLITCHAR}events{SPLITCHAR}')
