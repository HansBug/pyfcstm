"""Semantic binding tests for FCSTM BMC queries."""

from __future__ import annotations

import subprocess
import sys
import pytest

import pyfcstm.bmc.binding as binding_module
from pyfcstm.bmc.binding import (
    BmcBindingDiagnostic,
    BoundAssumption,
    BoundBmcQuery,
    BoundInitialSpec,
    BoundProperty,
    BoundReference,
    bind_bmc_query,
    bind_bmc_query_structure,
)
from pyfcstm.bmc.domain import build_bmc_domain
from pyfcstm.bmc.errors import BmcQueryParseError, InvalidBmcQuery
from pyfcstm.bmc.ast import (
    Active,
    BmcCondExpr,
    BmcNumExpr,
    BoolLiteral,
    Case,
    IntLiteral,
    NumericComparison,
)
from pyfcstm.bmc.parse import parse_bmc_cond_expression, parse_bmc_query
from pyfcstm.bmc.query import (
    BmcAssumption,
    BmcProperty,
    BmcQuery,
    EventAssumption,
    EventCardinalityAssumption,
    FrameAssumption,
    InitialSpec,
)
from pyfcstm.model import load_state_machine_from_text


def _query(text: str):
    return parse_bmc_query(text)


def _bind(text: str) -> BoundBmcQuery:
    return bind_bmc_query_structure(_query(text))


def _diagnostic(excinfo) -> BmcBindingDiagnostic:
    diag = getattr(excinfo.value, "diagnostic", None)
    assert isinstance(diag, BmcBindingDiagnostic)
    return diag


def _forged_bound_property_with_kind(kind: str) -> BoundProperty:
    prop = BmcProperty("reach", 1, predicate=BoolLiteral("true"))
    object.__setattr__(prop, "kind", kind)
    return BoundProperty(prop)


@pytest.fixture()
def binding_model():
    """Return a compact model with variables, states, and events for binding."""
    return load_state_machine_from_text(
        """
        def int x = 0;
        def int cycle = 1;
        def float pressure = 0.0;
        state Root {
            event Tick;
            event Reset;
            state Idle;
            state Done;
            [*] -> Idle;
            Idle -> Done :: Tick;
        }
        """
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param(
            "check reach <= 1: true;",
            {"mode": "cold", "kind": "reach", "assumptions": 0},
            id="default-cold-reach",
        ),
        pytest.param(
            'init cold where active("Root.Idle"); check forbid <= 2: false;',
            {"mode": "cold", "kind": "forbid", "assumptions": 0},
            id="cold-where",
        ),
        pytest.param(
            'init state("Root.Idle") where x >= 0; check invariant <= 3: x >= 0;',
            {"mode": "state", "kind": "invariant", "assumptions": 0},
            id="state-where-bare-var",
        ),
        pytest.param(
            'init terminated where var("cycle") == 1; check must_reach <= 4: terminated();',
            {"mode": "terminated", "kind": "must_reach", "assumptions": 0},
            id="terminated-where-model-cycle-var",
        ),
        pytest.param(
            'assume always: cycle <= 5; assume at 2: active("Root.Idle"); '
            'check exists_always <= 5: !active("Root.Bad");',
            {"mode": "cold", "kind": "exists_always", "assumptions": 2},
            id="frame-assumptions",
        ),
        pytest.param(
            'assume event("Root.Tick", *) == true; '
            'assume event("Root.Reset", 1..2) == false; '
            "assume events cardinality any; "
            'assume events cardinality at_most_one {"Root.Tick"}; '
            'check response <= 3: trigger event("Root.Tick", current) '
            '-> within 1 active("Root.Done");',
            {"mode": "cold", "kind": "response", "assumptions": 4},
            id="event-and-response",
        ),
        pytest.param(
            'check cover <= 2: case("Root.Idle::transition::Root.Done::1", current);',
            {"mode": "cold", "kind": "cover", "assumptions": 0},
            id="cover-current-canonical",
        ),
    ],
)
def test_bind_bmc_query_structure_accepts_positive_queries(source, expected):
    """Structure binding accepts conservative positive query shapes."""
    bound = _bind(source)
    canonical = bound.to_canonical()

    assert isinstance(bound, BoundBmcQuery)
    assert bound.initial.mode == expected["mode"]
    assert bound.property.kind == expected["kind"]
    assert len(bound.assumptions) == expected["assumptions"]
    assert canonical["node"] == "bound_bmc_query"
    assert canonical["initial"]["mode"] == expected["mode"]
    assert canonical["property"]["kind"] == expected["kind"]


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, code_fragment, path_fragment",
    [
        pytest.param(
            'check reach <= 5: event("Root.Tick", current);',
            "event_not_allowed",
            "property.predicate",
            id="ordinary-property-event-current",
        ),
        pytest.param(
            'assume always: event("Root.Tick", 0); check reach <= 1: true;',
            "event_not_allowed",
            "assumptions[0].predicate",
            id="frame-assumption-event",
        ),
        pytest.param(
            'check reach <= 5: active("Root.Idle", 2);',
            "explicit_frame_selector",
            "property.predicate.frame",
            id="ordinary-property-explicit-frame",
        ),
        pytest.param(
            'check response <= 5: trigger active("Root.Idle", 1) '
            '-> within 2 active("Root.Done");',
            "explicit_frame_selector",
            "property.trigger.frame",
            id="response-trigger-explicit-frame",
        ),
        pytest.param(
            'check response <= 5: trigger active("Root.Idle") '
            '-> within 2 active("Root.Done", 3);',
            "explicit_frame_selector",
            "property.response.frame",
            id="response-target-explicit-frame",
        ),
        pytest.param(
            'check response <= 5: trigger active("Root.Idle") '
            '-> within 2 event("Root.Tick", current);',
            "event_not_allowed",
            "property.response",
            id="response-target-event-current",
        ),
        pytest.param(
            'check response <= 5: trigger event("Root.Tick", 3) '
            '-> within 2 active("Root.Done");',
            "event_not_allowed",
            "property.trigger",
            id="response-trigger-event-index",
        ),
        pytest.param(
            'check cover <= 3: active("Root.Idle") && case("label");',
            "cover_predicate",
            "property.predicate",
            id="cover-composite-symbolic-and",
        ),
        pytest.param(
            'check cover <= 3: active("Root.Idle") and case("label");',
            "cover_predicate",
            "property.predicate",
            id="cover-composite-keyword-and",
        ),
        pytest.param(
            'check cover <= 3: case("label", 2);',
            "cover_predicate",
            "property.predicate",
            id="cover-fixed-step-case",
        ),
        pytest.param(
            "init cold where cycle == 0; check reach <= 1: true;",
            "cycle_not_allowed",
            "initial.predicate.left",
            id="init-where-bare-cycle",
        ),
        pytest.param(
            'init cold where event("Root.Tick", current); check reach <= 1: true;',
            "event_not_allowed",
            "initial.predicate",
            id="init-where-event",
        ),
        pytest.param(
            'check reach <= 3: called("Hook");',
            "unsupported_called_atom",
            "property.predicate",
            id="called-ordinary-property",
        ),
        pytest.param(
            'check cover <= 3: called("Hook");',
            "unsupported_called_atom",
            "property.predicate",
            id="called-cover-property",
        ),
        pytest.param(
            'check reach <= 3: (cycle <= 1) ? active("A") : case("L");',
            "case_not_allowed",
            "property.predicate.if_false",
            id="nested-conditional-case",
        ),
    ],
)
def test_bind_bmc_query_structure_rejects_context_errors(
    source, code_fragment, path_fragment
):
    """Binder rejects grammar-valid query shapes that violate semantic context."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        _bind(source)

    diagnostic = _diagnostic(excinfo)
    assert diagnostic.code == code_fragment
    assert path_fragment in diagnostic.path
    assert code_fragment in str(excinfo.value)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, code",
    [
        pytest.param(
            'assume event("Root.Tick", 3) == true; check reach <= 3: true;',
            "event_selector_out_of_range",
            id="event-selector-equals-bound",
        ),
        pytest.param(
            'assume event("Root.Tick", 4..5) == true; check reach <= 5: true;',
            "event_range_out_of_range",
            id="event-range-end-equals-bound",
        ),
        pytest.param(
            "assume at 4: true; check reach <= 3: true;",
            "frame_selector_out_of_range",
            id="assume-at-greater-than-bound",
        ),
    ],
)
def test_bind_bmc_query_structure_rejects_selector_boundaries(source, code):
    """Binder checks frame and event selector ranges against query bound."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        _bind(source)

    assert _diagnostic(excinfo).code == code


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source",
    [
        "check reach <= 0: true;",
        "assume at -1: true; check reach <= 1: true;",
        'check reach <= 5: event("Root.Tick", *);',
        'check reach <= 5: event("Root.Tick", 0..2);',
        'active("A") + 1',
        "cycle and true",
        "cycle && true",
        'var("x") and active("A")',
    ],
)
def test_parse_layer_rejects_non_ast_semantic_boundaries(source):
    """Parser-invalid boundaries remain part of the binding guardrail matrix."""
    with pytest.raises((BmcQueryParseError, InvalidBmcQuery)):
        if source.startswith("check") or source.startswith("assume"):
            parse_bmc_query(source)
        else:
            parse_bmc_cond_expression(source)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, expected_cycles",
    [
        ('assume event("Root.Tick", 0) == true; check reach <= 3: true;', (0,)),
        ('assume event("Root.Tick", 2) == true; check reach <= 3: true;', (2,)),
        (
            'assume event("Root.Tick", 0..2) == true; check reach <= 3: true;',
            (0, 1, 2),
        ),
        (
            'assume event("Root.Tick", *) == true; check reach <= 3: true;',
            (0, 1, 2),
        ),
    ],
)
def test_event_assumption_selectors_expand_to_cycle_tuples(source, expected_cycles):
    """Event assumptions normalize point, range, and wildcard selectors."""
    bound = _bind(source)

    assert bound.assumptions[0].cycles == expected_cycles


@pytest.mark.unittest
def test_bind_bmc_query_model_resolution_records_references(binding_model):
    """Model-aware binding resolves state, event, and variable references."""
    query = _query(
        'init state("Root.Idle") where x == var("x"); '
        'assume event("Root.Tick", 0) == true; '
        'assume events cardinality at_most_one {"Root.Tick", "Root.Reset"}; '
        'check reach <= 2: active("Root.Done") && var("cycle") >= cycle;'
    )

    bound = bind_bmc_query(query, model=binding_model)
    references = bound.to_canonical()["references"]
    by_key = {
        (item["kind"], item["name"], item["spelling"]): item for item in references
    }

    assert bound.initial.resolved_state_id is not None
    assert by_key[("state", "Root.Idle", "state_path")]["resolved_id"] is not None
    assert by_key[("state", "Root.Done", "active")]["resolved_id"] is not None
    assert by_key[("event", "Root.Tick", "event_assumption")]["resolved_id"] is not None
    assert (
        by_key[("event", "Root.Reset", "cardinality_event")]["resolved_id"] is not None
    )
    assert by_key[("variable", "x", "bare")]["declared_type"] == "int"
    assert by_key[("variable", "x", "var_call")]["declared_type"] == "int"
    assert by_key[("variable", "cycle", "var_call")]["declared_type"] == "int"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, code",
    [
        ('check reach <= 1: active("Root.Missing");', "unknown_state"),
        ('check reach <= 1: active("$STATE_TERMINATE");', "reserved_state_path"),
        (
            'init state("$STATE_DIAGNOSTIC"); check reach <= 1: true;',
            "reserved_state_path",
        ),
        (
            'assume event("Root.Missing", 0) == true; check reach <= 1: true;',
            "unknown_event",
        ),
        ("check reach <= 1: missing >= 0;", "unknown_variable"),
    ],
)
def test_bind_bmc_query_model_resolution_rejects_unknown_references(
    binding_model, source, code
):
    """Model-aware binding rejects unresolved state, event, and variable names."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query(_query(source), model=binding_model)

    assert _diagnostic(excinfo).code == code


@pytest.mark.unittest
def test_bind_bmc_query_domain_contracts(binding_model):
    """The public binding entry freezes model/domain combinations."""
    query = _query('check reach <= 2: active("Root.Done");')
    matching_domain = build_bmc_domain(binding_model, 2)
    mismatched_domain = build_bmc_domain(binding_model, 3)

    assert bind_bmc_query(query).to_canonical()["node"] == "bound_bmc_query"
    assert bind_bmc_query(query, domain=matching_domain).property.bound == 2

    with pytest.raises(InvalidBmcQuery) as mismatch:
        bind_bmc_query(query, domain=mismatched_domain)
    assert _diagnostic(mismatch).code == "domain_bound_mismatch"

    with pytest.raises(InvalidBmcQuery) as conflict:
        bind_bmc_query(query, model=binding_model, domain=matching_domain)
    assert _diagnostic(conflict).code == "model_domain_conflict"

    with pytest.raises(InvalidBmcQuery) as wrong_domain:
        bind_bmc_query(query, domain=object())
    assert _diagnostic(wrong_domain).code == "domain_type"


@pytest.mark.unittest
def test_binding_diagnostic_is_stable_and_validated():
    """Binding diagnostics expose stable canonical output and validation."""
    diagnostic = BmcBindingDiagnostic("code", "path", "message")

    assert str(diagnostic) == "code at path: message"
    assert diagnostic.to_canonical() == {
        "code": "code",
        "path": "path",
        "message": "message",
    }

    for args in [
        ("", "path", "message"),
        ("code", "", "message"),
        ("code", "path", ""),
    ]:
        with pytest.raises(InvalidBmcQuery):
            BmcBindingDiagnostic(*args)


@pytest.mark.unittest
def test_binding_imports_remain_layered():
    """Structure binding imports do not load model, solver, z3, or verify."""
    code = (
        "import sys; "
        "import pyfcstm.bmc.binding; "
        "bad = [name for name in sys.modules "
        "if name == 'z3' "
        "or name.startswith('pyfcstm.model') "
        "or name.startswith('pyfcstm.verify') "
        "or name.startswith('pyfcstm.solver')]; "
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
@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            lambda: BmcBindingDiagnostic(1, "path", "message"), id="diag-code-type"
        ),
        pytest.param(
            lambda: BmcBindingDiagnostic("code", 1, "message"), id="diag-path-type"
        ),
        pytest.param(
            lambda: BmcBindingDiagnostic("code", "path", 1), id="diag-message-type"
        ),
        pytest.param(
            lambda: BmcBindingDiagnostic("   ", "path", "message"),
            id="diag-code-whitespace",
        ),
        pytest.param(
            lambda: BmcBindingDiagnostic("code", "\t", "message"),
            id="diag-path-whitespace",
        ),
        pytest.param(
            lambda: BmcBindingDiagnostic("code", "path", "\n"),
            id="diag-message-whitespace",
        ),
        pytest.param(
            lambda: BoundReference("state", "", "path", "active"),
            id="reference-empty-name",
        ),
        pytest.param(
            lambda: BoundReference(" ", "A", "path", "active"),
            id="reference-whitespace-kind",
        ),
        pytest.param(
            lambda: BoundReference("state", " ", "path", "active"),
            id="reference-whitespace-name",
        ),
        pytest.param(
            lambda: BoundReference("state", "A", " ", "active"),
            id="reference-whitespace-path",
        ),
        pytest.param(
            lambda: BoundReference("state", "A", "path", " "),
            id="reference-whitespace-spelling",
        ),
        pytest.param(
            lambda: BoundReference("hook", "A", "path", "active"), id="reference-kind"
        ),
        pytest.param(
            lambda: BoundReference("state", "A", "path", "active", resolved_id=True),
            id="reference-resolved-bool",
        ),
        pytest.param(
            lambda: BoundReference("variable", "x", "path", "bare", declared_type=1),
            id="reference-declared-type",
        ),
        pytest.param(
            lambda: BoundReference("variable", "x", "path", "bare", declared_type=""),
            id="reference-declared-type-empty",
        ),
        pytest.param(
            lambda: BoundReference("variable", "x", "path", "bare", declared_type=" "),
            id="reference-declared-type-whitespace",
        ),
        pytest.param(lambda: BoundInitialSpec(object()), id="initial-source"),
        pytest.param(
            lambda: BoundInitialSpec(InitialSpec(), resolved_state_id=True),
            id="initial-resolved-bool",
        ),
        pytest.param(
            lambda: BoundAssumption(object(), "frame"), id="assumption-source"
        ),
        pytest.param(
            lambda: BoundAssumption(
                FrameAssumption("always", BoolLiteral("true")), "bad"
            ),
            id="assumption-kind",
        ),
        pytest.param(
            lambda: BoundAssumption(
                FrameAssumption("always", BoolLiteral("true")), "frame", frame=True
            ),
            id="assumption-frame-bool",
        ),
        pytest.param(
            lambda: BoundAssumption(
                FrameAssumption("always", BoolLiteral("true")), "frame", frame=-1
            ),
            id="assumption-frame-negative",
        ),
        pytest.param(
            lambda: BoundAssumption(
                FrameAssumption("always", BoolLiteral("true")), "frame", cycles="bad"
            ),
            id="assumption-cycles-string",
        ),
        pytest.param(
            lambda: BoundAssumption(
                FrameAssumption("always", BoolLiteral("true")), "frame", cycles=(True,)
            ),
            id="assumption-cycles-bool",
        ),
        pytest.param(lambda: BoundProperty(object()), id="property-source"),
        pytest.param(
            lambda: _forged_bound_property_with_kind("future"),
            id="property-source-unknown-kind",
        ),
        pytest.param(
            lambda: BoundProperty(
                BmcProperty("cover", 1, predicate=Case("case")), case_label=""
            ),
            id="property-label-empty",
        ),
        pytest.param(
            lambda: BoundProperty(
                BmcProperty("cover", 1, predicate=Case("case")), case_label=" "
            ),
            id="property-label-whitespace",
        ),
        pytest.param(
            lambda: BoundProperty(
                BmcProperty("reach", 1, predicate=BoolLiteral("true")),
                case_label="case",
            ),
            id="property-label-non-cover",
        ),
        pytest.param(
            lambda: BoundBmcQuery(
                object(),
                BoundInitialSpec(InitialSpec()),
                (),
                BoundProperty(BmcProperty("reach", 1, predicate=BoolLiteral("true"))),
            ),
            id="bound-query-source",
        ),
        pytest.param(
            lambda: BoundBmcQuery(
                BmcQuery(
                    property=BmcProperty("reach", 1, predicate=BoolLiteral("true"))
                ),
                object(),
                (),
                BoundProperty(BmcProperty("reach", 1, predicate=BoolLiteral("true"))),
            ),
            id="bound-query-initial",
        ),
        pytest.param(
            lambda: BoundBmcQuery(
                BmcQuery(
                    property=BmcProperty("reach", 1, predicate=BoolLiteral("true"))
                ),
                BoundInitialSpec(InitialSpec()),
                (),
                object(),
            ),
            id="bound-query-property",
        ),
        pytest.param(
            lambda: BoundBmcQuery(
                BmcQuery(
                    property=BmcProperty("reach", 1, predicate=BoolLiteral("true"))
                ),
                BoundInitialSpec(InitialSpec()),
                "bad",
                BoundProperty(BmcProperty("reach", 1, predicate=BoolLiteral("true"))),
            ),
            id="bound-query-assumptions-string",
        ),
        pytest.param(
            lambda: BoundBmcQuery(
                BmcQuery(
                    property=BmcProperty("reach", 1, predicate=BoolLiteral("true"))
                ),
                BoundInitialSpec(InitialSpec()),
                (object(),),
                BoundProperty(BmcProperty("reach", 1, predicate=BoolLiteral("true"))),
            ),
            id="bound-query-assumption-item",
        ),
    ],
)
def test_bound_binding_objects_reject_invalid_constructor_inputs(factory):
    """Bound dataclasses reject malformed direct construction inputs."""
    with pytest.raises(InvalidBmcQuery):
        factory()


@pytest.mark.unittest
def test_bound_initial_properties_and_sequence_normalization():
    """Bound snapshots expose convenience properties and normalize sequences."""
    initial = BoundInitialSpec(
        InitialSpec(predicate=BoolLiteral("true")), resolved_state_id=1
    )
    assumption = BoundAssumption(
        FrameAssumption("always", BoolLiteral("true")),
        "frame",
        cycles=[0, 1],
        resolved_event_ids=[2],
    )
    prop = BoundProperty(BmcProperty("reach", 2, predicate=BoolLiteral("true")))
    bound = BoundBmcQuery(
        BmcQuery(property=prop.source),
        initial,
        [assumption],
        prop,
        [BoundReference("event", "Root.Tick", "path", "event", 3)],
    )

    assert initial.mode == "cold"
    assert initial.predicate == BoolLiteral("true")
    assert assumption.cycles == (0, 1)
    assert assumption.resolved_event_ids == (2,)
    assert isinstance(bound.assumptions, tuple)
    assert isinstance(bound.references, tuple)


@pytest.mark.unittest
def test_bind_bmc_query_rejects_non_query_input():
    """Public binding entries reject non-query values with structured errors."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(object())

    assert _diagnostic(excinfo).code == "query_type"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, expected_names",
    [
        pytest.param(
            "check reach <= 2: -(x + 1) <= sqrt(y);",
            {"x", "y"},
            id="unary-binary-and-ufunc",
        ),
        pytest.param(
            'check reach <= 2: ((active("Root.Idle")) ? (x + 1) : sqrt(y)) >= 0;',
            {"Root.Idle", "x", "y"},
            id="numeric-conditional",
        ),
        pytest.param(
            'check reach <= 2: (active("Root.Idle")) ? active("Root.Done") : terminated();',
            {"Root.Idle", "Root.Done"},
            id="condition-conditional",
        ),
        pytest.param(
            "check reach <= 2: x <= 1.5 && y >= pi;",
            {"x", "y"},
            id="float-literal-and-math-constant",
        ),
    ],
)
def test_binding_walks_nested_numeric_and_condition_expression_shapes(
    source, expected_names
):
    """Binder traverses expression nodes that are not query-specific atoms."""
    bound = _bind(source)

    assert {reference.name for reference in bound.references} == expected_names


@pytest.mark.unittest
@pytest.mark.parametrize(
    "selector",
    [
        pytest.param(object(), id="opaque-object"),
        pytest.param("0..x", id="bad-range-endpoint"),
    ],
)
def test_internal_event_cycle_guard_rejects_unexpected_selector_shape(selector):
    """The event selector helper fails closed for non-parser selector shapes."""
    malformed = EventAssumption("Root.Tick", 0)
    object.__setattr__(malformed, "selector", selector)
    query = BmcQuery(
        property=BmcProperty("reach", 2, predicate=BoolLiteral("true")),
        assumptions=(malformed,),
    )

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    assert _diagnostic(excinfo).code == "event_selector_invalid"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "selector",
    [
        pytest.param(object(), id="opaque-object"),
        pytest.param("0..x", id="bad-range-endpoint"),
    ],
)
def test_internal_event_cycle_guard_remains_defensive_when_shape_check_is_bypassed(
    monkeypatch, selector
):
    """The event cycle helper independently rejects malformed selector values."""
    monkeypatch.setattr(binding_module, "_validate_query_shape", lambda query: None)
    malformed = EventAssumption("Root.Tick", 0)
    object.__setattr__(malformed, "selector", selector)
    query = BmcQuery(
        property=BmcProperty("reach", 2, predicate=BoolLiteral("true")),
        assumptions=(malformed,),
    )

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    assert _diagnostic(excinfo).code == "event_selector_invalid"


@pytest.mark.unittest
def test_internal_assumption_guard_rejects_unknown_assumption_subclass():
    """The binder fails closed if future assumption subclasses reach it."""

    class FutureAssumption(BmcAssumption):
        def _canonical_payload(self):
            return {}

        def _to_dsl(self):
            return "assume future;"

    query = BmcQuery(
        property=BmcProperty("reach", 1, predicate=BoolLiteral("true")),
        assumptions=(FutureAssumption(),),
    )

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    assert _diagnostic(excinfo).code == "assumption_type"


@pytest.mark.unittest
def test_internal_assumption_dispatch_remains_defensive_when_shape_check_is_bypassed(
    monkeypatch,
):
    """The binding dispatcher still rejects unknown assumptions after prechecks."""

    class FutureAssumption(BmcAssumption):
        def _canonical_payload(self):
            return {}

        def _to_dsl(self):
            return "assume future;"

    monkeypatch.setattr(binding_module, "_validate_query_shape", lambda query: None)
    query = BmcQuery(
        property=BmcProperty("reach", 1, predicate=BoolLiteral("true")),
        assumptions=(FutureAssumption(),),
    )

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    assert _diagnostic(excinfo).code == "assumption_type"


@pytest.mark.unittest
def test_bind_bmc_query_converts_invalid_model_to_query_diagnostic():
    """Model/domain entry converts invalid model objects into binding errors."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query(_query("check reach <= 1: true;"), model=object())

    assert _diagnostic(excinfo).code == "invalid_model"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "forged_frame",
    [
        pytest.param(None, id="missing-at-frame"),
        pytest.param(True, id="boolean-at-frame"),
        pytest.param("1", id="string-at-frame"),
        pytest.param(-1, id="negative-at-frame"),
    ],
)
def test_internal_frame_assumption_guard_rejects_forged_frame_values(forged_frame):
    """The binder fails closed if a frame assumption is forged after parsing."""
    assumption = FrameAssumption("at", BoolLiteral("true"), frame=0)
    object.__setattr__(assumption, "frame", forged_frame)
    query = BmcQuery(
        property=BmcProperty("reach", 1, predicate=BoolLiteral("true")),
        assumptions=(assumption,),
    )

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    assert _diagnostic(excinfo).code == "query_shape"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "mutator, expected_path, expected_code",
    [
        pytest.param(
            lambda query: object.__setattr__(query.property, "bound", 0),
            "property.bound",
            "query_shape",
            id="property-bound-zero",
        ),
        pytest.param(
            lambda query: object.__setattr__(query.property, "bound", True),
            "property.bound",
            "query_shape",
            id="property-bound-bool",
        ),
        pytest.param(
            lambda query: object.__setattr__(query.property, "kind", "future"),
            "property.kind",
            "query_shape",
            id="property-unknown-kind",
        ),
        pytest.param(
            lambda query: object.__setattr__(query.property, "predicate", None),
            "property.predicate",
            "query_shape",
            id="single-property-missing-predicate",
        ),
        pytest.param(
            lambda query: object.__setattr__(
                query.property, "trigger", BoolLiteral("true")
            ),
            "property",
            "query_shape",
            id="single-property-extra-trigger",
        ),
        pytest.param(
            lambda query: object.__setattr__(query, "initial", object()),
            "initial",
            "query_shape",
            id="initial-wrong-type",
        ),
        pytest.param(
            lambda query: object.__setattr__(query.initial, "mode", "warm"),
            "initial.mode",
            "query_shape",
            id="initial-unknown-mode",
        ),
        pytest.param(
            lambda query: object.__setattr__(query.initial, "state_path", "Root.Idle"),
            "initial.state_path",
            "query_shape",
            id="initial-cold-extra-state-path",
        ),
        pytest.param(
            lambda query: (
                object.__setattr__(query.initial, "mode", "state"),
                object.__setattr__(query.initial, "state_path", " "),
            ),
            "initial.state_path",
            "query_shape",
            id="initial-state-whitespace-path",
        ),
        pytest.param(
            lambda query: object.__setattr__(query.initial, "predicate", object()),
            "initial.predicate",
            "query_shape",
            id="initial-predicate-wrong-type",
        ),
        pytest.param(
            lambda query: object.__setattr__(query, "assumptions", "bad"),
            "assumptions",
            "query_shape",
            id="assumptions-string",
        ),
        pytest.param(
            lambda query: object.__setattr__(query, "property", object()),
            "property",
            "query_shape",
            id="property-wrong-type",
        ),
    ],
)
def test_binding_revalidates_forged_query_root_and_property_shapes(
    mutator, expected_path, expected_code
):
    """The binder fails closed if frozen query-root invariants are bypassed."""
    query = BmcQuery(property=BmcProperty("reach", 1, predicate=BoolLiteral("true")))
    mutator(query)

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    diagnostic = _diagnostic(excinfo)
    assert diagnostic.code == expected_code
    assert expected_path in diagnostic.path


@pytest.mark.unittest
@pytest.mark.parametrize(
    "mutator, expected_path",
    [
        pytest.param(
            lambda prop: object.__setattr__(prop, "within", 0),
            "property.within",
            id="response-window-zero",
        ),
        pytest.param(
            lambda prop: object.__setattr__(prop, "within", True),
            "property.within",
            id="response-window-bool",
        ),
        pytest.param(
            lambda prop: object.__setattr__(prop, "trigger", object()),
            "property.trigger",
            id="response-trigger-wrong-type",
        ),
        pytest.param(
            lambda prop: object.__setattr__(prop, "response", object()),
            "property.response",
            id="response-target-wrong-type",
        ),
        pytest.param(
            lambda prop: object.__setattr__(prop, "predicate", BoolLiteral("true")),
            "property.predicate",
            id="response-extra-predicate",
        ),
    ],
)
def test_binding_revalidates_forged_response_property_shape(mutator, expected_path):
    """The binder rechecks response-specific fields before semantic traversal."""
    prop = BmcProperty(
        "response",
        2,
        trigger=Active("Root.Idle"),
        response=Active("Root.Done"),
        within=1,
    )
    query = BmcQuery(property=prop)
    mutator(prop)

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    diagnostic = _diagnostic(excinfo)
    assert diagnostic.code == "query_shape"
    assert expected_path in diagnostic.path


@pytest.mark.unittest
@pytest.mark.parametrize(
    "assumption, mutator, expected_code, expected_path",
    [
        pytest.param(
            FrameAssumption("always", BoolLiteral("true")),
            lambda item: object.__setattr__(item, "kind", "future"),
            "query_shape",
            "assumptions[0].kind",
            id="frame-unknown-kind",
        ),
        pytest.param(
            FrameAssumption("always", BoolLiteral("true")),
            lambda item: object.__setattr__(item, "predicate", object()),
            "query_shape",
            "assumptions[0].predicate",
            id="frame-predicate-wrong-type",
        ),
        pytest.param(
            FrameAssumption("always", BoolLiteral("true")),
            lambda item: object.__setattr__(item, "frame", 0),
            "query_shape",
            "assumptions[0].frame",
            id="always-extra-frame",
        ),
        pytest.param(
            FrameAssumption("at", BoolLiteral("true"), frame=0),
            lambda item: object.__setattr__(item, "frame", True),
            "query_shape",
            "assumptions[0].frame",
            id="at-bool-frame",
        ),
        pytest.param(
            EventAssumption("Root.Tick", 0),
            lambda item: object.__setattr__(item, "event_path", " "),
            "query_shape",
            "assumptions[0].event_path",
            id="event-whitespace-path",
        ),
        pytest.param(
            EventAssumption("Root.Tick", 0),
            lambda item: object.__setattr__(item, "selector", True),
            "event_selector_invalid",
            "assumptions[0].selector",
            id="event-bool-selector",
        ),
        pytest.param(
            EventAssumption("Root.Tick", 0),
            lambda item: object.__setattr__(item, "selector", -1),
            "event_selector_invalid",
            "assumptions[0].selector",
            id="event-negative-selector",
        ),
        pytest.param(
            EventAssumption("Root.Tick", 0),
            lambda item: object.__setattr__(item, "expected", 1),
            "query_shape",
            "assumptions[0].expected",
            id="event-expected-non-bool",
        ),
        pytest.param(
            EventCardinalityAssumption("any"),
            lambda item: object.__setattr__(item, "kind", "future"),
            "query_shape",
            "assumptions[0].kind",
            id="cardinality-unknown-kind",
        ),
        pytest.param(
            EventCardinalityAssumption("any"),
            lambda item: object.__setattr__(item, "event_paths", "Root.Tick"),
            "query_shape",
            "assumptions[0].event_paths",
            id="cardinality-string-paths",
        ),
        pytest.param(
            EventCardinalityAssumption("any"),
            lambda item: object.__setattr__(item, "event_paths", ("Root.Tick",)),
            "query_shape",
            "assumptions[0].event_paths",
            id="cardinality-any-extra-path",
        ),
        pytest.param(
            EventCardinalityAssumption("at_most_one", ("Root.Tick",)),
            lambda item: object.__setattr__(item, "event_paths", ()),
            "query_shape",
            "assumptions[0].event_paths",
            id="cardinality-at-most-one-empty",
        ),
        pytest.param(
            EventCardinalityAssumption("at_most_one", ("Root.Tick",)),
            lambda item: object.__setattr__(item, "event_paths", ("Root.Tick", " ")),
            "query_shape",
            "assumptions[0].event_paths[1]",
            id="cardinality-whitespace-event",
        ),
        pytest.param(
            EventCardinalityAssumption("at_most_one", ("Root.Tick",)),
            lambda item: object.__setattr__(
                item, "event_paths", ("Root.Tick", "Root.Tick")
            ),
            "query_shape",
            "assumptions[0].event_paths",
            id="cardinality-duplicate-event",
        ),
    ],
)
def test_binding_revalidates_forged_assumption_shapes(
    assumption, mutator, expected_code, expected_path
):
    """The binder rechecks assumption invariants bypassed by direct mutation."""
    mutator(assumption)
    query = BmcQuery(
        property=BmcProperty("reach", 2, predicate=BoolLiteral("true")),
        assumptions=(assumption,),
    )

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    diagnostic = _diagnostic(excinfo)
    assert diagnostic.code == expected_code
    assert expected_path in diagnostic.path


@pytest.mark.unittest
@pytest.mark.parametrize(
    "predicate, code",
    [
        pytest.param("future_condition", "unsupported_condition_expr", id="condition"),
        pytest.param("future_numeric", "unsupported_numeric_expr", id="numeric"),
    ],
)
def test_binding_rejects_unknown_expression_subclasses(predicate, code):
    """Binder fails closed when future expression subclasses reach it."""

    class FutureCond(BmcCondExpr):
        def _canonical_payload(self):
            return {"name": "p"}

        def _to_dsl(self):
            return "future_cond()"

    class FutureNum(BmcNumExpr):
        def _canonical_payload(self):
            return {"name": "x"}

        def _to_dsl(self):
            return "future_num()"

    if predicate == "future_condition":
        query_predicate = FutureCond()
    else:
        query_predicate = NumericComparison(FutureNum(), "==", IntLiteral("0"))
    query = BmcQuery(property=BmcProperty("reach", 1, predicate=query_predicate))

    with pytest.raises(InvalidBmcQuery) as excinfo:
        bind_bmc_query_structure(query)

    assert _diagnostic(excinfo).code == code
