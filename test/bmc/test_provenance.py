"""TDD contracts for BMC source provenance and tracked relation groups."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import z3

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.bmc.parse import parse_bmc_query
from pyfcstm.bmc.provenance import (
    BmcSourceRef,
    BmcTrackedConstraint,
    SourceDocumentRegistry,
)
from pyfcstm.bmc.relation import BmcCoreFormula
from pyfcstm.model import load_state_machine_from_file, load_state_machine_from_text
from pyfcstm.utils.validate import Span


def test_source_registry_slices_multiline_span_exactly() -> None:
    """A source excerpt must be the exact half-open span slice."""
    source = "line one\n第二行内容\nline three"
    registry = SourceDocumentRegistry({"machine.fcstm": source})
    reference = BmcSourceRef(
        kind="fcstm",
        path="machine.fcstm",
        span=Span(line=1, column=6, end_line=2, end_column=4),
    )

    assert registry.excerpt(reference) == "one\n第二行"


def test_query_source_metadata_keeps_source_text_canonical_clean() -> None:
    """Query spans are available privately without changing canonical JSON."""
    text = 'init cold;\nassume at 0: var("x") == 1;\ncheck reach <= 1: true;'
    query = parse_bmc_query(text, source_path="query.fbmcq")

    assert query._source_path == "query.fbmcq"
    assert query._source_spans
    assert query.to_canonical() == {
        "node": "bmc_query",
        "initial": query.initial.to_canonical(),
        "assumptions": [item.to_canonical() for item in query.assumptions],
        "property": query.property.to_canonical(),
    }


def test_pathless_source_references_drop_unresolvable_spans() -> None:
    """Pathless FCSTM and FBMCQ metadata cannot retain misleading spans."""
    model = load_state_machine_from_text("def int x = 3;\nstate Root;")
    context = BmcEngine(model).prepare(
        'assume at 0: true;\ncheck reach <= 1: active("Root");',
        query_source_path=None,
    )
    core = build_bmc_core_formula(context)

    variable = next(
        group
        for group in core._tracked_groups
        if group.stable_id == "initial.variable.x"
    )
    assumption = next(
        group
        for group in core._tracked_groups
        if group.stable_id == "assumption.0000.frame.0000"
    )

    assert variable.source_ref.kind == "fcstm"
    assert variable.source_ref.path is None
    assert variable.source_ref.span is None
    assert context._source_registry.excerpt(variable.source_ref) is None
    assert assumption.source_ref.kind == "fbmcq"
    assert assumption.source_ref.path is None
    assert assumption.source_ref.span is None
    assert context._source_registry.excerpt(assumption.source_ref) is None
    assert variable.stable_id == "initial.variable.x"
    assert assumption.category == "assumption.frame"


def test_source_reference_drops_span_without_document_snapshot() -> None:
    """A path without a registered snapshot cannot support an exact span."""
    registry = SourceDocumentRegistry({})
    reference = registry.reference("fcstm", "missing.fcstm", Span(1, 1, 1, 8))

    assert reference.path == "missing.fcstm"
    assert reference.span is None
    assert registry.excerpt(reference) is None


def test_file_and_import_source_paths_are_not_collapsed(tmp_path: Path) -> None:
    """Imported model spans must retain the imported document path."""
    imported = tmp_path / "worker.fcstm"
    imported.write_text("state Worker;", encoding="utf-8")
    main = tmp_path / "main.fcstm"
    main.write_text(
        'state Root { import "./worker.fcstm" as Worker; [*] -> Worker; }',
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    worker = model.root_state.substates["Worker"]

    assert worker._source_path == str(imported.resolve())
    assert model._source_documents[str(main.resolve())] == main.read_text(
        encoding="utf-8"
    )
    assert model._source_documents[str(imported.resolve())] == imported.read_text(
        encoding="utf-8"
    )


def _conjoin(expressions):
    values = tuple(expressions)
    if not values:
        return z3.BoolVal(True)
    if len(values) == 1:
        return values[0]
    return z3.And(*values)


def test_tracked_groups_rebuild_each_aggregate_in_registration_order() -> None:
    """Tracked groups preserve every aggregate formula's old expression shape."""
    model = load_state_machine_from_text("state Root { state A; [*] -> A; }")
    context = BmcEngine(model).prepare(
        'assume always: cycle <= 2; check reach <= 2: active("Root.A");'
    )
    core = build_bmc_core_formula(context)
    groups = core._tracked_groups

    assert len({item.stable_id for item in groups}) == len(groups)
    assert all(item.expressions for item in groups)
    assert all(
        z3.is_bool(expression) for item in groups for expression in item.expressions
    )

    assert str(
        _conjoin(
            expression
            for item in groups
            if item.category == "domain.frame_state"
            for expression in item.expressions
        )
    ) == str(core.domain_formula)
    assert str(
        _conjoin(
            expression
            for item in groups
            if item.stage == "initialization"
            for expression in item.expressions
        )
    ) == str(core.initial_formula)
    assert str(
        _conjoin(
            expression
            for item in groups
            if item.category == "transition.step"
            for expression in item.expressions
        )
    ) == str(core.transition_formula)
    assert str(
        _conjoin(
            expression
            for item in groups
            if item.stage == "assumptions"
            for expression in item.expressions
        )
    ) == str(core.environment_formula)


def test_basic_core_formulas_match_pre_tracking_sexpression_golden() -> None:
    """Source tracking must not change the existing canonical formula text."""
    model = load_state_machine_from_text("state Root;")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare('check reach <= 1: active("Root");')
    )

    assert core.to_canonical()["formulas"] == {
        "D_N": dedent(
            """\
            And(Or(-3 == F_0_state, -1 == F_0_state, 0 == F_0_state),
                Or(-3 == F_1_state, -1 == F_1_state, 0 == F_1_state))"""
        ),
        "I_0": "-3 == F_0_state",
        "T_N": dedent(
            """\
            And(And(C_0_init___initial_Root_0_bda95de0da ==
                    And(-3 == F_0_state, True),
                    Implies(And(-3 == F_0_state, True), 0 == F_1_state)),
                And(C_0_init___delta___init___0_f7d616c3c1 ==
                    And(-3 == F_0_state,
                        Not(And(-3 == F_0_state, True))),
                    Implies(And(-3 == F_0_state,
                                Not(And(-3 == F_0_state, True))),
                            -3 == F_1_state)),
                Delta_0 ==
                And(-3 == F_0_state, Not(And(-3 == F_0_state, True))),
                Gamma_0 == False,
                Not(And(Delta_0, Gamma_0)))"""
        ),
        "ENV_N": "True",
        "Core_N": dedent(
            """\
            And(And(Or(-3 == F_0_state, -1 == F_0_state, 0 == F_0_state),
                    Or(-3 == F_1_state, -1 == F_1_state, 0 == F_1_state)),
                -3 == F_0_state,
                And(And(C_0_init___initial_Root_0_bda95de0da ==
                        And(-3 == F_0_state, True),
                        Implies(And(-3 == F_0_state, True),
                                0 == F_1_state)),
                    And(C_0_init___delta___init___0_f7d616c3c1 ==
                        And(-3 == F_0_state,
                            Not(And(-3 == F_0_state, True))),
                        Implies(And(-3 == F_0_state,
                                    Not(And(-3 == F_0_state, True))),
                                -3 == F_1_state)),
                    Delta_0 ==
                    And(-3 == F_0_state,
                        Not(And(-3 == F_0_state, True))),
                    Gamma_0 == False,
                    Not(And(Delta_0, Gamma_0))),
                True)"""
        ),
    }
    assert "tracked_groups" not in core.to_canonical()


def test_event_assumption_environment_formula_matches_golden() -> None:
    """Tracked event assumptions preserve the old environment expression."""
    model = load_state_machine_from_text("state Root { event go; }")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare(
            'assume event("Root.go", 0) == false;\ncheck reach <= 1: active("Root");'
        )
    )

    assert core.to_canonical()["formulas"]["ENV_N"] == (
        "Not(E_0_event_0_Root_go_06775bfa10)"
    )


def test_duplicate_assumption_occurrences_keep_distinct_stable_groups() -> None:
    """Equivalent source occurrences must not be merged by provenance."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare(
        'assume at 0: active("Root"); '
        'assume at 0: active("Root"); '
        'check reach <= 1: active("Root");'
    )
    core = build_bmc_core_formula(context)

    assumption_ids = [
        item.stable_id
        for item in core._tracked_groups
        if item.category == "assumption.frame"
    ]
    assert assumption_ids == [
        "assumption.0000.frame.0000",
        "assumption.0001.frame.0000",
    ]


def test_query_group_excerpt_uses_exact_fbmcq_span() -> None:
    """Real query groups retain an exact source snapshot and half-open span."""
    model = load_state_machine_from_text("state Root;")
    query_text = 'init state("Root") where true;\ncheck reach <= 1: active("Root");'
    context = BmcEngine(model).prepare(query_text, query_source_path="query.fbmcq")
    core = build_bmc_core_formula(context)

    target = next(
        item for item in core._tracked_groups if item.stable_id == "initial.target"
    )
    assert target.source_ref.path == "query.fbmcq"
    assert (
        context._source_registry.excerpt(target.source_ref)
        == 'init state("Root") where true;'
    )


def test_fcstm_and_fbmcq_document_namespaces_are_isolated(tmp_path: Path) -> None:
    """A colliding display path must not cross-contaminate excerpts."""
    machine_path = tmp_path / "machine.fcstm"
    machine_path.write_text("def int x = 7;\nstate Root;\n", encoding="utf-8")
    model = load_state_machine_from_file(machine_path)
    query_text = 'init state("Root") where true;\ncheck reach <= 1: active("Root");'

    context = BmcEngine(model).prepare(query_text, query_source_path="machine.fcstm")
    core = build_bmc_core_formula(context)

    variable = next(
        item for item in core._tracked_groups if item.stable_id == "initial.variable.x"
    )
    target = next(
        item for item in core._tracked_groups if item.stable_id == "initial.target"
    )

    assert variable.source_ref.kind == "fcstm"
    assert variable.source_ref.path == "machine.fcstm"
    assert context._source_registry.excerpt(variable.source_ref) == "def int x = 7;"
    assert target.source_ref.kind == "fbmcq"
    assert target.source_ref.path == "machine.fcstm"
    assert (
        context._source_registry.excerpt(target.source_ref)
        == 'init state("Root") where true;'
    )


def test_tracked_group_rejects_expression_from_another_z3_context() -> None:
    """The core bundle rejects groups that cannot be checked by its solver."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare('check reach <= 1: active("Root");')
    core = build_bmc_core_formula(context)
    other_context = z3.Context()
    foreign = BmcTrackedConstraint(
        "foreign",
        "kernel",
        "domain",
        (z3.Bool("foreign", ctx=other_context),),
        BmcSourceRef("generated", None, None),
    )

    with pytest.raises(BmcBuildError, match="core Z3 context"):
        BmcCoreFormula(
            context=core.context,
            symbols=core.symbols,
            domain_formula=core.domain_formula,
            initial_formula=core.initial_formula,
            transition_formula=core.transition_formula,
            environment_formula=core.environment_formula,
            core=core.core,
            steps=core.steps,
            _tracked_groups=(foreign,),
        )
