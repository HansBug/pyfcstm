"""Tests for the engine with the concrete interpretation."""
import math

import pytest

from pyfcstm.model import IfBlock, IfBlockBranch, Operation
from pyfcstm.model.expr import (
    BinaryOp,
    Boolean,
    ConditionalOp,
    Expr,
    Float,
    Integer,
    UnaryOp,
    Variable,
    parse_expr,
)
from pyfcstm.semantics import ir
from pyfcstm.semantics.adapters import expression_from_model, statements_from_model
from pyfcstm.semantics.concrete import CONCRETE, evaluate, normalize_persistent
from pyfcstm.semantics.engine import Interpretation, compile_expression, compile_statements
from pyfcstm.semantics.errors import EvaluationError, WritebackError


def _run(text, **env):
    return evaluate(parse_expr(text), env)


def _block(operations):
    return compile_statements(statements_from_model(operations), CONCRETE)


@pytest.mark.unittest
class TestAdapters:
    def test_expression_structure_and_identifiers(self):
        node = expression_from_model(parse_expr("(x > 0) ? -y : sqrt(z)"), "root")
        assert isinstance(node, ir.Conditional)
        assert node.node_id == "root"
        assert (node.test.node_id, node.if_true.node_id, node.if_false.node_id) == ("root.0", "root.1", "root.2")
        assert node.test.op == ">"
        assert node.if_true.op == "unary-"
        assert node.if_false.func == "sqrt"
        assert node.if_false.args[0].reference == "z"

    @pytest.mark.parametrize("op, token", [("and", "&&"), ("or", "||"), ("implies", "=>"), ("%", "%")])
    def test_operator_aliases_are_canonical(self, op, token):
        node = expression_from_model(BinaryOp(Boolean(True), op, Boolean(False)))
        assert node.op == token

    def test_unary_not_is_canonical(self):
        assert expression_from_model(UnaryOp("not", Boolean(True))).op == "!"
        assert expression_from_model(UnaryOp("+", Integer(1))).op == "unary+"

    def test_literals_keep_origin(self):
        literal = Float(2.5)
        node = expression_from_model(literal)
        assert node.value == 2.5 and node.origin is literal

    def test_subclasses_of_model_expressions_are_accepted(self):
        class Named(Variable):
            pass

        assert expression_from_model(Named("x")).reference == "x"

    def test_unknown_expression_is_rejected(self):
        with pytest.raises(TypeError, match="Unsupported expression type: Expr"):
            expression_from_model(Expr())

    def test_statement_structure(self):
        block = statements_from_model(
            [
                Operation("x", parse_expr("1")),
                IfBlock(
                    [
                        IfBlockBranch(parse_expr("x > 0"), [Operation("y", parse_expr("2"))]),
                        IfBlockBranch(None, []),
                    ]
                ),
            ],
            "blk",
        )
        assign, branch = block
        assert (assign.node_id, assign.target) == ("blk.0", "x")
        assert branch.node_id == "blk.1"
        assert [arm.node_id for arm in branch.arms] == ["blk.1.0", "blk.1.1"]
        assert branch.arms[0].body[0].target == "y"
        assert branch.arms[1].test is None

    def test_unknown_statement_is_rejected(self):
        with pytest.raises(TypeError, match="Unknown operation statement type"):
            statements_from_model([object()])


@pytest.mark.unittest
class TestConcreteExpressions:
    @pytest.mark.parametrize("text, env, expected", [
        ("7 / 2", {}, 3.5),
        ("x % -2", {"x": 7}, -1),
        ("2 ** -1", {}, 0.5),
        ("cbrt(-8)", {}, -2.0),
        ("sign(x)", {"x": -0.5}, -1),
        ("(x > 0) ? 1 : 2", {"x": 0}, 2),
        ("pi > 3", {}, True),
        ("!(x > 0)", {"x": 0}, True),
        ("(x > 0) xor (y > 0)", {"x": 1, "y": 1}, False),
        ("(x > 0) iff (y > 0)", {"x": 1, "y": 0}, False),
    ])
    def test_values(self, text, env, expected):
        assert _run(text, **env) == expected

    def test_short_circuit_operators_skip_the_right_operand(self):
        assert _run("x != 0 && 10 / x > 1", x=0) is False
        assert _run("x == 0 || 10 / x > 1", x=0) is True
        assert _run("x != 0 => 10 / x > 1", x=0) is True
        assert _run("x != 0 => 10 / x > 1", x=20) is False

    def test_eager_logical_operators_evaluate_both_operands(self):
        with pytest.raises(EvaluationError) as info:
            _run("(x == 0) xor (10 / x > 1)", x=0)
        assert info.value.kind == "division_by_zero"

    def test_conditional_evaluates_only_the_selected_branch(self):
        assert _run("(x == 0) ? 0 : 10 / x", x=0) == 0
        assert _run("(x == 0) ? 10 / x : 1", x=2) == 1

    @pytest.mark.parametrize("text, env, kind, error_type", [
        ("1 / x", {"x": 0}, "division_by_zero", ZeroDivisionError),
        ("1 % x", {"x": 0}, "modulo_by_zero", ZeroDivisionError),
        ("x ** -1", {"x": 0}, "zero_negative_power", ZeroDivisionError),
        ("x ** 0.5", {"x": -4}, "complex_result", ValueError),
        ("sqrt(x)", {"x": -1}, "math_domain", ValueError),
        ("x << -1", {"x": 1}, "negative_shift_count", ValueError),
        ("x << 1", {"x": 1.5}, "invalid_operand", TypeError),
        ("exp(x)", {"x": 1000}, "overflow", OverflowError),
    ])
    def test_runtime_errors_name_their_kind(self, text, env, kind, error_type):
        with pytest.raises(EvaluationError) as info:
            _run(text, **env)
        assert info.value.kind == kind
        assert isinstance(info.value.error, error_type)
        assert info.value.node is not None
        assert info.value.statement is None and info.value.role is None

    def test_math_domain_messages_are_normalized(self):
        with pytest.raises(EvaluationError) as info:
            _run("log(x)", x=0)
        assert str(info.value) == "math domain error"
        assert isinstance(info.value.__cause__, ValueError)

    def test_huge_shift_is_an_overflow(self):
        with pytest.raises(EvaluationError) as info:
            _run("1 << x", x=10 ** 30)
        assert info.value.kind == "overflow"

    def test_missing_variable_raises_key_error(self):
        with pytest.raises(KeyError):
            _run("x + 1")

    @pytest.mark.parametrize("node, token", [
        (ir.Call("e", None, "hypot", (ir.Literal("e.0", None, 1),)), "hypot"),
        (ir.Unary("e", None, "~", ir.Literal("e.0", None, 1)), "~"),
        (ir.Binary("e", None, "<=>", ir.Literal("e.0", None, 1), ir.Literal("e.1", None, 2)), "<=>"),
    ])
    def test_unknown_operations_are_rejected(self, node, token):
        with pytest.raises(KeyError, match=token):
            compile_expression(node, CONCRETE)({}, None)

    def test_unexplained_exceptions_propagate_unchanged(self):
        # abs() takes one argument; the TypeError is not an abs error rule,
        # so it surfaces as is instead of becoming an EvaluationError.
        node = ir.Call("e", None, "abs", (ir.Literal("e.0", None, -1), ir.Literal("e.1", None, 2)))
        with pytest.raises(TypeError):
            compile_expression(node, CONCRETE)({}, None)

    def test_host_atoms_are_resolved_by_the_interpretation(self):
        class Host(type(CONCRETE)):
            def host_atom(self, node, args, env, ctx):
                return (node.key, args, env["k"])

        node = ir.HostAtom("e", None, "test.atom", None, (ir.Literal("e.0", None, 3),))
        assert compile_expression(node, Host())({"k": 9}, None) == ("test.atom", (3,), 9)

    def test_unknown_ir_nodes_are_rejected(self):
        with pytest.raises(TypeError, match="Unsupported IR expression"):
            compile_expression(ir.Expr("e", None), CONCRETE)
        with pytest.raises(TypeError, match="Unsupported IR statement"):
            compile_statements((ir.Stmt("s", None),), CONCRETE)

    def test_conditional_without_selectable_branch_is_reported(self):
        class Never(type(CONCRETE)):
            def decide(self, condition, node, ctx, role):
                return False

            def no_branch(self, node, ctx):
                return "none"

        node = expression_from_model(ConditionalOp(Boolean(True), Integer(1), Integer(2)))
        assert compile_expression(node, Never())({}, None) == "none"

    def test_interpretation_base_methods_are_abstract(self):
        base = Interpretation()
        node = ir.Literal("e", None, 1)
        calls = [
            lambda: base.literal(node),
            lambda: base.symbol(node, {}, None),
            lambda: base.apply(node, None, (), None),
            lambda: base.unknown_operation(node, (), None),
            lambda: base.host_atom(node, (), {}, None),
            lambda: base.truth(1, node, None),
            lambda: base.negate(True),
            lambda: base.decide(True, node, None, "branch"),
            lambda: base.enter(None, True, node, "branch", True),
            lambda: base.constant(True, node),
            lambda: base.no_branch(node, None),
        ]
        for call in calls:
            with pytest.raises(NotImplementedError):
                call()


@pytest.mark.unittest
class TestConcreteStatements:
    def test_assignments_see_earlier_results(self):
        scope = {"x": 1}
        _block([Operation("x", parse_expr("x + 1")), Operation("y", parse_expr("x * 10"))])(scope, None)
        assert scope == {"x": 2, "y": 20}

    def test_first_matching_arm_runs_and_temporaries_disappear(self):
        block = _block(
            [
                IfBlock(
                    [
                        IfBlockBranch(parse_expr("x > 5"), [Operation("x", parse_expr("0"))]),
                        IfBlockBranch(
                            parse_expr("x > 1"),
                            [Operation("t", parse_expr("x * 2")), Operation("x", parse_expr("t"))],
                        ),
                        IfBlockBranch(None, [Operation("x", parse_expr("-1"))]),
                    ]
                )
            ]
        )
        for start, expected in ((9, 0), (3, 6), (0, -1)):
            scope = {"x": start}
            block(scope, None)
            assert scope == {"x": expected}

    def test_no_matching_arm_leaves_scope_unchanged(self):
        scope = {"x": 0}
        _block([IfBlock([IfBlockBranch(parse_expr("x > 0"), [Operation("x", parse_expr("1"))])])])(scope, None)
        assert scope == {"x": 0}

    def test_assignment_errors_record_the_statement(self):
        operation = Operation("y", parse_expr("1 / x"))
        with pytest.raises(EvaluationError) as info:
            _block([operation])({"x": 0}, None)
        assert info.value.role == "value"
        assert info.value.statement.target == "y"
        assert info.value.statement.origin is operation

    def test_condition_errors_record_the_branch(self):
        branch = IfBlockBranch(parse_expr("1 / x > 0"), [])
        with pytest.raises(EvaluationError) as info:
            _block([IfBlock([branch])])({"x": 0}, None)
        assert info.value.role == "test"
        assert info.value.statement.origin is branch

    def test_innermost_statement_is_kept(self):
        inner = Operation("y", parse_expr("1 / x"))
        block = _block([IfBlock([IfBlockBranch(parse_expr("true"), [inner])])])
        with pytest.raises(EvaluationError) as info:
            block({"x": 0}, None)
        assert info.value.statement.origin is inner


@pytest.mark.unittest
class TestPersistentNormalization:
    @pytest.mark.parametrize("declared, value, expected", [
        ("int", 3, 3), ("int", 3.0, 3), ("float", 3, 3.0), ("float", 2.5, 2.5),
    ])
    def test_accepted_values(self, declared, value, expected):
        result = normalize_persistent("x", declared, value, "test")
        assert result == expected and type(result) is type(expected)

    @pytest.mark.parametrize("declared, value, kind, message", [
        ("int", True, "writeback_type", "test must not be bool"),
        ("int", "1", "writeback_type", "test must be int or float, got str"),
        ("float", math.inf, "writeback_non_finite", "declared float must be finite, got inf"),
        ("int", math.nan, "writeback_non_finite", "declared int must be finite, got nan"),
        ("int", 3.5, "writeback_non_integral", "cannot assign float 3.5; non-integer float from test"),
        ("float", 10 ** 400, "writeback_float_range", "integer is outside Python float range"),
    ])
    def test_rejected_values(self, declared, value, kind, message):
        with pytest.raises(WritebackError, match=message) as info:
            normalize_persistent("x", declared, value, "test")
        assert info.value.kind == kind
        assert isinstance(info.value, ValueError)

    def test_unknown_declared_type_is_rejected(self):
        with pytest.raises(ValueError, match="unsupported persistent type 'bool'"):
            normalize_persistent("x", "bool", 1, "test")
