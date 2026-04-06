"""
Import assembly helpers for model-layer state-machine construction.

This module implements the model-layer import assembler used by
``parse_dsl_node_to_state_machine()``. The assembler keeps the DSL layer pure:
the DSL parser only produces AST nodes, while file loading, recursive import
resolution, path handling, cycle detection, variable mapping, and state-tree
inlining are all performed here in the model layer.

At the current phase boundary, this module provides:

* Relative import paths resolve against the declaring file's directory.
* Imported files are parsed recursively and inlined as child states.
* Circular imports and alias conflicts are reported explicitly.
* Imported root states are renamed to the declared alias and their display-name
  priority follows the PR79 design.
* Imported top-level ``def`` definitions are merged into the host model using
  Phase 3 mapping and conflict checks.
* Variable ``def`` mappings support exact / set / pattern / fallback rules,
  placeholder expansion, default alias-based isolation, and deep variable
  reference rewriting across definitions, guards, and operation blocks.
* Module-local absolute paths are rewritten into the final host instance scope
  so assembled state trees behave like ordinary inlined DSL.

Event mappings support module-absolute event promotion into host-relative or
host-absolute event paths, including display-name propagation and conflict
checks defined by PR79.
"""

import os
import re
from dataclasses import dataclass, fields, is_dataclass
from typing import Dict, List, Optional, Tuple

from ..dsl import node as dsl_nodes
from ..dsl.error import GrammarParseError
from ..dsl.parse import parse_state_machine_dsl
from ..utils import auto_decode

__all__ = [
    "assemble_state_machine_imports",
]


@dataclass
class _ResolvedImportEventMapping:
    source_path: Tuple[str, ...]
    target_state_path: Tuple[str, ...]
    target_event_name: str
    target_event_id_path: Tuple[str, ...]
    extra_name: Optional[str]


@dataclass
class _PendingEventRegistration:
    target_state_path: Tuple[str, ...]
    target_event_name: str
    mapping_extra_name: Optional[str]
    source_extra_name: Optional[str]
    import_alias: str
    source_path: Tuple[str, ...]


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

    host_explicit_def_names = {item.name for item in program.definitions}

    _assemble_state(
        node=program.root_state,
        current_state_path=(program.root_state.name,),
        import_base_dir=import_base_dir,
        import_stack=import_stack,
        host_program=program,
        host_explicit_def_names=host_explicit_def_names,
    )


def _assemble_state(
    node: dsl_nodes.StateDefinition,
    current_state_path: Tuple[str, ...],
    import_base_dir: str,
    import_stack: List[str],
    host_program: dsl_nodes.StateMachineDSLProgram,
    host_explicit_def_names,
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

        _assemble_program(
            program=imported_program,
            import_base_dir=os.path.dirname(resolved_file),
            import_stack=[*import_stack, resolved_file],
        )

        _apply_import_def_mappings(
            program=imported_program,
            import_item=import_item,
            owner_state_path=current_state_path,
        )
        _merge_imported_definitions(
            host_program=host_program,
            imported_program=imported_program,
            host_explicit_def_names=host_explicit_def_names,
            import_item=import_item,
            owner_state_path=current_state_path,
        )

        imported_root = imported_program.root_state
        event_mappings = _resolve_import_event_mappings(
            program=imported_program,
            import_item=import_item,
            owner_state_path=current_state_path,
        )
        imported_root.name = import_item.alias
        imported_root.extra_name = import_item.extra_name or imported_root.extra_name
        preserved_event_paths = _apply_import_event_mappings(
            program=imported_program,
            host_program=host_program,
            import_item=import_item,
            owner_state_path=current_state_path,
            resolved_event_mappings=event_mappings,
        )
        _rewrite_absolute_paths_for_imported_root(
            node=imported_root,
            instance_prefix=(*current_state_path[1:], import_item.alias),
            preserved_absolute_event_paths=preserved_event_paths,
        )
        imported_substates.append(imported_root)

    node.imports = []

    for subnode in node.substates:
        _assemble_state(
            node=subnode,
            current_state_path=(*current_state_path, subnode.name),
            import_base_dir=import_base_dir,
            import_stack=import_stack,
            host_program=host_program,
            host_explicit_def_names=host_explicit_def_names,
        )

    node.substates = [*imported_substates, *node.substates]


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
    preserved_absolute_event_paths: Optional[set] = None,
) -> None:
    preserved_absolute_event_paths = set(preserved_absolute_event_paths or set())
    for transition in node.transitions:
        if (
            transition.event_id is not None
            and transition.event_id.is_absolute
            and tuple(transition.event_id.path) not in preserved_absolute_event_paths
        ):
            transition.event_id.path = [*instance_prefix, *transition.event_id.path]

    for transition in node.force_transitions:
        if (
            transition.event_id is not None
            and transition.event_id.is_absolute
            and tuple(transition.event_id.path) not in preserved_absolute_event_paths
        ):
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
            preserved_absolute_event_paths=preserved_absolute_event_paths,
        )


def _resolve_import_event_mappings(
    program: dsl_nodes.StateMachineDSLProgram,
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> Dict[Tuple[str, ...], _ResolvedImportEventMapping]:
    event_mappings = [
        item
        for item in import_item.mappings
        if isinstance(item, dsl_nodes.ImportEventMapping)
    ]
    resolved = {}
    target_to_source = {}

    for mapping in event_mappings:
        if not mapping.source_event.is_absolute:
            raise SyntaxError(
                f"Invalid event mapping in import {import_item.alias!r} under state "
                f"{'.'.join(owner_state_path)!r}: source event {mapping.source_event} "
                "must be a module-absolute path."
            )

        source_path = tuple(mapping.source_event.path)
        (
            target_state_path,
            target_event_name,
            target_event_id_path,
        ) = _resolve_import_event_target_path(
            target_event=mapping.target_event,
            owner_state_path=owner_state_path,
        )
        if source_path in resolved:
            raise SyntaxError(
                f"Event mapping conflict: source event "
                f"{_format_event_path(source_path, is_absolute=True)!r} appears "
                f"multiple times in import {import_item.alias!r}."
            )
        target_key = (*target_state_path, target_event_name)
        if target_key in target_to_source and target_to_source[target_key] != source_path:
            raise SyntaxError(
                f"Event mapping conflict: import {import_item.alias!r} maps multiple "
                f"module events to the same host event "
                f"{_format_event_path(target_key, is_absolute=True)!r}."
            )

        resolved[source_path] = _ResolvedImportEventMapping(
            source_path=source_path,
            target_state_path=target_state_path,
            target_event_name=target_event_name,
            target_event_id_path=target_event_id_path,
            extra_name=mapping.extra_name,
        )
        target_to_source[target_key] = source_path

    return resolved


def _resolve_import_event_target_path(
    target_event: dsl_nodes.ChainID,
    owner_state_path: Tuple[str, ...],
) -> Tuple[Tuple[str, ...], str, Tuple[str, ...]]:
    if target_event.is_absolute:
        if len(target_event.path) < 1:
            raise SyntaxError("Invalid empty absolute target event path.")
        target_state_path = tuple((owner_state_path[0], *target_event.path[:-1]))
        return (
            target_state_path,
            target_event.path[-1],
            tuple(target_event.path),
        )
    else:
        if len(target_event.path) < 1:
            raise SyntaxError("Invalid empty relative target event path.")
        target_state_path = tuple((*owner_state_path, *target_event.path[:-1]))
        target_event_name = target_event.path[-1]
        target_event_id_path = tuple((*owner_state_path[1:], *target_event.path))
        return target_state_path, target_event_name, target_event_id_path


def _apply_import_event_mappings(
    program: dsl_nodes.StateMachineDSLProgram,
    host_program: dsl_nodes.StateMachineDSLProgram,
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
    resolved_event_mappings: Dict[Tuple[str, ...], _ResolvedImportEventMapping],
) -> set:
    source_event_names = {}
    _collect_event_extra_names(program.root_state, current_path=(), output=source_event_names)
    pending_registrations = []
    _rewrite_imported_state_event_paths(
        node=program.root_state,
        current_path=(),
        source_event_names=source_event_names,
        resolved_event_mappings=resolved_event_mappings,
        pending_registrations=pending_registrations,
    )
    _prune_mapped_source_event_definitions(
        node=program.root_state,
        current_path=(),
        resolved_event_mappings=resolved_event_mappings,
    )
    _validate_pending_event_registrations(
        registrations=pending_registrations,
        import_item=import_item,
        owner_state_path=owner_state_path,
    )
    _synthesize_host_events_for_import(
        host_root=host_program.root_state,
        registrations=pending_registrations,
    )
    return {
        tuple(item.target_state_path[1:]) + (item.target_event_name,)
        for item in pending_registrations
    }


def _collect_event_extra_names(
    node: dsl_nodes.StateDefinition,
    current_path: Tuple[str, ...],
    output: Dict[Tuple[str, ...], Optional[str]],
) -> None:
    current_state_path = tuple((*current_path, node.name))
    for event in node.events:
        output[(node.name, event.name)] = output.get((node.name, event.name), event.extra_name)
        output[(*current_state_path[1:], event.name)] = event.extra_name
        output[(event.name,)] = output.get((event.name,), event.extra_name)

    for subnode in node.substates:
        _collect_event_extra_names(subnode, current_state_path, output)


def _rewrite_imported_state_event_paths(
    node: dsl_nodes.StateDefinition,
    current_path: Tuple[str, ...],
    source_event_names: Dict[Tuple[str, ...], Optional[str]],
    resolved_event_mappings: Dict[Tuple[str, ...], _ResolvedImportEventMapping],
    pending_registrations: List[_PendingEventRegistration],
) -> None:
    current_state_path = tuple((*current_path, node.name))
    current_scope_path = current_state_path[1:]

    for transition in node.transitions:
        _rewrite_transition_event_id(
            transition=transition,
            current_scope_path=current_scope_path,
            source_event_names=source_event_names,
            resolved_event_mappings=resolved_event_mappings,
            pending_registrations=pending_registrations,
        )

    for transition in node.force_transitions:
        if transition.event_id is not None:
            _rewrite_transition_event_id(
                transition=transition,
                current_scope_path=current_scope_path,
                source_event_names=source_event_names,
                resolved_event_mappings=resolved_event_mappings,
                pending_registrations=pending_registrations,
            )

    for subnode in node.substates:
        _rewrite_imported_state_event_paths(
            node=subnode,
            current_path=current_state_path,
            source_event_names=source_event_names,
            resolved_event_mappings=resolved_event_mappings,
            pending_registrations=pending_registrations,
        )


def _rewrite_transition_event_id(
    transition,
    current_scope_path: Tuple[str, ...],
    source_event_names: Dict[Tuple[str, ...], Optional[str]],
    resolved_event_mappings: Dict[Tuple[str, ...], _ResolvedImportEventMapping],
    pending_registrations: List[_PendingEventRegistration],
) -> None:
    if transition.event_id is None:
        return

    if transition.event_id.is_absolute:
        source_path = tuple(transition.event_id.path)
    else:
        source_path = tuple((*current_scope_path, *transition.event_id.path))

    source_extra_name = _lookup_source_event_extra_name(
        source_path=source_path,
        source_event_names=source_event_names,
    )
    mapping = resolved_event_mappings.get(source_path)
    if mapping is not None:
        transition.event_id.is_absolute = True
        transition.event_id.path = list(mapping.target_event_id_path)
        pending_registrations.append(
            _PendingEventRegistration(
                target_state_path=mapping.target_state_path,
                target_event_name=mapping.target_event_name,
                mapping_extra_name=mapping.extra_name,
                source_extra_name=source_extra_name,
                import_alias="",
                source_path=source_path,
            )
        )
    elif transition.event_id.is_absolute:
        transition.event_id.path = [*current_scope_path, *transition.event_id.path]


def _prune_mapped_source_event_definitions(
    node: dsl_nodes.StateDefinition,
    current_path: Tuple[str, ...],
    resolved_event_mappings: Dict[Tuple[str, ...], _ResolvedImportEventMapping],
) -> None:
    current_state_path = tuple((*current_path, node.name))
    current_scope_path = current_state_path[1:]
    node.events = [
        item
        for item in node.events
        if tuple((*current_scope_path, item.name)) not in resolved_event_mappings
    ]

    for subnode in node.substates:
        _prune_mapped_source_event_definitions(
            node=subnode,
            current_path=current_state_path,
            resolved_event_mappings=resolved_event_mappings,
        )


def _lookup_source_event_extra_name(
    source_path: Tuple[str, ...],
    source_event_names: Dict[Tuple[str, ...], Optional[str]],
) -> Optional[str]:
    return source_event_names.get(source_path)


def _validate_pending_event_registrations(
    registrations: List[_PendingEventRegistration],
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> None:
    by_target = {}
    for item in registrations:
        target_key = (*item.target_state_path, item.target_event_name)
        if target_key not in by_target:
            by_target[target_key] = item
            continue

        existing = by_target[target_key]
        if item.mapping_extra_name is not None and existing.mapping_extra_name is not None:
            if item.mapping_extra_name != existing.mapping_extra_name:
                raise SyntaxError(
                    f"Event mapping conflict: host event "
                    f"{_format_event_path(target_key, is_absolute=True)!r} "
                    f"receives conflicting display names "
                    f"{existing.mapping_extra_name!r} and {item.mapping_extra_name!r} "
                    f"in import {import_item.alias!r} under state "
                    f"{'.'.join(owner_state_path)!r}."
                )


def _synthesize_host_events_for_import(
    host_root: dsl_nodes.StateDefinition,
    registrations: List[_PendingEventRegistration],
) -> None:
    if not registrations:
        return

    for item in registrations:
        owner_state = _ensure_state_path_exists(
            root=host_root,
            state_path=item.target_state_path,
        )
        event_name = item.target_event_name
        existing_event = None
        for event in owner_state.events:
            if event.name == event_name:
                existing_event = event
                break

        final_extra_name = (
            item.mapping_extra_name
            or (existing_event.extra_name if existing_event is not None else None)
            or item.source_extra_name
        )
        if existing_event is None:
            owner_state.events.append(
                dsl_nodes.EventDefinition(name=event_name, extra_name=final_extra_name)
            )
        else:
            if (
                item.mapping_extra_name is not None
                and existing_event.extra_name is not None
                and existing_event.extra_name != item.mapping_extra_name
            ):
                raise SyntaxError(
                    f"Event mapping conflict: host event "
                    f"{_format_event_path((*item.target_state_path, event_name), is_absolute=True)!r} "
                    f"receives conflicting display names "
                    f"{existing_event.extra_name!r} and {item.mapping_extra_name!r}."
                )
            if existing_event.extra_name is None and final_extra_name is not None:
                existing_event.extra_name = final_extra_name


def _ensure_state_path_exists(
    root: dsl_nodes.StateDefinition,
    state_path: Tuple[str, ...],
) -> dsl_nodes.StateDefinition:
    if not state_path:
        raise SyntaxError("Invalid empty host state path for event mapping.")
    if root.name != state_path[0]:
        raise SyntaxError(
            f"Invalid host root path for event mapping: expected root {root.name!r}, "
            f"got {state_path[0]!r}."
        )

    state = root
    for segment in state_path[1:]:
        next_state = None
        for subnode in state.substates:
            if subnode.name == segment:
                next_state = subnode
                break
        if next_state is None:
            raise SyntaxError(
                f"Event mapping target state "
                f"{_format_event_path(state_path, is_absolute=True)!r} does not exist "
                f"in host model."
            )
        state = next_state
    return state


def _format_event_path(path: Tuple[str, ...], is_absolute: bool) -> str:
    prefix = "/" if is_absolute else ""
    return prefix + ".".join(path)


def _apply_import_def_mappings(
    program: dsl_nodes.StateMachineDSLProgram,
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> None:
    def_mappings = [
        item
        for item in import_item.mappings
        if isinstance(item, dsl_nodes.ImportDefMapping)
    ]
    if not def_mappings:
        def_mappings = [
            dsl_nodes.ImportDefMapping(
                selector=dsl_nodes.ImportDefFallbackSelector(),
                target_template=dsl_nodes.ImportDefTargetTemplate(
                    template=f"{import_item.alias}_*"
                ),
            )
        ]

    if not program.definitions:
        return

    source_to_target = {}
    target_to_source = {}
    for def_item in program.definitions:
        target_name = _resolve_import_variable_target(
            source_name=def_item.name,
            mappings=def_mappings,
            import_item=import_item,
            owner_state_path=owner_state_path,
        )
        if (
            target_name in target_to_source
            and target_to_source[target_name] != def_item.name
        ):
            raise SyntaxError(
                f"Variable mapping conflict: import {import_item.alias!r} maps "
                f"multiple source variables to the same target variable "
                f"{target_name!r}."
            )

        source_to_target[def_item.name] = target_name
        target_to_source[target_name] = def_item.name

    for def_item in program.definitions:
        def_item.expr = _rewrite_expr_variables(def_item.expr, source_to_target)
        def_item.name = source_to_target[def_item.name]

    _rewrite_state_variable_references(program.root_state, source_to_target)


def _merge_imported_definitions(
    host_program: dsl_nodes.StateMachineDSLProgram,
    imported_program: dsl_nodes.StateMachineDSLProgram,
    host_explicit_def_names,
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> None:
    existing_definitions = {item.name: item for item in host_program.definitions}
    for def_item in imported_program.definitions:
        existing_item = existing_definitions.get(def_item.name)
        if existing_item is None:
            host_program.definitions.append(def_item)
            existing_definitions[def_item.name] = def_item
            continue

        if existing_item.type != def_item.type:
            if def_item.name in host_explicit_def_names:
                raise SyntaxError(
                    f"Variable mapping conflict: target variable {def_item.name!r} "
                    f"already exists in host model as type {existing_item.type!r}, "
                    f"cannot bind imported type {def_item.type!r}."
                )
            else:
                raise SyntaxError(
                    f"Variable mapping conflict: target variable {def_item.name!r} "
                    f"receives incompatible imported types {existing_item.type!r} "
                    f"and {def_item.type!r}."
                )

        if def_item.name in host_explicit_def_names:
            continue

        if existing_item.expr != def_item.expr:
            raise SyntaxError(
                f"Variable mapping conflict: target variable {def_item.name!r} has "
                f"conflicting initial values."
            )

    imported_program.definitions = []


def _resolve_import_variable_target(
    source_name: str,
    mappings: List[dsl_nodes.ImportDefMapping],
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> str:
    exact_rules = []
    set_rules = []
    pattern_rules = []
    fallback_rules = []
    seen_exact_names = {}
    seen_set_names = {}

    for mapping in mappings:
        selector = mapping.selector
        if isinstance(selector, dsl_nodes.ImportDefExactSelector):
            if selector.name in seen_exact_names:
                raise SyntaxError(
                    f"Variable mapping conflict: duplicated exact selector "
                    f"{selector.name!r} in import {import_item.alias!r}."
                )
            seen_exact_names[selector.name] = mapping
            exact_rules.append(mapping)
        elif isinstance(selector, dsl_nodes.ImportDefSetSelector):
            local_names = set()
            for item in selector.names:
                if item in local_names:
                    raise SyntaxError(
                        f"Variable mapping conflict: duplicated selector name "
                        f"{item!r} inside set rule in import {import_item.alias!r}."
                    )
                if item in seen_set_names:
                    raise SyntaxError(
                        f"Variable mapping conflict: selector name {item!r} appears "
                        f"in multiple set rules in import {import_item.alias!r}."
                    )
                local_names.add(item)
                seen_set_names[item] = mapping
            set_rules.append(mapping)
        elif isinstance(selector, dsl_nodes.ImportDefPatternSelector):
            pattern_rules.append(mapping)
        elif isinstance(selector, dsl_nodes.ImportDefFallbackSelector):
            fallback_rules.append(mapping)
        else:
            raise TypeError(f"Unknown import def selector - {selector!r}.")

    if len(fallback_rules) > 1:
        raise SyntaxError(
            f"Variable mapping conflict: multiple fallback rules found in import "
            f"{import_item.alias!r}."
        )

    exact_matches = [
        item
        for item in exact_rules
        if item.selector.name == source_name
    ]
    if exact_matches:
        return _render_target_template(
            template=exact_matches[0].target_template.template,
            source_name=source_name,
            captures=[],
            import_item=import_item,
            owner_state_path=owner_state_path,
        )

    set_matches = [
        item
        for item in set_rules
        if source_name in item.selector.names
    ]
    if len(set_matches) > 1:
        raise SyntaxError(
            f"Variable mapping conflict: selector name {source_name!r} matches "
            f"multiple set rules in import {import_item.alias!r}."
        )
    if set_matches:
        return _render_target_template(
            template=set_matches[0].target_template.template,
            source_name=source_name,
            captures=[],
            import_item=import_item,
            owner_state_path=owner_state_path,
        )

    pattern_matches = []
    for item in pattern_rules:
        captures = _match_pattern_selector(item.selector.pattern, source_name)
        if captures is not None:
            pattern_matches.append((item, captures))
    if len(pattern_matches) > 1:
        raise SyntaxError(
            f"Variable mapping conflict: source variable {source_name!r} matches "
            f"multiple pattern rules in import {import_item.alias!r}."
        )
    if pattern_matches:
        item, captures = pattern_matches[0]
        return _render_target_template(
            template=item.target_template.template,
            source_name=source_name,
            captures=captures,
            import_item=import_item,
            owner_state_path=owner_state_path,
        )

    if fallback_rules:
        return _render_target_template(
            template=fallback_rules[0].target_template.template,
            source_name=source_name,
            captures=[],
            import_item=import_item,
            owner_state_path=owner_state_path,
        )

    raise SyntaxError(
        f"Variable mapping conflict: source variable {source_name!r} in import "
        f"{import_item.alias!r} under state {'.'.join(owner_state_path)!r} is not "
        f"matched by any def mapping rule."
    )


def _match_pattern_selector(pattern: str, source_name: str):
    parts = pattern.split("*")
    regex = "^%s$" % "(.*?)".join(re.escape(part) for part in parts)
    match = re.match(regex, source_name)
    if match is None:
        return None
    return list(match.groups())


def _render_target_template(
    template: str,
    source_name: str,
    captures: List[str],
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> str:
    rendered = []
    i = 0
    while i < len(template):
        if template[i] == "$":
            if i + 1 < len(template) and template[i + 1] == "{":
                end_index = template.find("}", i + 2)
                if end_index < 0:
                    raise SyntaxError(
                        f"Invalid variable mapping template {template!r} in import "
                        f"{import_item.alias!r}: missing closing '}}'."
                    )
                raw_index = template[i + 2:end_index]
                if not raw_index.isdigit():
                    raise SyntaxError(
                        f"Invalid variable mapping template {template!r} in import "
                        f"{import_item.alias!r}: placeholder index {raw_index!r} "
                        f"is not numeric."
                    )
                rendered.append(
                    _mapping_placeholder_value(
                        source_name=source_name,
                        captures=captures,
                        index=int(raw_index),
                        template=template,
                        import_item=import_item,
                        owner_state_path=owner_state_path,
                    )
                )
                i = end_index + 1
                continue
            elif i + 1 < len(template) and template[i + 1].isdigit():
                rendered.append(
                    _mapping_placeholder_value(
                        source_name=source_name,
                        captures=captures,
                        index=int(template[i + 1]),
                        template=template,
                        import_item=import_item,
                        owner_state_path=owner_state_path,
                    )
                )
                i += 2
                continue

        if template[i] == "*":
            if len(captures) > 1:
                raise SyntaxError(
                    f"Invalid variable mapping template {template!r} in import "
                    f"{import_item.alias!r}: bare '*' is ambiguous when the source "
                    f"selector has multiple capture groups."
                )
            rendered.append(source_name if not captures else captures[0])
            i += 1
            continue

        rendered.append(template[i])
        i += 1

    return "".join(rendered)


def _mapping_placeholder_value(
    source_name: str,
    captures: List[str],
    index: int,
    template: str,
    import_item: dsl_nodes.ImportStatement,
    owner_state_path: Tuple[str, ...],
) -> str:
    if index == 0:
        return source_name
    elif 1 <= index <= len(captures):
        return captures[index - 1]
    else:
        raise SyntaxError(
            f"Invalid variable mapping template {template!r} in import "
            f"{import_item.alias!r} under state {'.'.join(owner_state_path)!r}: "
            f"placeholder ${index} is out of range for source variable "
            f"{source_name!r}."
        )


def _rewrite_expr_variables(expr, source_to_target: Dict[str, str]):
    if isinstance(expr, dsl_nodes.Name):
        if expr.name in source_to_target:
            expr.name = source_to_target[expr.name]
    elif isinstance(expr, dsl_nodes.Paren):
        expr.expr = _rewrite_expr_variables(expr.expr, source_to_target)
    elif isinstance(expr, dsl_nodes.UnaryOp):
        expr.expr = _rewrite_expr_variables(expr.expr, source_to_target)
    elif isinstance(expr, dsl_nodes.BinaryOp):
        expr.expr1 = _rewrite_expr_variables(expr.expr1, source_to_target)
        expr.expr2 = _rewrite_expr_variables(expr.expr2, source_to_target)
    elif isinstance(expr, dsl_nodes.ConditionalOp):
        expr.cond = _rewrite_expr_variables(expr.cond, source_to_target)
        expr.value_true = _rewrite_expr_variables(expr.value_true, source_to_target)
        expr.value_false = _rewrite_expr_variables(expr.value_false, source_to_target)
    elif isinstance(expr, dsl_nodes.UFunc):
        expr.expr = _rewrite_expr_variables(expr.expr, source_to_target)

    return expr


def _rewrite_operation_statement_variables(statement, source_to_target: Dict[str, str]):
    if isinstance(statement, dsl_nodes.OperationAssignment):
        if statement.name in source_to_target:
            statement.name = source_to_target[statement.name]
        statement.expr = _rewrite_expr_variables(statement.expr, source_to_target)
    elif isinstance(statement, dsl_nodes.OperationIf):
        for branch in statement.branches:
            if branch.condition is not None:
                branch.condition = _rewrite_expr_variables(
                    branch.condition, source_to_target
                )
            for item in branch.statements:
                _rewrite_operation_statement_variables(item, source_to_target)
    else:
        raise TypeError(f"Unknown operation statement node - {statement!r}.")


def _rewrite_operation_block_variables(items, source_to_target: Dict[str, str]):
    for item in items:
        _rewrite_operation_statement_variables(item, source_to_target)


def _rewrite_state_variable_references(
    node: dsl_nodes.StateDefinition,
    source_to_target: Dict[str, str],
) -> None:
    for transition in node.transitions:
        if transition.condition_expr is not None:
            transition.condition_expr = _rewrite_expr_variables(
                transition.condition_expr,
                source_to_target,
            )
        _rewrite_operation_block_variables(transition.post_operations, source_to_target)

    for transition in node.force_transitions:
        if transition.condition_expr is not None:
            transition.condition_expr = _rewrite_expr_variables(
                transition.condition_expr,
                source_to_target,
            )

    for enter_item in node.enters:
        if isinstance(enter_item, dsl_nodes.EnterOperations):
            _rewrite_operation_block_variables(enter_item.operations, source_to_target)

    for during_item in node.durings:
        if isinstance(during_item, dsl_nodes.DuringOperations):
            _rewrite_operation_block_variables(during_item.operations, source_to_target)

    for exit_item in node.exits:
        if isinstance(exit_item, dsl_nodes.ExitOperations):
            _rewrite_operation_block_variables(exit_item.operations, source_to_target)

    for during_aspect_item in node.during_aspects:
        if isinstance(during_aspect_item, dsl_nodes.DuringAspectOperations):
            _rewrite_operation_block_variables(
                during_aspect_item.operations,
                source_to_target,
            )

    for subnode in node.substates:
        _rewrite_state_variable_references(subnode, source_to_target)
