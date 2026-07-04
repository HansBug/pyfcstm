"""Macro-step case contract tests for FCSTM BMC."""

from __future__ import annotations

import subprocess
import sys

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
    TERMINATE_CASE_PATH,
    diagnostic_source,
    entry_source,
    stable_leaf_source,
    terminated_source,
)
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.expr import Boolean, Variable


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
