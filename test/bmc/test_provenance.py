"""TDD contracts for BMC source provenance and tracked relation groups."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from textwrap import dedent

import pytest
import z3

import pyfcstm.bmc.provenance as provenance_module
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcQuery
from pyfcstm.bmc.parse import parse_bmc_query
from pyfcstm.bmc.provenance import (
    BmcSourceRef,
    BmcTrackedConstraint,
    SourceDocumentRegistry,
)
from pyfcstm.bmc.relation import BmcCoreFormula, _append_tracked_group
from pyfcstm.model import (
    load_state_machine_from_file,
    load_state_machine_from_text,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.utils.validate import Span

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        pytest.param(
            {"kind": "unknown", "path": None, "span": None},
            ValueError,
            "source kind",
            id="source-kind",
        ),
        pytest.param(
            {"kind": "fcstm", "path": "", "span": None},
            ValueError,
            "source path",
            id="empty-path",
        ),
        pytest.param(
            {"kind": "fcstm", "path": None, "span": object()},
            TypeError,
            "source span",
            id="invalid-span-type",
        ),
    ],
)
def test_source_reference_rejects_malformed_values(kwargs, exception, message) -> None:
    """Source references reject invalid kind, path, and span values."""
    with pytest.raises(exception, match=message):
        BmcSourceRef(**kwargs)


def test_source_reference_canonicalizes_a_complete_span() -> None:
    """Canonical source references preserve all half-open span coordinates."""
    reference = BmcSourceRef("fcstm", "machine.fcstm", Span(2, 3, 4, 5))

    assert reference.to_canonical() == {
        "kind": "fcstm",
        "path": "machine.fcstm",
        "span": {"line": 2, "column": 3, "end_line": 4, "end_column": 5},
    }
    assert BmcSourceRef("generated", None, None).to_canonical() == {
        "kind": "generated",
        "path": None,
        "span": None,
    }


@pytest.mark.parametrize(
    ("field", "value", "exception", "message"),
    [
        pytest.param("stable_id", "", ValueError, "stable_id", id="stable-id"),
        pytest.param("stage", "", ValueError, "stage", id="stage"),
        pytest.param("category", "", ValueError, "category", id="category"),
        pytest.param("expressions", (), ValueError, "expressions", id="expressions"),
        pytest.param("source_ref", object(), TypeError, "source_ref", id="source-ref"),
    ],
)
def test_tracked_constraint_rejects_malformed_values(
    field, value, exception, message
) -> None:
    """Tracked constraints reject malformed identity and payload fields."""
    values = {
        "stable_id": "group",
        "stage": "kernel",
        "category": "domain",
        "expressions": (z3.BoolVal(True),),
        "source_ref": BmcSourceRef("generated", None, None),
    }
    values[field] = value

    with pytest.raises(exception, match=message):
        BmcTrackedConstraint(**values)


@pytest.mark.parametrize(
    ("expressions", "message"),
    [
        pytest.param((), "non-empty", id="empty"),
        pytest.param((z3.IntVal(1),), "Boolean", id="non-boolean"),
    ],
)
def test_tracked_group_registration_rejects_invalid_expressions(
    expressions, message
) -> None:
    """The relation-side registration guard rejects malformed Z3 inputs."""
    groups = []

    with pytest.raises(BmcBuildError, match=message):
        _append_tracked_group(
            groups,
            stable_id="invalid",
            stage="kernel",
            category="domain",
            expressions=expressions,
            source_ref=BmcSourceRef("generated", None, None),
        )


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        pytest.param(
            {"documents": {1: "text"}},
            ValueError,
            "document paths",
            id="document-path",
        ),
        pytest.param(
            {"documents": {"machine.fcstm": object()}},
            TypeError,
            "document text",
            id="document-text",
        ),
        pytest.param(
            {"documents": {}, "query_documents": {"": "query"}},
            ValueError,
            "query document paths",
            id="query-path",
        ),
        pytest.param(
            {"documents": {}, "query_documents": {"query.fbmcq": object()}},
            TypeError,
            "query document text",
            id="query-text",
        ),
    ],
)
def test_source_registry_rejects_malformed_documents(
    kwargs, exception, message
) -> None:
    """Document snapshots require non-empty paths and string contents."""
    with pytest.raises(exception, match=message):
        SourceDocumentRegistry(**kwargs)


@pytest.mark.parametrize(
    "span",
    [
        pytest.param(Span(1, 1), id="anchor-only"),
        pytest.param(Span(0, 1, 1, 2), id="invalid-start-line"),
        pytest.param(Span(1, 1, 2, 1), id="invalid-end-line"),
        pytest.param(Span(1, 3, 1, 2), id="end-before-start"),
        pytest.param(Span(1, 1, 1, 5), id="end-after-document"),
    ],
)
def test_source_registry_returns_none_for_unusable_spans(span) -> None:
    """Invalid and anchor-only spans never produce misleading excerpts."""
    registry = SourceDocumentRegistry({"machine.fcstm": "abc"})
    reference = BmcSourceRef("fcstm", "machine.fcstm", span)

    assert registry.excerpt(reference) is None


def test_source_registry_handles_aliases_and_unknown_namespaces(tmp_path: Path) -> None:
    """Document lookup resolves display aliases without crossing namespaces."""
    source_path = tmp_path / "nested" / "machine.fcstm"
    registry = SourceDocumentRegistry(
        {str(source_path): "state Root;"}, display_root=str(tmp_path)
    )

    display_path = os.path.relpath(str(source_path), str(tmp_path))
    assert registry.document(display_path) == "state Root;"
    assert registry.document(None) is None
    assert registry.document("nested/machine.fcstm", kind="unknown") is None


def test_source_registry_preserves_path_when_relative_path_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    """Unrelativizable paths retain the caller path, as on different Windows drives."""
    registry = SourceDocumentRegistry(
        {str(tmp_path / "machine.fcstm"): "state Root;"},
        display_root=str(tmp_path),
    )

    def fail_relpath(path, start):
        raise ValueError("paths use different drives")

    monkeypatch.setattr(provenance_module.os.path, "relpath", fail_relpath)

    path = str(tmp_path / "machine.fcstm")
    assert registry.display_path(path) == path


def test_source_registry_returns_none_for_missing_excerpt_document() -> None:
    """A direct reference cannot produce an excerpt without a source snapshot."""
    registry = SourceDocumentRegistry({"machine.fcstm": "state Root;"})
    reference = BmcSourceRef("fcstm", "missing.fcstm", Span(1, 1, 1, 5))

    assert registry.excerpt(reference) is None


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


def test_query_source_metadata_keeps_root_query_span_after_replace() -> None:
    """The returned immutable query root retains its own source span."""
    text = 'check reach <= 1: active("Root");'
    query = parse_bmc_query(text, source_path="query.fbmcq")
    registry = SourceDocumentRegistry({}, query_documents={"query.fbmcq": text})

    reference = registry.query_reference(query, query)

    assert reference.span is not None
    assert registry.excerpt(reference) == text


def test_query_source_metadata_rejects_invalid_public_metadata() -> None:
    """Parser and query dataclass reject malformed source metadata."""
    query_text = 'check reach <= 1: active("Root");'

    with pytest.raises(InvalidBmcQuery, match="_source_path"):
        parse_bmc_query(query_text, source_path="")

    query = parse_bmc_query(query_text)
    with pytest.raises(InvalidBmcQuery, match="_source_spans"):
        replace(query, _source_spans=(("not-an-id", Span(1, 1)),))


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


def test_imported_lifecycle_operations_keep_source_paths_and_excerpts(
    tmp_path: Path,
) -> None:
    """Lifecycle operations and nested branches retain imported provenance."""
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        """def int x = 0;
state Worker {
    event Tick;
    enter { if [x > 0] { x = x + 1; } else { x = x + 2; } }
    during before Tick { x = x + 3; }
    exit { x = x + 4; }
    >> during after Monitor { x = x + 5; }
    state Idle;
    [*] -> Idle;
}
""",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        'state Root { import "./worker.fcstm" as Worker; [*] -> Worker; }\n',
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    worker = model.root_state.substates["Worker"]
    registry = SourceDocumentRegistry(
        model._source_documents, display_root=model._source_root
    )

    actions = (
        worker.on_enters[0],
        worker.on_durings[0],
        worker.on_exits[0],
        worker.on_during_aspects[0],
    )
    for action in actions:
        assert action._source_path == str(imported.resolve())
        operation = action.operations[0]
        assert operation._source_path == str(imported.resolve())
        assert registry.model_reference(operation).path == "worker.fcstm"

    enter_if = worker.on_enters[0].operations[0]
    assert enter_if._source_path == str(imported.resolve())
    assert [
        registry.excerpt(registry.model_reference(branch.statements[0]))
        for branch in enter_if.branches
    ] == ["x = x + 1;", "x = x + 2;"]

    assert [
        registry.excerpt(registry.model_reference(action.operations[0]))
        for action in actions[1:]
    ] == ["x = x + 3;", "x = x + 4;", "x = x + 5;"]


def test_programmatic_ast_without_spans_fails_closed_for_operation_metadata() -> None:
    """Programmatic AST input does not receive fabricated operation paths."""
    program = dsl_nodes.StateMachineDSLProgram(
        definitions=[dsl_nodes.DefAssignment("x", "int", dsl_nodes.Integer("0"))],
        root_state=dsl_nodes.StateDefinition(
            "Root",
            enters=[
                dsl_nodes.EnterOperations(
                    [dsl_nodes.OperationAssignment("x", dsl_nodes.Integer("1"))]
                )
            ],
        ),
    )

    model = parse_dsl_node_to_state_machine(program)

    operation = model.root_state.on_enters[0].operations[0]
    assert getattr(operation, "_source_path", None) is None


def test_text_loader_records_snapshot_when_path_is_an_existing_file(
    tmp_path: Path,
) -> None:
    """Text loading records a snapshot when its path names a real file."""
    source_path = tmp_path / "machine.fcstm"
    source = "state Root;"
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_text(source, path=source_path)

    assert model._source_documents[str(source_path.resolve())] == source


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


def test_initial_where_definedness_is_tracked_with_the_source_predicate() -> None:
    """Initial predicate definedness constraints retain their source group."""
    model = load_state_machine_from_text("def int x = 1; def int y = 0; state Root;")
    query_text = 'init cold where x / y > 0;\ncheck reach <= 1: active("Root");'
    context = BmcEngine(model).prepare(query_text, query_source_path="query.fbmcq")
    core = build_bmc_core_formula(context)

    definedness = next(
        group
        for group in core._tracked_groups
        if group.stable_id == "initial.where.definedness.0000"
    )

    assert definedness.category == "definedness"
    assert definedness.source_ref.kind == "fbmcq"
    assert context._source_registry.excerpt(definedness.source_ref) == ("x / y > 0")
    assert len(definedness.expressions) == 1
    assert "F_0_y" in str(definedness.expressions[0])


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


def test_core_formula_rejects_malformed_tracked_group_payloads() -> None:
    """Core formulas reject invalid, duplicate, and non-Boolean groups."""
    model = load_state_machine_from_text("state Root;")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare('check reach <= 1: active("Root");')
    )

    with pytest.raises(BmcBuildError, match="tracked groups must contain"):
        replace(core, _tracked_groups=(object(),))

    group = core._tracked_groups[0]
    with pytest.raises(BmcBuildError, match="unique stable ids"):
        replace(core, _tracked_groups=(group, group))

    non_boolean = replace(group, expressions=(z3.Int("not_boolean"),))
    with pytest.raises(BmcBuildError, match="Z3 Boolean expressions"):
        replace(core, _tracked_groups=(non_boolean,))
