"""
This module provides utilities for enhancing Jinja2 environments with Python builtins and additional settings.

It includes functions to add Python built-in functions to Jinja2 environments as filters, tests, and globals,
as well as adding environment variables and custom text processing functions.
"""

import builtins
import inspect
import os
import textwrap

import jinja2

from .text import normalize, to_identifier


def add_builtins_to_env(env: jinja2.Environment) -> jinja2.Environment:
    """
    Mount Python built-in functions to a Jinja2 environment.

    This function adds Python's built-in functions to the specified Jinja2 environment
    as filters, tests, or global functions based on their characteristics.

    :param env: A Jinja2 Environment instance
    :type env: jinja2.Environment

    :return: The Jinja2 Environment with Python builtins mounted
    :rtype: jinja2.Environment

    Example::

        >>> env = jinja2.Environment()
        >>> env = add_builtins_to_env(env)
        >>> # Now Python builtins like len, str, etc. are available in templates
    """
    # Existing built-in filters, tests and global functions in Jinja2
    existing_filters = set(env.filters.keys())
    existing_tests = set(env.tests.keys())
    existing_globals = set(env.globals.keys())

    # Get all Python built-in functions
    builtin_items = [(name, obj) for name, obj in inspect.getmembers(builtins)
                     if not name.startswith('_')]  # Exclude internal functions starting with underscore

    # Categorize functions for appropriate mounting positions
    for name, func in builtin_items:
        # Skip non-function objects
        if not callable(func):
            continue

        # Determine if the function is suitable as a filter
        is_filter_candidate = (
            # Filters typically accept one main argument and may have other optional parameters
                inspect.isfunction(func) or inspect.isbuiltin(func)
        )

        # Determine if the function is suitable as a tester
        is_test_candidate = (
            # Test functions typically return boolean values, like isinstance, issubclass, etc.
                name.startswith('is') or
                name in ('all', 'any', 'callable', 'hasattr')
        )

        # Mount as a filter (if suitable and no conflict)
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

        # Mount as a tester (if suitable and no conflict)
        test_name = name
        if name.startswith('is'):
            # For functions starting with 'is', the prefix can be removed as the tester name
            test_name = name[2:].lower()
        if is_test_candidate and test_name not in existing_tests:
            env.tests[test_name] = func

        # Mount as a global function (if no conflict)
        if name not in existing_globals:
            env.globals[name] = func

    return env


def add_settings_for_env(env: jinja2.Environment) -> jinja2.Environment:
    """
    Add additional settings and functions to a Jinja2 environment.

    This function enhances a Jinja2 environment by:
    1. Adding Python built-in functions
    2. Adding custom text processing filters
    3. Adding environment variables as global variables

    :param env: The Jinja2 environment to enhance
    :type env: jinja2.Environment

    :return: The enhanced Jinja2 environment
    :rtype: jinja2.Environment

    Example::

        >>> env = jinja2.Environment()
        >>> env = add_settings_for_env(env)
        >>> # Now the environment has additional filters and globals
    """
    env = add_builtins_to_env(env)
    env.filters['normalize'] = normalize
    env.filters['to_identifier'] = to_identifier
    env.globals['indent'] = textwrap.indent
    for key, value in os.environ.items():
        if key not in env.globals:
            env.globals[key] = value
    return env
