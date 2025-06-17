"""
String normalization utilities for converting arbitrary strings to valid identifiers.

This module provides functions to normalize strings into valid identifier formats
that can be used in programming contexts. It handles special characters, spaces,
and ensures compliance with identifier naming rules.
"""

from unidecode import unidecode


def normalize(input_string):
    """
    Normalize a string to a valid identifier format.

    This is a convenience wrapper around to_identifier() with strict_mode set to False.

    :param input_string: The string to be normalized
    :type input_string: str

    :return: A normalized identifier string
    :rtype: str

    Example::

        >>> normalize("Hello World!")
        'Hello_World'
        >>> normalize("123 Test")
        '123_Test'
    """
    return to_identifier(input_string, strict_mode=False)


def to_identifier(input_string, strict_mode: bool = True):
    """
    Convert any string to a valid identifier format [0-9a-zA-Z_]+

    Rules:
    1. Preserve all letters and numbers
    2. Convert spaces and special characters to underscores
    3. If strict_mode is True, ensure the first character is not a number (as identifiers typically cannot start with a number)
    4. If strict_mode is True, handle empty strings and None inputs
    5. Handle consecutive special characters to avoid multiple consecutive underscores

    :param input_string: The string to be converted
    :type input_string: str
    :param strict_mode: When True, applies additional rules to ensure identifier validity across most languages.
                        When False, allows empty strings and identifiers starting with numbers
    :type strict_mode: bool, optional

    :return: A valid identifier string
    :rtype: str

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
