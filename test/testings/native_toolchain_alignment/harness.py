"""
Standalone C-family harness generation for native toolchain alignment.

This module converts a shared semantic fixture and rendered C-family runtime
metadata into a small case-specific harness source file. C harnesses call the
public generated C APIs through ``machine.h``. C++ harnesses call only the
generated wrapper APIs through ``machine.hpp``. Each harness executes fixture
steps, writes public observations as JSON Lines, and leaves semantic assertion
logic in Python.

The module contains:

* :class:`HarnessContext` - Template context for one generated harness.
* :func:`build_harness_context` - Convert a semantic case into template data.
* :func:`render_harness` - Render ``harness.c`` or ``harness.cpp``.
* :func:`render_cmake_project` - Render the native CMake project files.

Example::

    >>> from test.testings.simulate_semantics import load_semantic_case
    >>> case = load_semantic_case("design_basic_simple_transition")
    >>> context = build_harness_context("c", case)
    >>> context.case_id
    'design_basic_simple_transition'
"""

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import (
    to_c_identifier,
    to_c_path_identifier,
    to_c_public_identifier,
    to_c_public_macro_identifier,
)
from test.testings import simulate_semantics
from test.testings.simulate_semantics import SemanticCase

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "harness_templates")
_INCLUDE_DIRECTIVE_RE = re.compile(r"^\s*#\s*include\s*(?P<target>[^\n]+)", re.M)
_INCLUDE_LITERAL_RE = re.compile(r'(?:(?:"([^"\n]+)")|(?:<([^>\n]+)>))')
_LINE_CONTINUATION_RE = re.compile(r"\\\r?\n")
_TOKEN_PASTE_RE = re.compile(r"##")
_NATIVE_HANDLE_CALL_RE = re.compile(r"\bnative_handle\s*\(")
_DIRECT_C_TYPE_RE = re.compile(
    r"(?<!Wrapper::)\b(?:[A-Za-z_][A-Za-z0-9_]*Machine|Machine)"
    r"(Vars|StateId|EventId|Int|Hooks|EventChecks|ExecutionContext|EventContext)?\b"
)
_DIRECT_C_API_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*Machine_"
    r"(create_uninitialized|create|destroy|init|hot_start|set_hooks|"
    r"set_event_checks|cycle|vars|is_ended|current_state_id|"
    r"current_state_path|current_state_name|last_error|dsl_source)\b"
)


@dataclass(frozen=True)
class HarnessContext:
    """
    Template context for one native toolchain harness.

    :param template_name: Template under test, such as ``"c"`` or ``"cpp"``.
    :type template_name: str
    :param case_id: Shared semantic fixture case id.
    :type case_id: str
    :param machine_class_name: Generated public machine type prefix.
    :type machine_class_name: str
    :param machine_macro_name: Generated public macro prefix.
    :type machine_macro_name: str
    :param variables: Persistent variable descriptors.
    :type variables: typing.Sequence[typing.Mapping[str, typing.Any]]
    :param states: State descriptors with public id macros.
    :type states: typing.Sequence[typing.Mapping[str, typing.Any]]
    :param events: Event descriptors with public id macros.
    :type events: typing.Sequence[typing.Mapping[str, typing.Any]]
    :param actions: Action descriptors with public id macros.
    :type actions: typing.Sequence[typing.Mapping[str, typing.Any]]
    :param hooks: Abstract hook descriptors.
    :type hooks: typing.Sequence[typing.Mapping[str, typing.Any]]
    :param steps: Preprocessed semantic fixture steps.
    :type steps: typing.Sequence[typing.Mapping[str, typing.Any]]
    :param initial: Initial hot-start descriptor, if any.
    :type initial: typing.Mapping[str, typing.Any], optional
    :param initial_expect: Expected initial failure descriptor, if any.
    :type initial_expect: typing.Mapping[str, typing.Any], optional
    :param harness_source_name: Harness source filename.
    :type harness_source_name: str
    :param machine_source_names: Generated machine sources copied into the
        harness project.
    :type machine_source_names: typing.Sequence[str]
    :param wrapper_namespace_suffix: Generated C++ wrapper namespace suffix,
        if the harness uses a C++ wrapper.
    :type wrapper_namespace_suffix: str, optional

    Example::

        >>> from test.testings.simulate_semantics import load_semantic_case
        >>> ctx = build_harness_context("c", load_semantic_case("design_basic_simple_transition"))
        >>> ctx.machine_class_name
        'RootMachine'
    """

    template_name: str
    case_id: str
    machine_class_name: str
    machine_macro_name: str
    variables: Sequence[Mapping[str, Any]]
    states: Sequence[Mapping[str, Any]]
    events: Sequence[Mapping[str, Any]]
    actions: Sequence[Mapping[str, Any]]
    hooks: Sequence[Mapping[str, Any]]
    steps: Sequence[Mapping[str, Any]]
    initial: Optional[Mapping[str, Any]] = None
    initial_expect: Optional[Mapping[str, Any]] = None
    harness_source_name: str = "harness.c"
    machine_source_names: Sequence[str] = ("machine.c",)
    wrapper_namespace_suffix: Optional[str] = None

    @property
    def uses_cpp_wrapper(self) -> bool:
        """
        Return whether this context renders a C++ wrapper harness.

        :return: ``True`` for ``cpp`` and ``cpp_poll`` harnesses.
        :rtype: bool

        Example::

            >>> build_harness_context("cpp", simulate_semantics.load_semantic_case("design_basic_simple_transition")).uses_cpp_wrapper
            True
        """
        return self.wrapper_namespace_suffix is not None


_CONTEXT_TEMPLATE_NAMES = {
    "c": "c",
    "c_poll": "c_poll",
    "cpp": "c",
    "cpp_poll": "c_poll",
}
_HARNESS_TEMPLATE_FILES = {
    "c": "c_main.c.j2",
    "c_poll": "c_poll_main.c.j2",
    "cpp": "cpp_main.cpp.j2",
    "cpp_poll": "cpp_poll_main.cpp.j2",
}
_HARNESS_SOURCE_NAMES = {
    "c": "harness.c",
    "c_poll": "harness.c",
    "cpp": "harness.cpp",
    "cpp_poll": "harness.cpp",
}
_MACHINE_SOURCE_NAMES = {
    "c": ("machine.c",),
    "c_poll": ("machine.c",),
    "cpp": ("machine.c", "machine.cpp"),
    "cpp_poll": ("machine.c", "machine.cpp"),
}
_WRAPPER_NAMESPACE_SUFFIX = {"cpp": "cpp", "cpp_poll": "cpp_poll"}


def _parse_model(case: SemanticCase):
    ast_node = parse_with_grammar_entry(case.dsl_code, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast_node)


def _state_rows(model) -> List[Dict[str, Any]]:
    rows = []
    for state in model.walk_states():
        path = ".".join(state.path)
        slug = to_c_path_identifier(state.path)
        rows.append({"path": path, "macro": "STATE_%s" % slug})
    return rows


def _event_rows(model) -> List[Dict[str, Any]]:
    rows = []
    seen = set()
    for state in model.walk_states():
        for event in state.events.values():
            if event.path_name in seen:
                continue
            seen.add(event.path_name)
            rows.append(
                {
                    "path": event.path_name,
                    "macro": "EVENT_%s"
                    % to_c_path_identifier(event.path_name.split(".")),
                    "field": "check_%s"
                    % to_c_path_identifier(event.path_name.split(".")),
                }
            )
    return rows


def _action_rows(model) -> List[Dict[str, Any]]:
    rows = []
    seen = set()
    for state in model.walk_states():
        groups = [
            state.list_on_enters(with_ids=True),
            state.list_on_durings(aspect=None, with_ids=True),
            state.list_on_exits(with_ids=True),
            state.list_on_durings(aspect="before", with_ids=True),
            state.list_on_durings(aspect="after", with_ids=True),
            state.list_on_during_aspects(aspect="before", with_ids=True),
            state.list_on_during_aspects(aspect="after", with_ids=True),
        ]
        for group in groups:
            for _, item in group:
                if item.func_name in seen:
                    continue
                seen.add(item.func_name)
                rows.append(
                    {
                        "path": item.func_name,
                        "macro": "ACTION_%s"
                        % to_c_path_identifier(item.func_name.split(".")),
                    }
                )
    return rows


def _hook_rows(model) -> List[Dict[str, Any]]:
    rows = []
    seen = set()
    for state in model.walk_states():
        groups = [
            state.list_on_enters(with_ids=True),
            state.list_on_durings(aspect=None, with_ids=True),
            state.list_on_exits(with_ids=True),
            state.list_on_durings(aspect="before", with_ids=True),
            state.list_on_durings(aspect="after", with_ids=True),
            state.list_on_during_aspects(aspect="before", with_ids=True),
            state.list_on_during_aspects(aspect="after", with_ids=True),
        ]
        for group in groups:
            for _, item in group:
                resolved = item
                seen_refs = set()
                while resolved.ref is not None and id(resolved) not in seen_refs:
                    seen_refs.add(id(resolved))
                    resolved = resolved.ref
                if not resolved.is_abstract or resolved.func_name in seen:
                    continue
                seen.add(resolved.func_name)
                rows.append(
                    {
                        "action": resolved.func_name,
                        "field": "on_%s"
                        % to_c_path_identifier(resolved.func_name.split(".")),
                    }
                )
    return rows


def _var_rows(model) -> List[Dict[str, Any]]:
    rows = []
    for def_item in model.defines.values():
        rows.append(
            {
                "name": def_item.name,
                "field": to_c_identifier(def_item.name),
                "type": def_item.type,
            }
        )
    return rows


def _macro_lookup(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, str]:
    return {row["path"]: row[key] for row in rows}


def _cycle_inputs(step: Mapping[str, Any], case: SemanticCase, index: int) -> List[str]:
    field_path = "steps[%d]" % index
    cycle_input = simulate_semantics._cycle_input_for_step(
        step, case.id, case.yaml_path, field_path
    )
    if isinstance(cycle_input, str):
        return [cycle_input]
    return list(cycle_input)


def _normalize_current_path_for_event(
    current_state: Optional[str], event_ref: str, root_path: str
) -> str:
    if event_ref.startswith("/"):
        return root_path + "." + event_ref[1:]
    if event_ref.startswith("."):
        dot_count = len(event_ref) - len(event_ref.lstrip("."))
        remaining = event_ref[dot_count:]
        parts = current_state.split(".") if current_state else []
        return ".".join(parts[:-dot_count] + [remaining])
    if "." in event_ref:
        return event_ref
    return current_state + "." + event_ref if current_state else event_ref


def _event_macros_for_steps(
    steps: Sequence[Mapping[str, Any]],
    case: SemanticCase,
    event_macros: Mapping[str, str],
    root_path: str,
) -> List[Dict[str, Any]]:
    current_state = None
    result = []
    for index, step in enumerate(steps):
        events = []
        for event_ref in _cycle_inputs(step, case, index):
            resolved = event_ref
            if resolved not in event_macros:
                resolved = _normalize_current_path_for_event(
                    current_state, event_ref, root_path
                )
            events.append({"path": resolved, "macro": event_macros.get(resolved)})
        result.append({"events": events})
        expect = step.get("expect") or {}
        if "state" in expect:
            current_state = expect["state"]
    return result


def _initial_context(
    initial: Mapping[str, Any],
    state_macros: Mapping[str, str],
    variables: Sequence[Mapping[str, Any]],
    initial_expect: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    def synthetic_error() -> Dict[str, Any]:
        raises = (initial_expect or {}).get("raises") or {}
        return {
            "state_macro": state_macros.get(state_path),
            "state_path": state_path,
            "assignments": [],
            "synthetic_error": True,
            "error_message": str(raises.get("match", "Invalid initial variable value")),
        }

    if not initial:
        return None
    state_path = initial.get("state")
    vars_data = initial.get("vars")
    if state_path is None:
        return None
    if state_macros.get(state_path) is None:
        return synthetic_error()
    assignments = []
    for variable in variables:
        value = (vars_data or {}).get(variable["name"], 0)
        if type(value) is bool or type(value) not in (int, float):
            return synthetic_error()
        if type(value) is float and not math.isfinite(value):
            return synthetic_error()
        if variable["type"] == "int" and type(value) is float:
            if value != int(value):
                return synthetic_error()
            value = int(value)
        assignments.append({"field": variable["field"], "value": repr(value).lower()})
    return {
        "state_macro": state_macros.get(state_path),
        "state_path": state_path,
        "assignments": assignments,
        "synthetic_error": False,
    }


def _step_contexts(
    case: SemanticCase,
    state_macros: Mapping[str, str],
    event_steps: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    steps = []
    runtime_already_ended = False
    for index, step in enumerate(case.data.get("steps") or []):
        expect = step.get("expect") or {}
        cycle_count = simulate_semantics._effective_cycle_count(
            step, case.id, case.yaml_path, "steps[%d]" % index
        )
        expected_state = expect.get("state")
        pre_error_message = None
        events = event_steps[index]["events"]
        if any(item.get("macro") is None for item in events):
            if (
                runtime_already_ended
                and expect.get("ended") is True
                and "raises" not in expect
            ):
                # The generated C runtimes intentionally return success before
                # inspecting event ids once the machine has ended, matching the
                # simulator's public no-op behavior for ended cycles. A missing
                # event path in this situation therefore must not become a
                # synthetic harness-side error.
                events = []
            else:
                raises = expect.get("raises") or {}
                pre_error_message = str(raises.get("match", "Unknown event path"))
        steps.append(
            {
                "index": index,
                "cycle_count": cycle_count,
                "events": events,
                "expected_state_macro": state_macros.get(expected_state)
                if expected_state
                else None,
                "pre_error_message": pre_error_message,
            }
        )
        if "ended" in expect:
            runtime_already_ended = bool(expect["ended"])
    return steps


def build_harness_context(template_name: str, case: SemanticCase) -> HarnessContext:
    """
    Build a native harness template context for a semantic fixture.

    :param template_name: Template name, such as ``"c"`` or ``"cpp_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :return: Harness template context.
    :rtype: HarnessContext
    :raises ValueError: If ``template_name`` is unsupported.

    Example::

        >>> case = simulate_semantics.load_semantic_case("design_basic_simple_transition")
        >>> build_harness_context("c", case).template_name
        'c'
    """
    if template_name not in _CONTEXT_TEMPLATE_NAMES:
        raise ValueError("unsupported native toolchain template: %r" % template_name)
    model = _parse_model(case)
    states = _state_rows(model)
    events = _event_rows(model)
    actions = _action_rows(model)
    hooks = _hook_rows(model)
    variables = _var_rows(model)
    state_macros = _macro_lookup(states, "macro")
    event_macros = _macro_lookup(events, "macro")
    root_path = ".".join(model.root_state.path)
    event_steps = _event_macros_for_steps(
        case.data.get("steps") or [], case, event_macros, root_path
    )
    initial_expect = simulate_semantics._initial_constructor_expect(case)
    return HarnessContext(
        template_name=template_name,
        case_id=case.id,
        machine_class_name=to_c_public_identifier(model.root_state.name, "Machine"),
        machine_macro_name=to_c_public_macro_identifier(
            model.root_state.name, "_MACHINE"
        ),
        variables=variables,
        states=states,
        events=events,
        actions=actions,
        hooks=hooks,
        steps=_step_contexts(case, state_macros, event_steps),
        initial=_initial_context(
            case.data.get("initial") or {}, state_macros, variables, initial_expect
        ),
        initial_expect=initial_expect,
        harness_source_name=_HARNESS_SOURCE_NAMES[template_name],
        machine_source_names=_MACHINE_SOURCE_NAMES[template_name],
        wrapper_namespace_suffix=_WRAPPER_NAMESPACE_SUFFIX.get(template_name),
    )


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["tojson"] = json.dumps
    return env


def _mask_cpp_comments_and_literals(source: str, mask_literals: bool) -> str:
    """Replace C++ comments and optionally literals with whitespace.

    :param source: C++ source text to inspect.
    :type source: str
    :param mask_literals: Whether string and character literals should also be
        replaced by whitespace.
    :type mask_literals: bool
    :return: Source text with comments, and optionally literals, masked.
    :rtype: str

    Example::

        >>> _mask_cpp_comments_and_literals('// #include "machine.h"\\n', False)
        '\\n'
    """
    source = _LINE_CONTINUATION_RE.sub("", source)
    output = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        next_char = source[index + 1] if index + 1 < length else ""
        if char == "/" and next_char == "/":
            index += 2
            while index < length and source[index] != "\n":
                index += 1
            if index < length:
                output.append("\n")
                index += 1
        elif char == "/" and next_char == "*":
            output.extend((" ", " "))
            index += 2
            while index < length:
                current = source[index]
                following = source[index + 1] if index + 1 < length else ""
                if current == "*" and following == "/":
                    output.extend((" ", " "))
                    index += 2
                    break
                output.append("\n" if current == "\n" else " ")
                index += 1
        elif mask_literals and char in {'"', "'"}:
            quote = char
            output.append(" ")
            index += 1
            while index < length:
                current = source[index]
                output.append("\n" if current == "\n" else " ")
                index += 1
                if current == "\\" and index < length:
                    escaped = source[index]
                    output.append("\n" if escaped == "\n" else " ")
                    index += 1
                elif current == quote:
                    break
        else:
            output.append(char)
            index += 1
    return "".join(output)


def _iter_include_targets(source: str) -> List[str]:
    """Return literal include targets from comment-masked C++ source.

    :param source: C++ source text to inspect.
    :type source: str
    :return: Include targets; ``""`` means a non-literal include directive.
    :rtype: list[str]

    Example::

        >>> _iter_include_targets('#include "machine.hpp"\\n')
        ['machine.hpp']
    """
    directive_source = _mask_cpp_comments_and_literals(source, mask_literals=False)
    targets = []
    for match in _INCLUDE_DIRECTIVE_RE.finditer(directive_source):
        raw_target = match.group("target").strip()
        literal_match = _INCLUDE_LITERAL_RE.fullmatch(raw_target)
        targets.append(
            (literal_match.group(1) or literal_match.group(2)) if literal_match else ""
        )
    return targets


def _assert_cpp_wrapper_harness_source(source: str) -> None:
    """Assert that a C++ native harness enters through ``machine.hpp``.

    :param source: Rendered C++ harness source.
    :type source: str
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the source bypasses the C++ wrapper surface.

    Example::

        >>> _assert_cpp_wrapper_harness_source('#include "machine.hpp"\\n')
    """
    include_targets = _iter_include_targets(source)
    normalized_includes = [
        os.path.basename(target.replace("\\", "/")).lower()
        for target in include_targets
    ]
    symbol_source = _mask_cpp_comments_and_literals(source, mask_literals=True)
    assert include_targets and all(include_targets)
    assert "machine.hpp" in normalized_includes
    assert "machine.h" not in normalized_includes
    assert not _TOKEN_PASTE_RE.search(symbol_source)
    assert not _NATIVE_HANDLE_CALL_RE.search(symbol_source)
    symbol_source_without_alias = symbol_source.replace(
        "MachineWrapper", "            "
    )
    assert not _DIRECT_C_TYPE_RE.search(symbol_source_without_alias)
    assert not _DIRECT_C_API_RE.search(symbol_source)


def render_harness(
    template_name: str, case: SemanticCase, output_path: str
) -> HarnessContext:
    """
    Render a native C-family harness source file.

    :param template_name: Template name, such as ``"c"`` or ``"cpp_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param output_path: Destination harness source path.
    :type output_path: str
    :return: Harness context used for rendering.
    :rtype: HarnessContext

    Example::

        >>> import tempfile, os
        >>> case = simulate_semantics.load_semantic_case("design_basic_simple_transition")
        >>> td = tempfile.mkdtemp()
        >>> context = render_harness("c", case, os.path.join(td, "harness.c"))
        >>> context.case_id
        'design_basic_simple_transition'
    """
    context = build_harness_context(template_name, case)
    template_file = _HARNESS_TEMPLATE_FILES[template_name]
    text = _environment().get_template(template_file).render(context=context)
    if context.uses_cpp_wrapper:
        _assert_cpp_wrapper_harness_source(text)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return context


def render_cmake_project(context: HarnessContext, output_path: str) -> None:
    """
    Render the CMake project used by a native toolchain profile.

    :param context: Harness template context.
    :type context: HarnessContext
    :param output_path: Destination ``CMakeLists.txt`` path.
    :type output_path: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> import tempfile, os
        >>> case = simulate_semantics.load_semantic_case("design_basic_simple_transition")
        >>> context = build_harness_context("c", case)
        >>> td = tempfile.mkdtemp()
        >>> render_cmake_project(context, os.path.join(td, "CMakeLists.txt"))
    """
    text = _environment().get_template("CMakeLists.txt.j2").render(context=context)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
