"""
Jinja2 environment augmentation utilities.

This module provides helpers for enriching a :class:`jinja2.Environment` with
Python built-ins, text-processing filters, and selected operating system
environment variables. It is intended to simplify template authoring by making
common Python functions available as filters, tests, and globals, while also
adding project-specific text utilities.

The module contains the following public functions:

* :func:`add_builtins_to_env` - Register Python built-ins as filters, tests, and globals
* :func:`add_settings_for_env` - Apply built-ins plus additional filters and globals
* :func:`to_c_path_identifier` - Build collision-resistant C path identifiers
* :func:`to_c_public_identifier` - Build public C/C++ identifiers that avoid reserved forms
* :func:`to_c_public_macro_identifier` - Build public C/C++ macro identifiers
* :func:`is_c_public_identifier_reserved` - Detect reserved public C/C++ identifier shapes

.. note::
   The added filters and globals are only attached to the environment instance
   passed to the functions and do not affect other environments.

Example::

    >>> import jinja2
    >>> from pyfcstm.utils.jinja2 import add_settings_for_env
    >>> env = add_settings_for_env(jinja2.Environment())
    >>> template = env.from_string("{{ 'Hello World'|to_identifier }}")
    >>> template.render()
    'Hello_World'
"""

import builtins
import inspect
import os
import textwrap

import jinja2

from .text import normalize, to_identifier, to_c_identifier


def to_c_path_identifier(segments) -> str:
    """
    Convert a path sequence into a collision-resistant C identifier.

    Each path segment is encoded independently and prefixed with its original
    length. Encoding segment boundaries this way avoids collisions such as
    ``Root.A.B`` and ``Root.A_B``. Preserving case while escaping significant
    underscores also avoids collisions such as ``Root.A`` and ``Root.a`` or
    ``Internal`` and ``Internal_`` while keeping the output acceptable for
    C/C++ identifiers and out of the C++ reserved double-underscore namespace.

    :param segments: Iterable path segments to encode.
    :type segments: typing.Iterable[str]
    :return: C/C++-safe path identifier.
    :rtype: str

    Example::

        >>> to_c_path_identifier(["Root", "A", "B"])
        'p4_Root_p1_A_p1_B'
        >>> to_c_path_identifier(["Root", "A_B"])
        'p4_Root_p3_Az00005FB'
        >>> to_c_path_identifier(["Root", "A__B"])
        'p4_Root_p4_Az00005Fz00005FB'
        >>> to_c_path_identifier(["Root", "Internal_"])
        'p4_Root_p9_Internalz00005F'
    """
    parts = []
    for segment in segments:
        raw_segment = str(segment)
        encoded_chars = []
        for char in raw_segment:
            if "0" <= char <= "9" or "A" <= char <= "Z" or "a" <= char <= "y":
                encoded_chars.append(char)
            else:
                encoded_chars.append("z%06X" % ord(char))
        item = "".join(encoded_chars) or "empty"
        parts.append("p%d_%s" % (len(raw_segment), item))
    return "_".join(parts) or "p0_empty"


def _has_reserved_c_public_shape(identifier: str) -> bool:
    """
    Check whether a generated public C/C++ identifier has a reserved shape.

    :param identifier: Identifier spelling to inspect.
    :type identifier: str
    :return: Whether the spelling should be avoided for public generated names.
    :rtype: bool
    """
    return identifier.startswith("_") or "__" in identifier


def is_c_public_identifier_reserved(identifier: str) -> bool:
    """
    Return whether a public C/C++ identifier spelling should be avoided.

    Generated public macros, typedefs, and function prefixes should avoid names
    that C or C++ reserves for implementations. This helper checks the shapes
    that matter for generated public identifiers: a leading underscore or any
    double underscore.

    :param identifier: Identifier spelling to inspect.
    :type identifier: str
    :return: Whether the spelling has a reserved public C/C++ shape.
    :rtype: bool

    Example::

        >>> is_c_public_identifier_reserved('_ROOT_MACHINE')
        True
        >>> is_c_public_identifier_reserved('ROOT__MACHINE')
        True
        >>> is_c_public_identifier_reserved('ROOT_MACHINE')
        False
    """
    return _has_reserved_c_public_shape(identifier)


def to_c_public_identifier(input_string: str, suffix: str = "") -> str:
    """
    Convert text into a public C/C++ identifier that avoids reserved forms.

    The helper keeps ordinary identifiers readable, while falling back to the
    lossless path encoder whenever appending ``suffix`` would create a public
    spelling with a leading underscore or a double underscore. This is intended
    for generated C-family public ABI prefixes such as root-machine typedefs,
    function prefixes, visibility macros, and header-guard components.

    :param input_string: Source text to encode.
    :type input_string: str
    :param suffix: Optional suffix to append to the generated identifier,
        defaults to ``''``.
    :type suffix: str, optional
    :return: Public C/C++ identifier spelling.
    :rtype: str

    Example::

        >>> to_c_public_identifier('Root', 'Machine')
        'RootMachine'
        >>> to_c_public_identifier('_Root', 'Machine')
        'p_p5_z00005FRootMachine'
        >>> to_c_public_identifier('class', '_MACHINE')
        'p_p5_class_MACHINE'
    """
    candidate = to_c_identifier(input_string) + suffix
    if not _has_reserved_c_public_shape(candidate):
        return candidate
    return "p_%s%s" % (to_c_path_identifier([input_string]), suffix)


def to_c_public_macro_identifier(input_string: str, suffix: str = "") -> str:
    """
    Convert text into an uppercase public C/C++ macro identifier.

    This helper mirrors :func:`to_c_public_identifier` and uppercases the final
    spelling for generated public macro prefixes and header guards.

    :param input_string: Source text to encode.
    :type input_string: str
    :param suffix: Optional suffix to append before uppercasing, defaults to
        ``''``.
    :type suffix: str, optional
    :return: Public C/C++ macro identifier spelling.
    :rtype: str

    Example::

        >>> to_c_public_macro_identifier('Root', '_MACHINE')
        'ROOT_MACHINE'
        >>> to_c_public_macro_identifier('_Root', '_MACHINE')
        'P_P5_Z00005FROOT_MACHINE'
    """
    return to_c_public_identifier(input_string, suffix).upper()


def add_builtins_to_env(env: jinja2.Environment) -> jinja2.Environment:
    """
    Mount Python built-in functions to a Jinja2 environment.

    This function registers Python built-ins to the provided environment as:

    - **Filters**: Callable built-ins are added as filters when no naming
      conflict exists.
    - **Tests**: Common boolean checks are added as tests, using a simplified
      name for functions beginning with ``is`` (e.g., ``isinstance`` becomes
      the ``instance`` test).
    - **Globals**: All non-conflicting built-ins are added to the global
      namespace.

    In addition to these automatic registrations, this function always injects
    several convenience filters, even if they overwrite existing names in the
    environment:

    - ``str``: :class:`str`
    - ``set``: :class:`set`
    - ``dict``: :class:`dict`
    - ``keys``: ``lambda x: x.keys()``
    - ``values``: ``lambda x: x.values()``
    - ``enumerate``: :func:`enumerate`
    - ``reversed``: :func:`reversed`
    - ``filter``: ``lambda x, y: filter(y, x)``

    :param env: A Jinja2 environment instance to modify.
    :type env: jinja2.Environment
    :return: The same Jinja2 environment with built-ins mounted.
    :rtype: jinja2.Environment

    .. warning::
       This function may override pre-existing filters named ``str``, ``set``,
       ``dict``, ``keys``, ``values``, ``enumerate``, ``reversed``, and
       ``filter``.

    Example::

        >>> import jinja2
        >>> env = add_builtins_to_env(jinja2.Environment())
        >>> tmpl = env.from_string("{{ [1, 2, 3]|reversed|list }}")
        >>> tmpl.render()
        '[3, 2, 1]'
    """
    existing_filters = set(env.filters.keys())
    existing_tests = set(env.tests.keys())
    existing_globals = set(env.globals.keys())

    builtin_items = [
        (name, obj)
        for name, obj in inspect.getmembers(builtins)
        if not name.startswith("_")
    ]

    for name, func in builtin_items:
        if not callable(func):
            continue

        is_filter_candidate = inspect.isfunction(func) or inspect.isbuiltin(func)

        is_test_candidate = name.startswith("is") or name in (
            "all",
            "any",
            "callable",
            "hasattr",
        )

        filter_name = name
        if is_filter_candidate and filter_name not in existing_filters:
            env.filters[filter_name] = func
        env.filters["str"] = str
        env.filters["set"] = set
        env.filters["dict"] = dict
        env.filters["keys"] = lambda x: x.keys()
        env.filters["values"] = lambda x: x.values()
        env.filters["enumerate"] = enumerate
        env.filters["reversed"] = reversed
        env.filters["filter"] = lambda x, y: filter(y, x)

        test_name = name
        if name.startswith("is"):
            test_name = name[2:].lower()
        if is_test_candidate and test_name not in existing_tests:
            env.tests[test_name] = func

        if name not in existing_globals:
            env.globals[name] = func

    return env


def add_settings_for_env(env: jinja2.Environment) -> jinja2.Environment:
    """
    Add built-ins, text filters, and environment variables to a Jinja2 environment.

    This function enhances a Jinja2 environment by applying the following steps:

    1. Register Python built-ins via :func:`add_builtins_to_env`
    2. Add text-processing filters:
       - ``normalize``: :func:`pyfcstm.utils.text.normalize`
       - ``to_identifier``: :func:`pyfcstm.utils.text.to_identifier`
       - ``to_c_identifier``: :func:`pyfcstm.utils.text.to_c_identifier`
       - ``to_c_path_identifier``: :func:`to_c_path_identifier`
       - ``to_c_public_identifier``: :func:`to_c_public_identifier`
       - ``to_c_public_macro_identifier``: :func:`to_c_public_macro_identifier`
    3. Add a global helper:
       - ``indent``: :func:`textwrap.indent`
    4. Add operating system environment variables as globals (only if the name
       does not already exist in the environment).

    :param env: The Jinja2 environment to enhance.
    :type env: jinja2.Environment
    :return: The enhanced Jinja2 environment.
    :rtype: jinja2.Environment

    .. note::
       Environment variables are only added if their names do not already exist
       in the environment's global namespace.

    Example::

        >>> import jinja2
        >>> env = add_settings_for_env(jinja2.Environment())
        >>> template = env.from_string("{{ 'Hello World'|normalize }}")
        >>> template.render()
        'Hello_World'
    """
    env = add_builtins_to_env(env)
    env.filters["normalize"] = normalize
    env.filters["to_identifier"] = to_identifier
    env.filters["to_c_identifier"] = to_c_identifier
    env.filters["to_c_path_identifier"] = to_c_path_identifier
    env.filters["to_c_public_identifier"] = to_c_public_identifier
    env.filters["to_c_public_macro_identifier"] = to_c_public_macro_identifier
    env.filters["is_c_public_identifier_reserved"] = is_c_public_identifier_reserved
    env.tests["c_public_identifier_reserved"] = is_c_public_identifier_reserved
    env.globals["indent"] = textwrap.indent
    for key, value in os.environ.items():
        if key not in env.globals:
            env.globals[key] = value
    return env
