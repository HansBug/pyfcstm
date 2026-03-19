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

from typing import Iterable

import jinja2

from ..dsl import INIT_STATE, EXIT_STATE
from ..dsl import node as dsl_nodes
from ..model.model import OperationStatement
from ..utils import add_settings_for_env


def _render_operation_statement(node) -> str:
    """
    Render one operation statement to DSL text.

    :param node: AST or model operation statement to render.
    :type node: Any
    :return: DSL rendering of the statement.
    :rtype: str
    :raises TypeError: If ``node`` is not a supported operation statement.
    """
    if isinstance(node, OperationStatement):
        return str(node.to_ast_node())
    if isinstance(node, dsl_nodes.OperationalStatement):
        return str(node)

    raise TypeError(f'Unsupported operation statement type: {type(node)!r}')


def _render_operation_statements(nodes: Iterable, sep: str = '\n') -> str:
    """
    Render an iterable of operation statements to DSL text.

    :param nodes: Operation statements to render.
    :type nodes: Iterable
    :param sep: Separator inserted between rendered statements.
    :type sep: str
    :return: Joined DSL rendering.
    :rtype: str
    """
    return sep.join(_render_operation_statement(node) for node in nodes)


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
    env.globals['operation_stmt_render'] = _render_operation_statement
    env.filters['operation_stmt_render'] = _render_operation_statement
    env.globals['operation_stmts_render'] = _render_operation_statements
    env.filters['operation_stmts_render'] = _render_operation_statements
    return env
