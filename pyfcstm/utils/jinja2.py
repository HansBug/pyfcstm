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

    builtin_items = [(name, obj) for name, obj in inspect.getmembers(builtins)
                     if not name.startswith('_')]

    for name, func in builtin_items:
        if not callable(func):
            continue

        is_filter_candidate = (
            inspect.isfunction(func) or inspect.isbuiltin(func)
        )

        is_test_candidate = (
            name.startswith('is') or
            name in ('all', 'any', 'callable', 'hasattr')
        )

        filter_name = name
        if is_filter_candidate and filter_name not in existing_filters:
            env.filters[filter_name] = func
        env.filters['str'] = str
        env.filters['set'] = set
        env.filters['dict'] = dict
        env.filters['keys'] = lambda x: x.keys()
        env.filters['values'] = lambda x: x.values()
        env.filters['enumerate'] = enumerate
        env.filters['reversed'] = reversed
        env.filters['filter'] = lambda x, y: filter(y, x)

        test_name = name
        if name.startswith('is'):
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
    env.filters['normalize'] = normalize
    env.filters['to_identifier'] = to_identifier
    env.filters['to_c_identifier'] = to_c_identifier
    env.globals['indent'] = textwrap.indent
    for key, value in os.environ.items():
        if key not in env.globals:
            env.globals[key] = value
    return env
