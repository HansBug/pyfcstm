"""
Import assembly helpers for model-layer state-machine construction.

This module implements the Phase 2 multi-file import assembler used by
``parse_dsl_node_to_state_machine()``. The assembler keeps the DSL layer pure:
the DSL parser only produces AST nodes, while file loading, recursive import
resolution, path handling, cycle detection, and state-tree inlining are all
performed here in the model layer.

At the current phase boundary, this module focuses on structural assembly:

* Relative import paths resolve against the declaring file's directory.
* Imported files are parsed recursively and inlined as child states.
* Circular imports and alias conflicts are reported explicitly.
* Imported root states are renamed to the declared alias and their display-name
  priority follows the PR79 design.
* Module-local absolute paths are rewritten into the final host instance scope
  so assembled state trees behave like ordinary inlined DSL.

Variable ``def`` mappings, event mappings, and imported top-level ``def``
definitions remain Phase 3 / Phase 4 work and therefore still fail fast here
with explicit error messages.
"""

import os
from dataclasses import fields, is_dataclass
from typing import Optional, Tuple, List

from ..dsl import node as dsl_nodes
from ..dsl.error import GrammarParseError
from ..dsl.parse import parse_state_machine_dsl
from ..utils import auto_decode

__all__ = [
    "assemble_state_machine_imports",
]


def assemble_state_machine_imports(
    dnode: dsl_nodes.StateMachineDSLProgram,
    path: Optional[str] = None,
) -> dsl_nodes.StateMachineDSLProgram:
    """
    Assemble import statements in a DSL program into a single inline AST.

    :param dnode: Source DSL program AST.
    :type dnode: dsl_nodes.StateMachineDSLProgram
    :param path: Optional path contract used to resolve import locations.
        Existing directories are treated as import base directories directly,
        while other values are treated as file paths whose parent directory is
        used as the import base.
    :type path: Optional[str]
    :return: A cloned and import-expanded DSL program AST.
    :rtype: dsl_nodes.StateMachineDSLProgram
    :raises SyntaxError: If import assembly fails due to missing files,
        circular imports, alias conflicts, or not-yet-supported mapping /
        imported-definition features.
    """

    effective_path, import_base_dir, entry_file_path = _resolve_path_context(path)
    program = _clone_ast_node(dnode)
    _assemble_program(
        program=program,
        import_base_dir=import_base_dir,
        import_stack=[entry_file_path] if entry_file_path is not None else [],
    )
    return program


def _resolve_path_context(path: Optional[str]) -> Tuple[str, str, Optional[str]]:
    effective_path = path
    if effective_path is None:
        effective_path = os.getcwd()

    normalized_path = os.path.abspath(os.fspath(effective_path))
    if os.path.isdir(normalized_path):
        return normalized_path, normalized_path, None
    else:
        return normalized_path, os.path.dirname(normalized_path), normalized_path


def _clone_ast_node(node):
    if node is dsl_nodes.INIT_STATE:
        return dsl_nodes.INIT_STATE
    elif node is dsl_nodes.EXIT_STATE:
        return dsl_nodes.EXIT_STATE
    elif node is dsl_nodes.ALL:
        return dsl_nodes.ALL
    elif isinstance(node, list):
        return [_clone_ast_node(item) for item in node]
    elif isinstance(node, tuple):
        return tuple(_clone_ast_node(item) for item in node)
    elif isinstance(node, dict):
        return {
            _clone_ast_node(key): _clone_ast_node(value) for key, value in node.items()
        }
    elif is_dataclass(node):
        values = {
            field.name: _clone_ast_node(getattr(node, field.name))
            for field in fields(node)
        }
        return node.__class__(**values)
    else:
        return node


def _assemble_program(
    program: dsl_nodes.StateMachineDSLProgram,
    import_base_dir: str,
    import_stack: List[str],
) -> None:
    if program.root_state is None:
        raise SyntaxError("State machine DSL program does not contain a root state.")

    _assemble_state(
        node=program.root_state,
        current_state_path=(program.root_state.name,),
        import_base_dir=import_base_dir,
        import_stack=import_stack,
    )


def _assemble_state(
    node: dsl_nodes.StateDefinition,
    current_state_path: Tuple[str, ...],
    import_base_dir: str,
    import_stack: List[str],
) -> None:
    occupied_names = []
    for subnode in node.substates:
        if subnode.name not in occupied_names:
            occupied_names.append(subnode.name)

    imported_substates = []
    for import_item in node.imports:
        if import_item.alias in occupied_names:
            raise SyntaxError(
                f"Import alias conflict in state {'.'.join(current_state_path)!r}: "
                f"alias {import_item.alias!r} conflicts with an existing child state."
            )
        occupied_names.append(import_item.alias)

        _validate_import_statement_supported(
            import_item=import_item,
            owner_state_path=current_state_path,
        )

        resolved_file = _resolve_import_file(
            source_path=import_item.source_path,
            import_base_dir=import_base_dir,
            owner_state_path=current_state_path,
            alias=import_item.alias,
        )

        cycle_index = _find_cycle_index(import_stack, resolved_file)
        if cycle_index is not None:
            chain = [*import_stack[cycle_index:], resolved_file]
            raise SyntaxError(
                "Circular import detected: %s"
                % " -> ".join(map(repr, chain))
            )

        imported_program = _load_imported_program(
            file_path=resolved_file,
            import_item=import_item,
            owner_state_path=current_state_path,
        )

        if imported_program.definitions:
            raise SyntaxError(
                "Imported top-level variable definitions are not available in "
                "import assembly yet. This requires Phase 3 variable mapping. "
                f"Found {len(imported_program.definitions)} definition(s) in "
                f"imported file {resolved_file!r} for import "
                f"{import_item.source_path!r} as {import_item.alias!r}."
            )

        _assemble_program(
            program=imported_program,
            import_base_dir=os.path.dirname(resolved_file),
            import_stack=[*import_stack, resolved_file],
        )

        imported_root = imported_program.root_state
        imported_root.name = import_item.alias
        imported_root.extra_name = (
            import_item.extra_name or imported_root.extra_name or import_item.alias
        )
        _rewrite_absolute_paths_for_imported_root(
            node=imported_root,
            instance_prefix=(*current_state_path[1:], import_item.alias),
        )
        imported_substates.append(imported_root)

    node.imports = []

    for subnode in node.substates:
        _assemble_state(
            node=subnode,
            current_state_path=(*current_state_path, subnode.name),
            import_base_dir=import_base_dir,
            import_stack=import_stack,
        )

    node.substates = [*imported_substates, *node.substates]


def _validate_import_statement_supported(
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> None:
    if import_item.mappings:
        raise SyntaxError(
            "Import mappings are parsed but not available in import assembly yet. "
            "Variable mappings belong to Phase 3 and event mappings belong to "
            "Phase 4. "
            f"Found import {import_item.source_path!r} as {import_item.alias!r} "
            f"in state {'.'.join(owner_state_path)!r} with "
            f"{len(import_item.mappings)} mapping statement(s)."
        )


def _resolve_import_file(
    source_path: str,
    import_base_dir: str,
    owner_state_path: Tuple[str, ...],
    alias: str,
) -> str:
    if os.path.isabs(source_path):
        resolved_file = os.path.abspath(os.fspath(source_path))
    else:
        resolved_file = os.path.abspath(
            os.path.join(import_base_dir, os.fspath(source_path))
        )

    if not os.path.isfile(resolved_file):
        raise SyntaxError(
            f"Import source file not found for import {source_path!r} as {alias!r} "
            f"in state {'.'.join(owner_state_path)!r}: {resolved_file!r}."
        )

    return resolved_file


def _find_cycle_index(import_stack: List[str], file_path: str) -> Optional[int]:
    file_key = os.path.normcase(os.path.abspath(file_path))
    for index, item in enumerate(import_stack):
        if os.path.normcase(os.path.abspath(item)) == file_key:
            return index
    return None


def _load_imported_program(
    file_path: str,
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> dsl_nodes.StateMachineDSLProgram:
    try:
        with open(file_path, "rb") as f:
            content = auto_decode(f.read())
    except OSError as err:
        raise SyntaxError(
            f"Failed to read imported file {file_path!r} for import "
            f"{import_item.source_path!r} as {import_item.alias!r} in state "
            f"{'.'.join(owner_state_path)!r}: {err}"
        ) from err

    try:
        program = parse_state_machine_dsl(content)
    except GrammarParseError as err:
        raise SyntaxError(
            f"Failed to parse imported file {file_path!r} for import "
            f"{import_item.source_path!r} as {import_item.alias!r} in state "
            f"{'.'.join(owner_state_path)!r}: {err}"
        ) from err

    if program.root_state is None:
        raise SyntaxError(
            f"Imported file {file_path!r} for import {import_item.source_path!r} "
            f"as {import_item.alias!r} does not contain a root state."
        )

    return program


def _rewrite_absolute_paths_for_imported_root(
    node: dsl_nodes.StateDefinition,
    instance_prefix: Tuple[str, ...],
) -> None:
    for transition in node.transitions:
        if transition.event_id is not None and transition.event_id.is_absolute:
            transition.event_id.path = [*instance_prefix, *transition.event_id.path]

    for transition in node.force_transitions:
        if transition.event_id is not None and transition.event_id.is_absolute:
            transition.event_id.path = [*instance_prefix, *transition.event_id.path]

    for enter_item in node.enters:
        if isinstance(enter_item, dsl_nodes.EnterRefFunction) and enter_item.ref.is_absolute:
            enter_item.ref.path = [*instance_prefix, *enter_item.ref.path]

    for during_item in node.durings:
        if (
            isinstance(during_item, dsl_nodes.DuringRefFunction)
            and during_item.ref.is_absolute
        ):
            during_item.ref.path = [*instance_prefix, *during_item.ref.path]

    for exit_item in node.exits:
        if isinstance(exit_item, dsl_nodes.ExitRefFunction) and exit_item.ref.is_absolute:
            exit_item.ref.path = [*instance_prefix, *exit_item.ref.path]

    for during_aspect_item in node.during_aspects:
        if (
            isinstance(during_aspect_item, dsl_nodes.DuringAspectRefFunction)
            and during_aspect_item.ref.is_absolute
        ):
            during_aspect_item.ref.path = [
                *instance_prefix,
                *during_aspect_item.ref.path,
            ]

    for subnode in node.substates:
        _rewrite_absolute_paths_for_imported_root(
            node=subnode,
            instance_prefix=instance_prefix,
        )
