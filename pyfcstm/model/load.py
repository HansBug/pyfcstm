"""
Convenience model loading helpers for FCSTM sources.

This module provides high-level public entry points that collapse the common
workflow:

1. read or accept FCSTM DSL source text
2. parse DSL into AST
3. assemble imports and build the final :class:`StateMachine`

The helpers here do not replace the lower-level DSL parser or model builder.
They only provide a more direct public API for callers that already know they
want a fully constructed model object.

The main public helpers are:

* :func:`load_state_machine_from_file` - Load a model from a ``.fcstm`` file
* :func:`load_state_machine_from_text` - Load a model from DSL source text

Example::

    >>> import os
    >>> from tempfile import TemporaryDirectory
    >>> from pyfcstm.model.load import load_state_machine_from_file
    >>> with TemporaryDirectory() as td:
    ...     file_path = os.path.join(td, 'demo.fcstm')
    ...     with open(file_path, 'w', encoding='utf-8') as f:
    ...         _ = f.write('state Root;')
    ...     model = load_state_machine_from_file(file_path)
    ...     model.root_state.name
    'Root'

Example::

    >>> from pyfcstm.model.load import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> model.root_state.name
    'Root'

Example::

    >>> import os
    >>> from pyfcstm.model.load import load_state_machine_from_text
    >>> model = load_state_machine_from_text(
    ...     'state Root { state Idle; [*] -> Idle; }',
    ...     path=os.getcwd(),
    ... )
    >>> model.root_state.name
    'Root'
"""

import os
import pathlib
from typing import Optional, Union

from ..dsl import parse_state_machine_dsl
from ..utils import auto_decode
from .model import StateMachine, parse_dsl_node_to_state_machine

__all__ = [
    "load_state_machine_from_file",
    "load_state_machine_from_text",
]


def load_state_machine_from_file(path: Union[str, os.PathLike]) -> StateMachine:
    """
    Load a :class:`StateMachine` directly from an FCSTM file.

    This helper reads the file as bytes, decodes it with
    :func:`pyfcstm.utils.auto_decode`, parses the DSL into AST, and then builds
    the final import-aware model using the file path as the import resolution
    context.

    :param path: Path to the input ``.fcstm`` file.
    :type path: Union[str, os.PathLike]
    :return: Fully constructed state machine model.
    :rtype: StateMachine
    :raises OSError: If the file cannot be read.
    :raises UnicodeDecodeError: If the file content cannot be decoded.
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises SyntaxError: If model assembly or validation fails.

    Example::

        >>> import os
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     file_path = os.path.join(td, 'demo.fcstm')
        ...     with open(file_path, 'w', encoding='utf-8') as f:
        ...         _ = f.write('state Root;')
        ...     model = load_state_machine_from_file(file_path)
        ...     model.root_state.name
        'Root'
    """
    file_path = os.fspath(path)
    code = auto_decode(pathlib.Path(file_path).read_bytes())
    ast_node = parse_state_machine_dsl(code)
    return parse_dsl_node_to_state_machine(ast_node, path=file_path)


def load_state_machine_from_text(
    text: str,
    path: Optional[Union[str, os.PathLike]] = None,
) -> StateMachine:
    """
    Load a :class:`StateMachine` directly from FCSTM DSL source text.

    This helper parses the given DSL text into AST and then builds the final
    model. When ``path`` is omitted, the current working directory is used as
    the import resolution context; callers may also pass an explicit file path
    or directory path to control import resolution.

    :param text: FCSTM DSL source text.
    :type text: str
    :param path: Optional path contract for import resolution. Defaults to the
        current working directory when omitted.
    :type path: Optional[Union[str, os.PathLike]]
    :return: Fully constructed state machine model.
    :rtype: StateMachine
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises SyntaxError: If model assembly or validation fails.

    Example::

        >>> model = load_state_machine_from_text('state Root;')
        >>> model.root_state.name
        'Root'

    Example::

        >>> import os
        >>> model = load_state_machine_from_text(
        ...     'state Root { state Idle; [*] -> Idle; }',
        ...     path=os.getcwd(),
        ... )
        >>> model.root_state.name
        'Root'

    Example::

        >>> import os
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     child_path = os.path.join(td, 'worker.fcstm')
        ...     with open(child_path, 'w', encoding='utf-8') as f:
        ...         _ = f.write('state WorkerRoot { state Idle; [*] -> Idle; }')
        ...     model = load_state_machine_from_text(
        ...         'state Root { import "./worker.fcstm" as Worker; [*] -> Worker; }',
        ...         path=td,
        ...     )
        ...     sorted(model.root_state.substates.keys())
        ['Worker']
    """
    effective_path = os.getcwd() if path is None else os.fspath(path)
    ast_node = parse_state_machine_dsl(text)
    return parse_dsl_node_to_state_machine(ast_node, path=effective_path)
