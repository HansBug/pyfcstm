"""
Tests for solver operation parsing and execution.
"""

import pytest
import z3

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.solver.operation import (
    OperationBranch,
    OperationFailure,
    OperationSource,
    execute_operations,
    execute_operations_domain,
    merge_operation_definedness,
    parse_operations,
)
from pyfcstm.solver.domain import DomainConstraint, DomainSource
from pyfcstm.model import (
    IfBlock,
    IfBlockBranch,
    Operation,
    OperationStatement,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.model.expr import Variable, Integer, BinaryOp
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.simulate import SimulationRuntime


def assert_symbolic_outputs(var_exprs, new_exprs, assumptions, expected_outputs):
    solver = z3.Solver()
    for name, value in assumptions.items():
        solver.add(var_exprs[name] == value)
    for name, value in expected_outputs.items():
        solver.add(new_exprs[name] == value)
    assert solver.check() == z3.sat


def assert_z3_expr_equal(actual_expr, expected_expr):
    actual_simplified = z3.simplify(actual_expr)
    expected_simplified = z3.simplify(expected_expr)
    assert z3.eq(actual_simplified, expected_simplified), (
        f"Expected Z3 expr {expected_simplified.sexpr()}, "
        f"got {actual_simplified.sexpr()}"
    )


def assert_z3_expr_equivalent(actual_expr, expected_expr):
    solver = z3.Solver()
    solver.add(actual_expr != expected_expr)
    assert solver.check() == z3.unsat, (
        f"Expected Z3 expr equivalent to {expected_expr}, got {actual_expr}"
    )


def assert_constraints_allow(constraints, *extra_constraints):
    solver = z3.Solver()
    solver.add(*constraints)
    solver.add(*extra_constraints)
    assert solver.check() == z3.sat


def assert_constraints_reject(constraints, *extra_constraints):
    solver = z3.Solver()
    solver.add(*constraints)
    solver.add(*extra_constraints)
    assert solver.check() == z3.unsat


def build_runtime_for_block(block_code: str, initial_values):
    define_lines = [
        f"def int {name} = {value};" for name, value in initial_values.items()
    ]
    dsl_code = "\n".join(
        define_lines
        + [
            "state Root {",
            "    state A {",
            "        during {",
            block_code,
            "        }",
            "    }",
            "    [*] -> A;",
            "}",
        ]
    )
    ast = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    sm = parse_dsl_node_to_state_machine(ast)
    return SimulationRuntime(sm)


@pytest.mark.unittest
class TestParseOperations:
    """Test parse_operations function."""

    def test_parse_single_operation(self):
        """Test parsing a single operation."""
        ops = parse_operations("x = 10;")
        assert len(ops) == 1
        assert ops[0].var_name == "x"

    def test_parse_multiple_operations(self):
        """Test parsing multiple operations."""
        ops = parse_operations("x = 10; y = 20; z = 30;")
        assert len(ops) == 3
        assert ops[0].var_name == "x"
        assert ops[1].var_name == "y"
        assert ops[2].var_name == "z"

    def test_parse_with_expressions(self):
        """Test parsing operations with complex expressions."""
        ops = parse_operations("x = x + 1; y = x * 2;")
        assert len(ops) == 2
        assert ops[0].var_name == "x"
        assert ops[1].var_name == "y"

    def test_parse_empty_operations(self):
        """Test parsing empty operation set."""
        ops = parse_operations("")
        assert len(ops) == 0

    def test_parse_with_semicolons_only(self):
        """Test parsing with only semicolons."""
        ops = parse_operations(";;;")
        assert len(ops) == 0

    def test_parse_mixed_with_empty_statements(self):
        """Test parsing with empty statements mixed in."""
        ops = parse_operations("x = 1; ; y = 2; ;")
        assert len(ops) == 2
        assert ops[0].var_name == "x"
        assert ops[1].var_name == "y"

    def test_free_mode_no_restrictions(self):
        """Test free mode with no variable restrictions."""
        ops = parse_operations("a = b + c; d = e * f;", allowed_vars=None)
        assert len(ops) == 2
        assert ops[0].var_name == "a"
        assert ops[1].var_name == "d"

    def test_restricted_mode_valid_variables(self):
        """Test restricted mode with valid variables."""
        ops = parse_operations("x = x + 1; y = x * 2;", allowed_vars=["x", "y"])
        assert len(ops) == 2

    def test_restricted_mode_temporary_assignment_target(self):
        """Test restricted mode allows temporary assignment targets."""
        ops = parse_operations("z = x + 1; y = z * 2;", allowed_vars=["x", "y"])
        assert [op.var_name for op in ops] == ["z", "y"]

    def test_restricted_mode_invalid_expression_variable(self):
        """Test restricted mode with invalid variable in expression."""
        with pytest.raises(
            ValueError, match="Variable 'z' is not in allowed variables"
        ):
            parse_operations("x = z + 1;", allowed_vars=["x", "y"])

    def test_restricted_mode_variable_used_before_assignment(self):
        """Test restricted mode rejects temporary variables used before assignment."""
        with pytest.raises(
            ValueError, match="Variable 'z' is not in allowed variables"
        ):
            parse_operations("y = z + 1; z = x + 1;", allowed_vars=["x", "y"])

    def test_parse_with_bitwise_operators(self):
        """Test parsing operations with bitwise operators."""
        ops = parse_operations("x = x & 0xFF; y = x | 0x01;")
        assert len(ops) == 2

    def test_parse_with_functions(self):
        """Test parsing operations with mathematical functions."""
        ops = parse_operations("x = sin(y); z = sqrt(x);")
        assert len(ops) == 2

    def test_parse_invalid_syntax(self):
        """Test parsing with invalid syntax."""
        with pytest.raises(GrammarParseError):
            parse_operations("x = ;")

    def test_parse_unknown_statement_node_raises(self, monkeypatch):
        """Unexpected DSL operation nodes are rejected explicitly."""
        from pyfcstm.solver import operation

        class UnknownStatementNode:
            pass

        monkeypatch.setattr(
            operation,
            "parse_with_grammar_entry",
            lambda code, entry: [UnknownStatementNode()],
        )

        with pytest.raises(TypeError, match="Unknown operational statement node type"):
            operation.parse_operations("ignored")

    def test_parse_missing_semicolon(self):
        """Test parsing with missing semicolon."""
        with pytest.raises(GrammarParseError):
            parse_operations("x = 10")

    def test_parse_if_statement(self):
        """Test parsing an operation-block if statement."""
        statements = parse_operations(
            """
        if [x > 0] {
            y = x + 1;
        } else {
            y = x + 2;
        }
        """,
            allowed_vars=["x", "y"],
        )

        assert len(statements) == 1
        assert isinstance(statements[0], IfBlock)
        assert len(statements[0].branches) == 2
        assert statements[0].branches[1].condition is None

    def test_parse_if_condition_rejects_unknown_variable(self):
        """Test restricted mode rejects unknown variables in if conditions."""
        with pytest.raises(
            ValueError, match="Variable 'missing' is not in allowed variables"
        ):
            parse_operations(
                """
            if [missing > 0] {
                x = x + 1;
            }
            """,
                allowed_vars=["x"],
            )

    def test_parse_branch_local_temp_does_not_escape(self):
        """Test restricted mode rejects branch-local temporaries after the if block."""
        with pytest.raises(
            ValueError, match="Variable 'tmp' is not in allowed variables"
        ):
            parse_operations(
                """
            if [x > 0] {
                tmp = x + 1;
            }
            y = tmp;
            """,
                allowed_vars=["x", "y"],
            )

    def test_parse_outer_temp_can_be_used_after_if(self):
        """Test restricted mode allows pre-if temporaries to be used after the if block."""
        statements = parse_operations(
            """
        tmp = x + 1;
        if [x > 0] {
            tmp = tmp + 10;
        }
        y = tmp;
        """,
            allowed_vars=["x", "y"],
        )

        assert len(statements) == 3
        assert isinstance(statements[1], IfBlock)


@pytest.mark.unittest
class TestExecuteOperations:
    """Test execute_operations function."""

    def test_execute_single_operation(self):
        """Test executing a single operation."""
        op = Operation(var_name="x", expr=Integer(10))
        x = z3.Int("x")
        var_exprs = {"x": x}

        new_exprs = execute_operations(op, var_exprs)
        assert "x" in new_exprs
        # Verify the result is 10
        solver = z3.Solver()
        solver.add(new_exprs["x"] == 10)
        assert solver.check() == z3.sat

    def test_execute_operation_list(self):
        """Test executing a list of operations."""
        ops = [
            Operation(var_name="x", expr=Integer(5)),
            Operation(var_name="y", expr=Integer(10)),
        ]
        x = z3.Int("x")
        y = z3.Int("y")
        var_exprs = {"x": x, "y": y}

        new_exprs = execute_operations(ops, var_exprs)
        assert "x" in new_exprs
        assert "y" in new_exprs

    def test_execute_with_variable_reference(self):
        """Test executing operation that references a variable."""
        op = Operation(
            var_name="x", expr=BinaryOp(x=Variable("x"), op="+", y=Integer(1))
        )
        x = z3.Int("x")
        var_exprs = {"x": x}

        new_exprs = execute_operations(op, var_exprs)

        # Verify symbolically: new_exprs['x'] should be x + 1
        solver = z3.Solver()
        solver.add(x == 5)
        solver.add(new_exprs["x"] == 6)
        assert solver.check() == z3.sat

    def test_execute_sequential_operations(self):
        """Test executing operations that depend on each other."""
        ops = [
            Operation(
                var_name="x", expr=BinaryOp(x=Variable("x"), op="+", y=Integer(2))
            ),
            Operation(
                var_name="y", expr=BinaryOp(x=Variable("y"), op="+", y=Variable("x"))
            ),
        ]
        x = z3.Int("x")
        y = z3.Int("y")
        var_exprs = {"x": x, "y": y}

        new_exprs = execute_operations(ops, var_exprs)

        # x should be x + 2
        # y should be y + (x + 2)
        solver = z3.Solver()
        solver.add(x == 5, y == 10)
        solver.add(new_exprs["x"] == 7)  # 5 + 2
        solver.add(new_exprs["y"] == 17)  # 10 + 7
        assert solver.check() == z3.sat

    def test_execute_does_not_modify_original_state(self):
        """Test that execution does not modify the original state."""
        op = Operation(var_name="x", expr=Integer(10))
        x = z3.Int("x")
        var_exprs = {"x": x}

        original_x = var_exprs["x"]
        new_exprs = execute_operations(op, var_exprs)

        # Original state should be unchanged
        assert var_exprs["x"] is original_x
        # New state should be different
        assert new_exprs is not var_exprs

    def test_execute_with_multiple_variables(self):
        """Test executing operations with multiple variables."""
        ops = [
            Operation(var_name="x", expr=Integer(10)),
            Operation(var_name="y", expr=Integer(20)),
            Operation(
                var_name="z", expr=BinaryOp(x=Variable("x"), op="+", y=Variable("y"))
            ),
        ]
        x = z3.Int("x")
        y = z3.Int("y")
        z = z3.Int("z")
        var_exprs = {"x": x, "y": y, "z": z}

        new_exprs = execute_operations(ops, var_exprs)

        # z should be 10 + 20 = 30
        solver = z3.Solver()
        solver.add(new_exprs["z"] == 30)
        assert solver.check() == z3.sat

    def test_execute_with_temporary_variable(self):
        """Test executing operations with temporary variables that do not leak."""
        ops = [
            Operation(
                var_name="tmp", expr=BinaryOp(x=Variable("x"), op="+", y=Variable("y"))
            ),
            Operation(
                var_name="x", expr=BinaryOp(x=Variable("tmp"), op="+", y=Integer(1))
            ),
        ]
        x = z3.Int("x")
        y = z3.Int("y")
        var_exprs = {"x": x, "y": y}

        new_exprs = execute_operations(ops, var_exprs)

        assert set(new_exprs.keys()) == {"x", "y"}
        assert "tmp" not in new_exprs

        solver = z3.Solver()
        solver.add(x == 5, y == 10)
        solver.add(new_exprs["x"] == 16)
        solver.add(new_exprs["y"] == 10)
        assert solver.check() == z3.sat

    def test_execute_with_bitwise_operations(self):
        """Test executing operations with bitwise operators."""
        # Note: Z3 IntVal doesn't support bitwise operations with concrete values
        # This test verifies that the operation parsing works, but execution
        # with concrete Z3 values may have limitations
        ops = [
            Operation(var_name="x", expr=Integer(0xFF)),
            Operation(var_name="y", expr=Integer(0x0F)),
        ]
        x = z3.Int("x")
        y = z3.Int("y")
        var_exprs = {"x": x, "y": y}

        new_exprs = execute_operations(ops, var_exprs)

        # x should be 255, y should be 15
        solver = z3.Solver()
        solver.add(new_exprs["x"] == 255)
        solver.add(new_exprs["y"] == 15)
        assert solver.check() == z3.sat

    @pytest.mark.parametrize(
        ["code", "var_names", "expected_builder"],
        [
            (
                """
                if [x > 0] {
                    y = x + 10;
                }
                """,
                ["x", "y"],
                lambda vars_: {
                    "x": vars_["x"],
                    "y": z3.If(vars_["x"] > 0, vars_["x"] + 10, vars_["y"]),
                },
            ),
            (
                """
                if [x > 0] {
                    y = x + 10;
                } else {
                    y = x + 20;
                }
                """,
                ["x", "y"],
                lambda vars_: {
                    "x": vars_["x"],
                    "y": z3.If(vars_["x"] > 0, vars_["x"] + 10, vars_["x"] + 20),
                },
            ),
            (
                """
                if [mode == 0] {
                    y = 10;
                } else if [mode == 1] {
                    y = 20;
                } else {
                    y = 30;
                }
                """,
                ["x", "y", "mode"],
                lambda vars_: {
                    "x": vars_["x"],
                    "y": z3.If(
                        z3.IntVal(0) == vars_["mode"],
                        z3.IntVal(10),
                        z3.If(
                            z3.IntVal(1) == vars_["mode"], z3.IntVal(20), z3.IntVal(30)
                        ),
                    ),
                    "mode": vars_["mode"],
                },
            ),
            (
                """
                if [x > 0] {
                    tmp = x + 1;
                    if [y > 0] {
                        z = tmp + y;
                    } else {
                        z = tmp + 100;
                    }
                } else {
                    z = 999;
                }
                """,
                ["x", "y", "z"],
                lambda vars_: {
                    "x": vars_["x"],
                    "y": vars_["y"],
                    "z": z3.If(
                        vars_["x"] > 0,
                        z3.If(
                            vars_["y"] > 0,
                            vars_["x"] + 1 + vars_["y"],
                            vars_["x"] + 101,
                        ),
                        z3.IntVal(999),
                    ),
                },
            ),
            (
                """
                if [x > 0] {
                    x = x + 1;
                    y = x + 10;
                } else {
                    y = y + 100;
                }
                """,
                ["x", "y"],
                lambda vars_: {
                    "x": z3.If(vars_["x"] > 0, vars_["x"] + 1, vars_["x"]),
                    "y": z3.If(vars_["x"] > 0, vars_["x"] + 11, vars_["y"] + 100),
                },
            ),
        ],
    )
    def test_execute_if_blocks_symbolically(self, code, var_names, expected_builder):
        statements = parse_operations(code, allowed_vars=var_names)
        var_exprs = {name: z3.Int(name) for name in var_names}

        new_exprs = execute_operations(statements, var_exprs)
        expected_exprs = expected_builder(var_exprs)

        assert set(new_exprs.keys()) == set(var_exprs.keys())
        for name in var_names:
            assert_z3_expr_equal(new_exprs[name], expected_exprs[name])

    def test_execute_branch_local_temp_does_not_leak(self):
        """Test branch-local temporary expressions do not appear in final output."""
        statements = parse_operations(
            """
        if [x > 0] {
            tmp = x + y;
            x = tmp + 1;
        }
        """,
            allowed_vars=["x", "y"],
        )
        var_exprs = {"x": z3.Int("x"), "y": z3.Int("y")}

        new_exprs = execute_operations(statements, var_exprs)

        assert set(new_exprs.keys()) == {"x", "y"}
        assert "tmp" not in new_exprs
        assert_z3_expr_equal(
            new_exprs["x"],
            z3.If(
                var_exprs["x"] > 0, var_exprs["x"] + var_exprs["y"] + 1, var_exprs["x"]
            ),
        )
        assert_z3_expr_equal(new_exprs["y"], var_exprs["y"])

    def test_execute_outer_temp_participates_in_merge(self):
        """Test pre-if temporary expressions participate in branch merge."""
        statements = parse_operations(
            """
        tmp = x + 1;
        if [x > 0] {
            tmp = tmp + 10;
        }
        y = tmp;
        """,
            allowed_vars=["x", "y"],
        )
        var_exprs = {"x": z3.Int("x"), "y": z3.Int("y")}

        new_exprs = execute_operations(statements, var_exprs)

        assert set(new_exprs.keys()) == {"x", "y"}
        assert_z3_expr_equal(new_exprs["x"], var_exprs["x"])
        assert_z3_expr_equal(
            new_exprs["y"],
            z3.If(var_exprs["x"] > 0, var_exprs["x"] + 11, var_exprs["x"] + 1),
        )

    def test_execute_unknown_statement_type_raises(self):
        """The legacy executor still raises on unsupported statement objects."""
        x = z3.Int("x")

        with pytest.raises(TypeError, match="Unknown operation statement type"):
            execute_operations(OperationStatement(), {"x": x})


@pytest.mark.unittest
class TestExecuteOperationsDomain:
    """Test domain-aware operation execution."""

    def test_operation_source_is_domain_source_alias(self):
        """Operation source metadata reuses the expression-domain source type."""
        assert OperationSource is DomainSource

    def test_operation_branch_rejects_invalid_metadata(self):
        """Branch metadata keeps unreachable records internally consistent."""
        selector = z3.BoolVal(True)

        with pytest.raises(ValueError, match="branch kind"):
            OperationBranch(branch_id=None, branch_kind="case", selector=selector)
        with pytest.raises(ValueError, match="branch status"):
            OperationBranch(
                branch_id=None,
                branch_kind="if",
                selector=selector,
                status="maybe",
            )
        with pytest.raises(ValueError, match="result_env"):
            OperationBranch(
                branch_id=None,
                branch_kind="if",
                selector=selector,
                status="unsat",
                result_env={"x": z3.Int("x")},
            )
        with pytest.raises(ValueError, match="definedness constraints"):
            OperationBranch(
                branch_id=None,
                branch_kind="if",
                selector=selector,
                status="unsat",
                definedness_constraints=(DomainConstraint(selector),),
            )
        with pytest.raises(ValueError, match="failures"):
            OperationBranch(
                branch_id=None,
                branch_kind="if",
                selector=selector,
                status="unsat",
                failure=OperationFailure(kind="value_error", reason="bad branch"),
            )

    def test_else_only_branch_uses_true_selector(self):
        """A degenerate else-only block uses a true branch selector."""
        y = z3.Int("y")
        statement = IfBlock(
            branches=[
                IfBlockBranch(
                    condition=None,
                    statements=[Operation(var_name="y", expr=Integer(1))],
                ),
            ]
        )

        execution = execute_operations_domain(statement, {"y": y})

        assert execution.failure is None
        assert len(execution.branches) == 1
        assert execution.branches[0].branch_kind == "else"
        assert z3.is_true(z3.simplify(execution.branches[0].selector))
        assert_z3_expr_equal(execution.env["y"], z3.IntVal(1))

    def test_sequential_definedness_prunes_later_unreachable_branch(self):
        """Earlier domain constraints guide later conditional expression pruning."""
        statements = parse_operations(
            """
            x = 1 / y;
            z = (y == 0) ? sin(a) : x;
            """,
            allowed_vars=None,
        )
        var_exprs = {
            "x": z3.Int("x"),
            "y": z3.Int("y"),
            "z": z3.Int("z"),
            "a": z3.Real("a"),
        }

        execution = execute_operations_domain(statements, var_exprs)

        assert execution.failure is None
        assert execution.expr_constraints == ()
        assert set(execution.env.keys()) == set(var_exprs.keys())
        assert "tmp" not in execution.env
        assert [str(item.constraint) for item in execution.definedness_constraints] == [
            "y != 0"
        ]
        assert len(execution.steps) == 2
        assert_z3_expr_equal(execution.env["z"], execution.env["x"])

    def test_dead_execution_point_skips_later_assignment_translation(self):
        """A later assignment is skipped once prior domains make the path dead."""
        statements = parse_operations(
            """
            x = 1 / y;
            z = sin(a);
            """,
            allowed_vars=None,
        )
        x = z3.Int("x")
        y = z3.Int("y")
        z = z3.Int("z")
        a = z3.Real("a")

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y, "z": z, "a": a},
            path_conditions=(y == 0,),
        )

        assert execution.failure is None
        assert len(execution.steps) == 1
        assert execution.branches == ()
        assert_z3_expr_equal(execution.env["z"], z)
        assert_constraints_reject(
            [item.constraint for item in execution.definedness_constraints],
            y == 0,
        )

    def test_dead_execution_point_skips_later_if_condition_translation(self):
        """A later if-block is skipped when the whole execution point is dead."""
        statements = parse_operations(
            """
            x = 1 / y;
            if [sin(a) > 0] {
                z = 1;
            } else {
                z = 2;
            }
            """,
            allowed_vars=None,
        )
        x = z3.Int("x")
        y = z3.Int("y")
        z = z3.Int("z")
        a = z3.Real("a")

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y, "z": z, "a": a},
            path_conditions=(y == 0,),
        )

        assert execution.failure is None
        assert len(execution.steps) == 1
        assert execution.branches == ()
        assert_z3_expr_equal(execution.env["z"], z)
        assert_constraints_reject(
            [item.constraint for item in execution.definedness_constraints],
            y == 0,
        )

    def test_dead_execution_point_unknown_status_does_not_skip(self, monkeypatch):
        """Unknown reachability at a statement boundary must not prune execution."""
        from pyfcstm.solver import operation
        from pyfcstm.solver.logical import SatResult

        def always_unknown(constraints, *, timeout_ms=None, get_model=False):
            return SatResult(kind="unknown")

        monkeypatch.setattr(operation, "is_sat", always_unknown)
        statements = parse_operations(
            """
            x = 1 / y;
            z = sin(a);
            """,
            allowed_vars=None,
        )
        x = z3.Int("x")
        y = z3.Int("y")
        z = z3.Int("z")
        a = z3.Real("a")

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y, "z": z, "a": a},
            path_conditions=(y == 0,),
        )

        assert execution.failure is not None
        assert execution.failure.kind == "not_implemented"
        assert len(execution.steps) == 1

    def test_reachable_failure_stops_after_preserving_previous_definedness(self):
        """The first reachable translation failure stops later statements."""
        statements = parse_operations(
            """
            x = 1 / y;
            z = missing;
            w = 1;
            """,
            allowed_vars=None,
        )
        var_exprs = {
            "x": z3.Int("x"),
            "y": z3.Int("y"),
            "z": z3.Int("z"),
            "w": z3.Int("w"),
        }

        execution = execute_operations_domain(statements, var_exprs)

        assert execution.failure is not None
        assert execution.failure.kind == "value_error"
        assert execution.failure.translation_failure is not None
        assert execution.failure.translation_failure.kind == "value_error"
        assert "missing" in execution.failure.reason
        assert [step.after for step in execution.steps][-1]["x"] is execution.env["x"]
        assert len(execution.steps) == 1
        assert [str(item.constraint) for item in execution.definedness_constraints] == [
            "y != 0"
        ]
        assert_z3_expr_equal(execution.env["w"], var_exprs["w"])

    def test_branch_condition_definedness_is_guarded_by_prior_selectors(self):
        """An elif condition is evaluated only after earlier branches are skipped."""
        x, y = z3.Ints("x y")
        statements = parse_operations(
            """
            if [x == 0] {
                y = 0;
            } else if [1 / x > 0] {
                y = 1;
            } else {
                y = 2;
            }
            """,
            allowed_vars=["x", "y"],
        )

        execution = execute_operations_domain(statements, {"x": x, "y": y})

        assert execution.failure is None
        constraints = [item.constraint for item in execution.definedness_constraints]
        assert_constraints_allow(constraints, x == 0, execution.env["y"] == 0)
        assert any(
            "Implies" in str(item.constraint)
            for item in execution.definedness_constraints
        )
        assert any(
            "Implies" in str(item.constraint)
            for item in execution.branches[1].definedness_constraints
        )

        failing_statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
            } else if [1 / x > 0] {
                y = 2;
            } else {
                y = 3;
            }
            """,
            allowed_vars=["x", "y"],
        )
        failing_execution = execute_operations_domain(
            failing_statements, {"x": x, "y": y}
        )
        failing_constraints = [
            item.constraint for item in failing_execution.definedness_constraints
        ]

        assert failing_execution.failure is None
        assert_constraints_reject(failing_constraints, x == 0)

    def test_reachable_condition_translation_failure_stops_execution(self):
        """A reachable condition translation failure stops before branch bodies."""
        a = z3.Real("a")
        y = z3.Int("y")
        statements = parse_operations(
            """
            if [sin(a) > 0] {
                y = 1;
            } else {
                y = 0;
            }
            """,
            allowed_vars=["a", "y"],
        )

        execution = execute_operations_domain(statements, {"a": a, "y": y})

        assert execution.failure is not None
        assert execution.failure.kind == "not_implemented"
        assert execution.failure.translation_failure is not None
        assert execution.branches == ()
        assert execution.steps == ()
        assert_z3_expr_equal(execution.env["y"], y)

    def test_elif_condition_failure_preserves_prior_branch_env(self):
        """A failing elif condition keeps earlier successful branch environments."""
        x = z3.Int("x")
        a = z3.Real("a")
        y = z3.Int("y")
        w = z3.Int("w")
        statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
            } else if [sin(a) > 0] {
                y = 2;
            } else {
                y = 3;
            }
            w = 4;
            """,
            allowed_vars=None,
        )

        execution = execute_operations_domain(
            statements, {"x": x, "a": a, "y": y, "w": w}
        )

        assert execution.failure is not None
        assert execution.failure.kind == "not_implemented"
        assert len(execution.steps) == 1
        assert len(execution.branches) == 1
        assert execution.branches[0].failure is None
        assert_z3_expr_equal(execution.branches[0].result_env["y"], z3.IntVal(1))
        assert_constraints_reject((x > 0,), execution.env["y"] != 1)
        assert_constraints_reject((x <= 0,), execution.env["y"] != y)
        assert_z3_expr_equal(execution.env["w"], w)

    def test_nested_if_definedness_keeps_outer_path_prefix(self):
        """Nested branch body domains are guarded by every active selector."""
        flag, x, y, z = z3.Ints("flag x y z")
        statements = parse_operations(
            """
            if [x > 0] {
                if [flag > 0] {
                    z = 1 / (x - y);
                } else {
                    z = 0;
                }
            } else {
                z = 2;
            }
            """,
            allowed_vars=["flag", "x", "y", "z"],
        )

        execution = execute_operations_domain(
            statements,
            {"flag": flag, "x": x, "y": y, "z": z},
        )
        constraints = [item.constraint for item in execution.definedness_constraints]

        assert execution.failure is None
        assert any(
            str(step.path_conditions) == "(0 < x, 0 < flag)" for step in execution.steps
        )
        assert_constraints_allow(constraints, x <= 0, x == y)
        assert_constraints_allow(constraints, x > 0, flag <= 0, x == y)
        assert_constraints_reject(constraints, x > 0, flag > 0, x == y)

    def test_reachable_branch_body_failure_is_recorded_on_branch(self):
        """A branch body failure is kept on the executed branch record."""
        x = z3.Int("x")
        y = z3.Int("y")
        statements = parse_operations(
            """
            if [x > 0] {
                y = missing;
            } else {
                y = 0;
            }
            """,
            allowed_vars=None,
        )

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y},
            path_conditions=(x > 0,),
        )

        assert execution.failure is not None
        assert execution.failure.kind == "value_error"
        assert len(execution.branches) == 1
        assert execution.branches[0].branch_kind == "if"
        assert execution.branches[0].failure is execution.failure
        assert execution.steps == ()
        assert_z3_expr_equal(execution.env["y"], y)

    def test_branch_body_failure_preserves_partial_branch_env(self):
        """A branch body failure returns the work environment at the failure point."""
        x, y, z, w = z3.Ints("x y z w")
        statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
                z = missing;
            } else {
                y = 2;
            }
            w = 3;
            """,
            allowed_vars=None,
        )

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y, "z": z, "w": w},
            path_conditions=(x > 0,),
        )

        assert execution.failure is not None
        assert execution.failure.kind == "value_error"
        assert len(execution.steps) == 1
        assert len(execution.branches) == 1
        assert execution.branches[0].failure is execution.failure
        assert_z3_expr_equal(execution.branches[0].result_env["y"], z3.IntVal(1))
        assert_constraints_reject((x > 0,), execution.env["y"] != 1)
        assert_z3_expr_equal(execution.env["w"], w)

    def test_unreachable_elif_condition_is_not_translated(self):
        """An unreachable elif condition cannot leak unsupported functions."""
        x = z3.Int("x")
        y = z3.Int("y")
        z = z3.Real("z")
        statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
            } else if [sin(z) > 0] {
                y = 2;
            } else {
                y = 3;
            }
            """,
            allowed_vars=["x", "y", "z"],
        )

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y, "z": z},
            path_conditions=(x > 0,),
        )

        assert execution.failure is None
        assert [branch.status for branch in execution.branches] == [
            "sat",
            "unsat",
            "unsat",
        ]
        assert execution.branches[1].definedness_constraints == ()
        assert execution.branches[1].failure is None
        assert_constraints_allow([], x > 0, execution.env["y"] == 1)

    def test_arrival_unsat_elif_selector_keeps_current_condition_metadata(self):
        """An arrival-unsat elif still records its full effective selector."""
        x, y = z3.Ints("x y")
        statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
            } else if [x <= 0] {
                y = 2;
            } else if [x == 5] {
                y = 3;
            }
            """,
            allowed_vars=["x", "y"],
        )

        execution = execute_operations_domain(statements, {"x": x, "y": y})

        assert execution.failure is None
        assert [branch.status for branch in execution.branches] == [
            "sat",
            "sat",
            "unsat",
        ]
        assert_z3_expr_equivalent(
            execution.branches[2].selector,
            z3.And(z3.Not(x > 0), z3.Not(x <= 0), x == 5),
        )
        assert execution.branches[2].result_env is None

    @pytest.mark.parametrize(
        ["failure_factory", "metadata_expr"],
        [
            (lambda: ValueError("metadata value failure"), None),
            (lambda: TypeError("metadata type failure"), None),
            (lambda: z3.Z3Exception("metadata z3 failure"), None),
            (None, z3.IntVal(1)),
        ],
    )
    def test_arrival_unsat_elif_metadata_failure_falls_back_to_arrival_selector(
        self, monkeypatch, failure_factory, metadata_expr
    ):
        """Metadata-only condition translation failures do not leak from dead elif."""
        from pyfcstm.solver import operation

        x, y = z3.Ints("x y")
        dead_condition = Integer(1)
        statement = IfBlock(
            branches=[
                IfBlockBranch(
                    condition=BinaryOp(Variable("x"), ">", Integer(0)),
                    statements=[Operation(var_name="y", expr=Integer(1))],
                ),
                IfBlockBranch(
                    condition=BinaryOp(Variable("x"), "<=", Integer(0)),
                    statements=[Operation(var_name="y", expr=Integer(2))],
                ),
                IfBlockBranch(
                    condition=dead_condition,
                    statements=[Operation(var_name="y", expr=Integer(3))],
                ),
            ]
        )
        original_expr_to_z3 = operation.expr_to_z3

        def patched_expr_to_z3(expr, env):
            if expr is dead_condition:
                if failure_factory is not None:
                    raise failure_factory()
                return metadata_expr
            return original_expr_to_z3(expr, env)

        monkeypatch.setattr(operation, "expr_to_z3", patched_expr_to_z3)

        execution = execute_operations_domain(statement, {"x": x, "y": y})

        assert execution.failure is None
        assert execution.branches[2].status == "unsat"
        assert_z3_expr_equivalent(
            execution.branches[2].selector,
            z3.And(z3.Not(x > 0), z3.Not(x <= 0)),
        )
        assert execution.branches[2].result_env is None

    def test_unreachable_branch_is_recorded_without_execution_or_failure(self):
        """Pruned branches stay auditable while their statements are not executed."""
        x = z3.Int("x")
        y = z3.Int("y")
        z = z3.Real("z")
        statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
            } else {
                y = sin(z);
            }
            """,
            allowed_vars=["x", "y", "z"],
        )

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y, "z": z},
            path_conditions=(x > 0,),
        )

        assert execution.failure is None
        assert len(execution.branches) == 2
        assert [branch.branch_kind for branch in execution.branches] == ["if", "else"]
        assert [branch.status for branch in execution.branches] == ["sat", "unsat"]
        assert execution.branches[1].result_env is None
        assert execution.branches[1].definedness_constraints == ()
        assert execution.branches[1].failure is None
        assert_constraints_allow(
            [item.constraint for item in execution.definedness_constraints],
            x > 0,
            execution.env["y"] == 1,
        )

    def test_branch_result_env_uses_pre_if_merge_names_only(self):
        """Branch-local temporaries are visible in steps but not branch result env."""
        x, y = z3.Ints("x y")
        statements = parse_operations(
            """
            tmp = x + 1;
            if [x > 0] {
                tmp = tmp + 1;
                inner = tmp + 1;
            } else {
                tmp = tmp + 2;
            }
            y = tmp;
            """,
            allowed_vars=["x", "y"],
        )

        execution = execute_operations_domain(statements, {"x": x, "y": y})

        assert execution.failure is None
        assert set(execution.env.keys()) == {"x", "y"}
        assert "tmp" not in execution.env
        assert set(execution.branches[0].result_env.keys()) == {"x", "y", "tmp"}
        assert "inner" not in execution.branches[0].result_env
        assert any("inner" in step.after for step in execution.steps)
        assert_z3_expr_equal(execution.env["y"], z3.If(x > 0, x + 2, x + 3))

    def test_unknown_branch_feasibility_keeps_selector_in_merge(self, monkeypatch):
        """Unknown branch feasibility does not prune value merging."""
        from pyfcstm.solver import operation
        from pyfcstm.solver.logical import SatResult

        calls = []

        def always_unknown(constraints, *, timeout_ms=None, get_model=False):
            calls.append((tuple(constraints), timeout_ms, get_model))
            return SatResult(kind="unknown")

        monkeypatch.setattr(operation, "is_sat", always_unknown)
        flag = z3.Int("flag")
        y = z3.Int("y")
        statements = parse_operations(
            """
            if [flag > 0] {
                y = 1;
            } else {
                y = 0;
            }
            """,
            allowed_vars=["flag", "y"],
        )

        execution = execute_operations_domain(
            statements,
            {"flag": flag, "y": y},
            timeout_ms=17,
        )

        assert execution.failure is None
        assert calls
        assert all(
            timeout_ms == 17 and not get_model for _, timeout_ms, get_model in calls
        )
        assert {branch.status for branch in execution.branches} == {"unknown"}
        assert_constraints_allow([], flag > 0, execution.env["y"] == 1)
        assert_constraints_allow([], flag <= 0, execution.env["y"] == 0)

    def test_prune_unreachable_false_keeps_contradictory_branches(self):
        """Disabling pruning keeps branches even under contradictory paths."""
        x = z3.Int("x")
        y = z3.Int("y")
        statements = parse_operations(
            """
            if [x > 0] {
                y = 1;
            } else {
                y = 0;
            }
            """,
            allowed_vars=["x", "y"],
        )

        execution = execute_operations_domain(
            statements,
            {"x": x, "y": y},
            path_conditions=(x <= 0,),
            prune_unreachable=False,
        )

        assert execution.failure is None
        assert [branch.status for branch in execution.branches] == ["sat", "sat"]
        assert_constraints_allow([], x <= 0, execution.env["y"] == 0)

    def test_non_bool_condition_is_operation_failure_kind(self):
        """Operation-layer condition type failures use a stable kind."""
        statement = IfBlock(
            branches=[
                IfBlockBranch(
                    condition=Integer(1),
                    statements=[Operation(var_name="y", expr=Integer(1))],
                ),
            ]
        )
        y = z3.Int("y")

        execution = execute_operations_domain(statement, {"y": y})

        assert execution.failure is not None
        assert execution.failure.kind == "non_bool_condition"
        assert execution.failure.translation_failure is None
        assert execution.steps == ()

    def test_elif_non_bool_condition_preserves_prior_branch_env(self):
        """A non-Boolean elif condition keeps earlier successful branch envs."""
        statement = IfBlock(
            branches=[
                IfBlockBranch(
                    condition=BinaryOp(Variable("x"), ">", Integer(0)),
                    statements=[Operation(var_name="y", expr=Integer(1))],
                ),
                IfBlockBranch(
                    condition=Variable("x"),
                    statements=[Operation(var_name="y", expr=Integer(2))],
                ),
                IfBlockBranch(
                    condition=None,
                    statements=[Operation(var_name="y", expr=Integer(3))],
                ),
            ]
        )
        x = z3.Int("x")
        y = z3.Int("y")
        w = z3.Int("w")

        execution = execute_operations_domain(statement, {"x": x, "y": y, "w": w})

        assert execution.failure is not None
        assert execution.failure.kind == "non_bool_condition"
        assert execution.failure.translation_failure is None
        assert len(execution.steps) == 1
        assert len(execution.branches) == 1
        assert execution.branches[0].failure is None
        assert_z3_expr_equal(execution.branches[0].result_env["y"], z3.IntVal(1))
        assert_constraints_reject((x > 0,), execution.env["y"] != 1)
        assert_constraints_reject((x <= 0,), execution.env["y"] != y)
        assert_z3_expr_equal(execution.env["w"], w)

    def test_unsupported_statement_is_operation_failure_kind(self):
        """Unknown operation statements use the stable operation-layer kind."""
        x = z3.Int("x")

        execution = execute_operations_domain(OperationStatement(), {"x": x})

        assert execution.failure is not None
        assert execution.failure.kind == "unsupported_statement"
        assert execution.failure.translation_failure is None
        assert execution.steps == ()
        assert_z3_expr_equal(execution.env["x"], x)

    def test_merge_operation_definedness_delegates_for_operation_objects(self):
        """Operation-level merge accepts executions, steps, and branches."""
        x, y = z3.Ints("x y")
        statements = parse_operations(
            """
            if [x != 0] {
                y = 1 / x;
            } else {
                y = 0;
            }
            """,
            allowed_vars=["x", "y"],
        )
        execution = execute_operations_domain(statements, {"x": x, "y": y})
        manual_constraint = DomainConstraint(z3.BoolVal(True))

        merged = merge_operation_definedness(
            manual_constraint,
            execution,
            execution.steps[:1],
            execution.branches[0],
        )

        assert len(merged) >= len(execution.definedness_constraints)
        assert manual_constraint in merged
        assert all(hasattr(item, "constraint") for item in merged)
        with pytest.raises(TypeError, match="Unsupported operation definedness item"):
            merge_operation_definedness([object()])
        with pytest.raises(TypeError, match="Unsupported operation definedness item"):
            merge_operation_definedness(object())

    def test_old_execute_operations_matches_domain_env(self):
        """The legacy entry point keeps its return shape and value semantics."""
        statements = parse_operations(
            """
            tmp = x + 1;
            if [x > 0] {
                tmp = tmp + 10;
            } else {
                tmp = tmp + 20;
            }
            y = tmp;
            """,
            allowed_vars=["x", "y"],
        )
        var_exprs = {"x": z3.Int("x"), "y": z3.Int("y")}

        legacy = execute_operations(statements, var_exprs)
        execution = execute_operations_domain(statements, var_exprs)

        assert execution.failure is None
        assert set(legacy.keys()) == set(var_exprs.keys())
        assert set(execution.env.keys()) == set(var_exprs.keys())
        for name in var_exprs.keys():
            assert_z3_expr_equivalent(legacy[name], execution.env[name])


@pytest.mark.unittest
class TestIntegration:
    """Integration tests for parse and execute."""

    def test_parse_and_execute(self):
        """Test parsing and executing operations together."""
        code = "x = x + 2; y = y + x;"
        ops = parse_operations(code, allowed_vars=["x", "y"])

        x = z3.Int("x")
        y = z3.Int("y")
        var_exprs = {"x": x, "y": y}

        new_exprs = execute_operations(ops, var_exprs)

        # x should be x + 2, y should be y + (x + 2)
        solver = z3.Solver()
        solver.add(x == 5, y == 10)
        solver.add(new_exprs["x"] == 7)  # 5 + 2
        solver.add(new_exprs["y"] == 17)  # 10 + 7
        assert solver.check() == z3.sat

    def test_parse_and_execute_complex(self):
        """Test parsing and executing complex operations."""
        code = """
        counter = counter + 1;
        result = counter * 10;
        """
        ops = parse_operations(code, allowed_vars=["counter", "result"])

        counter = z3.Int("counter")
        result = z3.Int("result")
        var_exprs = {"counter": counter, "result": result}

        new_exprs = execute_operations(ops, var_exprs)

        # counter should be counter + 1, result should be (counter + 1) * 10
        solver = z3.Solver()
        solver.add(counter == 0)
        solver.add(new_exprs["counter"] == 1)  # 0 + 1
        solver.add(new_exprs["result"] == 10)  # 1 * 10
        assert solver.check() == z3.sat

    def test_parse_and_execute_with_temporary_variable(self):
        """Test parsing and executing operations with a temporary variable."""
        code = """
        temp = x + y;
        y = temp * 2;
        """
        ops = parse_operations(code, allowed_vars=["x", "y"])

        x = z3.Int("x")
        y = z3.Int("y")
        var_exprs = {"x": x, "y": y}

        new_exprs = execute_operations(ops, var_exprs)

        assert set(new_exprs.keys()) == {"x", "y"}
        assert "temp" not in new_exprs

        solver = z3.Solver()
        solver.add(x == 3, y == 4)
        solver.add(new_exprs["x"] == 3)
        solver.add(new_exprs["y"] == 14)
        assert solver.check() == z3.sat

    @pytest.mark.parametrize(
        ["block_code", "initial_values"],
        [
            (
                """
            if [x > 0] {
                tmp = x + 1;
                if [flag > 0] {
                    y = tmp + 10;
                } else {
                    y = tmp + 20;
                }
            } else {
                y = y + 100;
            }
                """,
                {"x": 5, "y": 1, "flag": 1},
            ),
            (
                """
            if [x > 0] {
                tmp = x + 1;
                if [flag > 0] {
                    y = tmp + 10;
                } else {
                    y = tmp + 20;
                }
            } else {
                y = y + 100;
            }
                """,
                {"x": 5, "y": 1, "flag": 0},
            ),
            (
                """
            if [x > 0] {
                tmp = x + 1;
                if [flag > 0] {
                    y = tmp + 10;
                } else {
                    y = tmp + 20;
                }
            } else {
                y = y + 100;
            }
                """,
                {"x": 0, "y": 1, "flag": 0},
            ),
        ],
    )
    def test_solver_and_runtime_match_for_if_blocks(self, block_code, initial_values):
        statements = parse_operations(
            block_code, allowed_vars=list(initial_values.keys())
        )
        var_exprs = {name: z3.Int(name) for name in initial_values.keys()}
        new_exprs = execute_operations(statements, var_exprs)

        runtime = build_runtime_for_block(block_code, initial_values)
        runtime.cycle()

        expected_outputs = {name: runtime.vars[name] for name in initial_values.keys()}

        assert_symbolic_outputs(var_exprs, new_exprs, initial_values, expected_outputs)
