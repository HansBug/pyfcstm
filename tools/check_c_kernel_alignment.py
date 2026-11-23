"""
Differential check of the generated C runtimes against the simulator.

Seeded random state machines with regions, forced transitions, pseudo states,
nested owners, aspects and effects are rendered through the built-in ``c`` and
``c_poll`` templates, compiled, and driven next to
:class:`pyfcstm.simulate.SimulationRuntime` with the same random events and
inputs.  After every cycle, including a cycle both sides refuse, the position,
the variables, the ended flag, the Delta flag and the kind of error must be the
same.  Every few cycles the run is restarted from the configuration the
simulator reports, through the hot start of both sides, and goes on.

The check lives outside ``pytest``: it compiles thousands of machines and is
meant for a long run on a build machine, not for the unit-test matrix.

Usage::

    python tools/check_c_kernel_alignment.py --check
    python tools/check_c_kernel_alignment.py --models 500 --cycles 40 --jobs 4
    python tools/check_c_kernel_alignment.py --models 200 --template c_poll --first-seed 9000

The exit status is ``0`` when every model aligned and ``1`` otherwise; each
mismatch prints its seed and the DSL source, so ``--first-seed N --models 1``
replays it.
"""

import argparse
import multiprocessing
import os
import random
import sys
from typing import List, Optional, Sequence, Tuple

# The native adapters of the unit tests drive the generated library, so the
# repository root has to be importable next to the installed package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VARS = ["a", "b", "c"]
INPUTS = ["i", "j"]
EVENTS = ["E1", "E2"]


class ModelGenerator:
    """
    Random FCSTM source with regions, owners, composites and pseudo states.

    :param rng: Seeded random source; the same seed gives the same model.
    :type rng: random.Random

    Example::

        >>> import random
        >>> source = ModelGenerator(random.Random(1)).model()
        >>> source.startswith('input int i;')
        True
    """

    def __init__(self, rng: random.Random):
        self.r = rng

    def atom(self) -> str:
        if self.r.random() < 0.3:
            return str(self.r.randint(0, 4))
        return self.r.choice(VARS + INPUTS)

    def expr(self) -> str:
        text = self.atom()
        for _ in range(self.r.randint(0, 2)):
            op = self.r.choice(["+", "-", "*"])
            text = "%s %s %s" % (
                text,
                op,
                str(self.r.randint(0, 3)) if op == "*" else self.atom(),
            )
        return text

    def block(self) -> str:
        return " ".join(
            "%s = %s;" % (self.r.choice(VARS), self.expr())
            for _ in range(self.r.randint(1, 2))
        )

    def guard(self) -> str:
        return "%s %s %s" % (
            self.expr(),
            self.r.choice([">", "<", ">=", "<=", "==", "!="]),
            self.atom(),
        )

    def eff(self, p: float = 0.4) -> str:
        return (" effect { %s }" % self.block()) if self.r.random() < p else ""

    def trig(self) -> str:
        kind = self.r.choice(["event", "guard", "guard", "none"])
        if kind == "event":
            return " : /%s" % self.r.choice(EVENTS)
        if kind == "guard":
            return " : if [%s]" % self.guard()
        return ""

    def actions(self) -> str:
        parts = []
        if self.r.random() < 0.35:
            parts.append("enter { %s }" % self.block())
        if self.r.random() < 0.8:
            parts.append("during { %s }" % self.block())
        if self.r.random() < 0.3:
            parts.append("exit { %s }" % self.block())
        return " ".join(parts)

    def aspects(self, p: float) -> str:
        out = []
        if self.r.random() < p:
            out.append(">> during before { %s }" % self.block())
        if self.r.random() < p:
            out.append(">> during after { %s }" % self.block())
        return "\n".join(out)

    def plain(self, p: float) -> str:
        out = []
        if self.r.random() < p:
            out.append("during before { %s }" % self.block())
        if self.r.random() < p:
            out.append("during after { %s }" % self.block())
        return "\n".join(out)

    def composite(self, name: str) -> str:
        kids = ["%s_a" % name, "%s_b" % name]
        lines = ["state %s {" % name]
        if self.r.random() < 0.4:
            lines.append("enter { %s }" % self.block())
        if self.r.random() < 0.4:
            lines.append("exit { %s }" % self.block())
        plain = self.plain(0.4)
        if plain:
            lines.append(plain)
        if self.r.random() < 0.6:
            lines.append("[*] -> %s : if [%s]%s;" % (kids[1], self.guard(), self.eff()))
        lines.append("[*] -> %s%s;" % (kids[0], self.eff(0.3)))
        for kid in kids:
            lines.append("state %s { %s }" % (kid, self.actions()))
        for _ in range(self.r.randint(0, 2)):
            lines.append(
                "%s -> %s : if [%s]%s;"
                % (self.r.choice(kids), self.r.choice(kids), self.guard(), self.eff())
            )
        if self.r.random() < 0.7:
            lines.append("%s -> [*]%s%s;" % (self.r.choice(kids), self.trig(), self.eff(0.3)))
        lines.append("}")
        return "\n".join(lines)

    def region(self, name: str, allow_nested: bool) -> str:
        count = self.r.randint(2, 3)
        names = ["%s%d" % (name, index) for index in range(count)]
        lines = ["region %s {" % name]
        aspects = self.aspects(0.25)
        if aspects:
            lines.append(aspects)
        kinds = {}
        for state in names:
            roll = self.r.random()
            if allow_nested and roll < 0.15:
                kinds[state] = "owner"
            elif roll < 0.40:
                kinds[state] = "composite"
            else:
                kinds[state] = "leaf"
        if self.r.random() < 0.45:
            pseudos = ["%s_p%d" % (name, index) for index in range(self.r.randint(1, 2))]
            lines.append("[*] -> %s%s;" % (pseudos[0], self.eff(0.3)))
            for index, pseudo in enumerate(pseudos):
                lines.append("pseudo state %s;" % pseudo)
                following = pseudos[index + 1] if index + 1 < len(pseudos) else None
                if following and self.r.random() < 0.7:
                    lines.append(
                        "%s -> %s : if [%s]%s;"
                        % (pseudo, following, self.guard(), self.eff(0.6))
                    )
                lines.append(
                    "%s -> %s : if [%s]%s;"
                    % (pseudo, self.r.choice(names), self.guard(), self.eff(0.6))
                )
                if self.r.random() < 0.3:
                    guard = (" : if [%s]" % self.guard()) if self.r.random() < 0.5 else ""
                    lines.append("%s -> [*]%s;" % (pseudo, guard))
                if self.r.random() < 0.75:
                    lines.append("%s -> %s%s;" % (pseudo, self.r.choice(names), self.eff(0.4)))
        else:
            if self.r.random() < 0.5:
                lines.append(
                    "[*] -> %s : if [%s]%s;" % (names[1], self.guard(), self.eff(0.5))
                )
            if self.r.random() < 0.85:
                lines.append("[*] -> %s%s;" % (names[0], self.eff(0.3)))
            else:
                lines.append("[*] -> %s : if [%s];" % (names[0], self.guard()))
        for state in names:
            if kinds[state] == "owner":
                lines.append(self.owner(state, allow_nested=False))
            elif kinds[state] == "composite":
                lines.append(self.composite(state))
            else:
                lines.append("state %s { %s }" % (state, self.actions()))
        for _ in range(self.r.randint(1, 3)):
            lines.append(
                "%s -> %s%s%s;"
                % (
                    self.r.choice(names),
                    self.r.choice(names),
                    self.trig() or (" : if [%s]" % self.guard()),
                    self.eff(),
                )
            )
        if self.r.random() < 0.55:
            lines.append(
                "%s -> [*]%s%s;"
                % (
                    self.r.choice(names),
                    self.trig() or (" : if [%s]" % self.guard()),
                    self.eff(0.3),
                )
            )
        lines.append("}")
        return "\n".join(lines)

    def owner(self, name: str, allow_nested: bool = True) -> str:
        lines = ["state %s {" % name]
        if self.r.random() < 0.4:
            lines.append("enter { %s }" % self.block())
        if self.r.random() < 0.4:
            lines.append("exit { %s }" % self.block())
        plain = self.plain(0.35)
        if plain:
            lines.append(plain)
        aspects = self.aspects(0.25)
        if aspects:
            lines.append(aspects)
        for index in range(self.r.randint(1, 3)):
            lines.append(self.region("%s_R%d" % (name, index), allow_nested))
        lines.append("}")
        return "\n".join(lines)

    def model(self) -> str:
        lines = [
            "input int i;",
            "input int j;",
            "def int a = 0;",
            "def int b = 0;",
            "def int c = %d;" % self.r.randint(0, 3),
            "state Root {",
            "event E1;",
            "event E2;",
        ]
        aspects = self.aspects(0.3)
        if aspects:
            lines.append(aspects)
        lines.append("[*] -> Idle;")
        lines.append("state Idle { %s }" % self.actions())
        lines.append("state F { %s }" % self.actions())
        lines.append(self.owner("P"))
        lines.append(self.owner("Q"))
        transitions = [
            "Idle -> P : /E1;",
            "Idle -> Q : if [%s];" % self.guard(),
            "F -> Idle : /E1;",
        ]
        if self.r.random() < 0.7:
            transitions.append("!P -> F : /E2;")
        if self.r.random() < 0.5:
            transitions.append("!Q -> Idle : if [%s];" % self.guard())
        transitions.append(
            "P -> %s : if [%s];" % (self.r.choice(["Idle", "F", "Q"]), self.guard())
        )
        transitions.append("Q -> F;")
        self.r.shuffle(transitions)
        lines.extend(transitions)
        lines.append("}")
        return "\n".join(lines) + "\n"


class _InputSource:
    """Input snapshot shared by the simulator and the generated runtime."""

    def __init__(self, names: Sequence[str]):
        self.input_names = tuple(names)
        self.snapshot = {}

    def get(self):
        return dict(self.snapshot)

    def cycle(self):
        return None


def _error_family(err: BaseException) -> str:
    """Name an error the way two runtimes can agree on it."""
    if "SimulationRuntimeDfsError" in [cls.__name__ for cls in type(err).__mro__]:
        return "loop" if "suspected loop" in str(err) else "limit"
    return type(err).__name__


def run_model(job: Tuple[int, str, int, int]) -> Tuple[int, str, str, str, str]:
    """
    Drive one random model through the simulator and the generated runtime.

    :param job: ``(seed, template, cycles, restart_every)``.
    :type job: Tuple[int, str, int, int]
    :return: ``(seed, template, verdict, detail, source)`` where the verdict is ``ok``,
        ``invalid`` (the random source is not a valid model, not a finding),
        ``refused`` (counts of cycles both sides refused are in ``detail``) or
        ``mismatch``.
    :rtype: Tuple[int, str, str, str, str]
    """
    from pyfcstm.model import load_state_machine_from_text
    from pyfcstm.simulate import SimulationRuntime
    from pyfcstm.simulate.runtime import SimulationRuntimeDfsError

    seed, template, cycles, restart_every = job
    rng = random.Random(seed)
    source = ModelGenerator(rng).model()
    try:
        model = load_state_machine_from_text(source)
    except (ValueError, SyntaxError) as err:  # pragma: no cover - generator output is valid
        # ModelValidationError and GrammarParseError are ValueError/SyntaxError
        # subclasses: an invalid random source is not a finding.
        return seed, template, "invalid", str(err).splitlines()[0][:100], source

    from test.testings import native_semantic_alignment as aligned

    runner = {
        "c": aligned.GENERATED_C_ALIGNMENT,
        "c_poll": aligned.GENERATED_C_POLL_ALIGNMENT,
    }[template]
    native_utils = aligned._native_utils_for_runner(runner)

    def build_pair(configuration=None, values=None):
        source_of_inputs = _InputSource(model.inputs)
        kwargs = {}
        if configuration is not None:
            kwargs = {"initial_state": configuration, "initial_vars": values}
        simulation = SimulationRuntime(model, input_source=source_of_inputs, **kwargs)
        simulation._fixture_input_source = source_of_inputs
        native = native_utils.build_c_runtime(source, **kwargs)
        return aligned._GeneratedNativeAlignmentRuntime(simulation, native, source), source_of_inputs

    refused = 0
    pair = None
    try:
        pair, inputs = build_pair()
        pair._assert_aligned("initial build")
        for step in range(cycles):
            if restart_every and step and step % restart_every == 0 and not pair.is_ended:
                values = {
                    name: value
                    for name, value in pair.vars.items()
                    if name not in model.inputs
                }
                configuration = pair.configuration
                pair._native_runtime.close()
                pair, inputs = build_pair(configuration, values)
                pair._assert_aligned("after hot start at %s" % configuration)
            inputs.snapshot = {name: rng.randint(-2, 3) for name in model.inputs}
            events = [event for event in ("Root.E1", "Root.E2") if rng.random() < 0.35]
            try:
                pair.cycle(events)
            except SimulationRuntimeDfsError:
                # Both sides refused with the same kind of error, which
                # ``cycle`` has already compared.
                refused += 1
    except AssertionError as err:
        return seed, template, "mismatch", str(err), source
    finally:
        if pair is not None:
            pair._native_runtime.close()
    if refused:
        return seed, template, "refused", "%d refused cycle(s)" % refused, source
    return seed, template, "ok", "", source


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--models", type=int, default=100, help="random models to check")
    parser.add_argument("--cycles", type=int, default=30, help="cycles driven per model")
    parser.add_argument("--first-seed", type=int, default=1, help="seed of the first model")
    parser.add_argument("--jobs", type=int, default=1, help="parallel workers")
    parser.add_argument(
        "--restart-every",
        type=int,
        default=7,
        help="restart from the reported configuration every N cycles; 0 disables",
    )
    parser.add_argument(
        "--template",
        choices=("c", "c_poll", "both"),
        default="both",
        help="template to check",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="small self-check run: 6 models, 12 cycles, both templates",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the check and print one line per finding and a summary.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: Optional[Sequence[str]]
    :return: ``0`` when every model aligned, otherwise ``1``.
    :rtype: int
    """
    args = _parse_args(argv)
    if args.check:
        args.models, args.cycles, args.template = 6, 12, "both"
    templates = ["c", "c_poll"] if args.template == "both" else [args.template]
    jobs: List[Tuple[int, str, int, int]] = [
        (seed, template, args.cycles, args.restart_every)
        for template in templates
        for seed in range(args.first_seed, args.first_seed + args.models)
    ]
    counts = {"ok": 0, "refused": 0, "invalid": 0, "mismatch": 0}
    failures = []

    def record(result):
        seed, template, verdict, detail, source = result
        counts[verdict] += 1
        if verdict == "mismatch":
            failures.append((seed, template, detail, source))

    if args.jobs > 1:
        with multiprocessing.Pool(args.jobs) as pool:
            for result in pool.imap_unordered(run_model, jobs):
                record(result)
    else:
        for job in jobs:
            record(run_model(job))
    for seed, template, detail, source in failures:
        print(
            "MISMATCH template=%s seed=%d\n%s\n--- source ---\n%s"
            % (template, seed, detail, source)
        )
    print(
        "checked %d model runs: %s"
        % (len(jobs), ", ".join("%s=%d" % item for item in counts.items()))
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
