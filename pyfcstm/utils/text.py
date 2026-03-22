"""
String normalization utilities for converting arbitrary strings to valid identifiers.

This module provides helper functions to normalize strings into valid identifier
formats that can be used in programming contexts. It converts non-ASCII
characters using transliteration, replaces invalid characters with underscores,
and optionally enforces identifier rules such as not starting with a digit.

The module contains the following main components:

* :func:`normalize` - Convenience wrapper for non-strict identifier conversion
* :func:`to_identifier` - Full identifier conversion with strict mode support
* :func:`to_c_identifier` - Conservative C/C++-safe identifier conversion
* :func:`to_python_identifier` - Python-safe identifier conversion
* :func:`to_java_identifier` - Java-safe identifier conversion
* :func:`to_ruby_identifier` - Ruby-safe identifier conversion
* :func:`to_ts_identifier` - TypeScript-safe identifier conversion
* :func:`to_js_identifier` - JavaScript-safe identifier conversion
* :func:`to_rust_identifier` - Rust-safe identifier conversion
* :func:`to_go_identifier` - Go-safe identifier conversion

Example::

    >>> from pyfcstm.utils.text import normalize, to_identifier
    >>> normalize("Hello World!")
    'Hello_World'
    >>> to_identifier("123 Test", strict_mode=True)
    '_123_Test'
    >>> to_identifier("class", keyword_safe_for=['python', 'java'])
    'class_'
"""

from typing import List, Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from unidecode import unidecode

IdentifierKeywordLanguage = Literal['c', 'cpp', 'python', 'java', 'ruby', 'ts', 'js', 'rust', 'go']

_LANGUAGE_ALIASES = {
    'c': 'c',
    'cpp': 'c',
    'c++': 'c',
    'cxx': 'c',
    'python': 'python',
    'py': 'python',
    'java': 'java',
    'ruby': 'ruby',
    'rb': 'ruby',
    'ts': 'ts',
    'typescript': 'ts',
    'js': 'js',
    'javascript': 'js',
    'rust': 'rust',
    'rs': 'rust',
    'go': 'go',
    'golang': 'go',
}

_CASE_INSENSITIVE_KEYWORD_LANGUAGES = {'c'}

_C_RESERVED_WORDS = {
    # C keywords / common reserved identifiers in generated-code contexts
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
    'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'inline',
    'int', 'long', 'register', 'restrict', 'return', 'short', 'signed',
    'sizeof', 'static', 'struct', 'switch', 'typedef', 'union', 'unsigned',
    'void', 'volatile', 'while',
    '_alignas', '_alignof', '_atomic', '_bool', '_complex', '_generic',
    '_imaginary', '_noreturn', '_static_assert', '_thread_local',
    # C++ keywords, kept here as a conservative superset for C/C++ codegen
    'alignas', 'alignof', 'and', 'and_eq', 'asm', 'bitand', 'bitor', 'bool',
    'catch', 'char16_t', 'char32_t', 'class', 'compl', 'concept', 'consteval',
    'constexpr', 'constinit', 'const_cast', 'decltype', 'delete',
    'dynamic_cast', 'explicit', 'export', 'false', 'friend', 'mutable',
    'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr', 'operator',
    'or', 'or_eq', 'private', 'protected', 'public', 'reinterpret_cast',
    'requires', 'static_assert', 'static_cast', 'template', 'this',
    'thread_local', 'throw', 'true', 'try', 'typeid', 'typename', 'using',
    'virtual', 'wchar_t', 'xor', 'xor_eq',
}

_PYTHON_RESERVED_WORDS = {
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
    'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
    'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
    'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
}

_JAVA_RESERVED_WORDS = {
    'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char',
    'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
    'extends', 'false', 'final', 'finally', 'float', 'for', 'goto', 'if',
    'implements', 'import', 'instanceof', 'int', 'interface', 'long', 'native',
    'new', 'null', 'package', 'private', 'protected', 'public', 'return',
    'short', 'static', 'strictfp', 'super', 'switch', 'synchronized', 'this',
    'throw', 'throws', 'transient', 'true', 'try', 'void', 'volatile', 'while',
    # Contextual/restricted keywords commonly worth avoiding in codegen.
    'exports', 'module', 'open', 'opens', 'permits', 'provides', 'record',
    'requires', 'sealed', 'to', 'transitive', 'uses', 'var', 'with', 'yield',
}

_RUBY_RESERVED_WORDS = {
    'BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'class', 'def',
    'defined', 'do', 'else', 'elsif', 'end', 'ensure', 'false', 'for', 'if',
    'in', 'module', 'next', 'nil', 'not', 'or', 'redo', 'rescue', 'retry',
    'return', 'self', 'super', 'then', 'true', 'undef', 'unless', 'until',
    'when', 'while', 'yield', '__ENCODING__', '__FILE__', '__LINE__',
}

_JS_RESERVED_WORDS = {
    'await', 'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
    'default', 'delete', 'do', 'else', 'enum', 'export', 'extends', 'false',
    'finally', 'for', 'function', 'if', 'implements', 'import', 'in',
    'instanceof', 'interface', 'let', 'new', 'null', 'package', 'private',
    'protected', 'public', 'return', 'static', 'super', 'switch', 'this',
    'throw', 'true', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
}

_TS_RESERVED_WORDS = set(_JS_RESERVED_WORDS)
_TS_RESERVED_WORDS.update({
    'abstract', 'any', 'as', 'asserts', 'bigint', 'boolean', 'constructor',
    'declare', 'from', 'get', 'global', 'infer', 'intrinsic', 'is', 'keyof',
    'module', 'namespace', 'never', 'number', 'object', 'out', 'override',
    'readonly', 'require', 'satisfies', 'set', 'string', 'symbol', 'type',
    'unique', 'unknown', 'using',
})

_RUST_RESERVED_WORDS = {
    'Self', 'abstract', 'as', 'async', 'await', 'become', 'box', 'break',
    'const', 'continue', 'crate', 'do', 'dyn', 'else', 'enum', 'extern',
    'false', 'final', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop', 'macro',
    'match', 'mod', 'move', 'mut', 'override', 'priv', 'pub', 'ref', 'return',
    'self', 'static', 'struct', 'super', 'trait', 'true', 'try', 'type',
    'typeof', 'union', 'unsafe', 'unsized', 'use', 'virtual', 'where', 'while',
    'yield',
}

_GO_RESERVED_WORDS = {
    'break', 'case', 'chan', 'const', 'continue', 'default', 'defer', 'else',
    'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import', 'interface',
    'map', 'package', 'range', 'return', 'select', 'struct', 'switch', 'type',
    'var',
}

_LANGUAGE_KEYWORDS = {
    'c': _C_RESERVED_WORDS,
    'python': _PYTHON_RESERVED_WORDS,
    'java': _JAVA_RESERVED_WORDS,
    'ruby': _RUBY_RESERVED_WORDS,
    'ts': _TS_RESERVED_WORDS,
    'js': _JS_RESERVED_WORDS,
    'rust': _RUST_RESERVED_WORDS,
    'go': _GO_RESERVED_WORDS,
}


def _normalize_keyword_language(language: str) -> str:
    """
    Normalize a keyword-safety language selector to its canonical key.

    :param language: User-provided language selector.
    :type language: str
    :return: Canonical language key used internally.
    :rtype: str
    :raises ValueError: If the language selector is unsupported.
    """
    normalized = _LANGUAGE_ALIASES.get(language.lower())
    if normalized is None:
        raise ValueError(
            'Unsupported identifier keyword-safe language {language!r}, '
            'expected one of: c, cpp, python, java, ruby, ts, js, rust, go.'.format(
                language=language,
            )
        )
    return normalized


def _normalize_keyword_safe_for(
        keyword_safe_for: Optional[List[IdentifierKeywordLanguage]],
) -> List[str]:
    """
    Normalize and de-duplicate keyword-safety language selectors.

    :param keyword_safe_for: Languages that must be keyword-safe.
    :type keyword_safe_for: Optional[List[IdentifierKeywordLanguage]]
    :return: Canonical language keys.
    :rtype: List[str]
    """
    retval = []
    seen = set()
    for item in keyword_safe_for or []:
        normalized = _normalize_keyword_language(item)
        if normalized not in seen:
            retval.append(normalized)
            seen.add(normalized)

    return retval


def _is_reserved_identifier(identifier: str, language: str) -> bool:
    """
    Check whether an identifier collides with a reserved word set.

    :param identifier: Identifier to check.
    :type identifier: str
    :param language: Canonical language key.
    :type language: str
    :return: Whether the identifier collides with the reserved set.
    :rtype: bool
    """
    if language in _CASE_INSENSITIVE_KEYWORD_LANGUAGES:
        return identifier.lower() in _LANGUAGE_KEYWORDS[language]
    return identifier in _LANGUAGE_KEYWORDS[language]


def _apply_keyword_safety(
        identifier: str,
        keyword_safe_for: Optional[List[IdentifierKeywordLanguage]],
) -> str:
    """
    Append underscores until the identifier is safe for all requested languages.

    :param identifier: Normalized identifier.
    :type identifier: str
    :param keyword_safe_for: Languages that must remain keyword-safe.
    :type keyword_safe_for: Optional[List[IdentifierKeywordLanguage]]
    :return: Keyword-safe identifier.
    :rtype: str
    """
    if not identifier:
        return identifier

    languages = _normalize_keyword_safe_for(keyword_safe_for)
    while any(_is_reserved_identifier(identifier, language) for language in languages):
        identifier += '_'

    return identifier


def normalize(
        input_string: str,
        keyword_safe_for: Optional[List[IdentifierKeywordLanguage]] = None,
) -> str:
    """
    Normalize a string to a valid identifier format.

    This is a convenience wrapper around :func:`to_identifier` with
    ``strict_mode`` set to ``False``. It replaces non-alphanumeric
    characters with underscores while allowing identifiers to start
    with digits and allowing empty input to return an empty string. When
    requested, it also avoids reserved words for selected target languages.

    :param input_string: The string to be normalized
    :type input_string: str
    :param keyword_safe_for: Optional target-language list whose reserved words
                             should be avoided conservatively. Supported values
                             are ``'c'``, ``'cpp'``, ``'python'``, ``'java'``,
                             ``'ruby'``, ``'ts'``, ``'js'``, ``'rust'``, and
                             ``'go'``.
    :type keyword_safe_for: Optional[List[Literal['c', 'cpp', 'python', 'java', 'ruby', 'ts', 'js', 'rust', 'go']]], optional
    :return: A normalized identifier string
    :rtype: str
    :raises TypeError: If ``input_string`` is not a string
    :raises ValueError: If an unsupported language is listed in
                        ``keyword_safe_for``.

    Example::

        >>> normalize("Hello World!")
        'Hello_World'
        >>> normalize("123 Test")
        '123_Test'
        >>> normalize("class", keyword_safe_for=['python'])
        'class_'
    """
    return to_identifier(input_string, strict_mode=False, keyword_safe_for=keyword_safe_for)


def to_identifier(
        input_string: str,
        strict_mode: bool = True,
        keyword_safe_for: Optional[List[IdentifierKeywordLanguage]] = None,
) -> str:
    """
    Convert any string to a valid identifier format ``[0-9a-zA-Z_]+``.

    Rules:

    1. Preserve all letters and numbers after transliteration
    2. Convert spaces and special characters to underscores
    3. If ``strict_mode`` is ``True``, ensure the first character is not a number
    4. If ``strict_mode`` is ``True``, handle empty strings by returning ``"_empty"``
    5. Avoid multiple consecutive underscores by collapsing them
    6. Optionally avoid reserved words for selected target languages

    :param input_string: The string to be converted
    :type input_string: str
    :param strict_mode: When ``True``, applies additional rules to ensure
                        identifier validity across most languages. When
                        ``False``, allows empty strings and identifiers
                        starting with numbers.
    :type strict_mode: bool, optional
    :param keyword_safe_for: Optional target-language list whose reserved words
                             should be avoided conservatively. Supported values
                             are ``'c'``, ``'cpp'``, ``'python'``, ``'java'``,
                             ``'ruby'``, ``'ts'``, ``'js'``, ``'rust'``, and
                             ``'go'``.
    :type keyword_safe_for: Optional[List[Literal['c', 'cpp', 'python', 'java', 'ruby', 'ts', 'js', 'rust', 'go']]], optional
    :return: A valid identifier string
    :rtype: str
    :raises TypeError: If ``input_string`` is not a string
    :raises ValueError: If an unsupported language is listed in
                        ``keyword_safe_for``.

    Example::

        >>> to_identifier("Hello World!", strict_mode=True)
        'Hello_World'
        >>> to_identifier("123 Test", strict_mode=True)
        '_123_Test'
        >>> to_identifier("", strict_mode=True)
        '_empty'
        >>> to_identifier("class", keyword_safe_for=['python', 'java'])
        'class_'
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

    return _apply_keyword_safety(result, keyword_safe_for)


def to_c_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that is safe for both C and C++ codegen.

    This function first normalizes the value with :func:`to_identifier`, then
    avoids identifiers that collide with common C/C++ reserved words by
    appending a trailing underscore when necessary.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A C/C++-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['c'])


def to_cpp_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that is safe for C/C++ codegen.

    The ``cpp`` selector is treated as an alias of the conservative C/C++
    reserved-word superset used by :func:`to_c_identifier`.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A C/C++-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['cpp'])


def to_python_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids Python reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A Python-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['python'])


def to_java_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids Java reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A Java-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['java'])


def to_ruby_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids Ruby reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A Ruby-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['ruby'])


def to_ts_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids TypeScript reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A TypeScript-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['ts'])


def to_js_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids JavaScript reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A JavaScript-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['js'])


def to_rust_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids Rust reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A Rust-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['rust'])


def to_go_identifier(input_string: str, strict_mode: bool = True) -> str:
    """
    Convert a string to an identifier that avoids Go reserved words.

    :param input_string: Source text to normalize.
    :type input_string: str
    :param strict_mode: Whether to apply strict identifier normalization.
    :type strict_mode: bool, optional
    :return: A Go-safe identifier.
    :rtype: str
    """
    return to_identifier(input_string, strict_mode=strict_mode, keyword_safe_for=['go'])
