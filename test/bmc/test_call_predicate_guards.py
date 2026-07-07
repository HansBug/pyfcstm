"""Defensive tests for BMC abstract-call predicate guardrails."""

from dataclasses import replace

import pytest
import z3

import pyfcstm.bmc.binding as binding_module
import pyfcstm.bmc.properties as properties_module
import pyfcstm.bmc.relation as relation_module
from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
    compile_bmc_property,
)
from pyfcstm.bmc.ast import (
    Active,
    BmcCondExpr,
    BmcNumExpr,
    Called,
    CallCount,
    CallFilter,
    CallStepPoint,
    CallStepSelector,
    Cycle,
    FrameVar,
    IntLiteral,
    NumericComparison,
    Terminated,
)
from pyfcstm.bmc.binding import BoundBmcQuery, BoundProperty
from pyfcstm.bmc.domain import build_bmc_domain
from pyfcstm.bmc.macro import BoolTemplate, CycleCase
from pyfcstm.bmc.query import BmcProperty, BmcQuery
from pyfcstm.bmc.relation import BmcAbstractCallRecord, BmcCaseRelation
from pyfcstm.bmc.parse import (
    parse_bmc_cond_expression,
    parse_bmc_query,
)
from pyfcstm.model import load_state_machine_from_text


def _bind_structure(source):
    """Parse and bind a query without a model domain."""
    return binding_module.bind_bmc_query_structure(parse_bmc_query(source))


def _engine_core(dsl, query):
    """Build a core formula for a compact FCSTM model and query."""
    model = load_state_machine_from_text(dsl)
    return build_bmc_core_formula(BmcEngine(model).prepare(query))


def _replace_core_property(core, prop):
    """Return ``core`` with a forged already-bound property object."""
    query = BmcQuery(
        property=prop,
        initial=core.context.query.initial,
        assumptions=core.context.query.assumptions,
    )
    bound_query = BoundBmcQuery(
        query,
        core.context.bound_query.initial,
        core.context.bound_query.assumptions,
        BoundProperty(prop),
        core.context.bound_query.references,
    )
    return replace(
        core, context=replace(core.context, query=query, bound_query=bound_query)
    )


def _minimal_case_relation(**overrides):
    """Construct a minimal case relation, optionally overriding fields."""
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
    kwargs = dict(
        step_index=0,
        case=case,
        selector=z3.Bool("case_selected"),
        antecedent=z3.BoolVal(True),
        consequent=z3.BoolVal(True),
        implication=z3.BoolVal(True),
        selector_constraint=z3.BoolVal(True),
        post_var_exprs={},
        guard_terms={},
        definedness_constraints=(),
        call_records=(),
    )
    kwargs.update(overrides)
    return BmcCaseRelation(**kwargs)


@pytest.mark.unittest
def test_stage_from_runtime_role_uses_exact_role_mapping():
    """Runtime-role stage inference is exact and documents transition effects."""
    assert relation_module._stage_from_runtime_role("state_enter") == "enter"
    assert relation_module._stage_from_runtime_role("state_exit") == "exit"
    assert relation_module._stage_from_runtime_role("leaf_during") == "during"
    assert relation_module._stage_from_runtime_role("plain_during_before") == "during"
    assert relation_module._stage_from_runtime_role("plain_during_after") == "during"
    assert relation_module._stage_from_runtime_role("aspect_during_before") == "during"
    assert relation_module._stage_from_runtime_role("aspect_during_after") == "during"
    assert relation_module._stage_from_runtime_role("transition_effect") == "during"
    with pytest.raises(BmcBuildError, match="unknown action runtime role"):
        relation_module._stage_from_runtime_role("reenter")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "factory, message",
    [
        pytest.param(
            lambda: CallStepPoint("future", 0),
            "kind",
            id="point-kind",
        ),
        pytest.param(
            lambda: CallStepPoint.relative(True),
            "integer",
            id="point-bool",
        ),
        pytest.param(
            lambda: CallStepPoint.absolute(-1),
            "non-negative",
            id="point-negative-absolute",
        ),
        pytest.param(
            lambda: CallStepSelector("future"),
            "unsupported",
            id="selector-kind",
        ),
        pytest.param(
            lambda: CallStepSelector.point("0"),
            "start",
            id="selector-start-type",
        ),
        pytest.param(
            lambda: CallStepSelector.range(CallStepPoint.absolute(0), "1"),
            "end",
            id="selector-end-type",
        ),
        pytest.param(
            lambda: CallStepSelector("all", CallStepPoint.absolute(0)),
            "endpoints",
            id="selector-all-endpoint",
        ),
        pytest.param(
            lambda: CallStepSelector("point"),
            "exactly one",
            id="selector-point-missing",
        ),
        pytest.param(
            lambda: CallStepSelector.range(None, None),
            "invalid",
            id="selector-empty-range",
        ),
        pytest.param(
            lambda: CallStepSelector.range(
                CallStepPoint.absolute(2), CallStepPoint.absolute(1)
            ),
            "start",
            id="selector-reversed-absolute",
        ),
        pytest.param(
            lambda: CallStepSelector.range(CallStepPoint.relative(1), None),
            "future",
            id="selector-open-future",
        ),
        pytest.param(
            lambda: CallStepSelector.range(None, CallStepPoint.relative(-1)),
            "past",
            id="selector-open-past",
        ),
        pytest.param(
            lambda: CallFilter(step=object()),
            "step",
            id="filter-step-type",
        ),
        pytest.param(
            lambda: CallFilter(named_ref="Ref", named_ref_is_null=True),
            "named_ref",
            id="filter-ref-conflict",
        ),
        pytest.param(
            lambda: CallFilter(named_ref_is_null=1),
            "bool",
            id="filter-null-flag-type",
        ),
        pytest.param(
            lambda: CallFilter(where=object()),
            "where",
            id="filter-where-type",
        ),
        pytest.param(
            lambda: CallCount(object()),
            "filter",
            id="count-filter-type",
        ),
        pytest.param(
            lambda: Called(filter=object()),
            "filter",
            id="called-filter-type",
        ),
        pytest.param(
            lambda: Called("Hook", filter=CallFilter(action="Hook")),
            "either",
            id="called-legacy-and-filter",
        ),
    ],
)
def test_call_predicate_ast_objects_reject_invalid_constructor_inputs(factory, message):
    """Call predicate AST nodes fail closed when constructed directly."""
    with pytest.raises(InvalidBmcQuery, match=message):
        factory()


@pytest.mark.unittest
def test_call_predicate_ast_canonical_text_covers_edge_shapes():
    """Call predicate AST nodes expose deterministic canonical DSL text."""
    assert str(CallStepSelector.omitted()) == ""
    assert str(CallStepSelector.all()) == "*"
    assert str(CallStepSelector.point(CallStepPoint.absolute(3))) == "3"
    assert str(CallStepSelector.range(None, CallStepPoint.relative(0))) == "..+0"

    called_default = Called()
    called_legacy = Called("Hook", frame=2)
    called_filtered_no_action = Called(filter=CallFilter(step=CallStepSelector.all()))
    called_filtered_full = Called(
        filter=CallFilter(
            action="Hook",
            stage="during",
            named_ref_is_null=True,
            where=NumericComparison(FrameVar("x"), "==", IntLiteral("1")),
        )
    )

    assert called_default.call_filter.to_canonical()["node"] == "call_filter"
    assert str(called_legacy) == 'called("Hook", 2)'
    assert str(called_filtered_no_action) == "called(*)"
    assert "named_ref=null" in str(called_filtered_full)
    assert called_filtered_full.to_canonical()["filter"]["named_ref_is_null"] is True


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param('called("Hook", where true, stage="during")', id="where-not-last"),
        pytest.param('called(stage="during", 1)', id="positional-after-named"),
        pytest.param('called("A", "B")', id="two-positional-actions"),
        pytest.param('called("A", action="B")', id="duplicate-action"),
    ],
)
def test_call_argument_listener_rejects_invalid_argument_order(expression):
    """Listener-level call-argument checks reject grammar-valid bad calls."""
    with pytest.raises(InvalidBmcQuery):
        parse_bmc_cond_expression(expression)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression, expected",
    [
        pytest.param("called(step=..+0)", "called(..+0)", id="open-start-range"),
        pytest.param("called(step=+0..)", "called(+0..)", id="open-end-range"),
        pytest.param("called(step=+0..+1)", "called(+0..+1)", id="relative-range"),
        pytest.param("called(step=0..1)", "called(0..1)", id="compact-int-range"),
    ],
)
def test_call_step_selector_listener_builds_all_range_shapes(expression, expected):
    """Listener converts call step ranges into the canonical selector objects."""
    assert str(parse_bmc_cond_expression(expression)) == expected


@pytest.mark.unittest
def test_call_where_binding_traverses_snapshot_expression_shapes():
    """Call ``where`` binding walks all allowed snapshot expression families."""
    source = (
        'check reach <= 3: called("Hook", where '
        '((x == 0 && var("x") == 0) ? '
        '!(abs(-((x + 1) * ((true) ? x : var("x")))) < 0) : true));'
    )
    bound = _bind_structure(source)

    assert bound.property.kind == "reach"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, code",
    [
        pytest.param(
            'check reach <= 3: called("Hook", where call_count() >= 0);',
            "call_count_not_allowed",
            id="nested-call-count",
        ),
        pytest.param(
            'check reach <= 3: called("Hook", where active("Root"));',
            "call_where_atom_not_allowed",
            id="active-atom",
        ),
        pytest.param(
            'check reach <= 3: called("Hook", where cycle == 0);',
            "cycle_not_allowed",
            id="cycle-not-snapshot",
        ),
        pytest.param(
            'check reach <= 3: called("Hook", stage="middle");',
            "call_stage",
            id="stage",
        ),
        pytest.param(
            'check reach <= 3: called("Hook", role="bad_role");',
            "call_role",
            id="role",
        ),
    ],
)
def test_call_filter_binding_rejects_invalid_semantic_shapes(source, code):
    """Call filter binding reports specific diagnostics for invalid filters."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        _bind_structure(source)

    assert excinfo.value.diagnostic.code == code


@pytest.mark.unittest
def test_model_binding_resolves_call_action_and_named_ref_paths():
    """Model-aware binding validates action and named-ref call filter targets."""
    model = load_state_machine_from_text(
        """
        state Root {
            state Library {
                enter abstract Shared;
            }
            state A {
                enter FirstRef ref /Library.Shared;
            }
            [*] -> A;
        }
        """
    )
    domain = build_bmc_domain(model, 2)
    good_query = parse_bmc_query(
        'check reach <= 2: called("Root.Library.Shared", named_ref="Root.A.FirstRef");'
    )

    good = binding_module.bind_bmc_query(good_query, domain=domain)
    assert good.property.kind == "reach"

    with pytest.raises(InvalidBmcQuery) as bad_action:
        binding_module.bind_bmc_query(
            parse_bmc_query('check reach <= 2: called("Root.Library.Missing");'),
            domain=domain,
        )
    assert bad_action.value.diagnostic.code == "unknown_call_action"

    with pytest.raises(InvalidBmcQuery) as bad_ref:
        binding_module.bind_bmc_query(
            parse_bmc_query(
                'check reach <= 2: called("Root.Library.Shared", '
                'named_ref="Root.A.Missing");'
            ),
            domain=domain,
        )
    assert bad_ref.value.diagnostic.code == "unknown_named_ref"


@pytest.mark.unittest
def test_call_filter_binding_private_type_guards_are_defensive():
    """Private binder guard functions reject forged non-call-filter objects."""
    assert binding_module._iter_model_actions(None) == ()

    with pytest.raises(InvalidBmcQuery) as bad_selector:
        binding_module._bind_call_step_selector(object(), 1, "property.predicate.step")
    assert bad_selector.value.diagnostic.code == "call_step_selector_type"

    with pytest.raises(InvalidBmcQuery) as bad_filter:
        binding_module._bind_call_filter(
            binding_module._BindingContext(bound=1),
            object(),
            "property.predicate.filter",
        )
    assert bad_filter.value.diagnostic.code == "call_filter_type"


@pytest.mark.unittest
def test_property_call_context_validation_rejects_forged_call_where_atoms():
    """Property compiler rechecks call-where context after binding."""
    base = _engine_core(
        """
        state Root {
            state A {
                during abstract Hook;
            }
            [*] -> A;
        }
        """,
        'check reach <= 1: called("Root.A.Hook");',
    )

    for where_expr, message in (
        (Active("Root.A"), "active"),
        (Terminated(), "terminated"),
        (NumericComparison(Cycle(), "==", IntLiteral("0")), "cycle"),
    ):
        forged = BmcProperty(
            "reach",
            1,
            predicate=Called(filter=CallFilter(action="Root.A.Hook", where=where_expr)),
        )
        with pytest.raises(UnsupportedBmcQuery, match=message):
            compile_bmc_property(_replace_core_property(base, forged))


@pytest.mark.unittest
def test_property_call_context_validation_rejects_non_objective_contexts():
    """Property helper rejects call filters outside property predicate contexts."""
    with pytest.raises(UnsupportedBmcQuery, match="outside property context"):
        properties_module._validate_call_filter_context(
            CallFilter(), "assumption", "assumptions[0].predicate.filter"
        )


@pytest.mark.unittest
def test_property_call_count_private_helpers_reject_forged_shapes():
    """Property helper guards reject malformed arithmetic and step selectors."""
    assert properties_module._require_arith(z3.IntVal(1), "ok").as_long() == 1
    with pytest.raises(BmcBuildError, match="arithmetic"):
        properties_module._require_arith(z3.BoolVal(True), "bad")
    with pytest.raises(UnsupportedBmcQuery, match="call filter"):
        properties_module._validate_call_filter_context(object(), "frame", "call")
    with pytest.raises(InvalidBmcQuery, match="out of range"):
        properties_module._effective_call_steps(
            CallStepSelector.point(CallStepPoint.absolute(1)), 0, 1
        )
    with pytest.raises(InvalidBmcQuery, match="endpoint"):
        properties_module._effective_call_steps(
            CallStepSelector.range(
                CallStepPoint.absolute(0), CallStepPoint.absolute(1)
            ),
            0,
            1,
        )
    assert (
        properties_module._effective_call_steps(
            CallStepSelector.range(
                CallStepPoint.absolute(2), CallStepPoint.relative(1)
            ),
            0,
            3,
        )
        == ()
    )

    with pytest.raises(InvalidBmcQuery, match="unknown snapshot"):
        properties_module._CallSnapshotSymbols({}).frame_var(0, "missing")


@pytest.mark.unittest
def test_call_where_private_binder_rejects_unknown_expression_subclasses():
    """Call-where private traversal fails closed for future AST subclasses."""

    class FutureNum(BmcNumExpr):
        """Numeric node with an unexpected runtime class."""

        def _canonical_payload(self):
            return {}

        def _to_dsl(self):
            return "future_num()"

    class FutureCond(BmcCondExpr):
        """Condition node with an unexpected runtime class."""

        def _canonical_payload(self):
            return {}

        def _to_dsl(self):
            return "future_cond()"

    ctx = binding_module._BindingContext(bound=1)

    with pytest.raises(InvalidBmcQuery) as bad_num:
        binding_module._bind_call_where_num_expr(
            ctx, FutureNum(), "property.predicate.filter.where.left"
        )
    assert bad_num.value.diagnostic.code == "unsupported_call_where_numeric_expr"

    with pytest.raises(InvalidBmcQuery) as bad_cond:
        binding_module._bind_call_where_condition(
            ctx, FutureCond(), "property.predicate.filter.where"
        )
    assert bad_cond.value.diagnostic.code == "unsupported_call_where_condition_expr"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "factory, message",
    [
        pytest.param(
            lambda: BmcAbstractCallRecord(
                True, "Hook", "during", "leaf_during", "Root", "Root", None, {}
            ),
            "integer",
            id="call-record-ordinal-type",
        ),
        pytest.param(
            lambda: BmcAbstractCallRecord(
                -1, "Hook", "during", "leaf_during", "Root", "Root", None, {}
            ),
            "non-negative",
            id="call-record-negative-ordinal",
        ),
        pytest.param(
            lambda: BmcAbstractCallRecord(
                0, "", "during", "leaf_during", "Root", "Root", None, {}
            ),
            "action_name",
            id="call-record-empty-action",
        ),
        pytest.param(
            lambda: BmcAbstractCallRecord(
                0, "Hook", "during", "leaf_during", "Root", "Root", "", {}
            ),
            "named_ref",
            id="call-record-empty-ref",
        ),
        pytest.param(
            lambda: BmcAbstractCallRecord(
                0,
                "Hook",
                "during",
                "leaf_during",
                "Root",
                "Root",
                None,
                {"": z3.Int("x")},
            ),
            "keys",
            id="call-record-empty-snapshot-key",
        ),
        pytest.param(
            lambda: BmcAbstractCallRecord(
                0,
                "Hook",
                "during",
                "leaf_during",
                "Root",
                "Root",
                None,
                {"x": z3.Bool("x")},
            ),
            "values",
            id="call-record-bool-snapshot-value",
        ),
        pytest.param(
            lambda: _minimal_case_relation(call_records=(object(),)),
            "call_records",
            id="case-relation-call-record-type",
        ),
    ],
)
def test_relation_call_record_objects_reject_invalid_constructor_inputs(
    factory, message
):
    """Relation-layer call record dataclasses validate public construction."""
    with pytest.raises(BmcBuildError, match=message):
        factory()


@pytest.mark.unittest
def test_relation_call_record_canonical_and_no_context_lowering_errors():
    """Relation lowering exposes call records and rejects missing call context."""
    record = BmcAbstractCallRecord(
        0,
        "Hook",
        "during",
        "leaf_during",
        "Root",
        "Root",
        None,
        {"x": z3.Int("x")},
    )
    relation = _minimal_case_relation(call_records=(record,))

    assert record.to_canonical()["action_name"] == "Hook"
    assert relation.to_canonical()["call_records"][0]["snapshot"] == {"x": "x"}

    with pytest.raises(UnsupportedBmcQuery, match="call_count"):
        relation_module._lower_bmc_num_expr(CallCount(), object(), frame_index=0)
    with pytest.raises(UnsupportedBmcQuery, match="called"):
        relation_module._lower_bmc_cond_expr(Called(), object(), frame_index=0)


@pytest.mark.unittest
def test_relation_ignores_anonymous_abstract_blocks_for_user_call_counts():
    """Anonymous abstract blocks execute as no-op blocks but create no call record."""
    formula = compile_bmc_property(
        _engine_core(
            """
            state Root {
                state A {
                    during abstract /* anonymous */;
                }
                [*] -> A;
            }
            """,
            "check reach <= 1: call_count(step=*) == 0;",
        )
    )
    solver = z3.Solver()
    solver.add(formula.solve_formula)

    assert solver.check() == z3.sat
