"""
String normalization utilities for converting arbitrary strings to valid identifiers.

This module provides helper functions to normalize strings into valid identifier
formats that can be used in programming contexts. It converts non-ASCII
characters using transliteration, replaces invalid characters with underscores,
and optionally enforces identifier rules such as not starting with a digit.

The module contains the following main components:

* :func:`normalize` - Convenience wrapper for non-strict identifier conversion
* :func:`to_identifier` - Full identifier conversion with strict mode support

Example::

    >>> from pyfcstm.utils.text import normalize, to_identifier
    >>> normalize("Hello World!")
    'Hello_World'
    >>> to_identifier("123 Test", strict_mode=True)
    '_123_Test'
"""

from unidecode import unidecode


def normalize(input_string: str) -> str:
    """
    Normalize a string to a valid identifier format.

    This is a convenience wrapper around :func:`to_identifier` with
    ``strict_mode`` set to ``False``. It replaces non-alphanumeric
    characters with underscores while allowing identifiers to start
    with digits and allowing empty input to return an empty string.

    :param input_string: The string to be normalized
    :type input_string: str
    :return: A normalized identifier string
    :rtype: str
    :raises TypeError: If ``input_string`` is not a string

    Example::

        >>> normalize("Hello World!")
        'Hello_World'
        >>> normalize("123 Test")
        '123_Test'
    """
    return to_identifier(input_string, strict_mode=False)


def to_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert any string to a valid identifier format ``[0-9a-zA-Z_]+``.

    Rules:

    1. Preserve all letters and numbers after transliteration
    2. Convert spaces and special characters to underscores
    3. If ``strict_mode`` is ``True``, ensure the first character is not a number
    4. If ``strict_mode`` is ``True``, handle empty strings by returning ``"_empty"``
    5. Avoid multiple consecutive underscores by collapsing them

    :param input_string: The string to be converted
    :type input_string: str
    :param strict_mode: When ``True``, applies additional rules to ensure
                        identifier validity across most languages. When
                        ``False``, allows empty strings and identifiers
                        starting with numbers.
    :type strict_mode: bool, optional
    :return: A valid identifier string
    :rtype: str
    :raises TypeError: If ``input_string`` is not a string

    Example::

        >>> to_identifier("Hello World!", strict_mode=True)
        'Hello_World'
        >>> to_identifier("123 Test", strict_mode=True)
        '_123_Test'
        >>> to_identifier("", strict_mode=True)
        '_empty'
    """
    input_string = unidecode(input_string)
    # Initialize result string
    result = ""

    # Process each character
    prev_is_underscore = False
    for char in input_string:
        if char.isalnum():  # If it's a letter or number
            result += char
            prev_is_underscore = False
        else:  # If it's another character
            if not prev_is_underscore:  # Avoid consecutive underscores
                result += "_"
                prev_is_underscore = True

    # Remove trailing underscore if present
    result = result.rstrip("_")

    # Apply strict mode rules if enabled
    if strict_mode:
        # Ensure it's not an empty string
        if not result:
            return "_empty"

        # Ensure the first character is not a digit
        if result and result[0].isdigit():
            result = "_" + result

    return result
