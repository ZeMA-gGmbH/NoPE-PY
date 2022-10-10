import math
import re
from typing import Union

from .dottedDict import DottedDict

pattern = re.compile(r'(?<!^)(?=[A-Z])')


def snakeToCamel(input: str) -> str:
    """Converts the given snake-case to camel-case
    """
    # split underscore using split
    temp = input.split('_')

    # joining result
    res = temp[0] + ''.join(ele.title() for ele in temp[1:])

    # Return the Result
    return res


def camelToSnake(input: str) -> str:
    """Converts the given camel case to snake-case
    """
    return pattern.sub('_', input).lower()


def replaceAll(org_str: str, value, replacement: str) -> str:
    """ Replaces all Chars in a String

    Args:
        org_str (str): base string
        value (str): the value which should be replaced, Or an array containing the value and replacer
        replacement (str): the value which is used as replacement

    Returns:
        str: The adapted Place
    """

    ret: str = org_str

    if isinstance(value, str) and (replacement is not None):
        ret = ret.replace(value, replacement)
    else:
        for pair in value:
            if isinstance(pair, str) and (replacement is not None):
                ret = ret.replace(pair, replacement)
            else:
                ret = ret.replace(pair[0], pair[1])

    return ret


def pad_string(num: Union[float, int], size: int, max_length=False):
    """ Function to Pad a String.

    Args:
        num (Union[float,int]): number
        size (int): Max pad-size or max number
        max_length (bool, optional): Flat must be set to true, if the size is the max value. Defaults to False.

    Returns:
        str: the Number as String
    """
    size = size
    if isinstance(max_length, bool) and max_length:
        size = math.ceil(math.log10(size))
    s = str(num)
    while len(s) < size:
        s = '0' + s
    return s


def insert(str: str, index: int, content: str) -> str:
    """ Inserts a String in the String
    """
    if index > 0:
        return str[0, index] + content + str[index, len(str)]
    else:
        return content + str


def to_camel_case(str: str, char='_') -> str:

    def callback_0(word, index):
        return word.to_lower_case() if index == 0 else word.to_upper_case()

    return replaceAll(str, char, ' ').replace(re.compile(
        '(?:^\\w|[A-Z]|\\b\\w)'), callback_0).replace(
        re.compile('\\s+'), '')


def to_snake_case(str: str) -> str:
    """ Helper to convert the string to the snake-case

    Args:
        str (str): The string to convert

    Returns:
        str: The converted string
    """
    if str == str.upper():
        return str

    ret = ''.join(['_' + i.lower() if i.isupper()
                   else i for i in str]).lstrip('_')

    if ret.startswith("_"):
        ret[1:]

    return ret


def limit_string(str: str, length: int,
                 limit_chars: str = '...') -> DottedDict:
    """ Helper to limit the string to a specific length. the rest is reduced by the limitChars

    Args:
        str (str): The string to work with
        length (int): The max length including the limitChars
        limit_chars (str, optional): The chars which should be used to express limiting. Defaults to '...'.

    Returns:
        dotted_dict: dict containing the following keys 'isLimited', 'original', 'limited'
    """
    if len(str) > length:
        return DottedDict({
            'isLimited': True,
            'original': str,
            'limited': str[0, length - len(limit_chars)] + limit_chars
        })
    else:
        return DottedDict({
            'isLimited': False,
            'original': str,
            'limited': str
        })


def insert_new_lines(str: str, max_length: int = 100) -> str:
    """ Helper to insert new lines after a given amount of time.

    Args:
        str (str): The String to work with
        max_length (int, optional): The Max-Lenght of the string, after which a new-line symbole has to be inserted. Defaults to 100.

    Returns:
        str: The adapted string.
    """

    splitted = str.split(' ')
    ret = []
    length = 0
    for word in splitted:

        length = length + len(word) + 1

        ret.append(word)

        if length > max_length:
            ret.append('\\n')
            length = 0

    return ret
