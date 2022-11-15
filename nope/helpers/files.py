import os
import pathlib


def createFile(path: str, with_file=True):
    """ Helper to create a path to a file.

    Args:
        path (str): The Path with or without a file.
        with_file (bool, optional): If the file is contained the Flag must be set to true. Defaults to True.
    """

    sep = os.sep
    abs_path = pathlib.Path(path).absolute()
    if not abs_path.exists():

        if with_file:
            abs_path_as_str = str(abs_path)
            path_segments = abs_path_as_str.split(sep)

            if len(path_segments) > 0:
                pathlib.Path(
                    sep.join(path_segments[:-1])).mkdir(parents=True, exist_ok=True)

            abs_path.touch(exist_ok=True)

        else:

            abs_path.mkdir(parents=True, exist_ok=True)

    return str(abs_path)
