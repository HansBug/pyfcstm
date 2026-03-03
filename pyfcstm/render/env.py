"""
Jinja2 environment configuration for template rendering.

This module provides a single convenience function, :func:`create_env`, which
builds a :class:`jinja2.Environment` configured for pyfcstm template rendering.
It augments a new environment with helper filters and globals via
:func:`pyfcstm.utils.jinja2.add_settings_for_env`, and then injects state machine
constants into the global namespace for template usage.

The module exposes the following public component:

* :func:`create_env` - Create a configured Jinja2 environment with state globals

Example::

    >>> from pyfcstm.render.env import create_env
    >>> env = create_env()
    >>> template = env.from_string("Initial state: {{ INIT_STATE }}")
    >>> template.render()
    'Initial state: ...'

.. note::
   The ``INIT_STATE`` and ``EXIT_STATE`` globals are imported from
   :mod:`pyfcstm.dsl` and made available to Jinja2 templates.
"""

import jinja2

from ..dsl import INIT_STATE, EXIT_STATE
from ..utils import add_settings_for_env


def create_env() -> jinja2.Environment:
    """
    Create and configure a Jinja2 environment for template rendering.

    This function initializes a :class:`jinja2.Environment`, applies additional
    filters and globals via :func:`pyfcstm.utils.jinja2.add_settings_for_env`,
    and registers the ``INIT_STATE`` and ``EXIT_STATE`` values as Jinja2 globals.

    :return: A configured Jinja2 environment instance.
    :rtype: jinja2.Environment

    Example::

        >>> env = create_env()
        >>> template = env.from_string("Initial state: {{ INIT_STATE }}")
        >>> rendered = template.render()
    """
    env = jinja2.Environment()
    env = add_settings_for_env(env)
    env.globals['INIT_STATE'] = INIT_STATE
    env.globals['EXIT_STATE'] = EXIT_STATE
    return env
