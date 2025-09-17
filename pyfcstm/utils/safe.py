"""
Utility module for creating safe sequence identifiers.

This module provides functionality to convert sequences of strings into safe, 
underscore-separated identifiers. It's particularly useful for generating 
consistent naming conventions from potentially inconsistent input strings.
"""

import re
from collections.abc import Sequence

from hbutils.string import underscore


def sequence_safe(segments: Sequence[str]) -> str:
    """
    Convert a sequence of strings into a safe underscore-separated identifier.

    This function takes a sequence of strings, converts each to underscore format,
    normalizes multiple consecutive underscores to single underscores, and joins
    them with double underscores ('__'). This is useful for creating consistent
    identifiers from potentially inconsistent input strings.

    :param segments: A sequence of strings to be converted into a safe identifier.
    :type segments: Sequence[str]

    :return: A safe underscore-separated identifier string.
    :rtype: str

    Example::
        >>> sequence_safe(['CamelCase', 'snake_case', 'kebab-case'])
        'camel_case__snake_case__kebab_case'
        >>> sequence_safe(['Hello World', 'Test___String'])
        'hello_world__test_string'
    """
    return '__'.join(map(lambda x: re.sub(r'_+', '_', underscore(x)), segments))
