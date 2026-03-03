"""
Rendering utilities for the :mod:`pyfcstm.render` package.

This module exposes the public rendering interfaces used throughout the
package. It re-exports the primary environment setup function, expression
rendering helpers, and the state machine code renderer to provide a
convenient import surface.

The module contains the following main components:

* :func:`create_env` - Create a configured Jinja2 environment
* :func:`render_expr_node` - High-level expression rendering helper
* :func:`fn_expr_render` - Low-level expression rendering implementation
* :func:`create_expr_render_template` - Template dictionary builder for expression rendering
* :class:`StateMachineCodeRenderer` - State machine code generation renderer

Example::

    >>> from pyfcstm.render import create_env, render_expr_node
    >>> env = create_env()
    >>> render_expr_node(1 + 1, lang_style='python')
    '2'

.. note::
   This module is a thin re-export layer. Refer to the corresponding
   submodules for detailed behavior and configuration options.

"""

from .env import create_env
from .expr import render_expr_node, fn_expr_render, create_expr_render_template
from .render import StateMachineCodeRenderer
