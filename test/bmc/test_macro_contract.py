"""Macro-step case contract tests for FCSTM BMC."""

from __future__ import annotations

import subprocess
import sys
from typing import Any, cast

import pytest

from pyfcstm.bmc import (
    STATE_DIAGNOSTIC_ID,
    STATE_TERMINATE_ID,
    BmcBuildError,
    InvalidBmcEncoding,
    build_bmc_domain,
)
from pyfcstm.bmc.macro import (
    ActionBlock,
    BoolTemplate,
    CycleCase,
    EventUse,
    GuardRequirement,
    MacroStepFormal,
    PartitionCheckResult,
    PriorityExclusion,
    build_fallback_case,
    build_semantic_delta_case,
    case_path_condition,
    diagnostic_absorb_case,
    terminated_absorb_case,
    verify_boolean_partition,
    verify_source_partition,
)
from pyfcstm.bmc.source import (
    DIAGNOSTIC_CASE_PATH,
    MacroStepSource,
    TERMINATE_CASE_PATH,
    diagnostic_source,
    entry_source,
    stable_leaf_source,
    terminated_source,
)
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.expr import Boolean, Variable


def _bad_object() -> Any:
    """Return an intentionally bad value without tripping static type checks."""
    return cast(Any, object())


@pytest.fixture()
def macro_model():
    """Build a macro-contract fixture model."""
    return load_state_machine_from_text(
        """
        def int x = 0;
        def float y = 1.0;
        state Root {
            event Go;
            state Plant {
                event Ping;
                state Idle { during { if [x > 0] { y = y + 1; } else { y = 0; } } }
                state Busy;
                [*] -> Idle;
                Idle -> Busy :: Ping + Go;
            }
            state Backup {
                event Ping;
                state Idle;
                [*] -> Idle;
            }
            [*] -> Plant;
        }
        """
    )


@pytest.fixture()
def macro_domain(macro_model):
    """Build a macro-contract fixture with variables and same-short-name events."""
    return build_bmc_domain(macro_model, bound=2)


@pytest.fixture()
def sample_operation(macro_model):
    """Return one concrete operation statement from the fixture model."""
    state = macro_model.root_state.substates["Plant"].substates["Idle"]
    return state.on_durings[0].operations[0]


def make_case(
    domain,
    source,
    label_kind="transition",
    condition=None,
    target_path=None,
    ordinal=0,
    **kwargs,
):
    """Create a valid synthetic case for contract tests."""
    if condition is None:
        condition = BoolTemplate.true()
    if target_path is None:
        target_path = source.source_state_path
    target_id = domain.state_path_to_id(target_path)
    return CycleCase(
        label_kind,
        source.source_state_id,
        source.source_state_path,
        target_id,
        target_path,
        "%s::%s::%s::%d"
        % (
            source.source_state_path,
            label_kind,
            target_path,
            ordinal,
        ),
        condition,
        kwargs.pop("action_blocks", ()),
        domain=domain,
        **kwargs,
    )


def make_large_priority_partition(source, condition_hook=None):
    """Create a synthetic large accepted/fallback partition."""
    accepted = []
    for index in range(13):
        prefix = (
            BoolTemplate.not_(
                BoolTemplate.or_(
                    *[
                        BoolTemplate.atom("accepted:%s" % case.label)
                        for case in accepted
                    ]
                )
            )
            if accepted
            else BoolTemplate.true()
        )
        condition = BoolTemplate.and_(
            prefix, BoolTemplate.atom("event:Root.Event%d" % index)
        )
        if condition_hook is not None:
            condition = condition_hook(index, accepted, condition)
        accepted.append(
            CycleCase(
                "transition",
                source.source_state_id,
                source.source_state_path,
                source.source_state_id,
                source.source_state_path,
                "%s::transition::%s::%d"
                % (source.source_state_path, source.source_state_path, index),
                condition,
                (),
            )
        )
    fallback = CycleCase(
        "fallback",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        "%s::fallback::%s::0" % (source.source_state_path, source.source_state_path),
        BoolTemplate.not_(
            BoolTemplate.or_(
                *[BoolTemplate.atom("accepted:%s" % case.label) for case in accepted]
            )
        ),
        (),
    )
    return tuple(accepted) + (fallback,)


@pytest.mark.unittest
def test_bool_template_public_validation_and_identity_reductions():
    """BoolTemplate validates public shape and folds simple boolean identities."""
    atom = BoolTemplate.atom("event:Root.Go")

    assert BoolTemplate.not_(BoolTemplate.true()).kind == "false"
    assert BoolTemplate.not_(BoolTemplate.false()).kind == "true"
    assert BoolTemplate.not_(BoolTemplate.not_(atom)) is atom
    assert BoolTemplate.and_().kind == "true"
    assert BoolTemplate.and_(BoolTemplate.true()).kind == "true"
    assert BoolTemplate.and_(atom, BoolTemplate.false()).kind == "false"
    assert BoolTemplate.or_().kind == "false"
    assert BoolTemplate.or_(BoolTemplate.false()).kind == "false"
    assert BoolTemplate.or_(atom, BoolTemplate.true()).kind == "true"

    with pytest.raises(InvalidBmcEncoding, match="Unsupported boolean template kind"):
        BoolTemplate("xor")
    with pytest.raises(InvalidBmcEncoding, match="atom name"):
        BoolTemplate("atom")
    with pytest.raises(InvalidBmcEncoding, match="atom templates cannot have operands"):
        BoolTemplate("atom", "a", (atom,))
    with pytest.raises(
        InvalidBmcEncoding, match="constant templates cannot have names"
    ):
        BoolTemplate("true", "a")
    with pytest.raises(
        InvalidBmcEncoding, match="constant templates cannot have operands"
    ):
        BoolTemplate("false", operands=(atom,))
    with pytest.raises(InvalidBmcEncoding, match="not templates cannot have names"):
        BoolTemplate("not", "a", (atom,))
    with pytest.raises(InvalidBmcEncoding, match="not templates must have one operand"):
        BoolTemplate("not", operands=())
    with pytest.raises(
        InvalidBmcEncoding, match="compound templates cannot have names"
    ):
        BoolTemplate("and", "a", (atom,))
    with pytest.raises(
        InvalidBmcEncoding, match="compound templates must have operands"
    ):
        BoolTemplate("or", operands=())
    with pytest.raises(InvalidBmcEncoding, match="operands must contain"):
        BoolTemplate.and_(atom, _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="operand must be BoolTemplate"):
        BoolTemplate.not_(_bad_object())


@pytest.mark.unittest
def test_bool_template_evaluate_rejects_missing_and_non_boolean_assignments():
    """BoolTemplate public evaluator fails loudly on malformed assignments."""
    atom = BoolTemplate.atom("event:Root.Go")

    assert BoolTemplate.and_(
        atom, BoolTemplate.not_(BoolTemplate.atom("event:Root.Stop"))
    ).evaluate({"event:Root.Go": True, "event:Root.Stop": False})
    with pytest.raises(BmcBuildError, match="missing boolean assignment"):
        atom.evaluate({})
    with pytest.raises(BmcBuildError, match="must be bool"):
        atom.evaluate({"event:Root.Go": _bad_object()})


@pytest.mark.unittest
def test_public_contract_dataclasses_reject_invalid_shapes(
    macro_domain,
    sample_operation,
):
    """Public macro contract objects validate their constructor boundaries."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    expr = Variable("x") > 0

    with pytest.raises(InvalidBmcEncoding, match="event_id must be non-negative"):
        EventUse(-1, "Root.Go", "positive", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="event polarity"):
        EventUse(0, "Root.Go", "maybe", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="owner_state_id must be non-negative"):
        GuardRequirement(
            "g0",
            -1,
            source.source_state_path,
            "t",
            expr,
            "positive",
            "transition_guard",
            0,
        )
    with pytest.raises(InvalidBmcEncoding, match="guard requirement expr"):
        GuardRequirement(
            "g0",
            source.source_state_id,
            source.source_state_path,
            "t",
            _bad_object(),
            "positive",
            "transition_guard",
            0,
        )
    with pytest.raises(InvalidBmcEncoding, match="after_action_block_index"):
        GuardRequirement(
            "g0",
            source.source_state_id,
            source.source_state_path,
            "t",
            expr,
            "positive",
            "transition_guard",
            -1,
        )
    with pytest.raises(InvalidBmcEncoding, match="excluded_case_labels"):
        PriorityExclusion("d0", "fallback", (), BoolTemplate.true())
    with pytest.raises(InvalidBmcEncoding, match="non-empty strings"):
        PriorityExclusion("d0", "fallback", ("",), BoolTemplate.true())
    with pytest.raises(
        InvalidBmcEncoding, match="excluded_condition must be BoolTemplate"
    ):
        PriorityExclusion("d0", "fallback", ("c0",), _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="accepted atoms"):
        PriorityExclusion("d0", "fallback", ("c0",), BoolTemplate.atom("event:Root.Go"))
    with pytest.raises(InvalidBmcEncoding, match="owner_state_id must be non-negative"):
        ActionBlock("state_action", "leaf_during", -1, "Root.Plant.Idle", ())
    with pytest.raises(InvalidBmcEncoding, match="OperationStatement"):
        ActionBlock(
            "state_action",
            "leaf_during",
            source.source_state_id,
            source.source_state_path,
            (_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="is_abstract"):
        ActionBlock(
            "state_action",
            "leaf_during",
            source.source_state_id,
            source.source_state_path,
            (sample_operation,),
            is_abstract=_bad_object(),
        )

    priority = PriorityExclusion(
        "d0",
        "fallback",
        ("c0",),
        BoolTemplate.atom("accepted:c0"),
    )
    assert priority.to_canonical()["node"] == "priority_exclusion"


@pytest.mark.unittest
def test_cycle_case_public_validation_rejects_invalid_local_shapes(macro_domain):
    """CycleCase rejects malformed labels, links, and local metadata."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    target_id = source.source_state_id
    target_path = source.source_state_path
    label = "%s::transition::%s::0" % (source.source_state_path, target_path)

    with pytest.raises(InvalidBmcEncoding, match="condition must be BoolTemplate"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            _bad_object(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="action_blocks"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="used_events"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (),
            used_events=(_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="GuardRequirement"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (),
            guard_requirements=(_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="PriorityExclusion"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (),
            priority_exclusions=(_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (),
            failed_conditions=(_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="label must use"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            "bad",
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="label source path"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            "Other::transition::%s::0" % target_path,
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="label case kind"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            "%s::fallback::%s::0" % (source.source_state_path, target_path),
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="label target path"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            "%s::transition::Other::0" % source.source_state_path,
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="label ordinal"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            "%s::transition::%s::x" % (source.source_state_path, target_path),
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="absorb cases must self-loop"):
        CycleCase(
            "absorb",
            STATE_TERMINATE_ID,
            TERMINATE_CASE_PATH,
            STATE_DIAGNOSTIC_ID,
            DIAGNOSTIC_CASE_PATH,
            "%s::absorb::%s::0" % (TERMINATE_CASE_PATH, DIAGNOSTIC_CASE_PATH),
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="absorb cases must use sentinel"):
        CycleCase(
            "absorb",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::absorb::%s::0" % (source.source_state_path, source.source_state_path),
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(
        InvalidBmcEncoding, match="diagnostic and delta cases target diagnostic"
    ):
        CycleCase(
            "diagnostic",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            "%s::diagnostic::%s::0" % (source.source_state_path, target_path),
            BoolTemplate.true(),
            (),
        )
    with pytest.raises(InvalidBmcEncoding, match="Duplicate guard requirement id"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.atom("guard:g0"),
            (),
            guard_requirements=(
                GuardRequirement(
                    "g0",
                    source.source_state_id,
                    source.source_state_path,
                    "t0",
                    Boolean(True),
                    "positive",
                    "transition_guard",
                    0,
                ),
                GuardRequirement(
                    "g0",
                    source.source_state_id,
                    source.source_state_path,
                    "t1",
                    Boolean(True),
                    "positive",
                    "transition_guard",
                    0,
                ),
            ),
        )
    with pytest.raises(InvalidBmcEncoding, match="domain must be BmcDomain"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (),
            domain=_bad_object(),
        )
    with pytest.raises(InvalidBmcEncoding, match="EventUse path"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            target_id,
            target_path,
            label,
            BoolTemplate.true(),
            (),
            used_events=(
                EventUse(
                    macro_domain.event_by_path("Root.Go").id,
                    "Root.Plant.Ping",
                    "positive",
                    "trigger",
                ),
            ),
            domain=macro_domain,
        )


@pytest.mark.unittest
def test_macro_step_formal_public_validation_rejects_invalid_bucket_shapes(
    macro_domain,
):
    """MacroStepFormal validates public source, bucket, and sentinel contracts."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    fallback = build_fallback_case(macro_domain, stable, ())
    transition = make_case(macro_domain, stable, target_path="Root.Plant.Busy")
    delta = CycleCase(
        "delta",
        stable.source_state_id,
        stable.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::delta::%s::0" % (stable.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
    )

    with pytest.raises(InvalidBmcEncoding, match="source must be MacroStepSource"):
        MacroStepFormal(_bad_object(), (fallback,))
    with pytest.raises(InvalidBmcEncoding, match="success_cases must be a sequence"):
        MacroStepFormal(stable, _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="delta_cases must be a sequence"):
        MacroStepFormal(stable, (fallback,), _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic_conditions"):
        MacroStepFormal(stable, (fallback,), (), _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        MacroStepFormal(stable, (_bad_object(),))
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        MacroStepFormal(stable, (fallback,), (_bad_object(),))
    with pytest.raises(InvalidBmcEncoding, match="BoolTemplate"):
        MacroStepFormal(stable, (fallback,), (), (_bad_object(),))
    with pytest.raises(InvalidBmcEncoding, match="at least one relation case"):
        MacroStepFormal(stable, ())
    with pytest.raises(InvalidBmcEncoding, match="case source path"):
        MacroStepFormal(
            MacroStepSource(
                "stable_leaf", "recurrence", stable.source_state_id, "Other"
            ),
            (fallback,),
        )
    with pytest.raises(InvalidBmcEncoding, match="build diagnostics"):
        MacroStepFormal(stable, (fallback,), (), (BoolTemplate.true(),))
    with pytest.raises(
        InvalidBmcEncoding, match="success_cases must not contain delta"
    ):
        MacroStepFormal(stable, (delta,))
    with pytest.raises(
        InvalidBmcEncoding, match="stable leaf formal requires a fallback"
    ):
        MacroStepFormal(stable, (transition,))
    with pytest.raises(InvalidBmcEncoding, match="stable leaf success cases"):
        MacroStepFormal(
            stable, (make_case(macro_domain, stable, label_kind="initial"), fallback)
        )
    bad_fallback_target = CycleCase(
        "fallback",
        stable.source_state_id,
        stable.source_state_path,
        macro_domain.state_path_to_id("Root.Plant.Busy"),
        "Root.Plant.Busy",
        "%s::fallback::Root.Plant.Busy::0" % stable.source_state_path,
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="fallback cases must self-loop"):
        MacroStepFormal(stable, (bad_fallback_target,))
    bad_transition_target = CycleCase(
        "transition",
        stable.source_state_id,
        stable.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::transition::%s::0" % (stable.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="stable leaf transitions"):
        MacroStepFormal(stable, (bad_transition_target, fallback))
    bad_priority = CycleCase(
        "fallback",
        stable.source_state_id,
        stable.source_state_path,
        stable.source_state_id,
        stable.source_state_path,
        "%s::fallback::%s::2" % (stable.source_state_path, stable.source_state_path),
        BoolTemplate.true(),
        (),
        priority_exclusions=(
            PriorityExclusion(
                "d0",
                "fallback",
                ("missing",),
                BoolTemplate.atom("accepted:missing"),
            ),
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="priority exclusion"):
        MacroStepFormal(stable, (bad_priority,))

    entry = entry_source(macro_domain, "Root.Plant")
    bad_entry_case = CycleCase(
        "initial",
        entry.source_state_id,
        entry.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::initial::%s::0" % (entry.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="entry transition and initial cases"):
        MacroStepFormal(entry, (bad_entry_case,))

    terminate = terminated_source(macro_domain)
    good_absorb = terminated_absorb_case(macro_domain)
    sentinel_delta = CycleCase(
        "delta",
        terminate.source_state_id,
        terminate.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::delta::%s::0" % (terminate.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="delta_cases require"):
        MacroStepFormal(terminate, (good_absorb,), (sentinel_delta,))
    second_absorb = CycleCase(
        "absorb",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::absorb::%s::1"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="must contain one case"):
        MacroStepFormal(terminate, (good_absorb, second_absorb))
    wrong_sentinel_case = CycleCase(
        "transition",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::transition::%s::0"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel formal case"):
        MacroStepFormal(terminate, (wrong_sentinel_case,))
    false_absorb = CycleCase(
        "absorb",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::absorb::%s::0"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.false(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel absorb condition"):
        MacroStepFormal(terminate, (false_absorb,))
    absorb_with_action = CycleCase(
        "absorb",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::absorb::%s::0"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.true(),
        (
            ActionBlock(
                "state_action",
                "leaf_during",
                macro_domain.state_path_to_id("Root.Plant.Idle"),
                "Root.Plant.Idle",
                (),
                is_abstract=True,
            ),
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel absorb case cannot"):
        MacroStepFormal(terminate, (absorb_with_action,))
    noncanonical_absorb = CycleCase(
        "absorb",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::absorb::%s::3"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel absorb label"):
        MacroStepFormal(terminate, (noncanonical_absorb,))

    assert (
        MacroStepFormal(stable, (fallback,)).to_canonical()["node"]
        == "macro_step_formal"
    )
    assert (
        PartitionCheckResult((), 0, 1).to_canonical()["node"]
        == "partition_check_result"
    )


@pytest.mark.unittest
def test_cycle_case_condition_is_control_path_only(macro_domain):
    """CycleCase.condition excludes source guards and writeback formulas."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    gamma = BoolTemplate.atom("event:Root.Plant.Ping")
    event = macro_domain.event_by_path("Root.Plant.Ping")
    case = make_case(
        macro_domain,
        source,
        condition=gamma,
        used_events=(EventUse(event.id, event.path, "positive", "trigger"),),
    )

    assert case.condition is gamma
    assert case_path_condition(case) is gamma
    assert case.to_canonical()["condition"]["name"] == "event:Root.Plant.Ping"
    assert "var_update" not in case.to_canonical()


@pytest.mark.unittest
def test_unknown_condition_atom_namespaces_are_rejected(macro_domain):
    """Case conditions fail closed unless atoms use event/guard/accepted namespaces."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")

    for atom in ("plain", "pre:x", "__source_state__:%d" % source.source_state_id):
        with pytest.raises(InvalidBmcEncoding, match="atom namespace"):
            make_case(macro_domain, source, condition=BoolTemplate.atom(atom))


@pytest.mark.unittest
def test_event_atoms_require_domain_events_and_metadata(macro_domain):
    """Domain eager validation covers event atoms in all case conditions."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    ping = macro_domain.event_by_path("Root.Plant.Ping")

    valid = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("event:Root.Plant.Ping"),
        used_events=(EventUse(ping.id, ping.path, "positive", "trigger"),),
    )
    assert valid.used_events[0].path == "Root.Plant.Ping"

    with pytest.raises(InvalidBmcEncoding, match="used_events"):
        make_case(
            macro_domain,
            source,
            condition=BoolTemplate.atom("event:Root.Plant.Ping"),
        )

    with pytest.raises(InvalidBmcEncoding, match="Unknown event path"):
        make_case(
            macro_domain,
            source,
            failed_conditions=(BoolTemplate.atom("event:Root.Plant.NoSuch"),),
        )


@pytest.mark.unittest
def test_guard_atoms_require_matching_requirement_and_anchor(macro_domain):
    """Guard atoms point to raw expressions with action-block prefix anchors."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    guard = GuardRequirement(
        "g0",
        source.source_state_id,
        source.source_state_path,
        "Idle -> Busy",
        Variable("x") > 0,
        "positive",
        "transition_guard",
        0,
    )
    case = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("guard:g0"),
        guard_requirements=(guard,),
    )

    assert case.guard_requirements[0].atom_name == "guard:g0"
    assert case.guard_requirements[0].after_action_block_index == 0
    assert case.to_canonical()["guard_requirements"][0]["expr"] == "x > 0"

    with pytest.raises(InvalidBmcEncoding, match="matching GuardRequirement"):
        make_case(macro_domain, source, condition=BoolTemplate.atom("guard:g_missing"))

    with pytest.raises(InvalidBmcEncoding, match="guard anchor"):
        make_case(
            macro_domain,
            source,
            condition=BoolTemplate.atom("guard:g1"),
            guard_requirements=(
                GuardRequirement(
                    "g1",
                    source.source_state_id,
                    source.source_state_path,
                    "Idle -> Busy",
                    Boolean(True),
                    "positive",
                    "transition_guard",
                    1,
                ),
            ),
        )


@pytest.mark.unittest
def test_action_block_preserves_if_block_without_condition_split(
    macro_domain,
    sample_operation,
):
    """ActionBlock stores model statements, including nested IfBlock objects."""
    block = ActionBlock(
        "state_action",
        "leaf_during",
        macro_domain.state_path_to_id("Root.Plant.Idle"),
        "Root.Plant.Idle",
        (sample_operation,),
        action_name="Root.Plant.Idle.<unnamed>",
    )
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    case = make_case(macro_domain, source, action_blocks=(block,))

    assert case.action_blocks[0].operations == (sample_operation,)
    assert (
        case.to_canonical()["action_blocks"][0]["operations"][0]["node"] == "if_block"
    )
    assert case.condition.variables == ()


@pytest.mark.unittest
def test_absorb_cases_are_regular_cases_with_true_condition(macro_domain):
    """Terminated and diagnostic absorbs are ordinary CycleCase objects."""
    terminate = terminated_absorb_case(macro_domain)
    diagnostic = diagnostic_absorb_case(macro_domain)

    assert terminate.source_state_id == STATE_TERMINATE_ID
    assert terminate.target_state_id == STATE_TERMINATE_ID
    assert terminate.source_state_path == TERMINATE_CASE_PATH
    assert terminate.label == "__terminate__::absorb::__terminate__::0"
    assert terminate.condition.evaluate({}) is True
    assert terminate.action_blocks == ()
    assert terminate.is_diagnostic is False

    assert diagnostic.source_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.target_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.source_state_path == DIAGNOSTIC_CASE_PATH
    assert diagnostic.label == "__diagnostic__::absorb::__diagnostic__::0"
    assert diagnostic.condition.evaluate({}) is True
    assert diagnostic.action_blocks == ()
    assert diagnostic.is_diagnostic is True


@pytest.mark.unittest
def test_fallback_condition_negates_accepted_labels_not_raw_conditions(macro_domain):
    """Fallback masks use accepted:<label> instead of copying trigger atoms."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    ping = macro_domain.event_by_path("Root.Plant.Ping")
    accepted = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("event:Root.Plant.Ping"),
        target_path="Root.Plant.Busy",
        used_events=(EventUse(ping.id, ping.path, "positive", "trigger"),),
    )
    failed = BoolTemplate.atom("event:Root.Go")
    root_go = macro_domain.event_by_path("Root.Go")

    fallback = build_fallback_case(macro_domain, source, (accepted,), (failed,))

    assert fallback.kind == "fallback"
    assert fallback.condition.variables == ("accepted:%s" % accepted.label,)
    assert fallback.priority_exclusions[0].excluded_case_labels == (accepted.label,)
    assert {item.path for item in fallback.used_events} == {ping.path, root_go.path}
    assert fallback.failed_conditions == (failed,)


@pytest.mark.unittest
def test_semantic_delta_condition_excludes_success_labels_and_build_diag(
    macro_domain,
):
    """Entry delta leaves failed candidate conditions as diagnostics only."""
    source = entry_source(macro_domain, "Root.Plant")
    accepted = make_case(
        macro_domain,
        source,
        label_kind="initial",
        target_path="Root.Plant.Idle",
        condition=BoolTemplate.atom("guard:g0"),
        guard_requirements=(
            GuardRequirement(
                "g0",
                source.source_state_id,
                source.source_state_path,
                "[*] -> Idle",
                Boolean(True),
                "positive",
                "initial_guard",
                0,
            ),
        ),
    )
    build_diag = BoolTemplate.atom("event:Root.Go")
    root_go = macro_domain.event_by_path("Root.Go")
    failed = BoolTemplate.atom("event:Root.Plant.Ping")

    delta = build_semantic_delta_case(
        macro_domain,
        source,
        (accepted,),
        (build_diag,),
        (failed,),
    )

    assert delta.kind == "delta"
    assert delta.target_state_id == STATE_DIAGNOSTIC_ID
    assert delta.condition.variables == (
        "accepted:%s" % accepted.label,
        "event:Root.Go",
    )
    assert delta.priority_exclusions[0].excluded_case_labels == (accepted.label,)
    assert root_go.path in {item.path for item in delta.used_events}
    assert delta.failed_conditions == (failed,)


@pytest.mark.unittest
def test_build_case_helpers_reject_invalid_public_arguments(macro_domain):
    """Public fallback and delta builders fail closed on malformed inputs."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    entry = entry_source(macro_domain, "Root.Plant")

    with pytest.raises(InvalidBmcEncoding, match="fallback case requires"):
        build_fallback_case(macro_domain, entry, ())
    with pytest.raises(InvalidBmcEncoding, match="ordinal must be non-negative"):
        build_fallback_case(macro_domain, stable, (), ordinal=-1)
    with pytest.raises(InvalidBmcEncoding, match="accepted_cases must be a sequence"):
        build_fallback_case(macro_domain, stable, _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        build_fallback_case(macro_domain, stable, (_bad_object(),))
    with pytest.raises(
        InvalidBmcEncoding, match="failed_conditions must be a sequence"
    ):
        build_fallback_case(macro_domain, stable, (), failed_conditions=_bad_object())
    with pytest.raises(InvalidBmcEncoding, match="BoolTemplate"):
        build_fallback_case(
            macro_domain, stable, (), failed_conditions=(_bad_object(),)
        )
    with pytest.raises(InvalidBmcEncoding, match="GuardRequirement"):
        build_fallback_case(
            macro_domain, stable, (), guard_requirements=(_bad_object(),)
        )

    bad_kind = make_case(macro_domain, stable, label_kind="fallback")
    with pytest.raises(InvalidBmcEncoding, match="ordinary accepted cases"):
        build_fallback_case(macro_domain, stable, (bad_kind,))
    bad_source = make_case(
        macro_domain,
        entry,
        label_kind="transition",
        target_path="Root.Plant.Idle",
    )
    with pytest.raises(InvalidBmcEncoding, match="accepted case source id"):
        build_fallback_case(macro_domain, stable, (bad_source,))
    bad_path = CycleCase(
        "transition",
        stable.source_state_id,
        "Other",
        stable.source_state_id,
        stable.source_state_path,
        "Other::transition::%s::0" % stable.source_state_path,
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="accepted case source path"):
        build_fallback_case(macro_domain, stable, (bad_path,))
    diagnostic = CycleCase(
        "transition",
        stable.source_state_id,
        stable.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::transition::%s::0" % (stable.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="target model states or terminate"):
        build_fallback_case(macro_domain, stable, (diagnostic,))
    with pytest.raises(InvalidBmcEncoding, match="Unknown event path"):
        build_fallback_case(
            macro_domain,
            stable,
            (),
            failed_conditions=(BoolTemplate.atom("event:Root.NoSuch"),),
        )

    with pytest.raises(InvalidBmcEncoding, match="semantic delta case requires"):
        build_semantic_delta_case(macro_domain, stable, ())
    with pytest.raises(InvalidBmcEncoding, match="ordinal must be non-negative"):
        build_semantic_delta_case(macro_domain, entry, (), ordinal=-1)
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic_conditions"):
        build_semantic_delta_case(
            macro_domain,
            entry,
            (),
            build_diagnostic_conditions=_bad_object(),
        )
    with pytest.raises(InvalidBmcEncoding, match="BoolTemplate"):
        build_semantic_delta_case(
            macro_domain,
            entry,
            (),
            build_diagnostic_conditions=(_bad_object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        build_semantic_delta_case(
            macro_domain, entry, (), failed_conditions=_bad_object()
        )
    with pytest.raises(InvalidBmcEncoding, match="GuardRequirement"):
        build_semantic_delta_case(
            macro_domain, entry, (), guard_requirements=(_bad_object(),)
        )
    with pytest.raises(
        InvalidBmcEncoding, match="failed_conditions must contain BoolTemplate"
    ):
        build_semantic_delta_case(
            macro_domain,
            entry,
            (),
            failed_conditions=(_bad_object(),),
        )


@pytest.mark.unittest
def test_partition_resolves_accepted_atoms_through_case_registry(macro_domain):
    """Source partition checks use accepted-path semantics, not free atoms."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    ping = macro_domain.event_by_path("Root.Plant.Ping")
    transition = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("event:Root.Plant.Ping"),
        target_path="Root.Plant.Busy",
        used_events=(EventUse(ping.id, ping.path, "positive", "trigger"),),
    )
    fallback = build_fallback_case(macro_domain, source, (transition,))

    result = verify_source_partition(source, (transition, fallback))

    assert result.variables == ("event:Root.Plant.Ping",)
    assert result.assignment_count == 2


@pytest.mark.unittest
def test_partition_handles_sentinel_delta_and_accepted_atom_failures(macro_domain):
    """Source partition checks cover sentinel, delta, diagnostic, and atom cycles."""
    terminate = terminated_source(macro_domain)
    terminated = verify_source_partition(
        terminate,
        (terminated_absorb_case(macro_domain),),
        max_assignments=1,
    )
    assert terminated.assignment_count == 0
    assert terminated.bucket_count == 1

    false_absorb = CycleCase(
        "absorb",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::absorb::%s::0"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.false(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel absorb condition"):
        verify_source_partition(terminate, (false_absorb,), max_assignments=1)

    absorb_with_action = CycleCase(
        "absorb",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::absorb::%s::0"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.true(),
        (
            ActionBlock(
                "state_action",
                "leaf_during",
                macro_domain.state_path_to_id("Root.Plant.Idle"),
                "Root.Plant.Idle",
                (),
                is_abstract=True,
            ),
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel absorb case cannot"):
        verify_source_partition(terminate, (absorb_with_action,), max_assignments=1)

    sentinel_fallback = CycleCase(
        "fallback",
        terminate.source_state_id,
        terminate.source_state_path,
        terminate.source_state_id,
        terminate.source_state_path,
        "%s::fallback::%s::0"
        % (terminate.source_state_path, terminate.source_state_path),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel formal case"):
        verify_source_partition(terminate, (sentinel_fallback,), max_assignments=1)

    entry = entry_source(macro_domain, "Root.Plant")
    accepted = make_case(
        macro_domain,
        entry,
        label_kind="initial",
        target_path="Root.Plant.Idle",
        condition=BoolTemplate.atom("event:Root.Go"),
        used_events=(
            EventUse(
                macro_domain.event_by_path("Root.Go").id,
                "Root.Go",
                "positive",
                "trigger",
            ),
        ),
    )
    diagnostic_condition = BoolTemplate.atom("event:Root.Plant.Ping")
    delta = build_semantic_delta_case(
        macro_domain,
        entry,
        (accepted,),
        build_diagnostic_conditions=(diagnostic_condition,),
    )
    result = verify_source_partition(
        entry,
        (accepted,),
        (delta,),
        (diagnostic_condition,),
        max_assignments=1,
    )
    assert result.assignment_count == 0
    assert result.bucket_count == 3

    first = CycleCase(
        "transition",
        entry.source_state_id,
        entry.source_state_path,
        entry.source_state_id,
        entry.source_state_path,
        "%s::transition::%s::10" % (entry.source_state_path, entry.source_state_path),
        BoolTemplate.atom(
            "accepted:%s::transition::%s::11"
            % (entry.source_state_path, entry.source_state_path)
        ),
        (),
    )
    second = CycleCase(
        "transition",
        entry.source_state_id,
        entry.source_state_path,
        entry.source_state_id,
        entry.source_state_path,
        "%s::transition::%s::11" % (entry.source_state_path, entry.source_state_path),
        BoolTemplate.atom("accepted:%s" % first.label),
        (),
    )
    with pytest.raises(BmcBuildError, match="cycle detected"):
        verify_source_partition(entry, (first, second), max_assignments=8)

    unknown = CycleCase(
        "transition",
        entry.source_state_id,
        entry.source_state_path,
        entry.source_state_id,
        entry.source_state_path,
        "%s::transition::%s::12" % (entry.source_state_path, entry.source_state_path),
        BoolTemplate.atom("accepted:missing-label"),
        (),
    )
    with pytest.raises(BmcBuildError, match="unknown case label"):
        verify_source_partition(entry, (unknown,), max_assignments=8)


@pytest.mark.unittest
def test_structural_partition_negative_shapes_fall_back_to_truth_table_budget(
    macro_domain,
):
    """Structural recognizer refuses malformed accepted/fallback/delta shapes."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")

    accepted_only = make_large_priority_partition(source)[:-1]
    with pytest.raises(BmcBuildError, match="assignment budget"):
        verify_source_partition(source, accepted_only, max_assignments=1)

    accepted = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("event:Root.Plant.Ping"),
        target_path="Root.Plant.Busy",
        used_events=(
            EventUse(
                macro_domain.event_by_path("Root.Plant.Ping").id,
                "Root.Plant.Ping",
                "positive",
                "trigger",
            ),
        ),
    )
    bad_fallback = CycleCase(
        "fallback",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        "%s::fallback::%s::20" % (source.source_state_path, source.source_state_path),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(BmcBuildError, match="overlap"):
        verify_source_partition(source, (accepted, bad_fallback), max_assignments=8)

    entry = entry_source(macro_domain, "Root.Plant")
    accepted_entry = make_case(
        macro_domain,
        entry,
        label_kind="initial",
        target_path="Root.Plant.Idle",
        condition=BoolTemplate.atom("event:Root.Go"),
        used_events=(
            EventUse(
                macro_domain.event_by_path("Root.Go").id,
                "Root.Go",
                "positive",
                "trigger",
            ),
        ),
    )
    bad_delta = CycleCase(
        "delta",
        entry.source_state_id,
        entry.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::delta::%s::20" % (entry.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(BmcBuildError, match="overlap"):
        verify_source_partition(
            entry, (accepted_entry,), (bad_delta,), max_assignments=8
        )


@pytest.mark.unittest
def test_verify_partition_public_validation_rejects_bad_arguments(macro_domain):
    """Public partition helpers validate their documented argument boundary."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    fallback = build_fallback_case(macro_domain, source, ())

    with pytest.raises(BmcBuildError, match="partition buckets"):
        verify_boolean_partition(_bad_object())
    with pytest.raises(BmcBuildError, match="at least one bucket"):
        verify_boolean_partition(())
    with pytest.raises(BmcBuildError, match="BoolTemplate"):
        verify_boolean_partition((_bad_object(),))
    with pytest.raises(BmcBuildError, match="max_assignments"):
        verify_boolean_partition((BoolTemplate.true(),), max_assignments=True)
    with pytest.raises(BmcBuildError, match="max_assignments"):
        verify_boolean_partition((BoolTemplate.true(),), max_assignments=0)
    with pytest.raises(BmcBuildError, match="partition variables"):
        verify_boolean_partition((BoolTemplate.true(),), variables=_bad_object())
    with pytest.raises(BmcBuildError, match="non-empty strings"):
        verify_boolean_partition((BoolTemplate.true(),), variables=("",))

    with pytest.raises(InvalidBmcEncoding, match="source must be MacroStepSource"):
        verify_source_partition(_bad_object(), (fallback,))
    with pytest.raises(InvalidBmcEncoding, match="success_cases must be a sequence"):
        verify_source_partition(source, _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="delta_cases must be a sequence"):
        verify_source_partition(source, (fallback,), _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic_conditions"):
        verify_source_partition(source, (fallback,), (), _bad_object())
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        verify_source_partition(source, (_bad_object(),))
    with pytest.raises(InvalidBmcEncoding, match="source id mismatch"):
        verify_source_partition(
            source, (make_case(macro_domain, entry_source(macro_domain, "Root.Plant")),)
        )
    wrong_path = CycleCase(
        "fallback",
        source.source_state_id,
        "Other",
        source.source_state_id,
        source.source_state_path,
        "Other::fallback::%s::0" % source.source_state_path,
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="source path mismatch"):
        verify_source_partition(source, (wrong_path,))
    delta = build_semantic_delta_case(
        macro_domain, entry_source(macro_domain, "Root.Plant"), ()
    )
    with pytest.raises(
        InvalidBmcEncoding, match="success_cases must not contain delta"
    ):
        verify_source_partition(entry_source(macro_domain, "Root.Plant"), (delta,))
    with pytest.raises(InvalidBmcEncoding, match="delta_cases may only contain delta"):
        entry = entry_source(macro_domain, "Root.Plant")
        verify_source_partition(entry, (), (make_case(macro_domain, entry),))
    with pytest.raises(InvalidBmcEncoding, match="BoolTemplate"):
        verify_source_partition(source, (fallback,), (), (_bad_object(),))
    with pytest.raises(InvalidBmcEncoding, match="delta cases require"):
        verify_source_partition(source, (fallback,), (delta,))


@pytest.mark.unittest
def test_macro_step_formal_revalidates_domainless_cases_and_accepted_atoms(
    macro_domain,
):
    """Domain-backed formals reject target, event, guard, and label bypasses."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    fallback = build_fallback_case(macro_domain, source, ())

    bad_target = CycleCase(
        "transition",
        source.source_state_id,
        source.source_state_path,
        999,
        "Missing.Target",
        "%s::transition::Missing.Target::0" % source.source_state_path,
        BoolTemplate.true(),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="Unknown state id"):
        MacroStepFormal(source, (bad_target, fallback))

    bad_event = CycleCase(
        "transition",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        "%s::transition::%s::1" % (source.source_state_path, source.source_state_path),
        BoolTemplate.true(),
        (),
        used_events=(EventUse(999, "Missing.Event", "positive", "trigger"),),
    )
    with pytest.raises(InvalidBmcEncoding, match="Unknown event id"):
        MacroStepFormal(source, (bad_event, fallback))

    unknown_accepted = CycleCase(
        "fallback",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        "%s::fallback::%s::1" % (source.source_state_path, source.source_state_path),
        BoolTemplate.atom("accepted:no-such-label"),
        (),
    )
    with pytest.raises(InvalidBmcEncoding, match="unknown case label"):
        MacroStepFormal(source, (unknown_accepted,))


@pytest.mark.unittest
def test_macro_step_formal_rejects_illegal_delta_buckets_and_label_collisions(
    macro_domain,
):
    """Formal buckets enforce source-local shape before solver lowering."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    fallback = build_fallback_case(macro_domain, stable, ())
    delta = CycleCase(
        "delta",
        stable.source_state_id,
        stable.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::delta::%s::0" % (stable.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        (),
        domain=macro_domain,
    )

    assert MacroStepFormal(stable, (fallback,)).cases == (fallback,)
    with pytest.raises(InvalidBmcEncoding, match="delta_cases require"):
        MacroStepFormal(stable, (fallback,), (delta,))
    with pytest.raises(InvalidBmcEncoding, match="Duplicate cycle case label"):
        MacroStepFormal(stable, (fallback, fallback))
    wrong_source = make_case(macro_domain, entry_source(macro_domain, "Root.Plant"))
    with pytest.raises(InvalidBmcEncoding, match="case source id"):
        MacroStepFormal(stable, (wrong_source,))


@pytest.mark.unittest
def test_macro_step_formal_accepts_entry_delta_and_sentinel_absorb_buckets(
    macro_domain,
):
    """Entry formals and sentinel formals accept their dedicated bucket shapes."""
    entry = entry_source(macro_domain, "Root.Plant")
    delta = build_semantic_delta_case(macro_domain, entry, ())
    assert MacroStepFormal(entry, (), (delta,)).delta_cases == (delta,)

    terminate = MacroStepFormal(
        terminated_source(macro_domain),
        (terminated_absorb_case(macro_domain),),
    )
    diagnostic = MacroStepFormal(
        diagnostic_source(macro_domain),
        (diagnostic_absorb_case(macro_domain),),
    )
    assert terminate.cases[0].target_state_id == STATE_TERMINATE_ID
    assert diagnostic.cases[0].target_state_id == STATE_DIAGNOSTIC_ID


@pytest.mark.unittest
def test_verify_boolean_partition_reports_gaps_overlaps_and_budget():
    """Truth-table checker stays build-time only and reports hard failures."""
    a = BoolTemplate.atom("event:Root.Go")

    assert verify_boolean_partition((a, BoolTemplate.not_(a))).bucket_count == 2
    with pytest.raises(BmcBuildError, match="overlap"):
        verify_boolean_partition((a, BoolTemplate.true()))
    with pytest.raises(BmcBuildError, match="gap"):
        verify_boolean_partition((a, BoolTemplate.false()))
    with pytest.raises(BmcBuildError, match="assignment budget"):
        verify_boolean_partition(
            (BoolTemplate.true(),),
            variables=("event:Root.A", "event:Root.B"),
            max_assignments=2,
        )


@pytest.mark.unittest
def test_verify_boolean_partition_rejects_unknown_atom_namespace():
    """Public partition checks fail closed on non-canonical atom prefixes."""
    atom = BoolTemplate.atom("opaque:bad")

    with pytest.raises(InvalidBmcEncoding, match="atom namespace"):
        verify_boolean_partition((atom, BoolTemplate.not_(atom)), max_assignments=4)


@pytest.mark.unittest
def test_structural_partition_checker_handles_large_priority_masks():
    """Large canonical accepted/fallback masks avoid truth-table budget failures."""
    source = stable_leaf_source(
        build_bmc_domain(load_state_machine_from_text("state Root;"), 1), "Root"
    )

    result = verify_source_partition(source, make_large_priority_partition(source))

    assert result.bucket_count == 14
    assert len(result.variables) == 13
    assert result.assignment_count == 0


@pytest.mark.unittest
def test_structural_partition_checker_rejects_extra_accepted_atoms():
    """Structural budget bypass applies only to exact canonical accepted masks."""
    source = stable_leaf_source(
        build_bmc_domain(load_state_machine_from_text("state Root;"), 1), "Root"
    )

    def inject_positive_accepted(index, accepted, condition):
        if index != 1:
            return condition
        return BoolTemplate.and_(
            condition, BoolTemplate.atom("accepted:%s" % accepted[0].label)
        )

    with pytest.raises(BmcBuildError, match="assignment budget"):
        verify_source_partition(
            source,
            make_large_priority_partition(source, inject_positive_accepted),
        )


@pytest.mark.unittest
def test_bmc_macro_import_does_not_load_z3_or_verify_modules():
    """Importing macro contracts remains independent from solver and verify."""
    code = (
        "import sys; "
        "import pyfcstm.bmc.macro; "
        "bad = ["
        "name for name in sys.modules "
        "if name == 'z3' or name.startswith('pyfcstm.verify')"
        "]; "
        "print(bad)"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.strip() == "[]"
