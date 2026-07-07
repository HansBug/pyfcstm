"""Public API tests for BMC relation building."""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest
import z3

from pyfcstm.bmc import BmcBuildError, BmcEngine, BmcTraceSymbols, build_bmc_domain
from pyfcstm.bmc.macro import BoolTemplate, CycleCase
from pyfcstm.bmc.relation import BmcCaseRelation, BmcCoreFormula, BmcStepRelation
from pyfcstm.bmc.relation import build_bmc_core_formula
from pyfcstm.model import load_state_machine_from_text


@pytest.mark.unittest
def test_relation_public_exports_are_lazy_and_complete() -> None:
    """The relation builder is public without exposing unstable options."""
    bmc = importlib.import_module("pyfcstm.bmc")
    relation = importlib.import_module("pyfcstm.bmc.relation")

    expected = {
        "BmcTraceSymbols",
        "BmcCaseRelation",
        "BmcStepRelation",
        "BmcCoreFormula",
        "build_bmc_core_formula",
    }

    assert expected.issubset(set(bmc.__all__))
    assert expected.issubset(set(dir(bmc)))
    assert set(relation.__all__) == expected
    assert "BmcRelationOptions" not in bmc.__all__
    assert not hasattr(relation, "BmcRelationOptions")
    assert bmc.BmcTraceSymbols.__name__ == "BmcTraceSymbols"
    assert callable(bmc.build_bmc_core_formula)


@pytest.mark.unittest
def test_bmc_root_import_still_does_not_load_z3_or_verify() -> None:
    """Adding relation exports keeps root import lazy and verify-independent."""
    code = (
        "import sys; "
        "import pyfcstm.bmc; "
        "bad = [name for name in sys.modules "
        "if name == 'z3' or name.startswith('pyfcstm.verify')]; "
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


@pytest.mark.unittest
def test_trace_symbols_allocate_frames_events_and_cases() -> None:
    """Trace symbols expose frame, event, and case lookup helpers."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            state A;
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare('check reach <= 1: active("Root.A");')

    symbols = BmcTraceSymbols.allocate(context.domain, {0: ("case0",)})

    assert symbols.frame_state(0).decl().name() == "F_0_state"
    assert symbols.frame_var(0, "x").sort().name() == "Int"
    assert symbols.event_input(0, "Root.Go").sort().name() == "Bool"
    assert symbols.case_selector(0, "case0").sort().name() == "Bool"
    assert symbols.to_canonical()["node"] == "bmc_trace_symbols"


@pytest.mark.unittest
def test_trace_symbols_reject_invalid_public_lookups() -> None:
    """Trace symbol lookup helpers fail closed with BMC errors."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            state A;
            [*] -> A;
        }
        """
    )
    symbols = BmcTraceSymbols.allocate(build_bmc_domain(model, 1), {0: ("case0",)})

    with pytest.raises(BmcBuildError, match="frame index out of range"):
        symbols.frame_state(-1)
    with pytest.raises(BmcBuildError, match="Unknown frame variable"):
        symbols.frame_var(0, "missing")
    with pytest.raises(BmcBuildError, match="frame index out of range"):
        symbols.frame_var(2, "x")
    with pytest.raises(BmcBuildError, match="Unknown event input"):
        symbols.event_input(0, "Root.Missing")
    with pytest.raises(BmcBuildError, match="step index out of range"):
        symbols.event_input(1, "Root.Go")
    with pytest.raises(BmcBuildError, match="step index out of range"):
        symbols.delta_flag(1)
    with pytest.raises(BmcBuildError, match="step index out of range"):
        symbols.gamma_flag(1)
    with pytest.raises(BmcBuildError, match="Unknown case selector"):
        symbols.case_selector(0, "missing")
    with pytest.raises(BmcBuildError, match="step index out of range"):
        symbols.case_selector(1, "case0")


@pytest.mark.unittest
def test_trace_symbols_allocate_rejects_non_domain() -> None:
    """The allocator validates its public domain argument."""
    with pytest.raises(BmcBuildError, match="domain must be BmcDomain"):
        BmcTraceSymbols.allocate(object())


@pytest.mark.unittest
def test_trace_symbols_dataclass_validates_public_payload_shape() -> None:
    """Direct public construction validates symbol collection lengths."""
    domain = build_bmc_domain(load_state_machine_from_text("state Root;"), 1)
    frame_states = (z3.Int("s0"), z3.Int("s1"))
    frame_vars = ({}, {})
    event_inputs = ({},)
    delta_flags = (z3.Bool("delta0"),)
    gamma_flags = (z3.Bool("gamma0"),)
    case_selectors = ({},)

    with pytest.raises(BmcBuildError, match="domain must be BmcDomain"):
        BmcTraceSymbols(
            object(),
            frame_states,
            frame_vars,
            event_inputs,
            delta_flags,
            gamma_flags,
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="frame_states must contain"):
        BmcTraceSymbols(
            domain,
            (),
            frame_vars,
            event_inputs,
            delta_flags,
            gamma_flags,
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="frame_vars must contain"):
        BmcTraceSymbols(
            domain,
            frame_states,
            (),
            event_inputs,
            delta_flags,
            gamma_flags,
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="event_inputs must contain"):
        BmcTraceSymbols(
            domain,
            frame_states,
            frame_vars,
            (),
            delta_flags,
            gamma_flags,
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="delta_flags must contain"):
        BmcTraceSymbols(
            domain,
            frame_states,
            frame_vars,
            event_inputs,
            (),
            gamma_flags,
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="gamma_flags must contain"):
        BmcTraceSymbols(
            domain,
            frame_states,
            frame_vars,
            event_inputs,
            delta_flags,
            (),
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="delta_flags must contain Z3 Boolean"):
        BmcTraceSymbols(
            domain,
            frame_states,
            frame_vars,
            event_inputs,
            (z3.Int("not_delta_bool"),),
            gamma_flags,
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="gamma_flags must contain Z3 Boolean"):
        BmcTraceSymbols(
            domain,
            frame_states,
            frame_vars,
            event_inputs,
            delta_flags,
            (z3.Int("not_gamma_bool"),),
            case_selectors,
        )
    with pytest.raises(BmcBuildError, match="case_selectors must contain"):
        BmcTraceSymbols(
            domain, frame_states, frame_vars, event_inputs, delta_flags, gamma_flags, ()
        )


@pytest.mark.unittest
def test_trace_symbols_duplicate_case_labels_report_internal_bug() -> None:
    """Duplicate case labels are internal builder bugs with issue guidance."""
    domain = build_bmc_domain(load_state_machine_from_text("state Root;"), 1)

    with pytest.raises(BmcBuildError, match="internal BMC bug") as error_info:
        BmcTraceSymbols.allocate(domain, {0: ("case0", "case0")})

    assert "https://github.com/HansBug/pyfcstm/issues" in str(error_info.value)


@pytest.mark.unittest
def test_relation_dataclasses_validate_public_payload_shape() -> None:
    """Public relation dataclasses reject malformed Z3 payloads."""
    case = CycleCase(
        "fallback",
        0,
        "Root",
        0,
        "Root",
        "Root::fallback::Root::0",
        BoolTemplate.true(),
        (),
    )

    with pytest.raises(BmcBuildError, match="step_index must be an integer"):
        BmcCaseRelation(
            True,
            case,
            z3.Bool("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {},
            {},
            (),
        )
    with pytest.raises(BmcBuildError, match="selector must be a Z3 Boolean"):
        BmcCaseRelation(
            0,
            case,
            z3.Int("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {},
            {},
            (),
        )
    with pytest.raises(BmcBuildError, match="step_index must be non-negative"):
        BmcCaseRelation(
            -1,
            case,
            z3.Bool("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {},
            {},
            (),
        )
    with pytest.raises(BmcBuildError, match="case must be CycleCase"):
        BmcCaseRelation(
            0,
            object(),
            z3.Bool("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {},
            {},
            (),
        )
    with pytest.raises(BmcBuildError, match="post_var_exprs must contain"):
        BmcCaseRelation(
            0,
            case,
            z3.Bool("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {"x": z3.Bool("bad")},
            {},
            (),
        )
    with pytest.raises(BmcBuildError, match="guard_terms must contain"):
        BmcCaseRelation(
            0,
            case,
            z3.Bool("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {},
            {"g0": z3.Int("bad")},
            (),
        )
    with pytest.raises(BmcBuildError, match="definedness_constraints must contain"):
        BmcCaseRelation(
            0,
            case,
            z3.Bool("selector"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            {},
            {},
            (object(),),
        )
    with pytest.raises(BmcBuildError, match="step_index must be an integer"):
        BmcStepRelation(True, (), (), z3.BoolVal(True))
    with pytest.raises(BmcBuildError, match="step_index must be non-negative"):
        BmcStepRelation(-1, (), (), z3.BoolVal(True))
    with pytest.raises(BmcBuildError, match="case_relations must contain"):
        BmcStepRelation(0, (), (object(),), z3.BoolVal(True))
    with pytest.raises(BmcBuildError, match="formals must contain"):
        BmcStepRelation(0, (object(),), (), z3.BoolVal(True))
    with pytest.raises(BmcBuildError, match="formula must be a Z3 Boolean"):
        BmcStepRelation(0, (), (), z3.Int("bad"))
    with pytest.raises(BmcBuildError, match="delta_constraint must be"):
        BmcStepRelation(0, (), (), z3.BoolVal(True), z3.Int("bad_delta"))
    with pytest.raises(BmcBuildError, match="gamma_constraint must be"):
        BmcStepRelation(
            0,
            (),
            (),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.Int("bad_gamma"),
        )
    with pytest.raises(BmcBuildError, match="progress_mutex_constraint must be"):
        BmcStepRelation(
            0,
            (),
            (),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.Int("bad_mutex"),
        )
    assert BmcStepRelation(0, (), (), z3.BoolVal(True)).case_registry == {}


@pytest.mark.unittest
def test_core_formula_dataclass_validates_public_payload_shape() -> None:
    """Core formula payloads reject malformed symbols, formulas, and steps."""
    context = BmcEngine(load_state_machine_from_text("state Root;")).prepare(
        "check reach <= 1: terminated();"
    )
    symbols = BmcTraceSymbols.allocate(context.domain)

    with pytest.raises(BmcBuildError, match="symbols must be BmcTraceSymbols"):
        BmcCoreFormula(
            context,
            object(),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            (),
            (),
        )
    with pytest.raises(BmcBuildError, match="domain_formula must be a Z3 Boolean"):
        BmcCoreFormula(
            context,
            symbols,
            z3.Int("bad"),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            (),
            (),
        )
    with pytest.raises(BmcBuildError, match="steps must contain"):
        BmcCoreFormula(
            context,
            symbols,
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            (object(),),
            (),
        )
    with pytest.raises(BmcBuildError, match="diagnostics must contain"):
        BmcCoreFormula(
            context,
            symbols,
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            z3.BoolVal(True),
            (),
            (object(),),
        )


@pytest.mark.unittest
def test_core_builder_rejects_context_domain_from_different_model() -> None:
    """The public builder catches inconsistent prepared context internals."""
    from pyfcstm.bmc.engine import BmcPreparedContext

    model = load_state_machine_from_text("state Root;")
    other_model = load_state_machine_from_text("state Other;")
    context = BmcEngine(model).prepare("check reach <= 1: terminated();")
    mismatched = BmcPreparedContext(
        model=context.model,
        query=context.query,
        bound_query=context.bound_query,
        domain=build_bmc_domain(other_model, context.bound),
        options=context.options,
        source_text=context.source_text,
    )

    with pytest.raises(BmcBuildError, match="context.domain must be built"):
        build_bmc_core_formula(mismatched)


@pytest.mark.unittest
def test_build_bmc_core_formula_rejects_non_context() -> None:
    """The public relation entry validates only its public boundary input."""
    with pytest.raises(BmcBuildError, match="context must be BmcPreparedContext"):
        build_bmc_core_formula(object())
