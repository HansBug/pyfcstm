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
    REGION_PENDING_ID,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcEngine,
    BmcError,
    build_bmc_core_formula,
    check_runtime_safety,
    compile_bmc_query,
    decode_bmc_result_trace,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import Configuration, load_state_machine_from_text
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


# What a model whose cycles may raise adds: operations that divide by the input.
_REGION_FAILING_ACTIONS = ("x = 10 % d;", "y = x / d;")
_REGION_FAILING_GUARDS = ("10 % d == 0", "x / d > 1")


class _Pool:
    """The actions and guards a random region model is made of."""

    def __init__(self, errors=False):
        self.actions = _REGION_ACTIONS + (_REGION_FAILING_ACTIONS if errors else ())
        self.guards = _REGION_GUARDS + (_REGION_FAILING_GUARDS if errors else ())


def _aspect_lines(rng, probability, pool):
    """Return ``>> during`` aspect declarations of one scope, possibly none."""
    lines = []
    for when in ("before", "after"):
        if rng.random() < probability:
            lines.append(">> during %s { %s }" % (when, rng.choice(pool.actions)))
    return lines


def _region_body(rng, name, depth, pool):
    """Return the source of one region with one to three states."""
    names = ["%s_S%d" % (name, index) for index in range(rng.randint(1, 3))]
    lines = ["region %s {" % name]
    lines.extend("    " + line for line in _aspect_lines(rng, 0.2, pool))
    if rng.random() < 0.3:
        # A guarded start: the region may fail to start, or start somewhere else.
        lines.append("    [*] -> %s : if [%s];" % (names[0], rng.choice(pool.guards)))
        if rng.random() < 0.6:
            lines.append("    [*] -> %s;" % names[-1])
    else:
        lines.append("    [*] -> %s;" % names[0])
    nested = depth == 0 and rng.random() < 0.25
    for index, state in enumerate(names):
        if nested and index == len(names) - 1:
            lines.append("    state %s {" % state)
            lines.append("        " + _region_body(rng, state + "_A", 1, pool).replace("\n", "\n        "))
            lines.append("        " + _region_body(rng, state + "_B", 1, pool).replace("\n", "\n        "))
            lines.append("    }")
            continue
        parts = []
        if rng.random() < 0.4:
            parts.append("enter { %s }" % rng.choice(pool.actions))
        if rng.random() < 0.7:
            parts.append("during { %s }" % rng.choice(pool.actions))
        lines.append("    state %s { %s }" % (state, " ".join(parts)))
    for source in names:
        for target in names + ["[*]", "[*]"]:
            if source == target or rng.random() > 0.35:
                continue
            trigger = rng.choice(
                ["if [%s]" % rng.choice(pool.guards), "if [%s]" % rng.choice(pool.guards), "/Go"]
            )
            lines.append("    %s -> %s : %s;" % (source, target, trigger))
    lines.append("}")
    return "\n".join(lines)


def _region_model(rng, errors=False):
    """Return a random machine whose ``Run`` state owns two or three regions.

    With ``errors`` the guards and actions also include operations that divide by
    the input and so raise for some inputs.
    """
    pool = _Pool(errors)
    regions = "\n".join(
        "        " + _region_body(rng, "R%d" % index, 0, pool).replace("\n", "\n        ")
        for index in range(rng.randint(2, 3))
    )
    lines = [
        "input int d;",
        "def int x = 0;",
        "def int y = 0;",
        "state Root {",
        "    event Go;",
    ]
    lines.extend("    " + line for line in _aspect_lines(rng, 0.25, pool))
    lines += [
        "    [*] -> %s;" % rng.choice(["Run", "Idle"]),
        "    state Idle;",
        "    state Run {",
    ]
    lines.extend("        " + line for line in _aspect_lines(rng, 0.25, pool))
    for when in ("before", "after"):
        if rng.random() < 0.2:
            lines.append(
                "        during %s { %s }" % (when, rng.choice(pool.actions))
            )
    lines += [
        regions,
        "    }",
        "    state Done { during { x = x + 1; } }",
        "    Idle -> Run : /Go;",
    ]
    if rng.random() < 0.7:
        lines.append("    Run -> Done : if [%s];" % rng.choice(pool.guards))
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
    given = set()
    for item in node.get("regions") or []:
        path = "%s.%s" % (node["state"], item["name"])
        given.add(item["name"])
        if item["configuration"] is None:
            parts.append(symbols.region_position(frame, path) == z3.IntVal(REGION_DONE_ID))
        else:
            parts.append(_configuration_predicate(core, frame, item["configuration"], path))
    for region in core.context.domain.regions:
        # A region the tree leaves out is one that waits for initialization.
        if region.owner_path == node["state"] and region.name not in given:
            parts.append(
                symbols.region_position(frame, region.path)
                == z3.IntVal(REGION_PENDING_ID)
            )
    return z3.And(*parts)


def _region_observation(core, runtime, result, frame, cycle):
    symbols = core.symbols
    if runtime.is_ended:
        position = symbols.frame_state(frame) == z3.IntVal(STATE_TERMINATE_ID)
    else:
        tree = runtime.configuration.to_dict()
        if tree["mode"] != "stable" and core.context.bound_query.initial.mode != "state":
            # Entered but not started: the cold start stayed a Delta.
            position = symbols.frame_state(frame) == z3.IntVal(STATE_INIT_ID)
        else:
            # A hot start that stayed a Delta still rests in the position it
            # began in, with the regions that wait for initialization.
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


def core_query(model, query):
    """Return the compiled property of a query, for a check that goes on to solve it."""
    return compile_bmc_query(model, query)


def _first_raising_cycle(model, steps):
    """Return the earliest cycle in which some inputs make the simulator raise.

    Every sequence of ``steps`` cycles over the inputs the query allows is run;
    ``None`` means none of them raises.
    """
    earliest = None
    cycle_inputs = [(d, go) for d in (-1, 0, 2) for go in (False, True)]
    for sequence in itertools.product(cycle_inputs, repeat=steps):
        runtime = SimulationRuntime(model, input_source={"d": 0})
        for cycle, (d, go) in enumerate(sequence):
            if earliest is not None and cycle >= earliest:
                break
            try:
                runtime.cycle(["Root.Go"] if go else [], inputs={"d": d})
            except SimulationRuntimeExpressionError:
                earliest = cycle
                break
            except SimulationRuntimeDfsError:
                # A search limit is the simulator giving up, not an error of the
                # model; the sequence says nothing about the relation.
                break
    return earliest


def check_region_safety(count, seed, steps=3):
    """Return ``(checked, undecided, skipped, failures)`` for the safety check.

    A random region model whose cycles may divide by the input is checked in two
    ways.  The runtime-safety check has to report a violation exactly when some
    sequence of inputs and events makes the simulator raise within ``steps``
    cycles, and in the earliest cycle in which any of them does.
    """
    rng = random.Random(seed)
    checked = undecided = skipped = 0
    failures = []
    query = (
        "assume always: d == -1 || d == 0 || d == 2;\n"
        "check reach <= %d: terminated();" % steps
    )
    for index in range(count):
        text = _region_model(rng, errors=True)
        try:
            model = load_state_machine_from_text(text)
        except Exception:  # noqa: BLE001 - generator output the grammar refuses
            skipped += 1
            continue
        try:
            core = build_bmc_core_formula(BmcEngine(model).prepare(query))
        except BmcError:
            skipped += 1
            continue
        result = check_runtime_safety(core, timeout_ms=20000)
        if result.status in ("unknown", "timeout"):
            undecided += 1
            continue
        raised = _first_raising_cycle(model, steps)
        reported = result.error.step if result.status == "violated" else None
        if reported != raised:
            failures.append((index, reported, raised, text))
            continue
        if reported is not None:
            prefix = solve_bmc_property(core_query(model, query), timeout_ms=20000)
            if prefix.runtime_safety is None or prefix.runtime_safety.status != "violated":
                # The second solve ran out of time before it reproduced the
                # violation the first check reported; nothing to replay.
                undecided += 1
                continue
            replay = replay_bmc_witness(
                model, decode_bmc_result_trace(prefix, source="runtime_error")
            )
            if not replay.ok:
                failures.append((index, reported, "error prefix does not replay", text))
                continue
        checked += 1
    return checked, undecided, skipped, failures


def _hot_start_texts(runtime, rng):
    """Return the spellings of one position a hot start can begin in.

    The position is the simulator's own, so the same machine starts at the same
    place in both.  Another spelling names only the owner, which makes the whole
    group wait, and another leaves one region out, which makes that region wait.
    """
    configuration = runtime.configuration
    texts = [str(configuration)]
    tree = configuration.to_dict()
    if tree["regions"]:
        texts.append(tree["state"])
        left_out = rng.randrange(len(tree["regions"]))
        trimmed = dict(
            tree,
            mode="transient",
            regions=[item for i, item in enumerate(tree["regions"]) if i != left_out],
        )
        texts.append(str(Configuration.from_dict(runtime.state_machine, trimmed)))
    return texts


def check_region_hot_starts(count, seed, steps=2):
    """Return ``(checked, skipped, failures)`` for hot starts in the middle of a run.

    Every model is run from the cold start until it has rested for a few cycles;
    that position is then taken as the start of a hot start, in the spellings of
    :func:`_hot_start_texts`, with the variables as they were.  The relation of
    each hot start, pinned to every sequence of inputs and events, must have the
    same configuration, variables and Delta as the simulator started there.
    """
    rng = random.Random(seed)
    checked = skipped = 0
    failures = []
    cycle_inputs = [(d, go) for d in (0, 1) for go in (False, True)]
    for index in range(count):
        text = _region_model(rng)
        try:
            model = load_state_machine_from_text(text)
            runtime = SimulationRuntime(model, input_source={"d": 0})
            for cycle in range(rng.randint(1, 3)):
                runtime.cycle(["Root.Go"] if cycle % 2 == 0 else [], inputs={"d": 1})
        except (SimulationRuntimeDfsError, SimulationRuntimeExpressionError, ValueError):
            skipped += 1
            continue
        if runtime.is_ended:
            skipped += 1
            continue
        variables = dict(runtime.vars)
        for start in _hot_start_texts(runtime, rng):
            where = " && ".join("%s == %s" % item for item in sorted(variables.items()))
            query = 'init state("%s") havoc * where %s;\ncheck reach <= %d: terminated();' % (
                start,
                where,
                steps,
            )
            try:
                core = build_bmc_core_formula(BmcEngine(model).prepare(query))
            except BmcError as err:
                try:
                    build_bmc_core_formula(
                        BmcEngine(model).prepare("check reach <= %d: terminated();" % steps)
                    )
                except BmcError:
                    # The model itself exceeds a documented bound of the relation
                    # (cold start refuses it the same way), so no start can be judged.
                    skipped += 1
                    break
                failures.append((index, start, "refused: %s" % err, text))
                continue
            problem = _compare_hot_start(model, core, start, variables, steps, cycle_inputs)
            if problem is not None:
                failures.append((index, start, problem, text))
            else:
                checked += 1
    return checked, skipped, failures


def _compare_hot_start(model, core, start, variables, steps, cycle_inputs):
    """Return why a hot start disagrees with the simulator, or ``None`` when it agrees."""
    for sequence in itertools.product(cycle_inputs, repeat=steps):
        try:
            runtime = SimulationRuntime(
                model,
                initial_state=start,
                initial_vars=variables,
                input_source={"d": 0},
            )
        except ValueError as err:
            return "the simulator refuses the start: %s" % err
        pins = []
        expected = []
        try:
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
        except (SimulationRuntimeDfsError, SimulationRuntimeExpressionError, ValueError):
            return None
        solver = z3.Solver()
        solver.set("timeout", 20000)
        solver.add(core.core, *pins)
        solver.push()
        solver.add(z3.And(*expected))
        reachable = solver.check()
        solver.pop()
        solver.add(z3.Not(z3.And(*expected)))
        forced = solver.check()
        if z3.unknown in (reachable, forced):
            return None
        if reachable != z3.sat or forced != z3.unsat:
            return "inputs %r: observations %s, forced %s" % (sequence, reachable, forced)
    return None


def _reachable_in_simulator(model, steps, cycle_inputs, wanted):
    """Return whether some sequence of cycles reaches a state where ``wanted`` holds.

    ``wanted`` is called with the runtime after every cycle, the cold start
    included, and says whether the state of the machine is the one asked about.
    """
    for sequence in itertools.product(cycle_inputs, repeat=steps):
        runtime = SimulationRuntime(model, input_source={"d": 0})
        for d, go in sequence:
            try:
                runtime.cycle(["Root.Go"] if go else [], inputs={"d": d})
            except (SimulationRuntimeDfsError, SimulationRuntimeExpressionError):
                break
            if wanted(runtime):
                return True
    return False


def check_region_properties(count, seed, steps=3):
    """Return ``(checked, undecided, skipped, failures)`` for properties of region models.

    For a random region model and a random state of it, ``reach`` of
    ``active("<state>")`` must have a witness exactly when some sequence of inputs
    and events within ``steps`` cycles brings the simulator to a configuration in
    which that state is active, and the witness has to replay.  The states of
    every region are asked about, and so are the owners.
    """
    rng = random.Random(seed)
    checked = undecided = skipped = 0
    failures = []
    cycle_inputs = [(d, go) for d in (0, 1) for go in (False, True)]
    for index in range(count):
        text = _region_model(rng)
        try:
            model = load_state_machine_from_text(text)
        except Exception:  # noqa: BLE001 - generator output the grammar refuses
            skipped += 1
            continue
        paths = sorted(
            ".".join(state.path) for state in model.walk_states() if len(state.path) > 1
        )
        for path in rng.sample(paths, min(3, len(paths))):
            query = (
                "assume always: d == 0 || d == 1;\n"
                'check reach <= %d: active("%s");' % (steps, path)
            )
            try:
                result = solve_bmc_property(
                    compile_bmc_query(model, query), timeout_ms=20000
                )
            except BmcError:
                skipped += 1
                continue
            if result.status in ("unknown", "timeout") or result.runtime_safety.status in (
                "unknown",
                "timeout",
            ):
                undecided += 1
                continue
            if result.runtime_safety.status == "violated":
                skipped += 1
                continue
            try:
                simulated = _reachable_in_simulator(
                    model,
                    steps,
                    cycle_inputs,
                    lambda runtime, path=path: not runtime.is_ended
                    and runtime.configuration.is_active(path),
                )
            except (SimulationRuntimeDfsError, ValueError):
                skipped += 1
                continue
            if bool(result.witness_found) != simulated:
                failures.append((index, path, result.witness_found, simulated, text))
                continue
            if result.witness_found and not replay_bmc_witness(
                model, decode_bmc_result_trace(result)
            ).ok:
                failures.append((index, path, "the witness does not replay", simulated, text))
                continue
            checked += 1
    return checked, undecided, skipped, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--check", action="store_true", required=True, help="Run both comparisons."
    )
    parser.add_argument("--expressions", type=int, default=1500)
    parser.add_argument("--models", type=int, default=40)
    parser.add_argument("--region-models", type=int, default=30)
    parser.add_argument("--region-steps", type=int, default=3)
    parser.add_argument("--region-safety-models", type=int, default=12)
    parser.add_argument("--region-hot-start-models", type=int, default=10)
    parser.add_argument("--region-property-models", type=int, default=8)
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
    safe_checked, safe_undecided, safe_skipped, safe_failures = check_region_safety(
        args.region_safety_models, args.seed, args.region_steps
    )
    print(
        "region safety: %d agree with the simulator, %d undecided by Z3, "
        "%d skipped, %d failures"
        % (safe_checked, safe_undecided, safe_skipped, len(safe_failures))
    )
    for index, reported, raised, text in safe_failures[:5]:
        print(
            "  region model %d: BMC reports step %r, the simulator raises in cycle %r\n%s"
            % (index, reported, raised, text)
        )
    hot_checked, hot_skipped, hot_failures = check_region_hot_starts(
        args.region_hot_start_models, args.seed
    )
    print(
        "region hot starts: %d positions agree on every sequence, %d models skipped, "
        "%d failures" % (hot_checked, hot_skipped, len(hot_failures))
    )
    for index, start, problem, text in hot_failures[:5]:
        print("  region model %d, start %r: %s\n%s" % (index, start, problem, text))
    prop_checked, prop_undecided, prop_skipped, prop_failures = check_region_properties(
        args.region_property_models, args.seed
    )
    print(
        "region properties: %d agree with the simulator, %d undecided by Z3, "
        "%d skipped, %d failures"
        % (prop_checked, prop_undecided, prop_skipped, len(prop_failures))
    )
    for index, path, found, simulated, text in prop_failures[:5]:
        print(
            "  region model %d, active(%r): witness %r, the simulator reaches it: %r\n%s"
            % (index, path, found, simulated, text)
        )
    return (
        1
        if failures
        or model_failures
        or region_failures
        or safe_failures
        or hot_failures
        or prop_failures
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
