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

    def __post_init__(self):
        for name in ("vars", "inputs", "parameters", "location"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, "state_path", tuple(self.state_path))

    def to_dict(self) -> dict:
        """Return independent JSON-compatible data, including unevaluated checks."""
        data = {item.name: getattr(self, item.name) for item in fields(self)}
        for name in ("vars", "inputs", "parameters", "location"):
            data[name] = dict(data[name])
        data["state_path"] = list(self.state_path)
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

    Example::

        >>> report = CycleDiagnostics(0, 'noop', None, None)
        >>> print(report)
        Cycle 0: noop; (terminated) -> (terminated)
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

    def __post_init__(self):
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(self, "roles", MappingProxyType(dict(self.roles)))
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
            "decisions": [decision.to_dict() for decision in self.decisions],
        }

    def __str__(self) -> str:
        return self.to_text()

    def to_text(
        self, *, transition: Optional[str] = None, verbose: bool = False
    ) -> str:
        """Format captured evidence without running the model again.

        :param transition: Optional exact transition label. Includes checks made
            while validating its successors. No matching record yields an
            explicit no-evidence message, not a claim that the source was inactive.
        :param verbose: Include every check, its parent, location and full values.
            The compact view groups equal label/phase/outcome summaries and shows
            guard-referenced values. Both views retain validation outcomes.
        :return: Plain text, with no ANSI sequences.
        :rtype: str
        """
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
        lines = [
            "Cycle %s: %s; %s -> %s" % (self.cycle_count, self.outcome, before, after)
        ]
        selected = set()
        decisions = []
        for decision in self.decisions:
            if (
                transition is None
                or decision.transition_label == transition
                or decision.parent_id in selected
            ):
                selected.add(decision.id)
                decisions.append(decision)
        if not decisions:
            lines.append(
                "No recorded evidence for %s." % transition
                if transition is not None
                else "No candidate checks recorded."
            )
            return "\n".join(lines)
        seen = set()
        depths = {}
        folded = 0
        for decision in decisions:
            depth = depths.get(decision.parent_id, -1) + 1
            depths[decision.id] = depth
            line_start = len(lines)
            key = (
                decision.transition_label,
                decision.phase,
                decision.outcome,
                decision.committed,
            )
            if not verbose and key in seen:
                folded += 1
                continue
            seen.add(key)
            lines.append(
                "#%s %s [%s] %s%s"
                % (
                    decision.id,
                    decision.transition_label,
                    decision.phase,
                    decision.outcome,
                    "; committed" if decision.committed else "",
                )
            )
            if decision.event is not None:
                lines.append(
                    "  event %s -> %s" % (decision.event, decision.event_result)
                )
            if decision.guard is not None:
                values = {**decision.parameters, **decision.inputs, **decision.vars}
                # Model identifiers are tokens; substring matches would confuse x and xx.
                referenced = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", decision.guard))
                relevant = {
                    name: value for name, value in values.items() if name in referenced
                }
                lines.append(
                    "  guard %s -> %s; values=%s"
                    % (decision.guard, decision.guard_result, _format_values(relevant))
                )
            if decision.blocked_by is not None:
                lines.append(
                    "  not evaluated after selection #%s" % decision.blocked_by
                )
            if verbose:
                lines.append(
                    "  parent=%s; event=%s -> %s; successor=%s"
                    % (
                        decision.parent_id,
                        decision.event,
                        decision.event_result,
                        decision.successor_result,
                    )
                )
                lines.append(
                    "  vars=%s; inputs=%s; parameters=%s"
                    % (
                        _format_values(decision.vars),
                        _format_values(decision.inputs),
                        _format_values(decision.parameters),
                    )
                )
                if decision.location:
                    lines.append("  source=%s" % dict(decision.location))
                lines[line_start:] = [
                    "  " * depth + line for line in lines[line_start:]
                ]
        if folded:
            lines.append(
                "%s repeated summaries folded; use verbose=True for every check."
                % folded
            )
        return "\n".join(lines)


class _DecisionCollector:
    """Call-local mutable collection; frozen only when the cycle returns."""

    def __init__(self, runtime):
        self.phase = "preflight"
        self.parent = None
        self.records = []
        self.roles = {
            name: define.role.value
            for name, define in runtime.state_machine.defines.items()
        }
        self.before = tuple(runtime.stack[-1].state.path) if runtime.stack else None

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
        )
        self.records.append(record)
        return record

    def finish(self, cycle_count, outcome, state_after):
        decisions = []
        for record in self.records:
            committed = (
                outcome != "delta"
                and record["phase"] == "execution"
                and record["outcome"] == "selected"
            )
            decisions.append(TransitionDecision(**record, committed=committed))
        return CycleDiagnostics(
            cycle_count, outcome, self.before, state_after, tuple(decisions), self.roles
        )
