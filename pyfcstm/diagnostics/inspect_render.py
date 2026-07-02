"""Presentation renderers for inspect diagnostics.

This module converts :class:`pyfcstm.diagnostics.inspect.ModelInspect`
instances into human-readable or LLM-oriented text without changing the
structured inspect JSON contract. The renderers are intentionally small and
side-effect free so the CLI can offer multiple output formats while
:func:`pyfcstm.diagnostics.inspect_model` and
:meth:`pyfcstm.diagnostics.inspect.ModelInspect.to_json` remain the single
source of truth for machine-readable model data.

The module contains:

.. list-table:: Inspect presentation helpers
   :header-rows: 1

   * - Helper
     - Purpose
   * - :func:`render_inspect_human`
     - Render a checker-style terminal report for humans.
   * - :class:`HumanRenderOptions`
     - Carry human-renderer presentation toggles such as ANSI color.
   * - :func:`render_inspect_llm_json`
     - Render the stable compact JSON packet for LLM repair loops.
   * - :func:`render_inspect_llm_markdown`
     - Render the stable Markdown packet for prompt composition.
   * - :func:`inspect_output_suffix_warning`
     - Detect suspicious ``--output`` suffix and format combinations.

Example::

    >>> from pyfcstm.diagnostics.inspect_render import inspect_output_suffix_warning
    >>> inspect_output_suffix_warning("report.json", "human")
    "output file 'report.json' looks like JSON, but inspect format is 'human'. Use '--format json' if you intended machine-readable JSON output."
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .codes import CODE_REGISTRY
from ..utils.validate import ModelDiagnostic, Span

INSPECT_LLM_SCHEMA_VERSION = "pyfcstm.inspect.llm.v1"
_INSPECT_OUTPUT_FORMATS = ("human", "json", "llm-json", "llm-md")
_SEVERITY_ORDER = ("error", "warning", "info")
_SEVERITY_HUMAN_LABELS = {
    "error": "ERROR",
    "warning": "WARN",
    "info": "INFO",
    "ok": "OK",
}
_STATUS_BY_SEVERITY = {
    "error": "error",
    "warning": "warning",
    "info": "info",
}
_ANSI_STYLE_BY_SEVERITY = {
    "error": "1;31",
    "warning": "33",
    "info": "36",
    "ok": "32",
}
_ANSI_BOLD = "1"
_ANSI_RESET = "\033[0m"
_SOURCE_CONTEXT_RADIUS = 1
_GLOBAL_REPAIR_RULES = (
    "Make the smallest source edit that preserves the modeler's apparent intent.",
    "Use diagnostic source/provenance before choosing a fix; inspect-static warnings are not solver proofs.",
    "Do not mechanically stack all suggested actions when multiple diagnostics refer to the same region.",
    "Do not delete states or transitions unless the report explicitly says the element is unused and the design intent supports deletion.",
    "A repair should clear all error and warning diagnostics; info diagnostics may remain when the model intent supports them.",
    "If changing a guard into an event-only transition makes a variable declaration unused, remove that variable or keep a real guard-affecting data-flow path.",
)
_REPAIR_NOTES_BY_CODE = {
    "W_COMBO_DUPLICATE_EVENT": (
        "Repeated identical event terms are presence-based and are usually redundant.",
        "If there is no evidence that the explicit two-hop pseudo chain is intentional, reducing the duplicated term to one event is the smallest semantic repair.",
    ),
    "W_UNREFERENCED_VAR": (
        "A declaration-only variable may be speculative scaffolding.",
        "Remove it only when no guard, assignment, abstract action, or external integration intent needs it.",
    ),
    "W_GUARD_VARS_NEVER_CHANGE": (
        "This is a static dataflow warning, not a proof that the guard is satisfiable.",
        "Adding a write is useful only when the variable should genuinely evolve at runtime.",
    ),
    "W_UNWRITTEN_READ_VAR": (
        "This is a static dataflow warning about missing writes after initialization.",
        "Do not add a self-assignment or dummy update only to silence the warning.",
    ),
    "W_DEAD_GUARD": (
        "This is verify-backed: SMT proved the guard unsatisfiable under model constraints.",
        "Prefer correcting the contradictory guard over making the transition unconditional.",
        "If the same variable also has static dataflow warnings, the repair must address both the contradiction and the missing guard-affecting data flow.",
    ),
    "W_GUARD_TAUTOLOGY": (
        "This is verify-backed: SMT proved the guard always true under model constraints.",
        "A tautological guard may document intent, so preserve that intent when simplifying.",
    ),
    "W_TOPOLOGICAL_NOEXIT": (
        "This is verify-backed topology feedback, not an instruction to add an unconditional exit blindly.",
    ),
    "I_TOPOLOGICAL_NON_TERMINATING": (
        "Long-running control loops can be intentional; decide intent before adding progress edges.",
    ),
    "W_EFFECT_SELF_ASSIGN": (
        "A self-assignment is a no-op and does not model real progress.",
        "If the variable exists only for that no-op effect, remove the variable and no-op effect instead of inventing a write that still does not affect a guard.",
    ),
    "W_REDUNDANT_TRANSITION": (
        "Remove only the duplicate transition or merge duplicate no-op effects.",
        "Keep the state structure and one intentional transition unless the report proves the element itself is unused.",
    ),
}


@dataclass(frozen=True)
class SourceExcerptLine:
    """One source line included in a diagnostic source window.

    :param line_number: One-based source line number.
    :type line_number: int
    :param text: Source line text without its trailing newline.
    :type text: str
    :param caret: Optional caret marker for the diagnostic anchor line.
    :type caret: Optional[str], optional

    Example::

        >>> SourceExcerptLine(3, "state Idle;", None).text
        'state Idle;'
    """

    line_number: int
    text: str
    caret: Optional[str] = None


@dataclass(frozen=True)
class SourceExcerpt:
    """Source excerpt window anchored by a diagnostic span.

    :param line_number: One-based line number for the diagnostic anchor.
    :type line_number: int
    :param text: Anchor source line text without its trailing newline.
    :type text: str
    :param caret: Caret marker aligned to the diagnostic span on the anchor
        line.
    :type caret: str
    :param context_lines: Source window around the anchor line. The window
        usually contains one line before and after the anchor when available.
    :type context_lines: Tuple[SourceExcerptLine, ...], optional

    Example::

        >>> SourceExcerpt(2, "def int x = 0;", "^^^^").line_number
        2
    """

    line_number: int
    text: str
    caret: str
    context_lines: Tuple[SourceExcerptLine, ...] = ()


@dataclass(frozen=True)
class HumanRenderOptions:
    """Options controlling human inspect presentation details.

    The options intentionally describe terminal presentation only. They do not
    change :meth:`pyfcstm.diagnostics.inspect.ModelInspect.to_json` or any LLM
    renderer, which keeps machine-readable inspect output independent of
    ANSI styling decisions.

    :param color_enabled: Whether ANSI color should be emitted for the human
        renderer. Defaults to ``False`` so programmatic calls are plain ASCII
        unless the CLI explicitly enables color for an interactive terminal.
    :type color_enabled: bool, optional

    Example::

        >>> HumanRenderOptions(color_enabled=True).color_enabled
        True
    """

    color_enabled: bool = False


def inspect_output_suffix_warning(
    output_file: Optional[str], output_format: str
) -> Optional[str]:
    """Return a warning for suspicious output suffix and format pairs.

    The function never changes the requested format. It only reports cases
    where a filename extension strongly suggests that the user may have meant a
    different ``--format`` value.

    :param output_file: Output path supplied to the CLI, or ``None`` for
        stdout.
    :type output_file: Optional[str]
    :param output_format: Requested inspect output format.
    :type output_format: str
    :return: Human-readable warning text, or ``None`` when the suffix is not
        suspicious.
    :rtype: Optional[str]
    :raises ValueError: If ``output_format`` is not a supported format.

    Example::

        >>> inspect_output_suffix_warning("report.json", "human") is not None
        True
        >>> inspect_output_suffix_warning("report.json", "json") is None
        True
    """
    _validate_output_format(output_format)
    if output_file is None:
        return None
    suffixes = tuple(s.lower() for s in os.path.basename(output_file).split(".")[1:])
    if not suffixes:
        return None
    last_suffix = suffixes[-1]
    if output_format == "human" and last_suffix in {"json", "md"}:
        return (
            "output file {path!r} looks like {kind}, but inspect format is 'human'. "
            "Use '--format {suggested}' if you intended {purpose}."
        ).format(
            path=output_file,
            kind="JSON" if last_suffix == "json" else "Markdown",
            suggested="json" if last_suffix == "json" else "llm-md",
            purpose=(
                "machine-readable JSON output"
                if last_suffix == "json"
                else "Markdown output"
            ),
        )
    if output_format in {"json", "llm-json"} and last_suffix == "md":
        return (
            "output file {path!r} looks like Markdown, but inspect format is {fmt!r}. "
            "Use '--format llm-md' if you intended Markdown output."
        ).format(path=output_file, fmt=output_format)
    if output_format == "llm-md" and last_suffix == "json":
        return (
            "output file {path!r} looks like JSON, but inspect format is 'llm-md'. "
            "Use '--format llm-json' or '--format json' if you intended JSON output."
        ).format(path=output_file)
    return None


def render_inspect_human(
    report: Any,
    source_text: Optional[str] = None,
    *,
    input_path: Optional[str] = None,
    options: Optional[HumanRenderOptions] = None,
) -> str:
    """Render an inspect report as checker-style human-readable text.

    :param report: Inspect report returned by
        :func:`pyfcstm.diagnostics.inspect_model`.
    :type report: pyfcstm.diagnostics.inspect.ModelInspect
    :param source_text: Optional FCSTM source text used to render source
        excerpts for diagnostics with spans.
    :type source_text: Optional[str], optional
    :param input_path: Optional path shown in the report heading and locations.
    :type input_path: Optional[str], optional
    :param options: Optional presentation controls such as ANSI color.
    :type options: pyfcstm.diagnostics.inspect_render.HumanRenderOptions, optional
    :return: Human-readable report ending with a newline.
    :rtype: str

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.diagnostics import inspect_model
        >>> model = load_state_machine_from_text('state Root { state Idle; [*] -> Idle; }')
        >>> text = render_inspect_human(inspect_model(model), 'state Root { state Idle; [*] -> Idle; }')
        >>> '[WARN] FCSTM Inspect Report' in text
        True
    """
    options = options or HumanRenderOptions()
    counts = _severity_counts(report.diagnostics)
    status = _status_from_counts(counts)
    lines: List[str] = []
    label = _format_human_severity_label(status, options=options)
    heading = "FCSTM Inspect Report"
    if input_path:
        heading = f"{heading}: {input_path}"
    lines.append(f"{label} {heading}")
    lines.append("")
    lines.append("Summary")
    lines.append(f"  status: {status}")
    lines.append(f"  root: {report.root_state_path}")
    lines.append(
        "  states: {total} total / {leaf} leaf".format(
            total=len(report.states),
            leaf=report.metrics.n_states_leaf,
        )
    )
    lines.append(f"  transitions: {len(report.transitions)}")
    lines.append(f"  variables: {report.metrics.n_variables}")
    lines.append(
        "  diagnostics: {error} errors / {warning} warnings / {info} infos".format(
            error=counts["error"],
            warning=counts["warning"],
            info=counts["info"],
        )
    )
    lines.append("")
    if not report.diagnostics:
        lines.append("No diagnostics.")
        return "\n".join(lines) + "\n"

    for diagnostic in report.diagnostics:
        lines.extend(
            _render_human_diagnostic(
                diagnostic,
                source_text=source_text,
                input_path=input_path,
                options=options,
            )
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_inspect_llm_json(
    report: Any, source_text: Optional[str] = None, *, input_path: Optional[str] = None
) -> str:
    """Render an inspect report as a stable compact JSON packet for LLMs.

    The packet is marked with :data:`INSPECT_LLM_SCHEMA_VERSION`. This
    versioned contract is intended for downstream repair loops that need a
    compact, source-located, and provenance-aware diagnostic report.

    :param report: Inspect report returned by
        :func:`pyfcstm.diagnostics.inspect_model`.
    :type report: pyfcstm.diagnostics.inspect.ModelInspect
    :param source_text: Optional source text for diagnostic excerpts.
    :type source_text: Optional[str], optional
    :param input_path: Optional input path attached to the packet.
    :type input_path: Optional[str], optional
    :return: Pretty-printed JSON packet ending with a newline.
    :rtype: str

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.diagnostics import inspect_model
        >>> model = load_state_machine_from_text('state Root { state Idle; [*] -> Idle; }')
        >>> text = render_inspect_llm_json(inspect_model(model), 'state Root { state Idle; [*] -> Idle; }')
        >>> INSPECT_LLM_SCHEMA_VERSION in text
        True
    """
    packet = _llm_packet(report, source_text, input_path=input_path)
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_inspect_llm_markdown(
    report: Any, source_text: Optional[str] = None, *, input_path: Optional[str] = None
) -> str:
    """Render an inspect report as stable Markdown for LLM prompts.

    :param report: Inspect report returned by
        :func:`pyfcstm.diagnostics.inspect_model`.
    :type report: pyfcstm.diagnostics.inspect.ModelInspect
    :param source_text: Optional source text for diagnostic excerpts.
    :type source_text: Optional[str], optional
    :param input_path: Optional path shown in the heading and locations.
    :type input_path: Optional[str], optional
    :return: Markdown report ending with a newline.
    :rtype: str

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.diagnostics import inspect_model
        >>> model = load_state_machine_from_text('state Root { state Idle; [*] -> Idle; }')
        >>> text = render_inspect_llm_markdown(inspect_model(model), 'state Root { state Idle; [*] -> Idle; }')
        >>> '# FCSTM Inspect Report' in text
        True
    """
    counts = _severity_counts(report.diagnostics)
    lines = ["# FCSTM Inspect Report", ""]
    lines.append(f"- Schema: `{INSPECT_LLM_SCHEMA_VERSION}`")
    lines.append("- Schema status: `stable`")
    lines.append(f"- Status: `{_status_from_counts(counts)}`")
    if input_path:
        lines.append(f"- Input: `{input_path}`")
    lines.append(
        "- Diagnostics: {error} errors / {warning} warnings / {info} infos".format(
            error=counts["error"],
            warning=counts["warning"],
            info=counts["info"],
        )
    )
    lines.append("")
    lines.append("## Repair protocol")
    lines.append("")
    for rule in _GLOBAL_REPAIR_RULES:
        lines.append(f"- {rule}")
    lines.append("")
    if not report.diagnostics:
        lines.append("No diagnostics.")
        return "\n".join(lines) + "\n"
    for diagnostic in report.diagnostics:
        detail = _diagnostic_llm_dict(diagnostic, source_text, input_path=input_path)
        lines.append(f"## {diagnostic.code}")
        lines.append("")
        lines.append(f"- Severity: `{diagnostic.severity}`")
        if detail.get("location"):
            loc = detail["location"]
            location_text = f"line {loc['line']}, column {loc['column']}"
            if input_path:
                location_text = f"{input_path}:{loc['line']}:{loc['column']}"
            lines.append(f"- Location: `{location_text}`")
        lines.append(f"- Message: {diagnostic.message}")
        if detail.get("source"):
            lines.append(f"- Source: {detail['source']}")
        if detail.get("summary"):
            lines.append(f"- Why it matters: {detail['summary']}")
        if detail.get("source_excerpt"):
            excerpt = detail["source_excerpt"]
            context = excerpt.get("context", [])
            gutter_width = _markdown_gutter_width(context, excerpt)
            lines.append("- Source:")
            lines.append("  ```fcstm")
            for source_line in context:
                lines.append(
                    _format_source_line(
                        source_line["line"],
                        gutter_width,
                        source_line["text"],
                        prefix="  ",
                    )
                )
                if source_line.get("caret"):
                    lines.append(
                        "  {space}| {caret}".format(
                            space=" " * (gutter_width + 1),
                            caret=source_line["caret"],
                        )
                    )
            lines.append("  ```")
        if detail["recommended_actions"]:
            lines.append("- Recommended actions:")
            for action in detail["recommended_actions"]:
                lines.append(f"  - {_format_action_for_markdown(action)}")
        if detail["do_not"]:
            lines.append("- Do not:")
            for item in detail["do_not"]:
                lines.append(f"  - {item}")
        if detail["repair_guidance"]:
            lines.append("- Repair notes:")
            for item in detail["repair_guidance"]:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate_output_format(output_format: str) -> None:
    if output_format not in _INSPECT_OUTPUT_FORMATS:
        raise ValueError(f"unsupported inspect output format: {output_format!r}")


def _severity_counts(diagnostics: Iterable[ModelDiagnostic]) -> Dict[str, int]:
    counts = {severity: 0 for severity in _SEVERITY_ORDER}
    for diagnostic in diagnostics:
        counts[diagnostic.severity] += 1
    return counts


def _status_from_counts(counts: Mapping[str, int]) -> str:
    for severity in _SEVERITY_ORDER:
        if counts.get(severity, 0):
            return _STATUS_BY_SEVERITY[severity]
    return "ok"


def _format_human_severity_label(severity: str, *, options: HumanRenderOptions) -> str:
    text = "[{label}]".format(label=_SEVERITY_HUMAN_LABELS[severity])
    return _style_text(text, _severity_style(severity), options=options)


def _severity_style(severity: str) -> str:
    return _ANSI_STYLE_BY_SEVERITY[severity]


def _style_text(text: str, style: str, *, options: HumanRenderOptions) -> str:
    if not options.color_enabled:
        return text
    return "\033[{style}m{text}{reset}".format(
        style=style,
        text=text,
        reset=_ANSI_RESET,
    )


def _render_human_diagnostic(
    diagnostic: ModelDiagnostic,
    *,
    source_text: Optional[str],
    input_path: Optional[str],
    options: HumanRenderOptions,
) -> List[str]:
    label = _format_human_severity_label(diagnostic.severity, options=options)
    code = _style_text(diagnostic.code, _ANSI_BOLD, options=options)
    lines = [f"{label} {code}", f"  {diagnostic.message}"]
    if diagnostic.span is not None:
        lines.append(f"  --> {_format_span(diagnostic.span, input_path=input_path)}")
    excerpt = _source_excerpt(source_text, diagnostic.span)
    if excerpt is not None:
        gutter_width = _source_gutter_width(excerpt)
        gutter = " " * (gutter_width + 2) + "|"
        lines.append(gutter)
        for source_line in excerpt.context_lines:
            lines.append(
                _format_source_line(
                    source_line.line_number,
                    gutter_width,
                    source_line.text,
                    prefix=" ",
                )
            )
            if source_line.caret is not None:
                caret = _style_text(
                    source_line.caret,
                    _severity_style(diagnostic.severity),
                    options=options,
                )
                lines.append(f"{gutter} {caret}")
        lines.append(gutter)
    spec = CODE_REGISTRY.get(diagnostic.code)
    lines.append(f"   = source: {_diagnostic_source(spec)}")
    if spec is not None and spec.for_llm is not None:
        lines.append(f"   = why: {spec.for_llm.summary}")
        if spec.for_llm.recommended_actions:
            for action in spec.for_llm.recommended_actions:
                lines.append(f"   = fix: {_format_action_for_human(action)}")
        if spec.for_llm.do_not:
            for item in spec.for_llm.do_not:
                lines.append(f"   = do-not: {item}")
    return lines


def _llm_packet(
    report: Any, source_text: Optional[str], *, input_path: Optional[str]
) -> Dict[str, Any]:
    counts = _severity_counts(report.diagnostics)
    return {
        "schema_version": INSPECT_LLM_SCHEMA_VERSION,
        "schema_status": "stable",
        "status": _status_from_counts(counts),
        "input": input_path,
        "repair_protocol": {
            "goal": "repair the FCSTM model with the smallest semantic source change",
            "rules": list(_GLOBAL_REPAIR_RULES),
        },
        "summary": {
            "errors": counts["error"],
            "warnings": counts["warning"],
            "infos": counts["info"],
            "root_state_path": report.root_state_path,
            "states": len(report.states),
            "leaf_states": report.metrics.n_states_leaf,
            "transitions": len(report.transitions),
            "variables": report.metrics.n_variables,
        },
        "diagnostics": [
            _diagnostic_llm_dict(diagnostic, source_text, input_path=input_path)
            for diagnostic in report.diagnostics
        ],
    }


def _diagnostic_llm_dict(
    diagnostic: ModelDiagnostic,
    source_text: Optional[str],
    *,
    input_path: Optional[str],
) -> Dict[str, Any]:
    spec = CODE_REGISTRY.get(diagnostic.code)
    excerpt = _source_excerpt(source_text, diagnostic.span)
    return {
        "code": diagnostic.code,
        "severity": diagnostic.severity,
        "message": diagnostic.message,
        "location": _span_dict(diagnostic.span, input_path=input_path),
        "source_excerpt": _excerpt_dict(excerpt),
        "refs": _jsonable(diagnostic.refs),
        "source": _diagnostic_source(spec),
        "provenance": {
            "kind": _diagnostic_source(spec),
            "verify_required": _diagnostic_source(spec) == "verify-backed",
        },
        "summary": spec.for_llm.summary
        if spec is not None and spec.for_llm is not None
        else None,
        "recommended_actions": (
            [_jsonable(item) for item in spec.for_llm.recommended_actions]
            if spec is not None and spec.for_llm is not None
            else []
        ),
        "do_not": (
            list(spec.for_llm.do_not)
            if spec is not None and spec.for_llm is not None
            else []
        ),
        "repair_guidance": _repair_guidance_for_code(diagnostic.code),
    }


def _diagnostic_source(spec: Optional[Any]) -> str:
    if spec is None:
        return "unknown"
    if getattr(spec, "emit_tier", None) == "verify_pipeline":
        return "verify-backed"
    return "inspect-static"


def _repair_guidance_for_code(code: str) -> List[str]:
    return list(_REPAIR_NOTES_BY_CODE.get(code, ()))


def _source_excerpt(
    source_text: Optional[str], span: Optional[Span]
) -> Optional[SourceExcerpt]:
    if source_text is None or span is None:
        return None
    lines = source_text.splitlines()
    if span.line < 1 or span.line > len(lines):
        return None
    text = lines[span.line - 1]
    context_start = max(1, span.line - _SOURCE_CONTEXT_RADIUS)
    context_end = min(len(lines), span.line + _SOURCE_CONTEXT_RADIUS)
    start_column = max(span.column, 1)
    end_column = span.end_column if span.end_line in (None, span.line) else None
    if end_column is None or end_column <= start_column:
        end_column = start_column + 1
    caret_len = max(1, end_column - start_column)
    caret = " " * (start_column - 1) + "^" * caret_len
    context_lines = []
    for line_number in range(context_start, context_end + 1):
        context_lines.append(
            SourceExcerptLine(
                line_number,
                lines[line_number - 1],
                caret if line_number == span.line else None,
            )
        )
    return SourceExcerpt(span.line, text, caret, tuple(context_lines))


def _source_gutter_width(excerpt: SourceExcerpt) -> int:
    if not excerpt.context_lines:
        return len(str(excerpt.line_number))
    return max(len(str(item.line_number)) for item in excerpt.context_lines)


def _markdown_gutter_width(
    context: List[Dict[str, Any]], excerpt: Dict[str, Any]
) -> int:
    if context:
        return max(len(str(item["line"])) for item in context)
    return len(str(excerpt["line"]))


def _format_source_line(
    line_number: int,
    gutter_width: int,
    text: str,
    *,
    prefix: str,
) -> str:
    base = "{prefix}{line:>{width}} |".format(
        prefix=prefix,
        line=line_number,
        width=gutter_width,
    )
    if text:
        return f"{base} {text}"
    return base


def _format_span(span: Span, *, input_path: Optional[str]) -> str:
    prefix = f"{input_path}:" if input_path else ""
    return f"{prefix}{span.line}:{span.column}"


def _span_dict(
    span: Optional[Span], *, input_path: Optional[str]
) -> Optional[Dict[str, Any]]:
    if span is None:
        return None
    data: Dict[str, Any] = {
        "line": span.line,
        "column": span.column,
    }
    if input_path is not None:
        data["path"] = input_path
    if span.end_line is not None:
        data["end_line"] = span.end_line
    if span.end_column is not None:
        data["end_column"] = span.end_column
    return data


def _excerpt_dict(excerpt: Optional[SourceExcerpt]) -> Optional[Dict[str, Any]]:
    if excerpt is None:
        return None
    context = [
        {
            "line": item.line_number,
            "text": item.text,
            "caret": item.caret,
            "is_anchor": item.line_number == excerpt.line_number,
        }
        for item in excerpt.context_lines
    ]
    return {
        "line": excerpt.line_number,
        "text": excerpt.text,
        "caret": excerpt.caret,
        "context": context,
    }


def _format_action_for_human(action: Mapping[str, Any]) -> str:
    pieces = []
    for key in ("kind", "target", "rationale"):
        if key in action:
            pieces.append(f"{key}: {action[key]}")
    if pieces:
        return "; ".join(pieces)
    return json.dumps(_jsonable(action), ensure_ascii=False, sort_keys=True)


def _format_action_for_markdown(action: Mapping[str, Any]) -> str:
    if "rationale" in action:
        prefix = []
        if "kind" in action:
            prefix.append(f"`{action['kind']}`")
        if "target" in action:
            prefix.append(f"target `{action['target']}`")
        if prefix:
            return f"{' / '.join(prefix)}: {action['rationale']}"
        return str(action["rationale"])
    return json.dumps(_jsonable(action), ensure_ascii=False, sort_keys=True)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _jsonable(getattr(value, name)) for name in value.__dataclass_fields__
        }
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
