"""Helpers for comparing combo-trigger expansion with hand-written pseudo chains.

The helpers in this module intentionally live under the Python test tree.  They
only depend on production ``pyfcstm`` APIs, the Python standard library, and
plain assertions so downstream compatibility tests can compare generated combo
models with equivalent hand-written pseudo-state models without crossing into
jsfcstm or editor test fixtures.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from textwrap import dedent
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from pyfcstm.dsl import EXIT_STATE, INIT_STATE, parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.model import State, StateMachine, Transition
from pyfcstm.simulate import SimulationRuntime


def parse_machine(source: str) -> StateMachine:
    """Parse FCSTM DSL source into a validated state-machine model.

    :param source: FCSTM DSL source text.
    :type source: str
    :return: Parsed state machine.
    :rtype: pyfcstm.model.model.StateMachine

    Example::

        >>> machine = parse_machine('state Root { state A; [*] -> A; }')
        >>> machine.root_state.name
        'Root'
    """
    ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def _is_init_endpoint(endpoint: object) -> bool:
    return endpoint is INIT_STATE or str(endpoint) == "INIT_STATE"


def _is_exit_endpoint(endpoint: object) -> bool:
    return endpoint is EXIT_STATE or str(endpoint) == "EXIT_STATE"


def _state_path(path: Sequence[str]) -> str:
    return ".".join(path)


def _pseudo_label_maps(model: StateMachine) -> Dict[Tuple[str, ...], str]:
    labels: Dict[Tuple[str, ...], str] = {}
    for parent in model.walk_states():
        counters: Dict[str, int] = defaultdict(int)
        for state in parent.substates.values():
            if not state.is_pseudo:
                continue
            display = state.extra_name or state.name
            counters[display] += 1
            labels[state.path] = "<pseudo:%s#%d>" % (display, counters[display])
    return labels


def _endpoint_label(
    owner: State,
    endpoint: object,
    pseudo_labels: Mapping[Tuple[str, ...], str],
) -> str:
    if _is_init_endpoint(endpoint):
        return "[*]"
    if _is_exit_endpoint(endpoint):
        return "[*]"

    name = str(endpoint)
    state = owner.substates.get(name)
    if state is not None and state.is_pseudo:
        return pseudo_labels[state.path]
    return name


def _event_name(transition: Transition) -> Optional[str]:
    if transition.event is None:
        return None
    return transition.event.path_name


def _guard_text(transition: Transition) -> Optional[str]:
    if transition.guard is None:
        return None
    return str(transition.guard)


def _effect_texts(transition: Transition) -> Tuple[str, ...]:
    return tuple(str(item.to_ast_node()) for item in transition.effects)


def pseudo_state_signature(model: StateMachine) -> Tuple[Tuple[str, str], ...]:
    """Return a normalized pseudo-state signature for a model.

    Generated combo states and hand-written pseudo states can have different
    concrete identifiers.  This signature compares them by parent path and
    display text, with an occurrence index for duplicate display texts under the
    same parent.

    :param model: State-machine model to summarize.
    :type model: pyfcstm.model.model.StateMachine
    :return: Normalized pseudo-state entries.
    :rtype: tuple

    Example::

        >>> machine = parse_machine('state Root { pseudo state P named "gate"; state A; [*] -> P; P -> A; }')
        >>> pseudo_state_signature(machine)
        (('Root', '<pseudo:gate#1>'),)
    """
    labels = _pseudo_label_maps(model)
    result = []
    for state in model.walk_states():
        if state.is_pseudo:
            parent_path = _state_path(state.parent.path) if state.parent else ""
            result.append((parent_path, labels[state.path]))
    return tuple(result)


def model_transition_signature(model: StateMachine) -> Tuple[Tuple[Any, ...], ...]:
    """Return a normalized transition graph signature for runtime comparison.

    The signature intentionally ignores combo provenance metadata.  It captures
    the ordinary model surface consumed by runtime, verify, and visualization:
    parent scope, normalized endpoints, canonical event path, guard text, and
    transition effects.

    :param model: State-machine model to summarize.
    :type model: pyfcstm.model.model.StateMachine
    :return: Ordered transition signature entries.
    :rtype: tuple

    Example::

        >>> machine = parse_machine('state Root { state A; state B; [*] -> A; A -> B; }')
        >>> model_transition_signature(machine)[0][:3]
        ('Root', '[*]', 'A')
    """
    labels = _pseudo_label_maps(model)
    result = []
    for owner in model.walk_states():
        for transition in owner.transitions:
            result.append(
                (
                    _state_path(owner.path),
                    _endpoint_label(owner, transition.from_state, labels),
                    _endpoint_label(owner, transition.to_state, labels),
                    _event_name(transition),
                    _guard_text(transition),
                    _effect_texts(transition),
                )
            )
    return tuple(result)


def combo_projection_signature(model: StateMachine) -> Tuple[Tuple[Any, ...], ...]:
    """Return key combo-provenance fields for generated transitions.

    :param model: State-machine model to summarize.
    :type model: pyfcstm.model.model.StateMachine
    :return: Ordered generated-transition provenance entries.
    :rtype: tuple

    Example::

        >>> machine = parse_machine('state Root { state A; state B; [*] -> A; A -> B :: E1 + E2; }')
        >>> len(combo_projection_signature(machine))
        2
    """
    labels = _pseudo_label_maps(model)
    result = []
    for owner in model.walk_states():
        for transition in owner.transitions:
            if not transition.combo_origin_refs:
                continue
            result.append(
                (
                    _state_path(owner.path),
                    _endpoint_label(owner, transition.from_state, labels),
                    _endpoint_label(owner, transition.to_state, labels),
                    _event_name(transition),
                    _guard_text(transition),
                    tuple(
                        (
                            ref.origin_id,
                            ref.term_index,
                            ref.role,
                            ref.consumes_term,
                            ref.term_text,
                        )
                        for ref in transition.combo_origin_refs
                    ),
                    transition.combo_projection_key,
                    transition.combo_projection_order_key,
                    transition.combo_reuse_group_id,
                    transition.combo_priority_run_identity,
                    transition.combo_priority_run_index,
                )
            )
    return tuple(result)


def _normalized_runtime_state(runtime: SimulationRuntime) -> str:
    if runtime.is_ended:
        return "<ended>"
    return _state_path(runtime.current_state.path)


def simulation_trace(
    model: StateMachine,
    cycle_events: Iterable[Any],
    *,
    initial_state: Optional[Any] = None,
    initial_vars: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], ...]:
    """Run a model and return stable per-cycle simulation metadata.

    :param model: State-machine model to execute.
    :type model: pyfcstm.model.model.StateMachine
    :param cycle_events: Iterable of values to pass to consecutive
        :meth:`pyfcstm.simulate.SimulationRuntime.cycle` calls.
    :type cycle_events: Iterable[typing.Any]
    :param initial_state: Optional hot-start state path.
    :type initial_state: typing.Any, optional
    :param initial_vars: Optional complete variable mapping for hot start.
    :type initial_vars: dict, optional
    :return: Tuple of per-cycle trace dictionaries.
    :rtype: tuple

    Example::

        >>> machine = parse_machine('state Root { state A; [*] -> A; }')
        >>> simulation_trace(machine, [None])[0]['state']
        'Root.A'
    """
    kwargs = {}
    if initial_state is not None:
        kwargs["initial_state"] = initial_state
    if initial_vars is not None:
        kwargs["initial_vars"] = copy.deepcopy(initial_vars)
    runtime = SimulationRuntime(model, **kwargs)

    trace: List[Dict[str, Any]] = []
    for events in cycle_events:
        result = runtime.cycle(events)
        trace.append(
            {
                "state": _normalized_runtime_state(runtime),
                "value": result.value,
                "vars": tuple(sorted(runtime.vars.items())),
                "input_events": result.input_events,
                "consumed_events": result.consumed_events,
                "unconsumed_events": result.unconsumed_events,
            }
        )
    return tuple(trace)


def assert_combo_matches_manual_pseudo(
    combo_source: str,
    manual_source: str,
    cycle_events: Iterable[Any],
) -> Tuple[StateMachine, StateMachine, Tuple[Dict[str, Any], ...]]:
    """Assert that combo DSL and a hand-written pseudo model are equivalent.

    :param combo_source: FCSTM source using combo trigger syntax.
    :type combo_source: str
    :param manual_source: FCSTM source using explicit pseudo states.
    :type manual_source: str
    :param cycle_events: Consecutive event inputs for runtime comparison.
    :type cycle_events: Iterable[typing.Any]
    :return: Parsed combo model, parsed manual model, and the shared trace.
    :rtype: tuple

    Example::

        >>> combo = 'state Root { state A; state B; [*] -> A; A -> B :: E1 + E2; }'
        >>> manual = 'state Root { state A; pseudo state P named "combo after E1"; state B; [*] -> A; A -> P :: E1; P -> B : /A.E2; }'
        >>> _, _, trace = assert_combo_matches_manual_pseudo(combo, manual, [None, ['Root.A.E1', 'Root.A.E2']])
        >>> trace[-1]['state']
        'Root.B'
    """
    combo_model = parse_machine(combo_source)
    manual_model = parse_machine(manual_source)
    events = list(cycle_events)

    assert pseudo_state_signature(combo_model) == pseudo_state_signature(manual_model)
    assert model_transition_signature(combo_model) == model_transition_signature(
        manual_model
    )

    combo_trace = simulation_trace(combo_model, events)
    manual_trace = simulation_trace(manual_model, events)
    assert combo_trace == manual_trace
    return combo_model, manual_model, combo_trace
