"""
The deterministic builder that turns a minimal core into a checked proof graph.

The search is a bounded closure: it starts from the facts the core members state,
proposes every rule application those facts allow, keeps the ones the checker
agrees with, and stops at the first verified contradiction.  What makes the result
publishable is not that it found something but that the search is pinned down --
the candidate universe is finite, the orderings are total, equal conclusions share
a node, and whatever the contradiction does not rest on is removed before anything
is published.

The module contains:
* :func:`build_domain_proof` - the closure, pruning and integrity pass

Nothing here decides *whether* a step is sound; that is
:mod:`pyfcstm.bmc.proof_rules`.  Keeping proposal and checking apart is what lets
the checker be used as an independent oracle over a graph this module produced.

.. note::
   Determinism is a published property, not an implementation detail: two users on
   the same input must read the same proof.  Every iteration order below is over a
   sorted sequence for that reason, never over a set or a dict.

Example::

    >>> from pyfcstm.bmc.solver import _SolveBudget
    >>> inputs = (
    ...     ("assumption.0000",
    ...      {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 0}),
    ...     ("assumption.0001",
    ...      {"kind": "variable_equality", "variable": "x", "frame": 0, "value": 1}),
    ... )
    >>> proof, record = build_domain_proof(
    ...     "assumptions_component", inputs, _SolveBudget(None)
    ... )
    >>> proof.verification_status
    'verified'
"""

import itertools
import json
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .explanation import (
    BmcConflictProof,
    BmcProofNode,
    _STATE_SLOT_SUBJECT,
    _fact_sentence,
)
from .proof_rules import PROOF_RULES, RuleApplication, check_rule

__all__ = ["build_domain_proof", "proof_facts_for_core"]

#: What the ledger calls this phase.
_PHASE_NAME = "proof_construction"

#: How many rule applications one search may check.
#:
#: The candidate universe is already finite -- rules only read facts derived from
#: the core, and the one rule that produces values is bounded by the expressions the
#: core mentions -- so this is a backstop against a rule added later that is not,
#: rather than a semantic limit.  Reaching it is reported as ``unsupported``, never
#: as a proof.
_MAX_APPLICATIONS = 4096


def _canonical(fact: Mapping[str, Any]) -> str:
    """Return the structural key two equal facts share.

    Sorting the keys is what makes the key structural rather than a record of the
    order a mapping happened to be built in.

    :param fact: A domain fact.
    :type fact: Mapping[str, object]
    :return: A stable string identifying this fact's content.
    :rtype: str

    Example::

        >>> _canonical({"b": 2, "a": 1}) == _canonical({"a": 1, "b": 2})
        True
    """
    return json.dumps(fact, sort_keys=True, default=str)


class _Node:
    """One entry of the closure, before it becomes a published node."""

    def __init__(self, index, kind, rule_id, premises, fact, item_ids):
        self.index = index
        self.kind = kind
        self.rule_id = rule_id
        self.premises = tuple(premises)
        self.fact = fact
        self.item_ids = tuple(item_ids)

    @property
    def stable_id(self) -> str:
        """The published id, which encodes position rather than content."""
        return "proof.%s.%04d" % (
            "input" if self.kind == "input" else "step",
            self.index,
        )


def _record(status: str, started: bool, elapsed: float, reason: Optional[str]):
    """Build the ledger entry for this phase."""
    from .infeasibility import ProbeRecord

    return ProbeRecord(_PHASE_NAME, status, started, elapsed, reason)


def _candidates(nodes: Sequence[_Node]) -> List[Tuple[str, Tuple[int, ...]]]:
    """Enumerate every rule application the current facts allow, in a total order.

    Ordering by rule id first and then by premise indices makes the search itself
    deterministic: whichever contradiction is reached first is the same one on every
    run, so "the first verified false" names one graph rather than any of several.

    :param nodes: The closure so far, in insertion order.
    :type nodes: Sequence[_Node]
    :return: Rule id and premise indices for each candidate.
    :rtype: List[Tuple[str, Tuple[int, ...]]]
    """
    proposals = []
    for rule_id in sorted(PROOF_RULES):
        if rule_id == "source_fact":
            # Inputs are seeded rather than derived; nothing proposes them.
            continue
        if rule_id in _VARIADIC_RULES:
            # One rule reads as many exclusions as the frame has states, so its
            # arity is a property of the input rather than of the rule.  Offering
            # every subset would be exponential; offering the facts that share a
            # frame is what the rule can actually use.
            for combination in _frame_groups(nodes):
                proposals.append((rule_id, combination))
            continue
        wanted = sorted(PROOF_RULES[rule_id].premise_kinds)
        if not wanted:
            continue
        for combination in itertools.permutations(range(len(nodes)), len(wanted)):
            # Match the tags before proposing.  ``premise_kinds`` exists for this --
            # a rule that reads two bounds cannot be applied to a domain and an
            # exclusion, and offering it anyway spends a check to learn that.  With
            # the tags ignored, four rules concluding ``false`` each burned n(n-1)
            # checks on pairs they could never read, and a frame with 32 legal
            # states exhausted the application limit before the one rule that could
            # close it was proposed even once.
            if sorted(nodes[index].fact.get("kind") for index in combination) != wanted:
                continue
            proposals.append((rule_id, combination))
    proposals.sort()
    return proposals


#: Rules whose premise count follows the input rather than the rule.
_VARIADIC_RULES = frozenset({"state_domain_exhaustion"})


def _frame_groups(nodes: Sequence[_Node]) -> List[Tuple[int, ...]]:
    """Group node indices by the frame their fact is about.

    A variadic rule reads every fact at one frame, so the groups are the candidate
    premise sets.  Sorted by frame and then by index, so the enumeration is total.

    :param nodes: The closure so far.
    :type nodes: Sequence[_Node]
    :return: One index tuple per frame, in frame order.
    :rtype: List[Tuple[int, ...]]
    """
    grouped: Dict[Any, List[int]] = {}
    for index, node in enumerate(nodes):
        frame = node.fact.get("frame")
        if frame is not None:
            grouped.setdefault(frame, []).append(index)
    return [tuple(sorted(grouped[frame])) for frame in sorted(grouped, key=repr)]


def build_domain_proof(
    scope: str,
    inputs: Sequence[Tuple[str, Mapping[str, Any]]],
    budget,
    member_ids: Optional[Sequence[str]] = None,
    state_names: Optional[Mapping[int, str]] = None,
) -> Tuple[Optional[BmcConflictProof], Any]:
    """Search for a checked proof that these facts admit no execution.

    The search saturates: it proposes applications over the facts it has, keeps the
    checked ones, and repeats until a contradiction is verified or nothing new can
    be derived.  A fixed point without a contradiction is an answer -- the rule
    catalog does not cover this shape -- and it publishes nothing, because a partial
    graph would claim a verification that did not happen.

    A proof is published only when every core member takes part in it.  A member the
    contradiction does not rest on would be named among the reasons while playing no
    part, so its presence means this core has no proof rather than a smaller one.

    :param scope: Diagnostic scope the proof will discharge.
    :type scope: str
    :param inputs: Core member ids paired with the fact each states.
    :type inputs: Sequence[Tuple[str, Mapping[str, object]]]
    :param budget: The shared solve budget; the search stops when it runs out.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :param member_ids: Every core member, including ones no fact was read from.
        Coverage is judged against these rather than against ``inputs``: a member
        whose fact could not be translated is absent from ``inputs`` entirely, and
        judging coverage there would let the proof close over a core it never saw
        all of.  Defaults to the ids present in ``inputs``.
    :type member_ids: Optional[Sequence[str]], optional
    :param state_names: What the model calls each state, keyed by encoded index, so
        each node's own sentence names the state the author wrote.  A node's sentence
        and the reading built from it are shown to the same reader, so both resolve
        states through the same table; without one, both fall back to the index.
        Defaults to ``None``.
    :type state_names: Optional[Mapping[int, str]], optional
    :return: The proof and the ledger entry, or ``None`` and the entry.
    :rtype: Tuple[Optional[BmcConflictProof], pyfcstm.bmc.infeasibility.ProbeRecord]

    Example::

        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> proof, record = build_domain_proof("assumptions_component", (), _SolveBudget(None))
        >>> proof is None and record.status
        'unknown'
    """
    started_at = time.monotonic()

    def elapsed() -> float:
        return (time.monotonic() - started_at) * 1000.0

    def exhausted() -> bool:
        # An unbounded budget has no deadline; a finite one is spent once its
        # deadline has passed.  The two are different answers and stay apart.
        return budget.deadline is not None and time.monotonic() >= budget.deadline

    # Sorted by core stable id, so the graph does not inherit the order a caller
    # happened to collect the members in.
    ordered = sorted(inputs, key=lambda pair: pair[0])
    nodes: List[_Node] = []
    seen: Dict[str, int] = {}
    for stable_id, fact in ordered:
        key = _canonical(fact)
        if key in seen:
            # An input node stands for one core member, so two members stating the
            # same fact have nowhere to go: merging them would give one node two
            # attributions, and dropping one would leave a member unread.  The
            # contract answers this directly -- a duplicate input fails closed -- and
            # a subset-minimal core should not contain one in the first place, since
            # either member alone would do.  Refusing says so instead of quietly
            # producing a shape the published invariants forbid.
            return None, _record(
                "unknown",
                True,
                elapsed(),
                "two core members state the same fact: %s and %s"
                % (nodes[seen[key]].item_ids[0], stable_id),
            )
        seen[key] = len(nodes)
        nodes.append(_Node(len(nodes), "input", "source_fact", (), fact, (stable_id,)))

    if not nodes:
        return None, _record(
            "unknown", True, elapsed(), "no core member states a domain fact."
        )

    contradiction: Optional[int] = None
    checked = 0
    while contradiction is None:
        if exhausted():
            return None, _record(
                "timeout", True, elapsed(), "budget exhausted during proof search."
            )
        grew = False
        for rule_id, premise_indices in _candidates(nodes):
            if checked >= _MAX_APPLICATIONS:
                return None, _record(
                    "unknown",
                    True,
                    elapsed(),
                    "proof search reached its application limit.",
                )
            if exhausted():
                return None, _record(
                    "timeout", True, elapsed(), "budget exhausted during proof search."
                )
            premises = [nodes[index] for index in premise_indices]
            conclusion = _conclusion_for(rule_id, premises)
            if conclusion is None:
                continue
            key = _canonical(conclusion)
            if key in seen:
                continue
            checked += 1
            if not check_rule(
                RuleApplication(
                    rule_id, tuple(node.fact for node in premises), conclusion
                )
            ):
                continue
            item_ids = sorted({item for node in premises for item in node.item_ids})
            index = len(nodes)
            seen[key] = index
            kind = "contradiction" if conclusion.get("kind") == "false" else "derived"
            nodes.append(
                _Node(index, kind, rule_id, premise_indices, conclusion, item_ids)
            )
            grew = True
            if kind == "contradiction":
                contradiction = index
                break
        if not grew:
            # A fixed point with no contradiction: every application the catalog
            # allows has been checked and none closed the case.
            return None, _record(
                "unknown",
                True,
                elapsed(),
                "no rule in the catalog closes this core.",
            )

    # Walk backwards from the contradiction; whatever is not reached took no part.
    used, pending = set(), [contradiction]
    while pending:
        current = pending.pop()
        if current in used:
            continue
        used.add(current)
        pending.extend(nodes[current].premises)

    covered = {item for index in used for item in nodes[index].item_ids}
    stated = (
        set(member_ids)
        if member_ids is not None
        else {stable_id for stable_id, _ in ordered}
    )
    if covered != stated:
        # The contradiction rests on part of the core.  A proof over a subset would
        # cite the rest among its reasons without using them.
        return None, _record(
            "unknown",
            True,
            elapsed(),
            "the contradiction does not rest on every core member.",
        )

    kept = sorted(used)
    renumbered = {old: new for new, old in enumerate(kept)}
    published = []
    for old in kept:
        node = nodes[old]
        published.append(
            BmcProofNode(
                _published_id(node, renumbered[old]),
                node.kind,
                node.rule_id,
                tuple(
                    _published_id(nodes[index], renumbered[index])
                    for index in sorted(node.premises, key=lambda i: renumbered[i])
                ),
                node.fact,
                node.item_ids,
                _fact_sentence(node.fact, state_names),
                "core_binding" if node.kind == "input" else "rule_checker",
            )
        )
    proof = BmcConflictProof(
        scope,
        published[-1].stable_id,
        tuple(published),
        "subset_minimal",
        "dependency_pruned",
        "verified",
    )
    return proof, _record("complete", True, elapsed(), None)


def _published_id(node: _Node, position: int) -> str:
    """Return the id a node carries once the graph is pruned and renumbered.

    Ids encode position in the published order rather than position in the search,
    so pruning a step does not leave a gap for a reader to wonder about.
    """
    return "proof.%s.%04d" % ("input" if node.kind == "input" else "step", position)


def _inherit_subject(
    conclusion: Dict[str, Any], source: Mapping[str, Any]
) -> Dict[str, Any]:
    """Carry the subject's kind from the fact a conclusion is derived from.

    The proposal has to offer what the checker will accept, and the checker requires
    a derivation to keep talking about the same kind of subject.  A variable simply
    omits the field, so the flag is only written when it is true -- an explicit
    ``False`` would be a second spelling of "not a state slot" for every consumer to
    handle.
    """
    if source.get("state_slot"):
        conclusion["state_slot"] = True
    return conclusion


def _conclusion_for(
    rule_id: str, premises: Sequence[_Node]
) -> Optional[Mapping[str, Any]]:
    """Propose what a rule would conclude from these premises, or ``None``.

    This is the proposal half of the search: it is allowed to be optimistic, since
    the checker decides.  What it may not do is invent a term the core does not
    mention -- every value it proposes is computed from facts already present, which
    is what keeps the candidate universe finite.

    :param rule_id: The rule being proposed.
    :type rule_id: str
    :param premises: The nodes it would read.
    :type premises: Sequence[_Node]
    :return: The proposed conclusion, or ``None`` when the shapes do not fit.
    :rtype: Optional[Mapping[str, object]]
    """
    facts = [node.fact for node in premises]
    if rule_id in (
        "incompatible_equalities",
        "interval_intersection",
        "state_domain_exhaustion",
        "definedness_failure",
        "boolean_complement",
    ):
        return {"kind": "false"}
    if rule_id == "transition_assignment":
        if len(facts) != 2:
            return None
        cases = [fact for fact in facts if fact.get("kind") == "transition_case"]
        if len(cases) != 1:
            return None
        case = cases[0]
        # Carried forward whole.  Listing the fields to copy is what let three
        # rounds of the same defect through: a field the list forgot vanished from
        # the proposal and from the checker's expectation alike, so the two agreed
        # and the fact quietly lost part of itself.
        return dict(case, kind="arithmetic_expression")
    if rule_id == "equality_substitution":
        if len(facts) != 2:
            return None
        value_fact, expression = facts
        if value_fact.get("kind") != "variable_equality":
            return None
        if expression.get("kind") != "arithmetic_expression":
            return None
        if not expression.get("operand_variable"):
            return None
        # The operand's name goes because this step has just replaced it; whatever
        # else the expression says is unchanged.
        substituted = dict(expression, operand=value_fact.get("value"))
        substituted.pop("operand_variable", None)
        return substituted
    if rule_id == "arithmetic_evaluation":
        if len(facts) != 2:
            return None
        value_fact, expression = facts
        if value_fact.get("kind") != "variable_equality":
            return None
        if expression.get("kind") != "arithmetic_expression":
            return None
        from .proof_rules import _evaluate

        result = _evaluate(
            expression.get("operator"),
            value_fact.get("value"),
            expression.get("operand"),
        )
        if result is None:
            return None
        return _inherit_subject(
            {
                "kind": "variable_equality",
                "variable": expression.get("variable"),
                "frame": expression.get("target_frame"),
                "value": result,
            },
            expression,
        )
    return None


#: How a published comparison operator reads as a proof fact.
#:
#: The core states one tag for every comparison and carries the operator beside it;
#: the rules read an equality and a bound as different things, because an equality
#: pins a value and a bound restricts a range.  Splitting here rather than widening
#: the rules keeps each rule's premise shape exactly what its side condition needs.
_COMPARISON_FACTS = {
    "eq": "variable_equality",
    "ge": "variable_bound",
    "gt": "variable_bound",
    "le": "variable_bound",
    "lt": "variable_bound",
}


def proof_facts_for_core(items) -> Tuple[Tuple[str, Mapping[str, Any]], ...]:
    """Translate published core members into the facts the rules read.

    The published vocabulary describes a core for a reader; the rule vocabulary
    describes premises for a checker.  They overlap without matching, so this is
    where one becomes the other -- and a member the rules have no reading for is
    dropped rather than guessed at, which makes the core incompletely covered and
    the proof unpublishable.  That is the intended outcome: a proof resting on a
    fact nobody could check is what the tier exists to refuse.

    :param items: Published core members.
    :type items: Iterable[BmcCoreItem]
    :return: Member ids paired with the fact each states, for readable members.
    :rtype: Tuple[Tuple[str, Mapping[str, object]], ...]

    Example::

        >>> proof_facts_for_core(())
        ()
    """
    translated = []
    for item in items:
        fact = item.normalized_fact
        stable_id = item.constraint.stable_id
        kind = fact.get("kind")
        if kind == "variable_comparison":
            operator = fact.get("operator")
            target = _COMPARISON_FACTS.get(operator)
            if target is None:
                # ``ne`` restricts nothing the rules can intersect, so there is no
                # premise shape for it and the member stays untranslated.
                continue
            if target == "variable_equality":
                translated.append(
                    (
                        stable_id,
                        {
                            "kind": target,
                            "variable": fact.get("variable"),
                            "frame": fact.get("frame"),
                            "value": fact.get("value"),
                        },
                    )
                )
            else:
                translated.append(
                    (
                        stable_id,
                        {
                            "kind": target,
                            "variable": fact.get("variable"),
                            "frame": fact.get("frame"),
                            "operator": operator,
                            "value": fact.get("value"),
                        },
                    )
                )
        elif kind == "state_domain":
            translated.append(
                (
                    stable_id,
                    {
                        "kind": "state_domain",
                        "frame": fact.get("frame"),
                        "states": list(fact.get("states") or ()),
                    },
                )
            )
        elif kind == "definedness_condition":
            variable = fact.get("variable")
            # Only division translates.  The rule reads a guard as one forbidden
            # value, and that is what a divisor's domain is: every value but zero.
            # A square root excludes a half-line rather than a point, so the rule's
            # shape does not fit it -- writing one anyway would produce a fact
            # weaker than the group it stands for, which the binding check refuses
            # in both directions.  Leaving it untranslated reaches the same refusal
            # sooner and says why.
            if variable is None or fact.get("operation") != "division":
                continue
            translated.append(
                (
                    stable_id,
                    {
                        "kind": "definedness_guard",
                        "variable": variable,
                        "frame": fact.get("frame"),
                        "operation": "division",
                        "forbidden": 0,
                    },
                )
            )
        elif kind == "transition_case":
            # ``operation`` is the published name and ``operator`` the rule's own;
            # the boundary is the contract's, so this is where one becomes the other.
            # Everything else travels unchanged, including the condition: a rule
            # reading a case without it would treat a conditional assignment as
            # unconditional, which is the one claim the group does not make.
            translated.append(
                (
                    stable_id,
                    dict(
                        {
                            key: value
                            for key, value in fact.items()
                            if key
                            in (
                                "variable",
                                "frame",
                                "target_frame",
                                "operand",
                                "operand_variable",
                                "condition",
                            )
                        },
                        kind="transition_case",
                        operator=fact.get("operation"),
                    ),
                )
            )
        elif kind == "state_membership":
            if fact.get("excluded"):
                translated.append(
                    (
                        stable_id,
                        {
                            "kind": "state_exclusion",
                            "frame": fact.get("frame"),
                            "state": fact.get("state"),
                        },
                    )
                )
            else:
                # A frame holds one state, so a requirement on its slot is an
                # equality like any other -- read as one, the rule that refuses two
                # values for a slot refuses two states for a frame, with no second
                # rule for the state case.
                #
                # The subject is named rather than left absent.  Every rule compares
                # the slot before it compares values, and a fact with no subject
                # would have to be tolerated there -- which is the fail-open shape
                # this tier spent three rounds removing.  The name does not have to
                # be one a model cannot declare: ``state_slot`` is what the slot
                # comparison, the binding and the reading go by, so a model with a
                # variable of the same name is just a model with that variable.
                translated.append(
                    (
                        stable_id,
                        {
                            "kind": "variable_equality",
                            "variable": _STATE_SLOT_SUBJECT,
                            "state_slot": True,
                            "frame": fact.get("frame"),
                            "value": fact.get("state"),
                        },
                    )
                )
    return tuple(translated)
