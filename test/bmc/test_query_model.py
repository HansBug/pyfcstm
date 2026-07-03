"""Data model tests for FCSTM BMC query objects."""

import json

import pytest
from typing import Any, cast

from pyfcstm.bmc import (
    Active,
    BmcAssumption,
    BmcBuildError,
    BmcCondExpr,
    BmcExpr,
    BmcError,
    BmcNumExpr,
    BmcProperty,
    BmcQuery,
    BmcQueryParseError,
    BoolLiteral,
    Called,
    Case,
    CondBinaryOp,
    CondConditionalOp,
    CondUnaryOp,
    Cycle,
    Event,
    EventAssumption,
    EventCardinalityAssumption,
    FloatLiteral,
    FrameAssumption,
    FrameVar,
    InitialSpec,
    IntLiteral,
    InvalidBmcEncoding,
    InvalidBmcQuery,
    MathConst,
    NameRef,
    NumBinaryOp,
    NumConditionalOp,
    NumUnaryOp,
    NumericComparison,
    Terminated,
    UFuncCall,
    UnsupportedBmcQuery,
)


@pytest.mark.unittest
def test_error_hierarchy():
    """BMC errors expose phase-specific subclasses under one base."""
    assert issubclass(BmcQueryParseError, BmcError)
    assert issubclass(InvalidBmcQuery, BmcError)
    assert issubclass(UnsupportedBmcQuery, BmcError)
    assert issubclass(InvalidBmcEncoding, BmcError)
    assert issubclass(BmcBuildError, BmcError)


@pytest.mark.unittest
def test_literal_canonical_forms_preserve_raw_kind_and_value():
    """Literal canonical forms keep enough information for grammar parity."""
    decimal = IntLiteral("42")
    hexed = IntLiteral("0x2A")
    floating = FloatLiteral("3.5e1")
    fractional = FloatLiteral(".5")
    exponent = FloatLiteral("1e-3")
    large_finite = FloatLiteral("1e308")
    truth = BoolLiteral("TRUE")

    assert decimal.to_canonical() == {
        "node": "int_literal",
        "kind": "decimal",
        "raw": "42",
        "value": 42,
    }
    assert hexed.to_canonical() == {
        "node": "int_literal",
        "kind": "hex",
        "raw": "0x2A",
        "value": 42,
    }
    assert IntLiteral("0x2A", kind="hex") == hexed
    assert decimal != hexed
    assert floating.to_canonical() == {
        "node": "float_literal",
        "kind": "float",
        "raw": "3.5e1",
        "value": 35.0,
    }
    assert fractional.to_canonical()["value"] == 0.5
    assert exponent.to_canonical()["value"] == 0.001
    assert large_finite.to_canonical()["raw"] == "1e308"
    json.dumps(large_finite.to_canonical(), allow_nan=False)
    json.dumps(floating.to_canonical(), allow_nan=False)
    assert truth.to_canonical() == {
        "node": "bool_literal",
        "kind": "bool",
        "raw": "TRUE",
        "value": True,
    }


def _round_trip_cases():
    """Build query DSL spelling fixtures for the object-to-text contract."""
    x = NameRef("x")
    y = NameRef("y")
    z = NameRef("z")
    root_idle = Active("Root.Idle")
    root_done = Active("Root.Done")
    comparison = NumericComparison(
        NumBinaryOp(x, "+", IntLiteral("1")), ">=", UFuncCall("sqrt", y)
    )
    condition = CondBinaryOp(
        CondUnaryOp("!", CondBinaryOp(root_idle, "||", root_done)),
        "=>",
        comparison,
    )
    response = BmcProperty(
        "response",
        8,
        trigger=Event("Root.Fault"),
        response=Active("Root.Recovering"),
        within=3,
    )
    cardinality = EventCardinalityAssumption("at_most_one", ("Root.Tick", "Root.Reset"))

    return [
        pytest.param(IntLiteral("0"), "0", id="expr-int-decimal-zero"),
        pytest.param(IntLiteral("42"), "42", id="expr-int-decimal"),
        pytest.param(IntLiteral("007"), "007", id="expr-int-leading-zero"),
        pytest.param(IntLiteral("0x2A"), "0x2A", id="expr-int-hex-upper"),
        pytest.param(IntLiteral("0xff"), "0xff", id="expr-int-hex-lower"),
        pytest.param(FloatLiteral(".5"), ".5", id="expr-float-leading-dot"),
        pytest.param(FloatLiteral("1."), "1.", id="expr-float-trailing-dot"),
        pytest.param(FloatLiteral("3.5e1"), "3.5e1", id="expr-float-exp"),
        pytest.param(FloatLiteral("1e-3"), "1e-3", id="expr-float-negative-exp"),
        pytest.param(BoolLiteral("true"), "true", id="expr-bool-lower-true"),
        pytest.param(BoolLiteral("True"), "true", id="expr-bool-title-true"),
        pytest.param(BoolLiteral("TRUE"), "true", id="expr-bool-upper-true"),
        pytest.param(BoolLiteral("false"), "false", id="expr-bool-lower-false"),
        pytest.param(BoolLiteral("False"), "false", id="expr-bool-title-false"),
        pytest.param(BoolLiteral("FALSE"), "false", id="expr-bool-upper-false"),
        pytest.param(x, "x", id="expr-name-x"),
        pytest.param(NameRef("counter_1"), "counter_1", id="expr-name-counter"),
        pytest.param(MathConst("pi"), "pi", id="expr-const-pi"),
        pytest.param(MathConst("E"), "E", id="expr-const-e"),
        pytest.param(MathConst("tau"), "tau", id="expr-const-tau"),
        pytest.param(NumUnaryOp("+", x), "+x", id="expr-num-unary-plus"),
        pytest.param(NumUnaryOp("-", x), "-x", id="expr-num-unary-minus"),
        pytest.param(
            NumUnaryOp("-", NumBinaryOp(x, "+", IntLiteral("1"))),
            "-(x + 1)",
            id="expr-num-unary-grouped-binary",
        ),
        pytest.param(NumBinaryOp(x, "**", y), "x ** y", id="expr-num-pow"),
        pytest.param(NumBinaryOp(x, "*", y), "x * y", id="expr-num-mul"),
        pytest.param(NumBinaryOp(x, "/", y), "x / y", id="expr-num-div"),
        pytest.param(NumBinaryOp(x, "%", y), "x % y", id="expr-num-mod"),
        pytest.param(NumBinaryOp(x, "+", y), "x + y", id="expr-num-add"),
        pytest.param(NumBinaryOp(x, "-", y), "x - y", id="expr-num-sub"),
        pytest.param(NumBinaryOp(x, "<<", y), "x << y", id="expr-num-shl"),
        pytest.param(NumBinaryOp(x, ">>", y), "x >> y", id="expr-num-shr"),
        pytest.param(NumBinaryOp(x, "&", y), "x & y", id="expr-num-bit-and"),
        pytest.param(NumBinaryOp(x, "^", y), "x ^ y", id="expr-num-bit-xor"),
        pytest.param(NumBinaryOp(x, "|", y), "x | y", id="expr-num-bit-or"),
        pytest.param(
            NumBinaryOp(NumBinaryOp(x, "+", y), "*", IntLiteral("2")),
            "(x + y) * 2",
            id="expr-num-binary-left-group",
        ),
        pytest.param(
            NumBinaryOp(x, "*", NumBinaryOp(y, "+", z)),
            "x * (y + z)",
            id="expr-num-binary-right-group",
        ),
        pytest.param(
            NumConditionalOp(root_idle, NumBinaryOp(x, "+", y), MathConst("pi")),
            '(active("Root.Idle")) ? (x + y) : pi',
            id="expr-num-ternary",
        ),
        pytest.param(UFuncCall("sin", x), "sin(x)", id="expr-ufunc-sin"),
        pytest.param(UFuncCall("cos", x), "cos(x)", id="expr-ufunc-cos"),
        pytest.param(UFuncCall("tan", x), "tan(x)", id="expr-ufunc-tan"),
        pytest.param(UFuncCall("asin", x), "asin(x)", id="expr-ufunc-asin"),
        pytest.param(UFuncCall("acos", x), "acos(x)", id="expr-ufunc-acos"),
        pytest.param(UFuncCall("atan", x), "atan(x)", id="expr-ufunc-atan"),
        pytest.param(UFuncCall("sinh", x), "sinh(x)", id="expr-ufunc-sinh"),
        pytest.param(UFuncCall("cosh", x), "cosh(x)", id="expr-ufunc-cosh"),
        pytest.param(UFuncCall("tanh", x), "tanh(x)", id="expr-ufunc-tanh"),
        pytest.param(UFuncCall("asinh", x), "asinh(x)", id="expr-ufunc-asinh"),
        pytest.param(UFuncCall("acosh", x), "acosh(x)", id="expr-ufunc-acosh"),
        pytest.param(UFuncCall("atanh", x), "atanh(x)", id="expr-ufunc-atanh"),
        pytest.param(UFuncCall("sqrt", x), "sqrt(x)", id="expr-ufunc-sqrt"),
        pytest.param(UFuncCall("cbrt", x), "cbrt(x)", id="expr-ufunc-cbrt"),
        pytest.param(UFuncCall("exp", x), "exp(x)", id="expr-ufunc-exp"),
        pytest.param(UFuncCall("log", x), "log(x)", id="expr-ufunc-log"),
        pytest.param(UFuncCall("log10", x), "log10(x)", id="expr-ufunc-log10"),
        pytest.param(UFuncCall("log2", x), "log2(x)", id="expr-ufunc-log2"),
        pytest.param(UFuncCall("log1p", x), "log1p(x)", id="expr-ufunc-log1p"),
        pytest.param(
            UFuncCall("abs", NumUnaryOp("-", x)), "abs(-x)", id="expr-ufunc-abs"
        ),
        pytest.param(UFuncCall("ceil", x), "ceil(x)", id="expr-ufunc-ceil"),
        pytest.param(UFuncCall("floor", x), "floor(x)", id="expr-ufunc-floor"),
        pytest.param(UFuncCall("round", x), "round(x)", id="expr-ufunc-round"),
        pytest.param(UFuncCall("trunc", x), "trunc(x)", id="expr-ufunc-trunc"),
        pytest.param(UFuncCall("sign", x), "sign(x)", id="expr-ufunc-sign"),
        pytest.param(
            CondUnaryOp("!", root_idle),
            '!active("Root.Idle")',
            id="expr-cond-unary-bang",
        ),
        pytest.param(
            CondUnaryOp("not", root_idle),
            '!active("Root.Idle")',
            id="expr-cond-unary-not",
        ),
        pytest.param(
            CondUnaryOp("!", CondBinaryOp(root_idle, "&&", root_done)),
            '!(active("Root.Idle") && active("Root.Done"))',
            id="expr-cond-unary-grouped-binary",
        ),
        pytest.param(NumericComparison(x, "<", y), "x < y", id="expr-cmp-lt"),
        pytest.param(NumericComparison(x, ">", y), "x > y", id="expr-cmp-gt"),
        pytest.param(NumericComparison(x, "<=", y), "x <= y", id="expr-cmp-le"),
        pytest.param(NumericComparison(x, ">=", y), "x >= y", id="expr-cmp-ge"),
        pytest.param(NumericComparison(x, "==", y), "x == y", id="expr-cmp-eq"),
        pytest.param(NumericComparison(x, "!=", y), "x != y", id="expr-cmp-ne"),
        pytest.param(
            CondBinaryOp(root_idle, "&&", root_done),
            'active("Root.Idle") && active("Root.Done")',
            id="expr-cond-and-symbol",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "and", root_done),
            'active("Root.Idle") && active("Root.Done")',
            id="expr-cond-and-alias",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "||", root_done),
            'active("Root.Idle") || active("Root.Done")',
            id="expr-cond-or-symbol",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "or", root_done),
            'active("Root.Idle") || active("Root.Done")',
            id="expr-cond-or-alias",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "xor", root_done),
            'active("Root.Idle") xor active("Root.Done")',
            id="expr-cond-xor",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "=>", root_done),
            'active("Root.Idle") => active("Root.Done")',
            id="expr-cond-implies-symbol",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "implies", root_done),
            'active("Root.Idle") => active("Root.Done")',
            id="expr-cond-implies-alias",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "iff", root_done),
            'active("Root.Idle") iff active("Root.Done")',
            id="expr-cond-iff",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "==", root_done),
            'active("Root.Idle") == active("Root.Done")',
            id="expr-cond-eq",
        ),
        pytest.param(
            CondBinaryOp(root_idle, "!=", root_done),
            'active("Root.Idle") != active("Root.Done")',
            id="expr-cond-ne",
        ),
        pytest.param(
            CondBinaryOp(
                CondBinaryOp(root_idle, "&&", root_done), "xor", BoolLiteral("true")
            ),
            '(active("Root.Idle") && active("Root.Done")) xor true',
            id="expr-cond-left-group",
        ),
        pytest.param(
            CondBinaryOp(
                root_idle, "&&", CondBinaryOp(root_done, "||", BoolLiteral("false"))
            ),
            'active("Root.Idle") && (active("Root.Done") || false)',
            id="expr-cond-right-group",
        ),
        pytest.param(
            CondConditionalOp(condition, root_done, CondUnaryOp("not", root_idle)),
            '(!(active("Root.Idle") || active("Root.Done")) => (x + 1) >= sqrt(y)) ? active("Root.Done") : !active("Root.Idle")',
            id="expr-cond-ternary",
        ),
        pytest.param(
            FrameVar('quoted"var\\name'),
            'var("quoted\\"var\\\\name")',
            id="expr-frame-var-escaped",
        ),
        pytest.param(
            FrameVar("中文变量"), 'var("中文变量")', id="expr-frame-var-unicode"
        ),
        pytest.param(FrameVar("cycle"), 'var("cycle")', id="expr-frame-var-reserved"),
        pytest.param(Cycle(), "cycle", id="expr-cycle"),
        pytest.param(
            Active("Root.Idle"), 'active("Root.Idle")', id="expr-active-current"
        ),
        pytest.param(
            Active("Root.Idle", frame=2),
            'active("Root.Idle", 2)',
            id="expr-active-frame",
        ),
        pytest.param(Terminated(), "terminated()", id="expr-terminated-current"),
        pytest.param(Terminated(frame=3), "terminated(3)", id="expr-terminated-frame"),
        pytest.param(
            Event("Root.Idle.Start"),
            'event("Root.Idle.Start", current)',
            id="expr-event-current",
        ),
        pytest.param(
            Event("Root.Idle.Start", selector=0),
            'event("Root.Idle.Start", 0)',
            id="expr-event-index",
        ),
        pytest.param(
            Case("Root.A::transition::Root.B::0"),
            'case("Root.A::transition::Root.B::0")',
            id="expr-case-current",
        ),
        pytest.param(
            Case("Root.A::transition::Root.B::0", frame=4),
            'case("Root.A::transition::Root.B::0", 4)',
            id="expr-case-frame",
        ),
        pytest.param(
            Called("CheckLimit"), 'called("CheckLimit")', id="expr-called-current"
        ),
        pytest.param(
            Called("CheckLimit", frame=5),
            'called("CheckLimit", 5)',
            id="expr-called-frame",
        ),
        pytest.param(InitialSpec(), "init cold;", id="query-init-cold"),
        pytest.param(
            InitialSpec(mode="terminated"),
            "init terminated;",
            id="query-init-terminated",
        ),
        pytest.param(
            InitialSpec(mode="cold", predicate=Active("Root.Ready")),
            'init cold where active("Root.Ready");',
            id="query-init-cold-where",
        ),
        pytest.param(
            InitialSpec(mode="terminated", predicate=Terminated()),
            "init terminated where terminated();",
            id="query-init-terminated-where",
        ),
        pytest.param(
            InitialSpec(mode="state", state_path="Root.Active"),
            'init state("Root.Active");',
            id="query-init-state",
        ),
        pytest.param(
            InitialSpec(
                mode="state",
                state_path="Root.Active",
                predicate=NumericComparison(FrameVar("x"), ">=", IntLiteral("0")),
            ),
            'init state("Root.Active") where var("x") >= 0;',
            id="query-init-state-where",
        ),
        pytest.param(
            FrameAssumption(
                "always", NumericComparison(FrameVar("x"), "<=", IntLiteral("100"))
            ),
            'assume always: var("x") <= 100;',
            id="query-assume-always",
        ),
        pytest.param(
            FrameAssumption("at", Active("Root.Ready"), frame=2),
            'assume at 2: active("Root.Ready");',
            id="query-assume-at",
        ),
        pytest.param(
            EventAssumption("Root.Tick"),
            'assume event("Root.Tick", *) == true;',
            id="query-assume-event-any",
        ),
        pytest.param(
            EventAssumption("Root.Tick", selector="01..03"),
            'assume event("Root.Tick", 1..3) == true;',
            id="query-assume-event-range",
        ),
        pytest.param(
            EventAssumption("Root.Tick", selector="02..02"),
            'assume event("Root.Tick", 2) == true;',
            id="query-assume-event-point-range",
        ),
        pytest.param(
            EventAssumption("Root.Reset", selector=0, expected=False),
            'assume event("Root.Reset", 0) == false;',
            id="query-assume-event-false",
        ),
        pytest.param(
            EventCardinalityAssumption("any"),
            "assume events cardinality any;",
            id="query-cardinality-any",
        ),
        pytest.param(
            cardinality,
            'assume events cardinality at_most_one {\n    "Root.Tick",\n    "Root.Reset"\n};',
            id="query-cardinality-at-most-one",
        ),
        pytest.param(
            BmcProperty("reach", 5, predicate=Active("Root.Done")),
            'check reach <= 5: active("Root.Done");',
            id="query-check-reach",
        ),
        pytest.param(
            BmcProperty("forbid", 5, predicate=Active("Root.Bad")),
            'check forbid <= 5: active("Root.Bad");',
            id="query-check-forbid",
        ),
        pytest.param(
            BmcProperty("invariant", 5, predicate=BoolLiteral("true")),
            "check invariant <= 5: true;",
            id="query-check-invariant",
        ),
        pytest.param(
            BmcProperty("must_reach", 5, predicate=Active("Root.Done")),
            'check must_reach <= 5: active("Root.Done");',
            id="query-check-must-reach",
        ),
        pytest.param(
            BmcProperty("exists_always", 5, predicate=Active("Root.Safe")),
            'check exists_always <= 5: active("Root.Safe");',
            id="query-check-exists-always",
        ),
        pytest.param(
            BmcProperty("cover", 5, predicate=Case("Root.A::transition::Root.B::0")),
            'check cover <= 5: case("Root.A::transition::Root.B::0");',
            id="query-check-cover",
        ),
        pytest.param(
            response,
            'check response <= 8:\n    trigger event("Root.Fault", current)\n    -> within 3 active("Root.Recovering");',
            id="query-check-response",
        ),
        pytest.param(
            BmcQuery(property=BmcProperty("reach", 1, predicate=Active("Root.Done"))),
            'init cold;\n\ncheck reach <= 1: active("Root.Done");',
            id="query-root-minimal",
        ),
        pytest.param(
            BmcQuery(
                initial=InitialSpec(
                    mode="state",
                    state_path="Root.Active",
                    predicate=NumericComparison(FrameVar("x"), ">=", IntLiteral("0")),
                ),
                assumptions=(
                    FrameAssumption(
                        "always",
                        NumericComparison(FrameVar("x"), "<=", IntLiteral("100")),
                    ),
                    FrameAssumption("at", Active("Root.Ready"), frame=2),
                    EventAssumption("Root.Tick", selector="01..03"),
                    EventAssumption("Root.Reset", selector=0, expected=False),
                    cardinality,
                    EventCardinalityAssumption("any"),
                ),
                property=response,
            ),
            'init state("Root.Active") where var("x") >= 0;\n\n'
            'assume always: var("x") <= 100;\n\n'
            'assume at 2: active("Root.Ready");\n\n'
            'assume event("Root.Tick", 1..3) == true;\n\n'
            'assume event("Root.Reset", 0) == false;\n\n'
            'assume events cardinality at_most_one {\n    "Root.Tick",\n    "Root.Reset"\n};\n\n'
            "assume events cardinality any;\n\n"
            'check response <= 8:\n    trigger event("Root.Fault", current)\n    -> within 3 active("Root.Recovering");',
            id="query-root-full",
        ),
    ]


ROUND_TRIP_CASES = _round_trip_cases()


@pytest.mark.unittest
@pytest.mark.parametrize("node, expected", ROUND_TRIP_CASES)
def test_bmc_nodes_render_canonical_query_dsl_spelling(node, expected):
    """AST/query nodes stringify to canonical ``.fbmcq`` DSL spelling."""
    assert str(node) == expected


@pytest.mark.unittest
def test_round_trip_fixture_count_is_intentionally_large():
    """Round-trip coverage stays broad enough to protect parser follow-up work."""
    assert len(ROUND_TRIP_CASES) >= 100


@pytest.mark.unittest
def test_bmc_nodes_keep_dataclass_repr_for_debugging():
    """Concrete nodes retain the dataclass-generated ``repr`` shape."""
    nodes = [param.values[0] for param in ROUND_TRIP_CASES]

    for node in nodes:
        representation = repr(node)
        assert representation.startswith("%s(" % node.__class__.__name__)
        assert representation.endswith(")")
        fields = getattr(node, "__dataclass_fields__", {})
        for field_name in fields:
            if not field_name.startswith("_"):
                assert "%s=" % field_name in representation


@pytest.mark.unittest
def test_fcstm_compatible_expression_canonical_shapes():
    """Core expression nodes cover the FCSTM expression grammar shape."""
    x = NameRef("x")
    y = NameRef("y")
    comparison = NumericComparison(x, "<", IntLiteral("10"))
    condition = CondBinaryOp(comparison, "and", CondUnaryOp("not", Active("Root.Idle")))
    numeric = NumConditionalOp(condition, UFuncCall("sqrt", x), MathConst("pi"))

    assert NumUnaryOp("-", x).to_canonical() == {
        "node": "num_unary",
        "op": "-",
        "operand": x.to_canonical(),
    }
    assert NumBinaryOp(x, "**", y).to_canonical() == {
        "node": "num_binary",
        "op": "**",
        "left": x.to_canonical(),
        "right": y.to_canonical(),
    }
    assert condition.to_canonical()["op"] == "&&"
    assert condition.right.to_canonical()["op"] == "!"
    assert numeric.to_canonical() == {
        "node": "num_conditional",
        "condition": condition.to_canonical(),
        "if_true": UFuncCall("sqrt", x).to_canonical(),
        "if_false": MathConst("pi").to_canonical(),
    }
    assert (
        CondBinaryOp(
            BoolLiteral("true"), "implies", BoolLiteral("FALSE")
        ).to_canonical()["op"]
        == "=>"
    )
    assert CondConditionalOp(
        condition, BoolLiteral("true"), BoolLiteral("false")
    ).to_canonical()["node"] == ("cond_conditional")


@pytest.mark.unittest
def test_all_fcstm_operator_aliases_and_ufuncs_are_representable():
    """Expression model keeps the anchor for FCSTM expression parity."""
    x = NameRef("x")
    y = NameRef("y")

    for op in ["**", "*", "/", "%", "+", "-", "<<", ">>", "&", "^", "|"]:
        assert NumBinaryOp(x, op, y).to_canonical()["op"] == op
    for op in ["<", ">", "<=", ">=", "==", "!="]:
        assert NumericComparison(x, op, y).to_canonical()["op"] == op
    for raw_op, canonical_op in [
        ("&&", "&&"),
        ("and", "&&"),
        ("||", "||"),
        ("or", "||"),
        ("=>", "=>"),
        ("implies", "=>"),
        ("xor", "xor"),
        ("iff", "iff"),
        ("==", "=="),
        ("!=", "!="),
    ]:
        assert (
            CondBinaryOp(
                BoolLiteral("true"), raw_op, BoolLiteral("false")
            ).to_canonical()["op"]
            == canonical_op
        )
    for func in [
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "asinh",
        "acosh",
        "atanh",
        "sqrt",
        "cbrt",
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
        "abs",
        "ceil",
        "floor",
        "round",
        "trunc",
        "sign",
    ]:
        assert UFuncCall(func, x).to_canonical()["func"] == func


@pytest.mark.unittest
def test_bool_literal_raw_families_share_values_but_keep_raw_spelling():
    """Boolean canonical shape preserves parser spelling while normalizing value."""
    assert [BoolLiteral(raw).value for raw in ["true", "True", "TRUE"]] == [
        True,
        True,
        True,
    ]
    assert [BoolLiteral(raw).value for raw in ["false", "False", "FALSE"]] == [
        False,
        False,
        False,
    ]
    assert BoolLiteral("True").to_canonical()["raw"] == "True"
    assert str(BoolLiteral("True")) == "true"
    assert str(BoolLiteral("FALSE")) == "false"


@pytest.mark.unittest
def test_bmc_only_nodes_have_expected_types_and_canonical_forms():
    """BMC extension atoms stay typed as numeric or conditional nodes."""
    numeric_nodes = [FrameVar("x"), Cycle()]
    condition_nodes = [
        Active("Root.Idle"),
        Terminated(),
        Event("Root.Idle.Start", selector=0),
        Event("Root.Idle.Start", selector="current"),
        Case("Root.Idle::transition::Root.Done::0", frame=1),
        Called("CheckLimit", frame=2),
    ]

    assert all(isinstance(node, BmcNumExpr) for node in numeric_nodes)
    assert all(isinstance(node, BmcCondExpr) for node in condition_nodes)
    assert FrameVar("x").to_canonical() == {
        "node": "frame_var",
        "name": "x",
        "spelling": "var_call",
    }
    assert Cycle().to_canonical() == {"node": "cycle"}
    assert Active("Root.Idle").to_canonical() == {
        "node": "active",
        "state_path": "Root.Idle",
        "frame": "current",
    }
    assert Event("Root.Idle.Start", selector="current").to_canonical() == {
        "node": "event",
        "event_path": "Root.Idle.Start",
        "selector": "current",
    }
    assert Terminated(frame=2).to_canonical() == {
        "node": "terminated",
        "frame": 2,
    }
    assert Case("Root.Idle::transition::Root.Done::0", frame=1).to_canonical() == {
        "node": "case",
        "label": "Root.Idle::transition::Root.Done::0",
        "frame": 1,
    }
    assert Called("CheckLimit", frame=2).to_canonical() == {
        "node": "called",
        "name": "CheckLimit",
        "frame": 2,
    }


@pytest.mark.unittest
def test_shallow_expression_type_validation():
    """Expression constructors reject numeric/condition subtype mix-ups early."""
    with pytest.raises(TypeError, match="BmcNumExpr"):
        NumBinaryOp(cast(Any, Active("Root.A")), "+", IntLiteral("1"))
    with pytest.raises(TypeError, match="BmcCondExpr"):
        CondBinaryOp(cast(Any, Cycle()), "&&", BoolLiteral("true"))
    with pytest.raises(TypeError, match="BmcCondExpr"):
        NumConditionalOp(cast(Any, Cycle()), IntLiteral("1"), IntLiteral("0"))
    with pytest.raises(ValueError, match="Unsupported"):
        CondBinaryOp(BoolLiteral("true"), "&&&", BoolLiteral("false"))


@pytest.mark.unittest
def test_initial_spec_and_property_skeletons():
    """Top-level query model represents default init, assumptions, and properties."""
    init = InitialSpec()
    frame_assumption = FrameAssumption(
        "always", NumericComparison(NameRef("x"), "<=", IntLiteral("10"))
    )
    event_assumption = EventAssumption(
        "Root.Idle.Start", selector="0..3", expected=True
    )
    cardinality = EventCardinalityAssumption(
        "at_most_one",
        event_paths=("Root.Idle.Start", "Root.Idle.Stop"),
    )
    reach = BmcProperty("reach", bound=5, predicate=Active("Root.Done"))
    response = BmcProperty(
        "response",
        bound=7,
        trigger=Event("Root.Idle.Start"),
        response=Active("Root.Done"),
        within=3,
    )
    cover = BmcProperty(
        "cover", bound=3, predicate=Case("Root.Idle::transition::Root.Done::0")
    )

    assert init.to_canonical() == {
        "node": "initial_spec",
        "mode": "cold",
        "state_path": None,
        "predicate": None,
    }
    assert (
        frame_assumption.to_canonical()["predicate"]
        == NumericComparison(NameRef("x"), "<=", IntLiteral("10")).to_canonical()
    )
    assert event_assumption.to_canonical() == {
        "node": "event_assumption",
        "event_path": "Root.Idle.Start",
        "selector": "0..3",
        "expected": True,
    }
    assert (
        EventAssumption("Root.Idle.Start", selector="3").to_canonical()["selector"] == 3
    )
    assert cardinality.to_canonical()["event_paths"] == [
        "Root.Idle.Start",
        "Root.Idle.Stop",
    ]
    assert reach.to_canonical()["kind"] == "reach"
    assert response.to_canonical()["trigger"] == Event("Root.Idle.Start").to_canonical()
    assert response.to_canonical()["within"] == 3
    assert (
        cover.to_canonical()["predicate"]
        == Case("Root.Idle::transition::Root.Done::0").to_canonical()
    )


@pytest.mark.unittest
@pytest.mark.parametrize("kind", ["forbid", "invariant", "must_reach", "exists_always"])
def test_predicate_property_kinds_are_supported(kind):
    """Predicate-only property kinds share the same structural contract."""
    prop = BmcProperty(kind, bound=2, predicate=Active("Root.Target"))

    assert prop.to_canonical()["kind"] == kind
    assert prop.to_canonical()["predicate"] == Active("Root.Target").to_canonical()


@pytest.mark.unittest
def test_bmc_query_canonical_form_is_stable():
    """BmcQuery composes top-level fields into a stable canonical dump."""
    query = BmcQuery(
        property=BmcProperty("forbid", bound=4, predicate=Active("Root.Bad")),
        assumptions=(FrameAssumption("at", BoolLiteral("true"), frame=0),),
    )

    assert query.to_canonical() == {
        "node": "bmc_query",
        "initial": InitialSpec().to_canonical(),
        "assumptions": [
            FrameAssumption("at", BoolLiteral("true"), frame=0).to_canonical(),
        ],
        "property": BmcProperty(
            "forbid", bound=4, predicate=Active("Root.Bad")
        ).to_canonical(),
    }


@pytest.mark.unittest
def test_query_canonical_collections_survive_json_round_trip():
    """Canonical query collections use JSON-stable list shapes."""
    cardinality = EventCardinalityAssumption("at_most_one", ("Root.A", "Root.B"))
    empty_cardinality = EventCardinalityAssumption("any")
    query = BmcQuery(property=BmcProperty("reach", 1, predicate=Active("Root.Done")))
    assumed_query = BmcQuery(
        property=BmcProperty("forbid", 2, predicate=Active("Root.Bad")),
        assumptions=(FrameAssumption("always", BoolLiteral("true")),),
    )

    for canonical in [
        cardinality.to_canonical(),
        empty_cardinality.to_canonical(),
        query.to_canonical(),
        assumed_query.to_canonical(),
    ]:
        assert json.loads(json.dumps(canonical, allow_nan=False)) == canonical

    assert empty_cardinality.to_canonical()["event_paths"] == []
    assert query.to_canonical()["assumptions"] == []


@pytest.mark.unittest
@pytest.mark.parametrize("node", [case.values[0] for case in ROUND_TRIP_CASES])
def test_round_trip_fixture_canonical_forms_are_json_stable(node):
    """Every round-trip fixture emits JSON-stable canonical data."""
    assert (
        json.loads(json.dumps(node.to_canonical(), allow_nan=False))
        == node.to_canonical()
    )


@pytest.mark.unittest
def test_query_model_rejects_invalid_skeleton_values():
    """Model skeletons validate enums and simple structural constraints."""
    with pytest.raises(InvalidBmcQuery, match="mode"):
        InitialSpec(mode="warm")
    with pytest.raises(InvalidBmcQuery, match="mode"):
        InitialSpec(mode=cast(Any, []))
    with pytest.raises(InvalidBmcQuery, match="state_path"):
        InitialSpec(mode="state")
    with pytest.raises(InvalidBmcQuery, match="state_path"):
        InitialSpec(mode="state", state_path=cast(Any, 42))
    with pytest.raises(InvalidBmcQuery, match="bound"):
        BmcProperty("reach", bound=0, predicate=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="kind"):
        BmcProperty("eventually", bound=3, predicate=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="property"):
        BmcProperty("reach", bound=3)
    with pytest.raises(InvalidBmcQuery, match="kind"):
        FrameAssumption(cast(Any, []), BoolLiteral("true"))
    with pytest.raises(InvalidBmcQuery, match="frame"):
        FrameAssumption("at", BoolLiteral("true"))
    with pytest.raises(InvalidBmcQuery, match="event_path"):
        EventAssumption("")
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector="bad")
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector=cast(Any, []))
    with pytest.raises(InvalidBmcQuery, match="expected"):
        EventAssumption("Root.E", expected=cast(Any, "true"))
    with pytest.raises(InvalidBmcQuery, match="only accept predicate"):
        BmcProperty(
            "reach",
            bound=3,
            predicate=Active("Root.Done"),
            trigger=Event("Root.E"),
        )
    with pytest.raises(InvalidBmcQuery, match="response window"):
        BmcProperty(
            "response",
            bound=3,
            trigger=Event("Root.E"),
            response=Active("Root.B"),
        )
    with pytest.raises(InvalidBmcQuery, match="only accept trigger"):
        BmcProperty(
            "response",
            bound=3,
            predicate=Active("Root.A"),
            trigger=Event("Root.E"),
            response=Active("Root.B"),
            within=1,
        )
    with pytest.raises(InvalidBmcQuery, match="property predicate"):
        BmcProperty("cover", bound=3)


@pytest.mark.unittest
def test_expression_model_rejects_invalid_literal_and_frame_values():
    """Expression model shallow checks catch malformed literal and frame values."""
    with pytest.raises(ValueError, match="non-empty"):
        IntLiteral("")
    with pytest.raises(ValueError, match="boolean"):
        BoolLiteral("maybe")
    for invalid_frame in ["next", True, -1, []]:
        with pytest.raises(InvalidBmcQuery, match="frame"):
            Active("Root.A", frame=invalid_frame)
        with pytest.raises(InvalidBmcQuery, match="frame"):
            Terminated(frame=invalid_frame)
        with pytest.raises(InvalidBmcQuery, match="frame"):
            Case("Root.A::fallback::Root.A::0", frame=invalid_frame)
        with pytest.raises(InvalidBmcQuery, match="frame"):
            Called("Check", frame=invalid_frame)
    for invalid_selector in ["next", True, -1, []]:
        with pytest.raises(InvalidBmcQuery, match="selector"):
            Event("Root.E", selector=invalid_selector)
    with pytest.raises(ValueError, match="identifier"):
        NameRef("not-a-fcstm-id")
    with pytest.raises(ValueError, match="Reserved"):
        NameRef("cycle")
    with pytest.raises(ValueError, match="Reserved"):
        NameRef("where")
    with pytest.raises(ValueError, match="floating"):
        FloatLiteral("1")
    with pytest.raises(ValueError, match="finite"):
        FloatLiteral("1e999")
    with pytest.raises(ValueError, match="hexadecimal"):
        IntLiteral("0X2A")
    with pytest.raises(ValueError, match="decimal"):
        IntLiteral("-42")
    with pytest.raises(ValueError, match="decimal"):
        IntLiteral("42\n")
    with pytest.raises(ValueError, match="hexadecimal"):
        IntLiteral("0x2A\n")
    with pytest.raises(ValueError, match="floating"):
        FloatLiteral("1.\n")
    with pytest.raises(ValueError, match="identifier"):
        NameRef("cycle\n")
    with pytest.raises(ValueError, match="hexadecimal"):
        IntLiteral("0x")
    with pytest.raises(ValueError, match="kind"):
        IntLiteral("0x2A", kind="decimal")
    with pytest.raises(ValueError, match="kind"):
        IntLiteral("42", kind="hex")
    with pytest.raises(InvalidBmcQuery, match="spelling"):
        FrameVar("x", spelling="bare")
    with pytest.raises(InvalidBmcQuery, match="name"):
        FrameVar("")
    with pytest.raises(InvalidBmcQuery, match="state_path"):
        Active("")
    with pytest.raises(InvalidBmcQuery, match="event_path"):
        Event("")
    with pytest.raises(InvalidBmcQuery, match="label"):
        Case("")
    with pytest.raises(InvalidBmcQuery, match="name"):
        Called("")


@pytest.mark.unittest
def test_query_model_rejects_additional_invalid_structural_values():
    """Query model rejects wrong primitive types and malformed containers."""
    with pytest.raises(InvalidBmcQuery, match="bound"):
        BmcProperty("reach", bound=True, predicate=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="bound"):
        BmcProperty("reach", bound=-1, predicate=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="frame"):
        FrameAssumption("at", BoolLiteral("true"), frame=True)
    with pytest.raises(InvalidBmcQuery, match="frame"):
        FrameAssumption("at", BoolLiteral("true"), frame=-1)
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector=True)
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector=-1)
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector="current")
    for selector in ["²", "²..3", "３", "１..２", "3..2"]:
        with pytest.raises(InvalidBmcQuery, match="selector"):
            EventAssumption("Root.E", selector=selector)
    assert EventAssumption("Root.E", selector=0).to_canonical()["selector"] == 0
    assert EventAssumption("Root.E", selector="0").to_canonical()["selector"] == 0
    assert (
        EventAssumption("Root.E", selector="01..02").to_canonical()["selector"]
        == "1..2"
    )
    assert EventAssumption("Root.E", selector="007").to_canonical()["selector"] == 7
    assert EventAssumption("Root.E", selector="03..03").to_canonical()["selector"] == 3
    with pytest.raises(InvalidBmcQuery, match="state_path"):
        InitialSpec(mode="cold", state_path="Root.A")
    with pytest.raises(InvalidBmcQuery, match="predicate"):
        InitialSpec(predicate=cast(Any, Cycle()))
    with pytest.raises(InvalidBmcQuery, match="frame"):
        FrameAssumption("always", BoolLiteral("true"), frame=0)
    with pytest.raises(InvalidBmcQuery, match="kind"):
        EventCardinalityAssumption(cast(Any, []))
    with pytest.raises(InvalidBmcQuery, match="event_paths"):
        EventCardinalityAssumption("at_most_one", ())
    with pytest.raises(InvalidBmcQuery, match="event_paths"):
        EventCardinalityAssumption("at_most_one", cast(Any, "Root.E"))
    with pytest.raises(InvalidBmcQuery, match="only valid"):
        EventCardinalityAssumption("any", ("Root.E",))
    with pytest.raises(InvalidBmcQuery, match="event_paths"):
        EventCardinalityAssumption("at_most_one", ("Root.E", ""))
    with pytest.raises(InvalidBmcQuery, match="duplicate"):
        EventCardinalityAssumption("at_most_one", ("Root.E", "Root.E"))
    with pytest.raises(InvalidBmcQuery, match="property"):
        BmcQuery(property=cast(Any, Active("Root.Done")))
    with pytest.raises(InvalidBmcQuery, match="initial"):
        BmcQuery(
            property=BmcProperty("reach", bound=1, predicate=Active("Root.Done")),
            initial=cast(Any, Active("Root.A")),
        )
    with pytest.raises(InvalidBmcQuery, match="assumptions"):
        BmcQuery(
            property=BmcProperty("reach", bound=1, predicate=Active("Root.Done")),
            assumptions=cast(Any, (Active("Root.A"),)),
        )
    with pytest.raises(InvalidBmcQuery, match="assumptions"):
        BmcQuery(
            property=BmcProperty("reach", bound=1, predicate=Active("Root.Done")),
            assumptions=cast(Any, Active("Root.A")),
        )


@pytest.mark.unittest
def test_bmc_expression_bases_are_abstract():
    """Expression category bases must not be instantiated directly."""

    for base_cls in (BmcExpr, BmcNumExpr, BmcCondExpr):
        with pytest.raises(TypeError, match="abstract"):
            cast(Any, base_cls)()


@pytest.mark.unittest
def test_bmc_assumption_base_requires_canonical_payload():
    """Public assumption subclasses must implement canonical payloads."""

    class FakeAssumption(BmcAssumption):
        pass

    with pytest.raises(TypeError, match="abstract"):
        cast(Any, FakeAssumption)()
