"""
Public Python data and browser-viewer API for FCSTM diagrams.

The module keeps the portable data contract separate from editor metadata. A
``DiagramData`` value is deterministic JSON and contains no local paths or
source ranges. Browser HTML may additionally carry an embedded source sidecar
so the source and diagram panes can be linked without network access.

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> data = model.diagram().to_dict()
    >>> data['rootState']['name']
    'Root'
"""

import atexit
import base64
import contextlib
import errno
import hashlib
import html as html_module
import json
import logging
import math
import os
import re
import shutil
import stat
import signal
import subprocess
import sys
import tempfile
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from collections.abc import Iterable
from typing import Iterator, Any, Dict, List, Mapping, Optional, Tuple, Union

from pygments import lex
from pygments.formatters import HtmlFormatter

from ..highlight import FcstmLexer
from ..utils.logging import get_logger
from ..model.model import (
    Event,
    IfBlock,
    Operation,
    OperationStatement,
    State,
    StateMachine,
    Transition,
)
from ..utils.validate import Span
from .engine import (
    DiagramUnavailableError,
    _asset_bytes,
    _asset_failure,
)

_logger = get_logger(__name__)

__all__ = [
    "DiagramData",
    "DiagramOptions",
    "DiagramViewState",
    "Diagram",
]


def _text(value: Any) -> str:
    """Return deterministic DSL text for a model value."""
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _portable_value(value: Mapping[str, Any]) -> Dict[str, Any]:
    """Copy renderer data after removing editor-only source metadata."""
    try:
        payload = json.dumps(
            _thaw_value(value), ensure_ascii=False, sort_keys=True, allow_nan=False
        )
    except ValueError as error:
        # allow_nan=False raises for NaN and +/-Infinity. Python writes those as
        # bare NaN/Infinity tokens, which no JSON parser accepts — the browser
        # this data is built for rejects the document outright — so the class
        # cannot claim to be JSON-compatible and also carry them.
        raise ValueError(
            "DiagramData values must be JSON numbers; NaN and infinity cannot be "
            "represented and would produce a document no JSON parser accepts (%s)"
            % error
        ) from error
    copied = json.loads(payload)
    if not isinstance(copied, dict) or not isinstance(copied.get("rootState"), dict):
        raise ValueError("DiagramData requires a rootState mapping")

    def strip(node: Dict[str, Any]) -> None:
        node.pop("range", None)
        node.pop("_sourcePath", None)
        for event in node.get("events", []):
            if isinstance(event, dict):
                event.pop("range", None)
                event.pop("_sourcePath", None)
        for action in node.get("actions", []):
            if isinstance(action, dict):
                action.pop("range", None)
                action.pop("_sourcePath", None)
        for transition in node.get("transitions", []):
            if isinstance(transition, dict):
                transition.pop("range", None)
                transition.pop("_sourcePath", None)
        for child in node.get("children", []):
            if isinstance(child, dict):
                strip(child)

    strip(copied["rootState"])
    copied.pop("filePath", None)
    return copied


def _strip_browser_private_fields(node: Dict[str, Any]) -> None:
    """Remove filesystem-only fields before embedding renderer data in HTML."""
    node.pop("_sourcePath", None)
    for event in node.get("events", []):
        if isinstance(event, dict):
            event.pop("_sourcePath", None)
    for action in node.get("actions", []):
        if isinstance(action, dict):
            action.pop("_sourcePath", None)
    for transition in node.get("transitions", []):
        if isinstance(transition, dict):
            transition.pop("_sourcePath", None)
    for child in node.get("children", []):
        if isinstance(child, dict):
            _strip_browser_private_fields(child)


def _span_range(span: Optional[Span]) -> Optional[Dict[str, Dict[str, int]]]:
    """Convert the model's one-based span into the renderer's zero-based range."""
    if span is None:
        return None
    start_line = max(0, int(span.line) - 1)
    start_column = max(0, int(span.column) - 1)
    end_line = start_line if span.end_line is None else max(0, int(span.end_line) - 1)
    end_column = (
        start_column if span.end_column is None else max(0, int(span.end_column) - 1)
    )
    return {
        "start": {"line": start_line, "character": start_column},
        "end": {"line": end_line, "character": end_column},
    }


def _operation_lines(statement: OperationStatement, depth: int = 1) -> List[str]:
    """Render one model operation statement into display lines."""
    prefix = "    " * depth
    if isinstance(statement, Operation):
        return [prefix + _text(statement.to_ast_node()).strip()]
    if isinstance(statement, IfBlock):
        lines: List[str] = []
        for index, branch in enumerate(statement.branches):
            if index == 0:
                head = "if [%s] {" % _text(branch.condition)
            elif branch.condition is None:
                head = "else {"
            else:
                head = "else if [%s] {" % _text(branch.condition)
            lines.append(prefix + head)
            if branch.statements:
                for child in branch.statements:
                    lines.extend(_operation_lines(child, depth + 1))
            else:
                lines.append(prefix + "    ...")
            lines.append(prefix + "}")
        return lines
    return [prefix + _text(statement).strip()]


def _effect_lines(transition: Transition) -> List[str]:
    if not transition.effects:
        return []
    lines = ["effect {"]
    for statement in transition.effects:
        lines.extend(_operation_lines(statement))
    lines.append("}")
    return lines


def _action_label(action: Any) -> str:
    stage = str(getattr(action, "stage", ""))
    aspect = getattr(action, "aspect", None)
    prefix = stage + ((" " + str(aspect)) if aspect else "")
    if getattr(action, "is_aspect", False):
        prefix = ">> " + prefix
    if getattr(action, "is_abstract", False):
        return "%s abstract %s" % (prefix, getattr(action, "name", None) or "action")
    if getattr(action, "is_ref", False):
        return "%s ref %s" % (
            prefix,
            ".".join(getattr(action, "ref_state_path", ()) or ()),
        )
    name = getattr(action, "name", None)
    if name:
        return "%s %s" % (prefix, name)
    count = len(getattr(action, "operations", ()) or ())
    return "%s {%d op%s}" % (prefix, count, "" if count == 1 else "s")


def _event_reference(transition: Transition) -> str:
    event = transition.event
    if event is None:
        return ""
    scope = transition.event_scope
    if scope == "local":
        return event.name
    if scope == "absolute":
        return "/" + ".".join(event.path[1:])
    owner = transition.parent
    if owner is not None and tuple(event.state_path[: len(owner.path)]) == owner.path:
        rest = event.state_path[len(owner.path) :]
        return ".".join((*rest, event.name))
    return "/" + ".".join(event.path[1:])


def _state_id(path: Tuple[Any, ...]) -> str:
    """Build the ID shared by Python data and the jsfcstm renderer."""
    return ".".join(str(segment) for segment in path)


def _transition_id(owner: State, index: int) -> str:
    """Build the contract ID from an owner path and final transition order."""
    return "%s::transition::%d" % (_state_id(owner.path), index)


def _is_marker(value: Any, name: str) -> bool:
    return getattr(value, "name", None) == name or str(value) == name


def _state_path_for(owner: State, value: Any) -> Optional[List[str]]:
    if _is_marker(value, "INIT_STATE") or _is_marker(value, "EXIT_STATE"):
        return None
    if not isinstance(value, str):
        return None
    candidate = owner.path + (value,)
    return list(candidate)


def _event_dict(event: Event, include_ranges: bool) -> Dict[str, Any]:
    result = {
        "name": event.name,
        "qualifiedName": event.path_name,
        "displayName": event.extra_name,
        "declared": bool(event.declared),
        "origins": list(event.origins),
    }
    if include_ranges:
        result["range"] = _span_range(event._span)
    return result


def _state_dict(state: State, include_ranges: bool) -> Dict[str, Any]:
    transitions = []
    for index, transition in enumerate(state.transitions):
        source_init = _is_marker(transition.from_state, "INIT_STATE")
        target_exit = _is_marker(transition.to_state, "EXIT_STATE")
        source_label = "[*]" if source_init else _text(transition.from_state)
        target_label = "[*]" if target_exit else _text(transition.to_state)
        trigger = _event_reference(transition) if transition.event else ""
        guard = _text(transition.guard) if transition.guard is not None else None
        effects = _effect_lines(transition)
        transition_id = _transition_id(state, index)
        transition_dict: Dict[str, Any] = {
            "id": transition_id,
            "sourceLabel": source_label,
            "targetLabel": target_label,
            "triggerLabel": trigger or None,
            "guardLabel": guard,
            "effectLines": effects,
            "eventName": transition.event.name if transition.event else None,
            "eventDisplayName": transition.event.extra_name
            if transition.event
            else None,
            "eventRelativePath": trigger or None,
            "eventAbsolutePath": ("/" + ".".join(transition.event.path[1:]))
            if transition.event
            else None,
            "triggerScope": transition.event_scope,
            "label": "%s -> %s%s%s%s"
            % (
                source_label,
                target_label,
                (" " + trigger) if trigger else "",
                (" if [" + guard + "]") if guard else "",
                " effect" if effects else "",
            ),
            "forced": bool(transition.is_forced),
            "sourceKind": "init" if source_init else "state",
            "targetKind": "exit" if target_exit else "state",
            "sourceStatePath": _state_path_for(state, transition.from_state),
            "targetStatePath": _state_path_for(state, transition.to_state),
            "eventQualifiedName": transition.event.path_name
            if transition.event
            else None,
            "eventColor": None,
        }
        if include_ranges:
            transition_dict["range"] = _span_range(transition._span)
            transition_dict["_sourcePath"] = getattr(transition, "_source_path", None)
        transitions.append(transition_dict)

    actions = []
    for action in [
        *state.on_enters,
        *state.on_durings,
        *state.on_exits,
        *state.on_during_aspects,
    ]:
        item = {
            "name": action.name,
            "qualifiedName": ".".join(
                str(x) for x in action.state_path if x is not None
            ),
            "stage": action.stage,
            "aspect": action.aspect,
            "mode": "ref"
            if action.is_ref
            else ("abstract" if action.is_abstract else "operations"),
            "abstract": bool(action.is_abstract),
            "reference": bool(action.is_ref),
            "globalAspect": bool(action.is_aspect),
            "operationCount": len(action.operations),
            "label": _action_label(action),
        }
        if include_ranges:
            item["range"] = _span_range(action._span)
        actions.append(item)

    result: Dict[str, Any] = {
        "id": _state_id(state.path),
        "name": state.name,
        "qualifiedName": _state_id(state.path),
        "displayName": state.extra_name,
        "pseudo": bool(state.is_pseudo),
        "comboRelay": bool(state.is_combo_relay),
        "leaf": bool(state.is_leaf_state),
        "root": bool(state.is_root_state),
        "events": [
            _event_dict(event, include_ranges) for event in state.events.values()
        ],
        "actions": actions,
        "transitions": transitions,
        "children": [
            _state_dict(child, include_ranges) for child in state.substates.values()
        ],
    }
    if include_ranges:
        result["range"] = _span_range(state._span)
        result["_sourcePath"] = getattr(state, "_source_path", None)
    return result


def _collect_counts(machine: StateMachine) -> Tuple[int, int, int, int]:
    states = list(machine.walk_states())
    events = [event for state in states for event in state.events.values()]
    transitions = [transition for state in states for transition in state.transitions]
    actions = [
        action
        for state in states
        for action in [
            *state.on_enters,
            *state.on_durings,
            *state.on_exits,
            *state.on_during_aspects,
        ]
    ]
    return len(states), len(events), len(transitions), len(actions)


def _build_diagram_dict(machine: StateMachine, include_ranges: bool) -> Dict[str, Any]:
    state_count, event_count, transition_count, action_count = _collect_counts(machine)
    transitions = [
        transition
        for state in machine.walk_states()
        for transition in state.transitions
    ]
    event_counts: Dict[str, int] = {}
    for transition in transitions:
        if transition.event:
            event_counts[transition.event.path_name] = (
                event_counts.get(transition.event.path_name, 0) + 1
            )
    palette = [
        "#4E79A7",
        "#F28E2B",
        "#E15759",
        "#76B7B2",
        "#59A14F",
        "#EDC948",
        "#B07AA1",
    ]
    event_colors = {
        path: palette[index % len(palette)]
        for index, path in enumerate(
            sorted(path for path, count in event_counts.items() if count > 1)
        )
    }

    def apply_colors(state_dict: Dict[str, Any]) -> None:
        for transition in state_dict["transitions"]:
            transition["eventColor"] = event_colors.get(
                transition.get("eventQualifiedName")
            )
        for child in state_dict["children"]:
            apply_colors(child)

    root = _state_dict(machine.root_state, include_ranges)
    apply_colors(root)
    event_legend = [
        {
            "qualifiedName": path,
            "label": path.split(".")[-1],
            "transitionCount": event_counts[path],
            "color": event_colors[path],
        }
        for path in sorted(event_colors)
    ]
    result: Dict[str, Any] = {
        "kind": "diagram",
        "filePath": "" if machine.source_path is None else str(machine.source_path),
        "machineName": machine.root_state.name,
        "summary": {
            "variables": len(machine.defines),
            "states": state_count,
            "events": event_count,
            "transitions": transition_count,
            "actions": action_count,
        },
        "variables": [
            {"name": item.name, "valueType": item.type, "initializer": _text(item.init)}
            for item in machine.defines.values()
        ],
        "eventLegend": event_legend,
        "rootState": root,
    }
    if not include_ranges:
        result.pop("filePath", None)
    return result


def _source_document_id(machine: StateMachine, source_path: Optional[str]) -> str:
    if source_path == "<memory>" or source_path is None:
        return "main.fcstm"
    # ``load_state_machine_from_text`` uses the working directory as the
    # import-resolution path while retaining the actual source under the
    # ``<memory>`` key.  That directory is not a source document and must not
    # leak into the browser sidecar as a basename such as ``pyfcstm``.
    if source_path == machine.source_path and "<memory>" in machine._source_documents:
        return "main.fcstm"
    main_path = machine.source_path
    if main_path and source_path != "<memory>":
        try:
            main_absolute = os.path.abspath(main_path)
            base = (
                main_absolute
                if os.path.isdir(main_absolute)
                else os.path.dirname(main_absolute)
            )
            relative = os.path.relpath(source_path, base)
            # Keep ``..`` segments instead of collapsing to a basename. Two
            # imports such as ``../a/child.fcstm`` and ``../b/child.fcstm``
            # must remain separate source documents in the browser sidecar.
            return relative.replace(os.sep, "/")
        except (OSError, ValueError):
            # OSError/ValueError: source paths can be on different drives or
            # become unavailable after a model is loaded. A path digest keeps
            # those documents distinct without embedding the absolute path.
            normalized = os.path.normcase(os.path.abspath(str(source_path)))
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
            basename = Path(source_path).name or "document.fcstm"
            return "external/%s/%s" % (digest, basename)
    return Path(source_path).name or "main.fcstm"


def _validate_source_override(
    machine: StateMachine, source_override: Optional[str]
) -> None:
    """Reject source overrides that would invalidate model source ranges."""
    if source_override is None or machine.source_text is None:
        return
    if _text(machine.source_text) != _text(source_override):
        raise ValueError(
            "source_text override does not match the source used to build the model; "
            "reparse the model from the replacement FCSTM text"
        )


def _source_sidecar(
    machine: StateMachine,
    source_override: Optional[str] = None,
    diagram: Optional[Mapping[str, Any]] = None,
) -> Tuple[str, Dict[str, Any], Dict[str, Union[str, List[str]]], Dict[str, str]]:
    _validate_source_override(machine, source_override)
    # A line-ending-only copy is the model's own source: treat it as such for
    # both the displayed text and the document registry, so the source pane and
    # ``sourceDocuments`` never disagree on the bytes of the same document.
    explicit_override = source_override is not None and (
        machine.source_text is None
        or _text(source_override) != _text(machine.source_text)
    )
    source = source_override if explicit_override else machine.source_text
    source = source or ""
    # Work on a copy: completing the browser sidecar must not mutate the
    # model's imported-document registry when the main source is absent.
    source_paths = dict(machine._source_documents or {})
    if explicit_override or not source_paths:
        main_source_path = machine.source_path or "<memory>"
        source_paths = {main_source_path: source}
    elif machine.source_path and machine.source_path not in source_paths:
        source_paths[machine.source_path] = source
    documents = {
        _source_document_id(machine, path): text for path, text in source_paths.items()
    }
    main_document_id = _source_document_id(machine, machine.source_path or "<memory>")
    if diagram is None:
        diagram = _build_diagram_dict(machine, include_ranges=True)
    mapping: Dict[str, Any] = {}
    line_to_id: Dict[str, Union[str, List[str]]] = {}

    def visit(state: Dict[str, Any]) -> None:
        state_id = state["id"]
        if state.get("range"):
            source_path = state.get("_sourcePath") or machine.source_path
            mapping[state_id] = {
                "kind": "state",
                "documentId": _source_document_id(machine, source_path),
                "range": state["range"],
            }
        for transition in state["transitions"]:
            if transition.get("range"):
                source_path = transition.get("_sourcePath") or machine.source_path
                mapping[transition["id"]] = {
                    "kind": "transition",
                    "documentId": _source_document_id(machine, source_path),
                    "range": transition["range"],
                }
        for child in state["children"]:
            visit(child)

    visit(diagram["rootState"])
    # A transition range is more useful than its enclosing state range when
    # both start on the same line.  Otherwise a click on ``Idle -> Run``
    # would only select the containing ``state Root`` node.
    candidates: Dict[Tuple[str, int], List[Tuple[int, int, str]]] = {}
    for key, value in mapping.items():
        document_id = str(value.get("documentId") or main_document_id)
        line = int(value["range"]["start"]["line"])
        span = value["range"]
        length = (int(span["end"]["line"]) - int(span["start"]["line"])) * 100000
        length += max(
            0, int(span["end"]["character"]) - int(span["start"]["character"])
        )
        priority = 0 if value.get("kind") == "transition" else 1
        candidates.setdefault((document_id, line), []).append((priority, length, key))
    for (document_id, line), items in candidates.items():
        ordered = [item[2] for item in sorted(items)]
        value: Union[str, List[str]] = ordered[0] if len(ordered) == 1 else ordered
        line_to_id["%s:%s" % (document_id, line)] = value
        if document_id == main_document_id:
            # Keep the original numeric keys for consumers that predate the
            # multi-document sidecar; document-qualified keys are canonical.
            line_to_id[str(line)] = value
    return source, mapping, line_to_id, documents


def _highlight_source(source: str) -> str:
    """Render source with stateful tokenization and addressable HTML lines."""
    lexer = FcstmLexer()
    formatter = HtmlFormatter(nowrap=True)
    token_lines: List[List[str]] = [[]]
    for token, value in lex(source, lexer):
        css_class = formatter._get_css_class(token)
        fragments = value.split("\n")
        for index, fragment in enumerate(fragments):
            if fragment:
                escaped = html_module.escape(fragment, quote=False)
                token_lines[-1].append(
                    '<span class="%s">%s</span>' % (css_class, escaped)
                )
            if index < len(fragments) - 1:
                token_lines.append([])
    expected_line_count = max(1, len(source.splitlines()))
    while len(token_lines) > expected_line_count:
        token_lines.pop()
    while len(token_lines) < expected_line_count:
        token_lines.append([])
    if not token_lines:
        token_lines = [[]]
    rendered = [
        '<span class="fcstm-source-line" data-line="%d" data-line-number="%d">%s</span>'
        % (index, index + 1, "".join(content) or " ")
        for index, content in enumerate(token_lines)
    ]
    # The parent uses normal whitespace handling, while each line preserves
    # its own source spacing. This keeps copied text line-oriented without
    # turning the separator newline into an extra visual row.
    return "\n".join(rendered)


def _highlight_css() -> str:
    """Return the small Pygments CSS fragment used by the source pane."""
    return (
        HtmlFormatter().get_style_defs(".fcstm-source-panel__code")
        + "\n"
        + (
            ".fcstm-source-panel__code { background-color: var(--fcstm-surface-raised); "
            "color: var(--fcstm-fg); }\n"
            ".fcstm-source-panel__code .w { color: var(--fcstm-line-number); }"
        )
    )


_OPTION_KEYS = {
    "detail_level",
    "detailLevel",
    "direction",
    "palette",
    "mode",
    "cjk_locale",
    "cjkLocale",
}
_VIEW_STATE_KEYS = {
    "mode",
    "collapsed_state_ids",
    "collapsedStateIds",
    "zoom",
    "pan_x",
    "panX",
    "pan_y",
    "panY",
}


def _reject_unknown_mapping_keys(
    value: Mapping[str, Any], allowed: set, name: str
) -> None:
    unknown = [key for key in value if key not in allowed]
    if unknown:
        labels = ", ".join(sorted(str(key) for key in unknown))
        raise ValueError("unknown %s field(s): %s" % (name, labels))


def _mapping_value(
    value: Mapping[str, Any], snake: str, camel: str, default: Any
) -> Any:
    has_snake = snake in value
    has_camel = camel in value
    if has_snake and has_camel:
        raise ValueError("%s and %s cannot both be provided" % (snake, camel))
    if has_snake:
        return value[snake]
    if has_camel:
        return value[camel]
    return default


def _coerce_finite_number(value: Any, field_name: str, positive: bool = False) -> float:
    """Normalize a numeric option and reject bool/NaN/infinite values."""
    number_label = "numbers" if field_name.endswith("offsets") else "number"
    if isinstance(value, bool):
        if positive:
            raise ValueError("%s must be a finite positive number" % field_name)
        raise ValueError("%s must be finite %s" % (field_name, number_label))
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        # TypeError/ValueError: callers supplied a non-numeric option or a
        # string that cannot be parsed as a number.
        if positive:
            raise ValueError(
                "%s must be a finite positive number" % field_name
            ) from error
        raise ValueError("%s must be finite %s" % (field_name, number_label)) from error
    if not math.isfinite(number) or (positive and number <= 0):
        if positive:
            raise ValueError("%s must be a finite positive number" % field_name)
        raise ValueError("%s must be finite %s" % (field_name, number_label))
    return number


def _coerce_window_size(value: Tuple[Any, Any]) -> Tuple[int, int]:
    """Validate the standalone app-window dimensions."""
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError("window_size must contain exactly two positive integers")
    width, height = value
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
    ):
        raise ValueError("window_size must contain exactly two positive integers")
    return width, height


def _browser_app_executable() -> Optional[str]:
    """Find a Chromium-family executable that supports ``--app`` windows."""
    override = os.environ.get("PYFCSTM_BROWSER")
    if override:
        # An explicit choice is honoured or reported, never quietly replaced by
        # a guess: a typo or a moved binary used to fall through to whatever
        # else happened to be installed, while the error text still presented
        # the variable as authoritative.
        resolved = shutil.which(override) or (
            override
            if os.path.isfile(override) and os.access(override, os.X_OK)
            else None
        )
        if resolved is None:
            raise DiagramUnavailableError(
                "PYFCSTM_BROWSER is set to %r, which is not an executable file "
                "on this system; point it at a Chromium-family browser or unset "
                "it to search the usual locations" % override
            )
        return resolved
    candidates = []
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", "")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")
        candidates.extend(
            [
                os.path.join(
                    local_app_data, "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    program_files, "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    program_files_x86, "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"
                ),
                "chrome.exe",
                "msedge.exe",
                "chromium.exe",
            ]
        )
    elif sys.platform == "darwin":
        candidates.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "google-chrome",
                "microsoft-edge",
                "chromium",
            ]
        )
    else:
        candidates.extend(
            [
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
                "microsoft-edge",
                "brave-browser",
            ]
        )
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isabs(candidate) and os.path.isfile(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _stop_browser(process: Any) -> None:
    """
    Stop the browser, and everything it started, as far as the platform allows.

    The main process exiting does not mean its children have.  After an interrupt,
    one of them recreated files inside the profile directory that had just been
    removed, leaving it behind for good.  On POSIX the browser is a session leader
    of its own -- that is what ``start_new_session`` bought -- so the group can be
    signalled as a unit; Windows has no equivalent here, and a profile that
    survives is reported rather than passed over.

    :param process: The browser process.
    :type process: subprocess.Popen
    :return: ``None``.
    :rtype: None
    """
    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
        try:
            group = os.getpgid(process.pid)
            # Only if it really leads its own group. Signalling ours would take
            # the interpreter down with it.
            if group == process.pid:
                os.killpg(group, signal.SIGTERM)
                return
        except OSError:
            # ProcessLookupError once it has already exited; PermissionError if
            # the group is not ours to signal. Either way, ask the process.
            pass
    process.terminate()


def _browser_complaint(stderr: Optional[bytes]) -> str:
    """
    Return the browser's own last words, as a suffix for a failure message.

    Its stderr is where the reason lives -- "Missing X server or $DISPLAY" is not
    something this module could have worked out on its own -- and the last lines
    are the ones that say why.

    :param stderr: Whatever the browser wrote, or ``None``.
    :type stderr: bytes, optional
    :return: ``": <reason>"``, or an empty string when it said nothing.
    :rtype: str
    """
    text = (stderr or b"").decode("utf-8", "replace")
    # Chromium prefixes every line with `[pid:tid:date:LEVEL:file:line]`, which is
    # longer than the sentence after it and hides it.
    lines = [re.sub(r"^\[[^]]*\]\s*", "", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    return ": %s" % " / ".join(lines[-2:])


def _open_standalone_window(path: Path, window_size: Tuple[int, int]) -> None:
    """
    Show the viewer in a browser app window and return when it is closed.

    Blocking, the way :func:`matplotlib.pyplot.show` blocks, because that is what
    lets the caller delete the document afterwards.  A detached launch cannot:
    the browser reads the file after this process is gone, so the document had to
    outlive it -- and everything that followed from that was machinery for a file
    nobody could ever remove.  A name every process could predict so repeats
    would reuse one copy, an exit hook that had to be kept away from that name,
    and two naming spaces to tell the two lifetimes apart, one of which deleted a
    live window's document when a user id and a process id happened to match.

    The window gets a profile directory of its own, which is what makes the wait
    mean anything: a Chromium-family browser handed a document without
    ``--user-data-dir`` passes it to whatever instance is already running and
    exits at once, so waiting on it would return before the window appeared.

    :param path: Document to show.
    :type path: pathlib.Path
    :param window_size: Width and height in pixels.
    :type window_size: tuple[int, int]
    :return: ``None``, once the window has closed.
    :rtype: None
    :raises DiagramUnavailableError: If no Chromium-family browser is available,
        or it cannot be launched.
    """
    executable = _browser_app_executable()
    if executable is None:
        raise DiagramUnavailableError(
            "a Chromium-family browser is required for the standalone diagram window; "
            "install Chrome, Chromium, Edge, or Brave, or set PYFCSTM_BROWSER"
        )
    width, height = window_size
    profile = None

    def command_of(directory):
        return [
            executable,
            "--app=%s" % path.resolve().as_uri(),
            # Ours, so the browser is a process to wait on rather than a message to
            # one already running. The two flags after it are what a fresh profile
            # would otherwise stop and ask about.
            "--user-data-dir=%s" % directory,
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=%d,%d" % (width, height),
        ]

    popen_kwargs: Dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        # Kept, because when the browser fails it is the only place the reason
        # exists: on a machine with no display it says exactly that, and a caller
        # told merely that something exited cannot act on it. `communicate` drains
        # it, so a chatty browser cannot fill the pipe and stall.
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        popen_kwargs["start_new_session"] = True
    complaint = b""
    code = 0
    process = None
    try:
        # Acquired inside the protective block, and with no handler entered while
        # it is held: this module argues both at length about the staging file, and
        # a nested `try:` line is itself unowned from Python 3.11 on -- measured
        # here, where two of them leaked this directory on 3.11 and 3.14 while
        # passing on 3.10.
        profile = tempfile.mkdtemp(prefix="pyfcstm-diagram-profile-")
        process = subprocess.Popen(command_of(profile), **popen_kwargs)
        _, complaint = process.communicate()
        code = process.returncode
    except BaseException as error:
        if process is None and isinstance(error, OSError):
            # `Popen` could not start it at all -- ENOENT for a path that is not
            # there any more, EACCES for one that is not executable. A typed
            # capability error is what callers of `show` are told to expect.
            raise DiagramUnavailableError(
                "failed to launch the standalone diagram window with %s: %s"
                % (executable, error)
            ) from error
        if process is not None:
            # A Ctrl-C while the window is open. Closing it is the honest
            # response: the caller is about to remove the document under it.
            _stop_browser(process)
            process.communicate()
        # Anything else -- including an interrupt before the browser existed --
        # travels on unchanged.
        raise
    finally:
        if profile is not None:
            try:
                shutil.rmtree(profile)
            except OSError as removal_error:
                # A few megabytes per call, so it is worth saying. PermissionError
                # where Windows still holds a lock, ENOTEMPTY where a browser
                # descendant wrote something back after the tree was walked. The
                # caller's own outcome is the one that propagates, the same way
                # `_discard` treats a staging file it cannot remove.
                _report_degradation(
                    "could not remove the browser profile %s: %s",
                    profile,
                    removal_error,
                )
    if code != 0:
        # The browser exited without the user closing a window, so the diagram was
        # never shown and saying otherwise is a false success. An SSH session or a
        # container without a display is the ordinary way to arrive here: the
        # executable exists, so nothing earlier objects, and Chromium exits within
        # a second saying it found no display.
        raise DiagramUnavailableError(
            "the standalone diagram window closed with status %d%s"
            % (code, _browser_complaint(complaint))
        )


# Private viewer directories, by the temporary directory each one sits in. Held so
# a fallback made once is not remade, and so tests pointed at their own temporary
# directory are independent; see `_private_viewer_directory`.
_PRIVATE_DIRECTORIES: Dict[str, Path] = {}

# Those of the above made for a process itself because the predictable name could
# not be trusted, against the process that made each one. The process id is what a
# `fork` makes necessary: a child inherits this mapping and its own exit hook, and
# neither the parent's directories nor the parent's registration are the child's.
# They are removed when they empty, and again at exit; see `_discard_empty_fallback`
# and `_reclaim_empty_fallbacks`.
_FALLBACK_DIRECTORIES: Dict[Path, int] = {}
_RECLAIM_REGISTERED: List[int] = []


def _private_viewer_directory() -> Path:
    """
    Return a directory only this user can look inside, one per user.

    A viewer holds the model's own source, and 0600 stops another local user
    reading it -- but not ``stat``-ing it, which needs no permission on the file at
    all.  The system temporary directory is listable, so a ~29 MB document's exact
    size is a fingerprint of the model: render a few candidates, compare byte
    counts, and the match says which one is on display.  A name derived from the
    document gave the same thing away more directly.  Neither is closed by changing
    what the file is called, because the leak is not in the name -- so the boundary
    is the directory, where the names and the individual sizes are as invisible as
    the contents.  Not everything is: ``stat`` on a *directory* needs only the
    parent's execute bit, so another user can still see that this one exists, when
    it last changed, and -- on a tmpfs, where a directory's size grows with its
    entries -- roughly how many things are in it.  None of that identifies a model,
    which is what the fingerprint was.

    Per user rather than per process, because that is what lets the name inside
    carry reuse: two processes showing one diagram write one file instead of ~29 MB
    each.  The name of a per-user directory is predictable, so it is verified
    before use -- a directory, not a link, ours, and closed to everyone else -- and a
    private one of this process's own is used instead when it is not, which keeps
    working at the cost of that reuse.

    What that verification is worth depends on the platform, and this is the limit
    of it.  On POSIX the mode and the owner are both checked, and both mean what
    they say.  On Windows there is no owner to ask about, and ``os.mkdir`` applies
    a restrictive ACL for a mode of 0o700 only from CPython 3.12.4 -- earlier
    versions in this package's range ignore it.  Privacy there rests on ``%TEMP%``
    being per account, which it is by default; a ``TEMP`` pointing at a directory
    other users share is not something this can detect, and in that case neither
    the directory nor the 0600 on the files inside it keeps anything private,
    because that mode is only Windows' read-only bit.  Pass an explicit ``output``
    path for a document that must not be somewhere shared.

    :return: A directory under the system temporary directory, readable only by
        this user.
    :rtype: pathlib.Path
    """
    base = tempfile.gettempdir()
    remembered = _PRIVATE_DIRECTORIES.get(base)
    if remembered is not None:
        # Checked again, not remembered as checked. A long-lived process resolves
        # this once and may write days later, by which time a tmp cleaner can have
        # removed the directory and somebody else created the predictable name as
        # 0777 -- and `is_dir()` alone would have followed a link into it.
        complaint = _unusable_viewer_directory(remembered)
        if complaint is None:
            return remembered
        _report_degradation("no longer using %s: %s", remembered, complaint)
        del _PRIVATE_DIRECTORIES[base]
        _FALLBACK_DIRECTORIES.pop(remembered, None)
    shared = Path(base) / (
        "pyfcstm-viewers-%d" % os.geteuid()
        if hasattr(os, "geteuid")
        else "pyfcstm-viewers"
    )
    complaint = _unusable_viewer_directory(shared)
    if complaint is None:
        _PRIVATE_DIRECTORIES[base] = shared
        return shared
    # Something else holds the name. A directory of our own still hides everything
    # a caller cares about; what is lost is only that a second process of ours
    # cannot find the same file, so it is worth recording rather than passing over.
    _report_degradation("not reusing %s: %s", shared, complaint)
    private = Path(tempfile.mkdtemp(prefix="pyfcstm-viewers-", dir=base))
    _PRIVATE_DIRECTORIES[base] = private
    _FALLBACK_DIRECTORIES[private] = os.getpid()
    if os.getpid() not in _RECLAIM_REGISTERED:
        # Once per process, and once more in a forked child: it inherits this list
        # non-empty and the parent's hook, which its own guard then skips, so a flag
        # rather than a set of process ids left the child with no hook at all. A
        # caller who keeps a viewer and later removes it leaves the directory empty,
        # and nothing in the call that made it is still running to notice.
        _RECLAIM_REGISTERED.append(os.getpid())
        atexit.register(_reclaim_empty_fallbacks, os.getpid())
        _register_with_multiprocessing(os.getpid())
    return private


def _register_with_multiprocessing(owner: int) -> None:
    """
    Register the reclaim where a :mod:`multiprocessing` worker will run it.

    A worker that finishes normally does not run :mod:`atexit` hooks: it runs its
    own finalizers and then ``os._exit``.  So the hook registered beside this one
    covers an ordinary interpreter and this one covers an ordinary worker, which is
    a path a caller reaches by using the standard library as documented rather than
    by killing anything.

    Only when the process is already using :mod:`multiprocessing` -- its ``util``
    module is imported by the machinery that starts a worker, so a plain
    interpreter neither pays for the import nor needs it.  Importing
    :mod:`multiprocessing` alone does not bring ``util`` with it, so the common shape
    -- show, then start a worker and hand it the path -- registers nothing here at
    all, and is covered anyway: ``util``'s own hook is registered when that worker
    starts, which is after this module's, and :mod:`atexit` runs the later
    registration first.  So ``util`` joins the worker before this module's hook looks
    at the directory.

    Two orders reach here, and neither leaves a directory behind.  Start a worker
    and then show, and ``util`` is already imported, so both this and the
    :mod:`atexit` hook exist: the hook was registered later and :mod:`atexit` runs
    the later one first, so it meets a directory the worker still holds, and this
    one -- after the join -- finds it empty.  Show and then start, and ``util`` was
    not imported when this ran, so there is no finalizer at all; ``util``'s own hook
    is then the later registration, runs first, and joins the worker before the hook
    beside this one looks at the directory.  Where both do run, whichever succeeds
    leaves the other with ``ENOENT``, which is why that is graded as the outcome
    asked for rather than as a failure.

    :param owner: The process this registration belongs to.
    :type owner: int
    :return: ``None``.
    :rtype: None
    """
    machinery = sys.modules.get("multiprocessing.util")
    finalize = getattr(machinery, "Finalize", None)
    if finalize is None:
        return
    # `exitpriority` is what puts it in the list that runs; without one the object is
    # only called if something still refers to it. Negative is what puts it after the
    # workers: `multiprocessing.util._exit_function` runs the finalizers at priority
    # zero and above, then joins the children, then runs what is left. A worker still
    # holding the viewer it was given has not removed it yet during the first of
    # those, so a reclaim there finds the directory occupied and the one chance to
    # empty it is spent.
    finalize(None, _reclaim_empty_fallbacks, args=(owner,), exitpriority=-1)


def _reclaim_empty_fallbacks(owner: int) -> None:
    """
    Remove this process's fallback viewer directories, if they are empty.

    Registered with :mod:`atexit` when the first one is made.  ``rmdir`` is what
    makes it safe to run over all of them: a directory still holding a document the
    caller keeps refuses to go, which is the contract, and one already gone is not
    an error worth reporting from an exit hook.

    A :mod:`multiprocessing` worker that finishes normally runs its own finalizers
    instead of these hooks, so :func:`_register_with_multiprocessing` puts the same
    call there as well.  What neither reaches is a process that leaves without
    running anything -- ``os._exit`` by hand, or a signal.  Such a process leaves an
    empty directory behind, and nothing here can reclaim it: this mapping holds only
    what the running process made, so another process's leftovers are invisible to
    it, and sweeping the temporary directory by name would race a process sitting
    between creating its own and writing into it.  That leftover is one empty
    directory per such process, and only where the predictable name could not be
    trusted in the first place.

    :param owner: The process that registered this.  Both the guard and the
        selection use it: a forked child must not run the parent's hook, and must
        not treat the parent's directories -- which it inherited -- as its own.
    :type owner: int
    :return: ``None``.
    :rtype: None
    """
    if os.getpid() != owner:
        # `fork` copies the exit hooks along with the mapping, and a child that exits
        # normally runs the parent's. Removing the parent's directory between its
        # creation and the first write into it would break that save.
        return
    mine = sorted(
        directory
        for directory, maker in _FALLBACK_DIRECTORIES.items()
        if maker == owner
    )
    for directory in mine:
        try:
            os.rmdir(str(directory))
        except OSError as error:
            if error.errno not in (errno.ENOTEMPTY, errno.EEXIST, errno.ENOENT):
                # The same three, graded the same way as in
                # `_discard_empty_fallback`: the first two are the contract, the
                # third is the outcome already reached. Anything else, EACCES on a
                # temporary directory locked down since, leaves the directory
                # behind, and being an exit hook is a reason not to raise rather
                # than a reason to say nothing.
                _report_degradation(
                    "could not remove the fallback directory %s: %s", directory, error
                )
            continue


def _discard_empty_fallback(directory: Path) -> None:
    """
    Remove a fallback viewer directory once it holds nothing.

    The per-user directory is meant to stay: one per user, empty between calls, and
    the place a second process looks.  A fallback is not -- it belongs to this
    process alone, so leaving it behind gave every run of ``pyfcstm diagram --open``
    an inode of its own for as long as the predictable name stayed untrustworthy.

    Only when empty, because the same directory holds documents a caller keeps.

    :param directory: Directory a viewer was just removed from.
    :type directory: pathlib.Path
    :return: ``None``.
    :rtype: None
    """
    if _FALLBACK_DIRECTORIES.get(directory) != os.getpid():
        # Not ours to remove: either not a fallback at all, or one a parent made
        # before forking, whose lifetime belongs to the parent.
        return
    try:
        os.rmdir(str(directory))
    except OSError as error:
        if error.errno not in (errno.ENOTEMPTY, errno.EEXIST, errno.ENOENT):
            # The first two are the contract -- a directory still holding a document
            # the caller keeps -- and POSIX allows either for it. `ENOENT` means it
            # has already gone, which is the outcome asked for. Anything else -- a
            # temporary directory that has become read-only, a mount gone away -- is
            # a directory left behind, which is the thing this function exists to
            # prevent, so it does not pass in silence. `_reclaim_empty_fallbacks`
            # grades the same three the same way.
            _report_degradation(
                "could not remove the fallback directory %s: %s", directory, error
            )
        return
    del _FALLBACK_DIRECTORIES[directory]
    for base, path in list(_PRIVATE_DIRECTORIES.items()):
        if path == directory:
            # Forgotten, so the next call looks at the predictable name again --
            # whatever was holding it may be gone.
            del _PRIVATE_DIRECTORIES[base]


def _unusable_viewer_directory(path: Path) -> Optional[str]:
    """
    Say why a viewer directory cannot be trusted, or ``None`` if it can.

    The name is predictable and its parent is world-writable, so this asks the four
    questions that make the answer safe: it is there, it is a directory rather than
    a link to one, it belongs to us, and nobody else may look inside.  The last one
    asks about the group and other bits rather than the whole mode, because a
    setgid parent makes an otherwise identical directory 2700.

    :param path: Directory the viewers would go in.
    :type path: pathlib.Path
    :return: A reason, or ``None``.
    :rtype: str or None
    """
    try:
        os.mkdir(str(path), 0o700)
        return None
    except FileExistsError:
        # The ordinary case after the first run of the day.
        pass
    except OSError as error:
        # EACCES on a temporary directory we may not write, EROFS, ENOSPC.
        return "%s" % error
    try:
        info = os.lstat(str(path))
    except OSError as error:
        # It went away between the two calls, which is not something to work
        # around; the fallback covers it.
        return "%s" % error
    if not stat.S_ISDIR(info.st_mode):
        return "it is not a directory"
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        return "it belongs to another user"
    shared = stat.S_IMODE(info.st_mode) & 0o077
    if os.name != "nt" and shared:
        # The bits that decide who else may look, not the whole mode. A setgid
        # parent -- an ordinary way to run a shared scratch directory -- makes the
        # new directory 2700, which is as private as 0700 and was being refused,
        # sending every process to a fallback and writing the same document again.
        return "it allows %03o to others" % shared
    return None


def _kept_viewer_path(document: str) -> Path:
    """
    Return the path a viewer the caller keeps is written to.

    Nothing removes these, so showing the same diagram twice must not write it
    twice: that left a fresh ~29 MB on every call, and three processes showing one
    diagram left 85 MB.  The name is the document's digest, which makes the reuse
    work between processes as well as within one -- safe here only because
    :func:`_private_viewer_directory` is not listable by anyone else, since the
    digest in a shared directory is a fingerprint of the model.

    :param document: The rendered HTML document.
    :type document: str
    :return: A path inside this user's private viewer directory.
    :rtype: pathlib.Path
    """
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()[:16]
    return _private_viewer_directory() / ("kept-%s.html" % digest)


def _temporary_viewer_path() -> Path:
    """
    Return a path for a viewer shown in a window, which nothing else uses.

    A window's own call removes this when the window closes, so by the rule in
    :func:`_kept_viewer_path` it must not be shared: two windows on one diagram
    would otherwise use one file and the first to close would blind the other.  A
    distinct prefix as well as a random name, so no arithmetic can bring the two
    apart.

    :return: A path inside this user's private viewer directory.
    :rtype: pathlib.Path
    """
    return _private_viewer_directory() / ("window-%s.html" % uuid.uuid4().hex[:16])


def _report_degradation(message: str, *args: Any) -> None:
    """
    Record a degradation from a cleanup path, tolerating a broken backend.

    ``Handler.emit`` is a user extension point, and a handler or filter that
    raises propagates to whoever logged.  Every call here is inside a
    ``finally`` where an exception may already be travelling, so an ordinary
    backend failure must not replace it with a complaint about a log line.

    The narrower guarantee is deliberate: ``SystemExit`` and
    ``KeyboardInterrupt`` pass through, because swallowing an interrupt is
    worse than the report it would hide.  Where a report *cannot* be allowed to
    interrupt anything -- between a document being written and ``os.replace``
    making it the target -- it is not routed here at all; it is collected and
    emitted afterwards.

    :param message: ``%``-style format string.
    :type message: str
    :param args: Values for the format string.
    :type args: object
    :return: ``None``.
    :rtype: None
    """
    # Nothing exercises the tolerance below: reaching it needs a `logging`
    # handler that raises, which no caller can arrange. Changes here are changes
    # to code no test will catch.
    try:
        _logger.warning(message, *args)
    except Exception:
        # Every class a logging backend can raise short of BaseException. There
        # is no narrower set to name: the exception comes from third-party
        # handler code rather than from any call this module makes, and it must
        # not replace whatever is already travelling through the `finally` this
        # is called from.
        #
        # Not dropped, though. `logging.Handler.handleError` sets the precedent:
        # when the logging machinery itself fails, the traceback goes to stderr
        # under `raiseExceptions`. Swallowing without a trace is what CLAUDE.md
        # forbids, and it would be a poor answer to a round spent adding
        # observability elsewhere.
        if logging.raiseExceptions:
            # Written in two independent attempts. Interpolating the
            # degradation and the traceback into one string means one bad
            # argument -- a `__str__` that raises, a stray `%` -- takes both
            # down, and this is the last place either can be said. The
            # degradation goes first because it is what the reader must act
            # on; the traceback only names the handler that broke.
            failure = traceback.format_exc()
            try:
                sys.stderr.write("pyfcstm: %s\n" % (message % args))
            except Exception:
                # An argument whose `__str__` raises, or a format string whose
                # placeholders do not match. The unformatted message is still
                # worth more than silence.
                try:
                    sys.stderr.write("pyfcstm: %s %r\n" % (message, args))
                except Exception:
                    # stderr itself is unusable; the attempt below will say so
                    # if it can.
                    pass
            try:
                sys.stderr.write(
                    "pyfcstm: logging failed while reporting it: %s\n" % failure
                )
            except Exception:
                # ValueError from a closed stream, OSError from one whose
                # descriptor has gone, AttributeError from a replacement that
                # is not file-like, and whatever `format_exc` raises on an
                # exotic exception. There is no third place to put this, and
                # raising would cost the caller their work.
                #
                # `Exception`, not `BaseException`: an interrupt arriving while
                # this line runs is the user's, and swallowing it here is the
                # same mistake as swallowing it one frame up.
                pass


# A collision needs a neighbour guessing 64 bits; a few tries turn that into a
# clear error rather than an unbounded loop.
_TEMPORARY_NAME_ATTEMPTS = 8


@contextlib.contextmanager
def _staging_file(target: Path, binary: bool) -> Iterator[Tuple[Any, Path, int]]:
    """
    Own the file a write is staged in, for as long as it exists.

    A context manager rather than a factory, because the descriptor and the path
    have to be owned from the instant they exist.  Handing them back left a
    window between the return and the caller's own ``try`` in which a Ctrl-C
    unwound the stack with nobody holding either -- one leaked descriptor and one
    leaked file, measured through :meth:`Diagram.save`.  Keeping one ``try`` for
    the set-up and a second one around the body left the same window between
    them.  So the single ``try`` below is entered before either resource exists:
    that is what makes every line from the creation to the removal owned, rather
    than moving the unowned line further along.

    A nested ``try`` while a resource is held brings the gap straight back.  From
    Python 3.11 the statement compiles to no instruction of its own and the line
    event lands before the exception table covers the block, so the ``try:`` line
    itself is unowned -- an inner one around the ``yield`` leaked the staging file
    on 3.11 and 3.14 while passing on 3.10.  Anything needing a handler while the
    descriptor or the file exists therefore belongs in a function of its own.

    Two nested ones remain, each exempt for its own reason and neither of them
    "nothing is held".  The one in the loop runs before the file exists, so an
    interrupt on its ``try:`` line has nothing to leave behind.  The one in the
    ``finally`` does hold a descriptor, and is exempt only because it is past the
    ``yield``: an interrupt delivered into cleanup is the single case no Python
    program survives, which is where the probe stops for the same reason.  A third
    one, anywhere between the creation and the ``yield``, would be a defect --
    which is why the handler that names the failed path does nothing else, and a
    removal that fails is recorded by :func:`_discard` rather than folded into the
    exception.  Folding it in cost the caller the exception's class, which is what
    they catch on.

    The file is opened with 0666 so the operating system applies the umask,
    exactly as it would for any other new file, and the mode that survives is
    read back from the descriptor.  That makes the file being written its own
    answer to "what mode should this end up with", so no second file has to be
    created and measured.  Where the platform has ``os.fchmod`` it is then
    tightened to 0600 for the duration of the write, because the document carries
    the model's source and the destination directory may be shared.  Windows has
    neither ``os.fchmod`` nor a mode beyond the read-only bit, so there the
    staging file keeps whatever the directory's own permissions gave it.

    On exit the stream is closed and the file removed, unless the body renamed it
    onto the target -- in which case there is nothing left at the staging path
    and the removal finds nothing to do.

    :param target: Destination the caller asked for.
    :type target: pathlib.Path
    :param binary: Whether the stream should accept bytes rather than text.
    :type binary: bool
    :return: Context manager yielding the open stream, the staging path, and the
        mode a new file receives in that directory.
    :rtype: contextlib.AbstractContextManager
    :raises OSError: If the directory will not accept a new file.
    """
    # `O_NOFOLLOW` and `O_BINARY` are what `tempfile` adds to its own open, kept
    # here for the same reasons: the first refuses to follow a symlink sitting at
    # the name, the second states binary intent at the point of creation. Both
    # are defensive rather than relied upon -- the name is freshly generated, so
    # nothing normal puts a symlink there -- and neither has a test, because what
    # they guard against is not a path a caller can reach.
    #
    # `O_BINARY` is belt and braces rather than load-bearing. `_io.FileIO` calls
    # `_setmode(self->fd, O_BINARY)` unconditionally on Windows, including when it
    # wraps a descriptor it was handed, so `os.fdopen` clears text translation
    # regardless -- checked against CPython 3.7 (Modules/_io/fileio.c:362,469)
    # and 3.14 (:397,508), where the `fd >= 0` branch only assigns and falls
    # through to that call.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    # One `try` for the whole life of both resources, entered before either of
    # them exists. Two blocks in sequence -- one to set up, one around the body --
    # leave every line between them owned by nobody, which is how the same leak
    # came back three times, a line further along each time.
    staging = None
    handle = -1
    stream = None
    try:
        for _ in range(_TEMPORARY_NAME_ATTEMPTS):
            # Named before it is created, so no line boundary can leave a file
            # behind with nothing that will remove it. Eight characters, matching
            # `NamedTemporaryFile`: a longer suffix eats into the NAME_MAX
            # headroom the target's own name leaves, and turned legal
            # 238-to-245-character names into ENAMETOOLONG. `O_EXCL` plus a retry
            # is what makes a collision harmless, not the width.
            staging = target.parent / (".%s.%s" % (target.name, uuid.uuid4().hex[:8]))
            try:
                handle = os.open(str(staging), flags, 0o666)
            except FileExistsError:
                # `O_EXCL` refused a name something else already holds, which is
                # the point of using it. That file is not ours to remove, so the
                # name goes back to being nothing before another is tried.
                staging = None
                continue
            except OSError:
                # `O_EXCL` means the open either created the file or created
                # nothing, and this is the second case: ENOSPC, EACCES, EROFS, or
                # ELOOP where `O_NOFOLLOW` refused a symlink already sitting at
                # the name. Nothing of ours is there to clean up either way.
                staging = None
                raise
            break
        else:
            raise OSError(
                "could not create a staging file beside %s after %d attempts"
                % (target, _TEMPORARY_NAME_ATTEMPTS)
            )
        default = os.fstat(handle).st_mode & 0o7777
        if hasattr(os, "fchmod"):
            # Restrictive while the document is being written, because it carries
            # the model's source and the directory may be shared. Windows has no
            # `fchmod` and no mode beyond the read-only bit.
            os.fchmod(handle, 0o600)
        stream = os.fdopen(
            handle, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})
        )
        yield stream, staging, default
    except OSError as error:
        # The path the caller asked for, whatever the operation names. A full disk
        # surfaced as a bare `[Errno 28] No space left on device` with no clue
        # which save it was, because the failure was on a descriptor rather than a
        # path; where the operation does name something -- `os.open`, `os.replace`
        # -- it names the staging file nobody asked about. This is the same reason
        # `_validate_write_target` exists, applied to the write itself. The class
        # and `errno` are left alone: callers catch `PermissionError` and read
        # `errno`, and `OSError.__str__` appends `filename` for us.
        #
        # Only where the OS raised it. An `OSError` built from a single message --
        # this module raises one when no staging name is free -- has no `errno`,
        # and setting `filename` switches `__str__` to the three-part form, which
        # would print `[Errno None] None: '<path>'` over the message. Those name
        # the target themselves.
        if error.errno is not None:
            error.filename = str(target)
            if error.filename2 is not None:
                # `os.replace` names both of its paths, and the first is the
                # staging file. Deleting the attribute rather than assigning
                # ``None`` is what gets `OSError.__str__` back to its one-path
                # form: the member is a pointer, so ``None`` still reads as set
                # and renders `-> None`.
                del error.filename2
        raise
    finally:
        # However this ends -- an interrupt at any line above included -- exactly
        # one thing owns the descriptor, and the file exists only if we made it.
        if stream is not None:
            _close_quietly(stream, staging)
        elif handle >= 0:
            try:
                os.close(handle)
            except OSError as close_error:
                # EBADF, where `os.fdopen` failed part-way and closed the
                # descriptor it had already wrapped. Nothing is leaking; there is
                # just nothing left to close.
                _report_degradation(
                    "could not close the staging descriptor for %s: %s",
                    staging,
                    close_error,
                )
        if staging is not None:
            _discard(staging)


def _close_quietly(stream: Any, staging: Optional[Path]) -> None:
    """
    Close a staging stream, reporting rather than raising if it will not.

    :param stream: Stream opened on the staging file.
    :type stream: io.IOBase
    :param staging: Path the stream was opened on, for the message, or ``None``
        once ownership of the path has been handed on and the stream is already
        closed -- where there is nothing left to report.
    :type staging: pathlib.Path or None
    :return: ``None``.
    :rtype: None
    """
    try:
        stream.close()
    except OSError as close_error:
        # EIO or ENOSPC surfacing from buffered data that never reached the disk.
        # Whatever brought us here is the outcome the caller needs.
        _report_degradation(
            "could not close the staging file %s: %s", staging, close_error
        )


def _discard(path: Path) -> None:
    """
    Remove a temporary file, reporting rather than raising if it cannot be.

    :param path: Path that may or may not still exist.
    :type path: pathlib.Path
    :return: ``None``.
    :rtype: None
    """
    try:
        path.unlink()
    except FileNotFoundError:
        # A staging file renamed onto its target, or a viewer the user removed
        # while the window was open. Both are ordinary.
        pass
    except OSError as removal_error:
        # PermissionError from an indexer or a browser holding the handle, EROFS
        # or ENOSPC from a read-only or exhausted filesystem. Whatever brought us
        # here is what the caller needs to see, so this only gets recorded.
        _report_degradation(
            "could not remove the temporary file %s: %s", path, removal_error
        )


def _final_mode(target: Path, requested: Optional[int], default: int) -> int:
    """
    Decide the mode the target should end up with.

    An explicit request wins, because callers use it for paths whose name is
    predictable and where an existing file may not be theirs.  Otherwise an
    existing target keeps its own mode -- re-saving must not silently downgrade
    a file someone made world-readable -- and a new one gets what any other new
    file in that directory would.

    :param target: Destination the caller asked for.
    :type target: pathlib.Path
    :param requested: Mode to force, or ``None``.
    :type requested: int, optional
    :param default: Mode a new file receives in the destination directory.
    :type default: int
    :return: Permission bits to apply before the replace.
    :rtype: int
    """
    if requested is not None:
        return requested
    try:
        return target.stat().st_mode & 0o7777
    except FileNotFoundError:
        # The usual case: the target does not exist yet, so there is no mode to
        # preserve. Other stat failures surface from _validate_write_target,
        # which runs first and re-raises them from its own is_dir() call.
        return default


def _write_protection_reason(target: Path) -> Optional[str]:
    """
    Say why an existing target must not be replaced, or ``None`` if it may be.

    The reason rather than a bare ``True``, because the two platforms refuse for
    different reasons: a single hardcoded message sent Windows users to look at
    file ownership, which is not the question there.

    On POSIX the question is ownership rather than writability.  ``os.replace``
    only needs write permission on the *directory*, so a file made read-only by
    somebody else would be swapped out silently -- and because an existing target
    keeps its own mode, nothing about the result would show it.  Our own
    read-only file is a different matter: the owner can put the write bit back at
    any time, so replacing it overrides nobody, and refusing on that basis made
    :meth:`Diagram.save` a one-shot operation under a umask that clears the bit.

    :param target: Destination the caller asked for.
    :type target: pathlib.Path
    :return: Sentence completing "cannot write <path>: ...", or ``None``.
    :rtype: str or None
    """
    try:
        info = target.stat()
    except OSError:
        # FileNotFoundError when there is nothing to protect; any other stat
        # failure is raised by `_validate_write_target`'s own checks.
        return None
    if os.access(str(target), os.W_OK):
        return None
    if not hasattr(os, "geteuid"):
        # Windows. `os.replace` maps to `MoveFileEx(MOVEFILE_REPLACE_EXISTING)`,
        # which refuses a read-only target however it came to be read-only and
        # whoever owns it, so there is no ownership question to ask here and no
        # exemption to grant for a file of our own -- the platform withholds the
        # permission that POSIX takes from the directory. Saying so here keeps
        # the `MoveFileEx` failure, which names the staging file, out of the way.
        return "it is marked read-only; clear the read-only attribute and retry"
    if info.st_uid != os.geteuid():
        return "the file belongs to another user and is not writable"
    return None


def _validate_write_target(target: Path) -> None:
    """
    Reject a destination before a temporary sibling is created for it.

    Without this the failure surfaces from the sibling file instead: writing to
    a directory reported a permission error on a hidden dotfile in its parent,
    naming neither the path the caller passed nor the actual problem.

    :param target: Requested destination path.
    :type target: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises IsADirectoryError: If the destination is an existing directory.
    :raises FileNotFoundError: If the parent directory does not exist.
    :raises NotADirectoryError: If the parent exists but is not a directory.
    :raises PermissionError: If the target is an existing file that must not be
        replaced -- unwritable and owned by another user on POSIX, marked
        read-only on Windows -- or the parent directory will not accept a new
        file.
    """
    if target.is_dir():
        raise IsADirectoryError("cannot write %s: it is a directory" % target)
    parent = target.parent
    if not parent.exists():
        raise FileNotFoundError(
            "cannot write %s: the directory %s does not exist" % (target, parent)
        )
    if not parent.is_dir():
        raise NotADirectoryError(
            "cannot write %s: %s is not a directory" % (target, parent)
        )
    protection = _write_protection_reason(target)
    if protection is not None:
        raise PermissionError("cannot write %s: %s" % (target, protection))
    if not os.access(str(parent), os.W_OK):
        # Checked here for the same reason as the cases above: the write itself
        # fails on the staging sibling, so the caller is told about a hidden
        # `.doc.html.<random>` they never asked for. A read-only output
        # directory is an ordinary mistake and deserves an ordinary message.
        raise PermissionError(
            "cannot write %s: the directory %s is not writable" % (target, parent)
        )


def _atomic_write_text(
    path: Union[str, os.PathLike], content: str, mode: Optional[int] = None
) -> Path:
    """
    Replace a text file atomically using a staging sibling.

    :param path: Destination path.
    :type path: str or os.PathLike
    :param content: Content to write.
    :type content: str
    :param mode: Force this mode on the result instead of deriving one.
    :type mode: int, optional
    :return: The destination path.
    :rtype: pathlib.Path
    :raises FileNotFoundError: If the parent directory does not exist.
    :raises IsADirectoryError: If ``path`` is an existing directory.
    :raises NotADirectoryError: If the parent path is not a directory.
    :raises PermissionError: If the target is an existing file that must not
        be replaced -- unwritable and owned by another user on POSIX, marked
        read-only on Windows -- or its directory will not accept a new file.
    :raises OSError: If the write itself fails, for example on a full or
        read-only filesystem.
    """
    target = Path(path)
    _validate_write_target(target)
    # The staging file has an owner for its whole life, so no unwinding -- an
    # interrupt included -- can leave the descriptor or the file behind.
    with _staging_file(target, binary=False) as (stream, staging, default):
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        os.chmod(str(staging), _final_mode(target, mode, default))
        os.replace(str(staging), str(target))
    return target


def _atomic_write_bytes(
    path: Union[str, os.PathLike], content: bytes, mode: Optional[int] = None
) -> Path:
    """
    Replace a binary file atomically using a staging sibling.

    :param path: Destination path.
    :type path: str or os.PathLike
    :param content: Content to write.
    :type content: bytes
    :param mode: Force this mode on the result instead of deriving one.
    :type mode: int, optional
    :return: The destination path.
    :rtype: pathlib.Path
    :raises FileNotFoundError: If the parent directory does not exist.
    :raises IsADirectoryError: If ``path`` is an existing directory.
    :raises NotADirectoryError: If the parent path is not a directory.
    :raises PermissionError: If the target is an existing file that must not
        be replaced -- unwritable and owned by another user on POSIX, marked
        read-only on Windows -- or its directory will not accept a new file.
    :raises OSError: If the write itself fails, for example on a full or
        read-only filesystem.
    """
    target = Path(path)
    _validate_write_target(target)
    # The staging file has an owner for its whole life, so no unwinding -- an
    # interrupt included -- can leave the descriptor or the file behind.
    with _staging_file(target, binary=True) as (stream, staging, default):
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        os.chmod(str(staging), _final_mode(target, mode, default))
        os.replace(str(staging), str(target))
    return target


def _embedded_font_css(locale: str) -> str:
    """Return data-URI font faces for the selected locale only."""
    payload = _embedded_font_payload(locale)
    rules = []
    for item in payload:
        family, weight, encoded, mime = item
        rules.append(
            "@font-face{font-family:%s;font-style:normal;font-weight:%d;src:url(data:%s;base64,%s) format('opentype');font-display:block}"
            % (json.dumps(family), weight, mime, encoded)
        )
    return "\n".join(rules)


def _embedded_font_payload(locale: str) -> List[Tuple[str, int, str, str]]:
    """Return the selected browser font faces as base64 payload records."""
    cjk = {
        "sc": ("NotoSansSC", "otf"),
        "tc": ("NotoSansTC", "otf"),
        "hk": ("NotoSansHK", "otf"),
        "jp": ("NotoSansJP", "otf"),
        "kr": ("NotoSansKR", "otf"),
    }.get(str(locale).lower(), ("NotoSansSC", "otf"))[0]
    faces = [
        ("JetBrains Mono", 400, "fonts/JetBrainsMono-Regular.ttf", "font/ttf"),
        ("JetBrains Mono", 500, "fonts/JetBrainsMono-Medium.ttf", "font/ttf"),
        ("JetBrains Mono", 700, "fonts/JetBrainsMono-Bold.ttf", "font/ttf"),
        ("Noto Sans %s" % cjk[8:], 400, "fonts/%s-Regular.otf" % cjk, "font/otf"),
        ("Noto Sans %s" % cjk[8:], 700, "fonts/%s-Bold.otf" % cjk, "font/otf"),
    ]
    payload: List[Tuple[str, int, str, str]] = []
    for family, weight, path, mime in faces:
        data = _asset_bytes(path)
        encoded = base64.b64encode(data).decode("ascii")
        payload.append((family, weight, encoded, mime))
    return payload


def _asset_text(name: str) -> str:
    data = _asset_bytes(name)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as err:
        # UnicodeDecodeError: generated JavaScript or CSS is not valid UTF-8.
        raise _asset_failure(name, "the text resource is not valid UTF-8", err) from err


def _embedded_resvg_script(locale: str) -> str:
    """Build the offline browser helper that expands SVG through resvg WASM."""
    wasm = _asset_bytes("resvg.wasm")
    cjk_family = {
        "sc": "Noto Sans SC",
        "tc": "Noto Sans TC",
        "hk": "Noto Sans HK",
        "jp": "Noto Sans JP",
        "kr": "Noto Sans KR",
    }.get(str(locale).lower(), "Noto Sans SC")
    wasm_payload = base64.b64encode(wasm).decode("ascii")
    binding = _asset_text("resvg-binding.js")
    return (
        binding
        + "\n"
        + "window.__FCSTM_RESVG_READY__=WebAssembly.compile(Uint8Array.from(atob(%s),function(c){return c.charCodeAt(0)})).then(function(m){return resvg.initWasm(m)});\n"
        % json.dumps(wasm_payload)
        + "window.__FCSTM_EXPAND_SVG__=async function(svg){await window.__FCSTM_RESVG_READY__;var css=Array.from(document.querySelectorAll('style')).map(function(x){return x.textContent||''}).join('\\n');var re=/font-family:\\s*\\\"([^\\\"]+)\\\"[^}]*font-weight:\\s*(\\d+)[^}]*base64,([^)'\\s]+)/g,b=[],m;while((m=re.exec(css))!==null){var raw=atob(m[3]),u=new Uint8Array(raw.length);for(var i=0;i<raw.length;i++)u[i]=raw.charCodeAt(i);b.push(u)}if(!b.length)throw new Error('embedded font data is unavailable');var r=new resvg.Resvg(String(svg),{font:{fontBuffers:b,loadSystemFonts:false,defaultFontFamily:%s,monospaceFamily:'JetBrains Mono'},shapeRendering:2,textRendering:2});try{return r.toString()}finally{r.free()}};\n"
        % json.dumps(cjk_family)
    )


@dataclass(frozen=True)
class DiagramOptions:
    """
    Immutable renderer options shared by Python and browser diagram views.

    :param detail_level: Detail preset, one of ``minimal``, ``normal`` or
        ``full``.  Recorded in the generated document and validated here, but
        the bundled viewer draws the same diagram for all three: the four
        settings the presets disagree on are state event labels, state action
        labels, transition-effect placement and event placement, and none of
        them reaches the standalone drawing path yet.  Treat it as a stored
        preference rather than a way to change what a viewer shows.
    :type detail_level: str
    :param direction: Layout direction, either ``TB`` or ``LR``.
    :type direction: str
    :param palette: Optional shared palette identifier.  When omitted, the
        browser preference is used.
    :type palette: str, optional
    :param mode: Optional colour mode, either ``light``, ``dark`` or ``auto``.
        When omitted, the browser preference is used.
    :type mode: str, optional
    :param cjk_locale: Embedded CJK font locale: ``sc``, ``tc``, ``hk``,
        ``jp`` or ``kr``.
    :type cjk_locale: str

    Example::

        >>> options = DiagramOptions(direction="LR", cjk_locale="sc")
        >>> options.to_dict()["direction"]
        'LR'
    """

    detail_level: str = "normal"
    direction: str = "TB"
    palette: Optional[str] = None
    mode: Optional[str] = None
    cjk_locale: str = "sc"

    def __post_init__(self) -> None:
        if self.detail_level not in ("minimal", "normal", "full"):
            raise ValueError("detail_level must be 'minimal', 'normal', or 'full'")
        if self.direction not in ("TB", "LR"):
            raise ValueError("direction must be 'TB' or 'LR'")
        if self.palette is not None and self.palette not in (
            "default",
            "nord",
            "solarized",
            "darcula",
        ):
            raise ValueError("unsupported palette: %s" % self.palette)
        locale = str(self.cjk_locale).lower()
        if locale not in ("sc", "tc", "hk", "jp", "kr"):
            raise ValueError("unsupported CJK locale: %s" % self.cjk_locale)
        object.__setattr__(self, "cjk_locale", locale)
        if self.mode is not None and self.mode not in ("light", "dark", "auto"):
            raise ValueError("mode must be 'light', 'dark', or 'auto'")

    def to_dict(self) -> Dict[str, Any]:
        """
        Return the renderer-ready jsfcstm option shape.

        .. note::
           This is the renderer's option vocabulary, not a serialization of
           this object. ``palette`` and ``mode`` are presentation choices the
           renderer takes elsewhere and do not appear here, and the remaining
           keys are fixed renderer defaults. The result is therefore **not**
           accepted back by :class:`Diagram`; use :func:`dataclasses.replace`
           or :meth:`Diagram.with_options` to derive changed options.

        :return: A new JSON-compatible option mapping.
        :rtype: dict
        """
        # The eight keys the detail level governs are deliberately absent. The
        # renderer fills them from its preset for the requested level, and
        # spelling them out here — with what happened to be the ``normal``
        # values — made ``detail_level`` inert: an explicit value always won, so
        # ``minimal`` and ``full`` rendered exactly like ``normal``. The keys
        # below are the ones no preset covers.
        return {
            "detailLevel": self.detail_level,
            "direction": self.direction,
            "cjkLocale": self.cjk_locale,
            "eventNameFormat": ["extra_name", "relpath"],
            "maxStateEvents": 4,
            "maxStateActions": 4,
            "maxTransitionEffectLines": 8,
            "maxLabelLength": 160,
        }


def _source_unavailable_reason(source: str, source_map: Mapping[str, Any]) -> str:
    """
    Explain why the viewer cannot link the diagram to its source.

    :param source: Source text carried by the snapshot, empty when absent.
    :type source: str
    :param source_map: Mapping from diagram element ID to a source range.
    :type source_map: collections.abc.Mapping
    :return: A reason for the viewer to show, or ``''`` when linking works.
    :rtype: str
    """
    if not source:
        return (
            "This model did not retain its original FCSTM source; load it through "
            "load_state_machine_from_file/text, or pass source_text explicitly."
        )
    if not source_map:
        return (
            "This model carries source text but no source ranges, so the diagram "
            "cannot be linked to it. Ranges come from parsing; a model built "
            "programmatically has none."
        )
    return ""


@dataclass(frozen=True)
class DiagramViewState:
    """
    Immutable browser state for collapse, zoom, pan and display mode.

    :param mode: ``fcstm`` for source-only, ``diagram`` for diagram-only, or
        ``compare`` for the linked split view.
    :type mode: str
    :param collapsed_state_ids: Qualified state IDs hidden in the diagram.
    :type collapsed_state_ids: tuple[str, ...]
    :param zoom: Positive initial zoom factor. ``None`` leaves the initial
        framing to the viewer, which fits the whole diagram to the viewport.
    :type zoom: float, optional
    :param pan_x: Initial horizontal pan offset in CSS pixels. ``None`` defers
        to the fitted framing, or to ``0`` when another field is set.
    :type pan_x: float, optional
    :param pan_y: Initial vertical pan offset in CSS pixels. ``None`` defers
        to the fitted framing, or to ``0`` when another field is set.
    :type pan_y: float, optional

    Example::

        >>> DiagramViewState(mode="fcstm").to_dict()["mode"]
        'fcstm'
    """

    mode: str = "compare"
    collapsed_state_ids: Tuple[str, ...] = ()
    # None is "no preference", which the viewer renders as fit-to-view. Keeping
    # the neutral numbers as defaults would make an explicit 1.0 / 0.0 request
    # indistinguishable from an absent one, and the viewer could only guess.
    zoom: Optional[float] = None
    pan_x: Optional[float] = None
    pan_y: Optional[float] = None

    def __post_init__(self) -> None:
        if self.mode not in ("fcstm", "diagram", "compare"):
            raise ValueError("mode must be 'fcstm', 'diagram', or 'compare'")
        ids = self.collapsed_state_ids
        # A single ID is the obvious mistake here, and str is iterable, so
        # tuple() would turn "Root.Run" into eight one-character IDs that
        # collapse nothing and report no error.
        if isinstance(ids, (str, bytes)):
            raise TypeError(
                "collapsed_state_ids must be a sequence of state IDs, not the "
                "single ID %r; wrap it in a tuple or list" % (ids,)
            )
        if not isinstance(ids, Iterable):
            raise TypeError(
                "collapsed_state_ids must be an iterable of state IDs, got %s"
                % type(ids).__name__
            )
        ids = tuple(ids)
        for item in ids:
            if not isinstance(item, str):
                raise TypeError(
                    "collapsed_state_ids entries must be state ID strings, got %r"
                    % (item,)
                )
        object.__setattr__(self, "collapsed_state_ids", ids)
        if self.zoom is not None:
            object.__setattr__(
                self, "zoom", _coerce_finite_number(self.zoom, "zoom", positive=True)
            )
        if self.pan_x is not None:
            object.__setattr__(
                self, "pan_x", _coerce_finite_number(self.pan_x, "pan_x offsets")
            )
        if self.pan_y is not None:
            object.__setattr__(
                self, "pan_y", _coerce_finite_number(self.pan_y, "pan_y offsets")
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return deterministic browser state keys.

        :return: A new JSON-compatible browser state mapping.
        :rtype: dict
        """
        return {
            "mode": self.mode,
            "collapsedStateIds": list(self.collapsed_state_ids),
            "zoom": self.zoom,
            "panX": self.pan_x,
            "panY": self.pan_y,
        }


@dataclass(frozen=True, eq=False)
class DiagramData:
    """
    Portable, deterministic diagram data without editor-only metadata.

    :param value: Renderer data. Source ranges, local paths and other
        editor-only fields are removed when the value is stored.
    :type value: collections.abc.Mapping[str, object]

    Example::

        >>> data = DiagramData({"kind": "diagram", "rootState": {"children": []}})
        >>> data.to_dict()["kind"]
        'diagram'
    """

    value: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.value, Mapping):
            raise TypeError("DiagramData.value must be a mapping")
        object.__setattr__(self, "value", _freeze_value(_portable_value(self.value)))

    def _canonical(self) -> str:
        """
        Return the canonical JSON text both equality and hashing are defined on.

        :return: Deterministic JSON with sorted keys and no insignificant space.
        :rtype: str
        """
        return json.dumps(
            _thaw_value(self.value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def __eq__(self, other: Any) -> bool:
        """
        Compare two snapshots by the same representation that hashes them.

        The generated comparison used Python's numeric rules, where ``1`` equals
        ``1.0`` and ``True`` equals ``1``, while the hash came from the JSON
        bytes, where they differ. Equal snapshots therefore missed each other in
        a ``dict`` and stacked up in a ``set``, breaking the invariant that
        equal objects hash alike. For a content-addressed value, the bytes are
        the identity.

        :param other: Value to compare against.
        :type other: Any
        :return: ``True`` when both are snapshots with identical canonical JSON.
        :rtype: bool
        """
        if not isinstance(other, DiagramData):
            return NotImplemented
        return self._canonical() == other._canonical()

    def __hash__(self) -> int:
        """
        Hash the immutable snapshot by its canonical JSON representation.

        The digest comes from SHA-256 rather than :func:`hash`, so equal
        snapshots keep the same value across processes and the result stays
        usable as a persisted content key.

        :return: A hash consistent for equal immutable snapshots, including
            across separate interpreter processes.
        :rtype: int
        """
        return int(
            hashlib.sha256(self._canonical().encode("utf-8")).hexdigest()[:16], 16
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a deep JSON-compatible copy of the portable contract.

        :return: An independent mapping; mutating it does not change this
            snapshot.
        :rtype: dict
        """
        return json.loads(
            json.dumps(_thaw_value(self.value), ensure_ascii=False, sort_keys=True)
        )

    def to_json(self, **kwargs: Any) -> str:
        """
        Serialize portable data with stable key ordering.

        :param kwargs: Optional keyword overrides passed to
            :func:`json.dumps`.
        :return: Deterministic UTF-8 JSON text.
        :rtype: str
        """
        options = {"ensure_ascii": False, "sort_keys": True, "separators": (",", ":")}
        options.update(kwargs)
        return json.dumps(self.to_dict(), **options)


class Diagram:
    """
    Immutable snapshot of a state machine, as portable data or a viewer.

    Built by :meth:`pyfcstm.model.model.StateMachine.diagram`.  The snapshot is taken
    once and detached from the model, so editing the model afterwards cannot
    change what an already-saved view shows.  Attribute assignment is refused
    for the same reason; :meth:`with_options` and :meth:`with_view_state` return
    new snapshots instead of mutating this one.

    :meth:`to_dict` and :meth:`to_json` give the portable form.  :meth:`to_html`
    gives a single self-contained document -- roughly 29 MB, with the renderer,
    layout engine, rasteriser and CJK fonts embedded under a strict inline
    policy and no network access -- and :meth:`show` opens it in a
    Chromium-family app window.

    :meth:`to_svg`, :meth:`to_png` and :meth:`to_pdf` are typed probes that
    always raise :class:`pyfcstm.diagram.engine.DiagramUnavailableError`: SVG, PNG and
    PDF are produced by the embedded viewer's own export, which needs a browser.
    They exist so the failure names the reason instead of the attribute being
    absent.

    :param model: State machine to snapshot.
    :type model: pyfcstm.model.model.StateMachine
    :param options: Renderer options, or a mapping of them, defaults to
        :class:`pyfcstm.diagram.api.DiagramOptions` with its own defaults.
    :type options: pyfcstm.diagram.api.DiagramOptions or collections.abc.Mapping,
        optional
    :param view_state: Initial browser view state, or a mapping of it, defaults
        to :class:`pyfcstm.diagram.api.DiagramViewState` with its own defaults.
    :type view_state: pyfcstm.diagram.api.DiagramViewState or
        collections.abc.Mapping, optional
    :param source_text: FCSTM source for the viewer's source pane, defaults to
        the text the model was parsed from.
    :type source_text: str, optional

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text(
        ...     'state Root { [*] -> A; state A; state B; A -> B :: Go; }'
        ... )
        >>> view = model.diagram(direction='LR')
        >>> view.to_dict()['machineName']
        'Root'
        >>> view.options.direction
        'LR'
        >>> view.with_options(direction='TB').options.direction
        'TB'
        >>> view.options.direction
        'LR'
    """

    @staticmethod
    def _normalize_options(value: Optional[Any]) -> DiagramOptions:
        if isinstance(value, Mapping):
            _reject_unknown_mapping_keys(value, _OPTION_KEYS, "DiagramOptions")
            return DiagramOptions(
                detail_level=str(
                    _mapping_value(value, "detail_level", "detailLevel", "normal")
                ),
                direction=str(value.get("direction", "TB")),
                palette=(
                    None if value.get("palette") is None else str(value.get("palette"))
                ),
                mode=(None if value.get("mode") is None else str(value.get("mode"))),
                cjk_locale=str(_mapping_value(value, "cjk_locale", "cjkLocale", "sc")),
            )
        if value is not None and not isinstance(value, DiagramOptions):
            raise TypeError("options must be DiagramOptions or a mapping")
        return value or DiagramOptions()

    @staticmethod
    def _normalize_view_state(value: Optional[Any]) -> DiagramViewState:
        if isinstance(value, Mapping):
            _reject_unknown_mapping_keys(value, _VIEW_STATE_KEYS, "DiagramViewState")
            return DiagramViewState(
                mode=str(value.get("mode", "compare")),
                # Forwarded unconverted: calling tuple() here consumed a bare
                # string into one entry per character before __post_init__
                # could reject it, so the mapping and keyword paths — which is
                # how most callers arrive — skipped that validation entirely.
                collapsed_state_ids=_mapping_value(
                    value, "collapsed_state_ids", "collapsedStateIds", ()
                ),
                zoom=value.get("zoom", None),
                pan_x=_mapping_value(value, "pan_x", "panX", None),
                pan_y=_mapping_value(value, "pan_y", "panY", None),
            )
        if value is not None and not isinstance(value, DiagramViewState):
            raise TypeError("view_state must be DiagramViewState or a mapping")
        return value or DiagramViewState()

    def __init__(
        self,
        model: StateMachine,
        options: Optional[DiagramOptions] = None,
        view_state: Optional[DiagramViewState] = None,
        source_text: Optional[str] = None,
    ) -> None:
        """
        Create a diagram snapshot for a state machine.

        :param model: State machine whose semantics and source sidecar are
            displayed.
        :type model: pyfcstm.model.model.StateMachine
        :param options: Optional immutable renderer options or a compatible
            mapping.
        :type options: pyfcstm.diagram.api.DiagramOptions or collections.abc.Mapping, optional
        :param view_state: Optional immutable browser state or compatible
            mapping.
        :type view_state: pyfcstm.diagram.api.DiagramViewState or collections.abc.Mapping, optional
        :param source_text: Optional FCSTM source for the source pane. It must
            match the text the model was parsed from; programmatic models
            without source ranges accept any value.
        :type source_text: str, optional
        """
        self.model = model
        self.options = self._normalize_options(options)
        self.view_state = self._normalize_view_state(view_state)
        self.source_text = model.source_text if source_text is None else source_text
        renderer_diagram = _build_diagram_dict(model, include_ranges=True)
        self._renderer_diagram = _freeze_value(renderer_diagram)
        self.data = DiagramData(renderer_diagram)
        (
            self._source,
            self._source_map,
            self._source_line_map,
            self._source_documents,
        ) = _source_sidecar(model, self.source_text, diagram=renderer_diagram)
        self._source_document_id = _source_document_id(
            model, model.source_path or "<memory>"
        )
        self._html_document: Optional[str] = None
        self._frozen = True

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Reject attribute assignment once the snapshot is built.

        The class is documented as an immutable snapshot and its data really is
        frozen, but the container was not: reassigning ``data`` or ``options``
        after the fact produced a snapshot that no longer described the model it
        was taken from. Internal setup goes through ``object.__setattr__``.

        :param name: Attribute name.
        :type name: str
        :param value: Attribute value.
        :type value: Any
        :return: ``None``.
        :rtype: None
        :raises AttributeError: If the snapshot has finished initializing.
        """
        if getattr(self, "_frozen", False):
            raise AttributeError(
                "Diagram snapshots are immutable; derive a new one with "
                "with_options() or with_view_state() instead of setting %r" % name
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        """
        Reject attribute deletion once the snapshot is built.

        Guarding only assignment left ``del`` as a way around it: removing the
        freeze flag reopened the object, and removing a field corrupted the
        snapshot outright.

        :param name: Attribute name.
        :type name: str
        :return: ``None``.
        :rtype: None
        :raises AttributeError: If the snapshot has finished initializing.
        """
        if getattr(self, "_frozen", False):
            raise AttributeError(
                "Diagram snapshots are immutable; %r cannot be deleted" % name
            )
        object.__delattr__(self, name)

    def _clone_snapshot(self, options: Any, view_state: Any) -> "Diagram":
        """Create a derived view without rereading the mutable model."""
        clone = object.__new__(type(self))
        assign = object.__setattr__
        assign(clone, "model", self.model)
        assign(clone, "options", self._normalize_options(options))
        assign(clone, "view_state", self._normalize_view_state(view_state))
        assign(clone, "source_text", self.source_text)
        assign(clone, "_renderer_diagram", self._renderer_diagram)
        assign(clone, "data", self.data)
        assign(clone, "_source", self._source)
        # The top level is copied so a derived snapshot cannot have entries
        # added or removed under it. The nested values stay shared; they are
        # only ever read, and deep-copying them would duplicate the whole
        # source sidecar on every derivation.
        assign(clone, "_source_map", dict(self._source_map))
        assign(clone, "_source_line_map", dict(self._source_line_map))
        assign(clone, "_source_documents", dict(self._source_documents))
        assign(clone, "_source_document_id", self._source_document_id)
        assign(clone, "_html_document", None)
        assign(clone, "_frozen", True)
        return clone

    def to_dict(self) -> Dict[str, Any]:
        """
        Return portable diagram data.

        :return: An independent JSON-compatible mapping without local paths
            or source ranges.
        :rtype: dict
        """
        return self.data.to_dict()

    def to_json(self, **kwargs: Any) -> str:
        """
        Return portable diagram data as deterministic JSON.

        :param kwargs: Optional keyword overrides passed to
            :func:`json.dumps`.
        :return: UTF-8 JSON text.
        :rtype: str
        """
        return self.data.to_json(**kwargs)

    @staticmethod
    def _merge_option_fields(
        current: DiagramOptions, updates: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """
        Overlay caller-supplied option fields onto the current options.

        The keyword form reads like :func:`dataclasses.replace`, so treating it
        as a whole-object replacement silently reset every field the caller did
        not repeat.

        :param current: Options the snapshot is being derived from.
        :type current: pyfcstm.diagram.api.DiagramOptions
        :param updates: Snake-case or camel-case fields to change.
        :type updates: collections.abc.Mapping
        :return: A complete option mapping ready for normalization.
        :rtype: dict
        :raises ValueError: If a field is unknown or supplied under both spellings.
        """
        _reject_unknown_mapping_keys(updates, _OPTION_KEYS, "DiagramOptions")
        merged = {
            "detail_level": current.detail_level,
            "direction": current.direction,
            "palette": current.palette,
            "mode": current.mode,
            "cjk_locale": current.cjk_locale,
        }
        missing = object()
        for snake, camel in (
            ("detail_level", "detailLevel"),
            ("cjk_locale", "cjkLocale"),
        ):
            supplied = _mapping_value(updates, snake, camel, missing)
            if supplied is not missing:
                merged[snake] = supplied
        for name in ("direction", "palette", "mode"):
            if name in updates:
                merged[name] = updates[name]
        return merged

    @staticmethod
    def _merge_view_state_fields(
        current: DiagramViewState, updates: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """
        Overlay caller-supplied view-state fields onto the current view state.

        :param current: View state the snapshot is being derived from.
        :type current: pyfcstm.diagram.api.DiagramViewState
        :param updates: Snake-case or camel-case fields to change.
        :type updates: collections.abc.Mapping
        :return: A complete view-state mapping ready for normalization.
        :rtype: dict
        :raises ValueError: If a field is unknown or supplied under both spellings.
        """
        _reject_unknown_mapping_keys(updates, _VIEW_STATE_KEYS, "DiagramViewState")
        merged = {
            "mode": current.mode,
            "collapsed_state_ids": current.collapsed_state_ids,
            "zoom": current.zoom,
            "pan_x": current.pan_x,
            "pan_y": current.pan_y,
        }
        missing = object()
        for snake, camel in (
            ("collapsed_state_ids", "collapsedStateIds"),
            ("pan_x", "panX"),
            ("pan_y", "panY"),
        ):
            supplied = _mapping_value(updates, snake, camel, missing)
            if supplied is not missing:
                merged[snake] = supplied
        for name in ("mode", "zoom"):
            if name in updates:
                merged[name] = updates[name]
        return merged

    def with_options(self, options: Optional[Any] = None, **kwargs: Any) -> "Diagram":
        """
        Return a new snapshot with replacement renderer options.

        :param options: An immutable options value or mapping that replaces the
            current options wholesale. If omitted, the keyword fields below are
            applied as a partial update instead.
        :type options: pyfcstm.diagram.api.DiagramOptions or collections.abc.Mapping, optional
        :param kwargs: Snake-case or camel-case option fields to change. Fields
            that are not named keep their current value.
        :return: A new independent diagram snapshot.
        :rtype: pyfcstm.diagram.api.Diagram
        :raises TypeError: If both ``options`` and keyword fields are supplied.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> dark = model.diagram(direction="LR").with_options(mode="dark")
            >>> dark.options.mode
            'dark'
            >>> dark.options.direction  # keyword fields are a partial update
            'LR'
        """
        if options is not None and kwargs:
            raise TypeError("provide options or keyword fields, not both")
        replacement = (
            options
            if options is not None
            else (
                self._merge_option_fields(self.options, kwargs)
                if kwargs
                else self.options
            )
        )
        return self._clone_snapshot(replacement, self.view_state)

    def with_view_state(
        self, view_state: Optional[Any] = None, **kwargs: Any
    ) -> "Diagram":
        """
        Return a new snapshot with replacement browser view state.

        :param view_state: An immutable view state value or mapping that
            replaces the current view state wholesale. If omitted, the keyword
            fields below are applied as a partial update instead.
        :type view_state: pyfcstm.diagram.api.DiagramViewState or collections.abc.Mapping, optional
        :param kwargs: Snake-case or camel-case view-state fields to change.
            Fields that are not named keep their current value.
        :return: A new independent diagram snapshot.
        :rtype: pyfcstm.diagram.api.Diagram
        :raises TypeError: If both ``view_state`` and keyword fields are supplied.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> zoomed = model.diagram(view_state={"zoom": 2.0})
            >>> source_only = zoomed.with_view_state(mode="fcstm")
            >>> source_only.view_state.mode
            'fcstm'
            >>> source_only.view_state.zoom  # unnamed fields keep their value
            2.0
        """
        if view_state is not None and kwargs:
            raise TypeError("provide view_state or keyword fields, not both")
        replacement = (
            view_state
            if view_state is not None
            else (
                self._merge_view_state_fields(self.view_state, kwargs)
                if kwargs
                else self.view_state
            )
        )
        return self._clone_snapshot(self.options, replacement)

    def to_svg(self) -> str:
        """
        Request a synchronous headless SVG export.

        :return: Nothing; this method always raises.
        :rtype: str
        :raises DiagramUnavailableError: Always.  SVG is produced by the
            embedded viewer's own export, which needs a browser.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> view = load_state_machine_from_text('state Root;').diagram()
            >>> view.to_svg()
            Traceback (most recent call last):
            ...
            pyfcstm.diagram.engine.DiagramUnavailableError: headless SVG export ...
        """
        raise DiagramUnavailableError(
            "headless SVG export is unavailable; use Diagram.to_html() browser export "
            "instead; `pip install pyfcstm[viz]` adds the rendering runtime but not "
            "a synchronous Python export"
        )

    def to_png(self, scale: float = 1.0) -> bytes:
        """
        Request a synchronous headless PNG export.

        :param scale: Positive finite output scale, validated before the
            unavailability is reported so a bad value is named first.
        :type scale: float
        :return: Nothing; this method always raises once ``scale`` is valid.
        :rtype: bytes
        :raises ValueError: If ``scale`` is not finite and positive.
        :raises DiagramUnavailableError: Always.  PNG is produced by the
            embedded viewer's own export, which needs a browser.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> view = load_state_machine_from_text('state Root;').diagram()
            >>> view.to_png(scale=-1)
            Traceback (most recent call last):
            ...
            ValueError: scale must be positive ...
            >>> view.to_png()
            Traceback (most recent call last):
            ...
            pyfcstm.diagram.engine.DiagramUnavailableError: headless PNG export ...
        """
        _coerce_finite_number(scale, "scale", positive=True)
        raise DiagramUnavailableError(
            "headless PNG export is unavailable; use Diagram.to_html() browser export "
            "instead; `pip install pyfcstm[viz]` adds the rendering runtime but not "
            "a synchronous Python export"
        )

    def to_pdf(self) -> bytes:
        """
        Request a synchronous headless vector PDF export.

        :return: Nothing; this method always raises.
        :rtype: bytes
        :raises DiagramUnavailableError: Always.  PDF is produced by the
            embedded viewer's own export, which needs a browser.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> view = load_state_machine_from_text('state Root;').diagram()
            >>> view.to_pdf()
            Traceback (most recent call last):
            ...
            pyfcstm.diagram.engine.DiagramUnavailableError: headless PDF export ...
        """
        raise DiagramUnavailableError(
            "headless PDF export is unavailable; use Diagram.to_html() browser export "
            "instead; `pip install pyfcstm[viz]` adds the rendering runtime but not "
            "a synchronous Python export"
        )

    def to_html(self, output: Optional[Union[str, os.PathLike]] = None) -> str:
        """
        Build a zero-network standalone HTML viewer with three view modes.

        :param output: Optional path to receive the generated HTML.
        :type output: str or os.PathLike, optional
        :return: Complete self-contained HTML text.
        :rtype: str
        :raises pyfcstm.diagram.engine.DiagramAssetError: If a bundled viewer, font or
            resvg asset is missing or unreadable.
        :raises OSError: If ``output`` is given and cannot be written, for
            example a missing parent directory or a read-only destination.
        """
        # Checked before anything is built, not after. Options and view state
        # are fixed when the snapshot is built, so every call produces the same
        # document; deciding that at the end still paid for reading the viewer
        # assets, serialising the state, deriving the nonce and hashing three
        # multi-megabyte scripts, which left a repeat call only about a tenth
        # cheaper than the first.
        if self._html_document is not None:
            if output is not None:
                _atomic_write_text(output, self._html_document)
            return self._html_document
        source = self._source
        source_map = self._source_map
        line_to_id = self._source_line_map
        source_documents = self._source_documents
        viewer = _asset_text("viewer.js")
        viewer_css = _asset_text("viewer.css")
        browser_diagram = _thaw_value(self._renderer_diagram)
        browser_diagram["filePath"] = ""
        _strip_browser_private_fields(browser_diagram["rootState"])
        summary = self._renderer_diagram["summary"]
        title = self._renderer_diagram["machineName"]
        state = {
            "title": title,
            "filePath": "",
            "previewOptions": self.options.to_dict(),
            "collapsedStateIds": list(self.view_state.collapsed_state_ids),
            "emptyTitle": "FCSTM Diagram",
            "emptyMessage": "No diagram available.",
            "summary": [
                {"label": "states", "value": summary["states"]},
                {"label": "transitions", "value": summary["transitions"]},
            ],
            "variables": [],
            "sharedEvents": [],
            "standalone": True,
            "standaloneMode": self.view_state.mode,
            "standaloneViewState": {
                "zoom": self.view_state.zoom,
                "panX": self.view_state.pan_x,
                "panY": self.view_state.pan_y,
            },
            "standaloneDiagram": browser_diagram,
            "sourceHtml": _highlight_source(source),
            # Source linking needs text *and* ranges. A programmatic model with
            # an explicit source_text has the text but no spans to click, so
            # reporting it as available showed a pane where nothing responds and
            # left the reason blank.
            "sourceAvailable": bool(source) and bool(source_map),
            "sourceUnavailableReason": _source_unavailable_reason(source, source_map),
            "sourceMap": source_map,
            "sourceLineMap": line_to_id,
            "sourceDocuments": {
                document_id: {"html": _highlight_source(document), "label": document_id}
                for document_id, document in source_documents.items()
            },
            "sourceDocumentId": self._source_document_id,
        }
        if self.options.palette is not None:
            state["palette"] = self.options.palette
        if self.options.mode is not None:
            state["colorMode"] = self.options.mode
        state_json = json.dumps(
            state, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        # Prevent embedded source text or labels from closing the bootstrap
        # script element while preserving the original characters after JSON
        # parsing in the browser.
        state_json = (
            state_json.replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )
        resvg_script = _embedded_resvg_script(self.options.cjk_locale)
        # The bundled component library renders its styles at runtime, so the
        # document needs a style nonce in addition to the hash of the embedded
        # stylesheet. The nonce is derived from the document's own content
        # rather than drawn at random, which is what keeps ``to_html``
        # byte-deterministic; it is derived before the bootstrap is built so
        # nothing depends on its own hash. The nonce is public by construction,
        # not a secret — see the note in the standalone entry point for the
        # policy trade-off that follows from that.
        style_nonce = base64.b64encode(
            hashlib.sha256(
                "\0".join(("style-nonce", state_json, resvg_script, viewer)).encode(
                    "utf-8"
                )
            ).digest()[:16]
        ).decode("ascii")
        bootstrap = (
            'window.__FCSTM_STYLE_NONCE__ = "%s";\nwindow.__FCSTM_INITIAL_STATE__ = %s;'
            % (
                style_nonce,
                state_json,
            )
        )
        scripts = [bootstrap, resvg_script, viewer]
        hashes = [
            "'sha256-%s'"
            % base64.b64encode(hashlib.sha256(item.encode("utf-8")).digest()).decode(
                "ascii"
            )
            for item in scripts
        ]
        css = (
            "html,body,#app{height:100%;margin:0}\n"
            + _embedded_font_css(self.options.cjk_locale)
            + "\n"
            + viewer_css
            + "\n"
            + _highlight_css()
        )
        style_sources = "'sha256-%s' 'nonce-%s'" % (
            base64.b64encode(hashlib.sha256(css.encode("utf-8")).digest()).decode(
                "ascii"
            ),
            style_nonce,
        )
        document = (
            "<!doctype html><html lang=\"%s\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; base-uri 'none'; object-src 'none'; form-action 'none'; frame-src 'none'; media-src 'none'; manifest-src 'none'; img-src data: blob:; style-src %s; style-src-attr 'none'; font-src data:; script-src %s 'wasm-unsafe-eval'; script-src-attr 'none'; connect-src 'none'; worker-src 'none'\"><style>%s</style></head><body><div id=\"app\"></div><script>%s</script><script>%s</script><script>%s</script></body></html>"
            % (
                # The viewer's own interface is English regardless of which
                # CJK font pair the diagram text needs, and the declared
                # document language drives assistive-technology voice and
                # translation prompts. Deriving it from ``cjk_locale`` made
                # a screen reader announce English controls in Mandarin.
                "en",
                style_sources,
                " ".join(hashes),
                css,
                bootstrap,
                resvg_script,
                viewer,
            )
        )
        object.__setattr__(self, "_html_document", document)
        if output is not None:
            _atomic_write_text(output, document)
        return document

    def save(
        self,
        path: Union[str, os.PathLike],
        format: Optional[str] = None,
        *,
        scale: float = 1.0,
    ) -> Path:
        """
        Save JSON/HTML directly and route SVG/PNG/PDF to their typed
        headless capability methods.

        :param path: Destination file path.
        :type path: str or os.PathLike
        :param format: Explicit ``json`` or ``html`` format; when omitted,
            the suffix is used.
        :type format: str, optional
        :param scale: PNG scale forwarded to the headless exporter.
        :type scale: float
        :return: The destination path.
        :rtype: pathlib.Path
        :raises ValueError: If the selected format is unsupported or a
            non-default scale is supplied for a non-PNG format.
        :raises DiagramUnavailableError: If the suffix selects SVG, PNG or
            PDF.  Those are produced by the embedded viewer's own export, which
            needs a browser; save the HTML and export from there.
        :raises FileNotFoundError: If the parent directory does not exist.
        :raises IsADirectoryError: If ``path`` is an existing directory.
        :raises NotADirectoryError: If the parent path is not a directory.
        :raises PermissionError: If the target is an existing file that must not
            be replaced -- unwritable and owned by another user on POSIX, marked
            read-only on Windows -- or its directory will not accept a new file.
        :raises OSError: If the write itself fails, for example on a full or
            read-only filesystem.
        """
        target = Path(path)
        selected = (format or target.suffix.lstrip(".") or "json").lower()
        numeric_scale = _coerce_finite_number(scale, "scale", positive=True)
        if selected != "png" and numeric_scale != 1.0:
            raise ValueError("scale is only supported for PNG output")
        if selected == "json":
            _atomic_write_text(target, self.to_json() + "\n")
        elif selected in ("html", "htm"):
            self.to_html(target)
        elif selected == "svg":
            _atomic_write_text(target, self.to_svg())
        elif selected == "png":
            _atomic_write_bytes(target, self.to_png(scale=numeric_scale))
        elif selected == "pdf":
            _atomic_write_bytes(target, self.to_pdf())
        else:
            raise ValueError("unsupported diagram format: %s" % selected)
        return target

    def show(
        self,
        output: Optional[Union[str, os.PathLike]] = None,
        *,
        open_window: bool = True,
        window_size: Tuple[int, int] = (1200, 900),
    ) -> Path:
        """
        Write an HTML viewer and optionally open it in a standalone app window.

        With ``open_window`` this blocks until the window is closed, the way
        :func:`matplotlib.pyplot.show` does, and then removes the document it
        wrote — so the returned path no longer exists unless you passed
        ``output``.  Waiting is what makes that removal safe: a detached browser
        reads the file after this process is gone, so the document would have to
        be left behind, and each one is roughly 29 MB.

        :param output: Optional destination path. When omitted the viewer is
            written 0600 inside a directory of your own that no other local user
            may look into -- neither the name of a viewer nor its size says which
            diagram it holds, and both would to anyone who could list them. On
            Windows that rests on ``%TEMP%`` being per account, which is the
            default: a ``TEMP`` shared between users cannot be detected here, and
            before CPython 3.12.4 the directory's mode is not applied there either.
            With a
            window that path is this call's, and this call removes it when the
            window closes. Without one nothing here removes it, and asking again
            for the same diagram returns the same file rather than another ~29 MB.
            That reuse follows the directory rather than the process: another
            process of yours resolving the same one is handed the same path, and a
            forked child inherits it -- so a peer removing what it was handed
            removes yours with it. Where the predictable name cannot be trusted
            each resolution makes its own directory and says so, which two
            independent processes do separately and a forked child does not. Pass a
            path of your own for a document you want to name, that only you may
            remove, or that must not be somewhere shared.
        :type output: str or os.PathLike, optional
        :param open_window: Whether to launch a Chromium-family app window,
            defaults to ``True``.
        :type open_window: bool
        :param window_size: Initial app-window width and height in pixels,
            defaults to ``(1200, 900)``.
        :type window_size: tuple[int, int]
        :return: The generated HTML path.
        :rtype: pathlib.Path
        :raises ValueError: If ``window_size`` is not two positive integers.
        :raises pyfcstm.diagram.engine.DiagramAssetError: If a bundled viewer, font or
            resvg asset is missing or unreadable.
        :raises OSError: If the document cannot be written, for example a
            missing parent directory or a read-only destination.
        :raises pyfcstm.diagram.engine.DiagramUnavailableError: If ``open_window`` is
            set and no Chromium-family browser can be launched, or one is launched
            and exits without showing a window -- an SSH session or a container
            with no display, where the browser is found and then reports that it
            has nowhere to draw. The document is written before the launch is
            attempted, so an explicit ``output`` still holds a usable viewer
            afterwards; a temporary one is removed either way.

        Example::

            >>> import tempfile
            >>> from pathlib import Path
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> view = load_state_machine_from_text('state Root;').diagram()
            >>> with tempfile.TemporaryDirectory() as folder:
            ...     # open_window=False writes the viewer without needing a
            ...     # browser, which is also what a headless caller wants.
            ...     written = view.show(Path(folder) / 'viewer.html',
            ...                         open_window=False)
            ...     written.is_file()
            True
            >>> view.show(window_size=(0, 900))
            Traceback (most recent call last):
            ...
            ValueError: window_size must contain exactly two positive integers
        """
        dimensions = _coerce_window_size(window_size)
        if output is None:
            document = self.to_html()
            # A window's copy is this call's to remove; one the caller keeps is
            # reused for the rest of the process. Neither name says what it holds.
            path = (
                _temporary_viewer_path() if open_window else _kept_viewer_path(document)
            )
            # 0600, and forced rather than preserved. The temporary directory is
            # readable and listable by every local user and the document carries
            # the model's own source, so the mode is the only thing keeping it
            # private. Forced, because a permissive file already at the path would
            # otherwise lend its mode to our content.
            _atomic_write_text(path, document, mode=0o600)
            ours = True
        else:
            path = self.save(output, format="html")
            ours = False
        if not open_window:
            # The caller asked for a file and a path to it, so it stays.
            return path
        try:
            # Blocks until the window closes.
            _open_standalone_window(path, dimensions)
        finally:
            if ours:
                # However this ends -- the window closed, a Ctrl-C closed it, or
                # there was no browser to open one -- nothing is reading a
                # document we wrote, so it goes. Being able to say that is the
                # whole reason for waiting rather than detaching. Only a path the
                # caller named survives, which is what `-o` is for.
                _discard(path)
                _discard_empty_fallback(path.parent)
        return path
