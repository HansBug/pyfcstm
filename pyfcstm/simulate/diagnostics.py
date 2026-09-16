"""Immutable evidence from actual simulator candidate checks.

Reports contain observations, not counterfactual executions. Formatting never
calls a guard, an input provider, or an abstract handler. ``vars`` retains the
runtime's persistent control/output mapping; ``roles`` identifies final model
roles, including imported bindings.
"""

import re
from dataclasses import dataclass, field, fields
from types import MappingProxyType
from typing import Mapping, Optional, Tuple, Union

from ..dsl import EXIT_STATE, INIT_STATE

Number = Union[int, float]


def _transition_label(state, transition):
    """Use the same source-local edge address as committed traces and BMC."""
    transitions = (
        state.init_transitions
        if transition.from_state == INIT_STATE
        else state.transitions_from
    )
    # Root exits are synthesized afresh on each model property access.
    index = (
        0
        if state.is_root_state and transition.from_state != INIT_STATE
        else next(i for i, item in enumerate(transitions) if item is transition)
    )
    target = "[*]" if transition.to_state == EXIT_STATE else transition.to_state
    return "%s::%d::%s->%s" % (
        ".".join(state.path),
        index,
        transition.from_state,
        target,
    )


def _format_values(values):
    """Keep all keys and reuse the runtime's bounded integer representation."""
    from .runtime import _safe_runtime_repr

    return "{%s}" % ", ".join(
        "%r: %s" % (name, _safe_runtime_repr(value)) for name, value in values.items()
    )


@dataclass(frozen=True)
class TransitionDecision:
    """One check, with the snapshot seen by that check.

    ``id`` is local to one report. ``parent_id`` names the enclosing candidate
    whose successor is being validated, not a committed predecessor. Siblings
    can belong to alternative search branches. ``None`` check results mean not
    evaluated; a missing event/guard expression means no condition was required.
    Only ``committed`` proves that this selection survived the whole cycle.

    :param id: Unique check number within the report.
    :param parent_id: Enclosing successor-validation check, or ``None``.
    :param transition_label: Source-local transition address shared with traces.
    :param phase: ``preflight``, ``execution``, or ``validation``.
    :param state_path: Source state at the check.
    :param event: Required canonical event, or ``None``.
    :param guard: Guard expression text, or ``None``.
    :param vars: Persistent control/output snapshot at the check.
    :param inputs: Frozen input vector for this actual cycle.
    :param parameters: Construction-time parameters.
    :param location: Available source path and span coordinates.
    :param event_result: Actual event match, or ``None`` if skipped.
    :param guard_result: Actual guard match, or ``None`` if skipped.
    :param successor_result: Aggregate validation result, or ``None`` if unused.
    :param outcome: ``event_missing``, ``guard_false``, ``successor_rejected``,
        ``selected``, ``enabled`` (search only), or ``not_evaluated``.
    :param blocked_by: Successful prior selection that skipped this candidate.
    :param committed: Whether this particular selection was committed.
    :param combo_origins: Detached authored combo references, including every
        origin sharing this expanded edge. Term indexes are zero-based.
    """

    id: int
    parent_id: Optional[int]
    transition_label: str
    phase: str
    state_path: Tuple[str, ...]
    event: Optional[str]
    guard: Optional[str]
    vars: Mapping[str, Number]
    inputs: Mapping[str, Number]
    parameters: Mapping[str, Number]
    location: Mapping[str, Optional[Union[str, int]]]
    event_result: Optional[bool] = None
    guard_result: Optional[bool] = None
    successor_result: Optional[bool] = None
    outcome: str = "not_evaluated"
    blocked_by: Optional[int] = None
    committed: bool = False
    combo_origins: Tuple[Mapping[str, object], ...] = ()

    def __post_init__(self):
        for name in ("vars", "inputs", "parameters", "location"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, "state_path", tuple(self.state_path))
        object.__setattr__(
            self,
            "combo_origins",
            tuple(MappingProxyType(dict(origin)) for origin in self.combo_origins),
        )

    def to_dict(self) -> dict:
        """Return independent JSON-compatible data, including unevaluated checks."""
        data = {item.name: getattr(self, item.name) for item in fields(self)}
        for name in ("vars", "inputs", "parameters", "location"):
            data[name] = dict(data[name])
        data["state_path"] = list(self.state_path)
        data["combo_origins"] = [dict(origin) for origin in self.combo_origins]
        return data


@dataclass(frozen=True)
class CycleDiagnostics:
    """Detached diagnostic report for one normally returned ``cycle`` call.

    :param cycle_count: Runtime cycle count after the call; no-op does not add one.
    :param outcome: ``cycle``, ``delta``, ``terminated``, or ``noop``.
    :param state_before: Active source path, or ``None`` after termination.
    :param state_after: Active final path, or ``None`` after termination.
    :param decisions: Actual checks, in observation order, including skipped edges.
    :param roles: Final model variable roles after import assembly.
    :param input_events: Normalized events supplied to this cycle; empty for no-op.
    :param inputs: Frozen cycle inputs; ``None`` for an ignored, unsampled call.
    :param parameters: Immutable instance parameter snapshot.
    :param vars_before: Persistent control/output values before the call.
    :param vars_after: Persistent control/output values committed by the call.

    Example::

        >>> report = CycleDiagnostics(0, 'noop', None, None)
        >>> print(report)
        Cycle 0: noop; (terminated) -> (terminated)
        Result: call ignored; no new inputs sampled and no cycle advanced.
        Events: (none processed)
        Inputs: (not sampled)
        Parameters: {}
        Persistent values before: {}
        Persistent values after:  {}
        Committed micro-transitions: (none)
        No candidate checks recorded.
        >>> report.to_dict()['decisions']
        []
    """

    cycle_count: int
    outcome: str
    state_before: Optional[Tuple[str, ...]]
    state_after: Optional[Tuple[str, ...]]
    decisions: Tuple[TransitionDecision, ...] = ()
    roles: Mapping[str, str] = field(default_factory=dict)
    input_events: Tuple[str, ...] = ()
    inputs: Optional[Mapping[str, Number]] = None
    parameters: Mapping[str, Number] = field(default_factory=dict)
    vars_before: Mapping[str, Number] = field(default_factory=dict)
    vars_after: Mapping[str, Number] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(self, "input_events", tuple(self.input_events))
        for name in ("roles", "parameters", "vars_before", "vars_after"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        if self.inputs is not None:
            object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))
        for name in ("state_before", "state_after"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, tuple(value))

    def to_dict(self) -> dict:
        """Return a complete detached payload without presentation folding."""
        return {
            "cycle_count": self.cycle_count,
            "outcome": self.outcome,
            "state_before": list(self.state_before)
            if self.state_before is not None
            else None,
            "state_after": list(self.state_after)
            if self.state_after is not None
            else None,
            "roles": dict(self.roles),
            "input_events": list(self.input_events),
            "inputs": dict(self.inputs) if self.inputs is not None else None,
            "parameters": dict(self.parameters),
            "vars_before": dict(self.vars_before),
            "vars_after": dict(self.vars_after),
            "decisions": [decision.to_dict() for decision in self.decisions],
        }

    def __str__(self) -> str:
        return self.to_text()

    def to_text(
        self,
        *,
        transition: Optional[str] = None,
        check_id: Optional[Union[int, str]] = None,
        verbose: bool = False,
    ) -> str:
        """Explain the committed boundary and captured checks without reexecution.

        :param transition: Exact expanded transition label. Includes its checks,
            their descendants, ancestors and selections that blocked them.
        :param check_id: A report-local check number (integer or decimal string),
            mutually exclusive with ``transition``. Includes the same context.
        :param verbose: Show every check, expanded labels, full snapshots and
            source spans. Compact text folds only adjacent identical uncommitted
            evidence, naming every folded ID. Committed occurrences never fold.
        :return: Plain text; unknown selectors say there is no recorded evidence.
        :rtype: str
        """
        if transition is not None and check_id is not None:
            raise ValueError("Select either transition or check_id, not both.")
        before = (
            ".".join(self.state_before)
            if self.state_before is not None
            else "(terminated)"
        )
        after = (
            ".".join(self.state_after)
            if self.state_after is not None
            else "(terminated)"
        )
        explanations = {
            "cycle": "cycle committed.",
            "delta": "no stoppable successor committed; state and persistent values unchanged; cycle and inputs advanced.",
            "terminated": "cycle committed and the machine terminated.",
            "noop": "call ignored; no new inputs sampled and no cycle advanced.",
        }
        lines = [
            "Cycle %s: %s; %s -> %s" % (self.cycle_count, self.outcome, before, after),
            "Result: " + explanations[self.outcome],
            "Events: " + (", ".join(self.input_events) or "(none processed)"),
            "Inputs: "
            + (
                _format_values(self.inputs)
                if self.inputs is not None
                else "(not sampled)"
            ),
            "Parameters: " + _format_values(self.parameters),
            "Persistent values before: " + _format_values(self.vars_before),
            "Persistent values after:  " + _format_values(self.vars_after),
        ]
        committed = [d for d in self.decisions if d.committed]
        if committed:
            lines.append("Committed micro-transitions (in execution order):")
            lines.extend("  #%s %s" % (d.id, _decision_name(d)) for d in committed)
        else:
            lines.append("Committed micro-transitions: (none)")
        decisions = self._select_decisions(transition, check_id)
        if not decisions:
            selector = transition if transition is not None else check_id
            lines.append(
                "No recorded evidence for %s." % selector
                if selector is not None
                else "No candidate checks recorded."
            )
            return "\n".join(lines)
        lines.append(
            "Candidate evidence (parent links describe validation, not execution order):"
        )
        groups = []
        previous_key = None
        for decision in decisions:
            # Equality includes every evidence field except the observation ID.
            # Only adjacent duplicates can fold; chronology and values survive.
            key = tuple(
                getattr(decision, f.name) for f in fields(decision) if f.name != "id"
            )
            if not verbose and not decision.committed and key == previous_key:
                groups[-1].append(decision)
            else:
                groups.append([decision])
            previous_key = key
        depths = {}
        for group in groups:
            decision = group[0]
            depth = depths.get(decision.parent_id, -1) + 1
            for item in group:
                depths[item.id] = depth
            entry = _decision_text(decision, verbose)
            if len(group) > 1:
                entry.append(
                    "  Identical adjacent checks folded: %s (%s checks)."
                    % (", ".join("#%s" % item.id for item in group), len(group))
                )
            lines.extend("  " * depth + line for line in entry)
        return "\n".join(lines)

    def _select_decisions(self, transition, check_id):
        """Retain query context without including unrelated siblings."""
        if transition is None and check_id is None:
            return self.decisions
        selected = set()
        for decision in self.decisions:
            if (
                decision.transition_label == transition
                or str(decision.id) == str(check_id)
                or decision.parent_id in selected
            ):
                selected.add(decision.id)
        by_id = {d.id: d for d in self.decisions}
        pending = list(selected)
        while pending:
            decision = by_id[pending.pop()]
            for related in (decision.parent_id, decision.blocked_by):
                if related is not None and related not in selected:
                    selected.add(related)
                    pending.append(related)
        return tuple(d for d in self.decisions if d.id in selected)


def _decision_name(decision):
    """Prefer authored combo paths without guessing from generated names."""
    if not decision.combo_origins:
        return decision.transition_label
    descriptions = []
    for origin in decision.combo_origins:
        descriptions.append(
            "%s -> %s [combo: %s] (term %s: %s; %s)"
            % (
                origin["source_path"],
                origin["target_path"],
                origin["trigger"],
                origin["term_index"] + 1,
                origin["term_text"],
                origin["role"],
            )
        )
    return ("Shared expanded edge for: " if len(descriptions) > 1 else "") + " | ".join(
        descriptions
    )


def _decision_text(decision, verbose):
    """Render facts without inventing a unique failure cause for a search tree."""
    explanations = {
        "event_missing": "required event missing; guard not evaluated",
        "guard_false": "guard failed; candidate not selected",
        "successor_rejected": "successor validation failed; this candidate's speculative writes were not committed",
        "selected": "selected in this phase; not committed",
        "enabled": "local conditions passed during search; not proof of a committed path",
        "not_evaluated": "not evaluated because a prior candidate was selected",
    }
    status = "committed" if decision.committed else explanations[decision.outcome]
    lines = [
        "#%s %s [%s] %s: %s"
        % (
            decision.id,
            _decision_name(decision),
            decision.phase,
            decision.outcome,
            status,
        )
    ]
    if verbose and decision.combo_origins:
        lines.append("  Expanded edge: " + decision.transition_label)
    if decision.event is not None:
        event_status = {True: "present", False: "missing", None: "not evaluated"}[
            decision.event_result
        ]
        lines.append("  Event %s: %s" % (decision.event, event_status))
    elif verbose:
        lines.append("  Event: no event requirement")
    if decision.guard is not None:
        guard_status = {True: "passed", False: "failed", None: "not evaluated"}[
            decision.guard_result
        ]
        values = {**decision.parameters, **decision.inputs, **decision.vars}
        referenced = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", decision.guard))
        relevant = {name: value for name, value in values.items() if name in referenced}
        lines.append(
            "  Guard %s: %s; values=%s"
            % (decision.guard, guard_status, _format_values(relevant))
        )
    elif verbose:
        lines.append("  Guard: no guard requirement")
    if decision.blocked_by is not None:
        lines.append("  Not evaluated after selection #%s." % decision.blocked_by)
    if decision.parent_id is not None:
        lines.append("  Checked while validating candidate #%s." % decision.parent_id)
    if verbose:
        successor = {True: "accepted", False: "rejected", None: "not requested"}[
            decision.successor_result
        ]
        lines.append("  Successor validation: %s." % successor)
    if verbose or decision.outcome == "guard_false":
        lines.append(
            "  Values at check (not final values): vars=%s; inputs=%s; parameters=%s"
            % (
                _format_values(decision.vars),
                _format_values(decision.inputs),
                _format_values(decision.parameters),
            )
        )
    if decision.location:
        location = decision.location
        lines.append(
            "  source=%s"
            % (
                dict(location)
                if verbose
                else "%s:%s:%s"
                % (
                    location.get("path", "<text>"),
                    location.get("line", "?"),
                    location.get("column", "?"),
                )
            )
        )
    return lines


class _DecisionCollector:
    """Call-local mutable collection; frozen only when the cycle returns."""

    def __init__(self, runtime, input_events=(), inputs=None):
        self.phase = "preflight"
        self.parent = None
        self.records = []
        self.roles = {
            name: define.role.value
            for name, define in runtime.state_machine.defines.items()
        }
        self.before = tuple(runtime.stack[-1].state.path) if runtime.stack else None
        self.vars_before = dict(runtime.vars)
        self.input_events = tuple(input_events)
        self.inputs = inputs
        self.parameters = dict(runtime.parameters)
        terms = {}
        for state in runtime.state_machine.walk_states():
            for transition in state.transitions:
                for ref in transition.combo_origin_refs:
                    terms.setdefault(ref.origin_id, {})[ref.term_index] = ref.term_text
        self.triggers = {
            origin: " + ".join(parts[index] for index in sorted(parts))
            for origin, parts in terms.items()
        }

    def start(self, state, transition, vars_, inputs, parameters, *, search=False):
        span = getattr(transition, "_span", None)
        location = {}
        if span is not None:
            location.update(
                {item.name: getattr(span, item.name) for item in fields(span)}
            )
        path = getattr(transition, "_source_path", None)
        if path is not None:
            location["path"] = path
        record = dict(
            id=len(self.records) + 1,
            parent_id=self.parent,
            transition_label=_transition_label(state, transition),
            phase="validation" if self.parent is not None or search else self.phase,
            state_path=state.path,
            event=transition.event.path_name if transition.event is not None else None,
            guard=str(transition.guard) if transition.guard is not None else None,
            vars=dict(vars_),
            inputs=dict(inputs),
            parameters=dict(parameters),
            location=location,
            combo_origins=tuple(
                {
                    "origin_id": ref.origin_id,
                    "source_path": ref.source_path
                    or (ref.selection_owner_path + ".[*]"),
                    "target_path": ref.target_path,
                    "trigger": self.triggers[ref.origin_id],
                    "term_index": ref.term_index,
                    "term_text": ref.term_text,
                    "role": ref.role,
                    "consumes_term": ref.consumes_term,
                }
                for ref in transition.combo_origin_refs
            ),
        )
        self.records.append(record)
        return record

    def finish(self, cycle_count, outcome, state_after, vars_after=None):
        decisions = []
        for record in self.records:
            committed = (
                outcome != "delta"
                and record["phase"] == "execution"
                and record["outcome"] == "selected"
            )
            decisions.append(TransitionDecision(**record, committed=committed))
        return CycleDiagnostics(
            cycle_count,
            outcome,
            self.before,
            state_after,
            tuple(decisions),
            self.roles,
            self.input_events,
            self.inputs,
            self.parameters,
            self.vars_before,
            self.vars_before if vars_after is None else vars_after,
        )
