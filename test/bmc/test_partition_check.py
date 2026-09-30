"""Source partition self-check on large nested priority partitions.

These tests pin the scaling contract of :func:`verify_source_partition`: a
partition whose truth table exceeds ``max_assignments`` is still decided
exactly -- by its priority-tree shape when the builder produced one, and by a
symbolic check otherwise -- instead of being rejected for its size.  The
differential test forces the large-partition path with ``max_assignments=1``
and compares every verdict with the truth-table path on the same buckets.
"""

from __future__ import annotations

import itertools
import random
from typing import List, Optional, Sequence, Tuple

import pytest

from pyfcstm.bmc import build_bmc_domain
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcEncoding
from pyfcstm.bmc.macro import BoolTemplate, CycleCase, verify_source_partition
from pyfcstm.bmc.source import MacroStepSource, entry_source, stable_leaf_source
from pyfcstm.model import load_state_machine_from_text


@pytest.fixture(scope="module")
def leaf_source() -> MacroStepSource:
    """Stable leaf source whose partition needs a fallback bucket."""
    domain = build_bmc_domain(load_state_machine_from_text("state Root;"), 1)
    return stable_leaf_source(domain, "Root")


@pytest.fixture(scope="module")
def plant_entry_source() -> MacroStepSource:
    """Entry source whose partition may close with an ordinary accepted case."""
    domain = build_bmc_domain(
        load_state_machine_from_text("state Root { state Idle; [*] -> Idle; }"), 1
    )
    return entry_source(domain, "Root")


def _accepted(label: str) -> BoolTemplate:
    return BoolTemplate.atom("accepted:" + label)


def _case(
    source: MacroStepSource, kind: str, ordinal: int, condition: BoolTemplate
) -> CycleCase:
    path = source.source_state_path
    return CycleCase(
        kind,
        source.source_state_id,
        path,
        source.source_state_id,
        path,
        "%s::%s::%s::%d" % (path, kind, path, ordinal),
        condition,
        (),
    )


def _fallback(source: MacroStepSource, accepted: Sequence[CycleCase]) -> CycleCase:
    return _case(
        source,
        "fallback",
        0,
        BoolTemplate.not_(
            BoolTemplate.or_(*[_accepted(case.label) for case in accepted])
        ),
    )


def priority_tree(
    source: MacroStepSource,
    fanouts: Sequence[int],
    literal=None,
) -> Tuple[List[CycleCase], List[List[BoolTemplate]]]:
    """
    Build accepted cases shaped like nested declaration-priority choosers.

    Every chooser tries its candidates in order; a leaf case holds the literals
    of its path and, at every level, excludes the cases reached through the
    earlier siblings of that level -- the shape macro expansion produces for
    nested initial transitions.  ``literal(node_index)`` returns the literal of
    one candidate node and defaults to a fresh event atom per node.
    """
    if literal is None:

        def literal(index):
            return BoolTemplate.atom("event:Root.E%d" % index)

    counter = [0]
    cases: List[CycleCase] = []
    masks: List[List[BoolTemplate]] = []

    def expand(depth, literals, exclusions):
        subtree = []
        for _ in range(fanouts[depth]):
            node = literal(counter[0])
            counter[0] += 1
            earlier = [_accepted(case.label) for case in subtree]
            mask = [BoolTemplate.not_(BoolTemplate.or_(*earlier))] if earlier else []
            if depth + 1 == len(fanouts):
                case = _case(
                    source,
                    "transition",
                    len(cases),
                    BoolTemplate.and_(*literals, node, *exclusions, *mask),
                )
                cases.append(case)
                masks.append(exclusions + mask)
                subtree.append(case)
            else:
                subtree.extend(expand(depth + 1, literals + [node], exclusions + mask))
        return subtree

    expand(0, [], [])
    return cases, masks


@pytest.mark.unittest
def test_nested_priority_tree_is_proved_without_enumeration(leaf_source):
    """A nested priority tree far beyond the truth-table budget is proved directly."""
    accepted, _ = priority_tree(leaf_source, (4, 3, 3))

    result = verify_source_partition(
        leaf_source, accepted + [_fallback(leaf_source, accepted)]
    )

    assert result.assignment_count == 0
    assert result.bucket_count == 37
    assert len(result.variables) == 4 + 12 + 36
    assert not any(name.startswith("accepted:") for name in result.variables)


@pytest.mark.unittest
def test_deep_nested_tree_with_hundreds_of_cases_is_proved(leaf_source):
    """Stress: 400 cases over 505 atoms, which a truth table could never enumerate."""
    accepted, _ = priority_tree(leaf_source, (5, 4, 4, 5))

    result = verify_source_partition(
        leaf_source, accepted + [_fallback(leaf_source, accepted)]
    )

    assert result.assignment_count == 0
    assert result.bucket_count == 401
    assert len(result.variables) == 5 + 20 + 80 + 400


@pytest.mark.unittest
def test_large_partition_violations_are_still_reported(leaf_source):
    """Past the truth-table budget the check still finds real gaps and overlaps."""
    accepted, _ = priority_tree(leaf_source, (4, 3, 3))

    with pytest.raises(
        BmcBuildError, match=r"partition violation: gap at assignment \{"
    ):
        verify_source_partition(leaf_source, accepted)

    # Drop the sibling mask of the second leaf: it now overlaps the first one.
    first, second = accepted[0], accepted[1]
    unmasked = _case(
        leaf_source,
        "transition",
        1,
        BoolTemplate.and_(
            *[
                operand
                for operand in second.condition.operands
                if not (
                    operand.kind == "not"
                    and operand.operands[0] == _accepted(first.label)
                )
            ]
        ),
    )
    overlapping = [first, unmasked] + accepted[2:]
    with pytest.raises(
        BmcBuildError,
        match=r"partition violation: overlap at assignment \{.*\}: \[0, 1\]",
    ):
        verify_source_partition(
            leaf_source, overlapping + [_fallback(leaf_source, overlapping)]
        )

    # A fallback that forgets one accepted case overlaps with it.
    partial = _fallback(leaf_source, accepted[1:])
    with pytest.raises(BmcBuildError, match="partition violation: overlap"):
        verify_source_partition(leaf_source, accepted + [partial])


def decision_list(source, size):
    """Bucket ``k`` holds when atom ``k`` is the first true atom; returns cases and the none-true condition."""
    atoms = [BoolTemplate.atom("event:Root.E%d" % index) for index in range(size)]
    cases = [
        _case(
            source,
            "transition",
            index,
            BoolTemplate.and_(
                atom, *[BoolTemplate.not_(item) for item in atoms[:index]]
            ),
        )
        for index, atom in enumerate(atoms)
    ]
    return cases, BoolTemplate.and_(*[BoolTemplate.not_(item) for item in atoms])


@pytest.mark.unittest
def test_large_partition_exact_check_accepts_valid_non_tree_shapes(plant_entry_source):
    """Valid partitions outside the tree shape are decided exactly, not refused."""
    source = plant_entry_source
    cases, none_true = decision_list(source, 20)
    cases.append(_case(source, "transition", 20, none_true))

    result = verify_source_partition(source, cases)

    assert result.assignment_count == 0
    assert result.bucket_count == 21
    assert len(result.variables) == 20


@pytest.mark.unittest
@pytest.mark.parametrize("size", [5, 20], ids=["truth-table", "symbolic"])
def test_build_diagnostics_form_one_extra_bucket(plant_entry_source, size):
    """Build diagnostics must fill the gap the cases leave, and never overlap them."""
    source = plant_entry_source
    cases, none_true = decision_list(source, size)

    result = verify_source_partition(
        source, cases, build_diagnostic_conditions=(none_true,)
    )
    assert result.bucket_count == size + 1

    with pytest.raises(
        BmcBuildError, match=r"overlap at assignment \{.*\}: \[0, %d\]" % size
    ):
        verify_source_partition(
            source, cases, build_diagnostic_conditions=(none_true, cases[0].condition)
        )
    with pytest.raises(BmcBuildError, match="gap at assignment"):
        verify_source_partition(
            source, cases[:-1], build_diagnostic_conditions=(none_true,)
        )


@pytest.mark.unittest
def test_large_partition_rejects_unknown_labels_and_cycles(leaf_source):
    """Accepted references are validated before any large-partition proof."""
    accepted, _ = priority_tree(leaf_source, (4, 3, 3))
    dangling = _case(
        leaf_source,
        "transition",
        36,
        BoolTemplate.and_(
            BoolTemplate.atom("event:Root.Extra"),
            BoolTemplate.not_(_accepted("Root::transition::Root::99")),
        ),
    )
    with pytest.raises(BmcBuildError, match="unknown case label"):
        verify_source_partition(
            leaf_source,
            accepted + [dangling, _fallback(leaf_source, accepted + [dangling])],
        )

    first = _case(
        leaf_source,
        "transition",
        36,
        BoolTemplate.and_(
            BoolTemplate.atom("event:Root.A"),
            BoolTemplate.not_(_accepted("Root::transition::Root::37")),
        ),
    )
    second = _case(
        leaf_source,
        "transition",
        37,
        BoolTemplate.and_(
            BoolTemplate.atom("event:Root.B"), BoolTemplate.not_(_accepted(first.label))
        ),
    )
    looped = accepted + [first, second]
    with pytest.raises(BmcBuildError, match="cycle detected"):
        verify_source_partition(leaf_source, looped + [_fallback(leaf_source, looped)])


@pytest.mark.unittest
def test_source_partition_validates_max_assignments(leaf_source):
    """The budget argument is validated on every path, not only the truth table."""
    accepted, _ = priority_tree(leaf_source, (2, 2))
    cases = accepted + [_fallback(leaf_source, accepted)]
    for bad in (0, -1, True, 1.5, "8"):
        with pytest.raises(BmcBuildError, match="max_assignments"):
            verify_source_partition(leaf_source, cases, max_assignments=bad)


def _mutate(rng, source, accepted, masks):
    """Return accepted and terminal buckets after one random, possibly breaking edit."""
    accepted = list(accepted)
    choice = rng.randrange(6)
    if choice == 0 and len(accepted) > 1:
        index = rng.randrange(len(accepted))
        victim = accepted[index]
        if masks[index]:
            dropped = rng.choice(masks[index])
            kept = [op for op in victim.condition.operands if op != dropped] or [
                BoolTemplate.true()
            ]
            accepted[index] = _case(
                source, "transition", index, BoolTemplate.and_(*kept)
            )
    elif choice == 1 and len(accepted) > 1:
        index = rng.randrange(len(accepted))
        other = rng.choice([case for i, case in enumerate(accepted) if i != index])
        accepted[index] = _case(
            source,
            "transition",
            index,
            BoolTemplate.and_(accepted[index].condition, _accepted(other.label)),
        )
    elif choice == 2:
        index = rng.randrange(len(accepted))
        victim = accepted[index]
        accepted[index] = _case(
            source, "transition", index, BoolTemplate.not_(victim.condition)
        )
    terminal_choice = rng.randrange(4)
    if terminal_choice == 0:
        terminal: Optional[CycleCase] = None
    elif terminal_choice == 1 and len(accepted) > 1:
        terminal = _fallback(source, accepted[1:])
    else:
        terminal = _fallback(source, accepted)
    return accepted, terminal


def _verdict(source, cases, max_assignments, delta=(), diagnostics=()):
    try:
        result = verify_source_partition(
            source, cases, delta, diagnostics, max_assignments=max_assignments
        )
    except BmcBuildError as err:
        message = str(err)
        return ("violation", "gap" in message, "overlap" in message)
    # Variables are informational: truth-table resolution may constant-fold a
    # literal away, so the differential compares verdicts and bucket counts.
    return ("partition", result.bucket_count)


class _CyclicReference(Exception):
    """An accepted atom refers back to a case that is still being substituted."""


def _substituted(template, assignment, registry, active, memo):
    """Evaluate ``template`` with every accepted atom replaced by its case condition.

    ``memo`` caches each case's value under the current assignment; it only
    avoids re-evaluating the same substituted condition.
    """
    if template.kind in ("true", "false"):
        return template.kind == "true"
    if template.kind == "atom":
        name = template.name
        if name.startswith("accepted:"):
            label = name[len("accepted:") :]
            if label in active:
                raise _CyclicReference(label)
            if label not in memo:
                memo[label] = _substituted(
                    registry[label], assignment, registry, active + (label,), memo
                )
            return memo[label]
        return assignment[name]
    values = [
        _substituted(item, assignment, registry, active, memo)
        for item in template.operands
    ]
    if template.kind == "not":
        return not values[0]
    return all(values) if template.kind == "and" else any(values)


def _independent_verdict(cases, diagnostics=()):
    """Brute-force oracle written from the definition of a partition.

    Build diagnostics, written over event atoms only, form one extra bucket.
    """
    registry = {case.label: case.condition for case in cases}
    names = sorted(
        {
            name
            for case in cases
            for name in case.condition.variables
            if not name.startswith("accepted:")
        }
        | {name for item in diagnostics for name in item.variables}
    )
    gap = overlap = False
    for values in itertools.product((False, True), repeat=len(names)):
        assignment = dict(zip(names, values))
        memo = {}
        try:
            count = sum(
                _substituted(case.condition, assignment, registry, (case.label,), memo)
                for case in cases
            )
            count += any(
                _substituted(item, assignment, {}, (), {}) for item in diagnostics
            )
        except _CyclicReference:
            # Cyclic definitions describe no partition at all.
            return ("violation", False, False)
        gap = gap or count == 0
        overlap = overlap or count > 1
    if gap or overlap:
        return ("violation", gap, overlap)
    return ("partition", len(cases) + (1 if diagnostics else 0))


@pytest.mark.unittest
def test_large_partition_path_matches_truth_table_on_random_partitions(leaf_source):
    """Differential: both self-check paths agree with a brute-force oracle everywhere."""
    rng = random.Random(20260930)
    kinds = {"partition": 0, "violation": 0}
    for _ in range(400):
        fanouts = [rng.randint(1, 3) for _ in range(rng.randint(1, 3))]
        pool = [
            BoolTemplate.atom("event:Root.P%d" % index)
            for index in range(rng.randint(2, 6))
        ]

        def literal(index, pool=pool):
            atom = rng.choice(pool)
            return atom if rng.random() < 0.7 else BoolTemplate.not_(atom)

        accepted, masks = priority_tree(leaf_source, fanouts, literal)
        accepted, terminal = _mutate(rng, leaf_source, accepted, masks)
        cases = accepted + ([terminal] if terminal is not None else [])

        reference = _independent_verdict(cases)
        assert _verdict(leaf_source, cases, 4096) == reference
        assert _verdict(leaf_source, cases, 1) == reference
        kinds[reference[0]] += 1
    # The generator must exercise both outcomes to mean anything.
    assert kinds["partition"] > 50 and kinds["violation"] > 50


@pytest.mark.unittest
def test_delta_partitions_with_diagnostics_match_brute_force(plant_entry_source):
    """Differential for entry sources closed by a delta bucket beside build diagnostics."""
    source = plant_entry_source
    rng = random.Random(20261001)
    kinds = {"partition": 0, "violation": 0}
    for _ in range(300):
        fanouts = [rng.randint(1, 3) for _ in range(rng.randint(1, 3))]
        pool = [
            BoolTemplate.atom("event:Root.P%d" % index)
            for index in range(rng.randint(2, 6))
        ]

        def literal(index, pool=pool):
            atom = rng.choice(pool)
            return atom if rng.random() < 0.7 else BoolTemplate.not_(atom)

        accepted, masks = priority_tree(source, fanouts, literal)
        accepted, _ = _mutate(rng, source, accepted, masks)
        atom = rng.choice(pool)
        diagnostics = rng.choice(
            [(), (atom,), (BoolTemplate.and_(atom, BoolTemplate.not_(atom)),)]
        )
        # The delta bucket usually excludes every accepted case and diagnostic;
        # sometimes it forgets the first accepted case.
        excluded = accepted[1:] if rng.random() < 0.2 else accepted
        delta = _case(
            source,
            "delta",
            0,
            BoolTemplate.not_(
                BoolTemplate.or_(
                    *[_accepted(case.label) for case in excluded], *diagnostics
                )
            ),
        )

        reference = _independent_verdict(accepted + [delta], diagnostics)
        assert _verdict(source, accepted, 4096, (delta,), diagnostics) == reference
        assert _verdict(source, accepted, 1, (delta,), diagnostics) == reference
        kinds[reference[0]] += 1
    assert kinds["partition"] > 30 and kinds["violation"] > 30


@pytest.mark.unittest
def test_source_partition_rejects_duplicate_labels_and_empty_input(plant_entry_source):
    """Every case needs its own label, and a partition needs at least one bucket."""
    source = plant_entry_source
    first = _case(source, "transition", 0, BoolTemplate.atom("event:Root.A"))
    twin = _case(source, "transition", 0, BoolTemplate.false())
    rest = _case(source, "transition", 1, BoolTemplate.true())
    for budget in (1, 4096):
        with pytest.raises(InvalidBmcEncoding, match="Duplicate cycle case label"):
            verify_source_partition(source, [first, twin, rest], max_assignments=budget)
    with pytest.raises(BmcBuildError, match="at least one bucket"):
        verify_source_partition(source, [])
