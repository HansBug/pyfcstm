"""
Jinja2 Environment Module

This module provides functionality for creating and configuring a Jinja2 environment
for template rendering. It sets up global variables and adds custom settings to the
environment to support state machine template rendering.
"""

import jinja2

from ..dsl import INIT_STATE, EXIT_STATE
from ..utils import add_settings_for_env


def create_env():
    """
    Create and configure a Jinja2 environment for template rendering.

    This function initializes a Jinja2 Environment instance, adds custom settings
    through the add_settings_for_env utility, and sets up global variables for
    state machine templates including initial and exit states.

    :return: A configured Jinja2 Environment instance
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
