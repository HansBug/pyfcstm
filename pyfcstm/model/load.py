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
from typing import List, Optional, Tuple, Union

from ..dsl import parse_state_machine_dsl
from ..utils import auto_decode
from ..utils.validate import ModelDiagnostic
from .model import StateMachine, parse_dsl_node_to_state_machine

__all__ = [
    "load_state_machine_from_file",
    "load_state_machine_from_text",
]


def load_state_machine_from_file(
    path: Union[str, os.PathLike],
    *,
    collect: bool = False,
) -> Union[
    StateMachine,
    Tuple[Optional[StateMachine], List[ModelDiagnostic]],
]:
    """
    Load a :class:`StateMachine` directly from an FCSTM file.

    This helper reads the file as bytes, decodes it with
    :func:`pyfcstm.utils.auto_decode`, parses the DSL into AST, and then builds
    the final import-aware model using the file path as the import resolution
    context.

    ``collect`` is forwarded to
    :func:`pyfcstm.model.parse_dsl_node_to_state_machine` and follows the same
    contract. In the default **strict** mode the first model error raises. In
    **collect** mode the return value becomes a
    ``(model_or_None, diagnostics)`` tuple carrying every detected error, and
    the model it returns may be internally inconsistent -- for example a
    transition whose endpoint name does not resolve.

    :param path: Path to the input ``.fcstm`` file.
    :type path: Union[str, os.PathLike]
    :param collect: When ``True``, return ``(model_or_None, diagnostics)``
        instead of raising on the first model error, defaults to ``False``.
    :type collect: bool, optional
    :return: Fully constructed state machine model, or the
        ``(model_or_None, diagnostics)`` pair when ``collect`` is ``True``.
    :rtype: Union[StateMachine, Tuple[Optional[StateMachine], List[pyfcstm.utils.validate.ModelDiagnostic]]]
    :raises OSError: If the file cannot be read.
    :raises UnicodeDecodeError: If the file content cannot be decoded.
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises SyntaxError: If model assembly or validation fails and ``collect``
        is ``False``.

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
    # Two source-text mechanisms coexist and serve different readers: BMC
    # provenance slices spans out of a path-keyed document map, while inspect and
    # the diagram viewer read the scalars for the one file the caller named.  Only
    # the scalars are set here, because ``_attach_model_source_metadata`` walks the
    # assembled AST and builds the map from them -- setting the map here as well
    # was dead code, which a mutation confirmed: removing it left 7645 tests green.
    ast_node._source_path = os.path.abspath(file_path)
    ast_node._source_text = code
    built = parse_dsl_node_to_state_machine(ast_node, path=file_path, collect=collect)
    machine, diagnostics = built if collect else (built, ())
    if machine is not None:
        machine.source_text = code
        machine.source_path = file_path
    return (machine, diagnostics) if collect else machine


def load_state_machine_from_text(
    text: str,
    path: Optional[Union[str, os.PathLike]] = None,
    *,
    collect: bool = False,
) -> Union[
    StateMachine,
    Tuple[Optional[StateMachine], List[ModelDiagnostic]],
]:
    """
    Load a :class:`StateMachine` directly from FCSTM DSL source text.

    This helper parses the given DSL text into AST and then builds the final
    model. When ``path`` is omitted, the current working directory is used as
    the import resolution context; callers may also pass an explicit file path
    or directory path to control import resolution.

    ``collect`` follows the same contract as in
    :func:`load_state_machine_from_file`.

    :param text: FCSTM DSL source text.
    :type text: str
    :param path: Optional path contract for import resolution. Defaults to the
        current working directory when omitted.
    :type path: Optional[Union[str, os.PathLike]]
    :param collect: When ``True``, return ``(model_or_None, diagnostics)``
        instead of raising on the first model error, defaults to ``False``.
    :type collect: bool, optional
    :return: Fully constructed state machine model, or the
        ``(model_or_None, diagnostics)`` pair when ``collect`` is ``True``.
    :rtype: Union[StateMachine, Tuple[Optional[StateMachine], List[pyfcstm.utils.validate.ModelDiagnostic]]]
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises SyntaxError: If model assembly or validation fails and ``collect``
        is ``False``.

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
    # Same pairing as the file loader, and the same reason for setting only the
    # scalars.  ``<memory>`` is what the map ends up keyed on, and
    # ``pyfcstm.diagram.api`` reads that key to tell a model loaded from text --
    # whose ``source_path`` is the working directory used for import resolution --
    # from one loaded from a file.
    ast_node._source_path = "<memory>"
    ast_node._source_text = text
    built = parse_dsl_node_to_state_machine(
        ast_node, path=effective_path, collect=collect
    )
    machine, diagnostics = built if collect else (built, ())
    if machine is not None:
        machine.source_text = text
        machine.source_path = effective_path
    return (machine, diagnostics) if collect else machine
