"""
Command-line interface assembly for the PyFCSTM entry points.

This module composes the top-level CLI command group by applying a sequence
of subcommand decorators. It exposes a ready-to-use Click group that includes
the available subcommands registered by :mod:`pyfcstm.entry.generate`,
:mod:`pyfcstm.entry.plantuml`, and :mod:`pyfcstm.entry.simulate`.

The module contains the following main component:

* :data:`cli` - Preconfigured Click command group with registered subcommands

Example::

    >>> from pyfcstm.entry.cli import cli
    >>> # ``cli`` is a click.Group and can be invoked by Click's command runner.
    >>> isinstance(cli.name, str)
    True

.. note::
   Subcommands are added by decorator functions that mutate the Click group in
   place and return it for chaining.
"""

from typing import Callable, List

import click

from .dispatch import pyfcstmcli
from .generate import _add_generate_subcommand
from .plantuml import _add_plantuml_subcommand
from .simulate import _add_simulate_subcommand
from .sysdesim import _add_sysdesim_subcommand
from .visualize import _add_visualize_subcommand

_DECORATORS: List[Callable[[click.Group], click.Group]] = [
    _add_generate_subcommand,
    _add_plantuml_subcommand,
    _add_visualize_subcommand,
    _add_simulate_subcommand,
    _add_sysdesim_subcommand,
]

cli: click.Group = pyfcstmcli
for deco in _DECORATORS:
    cli = deco(cli)
