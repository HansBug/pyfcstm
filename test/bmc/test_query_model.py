"""Data model tests for FCSTM BMC query objects."""

import pytest

from pyfcstm.bmc import (
    Active,
    BmcBuildError,
    BmcCondExpr,
    BmcError,
    BmcNumExpr,
    BmcProperty,
    BmcQuery,
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
    assert issubclass(InvalidBmcQuery, BmcError)
    assert issubclass(UnsupportedBmcQuery, BmcError)
    assert issubclass(InvalidBmcEncoding, BmcError)
    assert issubclass(BmcBuildError, BmcError)


@pytest.mark.unittest
def test_literal_canonical_forms_preserve_raw_kind_and_value():
    """Literal canonical forms keep enough information for grammar parity."""
    decimal = IntLiteral("42")
    hexed = IntLiteral("0x2A", kind="hex")
    floating = FloatLiteral("3.5e1")
    fractional = FloatLiteral(".5")
    exponent = FloatLiteral("1e-3")
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
    assert decimal != hexed
    assert floating.to_canonical() == {
        "node": "float_literal",
        "kind": "float",
        "raw": "3.5e1",
        "value": 35.0,
    }
    assert fractional.to_canonical()["value"] == 0.5
    assert exponent.to_canonical()["value"] == 0.001
    assert truth.to_canonical() == {
        "node": "bool_literal",
        "kind": "bool",
        "raw": "TRUE",
        "value": True,
    }


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
    """Expression model keeps the PR-1 anchor for FCSTM expression parity."""
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
        NumBinaryOp(Active("Root.A"), "+", IntLiteral("1"))
    with pytest.raises(TypeError, match="BmcCondExpr"):
        CondBinaryOp(Cycle(), "&&", BoolLiteral("true"))
    with pytest.raises(TypeError, match="BmcCondExpr"):
        NumConditionalOp(Cycle(), IntLiteral("1"), IntLiteral("0"))
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
        EventAssumption("Root.Idle.Start", selector="3").to_canonical()["selector"]
        == "3"
    )
    assert cardinality.to_canonical()["event_paths"] == (
        "Root.Idle.Start",
        "Root.Idle.Stop",
    )
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
        "assumptions": (
            FrameAssumption("at", BoolLiteral("true"), frame=0).to_canonical(),
        ),
        "property": BmcProperty(
            "forbid", bound=4, predicate=Active("Root.Bad")
        ).to_canonical(),
    }


@pytest.mark.unittest
def test_query_model_rejects_invalid_skeleton_values():
    """Model skeletons validate enums and simple structural constraints."""
    with pytest.raises(InvalidBmcQuery, match="mode"):
        InitialSpec(mode="warm")
    with pytest.raises(InvalidBmcQuery, match="state_path"):
        InitialSpec(mode="state")
    with pytest.raises(InvalidBmcQuery, match="bound"):
        BmcProperty("reach", bound=0, predicate=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="kind"):
        BmcProperty("eventually", bound=3, predicate=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="property"):
        BmcProperty("reach", bound=3)
    with pytest.raises(InvalidBmcQuery, match="frame"):
        FrameAssumption("at", BoolLiteral("true"))
    with pytest.raises(InvalidBmcQuery, match="event_path"):
        EventAssumption("")
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector="bad")
    with pytest.raises(InvalidBmcQuery, match="selector"):
        EventAssumption("Root.E", selector=[])
    with pytest.raises(InvalidBmcQuery, match="expected"):
        EventAssumption("Root.E", expected="true")
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
    with pytest.raises(ValueError, match="frame"):
        Active("Root.A", frame="next")
    with pytest.raises(ValueError, match="frame"):
        Event("Root.E", selector=-1)
    with pytest.raises(ValueError, match="identifier"):
        NameRef("not-a-fcstm-id")
    with pytest.raises(ValueError, match="Reserved"):
        NameRef("cycle")
    with pytest.raises(ValueError, match="floating"):
        FloatLiteral("1")
    with pytest.raises(ValueError, match="decimal"):
        IntLiteral("0X2A")
    with pytest.raises(ValueError, match="hexadecimal"):
        IntLiteral("0x")
    with pytest.raises(ValueError, match="spelling"):
        FrameVar("x", spelling="bare")


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
    assert EventAssumption("Root.E", selector=0).to_canonical()["selector"] == 0
    with pytest.raises(InvalidBmcQuery, match="state_path"):
        InitialSpec(mode="cold", state_path="Root.A")
    with pytest.raises(InvalidBmcQuery, match="predicate"):
        InitialSpec(predicate=Cycle())
    with pytest.raises(InvalidBmcQuery, match="frame"):
        FrameAssumption("always", BoolLiteral("true"), frame=0)
    with pytest.raises(InvalidBmcQuery, match="event_paths"):
        EventCardinalityAssumption("at_most_one", ())
    with pytest.raises(InvalidBmcQuery, match="event_paths"):
        EventCardinalityAssumption("at_most_one", "Root.E")
    with pytest.raises(InvalidBmcQuery, match="only valid"):
        EventCardinalityAssumption("any", ("Root.E",))
    with pytest.raises(InvalidBmcQuery, match="event_paths"):
        EventCardinalityAssumption("at_most_one", ("Root.E", ""))
    with pytest.raises(InvalidBmcQuery, match="property"):
        BmcQuery(property=Active("Root.Done"))
    with pytest.raises(InvalidBmcQuery, match="initial"):
        BmcQuery(
            property=BmcProperty("reach", bound=1, predicate=Active("Root.Done")),
            initial=Active("Root.A"),
        )
    with pytest.raises(InvalidBmcQuery, match="assumptions"):
        BmcQuery(
            property=BmcProperty("reach", bound=1, predicate=Active("Root.Done")),
            assumptions=(Active("Root.A"),),
        )
    with pytest.raises(InvalidBmcQuery, match="assumptions"):
        BmcQuery(
            property=BmcProperty("reach", bound=1, predicate=Active("Root.Done")),
            assumptions=Active("Root.A"),
        )
