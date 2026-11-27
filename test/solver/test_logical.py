"""Tests for small Z3 logical helper predicates."""

from dataclasses import FrozenInstanceError
from typing import List, cast

import pytest
import z3

from pyfcstm.solver import logical
from pyfcstm.solver.logical import (
    SatResult,
    answer_memo,
    is_overlap,
    is_sat,
    is_valid,
)


def exprs(*items) -> List[z3.ExprRef]:
    """Cast Z3 boolean expressions through the broad upstream stubs."""
    return [cast(z3.ExprRef, item) for item in items]


def expr(item) -> z3.ExprRef:
    """Cast one Z3 expression through the broad upstream stubs."""
    return cast(z3.ExprRef, item)


@pytest.mark.unittest
class TestSatResult:
    """Test the public result object returned by logical helpers."""

    def test_sat_result_is_frozen(self):
        """The result object is immutable after construction."""
        result = SatResult(kind="sat")

        with pytest.raises(FrozenInstanceError):
            setattr(result, "kind", "unsat")


@pytest.mark.unittest
class TestIsSat:
    """Test satisfiability checks."""

    def test_sat_constraints(self):
        """Satisfiable constraints return ``sat``."""
        x = z3.Int("x")

        result = is_sat(exprs(x > 1, x < 3), timeout_ms=1000)

        assert result.kind == "sat"
        assert result.model is None

    def test_unsat_constraints(self):
        """Contradictory constraints return ``unsat``."""
        x = z3.Int("x")

        result = is_sat(exprs(x > 1, x < 1), timeout_ms=1000)

        assert result.kind == "unsat"
        assert result.model is None

    def test_unknown_constraints_are_not_reported_as_timeout(self, monkeypatch):
        """Non-timeout unknown results stay distinguishable from timeouts."""

        class UnknownSolver:
            configured_timeout = None

            def __init__(self, ctx=None):
                self.ctx = ctx

            def set(self, *args, **kwargs):
                self.configured_timeout = (args, kwargs)

            def add(self, *constraints):
                pass

            def check(self):
                return z3.unknown

            def reason_unknown(self):
                return "incomplete"

        monkeypatch.setattr(logical.z3, "Solver", UnknownSolver)

        result = is_sat(exprs(z3.BoolVal(True)), timeout_ms=1000)

        assert result.kind == "unknown"
        assert result.model is None

    def test_default_timeout_does_not_configure_z3_timeout(self, monkeypatch):
        """The default timeout policy leaves Z3's timeout parameter unset."""
        calls = []

        class NoTimeoutSolver:
            def __init__(self, ctx=None):
                self.ctx = ctx

            def set(self, *args, **kwargs):
                calls.append((args, kwargs))

            def add(self, *constraints):
                pass

            def check(self):
                return z3.sat

            def model(self):
                return None

        monkeypatch.setattr(logical.z3, "Solver", NoTimeoutSolver)

        result = is_sat(exprs(z3.BoolVal(True)))

        assert result.kind == "sat"
        assert calls == []

    def test_none_timeout_does_not_configure_z3_timeout(self, monkeypatch):
        """Passing ``None`` explicitly is the same no-timeout policy."""
        calls = []

        class NoTimeoutSolver:
            def __init__(self, ctx=None):
                self.ctx = ctx

            def set(self, *args, **kwargs):
                calls.append((args, kwargs))

            def add(self, *constraints):
                pass

            def check(self):
                return z3.unsat

        monkeypatch.setattr(logical.z3, "Solver", NoTimeoutSolver)

        result = is_sat(exprs(z3.BoolVal(False)), timeout_ms=None)

        assert result.kind == "unsat"
        assert calls == []

    def test_non_none_timeout_is_delegated_to_z3(self, monkeypatch):
        """Any non-``None`` timeout value is passed to Z3 unchanged."""
        calls = []

        class TimeoutCaptureSolver:
            def __init__(self, ctx=None):
                self.ctx = ctx

            def set(self, *args, **kwargs):
                calls.append((args, kwargs))

            def add(self, *constraints):
                pass

            def check(self):
                return z3.sat

            def model(self):
                return None

        monkeypatch.setattr(logical.z3, "Solver", TimeoutCaptureSolver)

        result = is_sat(exprs(z3.BoolVal(True)), timeout_ms=123)

        assert result.kind == "sat"
        assert calls == [(("timeout", 123), {})]

    def test_timeout_constraints(self, monkeypatch):
        """Timeout-limited checks return ``timeout`` instead of raising."""

        class TimeoutSolver:
            def __init__(self, ctx=None):
                self.ctx = ctx

            def set(self, *args, **kwargs):
                pass

            def add(self, *constraints):
                pass

            def check(self):
                return z3.unknown

            def reason_unknown(self):
                return "timeout"

        monkeypatch.setattr(logical.z3, "Solver", TimeoutSolver)

        result = is_sat(exprs(z3.BoolVal(True)), timeout_ms=1)

        assert result.kind == "timeout"
        assert result.model is None

    def test_iterable_constraints_are_accepted(self):
        """Constraint inputs may be any finite iterable accepted by Python unpacking."""
        value = z3.Int("iterable_value")

        result = is_sat((expr(item) for item in (value >= 1, value <= 1)))

        assert result.kind == "sat"

    def test_zero_timeout_is_delegated_to_z3(self):
        """The helper does not impose a finite budget on explicit values."""
        result = is_sat(exprs(z3.BoolVal(True)), timeout_ms=0)

        assert result.kind == "sat"

    def test_negative_timeout_is_delegated_to_z3(self):
        """Z3-supported timeout values are policy decisions for callers."""
        result = is_sat(exprs(z3.BoolVal(True)), timeout_ms=-1)

        assert result.kind == "sat"

    def test_invalid_timeout_value_is_reported_by_z3(self):
        """Timeout values outside Z3's accepted parameter domain are not swallowed."""
        with pytest.raises(z3.Z3Exception):
            getattr(logical, "is_sat")(exprs(z3.BoolVal(True)), timeout_ms="invalid")

    def test_real_z3_timeout_constraints(self):
        """A real nonlinear arithmetic query can still be classified as timeout."""
        x, y, z = z3.Ints("x y z")

        result = is_sat(
            exprs(
                x > 0,
                y > 0,
                z > 0,
                x < 1000,
                y < 1000,
                z < 1000,
                x**3 + y**3 == z**3,
            ),
            timeout_ms=1,
        )

        assert result.kind == "timeout"

    def test_get_model_returns_model_only_for_sat(self):
        """Model retrieval is opt-in and only populated for sat checks."""
        value = z3.Int("value")

        sat_result = is_sat(exprs(value == 7), timeout_ms=1000, get_model=True)
        unsat_result = is_sat(
            exprs(value == 7, value == 8), timeout_ms=1000, get_model=True
        )

        assert sat_result.kind == "sat"
        assert isinstance(sat_result.model, z3.ModelRef)
        assert str(sat_result.model.eval(value)) == "7"
        assert unsat_result.kind == "unsat"
        assert unsat_result.model is None


@pytest.mark.unittest
class TestIsValid:
    """Test validity checks."""

    def test_true_literal_is_valid(self):
        """``true`` is valid."""
        assert is_valid(expr(z3.BoolVal(True))).kind == "sat"

    def test_false_literal_is_not_valid(self):
        """``false`` is not valid."""
        assert is_valid(expr(z3.BoolVal(False)), timeout_ms=1000).kind == "unsat"

    def test_variable_tautology_is_valid(self):
        """A tautology over variables is valid."""
        value = z3.Int("value")

        result = is_valid(expr(value == value), timeout_ms=1000)

        assert result.kind == "sat"

    def test_unknown_or_timeout_propagates(self, monkeypatch):
        """The validity helper preserves non-Boolean solver outcomes."""

        def timeout_result(constraints, *, timeout_ms, get_model=False):
            return SatResult(kind="timeout")

        monkeypatch.setattr(logical, "is_sat", timeout_result)

        assert is_valid(expr(z3.BoolVal(True)), timeout_ms=1).kind == "timeout"

    def test_default_timeout_is_forwarded_as_none(self, monkeypatch):
        """The validity helper keeps the default no-timeout policy."""
        timeouts = []

        def valid_result(constraints, *, timeout_ms=None, get_model=False):
            timeouts.append(timeout_ms)
            return SatResult(kind="unsat")

        monkeypatch.setattr(logical, "is_sat", valid_result)

        assert is_valid(expr(z3.BoolVal(True))).kind == "sat"
        assert timeouts == [None]


@pytest.mark.unittest
class TestIsOverlap:
    """Test overlap checks between formulas."""

    def test_overlapping_formulas(self):
        """Overlapping predicates return ``sat``."""
        value = z3.Int("value")

        result = is_overlap(expr(value > 0), expr(value < 10))

        assert result.kind == "sat"

    def test_disjoint_formulas(self):
        """Mutually exclusive predicates return ``unsat``."""
        value = z3.Int("value")

        result = is_overlap(expr(value > 0), expr(value < 0), timeout_ms=1000)

        assert result.kind == "unsat"

    def test_timeout_formulas(self, monkeypatch):
        """Timeouts are preserved for overlap checks."""

        timeouts = []

        def timeout_result(constraints, *, timeout_ms, get_model=False):
            timeouts.append(timeout_ms)
            return SatResult(kind="timeout")

        monkeypatch.setattr(logical, "is_sat", timeout_result)

        result = is_overlap(
            expr(z3.BoolVal(True)), expr(z3.BoolVal(True)), timeout_ms=1
        )

        assert result.kind == "timeout"
        assert timeouts == [1]

    def test_default_timeout_is_forwarded_as_none(self, monkeypatch):
        """The overlap helper keeps the default no-timeout policy."""
        timeouts = []

        def overlap_result(constraints, *, timeout_ms=None, get_model=False):
            timeouts.append(timeout_ms)
            return SatResult(kind="sat")

        monkeypatch.setattr(logical, "is_sat", overlap_result)

        result = is_overlap(expr(z3.BoolVal(True)), expr(z3.BoolVal(True)))

        assert result.kind == "sat"
        assert timeouts == [None]


@pytest.mark.unittest
class TestAnswerMemo:
    """``answer_memo`` shares definite answers only while its block is open."""

    def test_the_same_query_is_solved_once_inside_the_block(self) -> None:
        x = z3.Int("x")
        with answer_memo():
            first = is_sat([x > 1, x < 3])
            second = is_sat([x > 1, x < 3])

        assert first.kind == "sat"
        assert second is first

    def test_nothing_is_shared_outside_the_block(self) -> None:
        x = z3.Int("x")
        with answer_memo():
            first = is_sat([x > 1, x < 3])

        assert is_sat([x > 1, x < 3]) is not first
        assert is_sat([x > 1, x < 3]).kind == "sat"

    def test_unsat_is_remembered_and_queries_are_told_apart(self) -> None:
        x = z3.Int("x")
        with answer_memo():
            low = is_sat([x > 1, x < 1])
            high = is_sat([x > 1, x < 3])
            again = is_sat([x > 1, x < 1])

        assert (low.kind, high.kind) == ("unsat", "sat")
        assert again is low

    def test_a_timeout_or_a_model_request_is_never_remembered(self) -> None:
        x = z3.Int("x")
        with answer_memo():
            with_model = is_sat([x > 1], get_model=True)
            bounded = is_sat([x > 1], timeout_ms=1000)
            plain = is_sat([x > 1])

        assert with_model.model is not None
        assert bounded is not plain
        assert is_sat([x > 1]) is not None

    def test_an_undecided_answer_is_not_remembered(self) -> None:
        x, y = z3.Ints("x y")
        hard = [x * x * x + y * y * y == 33, x > 100, y < -100]
        with answer_memo():
            first = is_sat(hard, timeout_ms=1)
            assert first.kind in ("sat", "unsat", "unknown", "timeout")
            assert is_sat(hard, timeout_ms=1) is not first

    def test_constraints_of_mixed_contexts_are_solved_each_time(self) -> None:
        other = z3.Context()
        with answer_memo():
            first = is_sat([z3.Bool("a"), z3.Bool("b", other)])
            second = is_sat([z3.Bool("a"), z3.Bool("b", other)])

        assert first is not second

    def test_blocks_nest_and_the_inner_one_joins_the_outer(self) -> None:
        x = z3.Int("x")
        with answer_memo():
            with answer_memo():
                first = is_sat([x > 1])
            assert is_sat([x > 1]) is first

        assert is_sat([x > 1]) is not first

    def test_the_table_is_emptied_when_it_is_full(self) -> None:
        x = z3.Int("x")
        with answer_memo(limit=3):
            first = is_sat([x > 0])
            for value in range(1, 4):
                is_sat([x > value])
            assert is_sat([x > 0]) is not first
            latest = is_sat([x > 9])
            assert is_sat([x > 9]) is latest

    def test_an_exception_still_closes_the_block(self) -> None:
        x = z3.Int("x")
        with pytest.raises(RuntimeError):
            with answer_memo():
                first = is_sat([x > 1])
                raise RuntimeError("stop")

        assert is_sat([x > 1]) is not first

    def test_an_empty_query_is_satisfiable_without_a_solver(self) -> None:
        assert is_sat([]).kind == "sat"
        assert is_sat([]).model is None
        assert is_sat([], get_model=True).model is not None
