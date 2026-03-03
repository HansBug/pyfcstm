"""
Utilities for generating safe, underscore-based sequence identifiers.

This module provides a small helper for converting sequences of string segments
into a consistent, safe identifier format. Each segment is normalized to
underscore style and excessive consecutive underscores are collapsed, then the
segments are joined by double underscores. This is particularly useful when
building stable names from mixed naming conventions such as CamelCase,
snake_case, kebab-case, or free-form strings.

The module contains the following main components:

* :func:`sequence_safe` - Normalize and join string segments into a safe identifier.

Example::

    >>> from pyfcstm.utils.safe import sequence_safe
    >>> sequence_safe(['CamelCase', 'snake_case', 'kebab-case'])
    'camel_case__snake_case__kebab_case'
"""

import re
from typing import Iterable

from hbutils.string import underscore


def sequence_safe(segments: Iterable[str]) -> str:
    """
    Convert a sequence of strings into a safe underscore-separated identifier.

    Each input segment is transformed into underscore style using
    :func:`hbutils.string.underscore`, multiple consecutive underscores are
    collapsed to a single underscore, and all segments are joined by a double
    underscore separator (``"__"``). The resulting identifier is stable and
    suitable for consistent naming.

    :param segments: Sequence of string segments to be normalized and joined.
    :type segments: Iterable[str]
    :return: A safe underscore-separated identifier.
    :rtype: str

    Example::

        >>> sequence_safe(['CamelCase', 'snake_case', 'kebab-case'])
        'camel_case__snake_case__kebab_case'
        >>> sequence_safe(['Hello World', 'Test___String'])
        'hello_world__test_string'
    """
    return '__'.join(map(lambda x: re.sub(r'_+', '_', underscore(x)), segments))
