"""
Standalone C harness generation for native toolchain semantic alignment.

This module converts a shared semantic fixture and rendered C-family runtime
metadata into a small case-specific ``harness.c`` file. The harness uses only
public generated APIs, executes fixture steps, writes public observations as
JSON Lines, and leaves semantic assertion logic in Python.

The module contains:

* :class:`HarnessContext` - Template context for one generated harness.
* :func:`build_harness_context` - Convert a semantic case into template data.
* :func:`render_harness` - Render ``harness.c`` for ``c`` or ``c_poll``.
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


@dataclass(frozen=True)
class HarnessContext:
    """
    Template context for one native toolchain C harness.

    :param template_name: Template under test, either ``"c"`` or ``"c_poll"``.
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
    Build a C harness template context for a semantic fixture.

    :param template_name: Template name, either ``"c"`` or ``"c_poll"``.
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
    if template_name not in ("c", "c_poll"):
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


def render_harness(
    template_name: str, case: SemanticCase, output_path: str
) -> HarnessContext:
    """
    Render a native C harness source file.

    :param template_name: Template name, either ``"c"`` or ``"c_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param output_path: Destination ``harness.c`` path.
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
    template_file = "c_poll_main.c.j2" if template_name == "c_poll" else "c_main.c.j2"
    text = _environment().get_template(template_file).render(context=context)
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
