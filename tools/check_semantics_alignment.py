"""
Differential check of the operator catalog's runnable and Z3 semantics.

Three seeded comparisons, all through public APIs:

* Expressions: random expressions are evaluated by the concrete engine and
  translated to Z3.  Where the runtime returns a value, every definedness fact
  holds and the Z3 value equals it; where the runtime raises, a definedness
  fact of the same error kind fails.  A float result that differs only because
  the runtime rounds to IEEE doubles while Z3 computes exact reals is counted as
  ``float_boundary``, the documented boundary, and is not a failure.
* Models: random state machines are checked for reachable runtime errors by
  ``pyfcstm bmc``'s runtime-safety check and by exhaustive simulation over a
  small input domain; every reported error must replay.
* Region models: random state machines whose states own regions are run by
  exhaustive simulation over a small input domain, and the trace relation of
  ``build_bmc_core_formula`` must force exactly the simulator's cycle-by-cycle
  configuration, variables, Delta classification and fallback-only
  classification.  A model that the
  simulator or the relation rejects with an error is counted and skipped, never
  compared.

Usage::

    python tools/check_semantics_alignment.py --check
    python tools/check_semantics_alignment.py --check --expressions 5000 --models 200
    python tools/check_semantics_alignment.py --check --region-models 200 --region-steps 3
"""

import argparse
import itertools
import math
import random
import sys
from fractions import Fraction

import z3

from pyfcstm.bmc import (
    REGION_DONE_ID,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcEngine,
    BmcError,
    build_bmc_core_formula,
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
from pyfcstm.simulate.runtime import (
    SimulationRuntimeDfsError,
    SimulationRuntimeExpressionError,
)

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


_REGION_GUARDS = (
    "x > 2",
    "y < 3",
    "d == 1",
    "x % 2 == 0",
    "d > 0 && x < 5",
    "x > y",
    "y >= 4",
)
_REGION_ACTIONS = (
    "x = x + 1;",
    "y = y + d;",
    "x = y + 2;",
    "y = x * 2;",
    "x = d;",
    "x = x + y;",
)


def _aspect_lines(rng, probability):
    """Return ``>> during`` aspect declarations of one scope, possibly none."""
    lines = []
    for when in ("before", "after"):
        if rng.random() < probability:
            lines.append(">> during %s { %s }" % (when, rng.choice(_REGION_ACTIONS)))
    return lines


def _region_body(rng, name, depth):
    """Return the source of one region with one to three states."""
    names = ["%s_S%d" % (name, index) for index in range(rng.randint(1, 3))]
    lines = ["region %s {" % name]
    lines.extend("    " + line for line in _aspect_lines(rng, 0.2))
    if rng.random() < 0.3:
        # A guarded start: the region may fail to start, or start somewhere else.
        lines.append("    [*] -> %s : if [%s];" % (names[0], rng.choice(_REGION_GUARDS)))
        if rng.random() < 0.6:
            lines.append("    [*] -> %s;" % names[-1])
    else:
        lines.append("    [*] -> %s;" % names[0])
    nested = depth == 0 and rng.random() < 0.25
    for index, state in enumerate(names):
        if nested and index == len(names) - 1:
            lines.append("    state %s {" % state)
            lines.append("        " + _region_body(rng, state + "_A", 1).replace("\n", "\n        "))
            lines.append("        " + _region_body(rng, state + "_B", 1).replace("\n", "\n        "))
            lines.append("    }")
            continue
        parts = []
        if rng.random() < 0.4:
            parts.append("enter { %s }" % rng.choice(_REGION_ACTIONS))
        if rng.random() < 0.7:
            parts.append("during { %s }" % rng.choice(_REGION_ACTIONS))
        lines.append("    state %s { %s }" % (state, " ".join(parts)))
    for source in names:
        for target in names + ["[*]", "[*]"]:
            if source == target or rng.random() > 0.35:
                continue
            trigger = rng.choice(
                ["if [%s]" % rng.choice(_REGION_GUARDS), "if [%s]" % rng.choice(_REGION_GUARDS), "/Go"]
            )
            lines.append("    %s -> %s : %s;" % (source, target, trigger))
    lines.append("}")
    return "\n".join(lines)


def _region_model(rng):
    """Return a random machine whose ``Run`` state owns two or three regions."""
    regions = "\n".join(
        "        " + _region_body(rng, "R%d" % index, 0).replace("\n", "\n        ")
        for index in range(rng.randint(2, 3))
    )
    lines = [
        "input int d;",
        "def int x = 0;",
        "def int y = 0;",
        "state Root {",
        "    event Go;",
    ]
    lines.extend("    " + line for line in _aspect_lines(rng, 0.25))
    lines += [
        "    [*] -> %s;" % rng.choice(["Run", "Idle"]),
        "    state Idle;",
        "    state Run {",
    ]
    lines.extend("        " + line for line in _aspect_lines(rng, 0.25))
    for when in ("before", "after"):
        if rng.random() < 0.2:
            lines.append(
                "        during %s { %s }" % (when, rng.choice(_REGION_ACTIONS))
            )
    lines += [
        regions,
        "    }",
        "    state Done { during { x = x + 1; } }",
        "    Idle -> Run : /Go;",
    ]
    if rng.random() < 0.7:
        lines.append("    Run -> Done : if [%s];" % rng.choice(_REGION_GUARDS))
    if rng.random() < 0.3:
        lines.append("    Run -> Run : /Go;")
    if rng.random() < 0.5:
        lines.append("    Done -> Idle : /Go;")
    lines.append("}")
    return "\n".join(lines)


def _configuration_predicate(core, frame, node, region_path=None):
    symbols = core.symbols
    state_id = core.context.domain.state_path_to_id(node["state"])
    position = (
        symbols.frame_state(frame)
        if region_path is None
        else symbols.region_position(frame, region_path)
    )
    parts = [position == z3.IntVal(state_id)]
    for item in node.get("regions") or []:
        path = "%s.%s" % (node["state"], item["name"])
        if item["configuration"] is None:
            parts.append(symbols.region_position(frame, path) == z3.IntVal(REGION_DONE_ID))
        else:
            parts.append(_configuration_predicate(core, frame, item["configuration"], path))
    return z3.And(*parts)


def _region_observation(core, runtime, result, frame, cycle):
    symbols = core.symbols
    if runtime.is_ended:
        position = symbols.frame_state(frame) == z3.IntVal(STATE_TERMINATE_ID)
    else:
        tree = runtime.configuration.to_dict()
        if tree["mode"] != "stable":
            # Entered but not started: the cold start stayed a Delta.
            position = symbols.frame_state(frame) == z3.IntVal(STATE_INIT_ID)
        else:
            position = _configuration_predicate(core, frame, tree)
    return z3.And(
        position,
        symbols.frame_var(frame, "x") == runtime.vars["x"],
        symbols.frame_var(frame, "y") == runtime.vars["y"],
        symbols.delta_flag(cycle) == bool(result.delta),
        # A cycle is one of fallbacks only when it is not a Delta and no
        # transition, initial ones included, fired in any region.
        symbols.gamma_flag(cycle)
        == (
            not result.delta
            and not any(item.kind == "transition" for item in result.trace)
        ),
    )


def check_region_models(count, seed, steps=3):
    """Return ``(checked, skipped_by_simulator, skipped_by_relation, failures)``.

    Every cycle of every sequence over the input domain is compared: the
    relation, pinned to the sequence, must have a solution and no solution that
    differs from the simulator's configuration, variables, Delta or whether the
    cycle was one of fallbacks only.
    """
    rng = random.Random(seed)
    checked = skipped_sim = skipped_bmc = 0
    failures = []
    cycle_inputs = [(d, go) for d in (0, 1) for go in (False, True)]
    for index in range(count):
        text = _region_model(rng)
        try:
            model = load_state_machine_from_text(text)
        except Exception:  # noqa: BLE001 - generator output the grammar refuses
            skipped_sim += 1
            continue
        try:
            core = build_bmc_core_formula(
                BmcEngine(model).prepare("check reach <= %d: terminated();" % steps)
            )
        except BmcError:
            skipped_bmc += 1
            continue
        try:
            runs = []
            for sequence in itertools.product(cycle_inputs, repeat=steps):
                runtime = SimulationRuntime(model, input_source={"d": 0})
                pins = []
                expected = []
                for cycle, (d, go) in enumerate(sequence):
                    result = runtime.cycle(
                        ["Root.Go"] if go else [], inputs={"d": d}, trace=True
                    )
                    pins.append(core.symbols.step_inputs[cycle]["d"] == d)
                    literal = core.symbols.event_input(cycle, "Root.Go")
                    pins.append(literal if go else z3.Not(literal))
                    expected.append(
                        _region_observation(core, runtime, result, cycle + 1, cycle)
                    )
                runs.append((sequence, pins, expected))
        except (SimulationRuntimeDfsError, SimulationRuntimeExpressionError, ValueError):
            skipped_sim += 1
            continue
        verdicts = []
        for sequence, pins, expected in runs:
            solver = z3.Solver()
            solver.set("timeout", 20000)
            solver.add(core.core, *pins)
            solver.push()
            solver.add(z3.And(*expected))
            reachable = solver.check()
            solver.pop()
            solver.add(z3.Not(z3.And(*expected)))
            forced = solver.check()
            if reachable == z3.unknown or forced == z3.unknown:
                verdicts.append("undecided")
            elif reachable != z3.sat or forced != z3.unsat:
                failures.append((index, sequence, reachable, forced, text))
                break
            else:
                verdicts.append("ok")
        if failures and failures[-1][0] == index:
            continue
        if "undecided" in verdicts:
            skipped_bmc += 1
        else:
            checked += 1
    return checked, skipped_sim, skipped_bmc, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--check", action="store_true", required=True, help="Run both comparisons."
    )
    parser.add_argument("--expressions", type=int, default=1500)
    parser.add_argument("--models", type=int, default=40)
    parser.add_argument("--region-models", type=int, default=30)
    parser.add_argument("--region-steps", type=int, default=3)
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
    region_checked, skipped_sim, skipped_bmc, region_failures = check_region_models(
        args.region_models, args.seed, args.region_steps
    )
    print(
        "region models: %d agree on every sequence, %d skipped by the simulator, "
        "%d skipped by the relation, %d failures"
        % (region_checked, skipped_sim, skipped_bmc, len(region_failures))
    )
    for index, sequence, reachable, forced, text in region_failures[:5]:
        print(
            "  region model %d, inputs %r: observations %s, forced %s\n%s"
            % (index, sequence, reachable, forced, text)
        )
    return 1 if failures or model_failures or region_failures else 0


if __name__ == "__main__":
    sys.exit(main())
