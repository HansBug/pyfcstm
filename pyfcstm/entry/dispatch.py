"""
Command-line interface entry point for the :mod:`pyfcstm` package.

This module defines the main Click command group used to expose the CLI for
the project, including version reporting and help configuration. It builds
user-facing metadata from the project configuration and provides a top-level
command entry point.

The module contains the following main components:

* :func:`pyfcstmcli` - Main Click command group for the CLI

Example::

    >>> from pyfcstm.entry.dispatch import pyfcstmcli
    >>> # Typically invoked via a Click entry point:
    >>> # python -m pyfcstm --help

.. note::
   The version display is implemented via a Click option callback, which
   prints version information and exits the process.

"""

import click
from click.core import Context, Option

from .base import CONTEXT_SETTINGS
from .._bootstrap import format_version_info
from ..config.meta import __DESCRIPTION__


# noinspection PyUnusedLocal
def print_version(ctx: Context, param: Option, value: bool) -> None:
    """
    Print the version information for the CLI and exit.

    This callback is invoked by Click when the ``--version`` flag is provided.
    It prints the project title, version, and author list (if available), then
    exits the Click context.

    :param ctx: Click context for the current command invocation.
    :type ctx: :class:`click.core.Context`
    :param param: Current Click option metadata.
    :type param: :class:`click.core.Option`
    :param value: Boolean flag indicating whether the option was provided.
    :type value: bool
    :return: ``None``.
    :rtype: None
    :raises click.exceptions.Exit: Raised implicitly when :meth:`click.Context.exit`
        is invoked after printing version information.

    Example::

        >>> import click
        >>> from pyfcstm.entry.dispatch import print_version
        >>> ctx = click.Context(click.Command('demo'))
        >>> print_version(ctx, click.Option(['--version']), True)  # doctest: +SKIP

    """
    if not value or ctx.resilient_parsing:
        return  # pragma: no cover
    click.echo(format_version_info())
    ctx.exit()


@click.group(context_settings=CONTEXT_SETTINGS, help=__DESCRIPTION__)
@click.option(
    "-v",
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show pyfcstm's version information.",
)
@click.option(
    "--self-check",
    is_flag=True,
    expose_value=False,
    help='Run installation and runtime self-checks. Use "pyfcstm --self-check --help" for options.',
)
def pyfcstmcli() -> None:
    """
    Main Click command group for the :mod:`pyfcstm` CLI.

    This command group provides a common entry point for subcommands and
    integrates global options such as ``--version`` and help flags.

    :return: ``None``.
    :rtype: None

    Example::

        >>> # Typically invoked via a console entry point:
        >>> # $ pyfcstm --help

    """
    pass  # pragma: no cover
