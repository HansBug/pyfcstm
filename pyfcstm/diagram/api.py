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
import hashlib
import html as html_module
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from collections.abc import Iterable
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

from pygments import lex
from pygments.formatters import HtmlFormatter

from ..highlight import FcstmLexer
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


def _open_standalone_window(path: Path, window_size: Tuple[int, int]) -> None:
    """Launch the self-contained viewer in a browser app window."""
    executable = _browser_app_executable()
    if executable is None:
        raise DiagramUnavailableError(
            "a Chromium-family browser is required for the standalone diagram window; "
            "install Chrome, Chromium, Edge, or Brave, or set PYFCSTM_BROWSER"
        )
    width, height = window_size
    command = [
        executable,
        "--app=%s" % path.resolve().as_uri(),
        "--new-window",
        "--window-size=%d,%d" % (width, height),
    ]
    popen_kwargs: Dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        popen_kwargs["start_new_session"] = True
    try:
        subprocess.Popen(command, **popen_kwargs)
    except OSError as err:
        raise DiagramUnavailableError(
            "failed to launch the standalone diagram window with %s: %s"
            % (executable, err)
        ) from err


def _temporary_viewer_path(document: str, for_window: bool) -> Path:
    """
    Return a temporary path for a rendered viewer document.

    The two callers want opposite lifetimes, and a shared name cannot serve
    both: a document handed to a window must outlive this process, because the
    browser is launched detached and reads the file after we are gone, while a
    document nobody opened is this process's litter. Giving them one
    content-derived name meant an unrelated process rendering the same model
    could delete a live window's document at its own exit, so the names differ.

    A window's name is derived from the document alone, so showing the same
    diagram twice — in this process or any other — reuses one file instead of
    leaving another ~30 MB behind. A no-window name also carries the process
    id, which makes it unambiguously ours to remove.

    :param document: The rendered HTML document.
    :type document: str
    :param for_window: Whether the caller is about to open a browser window.
    :type for_window: bool
    :return: A path under the system temporary directory.
    :rtype: pathlib.Path
    """
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()[:16]
    suffix = "" if for_window else "-%d" % os.getpid()
    return Path(tempfile.gettempdir()) / (
        "pyfcstm-diagram-%s%s.html" % (digest, suffix)
    )


# Process-scoped temporary viewers, removed when this interpreter exits. Names
# carry our process id, so nothing here can belong to another process and no
# coordination is needed to decide who may delete what.
_TEMPORARY_VIEWERS: Set[Path] = set()


def _register_temporary_viewer(path: Path) -> None:
    """
    Arrange for a process-scoped temporary viewer to be removed at exit.

    :param path: Temporary viewer path carrying this process id.
    :type path: pathlib.Path
    :return: ``None``.
    :rtype: None
    """
    if path in _TEMPORARY_VIEWERS:
        return
    _TEMPORARY_VIEWERS.add(path)
    atexit.register(_remove_temporary_viewer, path)


def _remove_temporary_viewer(path: Path) -> None:
    """
    Delete a process-scoped temporary viewer.

    :param path: Temporary viewer path.
    :type path: pathlib.Path
    :return: ``None``.
    :rtype: None
    """
    if path not in _TEMPORARY_VIEWERS:
        return
    try:
        path.unlink()
    except OSError as error:
        # FileNotFoundError: the user or the OS already removed it.
        # PermissionError: a browser still holds it open on Windows.
        # IsADirectoryError: the predictable path was replaced by a directory.
        # None is worth a traceback out of an atexit hook, and anything else is
        # a bug worth seeing.
        if not isinstance(
            error, (FileNotFoundError, PermissionError, IsADirectoryError)
        ):
            raise


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


def _apply_target_mode(
    temporary_path: Path, target: Path, mode: Optional[int] = None
) -> None:
    """
    Give the temporary file the mode the target should end up with.

    ``NamedTemporaryFile`` creates at 0600 and ``os.replace`` carries that mode
    onto the target, so without this a generated file lands unreadable to
    everyone else and re-saving silently downgrades an existing world-readable
    file. An existing target keeps its own mode; a new one follows the umask.

    :param temporary_path: The sibling file about to replace the target.
    :type temporary_path: pathlib.Path
    :param target: Final destination path.
    :type target: pathlib.Path
    :param mode: Force this mode instead of preserving or deriving one. Used
        for paths whose name is predictable, where an existing file may have
        been placed there by someone else.
    :type mode: int, optional
    :return: ``None``.
    :rtype: None
    """
    if mode is not None:
        os.chmod(str(temporary_path), mode)
        return
    try:
        os.chmod(str(temporary_path), target.stat().st_mode & 0o7777)
        return
    except FileNotFoundError:
        # The usual case: the target does not exist yet, so there is no mode to
        # preserve. Other stat failures surface from _validate_write_target,
        # which runs first and re-raises them from its own is_dir() call.
        pass
    os.chmod(str(temporary_path), _umask_default_mode(temporary_path.parent))


def _umask_default_mode(directory: Path) -> int:
    """
    Return the mode a plain new file receives in ``directory``.

    Read by letting the operating system apply the umask to a throwaway file
    rather than by calling ``os.umask(0)`` to sample it. The umask is
    process-wide, not per-thread, so clearing it even briefly means a file
    another thread creates in that window is born with whatever permissions its
    own mode argument asked for — measured as 0666 where 0644 was expected.
    A public write path must not widen the whole process to learn its own
    default.

    :param directory: Directory the real write is about to happen in, so the
        probe sees the same filesystem and any inherited default ACL.
    :type directory: pathlib.Path
    :return: Permission bits, already masked.
    :rtype: int
    """
    handle, probe = tempfile.mkstemp(prefix=".pyfcstm-umask-", dir=str(directory))
    os.close(handle)
    try:
        # mkstemp forces 0600, so ask for 0666 explicitly and let the kernel
        # subtract the umask exactly as it would for the real file.
        os.chmod(probe, 0o666)
        widened = os.open(probe + ".probe", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
        os.close(widened)
        try:
            return os.stat(probe + ".probe").st_mode & 0o7777
        finally:
            os.unlink(probe + ".probe")
    finally:
        os.unlink(probe)


def _atomic_write_text(
    path: Union[str, os.PathLike], content: str, mode: Optional[int] = None
) -> Path:
    """Replace a text file atomically using a temporary sibling."""
    target = Path(path)
    _validate_write_target(target)
    temporary = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=".%s." % target.name,
        dir=str(target.parent),
        delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        _apply_target_mode(temporary_path, target, mode)
        os.replace(str(temporary_path), str(target))
    except OSError as write_error:
        try:
            temporary_path.unlink()
        except OSError as cleanup_error:
            # OSError: unlink can fail after a write/replace error on a
            # read-only or concurrently cleaned directory; keep both causes
            # observable instead of silently discarding the cleanup failure.
            raise OSError(
                "%s; temporary cleanup failed for %s: %s"
                % (write_error, temporary_path, cleanup_error)
            ) from write_error
        raise
    return target


def _atomic_write_bytes(
    path: Union[str, os.PathLike], content: bytes, mode: Optional[int] = None
) -> Path:
    """Replace a binary file atomically using a temporary sibling."""
    target = Path(path)
    _validate_write_target(target)
    temporary = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=".%s." % target.name,
        dir=str(target.parent),
        delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        _apply_target_mode(temporary_path, target, mode)
        os.replace(str(temporary_path), str(target))
    except OSError as write_error:
        try:
            temporary_path.unlink()
        except OSError as cleanup_error:
            # OSError: unlink can fail after a write/replace error on a
            # read-only or concurrently cleaned directory; keep both causes
            # observable instead of silently discarding the cleanup failure.
            raise OSError(
                "%s; temporary cleanup failed for %s: %s"
                % (write_error, temporary_path, cleanup_error)
            ) from write_error
        raise
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
        ``full``.
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
    Facade for portable data and a self-contained browser view.

    The synchronous headless methods are present as typed capability probes;
    the optional runtime that implements them belongs to the delivery stage.
    Browser SVG/PNG/PDF export remains available from the embedded viewer.
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
        :type model: pyfcstm.model.StateMachine
        :param options: Optional immutable renderer options or a compatible
            mapping.
        :type options: pyfcstm.diagram.DiagramOptions or collections.abc.Mapping, optional
        :param view_state: Optional immutable browser state or compatible
            mapping.
        :type view_state: pyfcstm.diagram.DiagramViewState or collections.abc.Mapping, optional
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
        :type current: pyfcstm.diagram.DiagramOptions
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
        :type current: pyfcstm.diagram.DiagramViewState
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
        :type options: pyfcstm.diagram.DiagramOptions or collections.abc.Mapping, optional
        :param kwargs: Snake-case or camel-case option fields to change. Fields
            that are not named keep their current value.
        :return: A new independent diagram snapshot.
        :rtype: pyfcstm.diagram.Diagram
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
        :type view_state: pyfcstm.diagram.DiagramViewState or collections.abc.Mapping, optional
        :param kwargs: Snake-case or camel-case view-state fields to change.
            Fields that are not named keep their current value.
        :return: A new independent diagram snapshot.
        :rtype: pyfcstm.diagram.Diagram
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

        :return: This method does not return while the optional headless
            runtime is unavailable.
        :rtype: str
        :raises DiagramUnavailableError: Always in the browser-only stage.
        """
        raise DiagramUnavailableError(
            "headless SVG export is unavailable; use Diagram.to_html() browser export "
            "or wait for the headless delivery stage; `pip install pyfcstm[viz]` "
            "adds the rendering runtime but not this synchronous API"
        )

    def to_png(self, scale: float = 1.0) -> bytes:
        """
        Request a synchronous headless PNG export.

        :param scale: Positive finite output scale reserved for the headless
            runtime.
        :type scale: float
        :return: This method does not return while the optional headless
            runtime is unavailable.
        :rtype: bytes
        :raises ValueError: If ``scale`` is not finite and positive.
        :raises DiagramUnavailableError: Always in the browser-only stage.
        """
        _coerce_finite_number(scale, "scale", positive=True)
        raise DiagramUnavailableError(
            "headless PNG export is unavailable; use Diagram.to_html() browser export "
            "or wait for the headless delivery stage; `pip install pyfcstm[viz]` "
            "adds the rendering runtime but not this synchronous API"
        )

    def to_pdf(self) -> bytes:
        """
        Request a synchronous headless vector PDF export.

        :return: This method does not return while the optional headless
            runtime is unavailable.
        :rtype: bytes
        :raises DiagramUnavailableError: Always in the browser-only stage.
        """
        raise DiagramUnavailableError(
            "headless PDF export is unavailable; use Diagram.to_html() browser export "
            "or wait for the headless delivery stage; `pip install pyfcstm[viz]` "
            "adds the rendering runtime but not this synchronous API"
        )

    def to_html(self, output: Optional[Union[str, os.PathLike]] = None) -> str:
        """
        Build a zero-network standalone HTML viewer with three view modes.

        :param output: Optional path to receive the generated HTML.
        :type output: str or os.PathLike, optional
        :return: Complete self-contained HTML text.
        :rtype: str
        :raises pyfcstm.diagram.DiagramAssetError: If a bundled viewer, font or
            resvg asset is missing or unreadable.
        :raises OSError: If ``output`` is given and cannot be written, for
            example a missing parent directory or a read-only destination.
        """
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
        # A single slot, not a content-addressed map: options and view state are
        # fixed when the snapshot is built, so every call produces the same
        # document and the old key was a hash of the very bytes it guarded —
        # which also meant joining a second ~30 MB copy just to compute it.
        document = self._html_document
        if document is None:
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
        :param scale: PNG scale forwarded to the optional headless exporter.
        :type scale: float
        :return: The destination path.
        :rtype: pathlib.Path
        :raises ValueError: If the selected format is unsupported or a
            non-default scale is supplied for a non-PNG format.
        :raises DiagramUnavailableError: If a headless SVG, PNG, or PDF
            runtime is not installed in this browser-only stage.
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

        :param output: Optional destination path. When omitted the viewer is
            written 0600 to a temporary path, and which path depends on
            ``open_window``. With a window, the name is derived from the
            document alone: the file is left in place, because the browser is
            detached and reads it after this process is gone, and showing the
            same diagram again — here or in another process — reuses that one
            file. Without a window the name also carries this process id and
            the file is removed at interpreter exit. Each viewer is roughly
            30 MB, so pass an explicit path when you want to manage the file
            yourself.
        :type output: str or os.PathLike, optional
        :param open_window: Whether to launch a Chromium-family app window,
            defaults to ``True``.
        :type open_window: bool
        :param window_size: Initial app-window width and height in pixels,
            defaults to ``(1200, 900)``.
        :type window_size: tuple[int, int]
        :return: The generated HTML path.
        :rtype: pathlib.Path
        """
        dimensions = _coerce_window_size(window_size)
        if output is None:
            document = self.to_html()
            path = _temporary_viewer_path(document, for_window=open_window)
            # Recorded before the write: if the launch below fails, whether this
            # file is ours to remove depends on whether we are the process that
            # created it.
            preexisting = path.exists()
            # 0600, and forced rather than preserved. The name is derived from
            # the document, so on a shared temp directory anyone can predict
            # it: both to read the model's own source out of the viewer, and to
            # pre-create the path with a permissive mode that a mode-preserving
            # write would then copy onto our content.
            _atomic_write_text(path, document, mode=0o600)
            if not open_window:
                _register_temporary_viewer(path)
            temporary = None if preexisting else path
        else:
            path = self.save(output, format="html")
            temporary = None
        if open_window:
            try:
                _open_standalone_window(path, dimensions)
            except DiagramUnavailableError:
                # No window opened this document, so the reason it is kept does
                # not apply. It is only ours to remove if we created it: an
                # earlier run in another process may have a window on the very
                # same path, since the name is shared by design.
                if temporary is not None:
                    _register_temporary_viewer(temporary)
                raise
        return path
