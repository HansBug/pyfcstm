"""Solving in a Z3 context of its own, driven with the caller's terms."""

import pytest
import z3

from pyfcstm.solver.context import (
    Deferred,
    IsolatedSolver,
    SolveContextOwner,
    current_owner,
    declare,
    in_solve_context,
    is_linear,
    isolated_owner,
    solver_context_in_use,
)

pytestmark = pytest.mark.unittest

x, y = z3.Ints("x y")


@pytest.mark.parametrize(
    ("terms", "expected"),
    [
        ([x + y > 1], True),
        ([x - 2 * y > 3, x % 3 == 1], True),
        ([x / 2 > 1], True),
        ([x * (y - y + 2) > 3], True),
        ([x * y > 3], False),
        ([x % y == 1], False),
        ([x ** y > 3], False),
        ([z3.AtMost(z3.Bool("a"), z3.Bool("b"), 1)], True),
        ([z3.And(z3.AtLeast(z3.Bool("a"), z3.Bool("b"), 1), x > 0)], True),
        ([z3.AtMost(z3.Bool("a"), z3.Bool("b"), 1), x * y > 3], False),
    ],
)
def test_linearity_follows_what_z3_decides(terms, expected) -> None:
    context = z3.Context()
    moved = [term.translate(context) for term in terms]

    assert is_linear(moved, context) is expected


def test_no_owner_exists_outside_a_wrapped_call() -> None:
    assert current_owner() is None and isolated_owner() is None
    assert solver_context_in_use() == "shared"


def test_a_linear_declaration_isolates_and_a_non_linear_one_does_not() -> None:
    @in_solve_context(lambda *terms: terms)
    def probe(*terms):
        owner = isolated_owner()
        return None if owner is None else owner.context

    assert probe(x + y > 1) is not None
    assert probe(x * y > 1) is None
    assert current_owner() is None


def test_false_means_solve_where_the_formula_was_built() -> None:
    @in_solve_context(lambda *terms: False)
    def probe(*terms):
        return isolated_owner(), list(current_owner().linear)

    owner, linear = probe(x + y > 1)

    assert owner is None and linear == [(False, frozenset())]


def test_a_function_without_a_fragment_declares_nothing() -> None:
    @in_solve_context()
    def probe():
        return list(current_owner().linear)

    assert probe() == []


def test_a_deferred_declaration_runs_unisolated_until_it_is_completed() -> None:
    @in_solve_context(lambda *terms: Deferred(terms))
    def probe(*terms):
        owner = current_owner()
        before = isolated_owner()
        owner.linear[-1] = declare(owner, tuple(owner.deferred))
        return before, isolated_owner() is not None

    assert probe(x + y > 1) == (None, True)
    assert probe(x * y > 1) == (None, False)


def test_a_nested_call_that_does_not_own_adopts_the_declaration() -> None:
    @in_solve_context(lambda *terms: terms, own=False)
    def inner():
        return isolated_owner() is not None

    @in_solve_context(lambda *terms: terms)
    def outer(*terms):
        return inner(), isolated_owner() is not None

    assert outer(x + y > 1) == (True, True)
    assert outer(x * y > 1) == (False, False)


def test_the_context_is_released_when_the_outermost_call_ends() -> None:
    import gc
    import weakref

    holder = []

    @in_solve_context(lambda *terms: terms)
    def probe(*terms):
        holder.append(weakref.ref(isolated_owner().context))

    probe(x + y > 1)
    gc.collect()

    assert holder[0]() is None


def test_a_non_linear_declaration_inside_a_linear_solve_releases_the_context() -> None:
    @in_solve_context(lambda *terms: terms)
    def probe(*terms):
        return current_owner().context

    assert probe(x * y > 1) is None


def test_an_isolated_solver_answers_in_the_callers_context() -> None:
    owner = SolveContextOwner()
    owner.context = z3.Context()
    solver = IsolatedSolver(z3.Solver(ctx=owner.context), owner)
    solver.add(x > 2, x < 5)
    solver.push()
    solver.add(x > 3)

    assert solver.check() == z3.sat
    model = solver.model()
    assert model.ctx == z3.main_ctx() and model.eval(x).as_long() == 4
    solver.pop()
    assert owner.used is True
    solver.set("timeout", 1000)
    assert solver.reason_unknown() is not None
    assert solver.statistics() is not None


def test_an_isolated_solver_returns_unsat_cores_in_the_callers_context() -> None:
    owner = SolveContextOwner()
    owner.context = z3.Context()
    solver = IsolatedSolver(z3.Solver(ctx=owner.context), owner)
    first, second = z3.Bools("first second")
    solver.add(z3.Implies(first, x > 1), z3.Implies(second, x < 0))

    assert solver.check(first, second) == z3.unsat
    core = solver.unsat_core()
    assert {item.ctx for item in core} == {z3.main_ctx()}
    assert {str(item) for item in core} == {"first", "second"}
