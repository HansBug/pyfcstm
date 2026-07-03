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
    BoolTemplate,
    CycleCase,
    EventUse,
    MacroStepFormal,
    VarUpdate,
    build_fallback_case,
    build_semantic_delta_case,
    build_var_updates,
    carry_var_updates,
    case_antecedent_condition,
    diagnostic_absorb_case,
    terminated_absorb_case,
    var_update_for,
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


@pytest.fixture()
def macro_domain():
    """Build a macro-contract fixture with variables and same-short-name events."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        def float y = 1.0;
        state Root {
            event Go;
            state Plant {
                event Ping;
                state Idle;
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
    return build_bmc_domain(model, bound=2)


def make_case(
    domain, source, label_kind="transition", condition=None, target_path=None, ordinal=0
):
    """Create a valid synthetic case for contract tests."""
    if condition is None:
        condition = BoolTemplate.atom("g%d" % ordinal)
    if target_path is None:
        target_path = source.source_state_path
    target_id = domain.state_path_to_id(target_path)
    return CycleCase(
        label_kind,
        source.source_state_id,
        source.source_state_path,
        target_id,
        target_path,
        "%s::%s::%s::%d" % (source.source_state_path, label_kind, target_path, ordinal),
        condition,
        carry_var_updates(domain),
        domain=domain,
    )


@pytest.mark.unittest
def test_cycle_case_condition_is_bare_gamma_and_source_guard_is_composed_later(
    macro_domain,
):
    """CycleCase.condition excludes the pre-state source guard by contract."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    gamma = BoolTemplate.atom("trigger")
    case = make_case(macro_domain, source, condition=gamma)

    assert case.condition is gamma
    assert case.condition.variables == ("trigger",)
    assert (
        case_antecedent_condition(case).to_canonical()
        == BoolTemplate.and_(
            BoolTemplate.atom("source_state:%d" % source.source_state_id),
            gamma,
        ).to_canonical()
    )


@pytest.mark.unittest
def test_case_target_and_event_use_must_match_domain(macro_domain):
    """Cases validate target ids and full event paths, including same short names."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    plant_ping = macro_domain.event_by_path("Root.Plant.Ping")
    backup_ping = macro_domain.event_by_path("Root.Backup.Ping")

    case = CycleCase(
        "transition",
        source.source_state_id,
        source.source_state_path,
        macro_domain.state_path_to_id("Root.Plant.Busy"),
        "Root.Plant.Busy",
        "%s::transition::Root.Plant.Busy::0" % source.source_state_path,
        BoolTemplate.atom("ping"),
        carry_var_updates(macro_domain),
        used_events=(EventUse(plant_ping.id, plant_ping.path, "positive", "trigger"),),
        domain=macro_domain,
    )
    assert case.used_events[0].event_id != backup_ping.id
    assert case.used_events[0].path == "Root.Plant.Ping"

    with pytest.raises(InvalidBmcEncoding, match="target path"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            macro_domain.state_path_to_id("Root.Plant.Busy"),
            "Root.Backup.Idle",
            "%s::transition::Root.Backup.Idle::0" % source.source_state_path,
            BoolTemplate.atom("bad_target"),
            carry_var_updates(macro_domain),
            domain=macro_domain,
        )
    with pytest.raises(InvalidBmcEncoding, match="EventUse path"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::transition::%s::1"
            % (source.source_state_path, source.source_state_path),
            BoolTemplate.atom("bad_event"),
            carry_var_updates(macro_domain),
            used_events=(
                EventUse(plant_ping.id, backup_ping.path, "positive", "trigger"),
            ),
            domain=macro_domain,
        )


@pytest.mark.unittest
def test_var_update_requires_complete_explicit_persistent_var_coverage(macro_domain):
    """Writeback recipes cover every persistent var and reject unknown or duplicate entries."""
    complete = carry_var_updates(macro_domain)
    assert [item.variable_name for item in complete] == ["x", "y"]
    assert all(item.is_carry for item in complete)
    assert build_var_updates(macro_domain, complete) == complete
    assert var_update_for(macro_domain, "x", "x+1").to_canonical() == {
        "node": "var_update",
        "variable_id": macro_domain.variable_name_to_id("x"),
        "variable_name": "x",
        "expression": "x+1",
        "is_carry": False,
    }

    with pytest.raises(InvalidBmcEncoding, match="cover every"):
        build_var_updates(macro_domain, complete[:1])
    with pytest.raises(InvalidBmcEncoding, match="Duplicate variable update id"):
        build_var_updates(macro_domain, complete + (complete[0],))
    with pytest.raises(InvalidBmcEncoding, match="Unknown variable id"):
        build_var_updates(macro_domain, complete + (VarUpdate(999, "z", "0"),))
    with pytest.raises(InvalidBmcEncoding, match="id/name mismatch"):
        build_var_updates(
            macro_domain,
            (VarUpdate(complete[0].variable_id, "y", "pre:y"),) + complete[1:],
        )


@pytest.mark.unittest
def test_absorb_cases_are_regular_cases_with_true_gamma_and_carry_all(macro_domain):
    """Terminated and diagnostic absorbs are ordinary CycleCase objects."""
    terminate = terminated_absorb_case(macro_domain)
    diagnostic = diagnostic_absorb_case(macro_domain)

    assert terminate.source_state_id == STATE_TERMINATE_ID
    assert terminate.target_state_id == STATE_TERMINATE_ID
    assert terminate.source_state_path == TERMINATE_CASE_PATH
    assert terminate.label == "__terminate__::absorb::__terminate__::0"
    assert terminate.condition.evaluate({}) is True
    assert terminate.is_diagnostic is False
    assert [item.variable_name for item in terminate.var_update] == ["x", "y"]

    assert diagnostic.source_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.target_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.source_state_path == DIAGNOSTIC_CASE_PATH
    assert diagnostic.label == "__diagnostic__::absorb::__diagnostic__::0"
    assert diagnostic.condition.evaluate({}) is True
    assert diagnostic.is_diagnostic is True


@pytest.mark.unittest
def test_fallback_condition_negates_only_accepted_gamma_not_failed_metadata(
    macro_domain,
):
    """Failed raw candidates do not shrink stable leaf fallback uncovered space."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    accepted = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("accepted"),
        target_path="Root.Plant.Busy",
    )
    failed = BoolTemplate.atom("failed_raw")

    fallback = build_fallback_case(macro_domain, source, (accepted,), (failed,))

    assert fallback.kind == "fallback"
    assert (
        fallback.condition.to_canonical()
        == BoolTemplate.not_(BoolTemplate.atom("accepted")).to_canonical()
    )
    assert fallback.failed_conditions == (failed,)
    assert fallback.condition.evaluate({"accepted": False, "failed_raw": True}) is True
    assert fallback.condition.evaluate({"accepted": True, "failed_raw": False}) is False


@pytest.mark.unittest
def test_semantic_delta_condition_excludes_success_and_build_diag_not_failed(
    macro_domain,
):
    """Entry delta leaves failed candidate conditions as diagnostics only."""
    source = entry_source(macro_domain, "Root.Plant")
    accepted = make_case(
        macro_domain,
        source,
        condition=BoolTemplate.atom("accepted"),
        target_path="Root.Plant.Idle",
    )
    build_diag = BoolTemplate.atom("unsupported")
    failed = BoolTemplate.atom("failed_raw")

    delta = build_semantic_delta_case(
        macro_domain, source, (accepted,), (build_diag,), (failed,)
    )

    expected = BoolTemplate.not_(
        BoolTemplate.or_(BoolTemplate.atom("accepted"), build_diag)
    )
    assert delta.kind == "delta"
    assert delta.target_state_id == STATE_DIAGNOSTIC_ID
    assert delta.is_diagnostic is True
    assert delta.condition.to_canonical() == expected.to_canonical()
    assert delta.failed_conditions == (failed,)
    assert (
        delta.condition.evaluate(
            {"accepted": False, "unsupported": False, "failed_raw": True}
        )
        is True
    )


@pytest.mark.unittest
def test_macro_step_formal_rejects_illegal_delta_buckets_and_label_collisions(
    macro_domain,
):
    """Formal buckets enforce source-local shape before runtime expansion is implemented."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    fallback = build_fallback_case(macro_domain, stable, ())
    delta = CycleCase(
        "delta",
        stable.source_state_id,
        stable.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::delta::%s::0" % (stable.source_state_path, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.atom("delta"),
        carry_var_updates(macro_domain),
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
    """Entry formals may contain delta while sentinel formals absorb exactly once."""
    entry = entry_source(macro_domain, "Root.Plant")
    success = make_case(
        macro_domain,
        entry,
        condition=BoolTemplate.atom("ok"),
        target_path="Root.Plant.Idle",
    )
    delta = build_semantic_delta_case(macro_domain, entry, (success,))
    formal = MacroStepFormal(entry, (success,), (delta,))
    assert formal.cases == (success, delta)
    assert [case.kind for case in formal.delta_cases] == ["delta"]

    terminated_formal = MacroStepFormal(
        terminated_source(macro_domain),
        (terminated_absorb_case(macro_domain),),
    )
    diagnostic_formal = MacroStepFormal(
        diagnostic_source(macro_domain),
        (diagnostic_absorb_case(macro_domain),),
    )
    assert terminated_formal.success_cases[0].is_diagnostic is False
    assert diagnostic_formal.success_cases[0].is_diagnostic is True

    with pytest.raises(InvalidBmcEncoding, match="Duplicate cycle case label"):
        MacroStepFormal(
            terminated_source(macro_domain),
            (
                terminated_absorb_case(macro_domain),
                terminated_absorb_case(macro_domain),
            ),
        )


@pytest.mark.unittest
def test_partition_verifier_accepts_complete_disjoint_stable_and_entry_universes(
    macro_domain,
):
    """Synthetic truth-table partitions prove fallback and delta bucket contracts."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    accepted = make_case(
        macro_domain,
        stable,
        condition=BoolTemplate.atom("accepted"),
        target_path="Root.Plant.Busy",
    )
    fallback = build_fallback_case(macro_domain, stable, (accepted,))
    result = MacroStepFormal(stable, (accepted, fallback)).verify_partition()
    assert result.to_canonical() == {
        "node": "partition_check_result",
        "variables": ["accepted"],
        "assignment_count": 2,
        "bucket_count": 2,
        "scope": "build-time-self-check",
    }

    entry = entry_source(macro_domain, "Root.Plant")
    success = make_case(
        macro_domain,
        entry,
        condition=BoolTemplate.atom("success"),
        target_path="Root.Plant.Idle",
    )
    build_diag = BoolTemplate.and_(
        BoolTemplate.atom("build_diag"),
        BoolTemplate.not_(BoolTemplate.atom("success")),
    )
    delta = build_semantic_delta_case(macro_domain, entry, (success,), (build_diag,))
    entry_result = MacroStepFormal(
        entry, (success,), (delta,), (build_diag,)
    ).verify_partition()
    assert entry_result.variables == ("build_diag", "success")
    assert entry_result.bucket_count == 3


@pytest.mark.unittest
def test_partition_verifier_fails_closed_on_gap_overlap_and_unknown_budget():
    """Partition self-checks fail closed and never become Core_N clauses."""
    a = BoolTemplate.atom("a")
    with pytest.raises(BmcBuildError, match="overlap"):
        verify_boolean_partition((a, a, BoolTemplate.not_(a)))
    with pytest.raises(BmcBuildError, match="gap"):
        verify_boolean_partition((a,))
    with pytest.raises(BmcBuildError, match="assignment budget"):
        verify_boolean_partition(
            (a, BoolTemplate.not_(a)), variables=("a", "b"), max_assignments=2
        )

    result = verify_boolean_partition((a, BoolTemplate.not_(a)))
    assert "clauses" not in result.to_canonical()
    assert result.to_canonical()["scope"] == "build-time-self-check"


@pytest.mark.unittest
def test_case_validation_rejects_label_kind_and_primitive_mismatches(macro_domain):
    """CycleCase and metadata constructors fail on malformed contract values."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    with pytest.raises(InvalidBmcEncoding, match="label case kind"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::fallback::%s::0"
            % (source.source_state_path, source.source_state_path),
            BoolTemplate.true(),
            carry_var_updates(macro_domain),
            domain=macro_domain,
        )
    with pytest.raises(InvalidBmcEncoding, match="event_id"):
        EventUse(-1, "Root.Go", "positive", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="event polarity"):
        EventUse(0, "Root.Go", "maybe", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="boolean template kind"):
        BoolTemplate("xor")
    with pytest.raises(InvalidBmcEncoding, match="Unknown state id"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            9999,
            "Missing",
            "%s::transition::Missing::0" % source.source_state_path,
            BoolTemplate.true(),
            carry_var_updates(macro_domain),
            domain=macro_domain,
        )
    with pytest.raises(InvalidBmcEncoding, match="operands"):
        BoolTemplate.or_(BoolTemplate.atom("ok"), object())


@pytest.mark.unittest
def test_macro_imports_do_not_load_z3_or_verify_modules():
    """Macro contracts stay solver-independent and verify-registry independent."""
    code = (
        "import sys; "
        "import pyfcstm.bmc.macro; "
        "print('z3' in sys.modules); "
        "print(any(name.startswith('pyfcstm.verify') for name in sys.modules))"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.splitlines() == ["False", "False"]


@pytest.mark.unittest
def test_bool_template_validation_and_evaluation_fail_closed():
    """BoolTemplate rejects malformed recipes and evaluation unknowns."""
    atom = BoolTemplate.atom("a")

    with pytest.raises(InvalidBmcEncoding, match="operands"):
        BoolTemplate("atom", name="a", operands=(atom,))
    with pytest.raises(InvalidBmcEncoding, match="names"):
        BoolTemplate("true", name="a")
    with pytest.raises(InvalidBmcEncoding, match="operands"):
        BoolTemplate("false", operands=(atom,))
    with pytest.raises(InvalidBmcEncoding, match="names"):
        BoolTemplate("not", name="a", operands=(atom,))
    with pytest.raises(InvalidBmcEncoding, match="one operand"):
        BoolTemplate("not")
    with pytest.raises(InvalidBmcEncoding, match="names"):
        BoolTemplate("and", name="a", operands=(atom,))
    with pytest.raises(InvalidBmcEncoding, match="must have operands"):
        BoolTemplate("or")
    with pytest.raises(BmcBuildError, match="missing boolean assignment"):
        atom.evaluate({})
    with pytest.raises(BmcBuildError, match="must be bool"):
        atom.evaluate({"a": 1})

    forged = BoolTemplate.true()
    object.__setattr__(forged, "kind", "xor")
    with pytest.raises(BmcBuildError, match="unsupported boolean"):
        forged.evaluate({})


@pytest.mark.unittest
def test_event_and_var_update_validation_rejects_malformed_metadata(macro_domain):
    """EventUse and VarUpdate reject malformed primitive metadata."""
    with pytest.raises(InvalidBmcEncoding, match="event_id"):
        EventUse(True, "Root.Go", "positive", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="event_id"):
        EventUse(-1, "Root.Go", "positive", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="event path"):
        EventUse(0, "", "positive", "trigger")
    with pytest.raises(InvalidBmcEncoding, match="event reason"):
        EventUse(0, "Root.Go", "positive", "unknown")

    with pytest.raises(InvalidBmcEncoding, match="variable_id"):
        VarUpdate(True, "x", "pre:x")
    with pytest.raises(InvalidBmcEncoding, match="non-negative"):
        VarUpdate(-1, "x", "pre:x")
    with pytest.raises(InvalidBmcEncoding, match="variable_name"):
        VarUpdate(0, "", "pre:x")
    with pytest.raises(InvalidBmcEncoding, match="expression"):
        VarUpdate(0, "x", "")
    with pytest.raises(InvalidBmcEncoding, match="is_carry"):
        VarUpdate(0, "x", "pre:x", is_carry=object())
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        carry_var_updates(object())
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        var_update_for(object(), "x", "pre:x")
    with pytest.raises(InvalidBmcEncoding, match="variable must"):
        var_update_for(macro_domain, object(), "pre:x")
    with pytest.raises(InvalidBmcEncoding, match="Unknown variable name"):
        var_update_for(macro_domain, "missing", "0")
    with pytest.raises(InvalidBmcEncoding, match="updates must be a sequence"):
        build_var_updates(macro_domain, object())
    with pytest.raises(InvalidBmcEncoding, match="VarUpdate"):
        build_var_updates(macro_domain, (object(),))
    duplicate_name = (
        VarUpdate(macro_domain.variable_name_to_id("x"), "x", "pre:x"),
        VarUpdate(macro_domain.variable_name_to_id("y"), "x", "pre:x"),
    )
    with pytest.raises(InvalidBmcEncoding, match="Duplicate variable update name"):
        build_var_updates(macro_domain, duplicate_name)


@pytest.mark.unittest
def test_cycle_case_validation_rejects_malformed_contract_fields(macro_domain):
    """CycleCase rejects malformed labels, metadata, and kind-specific shapes."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    carry = carry_var_updates(macro_domain)
    label = "%s::transition::%s::0" % (
        source.source_state_path,
        source.source_state_path,
    )

    with pytest.raises(InvalidBmcEncoding, match="condition"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            label,
            object(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="used_events"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            label,
            BoolTemplate.true(),
            carry,
            used_events=(object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            label,
            BoolTemplate.true(),
            carry,
            failed_conditions=(object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="var_update"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            label,
            BoolTemplate.true(),
            (object(),),
        )
    with pytest.raises(InvalidBmcEncoding, match="source::kind"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "bad",
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="label source"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "Other::transition::%s::0" % source.source_state_path,
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="label target"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::transition::Other::0" % source.source_state_path,
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="ordinal"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::transition::%s::x"
            % (source.source_state_path, source.source_state_path),
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="self-loop"):
        CycleCase(
            "absorb",
            STATE_TERMINATE_ID,
            TERMINATE_CASE_PATH,
            STATE_DIAGNOSTIC_ID,
            DIAGNOSTIC_CASE_PATH,
            "%s::absorb::%s::0" % (TERMINATE_CASE_PATH, DIAGNOSTIC_CASE_PATH),
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="sentinel"):
        CycleCase(
            "absorb",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::absorb::%s::0" % (source.source_state_path, source.source_state_path),
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="target diagnostic"):
        CycleCase(
            "delta",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::delta::%s::0" % (source.source_state_path, source.source_state_path),
            BoolTemplate.true(),
            carry,
        )
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            label,
            BoolTemplate.true(),
            carry,
            domain=object(),
        )


@pytest.mark.unittest
def test_macro_step_formal_validation_rejects_bucket_shape_errors(macro_domain):
    """MacroStepFormal validates bucket types, source matches, and sentinel formals."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    entry = entry_source(macro_domain, "Root.Plant")
    transition = make_case(macro_domain, entry, target_path="Root.Plant.Idle")
    stable_transition = make_case(macro_domain, stable)
    fallback = build_fallback_case(macro_domain, stable, (stable_transition,))

    with pytest.raises(InvalidBmcEncoding, match="source"):
        MacroStepFormal(object(), (fallback,))
    with pytest.raises(InvalidBmcEncoding, match="success_cases"):
        MacroStepFormal(stable, (object(),))
    with pytest.raises(InvalidBmcEncoding, match="delta_cases"):
        MacroStepFormal(entry, (transition,), object())
    with pytest.raises(InvalidBmcEncoding, match="delta_cases"):
        MacroStepFormal(entry, (transition,), (object(),))
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic"):
        MacroStepFormal(entry, (transition,), (), (object(),))
    with pytest.raises(InvalidBmcEncoding, match="at least one"):
        MacroStepFormal(entry, ())
    with pytest.raises(InvalidBmcEncoding, match="fallback"):
        MacroStepFormal(stable, (stable_transition,))
    with pytest.raises(InvalidBmcEncoding, match="build diagnostics"):
        MacroStepFormal(stable, (fallback,), (), (BoolTemplate.atom("diag"),))
    misplaced_delta = build_semantic_delta_case(macro_domain, entry, (transition,))
    with pytest.raises(InvalidBmcEncoding, match="success_cases"):
        MacroStepFormal(entry, (misplaced_delta,))
    non_delta = make_case(macro_domain, entry, target_path="Root.Plant.Idle")
    with pytest.raises(InvalidBmcEncoding, match="delta_cases may only"):
        MacroStepFormal(entry, (), (non_delta,))
    with pytest.raises(InvalidBmcEncoding, match="case source id"):
        MacroStepFormal(terminated_source(macro_domain), (transition,))
    wrong_sentinel_case = CycleCase(
        "absorb",
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "__diagnostic__::absorb::__diagnostic__::0",
        BoolTemplate.true(),
        carry_var_updates(macro_domain),
        domain=macro_domain,
    )
    with pytest.raises(InvalidBmcEncoding, match="case source id"):
        MacroStepFormal(terminated_source(macro_domain), (wrong_sentinel_case,))


@pytest.mark.unittest
def test_fallback_and_delta_helpers_reject_bad_inputs(macro_domain):
    """Fallback and delta helper constructors validate source and metadata shape."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    other_stable = stable_leaf_source(macro_domain, "Root.Backup.Idle")
    entry = entry_source(macro_domain, "Root.Plant")
    other_entry = entry_source(macro_domain, "Root.Backup")
    stable_case = make_case(macro_domain, stable)
    other_stable_case = make_case(macro_domain, other_stable)
    entry_case = make_case(macro_domain, entry, target_path="Root.Plant.Idle")
    other_entry_case = make_case(
        macro_domain, other_entry, target_path="Root.Backup.Idle"
    )

    with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
        build_fallback_case(macro_domain, entry, ())
    with pytest.raises(InvalidBmcEncoding, match="ordinal"):
        build_fallback_case(macro_domain, stable, (), ordinal=-1)
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        build_fallback_case(macro_domain, stable, (object(),))
    with pytest.raises(InvalidBmcEncoding, match="fallback source"):
        build_fallback_case(macro_domain, stable, (other_stable_case,))
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        build_fallback_case(macro_domain, stable, (stable_case,), (object(),))

    with pytest.raises(InvalidBmcEncoding, match="entry source"):
        build_semantic_delta_case(macro_domain, stable, ())
    with pytest.raises(InvalidBmcEncoding, match="ordinal"):
        build_semantic_delta_case(macro_domain, entry, (), ordinal=-1)
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        build_semantic_delta_case(macro_domain, entry, (object(),))
    with pytest.raises(InvalidBmcEncoding, match="delta source"):
        build_semantic_delta_case(macro_domain, entry, (other_entry_case,))
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic"):
        build_semantic_delta_case(macro_domain, entry, (entry_case,), (object(),))
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        build_semantic_delta_case(macro_domain, entry, (entry_case,), (), (object(),))


@pytest.mark.unittest
def test_partition_helpers_reject_bad_inputs_and_source_mismatches(macro_domain):
    """Partition self-check helpers reject malformed buckets and case ownership."""
    stable = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    entry = entry_source(macro_domain, "Root.Plant")
    other_entry = entry_source(macro_domain, "Root.Backup")
    delta = build_semantic_delta_case(macro_domain, entry, ())
    other_delta = build_semantic_delta_case(macro_domain, other_entry, ())

    with pytest.raises(BmcBuildError, match="at least one"):
        verify_boolean_partition(())
    with pytest.raises(BmcBuildError, match="BoolTemplate"):
        verify_boolean_partition((object(),))
    with pytest.raises(BmcBuildError, match="max_assignments"):
        verify_boolean_partition((BoolTemplate.true(),), max_assignments=True)
    with pytest.raises(BmcBuildError, match="max_assignments"):
        verify_boolean_partition((BoolTemplate.true(),), max_assignments=0)
    with pytest.raises(BmcBuildError, match="variables"):
        verify_boolean_partition((BoolTemplate.true(),), variables=("",))
    with pytest.raises(BmcBuildError, match="missing boolean assignment"):
        verify_boolean_partition((BoolTemplate.atom("a"),), variables=())

    with pytest.raises(InvalidBmcEncoding, match="source"):
        verify_source_partition(object(), (), ())
    with pytest.raises(InvalidBmcEncoding, match="entry source"):
        verify_source_partition(stable, (), (delta,))
    with pytest.raises(InvalidBmcEncoding, match="CycleCase"):
        verify_source_partition(entry, (object(),), ())
    with pytest.raises(InvalidBmcEncoding, match="source id"):
        verify_source_partition(entry, (), (other_delta,))
    non_delta = make_case(macro_domain, entry, target_path="Root.Plant.Idle")
    with pytest.raises(InvalidBmcEncoding, match="delta_cases may only"):
        verify_source_partition(entry, (), (non_delta,))
    with pytest.raises(InvalidBmcEncoding, match="success_cases"):
        verify_source_partition(entry, (delta,), ())
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic"):
        verify_source_partition(entry, (), (delta,), (object(),))


@pytest.mark.unittest
def test_additional_macro_contract_branches_are_hardened(macro_domain):
    """Contract helpers cover no-domain, path-mismatch, and lookup-failure branches."""
    assert BoolTemplate.true().evaluate({}) is True
    assert BoolTemplate.false().evaluate({}) is False
    assert BoolTemplate.and_().kind == "true"
    assert BoolTemplate.and_(BoolTemplate.atom("a")) == BoolTemplate.atom("a")
    assert BoolTemplate.or_(BoolTemplate.atom("a")) == BoolTemplate.atom("a")
    with pytest.raises(InvalidBmcEncoding, match="operands"):
        BoolTemplate("and", operands=(object(),))

    with pytest.raises(InvalidBmcEncoding, match="Unknown variable id"):
        var_update_for(macro_domain, 999, "0")
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        build_var_updates(object(), ())

    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    carry = carry_var_updates(macro_domain)
    event = macro_domain.event_by_path("Root.Go")
    with pytest.raises(InvalidBmcEncoding, match="Unknown event id"):
        CycleCase(
            "transition",
            source.source_state_id,
            source.source_state_path,
            source.source_state_id,
            source.source_state_path,
            "%s::transition::%s::2"
            % (source.source_state_path, source.source_state_path),
            BoolTemplate.true(),
            carry,
            used_events=(EventUse(event.id + 1000, event.path, "positive", "trigger"),),
            domain=macro_domain,
        )
    plain = CycleCase(
        "transition",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        "%s::transition::%s::3" % (source.source_state_path, source.source_state_path),
        BoolTemplate.true(),
        carry,
    )
    assert plain.to_canonical()["label"].endswith("::3")
    with pytest.raises(InvalidBmcEncoding, match="case"):
        case_antecedent_condition(object())

    entry = entry_source(macro_domain, "Root.Plant")
    wrong_path_case = CycleCase(
        "delta",
        entry.source_state_id,
        "Other",
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "Other::delta::__diagnostic__::0",
        BoolTemplate.true(),
        carry,
    )
    with pytest.raises(InvalidBmcEncoding, match="case source path"):
        MacroStepFormal(entry, (), (wrong_path_case,))
    assert (
        MacroStepFormal(
            entry, (), (build_semantic_delta_case(macro_domain, entry, ()),)
        ).to_canonical()["node"]
        == "macro_step_formal"
    )

    diagnostic = diagnostic_source(macro_domain)
    diagnostic_case = diagnostic_absorb_case(macro_domain)
    with pytest.raises(InvalidBmcEncoding, match="case source id"):
        MacroStepFormal(
            diagnostic,
            (diagnostic_case,),
            (build_semantic_delta_case(macro_domain, entry, ()),),
        )
    non_absorb = CycleCase(
        "diagnostic",
        diagnostic.source_state_id,
        diagnostic.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "__diagnostic__::diagnostic::__diagnostic__::0",
        BoolTemplate.true(),
        carry,
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel formal case"):
        MacroStepFormal(diagnostic, (non_absorb,))
    with pytest.raises(InvalidBmcEncoding, match="case source id"):
        MacroStepFormal(diagnostic, (terminated_absorb_case(macro_domain),))

    accepted_wrong_path = CycleCase(
        "transition",
        source.source_state_id,
        "Other",
        source.source_state_id,
        source.source_state_path,
        "Other::transition::%s::0" % source.source_state_path,
        BoolTemplate.atom("wrong"),
        carry,
    )
    with pytest.raises(InvalidBmcEncoding, match="fallback source"):
        build_fallback_case(macro_domain, source, (accepted_wrong_path,))
    entry_wrong_path = CycleCase(
        "transition",
        entry.source_state_id,
        "Other",
        macro_domain.state_path_to_id("Root.Plant.Idle"),
        "Root.Plant.Idle",
        "Other::transition::Root.Plant.Idle::0",
        BoolTemplate.atom("wrong"),
        carry,
    )
    with pytest.raises(InvalidBmcEncoding, match="delta source"):
        build_semantic_delta_case(macro_domain, entry, (entry_wrong_path,))
    with pytest.raises(InvalidBmcEncoding, match="source path"):
        verify_source_partition(entry, (), (wrong_path_case,))


@pytest.mark.unittest
def test_macro_contract_sequence_type_guards_and_sentinel_absorb_branches(
    macro_domain,
):
    """Sequence guards and sentinel absorb invariants fail closed."""
    source = stable_leaf_source(macro_domain, "Root.Plant.Idle")
    entry = entry_source(macro_domain, "Root.Plant")
    diagnostic = diagnostic_source(macro_domain)
    terminate = terminated_source(macro_domain)
    carry = carry_var_updates(macro_domain)
    success = make_case(macro_domain, source, condition=BoolTemplate.atom("ok"))
    delta = build_semantic_delta_case(macro_domain, entry, ())

    with pytest.raises(InvalidBmcEncoding, match="success_cases"):
        MacroStepFormal(source, object())
    with pytest.raises(InvalidBmcEncoding, match="delta_cases"):
        MacroStepFormal(entry, (), object())
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic_conditions"):
        MacroStepFormal(entry, (), (delta,), object())

    with pytest.raises(InvalidBmcEncoding, match="case source id"):
        MacroStepFormal(diagnostic, (diagnostic_absorb_case(macro_domain),), (delta,))
    second_diagnostic_absorb = CycleCase(
        "absorb",
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "__diagnostic__::absorb::__diagnostic__::1",
        BoolTemplate.true(),
        carry,
    )
    with pytest.raises(InvalidBmcEncoding, match="must contain one case"):
        MacroStepFormal(
            diagnostic,
            (diagnostic_absorb_case(macro_domain), second_diagnostic_absorb),
        )
    wrong_sentinel_loop = CycleCase(
        "absorb",
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "__diagnostic__::absorb::__diagnostic__::1",
        BoolTemplate.true(),
        carry,
    )
    object.__setattr__(wrong_sentinel_loop, "source_state_id", STATE_TERMINATE_ID)
    object.__setattr__(wrong_sentinel_loop, "source_state_path", TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="self-loop sentinel id"):
        MacroStepFormal(terminate, (wrong_sentinel_loop,))

    with pytest.raises(InvalidBmcEncoding, match="accepted_cases"):
        build_fallback_case(macro_domain, source, object())
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        build_fallback_case(macro_domain, source, (success,), object())
    with pytest.raises(InvalidBmcEncoding, match="accepted_cases"):
        build_semantic_delta_case(macro_domain, entry, object())
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic_conditions"):
        build_semantic_delta_case(macro_domain, entry, (), object())
    with pytest.raises(InvalidBmcEncoding, match="failed_conditions"):
        build_semantic_delta_case(macro_domain, entry, (), (), object())

    with pytest.raises(BmcBuildError, match="partition buckets"):
        verify_boolean_partition(object())
    with pytest.raises(BmcBuildError, match="partition variables"):
        verify_boolean_partition((BoolTemplate.true(),), variables=object())
    with pytest.raises(InvalidBmcEncoding, match="success_cases"):
        verify_source_partition(source, object())
    with pytest.raises(InvalidBmcEncoding, match="delta_cases"):
        verify_source_partition(entry, (), object())
    with pytest.raises(InvalidBmcEncoding, match="build_diagnostic_conditions"):
        verify_source_partition(entry, (), (delta,), object())
