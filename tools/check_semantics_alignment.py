"""
Differential check of the operator catalog's runnable and Z3 semantics.

Two seeded comparisons, both through public APIs:

* Expressions: random expressions are evaluated by the concrete engine and
  translated to Z3.  Where the runtime returns a value, every definedness fact
  holds and the Z3 value equals it; where the runtime raises, a definedness
  fact of the same error kind fails.  A float result that differs only because
  the runtime rounds to IEEE doubles while Z3 computes exact reals is counted as
  ``float_boundary``, the documented boundary, and is not a failure.
* Models: random state machines are checked for reachable runtime errors by
  ``pyfcstm bmc``'s runtime-safety check and by exhaustive simulation over a
  small input domain; every reported error must replay.

Usage::

    python tools/check_semantics_alignment.py --check
    python tools/check_semantics_alignment.py --check --expressions 5000 --models 200
"""

import argparse
import itertools
import math
import random
import sys
from fractions import Fraction

import z3

from pyfcstm.bmc import (
    compile_bmc_query,
    decode_bmc_result_trace,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.expr import (
    BinaryOp,
    ConditionalOp,
    Float,
    Integer,
    UFunc,
    UnaryOp,
    Variable,
)
from pyfcstm.semantics.adapters import expression_from_model
from pyfcstm.semantics.concrete import evaluate
from pyfcstm.semantics.errors import EvaluationError
from pyfcstm.semantics.symbolic import SymbolicFailure, SymbolicSession, translate
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeExpressionError

_INT_POINTS = (-3, 0, 2)
_FLOAT_POINTS = (-1.5, 0.0, 2.25)
_FUNCTIONS = ("abs", "sign", "floor", "ceil", "trunc", "round", "sqrt")


def _numeric(rng, depth):
    if depth == 0 or rng.random() < 0.3:
        return rng.choice(
            [
                Variable("i"),
                Variable("f"),
                Integer(rng.randint(-3, 3)),
                Float(rng.choice([0.5, -2.0, 1.25])),
            ]
        )
    kind = rng.random()
    if kind < 0.55:
        op = rng.choice(["+", "-", "*", "/", "%", "**"])
        right = Integer(rng.randint(-1, 2)) if op == "**" else _numeric(rng, depth - 1)
        return BinaryOp(_numeric(rng, depth - 1), op, right)
    if kind < 0.75:
        return UFunc(rng.choice(_FUNCTIONS), _numeric(rng, depth - 1))
    if kind < 0.85:
        return UnaryOp("-", _numeric(rng, depth - 1))
    condition = BinaryOp(
        _numeric(rng, depth - 1),
        rng.choice(["<", ">=", "==", "!="]),
        _numeric(rng, depth - 1),
    )
    if rng.random() < 0.5:
        condition = BinaryOp(
            condition,
            rng.choice(["&&", "||", "=>", "xor", "iff"]),
            BinaryOp(_numeric(rng, depth - 1), ">", Integer(0)),
        )
    return ConditionalOp(condition, _numeric(rng, depth - 1), _numeric(rng, depth - 1))


def _algebraic_floors(value):
    # Z3 neither simplifies nor decides ToInt of an irrational algebraic
    # number, such as trunc(sqrt(2)); an irrational number is never an
    # integer, so a close rational approximation has the same floor.
    floors, pending = [], [value]
    while pending:
        term = pending.pop()
        if z3.is_to_int(term) and z3.is_algebraic_value(term.arg(0)):
            floors.append(
                (term, z3.IntVal(math.floor(term.arg(0).approx(20).as_fraction())))
            )
        else:
            pending.extend(term.children())
    return floors


def _exact(value):
    """Return a closed Z3 value as a Fraction, or ``None`` when it is irrational."""
    if not (z3.is_int_value(value) or z3.is_rational_value(value)):
        value = z3.simplify(z3.substitute(value, *_algebraic_floors(value)))
    if z3.is_int_value(value):
        return Fraction(value.as_long())
    if z3.is_rational_value(value):
        return Fraction(value.numerator_as_long(), value.denominator_as_long())
    return None


def check_expressions(count, seed):
    """Return ``(compared, float_boundary, unsupported, failures)``."""
    rng = random.Random(seed)
    i, f = z3.Int("i"), z3.Real("f")
    compared = boundary = unsupported = 0
    failures = []
    for _ in range(count):
        expr = _numeric(rng, 3)
        try:
            value, session = translate(
                expression_from_model(expr), {"i": i, "f": f}, SymbolicSession()
            )
        except SymbolicFailure:
            unsupported += 1
            continue
        for iv, fv in itertools.product(_INT_POINTS, _FLOAT_POINTS):
            point = ((i, z3.IntVal(iv)), (f, z3.RealVal(fv)))
            facts = [
                (fact.kind, z3.simplify(z3.substitute(fact.constraint, *point)))
                for fact in session.definedness
            ]
            try:
                expected = evaluate(expr, {"i": iv, "f": fv})
            except EvaluationError as err:
                kinds = {kind for kind, holds in facts if z3.is_false(holds)}
                if err.kind not in kinds and kinds != {"overflow"}:
                    failures.append(
                        (
                            str(expr),
                            iv,
                            fv,
                            "runtime %s, Z3 failing %s" % (err.kind, sorted(kinds)),
                        )
                    )
                compared += 1
                continue
            if any(z3.is_false(holds) for _kind, holds in facts):
                failures.append(
                    (str(expr), iv, fv, "runtime value %r, Z3 undefined" % (expected,))
                )
                continue
            actual = _exact(z3.simplify(z3.substitute(value, *point)))
            if actual is None or actual != Fraction(expected):
                if isinstance(expected, float):
                    boundary += 1
                else:
                    failures.append(
                        (str(expr), iv, fv, "runtime %r, Z3 %s" % (expected, actual))
                    )
                continue
            compared += 1
    return compared, boundary, unsupported, failures


def _model(rng):
    expressions = [
        "10 / d",
        "x / d",
        "x % d",
        "x + d",
        "(d == 0) ? 1 : 10 / d",
        "sqrt(x)",
        "x - 3",
        "d * 2",
    ]
    conditions = [
        "d == 0",
        "d != 0",
        "10 / d > 1",
        "x / d > 0",
        "x > 1",
        "d > 0 && 10 / d > 3",
        "true",
        "false",
    ]

    def action():
        return "x = %s;" % rng.choice(expressions)

    lines = [
        "input int d;",
        "def %s x = %s;" % rng.choice([("int", "0"), ("float", "0.0")]),
        "state Root {",
        "    [*] -> A;",
        "    state A { during { %s } }" % action()
        if rng.random() < 0.4
        else "    state A;",
        "    state B { enter { %s } }" % action()
        if rng.random() < 0.5
        else "    state B;",
        "    state C {",
        "        enter { %s }" % action() if rng.random() < 0.6 else "",
    ]
    for target in rng.sample(["C1", "C2"], rng.randint(1, 2)):
        lines.append("        [*] -> %s : if [%s];" % (target, rng.choice(conditions)))
    lines += ["        state C1; state C2;", "    }"]
    for source, target in rng.sample(
        [("A", "B"), ("A", "C"), ("B", "A"), ("B", "C"), ("C", "A")], 3
    ):
        lines.append(
            "    %s -> %s : if [%s];" % (source, target, rng.choice(conditions))
        )
    lines.append("}")
    return "\n".join(lines)


def _simulated_error(machine, steps):
    for sequence in itertools.product((-1, 0, 2), repeat=steps):
        runtime = SimulationRuntime(machine, input_source={"d": 0})
        for value in sequence:
            try:
                runtime.cycle(inputs={"d": value})
            except SimulationRuntimeExpressionError:
                return True
    return False


def check_models(count, seed, steps=3):
    """Return ``(checked, undecided, failures)``."""
    rng = random.Random(seed)
    checked = undecided = 0
    failures = []
    query = (
        'assume always: d == -1 || d == 0 || d == 2;\ncheck reach <= %d: active("Root.B");'
        % steps
    )
    for index in range(count):
        text = _model(rng)
        machine = load_state_machine_from_text(text)
        result = solve_bmc_property(compile_bmc_query(machine, query), timeout_ms=20000)
        status = result.runtime_safety.status
        if status in ("unknown", "timeout"):
            undecided += 1
            continue
        checked += 1
        violated = status == "violated"
        if violated != _simulated_error(machine, steps):
            failures.append((index, "BMC %s disagrees with simulation" % status, text))
        elif (
            violated
            and not replay_bmc_witness(
                machine, decode_bmc_result_trace(result, source="runtime_error")
            ).ok
        ):
            failures.append((index, "error prefix does not replay", text))
    return checked, undecided, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--check", action="store_true", required=True, help="Run both comparisons."
    )
    parser.add_argument("--expressions", type=int, default=1500)
    parser.add_argument("--models", type=int, default=40)
    parser.add_argument("--seed", type=int, default=522)
    args = parser.parse_args()
    compared, boundary, unsupported, failures = check_expressions(
        args.expressions, args.seed
    )
    print(
        "expressions: %d points agree, %d float_boundary, %d without a Z3 encoding, %d failures"
        % (compared, boundary, unsupported, len(failures))
    )
    for item in failures[:20]:
        print("  %s at i=%r f=%r: %s" % item)
    checked, undecided, model_failures = check_models(args.models, args.seed)
    print(
        "models: %d agree, %d undecided by Z3, %d failures"
        % (checked, undecided, len(model_failures))
    )
    for index, reason, text in model_failures[:5]:
        print("  model %d: %s\n%s" % (index, reason, text))
    return 1 if failures or model_failures else 0


if __name__ == "__main__":
    sys.exit(main())
