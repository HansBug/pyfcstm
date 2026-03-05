"""
String value parsing utilities for CLI option handling.

This module provides utilities for parsing string values from command-line options
into appropriate Python types. It supports automatic type inference and explicit
type hints for robust CLI argument parsing.

The main public components are:

* :func:`parse_value` - Parse a string value to appropriate Python type
* :func:`parse_key_value_pairs` - Parse multiple key=value pairs into a dictionary

Supported types:

* Primitive types: ``None``, ``bool``, ``int``, ``float``, ``str``, ``auto``
* Container types: ``tuple[T, ...]`` (variable length), ``tuple[T1, T2, ...]`` (fixed length)
* Optional types: ``optional`` (equivalent to ``optional[auto]``), ``optional[T]``

Example::

    >>> from pyfcstm.utils.parse import parse_value, parse_key_value_pairs
    >>>
    >>> # Auto mode - infer type from value
    >>> parse_value('42')
    42
    >>> parse_value('true')
    True
    >>> parse_value('"hello world"')
    'hello world'
    >>>
    >>> # Explicit type hints
    >>> parse_value('42', 'int')
    42
    >>> parse_value('name,path', 'tuple[str, ...]')
    ('name', 'path')
    >>>
    >>> # Optional types
    >>> parse_value('none', 'optional[str]')
    None
    >>> parse_value('hello', 'optional[str]')
    'hello'
    >>> parse_value('42', 'optional')
    42
    >>>
    >>> # Parse multiple options
    >>> parse_key_value_pairs(
    ...     ('show_events=true', 'max_depth=2', 'format=name,path'),
    ...     type_hints={'format': 'tuple[str, ...]', 'max_depth': 'int'}
    ... )
    {'show_events': True, 'max_depth': 2, 'format': ('name', 'path')}
"""

import codecs
from typing import Any, Dict, Optional, Tuple, Union

__all__ = [
    'parse_value',
    'parse_key_value_pairs',
]


def parse_value(
    value_str: str,
    expected_type: Union[type, str, None] = 'auto'
) -> Any:
    """
    Parse a string value to appropriate Python type.

    Supports: None, bool, int, float, str, auto, tuple, and optional types.

    Type Inference (Auto Mode)
    ---------------------------

    When ``expected_type`` is ``'auto'`` (default), the function attempts to infer
    the type using the following priority:

    1. **int**: Try parsing as integer (e.g., ``'42'`` → ``42``)
    2. **float**: Try parsing as float (e.g., ``'3.14'`` → ``3.14``)
    3. **str (quoted)**: Check for quoted strings with escape sequences (e.g., ``'"hello\\nworld"'`` → ``'hello\\nworld'``)
    4. **None**: Check for ``'none'`` or ``'null'`` (case-insensitive)
    5. **bool**: Check for ``'true'``/``'yes'`` or ``'false'``/``'no'`` (case-insensitive)
    6. **str (unquoted)**: Default to string for everything else

    Explicit Type Hints
    --------------------

    When ``expected_type`` is specified, the value is parsed according to that type:

    * **Primitive types**: Pass the type directly (``int``, ``float``, ``str``, ``bool``, ``None``, ``type(None)``)
      or as string (``'int'``, ``'float'``, ``'str'``, ``'bool'``, ``'none'``, ``'auto'``)
    * **Tuple types**: Use string notation:

      * ``'tuple[str, ...]'`` - Variable length tuple with single element type
      * ``'tuple[str, int]'`` - Fixed length tuple with specific types for each element
      * ``'tuple[auto, ...]'`` - Variable length tuple with auto type inference for each element

    * **Optional types**: Use string notation:

      * ``'optional'`` - Equivalent to ``'optional[auto]'``, tries the specified type first, then None
      * ``'optional[str]'`` - Tries to parse as string first, then None if value is 'none'/'null'
      * ``'optional[int]'`` - Tries to parse as int first, then None if value is 'none'/'null'

    String Handling
    ---------------

    * **Quoted strings**: Strings enclosed in single or double quotes have the quotes removed
      and escape sequences processed (``\\n``, ``\\t``, ``\\r``, ``\\\\``, ``\\'``, ``\\"``, etc.)
    * **Unquoted strings**: Used as-is when type is ``str`` or in auto mode as fallback

    :param value_str: String value to parse
    :type value_str: str
    :param expected_type: Expected type or ``'auto'`` for automatic inference (default).
        Can be a type (``int``, ``float``, ``str``, ``bool``, ``None``, ``type(None)``),
        a string representation (``'int'``, ``'float'``, ``'str'``, ``'bool'``, ``'none'``, ``'auto'``,
        ``'tuple[str, ...]'``, ``'tuple[auto, ...]'``, ``'optional'``, ``'optional[str]'``), or ``'auto'``.
    :type expected_type: Union[type, str, None]
    :return: Parsed value with appropriate type
    :rtype: Any
    :raises ValueError: If the value cannot be parsed as the expected type

    Example::

        >>> # Auto mode - type inference
        >>> parse_value('42')
        42
        >>> parse_value('3.14')
        3.14
        >>> parse_value('true')
        True
        >>> parse_value('none')
        None
        >>> parse_value('hello')
        'hello'
        >>> parse_value('"hello world"')
        'hello world'
        >>> parse_value('"hello\\nworld"')
        'hello\\nworld'
        >>>
        >>> # Explicit type hints (type objects)
        >>> parse_value('42', int)
        42
        >>> parse_value('true', bool)
        True
        >>> parse_value('none', None)
        None
        >>> parse_value('none', type(None))
        None
        >>> parse_value('"hello world"', str)
        'hello world'
        >>>
        >>> # Explicit type hints (string representations)
        >>> parse_value('42', 'int')
        42
        >>> parse_value('3.14', 'float')
        3.14
        >>> parse_value('true', 'bool')
        True
        >>> parse_value('none', 'none')
        None
        >>> parse_value('hello', 'str')
        'hello'
        >>>
        >>> # Tuple types
        >>> parse_value('name,path', 'tuple[str, ...]')
        ('name', 'path')
        >>> parse_value('name,42', 'tuple[str, int]')
        ('name', 42)
        >>> parse_value('a,b,c', 'tuple[str, ...]')
        ('a', 'b', 'c')
    """
    # Handle None type (both None and type(None) are equivalent)
    if expected_type is None or expected_type is type(None):
        if value_str.lower() in ('none', 'null'):
            return None
        raise ValueError(f"Expected None, got: {value_str}")

    if isinstance(expected_type, str) and expected_type.lower() == 'none':
        if value_str.lower() in ('none', 'null'):
            return None
        raise ValueError(f"Expected None, got: {value_str}")

    # Handle optional types
    if isinstance(expected_type, str) and expected_type.lower().startswith('optional'):
        # Check if value is None first
        if value_str.lower() in ('none', 'null'):
            return None

        # Parse optional type specification
        if expected_type.lower() == 'optional':
            # optional without type parameter is equivalent to optional[auto]
            inner_type = 'auto'
        else:
            # Extract inner type from optional[T]
            inner = expected_type[9:-1]  # Remove 'optional[' and ']'
            inner_type = inner.strip()

        # Try to parse with the inner type
        try:
            return parse_value(value_str, inner_type)
        except ValueError:
            # If parsing fails and value is not 'none'/'null', re-raise
            raise

    # Handle tuple types
    if isinstance(expected_type, str) and expected_type.startswith('tuple['):
        # Parse tuple type specification
        inner = expected_type[6:-1].strip()  # Remove 'tuple[' and ']' and strip whitespace

        # Check if it's a variable length tuple (ends with '...')
        # Strip whitespace around commas to be completely insensitive
        inner_normalized = inner.replace(' ', '')
        if inner_normalized.endswith(',...'):
            # Variable length tuple with single element type
            # Extract element type before ', ...' or ',...'
            if ', ...' in inner:
                element_type_str = inner.rsplit(', ...', 1)[0].strip()
            else:
                element_type_str = inner_normalized.rsplit(',...', 1)[0].strip()

            # Support 'auto' in tuple element types
            if element_type_str.lower() == 'auto':
                element_type = 'auto'
            else:
                element_type = _parse_type_string(element_type_str)
            parts = value_str.split(',')
            return tuple(parse_value(part.strip(), element_type) for part in parts)
        else:
            # Fixed length tuple with specific types
            element_types_str = [t.strip() for t in inner.split(',')]
            # Support 'auto' in tuple element types
            element_types = []
            for t in element_types_str:
                if t.lower() == 'auto':
                    element_types.append('auto')
                else:
                    element_types.append(_parse_type_string(t))
            parts = value_str.split(',')

            if len(parts) != len(element_types):
                raise ValueError(
                    f"Expected {len(element_types)} elements for {expected_type}, got {len(parts)}"
                )

            return tuple(
                parse_value(part.strip(), elem_type)
                for part, elem_type in zip(parts, element_types)
            )

    # Handle specific type
    if expected_type != 'auto':
        if isinstance(expected_type, str):
            expected_type = _parse_type_string(expected_type)
        return _parse_single_value(value_str, expected_type)

    # Auto mode: try to infer type
    # Priority: int -> float -> quoted string -> bool/none -> unquoted string

    # Try int
    try:
        return int(value_str)
    except ValueError:
        pass

    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Check for quoted strings
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return _decode_string(value_str[1:-1])

    # Check for None
    if value_str.lower() in ('none', 'null'):
        return None

    # Check for bool
    if value_str.lower() in ('true', 'yes'):
        return True
    if value_str.lower() in ('false', 'no'):
        return False

    # Default to string
    return value_str


def _decode_string(s: str) -> str:
    """
    Decode escape sequences in a string.

    Supports all Python escape sequences: \\n, \\t, \\r, \\\\, \\', \\", \\xhh, \\uhhhh, \\Uhhhhhhhh, etc.

    :param s: String with potential escape sequences
    :type s: str
    :return: Decoded string
    :rtype: str
    """
    try:
        # Use Python's built-in codec to decode escape sequences
        return codecs.decode(s, 'unicode_escape')
    except Exception:
        # If decoding fails, return as-is
        return s


def _parse_type_string(type_str: str) -> Union[type, str]:
    """
    Parse a type string to a Python type or special string.

    :param type_str: Type string like 'int', 'float', 'str', 'bool', 'none', 'auto'
    :type type_str: str
    :return: Python type or 'auto' string
    :rtype: Union[type, str]
    :raises ValueError: If the type string is not recognized
    """
    type_map = {
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'none': type(None),
        'auto': 'auto',
    }
    type_str_lower = type_str.lower()
    if type_str_lower not in type_map:
        raise ValueError(f"Unknown type: {type_str}")
    return type_map[type_str_lower]


def _parse_single_value(value_str: str, expected_type: Union[type, str]) -> Any:
    """
    Parse a single value with a specific expected type.

    :param value_str: String value to parse
    :type value_str: str
    :param expected_type: Expected Python type or 'auto'
    :type expected_type: Union[type, str]
    :return: Parsed value
    :rtype: Any
    :raises ValueError: If the value cannot be parsed as the expected type
    """
    # Handle 'auto' type - use auto mode inference
    if expected_type == 'auto':
        return parse_value(value_str, 'auto')

    # Handle None
    if expected_type is type(None):
        if value_str.lower() in ('none', 'null'):
            return None
        raise ValueError(f"Expected None, got: {value_str}")

    # Handle bool
    if expected_type is bool:
        if value_str.lower() in ('true', 'yes', '1'):
            return True
        if value_str.lower() in ('false', 'no', '0'):
            return False
        raise ValueError(f"Expected bool, got: {value_str}")

    # Handle str with quote removal and escape sequence decoding
    if expected_type is str:
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return _decode_string(value_str[1:-1])
        return value_str

    # Handle int
    if expected_type is int:
        try:
            return int(value_str)
        except ValueError:
            raise ValueError(f"Expected int, got: {value_str}")

    # Handle float
    if expected_type is float:
        try:
            return float(value_str)
        except ValueError:
            raise ValueError(f"Expected float, got: {value_str}")

    raise ValueError(f"Unsupported type: {expected_type}")


def parse_key_value_pairs(
    option_pairs: Tuple[str, ...],
    type_hints: Optional[Dict[str, Union[type, str]]] = None
) -> Dict[str, Any]:
    """
    Parse multiple key=value pairs into a dictionary.

    Each pair must be in the format ``'key=value'``. Values are parsed according to
    the type hints provided in ``type_hints``. If a key is not in ``type_hints``,
    its value is parsed in auto mode (type inference).

    :param option_pairs: Tuple of 'key=value' strings
    :type option_pairs: Tuple[str, ...]
    :param type_hints: Optional dictionary mapping field names to expected types.
        If a field is not in type_hints, it will be parsed with 'auto' mode.
        Type hints can be Python types (``int``, ``float``, ``str``, ``bool``, ``None``, ``type(None)``)
        or string representations (``'int'``, ``'float'``, ``'str'``, ``'bool'``, ``'none'``,
        ``'tuple[str, ...]'``, ``'tuple[str, int]'``).
    :type type_hints: Optional[Dict[str, Union[type, str]]]
    :return: Dictionary of parsed options
    :rtype: Dict[str, Any]
    :raises ValueError: If a pair is not in 'key=value' format or parsing fails

    Example::

        >>> # Auto mode for all fields
        >>> parse_key_value_pairs(('show_events=true', 'max_depth=2'))
        {'show_events': True, 'max_depth': 2}
        >>>
        >>> # With type hints (type objects)
        >>> parse_key_value_pairs(
        ...     ('state_name_format=name,path', 'max_depth=2', 'enabled=true'),
        ...     type_hints={'state_name_format': 'tuple[str, ...]', 'max_depth': int}
        ... )
        {'state_name_format': ('name', 'path'), 'max_depth': 2, 'enabled': True}
        >>>
        >>> # With type hints (string representations)
        >>> parse_key_value_pairs(
        ...     ('state_name_format=name,path', 'max_depth=2', 'enabled=true'),
        ...     type_hints={'state_name_format': 'tuple[str, ...]', 'max_depth': 'int', 'enabled': 'bool'}
        ... )
        {'state_name_format': ('name', 'path'), 'max_depth': 2, 'enabled': True}
        >>>
        >>> # Complex example with multiple types
        >>> parse_key_value_pairs(
        ...     ('name="My App"', 'version=1.0', 'debug=false', 'ports=8080,8081,8082'),
        ...     type_hints={'name': str, 'version': float, 'debug': bool, 'ports': 'tuple[int, ...]'}
        ... )
        {'name': 'My App', 'version': 1.0, 'debug': False, 'ports': (8080, 8081, 8082)}
    """
    type_hints = type_hints or {}
    options = {}

    for pair in option_pairs:
        if '=' not in pair:
            raise ValueError(
                f"Option must be in 'key=value' format, got: {pair}"
            )

        key, value = pair.split('=', 1)
        key = key.strip()
        value = value.strip()

        # Get expected type for this field
        expected_type = type_hints.get(key, 'auto')

        try:
            options[key] = parse_value(value, expected_type)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse option '{key}': {e}"
            )

    return options
