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

import base64
import hashlib
import html as html_module
import json
import math
import os
import pkgutil
import tempfile
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from pygments import lex
from pygments.formatters import HtmlFormatter

from ..highlight import FcstmLexer
from ..model.model import Event, IfBlock, Operation, OperationStatement, State, StateMachine, Transition
from ..utils.validate import Span
from .engine import DiagramAssetError

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
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


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
    end_column = start_column if span.end_column is None else max(0, int(span.end_column) - 1)
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
        return "%s ref %s" % (prefix, ".".join(getattr(action, "ref_state_path", ()) or ()))
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


def _transition_signature(owner: State, transition: Transition, discriminator: Optional[int] = None) -> str:
    """Build a stable semantic ID independent of source coordinates."""
    source = "INIT_STATE" if transition.from_state is not None and getattr(transition.from_state, "name", None) == "INIT_STATE" else _text(transition.from_state)
    target = "EXIT_STATE" if transition.to_state is not None and getattr(transition.to_state, "name", None) == "EXIT_STATE" else _text(transition.to_state)
    event = transition.event.path_name if transition.event else ""
    guard = _text(transition.guard)
    effects = "\n".join(_effect_lines(transition))
    payload_parts = [".".join(owner.path), source, target, event, guard, effects]
    if discriminator is not None:
        payload_parts.append(str(discriminator))
    payload = "|".join(payload_parts)
    return "transition:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


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
    duplicate_counts: Dict[str, int] = {}
    for transition in state.transitions:
        source_init = _is_marker(transition.from_state, "INIT_STATE")
        target_exit = _is_marker(transition.to_state, "EXIT_STATE")
        source_label = "[*]" if source_init else _text(transition.from_state)
        target_label = "[*]" if target_exit else _text(transition.to_state)
        trigger = _event_reference(transition) if transition.event else ""
        guard = _text(transition.guard) if transition.guard is not None else None
        effects = _effect_lines(transition)
        base_id = _transition_signature(state, transition)
        duplicate_index = duplicate_counts.get(base_id, 0)
        duplicate_counts[base_id] = duplicate_index + 1
        transition_id = base_id if duplicate_index == 0 else _transition_signature(state, transition, duplicate_index)
        transition_dict: Dict[str, Any] = {
            "id": transition_id,
            "sourceLabel": source_label,
            "targetLabel": target_label,
            "triggerLabel": trigger or None,
            "guardLabel": guard,
            "effectLines": effects,
            "eventName": transition.event.name if transition.event else None,
            "eventDisplayName": transition.event.extra_name if transition.event else None,
            "eventRelativePath": trigger or None,
            "eventAbsolutePath": ("/" + ".".join(transition.event.path[1:])) if transition.event else None,
            "triggerScope": transition.event_scope,
            "label": "%s -> %s%s%s%s" % (
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
            "eventQualifiedName": transition.event.path_name if transition.event else None,
            "eventColor": None,
        }
        if include_ranges:
            transition_dict["range"] = _span_range(transition._span)
            transition_dict["_sourcePath"] = getattr(transition, "_source_path", None)
        transitions.append(transition_dict)

    actions = []
    for action in [*state.on_enters, *state.on_durings, *state.on_exits, *state.on_during_aspects]:
        item = {
            "name": action.name,
            "qualifiedName": ".".join(str(x) for x in action.state_path if x is not None),
            "stage": action.stage,
            "aspect": action.aspect,
            "mode": "ref" if action.is_ref else ("abstract" if action.is_abstract else "operations"),
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
        "id": ".".join(state.path),
        "name": state.name,
        "qualifiedName": ".".join(state.path),
        "displayName": state.extra_name,
        "pseudo": bool(state.is_pseudo),
        "comboRelay": bool(state.is_combo_relay),
        "leaf": bool(state.is_leaf_state),
        "root": bool(state.is_root_state),
        "events": [_event_dict(event, include_ranges) for event in state.events.values()],
        "actions": actions,
        "transitions": transitions,
        "children": [_state_dict(child, include_ranges) for child in state.substates.values()],
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
        for action in [*state.on_enters, *state.on_durings, *state.on_exits, *state.on_during_aspects]
    ]
    return len(states), len(events), len(transitions), len(actions)


def _build_diagram_dict(machine: StateMachine, include_ranges: bool) -> Dict[str, Any]:
    state_count, event_count, transition_count, action_count = _collect_counts(machine)
    transitions = [transition for state in machine.walk_states() for transition in state.transitions]
    event_counts: Dict[str, int] = {}
    for transition in transitions:
        if transition.event:
            event_counts[transition.event.path_name] = event_counts.get(transition.event.path_name, 0) + 1
    palette = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1"]
    event_colors = {
        path: palette[index % len(palette)]
        for index, path in enumerate(sorted(path for path, count in event_counts.items() if count > 1))
    }

    def apply_colors(state_dict: Dict[str, Any]) -> None:
        for transition in state_dict["transitions"]:
            transition["eventColor"] = event_colors.get(transition.get("eventQualifiedName"))
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
            base = main_absolute if os.path.isdir(main_absolute) else os.path.dirname(main_absolute)
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


def _source_sidecar(machine: StateMachine, source_override: Optional[str] = None) -> Tuple[str, Dict[str, Any], Dict[str, Union[str, List[str]]], Dict[str, str]]:
    source = machine.source_text if source_override is None else source_override
    source = source or ""
    source_paths = machine._source_documents or {}
    explicit_override = source_override is not None and source_override != machine.source_text
    if explicit_override or not source_paths:
        main_source_path = machine.source_path or "<memory>"
        source_paths = {main_source_path: source}
    elif machine.source_path and machine.source_path not in source_paths:
        source_paths[machine.source_path] = source
    documents = {
        _source_document_id(machine, path): text for path, text in source_paths.items()
    }
    main_document_id = _source_document_id(machine, machine.source_path or "<memory>")
    diagram = _build_diagram_dict(machine, include_ranges=True)
    mapping: Dict[str, Any] = {}
    line_to_id: Dict[str, Union[str, List[str]]] = {}

    def visit(state: Dict[str, Any]) -> None:
        state_id = state["id"]
        if state.get("range"):
            source_path = state.get("_sourcePath") or machine.source_path
            mapping[state_id] = {"kind": "state", "documentId": _source_document_id(machine, source_path), "range": state["range"]}
        for transition in state["transitions"]:
            if transition.get("range"):
                source_path = transition.get("_sourcePath") or machine.source_path
                mapping[transition["id"]] = {"kind": "transition", "documentId": _source_document_id(machine, source_path), "range": transition["range"]}
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
        length += max(0, int(span["end"]["character"]) - int(span["start"]["character"]))
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
                token_lines[-1].append('<span class="%s">%s</span>' % (css_class, escaped))
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
        '<span class="fcstm-source-line" data-line="%d">%s</span>'
        % (index, "".join(content) or " ")
        for index, content in enumerate(token_lines)
    ]
    return "\n".join(rendered)


def _highlight_css() -> str:
    """Return the small Pygments CSS fragment used by the source pane."""
    return HtmlFormatter().get_style_defs(".fcstm-source-panel__code")


def _embedded_font_css(locale: str) -> str:
    """Return data-URI font faces for the selected locale only."""
    payload = _embedded_font_payload(locale)
    rules = []
    for item in payload:
        family, weight, encoded, mime = item
        rules.append("@font-face{font-family:%s;font-style:normal;font-weight:%d;src:url(data:%s;base64,%s) format('opentype');font-display:block}" % (json.dumps(family), weight, mime, encoded))
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
        data = pkgutil.get_data("pyfcstm.diagram.assets", path)
        if data is None:
            raise DiagramAssetError("missing browser font asset %s; run `make build_assets`" % path)
        encoded = base64.b64encode(data).decode("ascii")
        payload.append((family, weight, encoded, mime))
    return payload


def _asset_text(name: str) -> str:
    data = pkgutil.get_data("pyfcstm.diagram.assets", name)
    if data is None:
        raise DiagramAssetError("missing browser viewer asset %s; run `make build_assets`" % name)
    return data.decode("utf-8")


def _embedded_resvg_script(locale: str) -> str:
    """Build the offline browser helper that expands SVG through resvg WASM."""
    wasm = pkgutil.get_data("pyfcstm.diagram.assets", "resvg.wasm")
    if wasm is None:
        raise DiagramAssetError("missing browser resvg WASM asset; run `make build_assets`")
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
        if self.palette is not None and self.palette not in ("default", "nord", "solarized", "darcula"):
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

        :return: A new JSON-compatible option mapping.
        :rtype: dict
        """
        return {
            "detailLevel": self.detail_level,
            "direction": self.direction,
            "cjkLocale": self.cjk_locale,
            "showVariableDefinitions": True,
            "showEvents": True,
            "showTransitionGuards": True,
            "showTransitionEffects": True,
            "transitionEffectMode": "note",
            "eventVisualizationMode": "both",
            "showStateEvents": True,
            "showStateActions": False,
            "eventNameFormat": ["extra_name", "relpath"],
            "maxStateEvents": 4,
            "maxStateActions": 4,
            "maxTransitionEffectLines": 8,
            "maxLabelLength": 160,
        }


@dataclass(frozen=True)
class DiagramViewState:
    """
    Immutable browser state for collapse, zoom, pan and display mode.

    :param mode: ``fcstm`` for source-only, ``diagram`` for diagram-only, or
        ``compare`` for the linked split view.
    :type mode: str
    :param collapsed_state_ids: Qualified state IDs hidden in the diagram.
    :type collapsed_state_ids: tuple[str, ...]
    :param zoom: Positive initial zoom factor.
    :type zoom: float
    :param pan_x: Initial horizontal pan offset in CSS pixels.
    :type pan_x: float
    :param pan_y: Initial vertical pan offset in CSS pixels.
    :type pan_y: float

    Example::

        >>> DiagramViewState(mode="fcstm").to_dict()["mode"]
        'fcstm'
    """

    mode: str = "compare"
    collapsed_state_ids: Tuple[str, ...] = ()
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def __post_init__(self) -> None:
        if self.mode not in ("fcstm", "diagram", "compare"):
            raise ValueError("mode must be 'fcstm', 'diagram', or 'compare'")
        object.__setattr__(self, "collapsed_state_ids", tuple(self.collapsed_state_ids))
        if not math.isfinite(float(self.zoom)) or float(self.zoom) <= 0:
            raise ValueError("zoom must be a finite positive number")
        if not math.isfinite(float(self.pan_x)) or not math.isfinite(float(self.pan_y)):
            raise ValueError("pan offsets must be finite numbers")

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


@dataclass(frozen=True)
class DiagramData:
    """
    Portable, deterministic diagram data without editor-only metadata.

    :param value: Internal renderer data.  ``to_dict`` removes source ranges,
        local paths and other editor-only fields before exposing it.
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
        object.__setattr__(self, "value", _freeze_value(dict(self.value)))

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a deep JSON-compatible copy of the portable contract.

        :return: An independent mapping; mutating it does not change this
            snapshot.
        :rtype: dict
        """
        value = json.loads(json.dumps(_thaw_value(self.value), ensure_ascii=False, sort_keys=True))

        def strip(node: Dict[str, Any]) -> None:
            node.pop("range", None)
            node.pop("_sourcePath", None)
            for event in node.get("events", []):
                event.pop("range", None)
                event.pop("_sourcePath", None)
            for action in node.get("actions", []):
                action.pop("range", None)
                action.pop("_sourcePath", None)
            for transition in node.get("transitions", []):
                transition.pop("range", None)
                transition.pop("_sourcePath", None)
            for child in node.get("children", []):
                strip(child)

        strip(value["rootState"])
        value.pop("filePath", None)
        return value

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
    """Facade for portable data and a self-contained browser view.

    Synchronous headless SVG/PNG/PDF methods are intentionally owned by the
    later delivery stage.  This stage keeps rendering in the embedded browser
    viewer so a base Python installation remains independent of MiniRacer.
    """

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
        :param source_text: Optional source text override for the FCSTM pane.
        :type source_text: str, optional
        """
        self.model = model
        if isinstance(options, Mapping):
            options = DiagramOptions(
                detail_level=str(options.get("detail_level", options.get("detailLevel", "normal"))),
                direction=str(options.get("direction", "TB")),
                palette=(None if options.get("palette") is None else str(options.get("palette"))),
                mode=(None if options.get("mode") is None else str(options.get("mode"))),
                cjk_locale=str(options.get("cjk_locale", options.get("cjkLocale", "sc"))),
            )
        if isinstance(view_state, Mapping):
            view_state = DiagramViewState(
                mode=str(view_state.get("mode", "compare")),
                collapsed_state_ids=tuple(view_state.get("collapsed_state_ids", view_state.get("collapsedStateIds", ()))),
                zoom=float(view_state.get("zoom", 1.0)),
                pan_x=float(view_state.get("pan_x", view_state.get("panX", 0.0))),
                pan_y=float(view_state.get("pan_y", view_state.get("panY", 0.0))),
            )
        self.options = options or DiagramOptions()
        self.view_state = view_state or DiagramViewState()
        self.source_text = model.source_text if source_text is None else source_text
        self._renderer_diagram = _build_diagram_dict(model, include_ranges=True)
        self.data = DiagramData(self._renderer_diagram)

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

    def to_html(self, output: Optional[Union[str, os.PathLike]] = None) -> str:
        """
        Build a zero-network standalone HTML viewer with three view modes.

        :param output: Optional path to receive the generated HTML.
        :type output: str or os.PathLike, optional
        :return: Complete self-contained HTML text.
        :rtype: str
        :raises DiagramAssetError: If a bundled viewer, font or resvg asset is
            missing or unreadable.
        """
        source, source_map, line_to_id, source_documents = _source_sidecar(self.model, self.source_text)
        viewer = _asset_text("viewer.js")
        viewer_css = _asset_text("viewer.css")
        browser_diagram = json.loads(json.dumps(self._renderer_diagram, ensure_ascii=False))
        browser_diagram["filePath"] = ""
        _strip_browser_private_fields(browser_diagram["rootState"])
        state = {
            "title": self.model.root_state.name,
            "filePath": "",
            "previewOptions": self.options.to_dict(),
            "collapsedStateIds": list(self.view_state.collapsed_state_ids),
            "emptyTitle": "FCSTM Diagram",
            "emptyMessage": "No diagram available.",
            "summary": [
                {"label": "states", "value": len(list(self.model.walk_states()))},
                {"label": "transitions", "value": sum(len(s.transitions) for s in self.model.walk_states())},
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
            "sourceAvailable": bool(source),
            "sourceUnavailableReason": "当前模型没有保留原始 FCSTM 源码；请通过 load_state_machine_from_file/text 加载，或显式传入 source_text。" if not source else "",
            "sourceMap": source_map,
            "sourceLineMap": line_to_id,
            "sourceDocuments": {
                document_id: {"html": _highlight_source(document), "label": document_id}
                for document_id, document in source_documents.items()
            },
            "sourceDocumentId": _source_document_id(self.model, self.model.source_path or "<memory>"),
        }
        if self.options.palette is not None:
            state["palette"] = self.options.palette
        if self.options.mode is not None:
            state["colorMode"] = self.options.mode
        state_json = json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
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
        bootstrap = "window.__FCSTM_INITIAL_STATE__ = %s;" % state_json
        resvg_script = _embedded_resvg_script(self.options.cjk_locale)
        scripts = [bootstrap, resvg_script, viewer]
        hashes = [
            "'sha256-%s'" % base64.b64encode(hashlib.sha256(item.encode("utf-8")).digest()).decode("ascii")
            for item in scripts
        ]
        css = "html,body,#app{height:100%;margin:0}\n" + _embedded_font_css(self.options.cjk_locale) + "\n" + viewer_css + "\n" + _highlight_css()
        style_hash = "'sha256-%s'" % base64.b64encode(hashlib.sha256(css.encode("utf-8")).digest()).decode("ascii")
        document = "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; base-uri 'none'; object-src 'none'; form-action 'none'; frame-src 'none'; media-src 'none'; manifest-src 'none'; img-src data: blob:; style-src %s; style-src-attr 'none'; font-src data:; script-src %s 'wasm-unsafe-eval'; script-src-attr 'none'; connect-src 'none'; worker-src 'none'\"><style>%s</style></head><body><div id=\"app\"></div><script>%s</script><script>%s</script><script>%s</script></body></html>" % (style_hash, " ".join(hashes), css, bootstrap, resvg_script, viewer)
        if output is not None:
            Path(output).write_text(document, encoding="utf-8")
        return document

    def save(self, path: Union[str, os.PathLike], format: Optional[str] = None) -> Path:
        """
        Save JSON or HTML according to ``format`` or the file suffix.

        :param path: Destination file path.
        :type path: str or os.PathLike
        :param format: Explicit ``json`` or ``html`` format; when omitted,
            the suffix is used.
        :type format: str, optional
        :return: The destination path.
        :rtype: pathlib.Path
        :raises ValueError: If the selected format is unsupported.
        """
        target = Path(path)
        selected = (format or target.suffix.lstrip(".") or "json").lower()
        if selected == "json":
            target.write_text(self.to_json() + "\n", encoding="utf-8")
        elif selected in ("html", "htm"):
            self.to_html(target)
        else:
            raise ValueError("unsupported diagram format: %s" % selected)
        return target

    def show(self, output: Optional[Union[str, os.PathLike]] = None, *, open_browser: bool = True) -> Path:
        """
        Write an HTML viewer and optionally open it in the default browser.

        :param output: Optional destination path.  A temporary file is used
            when omitted.
        :type output: str or os.PathLike, optional
        :param open_browser: Whether to launch the default browser.
        :type open_browser: bool
        :return: The generated HTML path.
        :rtype: pathlib.Path
        """
        if output is None:
            handle = tempfile.NamedTemporaryFile(prefix="pyfcstm-diagram-", suffix=".html", delete=False)
            handle.close()
            output = handle.name
        path = self.save(output, format="html")
        if open_browser:
            webbrowser.open(path.resolve().as_uri())
        return path
