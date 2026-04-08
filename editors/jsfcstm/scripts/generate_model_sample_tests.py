#!/usr/bin/env python
"""
Generate pyfcstm-backed jsfcstm model sample tests.

This script treats the Python implementation as the reference model:

1. One FCSTM sample example is loaded through ``pyfcstm``.
2. The resulting model is normalized into a JSON-serializable snapshot.
3. The model is converted back into import-free DSL text via
   ``str(model.to_ast_node())``.
4. A runnable TypeScript test case is emitted to the requested output path.

At test runtime, jsfcstm parses the generated DSL text and compares its own
runtime model snapshot against the Python-generated expectation. This keeps the
runtime tests fully TypeScript-based while ensuring the expected answers come
directly from pyfcstm.
"""

from __future__ import annotations

import json
import os
import argparse
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Union

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_CODES_DIR = REPO_ROOT / "test" / "testfile" / "sample_codes"
OUTPUT_DIR = REPO_ROOT / "editors" / "jsfcstm" / "test" / "model-py-generated"
SUPPORT_FILE = OUTPUT_DIR / "support.ts"

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model.expr import (  # noqa: E402
    BinaryOp,
    Boolean,
    ConditionalOp,
    Float,
    Integer,
    UFunc,
    UnaryOp,
    Variable,
)
from pyfcstm.model.model import (  # noqa: E402
    Event,
    IfBlock,
    OnAspect,
    OnStage,
    Operation,
    State,
    Transition,
    VarDefine,
    parse_dsl_node_to_state_machine,
)


def _path_name(path: Iterable[str]) -> str:
    return ".".join(path)


def _normalize_special_state(value: Any) -> str:
    if value is dsl_nodes.INIT_STATE:
        return "INIT_STATE"
    if value is dsl_nodes.EXIT_STATE:
        return "EXIT_STATE"
    if value is dsl_nodes.ALL:
        return "ALL"
    return str(value)


def _normalize_expr(expr) -> Dict[str, Any]:
    if isinstance(expr, Integer):
        return {
            "type": "Integer",
            "value": expr.value,
        }
    if isinstance(expr, Float):
        return {
            "type": "Float",
            "value": expr.value,
        }
    if isinstance(expr, Boolean):
        return {
            "type": "Boolean",
            "value": expr.value,
        }
    if isinstance(expr, Variable):
        return {
            "type": "Variable",
            "name": expr.name,
        }
    if isinstance(expr, UnaryOp):
        return {
            "type": "UnaryOp",
            "op": expr.op,
            "x": _normalize_expr(expr.x),
        }
    if isinstance(expr, BinaryOp):
        return {
            "type": "BinaryOp",
            "op": expr.op,
            "x": _normalize_expr(expr.x),
            "y": _normalize_expr(expr.y),
        }
    if isinstance(expr, ConditionalOp):
        return {
            "type": "ConditionalOp",
            "cond": _normalize_expr(expr.cond),
            "if_true": _normalize_expr(expr.if_true),
            "if_false": _normalize_expr(expr.if_false),
        }
    if isinstance(expr, UFunc):
        return {
            "type": "UFunc",
            "func": expr.func,
            "x": _normalize_expr(expr.x),
        }

    raise TypeError(f"Unsupported model expression: {expr!r}")


def _normalize_statement(statement) -> Dict[str, Any]:
    if isinstance(statement, Operation):
        return {
            "type": "Operation",
            "var_name": statement.var_name,
            "expr": _normalize_expr(statement.expr),
        }
    if isinstance(statement, IfBlock):
        return {
            "type": "IfBlock",
            "branches": [
                {
                    "condition": _normalize_expr(branch.condition)
                    if branch.condition is not None
                    else None,
                    "statements": [
                        _normalize_statement(item) for item in branch.statements
                    ],
                }
                for branch in statement.branches
            ],
        }

    raise TypeError(f"Unsupported model statement: {statement!r}")


def _normalize_action(action: Union[OnStage, OnAspect]) -> Dict[str, Any]:
    return {
        "type": type(action).__name__,
        "stage": action.stage,
        "aspect": action.aspect,
        "name": action.name,
        "doc": action.doc,
        "operations": [_normalize_statement(item) for item in action.operations],
        "is_abstract": action.is_abstract,
        "is_ref": action.is_ref,
        "is_aspect": action.is_aspect,
        "state_path": list(action.state_path),
        "func_name": action.func_name,
        "parent": _path_name(action.parent.path) if action.parent is not None else None,
        "ref_state_path": list(action.ref_state_path)
        if action.ref_state_path is not None
        else None,
        "ref_resolved": bool(action.ref),
        "ref_target_qualified_name": action.ref.func_name if action.ref else None,
    }


def _normalize_transition(transition: Transition) -> Dict[str, Any]:
    return {
        "from_state": _normalize_special_state(transition.from_state),
        "to_state": _normalize_special_state(transition.to_state),
        "event": transition.event.path_name if transition.event is not None else None,
        "guard": _normalize_expr(transition.guard) if transition.guard is not None else None,
        "effects": [_normalize_statement(item) for item in transition.effects],
        "parent": _path_name(transition.parent.path) if transition.parent is not None else None,
    }


def _normalize_event(event: Event) -> Dict[str, Any]:
    return {
        "name": event.name,
        "state_path": list(event.state_path),
        "path": list(event.path),
        "path_name": event.path_name,
        "extra_name": event.extra_name,
    }


def _normalize_list_with_ids(
    items: Iterable[Union[Tuple[int, Any], Any]]
) -> List[Union[str, List[Union[int, str]]]]:
    retval = []
    for item in items:
        if isinstance(item, tuple):
            retval.append([item[0], item[1].func_name])
        else:
            retval.append(item.func_name)
    return retval


def _normalize_recursive_actions(
    items: Iterable[Union[Tuple[int, State, Union[OnStage, OnAspect]], Tuple[State, Union[OnStage, OnAspect]]]]
) -> List[List[Union[int, str]]]:
    retval = []
    for item in items:
        if len(item) == 3:
            id_, state, action = item
            retval.append([id_, _path_name(state.path), action.func_name])
        else:
            state, action = item
            retval.append([_path_name(state.path), action.func_name])
    return retval


def _normalize_state(state: State) -> Dict[str, Any]:
    return {
        "name": state.name,
        "path": list(state.path),
        "parent": _path_name(state.parent.path) if state.parent is not None else None,
        "substates": list(state.substates.keys()),
        "events": {
            name: _normalize_event(event)
            for name, event in sorted(state.events.items(), key=lambda x: x[0])
        },
        "transitions": [_normalize_transition(item) for item in state.transitions],
        "named_functions": {
            name: _normalize_action(action)
            for name, action in sorted(state.named_functions.items(), key=lambda x: x[0])
        },
        "on_enters": [_normalize_action(item) for item in state.on_enters],
        "on_durings": [_normalize_action(item) for item in state.on_durings],
        "on_exits": [_normalize_action(item) for item in state.on_exits],
        "on_during_aspects": [
            _normalize_action(item) for item in state.on_during_aspects
        ],
        "substate_name_to_id": dict(state.substate_name_to_id),
        "extra_name": state.extra_name,
        "is_pseudo": state.is_pseudo,
        "is_leaf_state": state.is_leaf_state,
        "is_root_state": state.is_root_state,
        "is_stoppable": state.is_stoppable,
        "abstract_on_enters": [item.func_name for item in state.abstract_on_enters],
        "non_abstract_on_enters": [
            item.func_name for item in state.non_abstract_on_enters
        ],
        "abstract_on_durings": [item.func_name for item in state.abstract_on_durings],
        "non_abstract_on_durings": [
            item.func_name for item in state.non_abstract_on_durings
        ],
        "abstract_on_exits": [item.func_name for item in state.abstract_on_exits],
        "non_abstract_on_exits": [
            item.func_name for item in state.non_abstract_on_exits
        ],
        "abstract_on_during_aspects": [
            item.func_name for item in state.abstract_on_during_aspects
        ],
        "non_abstract_on_during_aspects": [
            item.func_name for item in state.non_abstract_on_during_aspects
        ],
        "init_transitions": [_normalize_transition(item) for item in state.init_transitions],
        "transitions_from": [_normalize_transition(item) for item in state.transitions_from],
        "transitions_to": [_normalize_transition(item) for item in state.transitions_to],
        "transitions_entering_children": [
            _normalize_transition(item) for item in state.transitions_entering_children
        ],
        "transitions_entering_children_simplified": [
            _normalize_transition(item) if item is not None else None
            for item in state.transitions_entering_children_simplified
        ],
        "list_on_enters": _normalize_list_with_ids(state.list_on_enters()),
        "list_on_enters_with_ids": _normalize_list_with_ids(
            state.list_on_enters(with_ids=True)
        ),
        "list_on_durings": _normalize_list_with_ids(state.list_on_durings()),
        "list_on_durings_with_ids": _normalize_list_with_ids(
            state.list_on_durings(with_ids=True)
        ),
        "list_on_exits": _normalize_list_with_ids(state.list_on_exits()),
        "list_on_exits_with_ids": _normalize_list_with_ids(
            state.list_on_exits(with_ids=True)
        ),
        "list_on_during_aspects": _normalize_list_with_ids(
            state.list_on_during_aspects()
        ),
        "list_on_during_aspects_with_ids": _normalize_list_with_ids(
            state.list_on_during_aspects(with_ids=True)
        ),
        "list_on_during_aspect_recursively": _normalize_recursive_actions(
            state.list_on_during_aspect_recursively()
        ),
        "list_on_during_aspect_recursively_with_ids": _normalize_recursive_actions(
            state.list_on_during_aspect_recursively(with_ids=True)
        ),
        "walk_states": [_path_name(item.path) for item in state.walk_states()],
    }


def _normalize_ast_chain_id(node: dsl_nodes.ChainID) -> Dict[str, Any]:
    return {
        "__class__": "ChainID",
        "path": list(node.path),
        "is_absolute": bool(node.is_absolute),
    }


def _normalize_ast_expr(expr) -> Dict[str, Any]:
    if isinstance(expr, (dsl_nodes.Boolean, dsl_nodes.Integer, dsl_nodes.HexInt, dsl_nodes.Float, dsl_nodes.Constant)):
        return {
            "__class__": type(expr).__name__,
            "raw": expr.raw,
        }
    if isinstance(expr, dsl_nodes.Name):
        return {
            "__class__": "Name",
            "name": expr.name,
        }
    if isinstance(expr, dsl_nodes.Paren):
        return {
            "__class__": "Paren",
            "expr": _normalize_ast_expr(expr.expr),
        }
    if isinstance(expr, dsl_nodes.UnaryOp):
        return {
            "__class__": "UnaryOp",
            "op": expr.op,
            "expr": _normalize_ast_expr(expr.expr),
        }
    if isinstance(expr, dsl_nodes.BinaryOp):
        return {
            "__class__": "BinaryOp",
            "expr1": _normalize_ast_expr(expr.expr1),
            "op": expr.op,
            "expr2": _normalize_ast_expr(expr.expr2),
        }
    if isinstance(expr, dsl_nodes.ConditionalOp):
        return {
            "__class__": "ConditionalOp",
            "cond": _normalize_ast_expr(expr.cond),
            "value_true": _normalize_ast_expr(expr.value_true),
            "value_false": _normalize_ast_expr(expr.value_false),
        }
    if isinstance(expr, dsl_nodes.UFunc):
        return {
            "__class__": "UFunc",
            "func": expr.func,
            "expr": _normalize_ast_expr(expr.expr),
        }

    raise TypeError(f"Unsupported AST expression: {expr!r}")


def _normalize_ast_operation(statement) -> Dict[str, Any]:
    if isinstance(statement, dsl_nodes.OperationAssignment):
        return {
            "__class__": "OperationAssignment",
            "name": statement.name,
            "expr": _normalize_ast_expr(statement.expr),
        }
    if isinstance(statement, dsl_nodes.OperationIf):
        return {
            "__class__": "OperationIf",
            "branches": [
                {
                    "__class__": "OperationIfBranch",
                    "condition": _normalize_ast_expr(branch.condition)
                    if branch.condition is not None
                    else None,
                    "statements": [
                        _normalize_ast_operation(item) for item in branch.statements
                    ],
                }
                for branch in statement.branches
            ],
        }

    raise TypeError(f"Unsupported AST operation: {statement!r}")


def _normalize_ast_action(action) -> Dict[str, Any]:
    operations = None
    ref = None
    doc = None

    if hasattr(action, "operations"):
        operations = [_normalize_ast_operation(item) for item in action.operations]
    if hasattr(action, "ref") and action.ref is not None:
        ref = _normalize_ast_chain_id(action.ref)
    if hasattr(action, "doc"):
        doc = action.doc

    return {
        "__class__": type(action).__name__,
        "name": getattr(action, "name", None),
        "aspect": getattr(action, "aspect", None),
        "doc": doc,
        "operations": operations,
        "ref": ref,
    }


def _normalize_ast_transition(transition: dsl_nodes.TransitionDefinition) -> Dict[str, Any]:
    return {
        "__class__": "TransitionDefinition",
        "from_state": _normalize_special_state(transition.from_state),
        "to_state": _normalize_special_state(transition.to_state),
        "event_id": _normalize_ast_chain_id(transition.event_id)
        if transition.event_id is not None
        else None,
        "condition_expr": _normalize_ast_expr(transition.condition_expr)
        if transition.condition_expr is not None
        else None,
        "post_operations": [
            _normalize_ast_operation(item) for item in transition.post_operations
        ],
    }


def _normalize_ast_state(state: dsl_nodes.StateDefinition) -> Dict[str, Any]:
    return {
        "__class__": "StateDefinition",
        "name": state.name,
        "extra_name": state.extra_name,
        "events": [
            {
                "__class__": "EventDefinition",
                "name": item.name,
                "extra_name": item.extra_name,
            }
            for item in state.events
        ],
        "substates": [_normalize_ast_state(item) for item in state.substates],
        "transitions": [
            _normalize_ast_transition(item) for item in state.transitions
        ],
        "enters": [_normalize_ast_action(item) for item in state.enters],
        "durings": [_normalize_ast_action(item) for item in state.durings],
        "exits": [_normalize_ast_action(item) for item in state.exits],
        "during_aspects": [
            _normalize_ast_action(item) for item in state.during_aspects
        ],
        "is_pseudo": bool(state.is_pseudo),
    }


def _normalize_ast_program(
    program: dsl_nodes.StateMachineDSLProgram,
) -> Dict[str, Any]:
    return {
        "__class__": "StateMachineDSLProgram",
        "definitions": [
            {
                "__class__": "DefAssignment",
                "name": item.name,
                "type": item.type,
                "expr": _normalize_ast_expr(item.expr),
            }
            for item in program.definitions
        ],
        "root_state": _normalize_ast_state(program.root_state),
    }


def _normalize_model(model) -> Dict[str, Any]:
    walked_states = list(model.walk_states())
    all_events = []
    all_actions = []
    for state in walked_states:
        all_events.extend(state.events.values())
        all_actions.extend(
            [*state.on_enters, *state.on_durings, *state.on_exits, *state.on_during_aspects]
        )
    return {
        "defines": {
            name: {
                "type": definition.type,
                "init": _normalize_expr(definition.init),
            }
            for name, definition in sorted(model.defines.items(), key=lambda x: x[0])
        },
        "root_state": model.root_state.name,
        "walk_states": [_path_name(state.path) for state in walked_states],
        "all_events": [_normalize_event(event) for event in all_events],
        "all_actions": [action.func_name for action in all_actions],
        "states": {
            _path_name(state.path): _normalize_state(state) for state in walked_states
        },
        "ast": _normalize_ast_program(model.to_ast_node()),
    }


def _write_test_file(
    relative_source_path: str,
    source: str | None,
    expected: Dict[str, Any],
    output_file: Path,
    sample_files: List[Tuple[str, str]] | None = None,
    entry_file: str | None = None,
) -> None:
    support_import_path = os.path.relpath(SUPPORT_FILE, output_file.parent).replace(
        os.path.sep, "/"
    )
    if support_import_path.endswith(".ts"):
        support_import_path = support_import_path[:-3]
    if not support_import_path.startswith("."):
        support_import_path = f"./{support_import_path}"

    if sample_files is None and entry_file is None:
        if source is None:
            raise ValueError("Single-file sample tests must provide source text.")
        case_body = (
            f"    source: {json.dumps(source, ensure_ascii=False)},\n"
            f"    expected: {json.dumps(expected, ensure_ascii=False, indent=4)},\n"
        )
    elif sample_files is not None and entry_file is not None:
        if source is not None:
            raise ValueError("Multi-file sample tests must not embed source text.")
        case_body = (
            "    source: null,\n"
            f"    files: {json.dumps(sample_files, ensure_ascii=False, indent=4)},\n"
            f"    entryFile: {json.dumps(entry_file, ensure_ascii=False)},\n"
            f"    expected: {json.dumps(expected, ensure_ascii=False, indent=4)},\n"
        )
    else:
        raise ValueError(
            "Sample tests must be either single-file source-based or multi-file workspace-based."
        )

    content = (
        "// Generated by scripts/generate_model_sample_tests.py. Do not edit manually.\n"
        f"import {{runPyGeneratedModelCase}} from {json.dumps(support_import_path, ensure_ascii=False)};\n\n"
        "runPyGeneratedModelCase({\n"
        f"    name: {json.dumps(relative_source_path, ensure_ascii=False)},\n"
        f"    relativeSourcePath: {json.dumps(relative_source_path, ensure_ascii=False)},\n"
        f"{case_body}"
        "});\n"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content, encoding="utf-8")


def _resolve_sample_input(sample_input: Path) -> Tuple[Path, str]:
    sample_root = SAMPLE_CODES_DIR.resolve()
    resolved_input = sample_input.resolve()
    try:
        relative_path = resolved_input.relative_to(sample_root)
    except ValueError as err:
        raise ValueError(
            f"Sample input must be under {SAMPLE_CODES_DIR}, got {sample_input}."
        ) from err

    if resolved_input.is_dir():
        entry_file = resolved_input / "main.fcstm"
        if not entry_file.is_file():
            raise FileNotFoundError(
                f"Sample directory {sample_input} does not contain main.fcstm."
            )
        return entry_file, relative_path.as_posix()

    if resolved_input.is_file() and resolved_input.suffix == ".fcstm":
        return resolved_input, relative_path.as_posix()

    raise FileNotFoundError(f"Sample input {sample_input} is neither a DSL file nor a sample directory.")


def _collect_sample_files(sample_input: Path) -> Tuple[List[Tuple[str, str]] | None, str | None]:
    resolved_input = sample_input.resolve()
    if resolved_input.is_dir():
        files = []
        for item in sorted(resolved_input.rglob("*.fcstm")):
            files.append(
                (
                    item.relative_to(resolved_input).as_posix(),
                    item.read_text(encoding="utf-8"),
                )
            )
        return files, "main.fcstm"

    return None, None


def generate_sample_test(sample_input: Path, output_file: Path) -> None:
    entry_file, relative_source_path = _resolve_sample_input(sample_input)
    ast_node = parse_state_machine_dsl(entry_file.read_text(encoding="utf-8"))
    model = parse_dsl_node_to_state_machine(ast_node, path=entry_file)
    source = str(model.to_ast_node())
    expected = _normalize_model(model)
    sample_files, entry_file_path = _collect_sample_files(sample_input)
    _write_test_file(
        relative_source_path,
        source if sample_files is None else None,
        expected,
        output_file,
        sample_files=sample_files,
        entry_file=entry_file_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one pyfcstm-backed jsfcstm model sample test file."
    )
    parser.add_argument(
        "-i",
        "--input-file",
        required=True,
        help="Input sample file or sample directory under test/testfile/sample_codes.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        required=True,
        help="Output TypeScript test file path.",
    )
    args = parser.parse_args()

    generate_sample_test(Path(args.input_file), Path(args.output_file))


if __name__ == "__main__":
    main()
