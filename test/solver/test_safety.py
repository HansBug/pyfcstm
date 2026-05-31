"""Tests for solver expression safety classification."""

from dataclasses import FrozenInstanceError

import pytest

from pyfcstm.model import IfBlock, IfBlockBranch, Operation, OperationStatement
from pyfcstm.model.expr import BinaryOp, Float, Integer, UFunc, UnaryOp, Variable
from pyfcstm.solver.safety import (
    SafetyCheck,
    check_expr_safety,
    check_expr_safety_for_effect,
)


def assert_unsafe(expr, reason):
    """Assert that an expression is rejected for the expected reason."""
    result = check_expr_safety(expr)
    assert result.safe is False
    assert result.reason == reason
    assert result.offending_node is not None
    return result.offending_node


def assert_safe(expr):
    """Assert that an expression is accepted as solver-safe."""
    result = check_expr_safety(expr)
    assert result == SafetyCheck(safe=True)


@pytest.mark.unittest
class TestSafetyCheck:
    """Test the public safety result object."""

    def test_safety_check_is_frozen(self):
        """The safety result is immutable after construction."""
        result = SafetyCheck(safe=True)

        with pytest.raises(FrozenInstanceError):
            setattr(result, "safe", False)


@pytest.mark.unittest
class TestBitwiseSafety:
    """Test bitwise operator rejection."""

    def test_bitwise_binary_operator_positive_cases(self):
        """Binary bitwise operators are rejected."""
        left_shift = BinaryOp(Variable("flags"), "<<", Integer(1))
        bit_and = BinaryOp(Variable("flags"), "&", Integer(0xFF))

        assert assert_unsafe(left_shift, "bitwise") is left_shift
        assert assert_unsafe(bit_and, "bitwise") is bit_and

    def test_bitwise_unary_operator_positive_case(self):
        """Unary bitwise not is rejected."""
        bit_not = UnaryOp("~", Variable("flags"))

        assert assert_unsafe(bit_not, "bitwise") is bit_not

    def test_bitwise_negative_case(self):
        """Arithmetic and logical operators are not bitwise hazards."""
        assert_safe(BinaryOp(Variable("flags"), "+", Integer(1)))
        assert_safe(UnaryOp("-", Variable("flags")))


@pytest.mark.unittest
class TestTranscendentalSafety:
    """Test transcendental function rejection."""

    def test_transcendental_positive_cases(self):
        """Trigonometric and logarithmic functions are rejected."""
        sin_expr = UFunc("sin", Variable("angle"))
        log_expr = UFunc("log", Variable("value"))

        assert assert_unsafe(sin_expr, "transcendental") is sin_expr
        assert assert_unsafe(log_expr, "transcendental") is log_expr

    def test_transcendental_additional_positive_cases(self):
        """Exponential and cube-root functions are rejected."""
        exp_expr = UFunc("exp", Variable("value"))
        cbrt_expr = UFunc("cbrt", Variable("value"))

        assert assert_unsafe(exp_expr, "transcendental") is exp_expr
        assert assert_unsafe(cbrt_expr, "transcendental") is cbrt_expr

    def test_transcendental_negative_case(self):
        """Supported algebraic helpers are not classified as transcendental."""
        assert_safe(UFunc("abs", Variable("value")))
        assert_safe(UFunc("sqrt", Variable("value")))


@pytest.mark.unittest
class TestPowerSafety:
    """Test power-expression rejection."""

    def test_double_var_power_positive_cases(self):
        """Power expressions with variables on both sides are rejected."""
        direct = BinaryOp(Variable("base"), "**", Variable("exponent"))
        nested_left = BinaryOp(
            BinaryOp(Variable("base"), "+", Integer(1)),
            "**",
            Variable("exponent"),
        )

        assert assert_unsafe(direct, "double_var_power") is direct
        assert assert_unsafe(nested_left, "double_var_power") is nested_left

    def test_double_var_power_negative_case(self):
        """A variable base with a constant exponent is accepted."""
        assert_safe(BinaryOp(Variable("base"), "**", Integer(2)))

    def test_variable_exponent_positive_cases(self):
        """Constant-base power with variable exponents is rejected."""
        direct = BinaryOp(Integer(2), "**", Variable("exponent"))
        nested_right = BinaryOp(
            Integer(2),
            "**",
            BinaryOp(Variable("exponent"), "+", Integer(1)),
        )

        assert assert_unsafe(direct, "variable_exponent") is direct
        assert assert_unsafe(nested_right, "variable_exponent") is nested_right

    def test_variable_exponent_negative_case(self):
        """Constant-only power expressions are accepted."""
        assert_safe(BinaryOp(Integer(2), "**", Integer(8)))


@pytest.mark.unittest
class TestTraversalAndEffects:
    """Test traversal ordering and operation-block safety."""

    def test_none_input_is_safe(self):
        """Missing optional expressions are safe."""
        assert check_expr_safety(None) == SafetyCheck(safe=True)

    def test_plain_linear_expression_is_safe(self):
        """Linear arithmetic and comparisons are safe."""
        expr = BinaryOp(
            BinaryOp(Variable("value"), "*", Integer(2)),
            "+",
            Float(1.5),
        )

        assert_safe(expr)

    def test_first_unsafe_subexpression_is_reported(self):
        """Traversal reports the first unsafe child before later hazards."""
        first = BinaryOp(Variable("flags"), "|", Integer(1))
        second = UFunc("sin", Variable("angle"))
        expr = BinaryOp(first, "+", second)

        result = check_expr_safety(expr)

        assert result.safe is False
        assert result.reason == "bitwise"
        assert result.offending_node is first

    def test_effect_operation_list_reports_unsafe_assignment(self):
        """Operation safety scans every assignment expression."""
        unsafe_expr = UFunc("tan", Variable("angle"))
        operations = [
            Operation(var_name="safe", expr=BinaryOp(Variable("x"), "+", Integer(1))),
            Operation(var_name="unsafe", expr=unsafe_expr),
        ]

        result = check_expr_safety_for_effect(operations)

        assert result.safe is False
        assert result.reason == "transcendental"
        assert result.offending_node is unsafe_expr

    def test_effect_if_block_reports_unsafe_condition(self):
        """If-block conditions are included in effect safety scans."""
        unsafe_condition = BinaryOp(Variable("flags"), "^", Integer(1))
        operations = [
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=unsafe_condition,
                        statements=[Operation(var_name="x", expr=Integer(1))],
                    ),
                    IfBlockBranch(
                        condition=None,
                        statements=[Operation(var_name="x", expr=Integer(2))],
                    ),
                ]
            )
        ]

        result = check_expr_safety_for_effect(operations)

        assert result.safe is False
        assert result.reason == "bitwise"
        assert result.offending_node is unsafe_condition

    def test_effect_if_block_reports_unsafe_branch_statement(self):
        """If-block branch statements are included in effect safety scans."""
        unsafe_expr = BinaryOp(Integer(2), "**", Variable("exponent"))
        operations = [
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=BinaryOp(Variable("x"), ">", Integer(0)),
                        statements=[Operation(var_name="x", expr=unsafe_expr)],
                    )
                ]
            )
        ]

        result = check_expr_safety_for_effect(operations)

        assert result.safe is False
        assert result.reason == "variable_exponent"
        assert result.offending_node is unsafe_expr

    def test_effect_operation_list_rejects_unknown_statement_type(self):
        """Unknown statement classes are not silently accepted as safe."""

        class UnknownStatement(OperationStatement):
            def to_ast_node(self):
                raise NotImplementedError

        with pytest.raises(TypeError, match="Unknown operation statement type"):
            check_expr_safety_for_effect([UnknownStatement()])

    def test_effect_operation_list_accepts_safe_block(self):
        """Safe assignment and if-block expressions are accepted."""
        operations = [
            Operation(var_name="x", expr=BinaryOp(Variable("x"), "+", Integer(1))),
            IfBlock(
                branches=[
                    IfBlockBranch(
                        condition=BinaryOp(Variable("x"), ">", Integer(0)),
                        statements=[
                            Operation(var_name="y", expr=UFunc("abs", Variable("x")))
                        ],
                    )
                ]
            ),
        ]

        assert check_expr_safety_for_effect(operations) == SafetyCheck(safe=True)
