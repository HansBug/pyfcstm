#!/usr/bin/env python
"""
Measure what regions cost in models, simulation and generated runtimes.

This is a maintenance tool: it is not part of the ``pyfcstm`` package, it is not
run by pytest and it is not run in CI. It produces the JSON Lines data files that
back the page ``docs/source/explanations/region_performance`` and the figures
drawn from them. Numbers in that page are properties of one machine, one commit
and one Python or C compiler; rerun the tool to refresh them.

Sub-commands:

* ``e1``: model size. Builds a region model and its hand-expanded flat
  equivalent for small parameters, counts states and transitions, and checks on
  random input sequences that both give the same variable values every cycle.
  Also measures the coupled case in which a later region reads what an earlier
  region wrote in the same cycle.
* ``e2``: time per cycle of :class:`pyfcstm.simulate.SimulationRuntime`, one
  parameter swept at a time.
* ``e3``: time per cycle of the generated Python runtime on the same models.
* ``e4``: time per cycle, code size, ``sizeof`` and capacity macros of the
  generated C runtime (needs ``gcc`` and ``size``).
* ``fit``: least-squares fits over the data written by the other sub-commands.

Parameters of the generated sweep models (see :func:`sweep_model`): ``R``
regions per owner, ``S`` states per region, ``T`` transitions per state, ``D``
owner nesting levels, ``V`` variables written by every transition.

The module contains:

* :class:`Writer` - JSON Lines writer that stamps every record with the commit
  and a machine description
* :func:`sweep_model`, :func:`product_model`, :func:`expanded_model`,
  :func:`coupled_models`, :func:`flat_family` - generators of the measured models
* :func:`count_model`, :func:`load_model` - model loading and size counting
* :func:`measure_sim`, :func:`measure_python_runtime`, :func:`measure_c` -
  per-engine measurement of one model
* :func:`linear_fit`, :func:`poly_fit`, :func:`power_fit` - dependency-free fits
* :func:`cmd_e1`, :func:`cmd_e2`, :func:`cmd_e3`, :func:`cmd_e4`,
  :func:`cmd_fit`, :func:`build_parser`, :func:`main` - the command line

.. note::
   Timing needs a quiet machine. Pin the process with ``--core`` and treat
   differences below the run-to-run noise (about 2 % to 16 % in the recorded
   data) as no difference.

Example::

    $ python tools/measure_region_performance.py e2 --out data/e2.jsonl --core 3
    $ python tools/measure_region_performance.py fit --data-dir data --out data/fits.json

Every record carries the commit, a machine description, the parameters, the
number of repeats and the statistic that is reported.
"""

import argparse
import importlib.util
import json
import math
import os
import platform
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time

BASE = {"R": 4, "S": 8, "T": 2, "D": 1, "V": 1}
SWEEPS = {
    "R": [1, 2, 4, 8, 16, 32, 64, 128],
    "S": [3, 4, 8, 16, 32, 64, 128],
    "T": [1, 2, 3, 4, 5, 6, 7],
    "V": [1, 2, 4, 8, 16, 32, 64],
}
DEPTHS = [1, 2, 3, 4, 5, 6, 8, 10, 12]
C_SWEEPS = {
    "R": [1, 2, 4, 8, 16, 32, 64],
    "S": [3, 4, 8, 16, 32, 64],
    "T": [1, 2, 3, 4, 5, 6, 7],
    "V": [1, 2, 4, 8, 16, 32, 64],
}
SEQ_LEN = 1024


# ----------------------------------------------------------------------------
# Environment description
# ----------------------------------------------------------------------------


def repo_root():
    """
    Return the root of the checkout that contains this tool.

    The tool lives in ``tools/`` of the repository, so the root is two directory
    levels above this file. It is used to ask git for the commit that a measurement
    belongs to, which is why it follows the file and not the working directory.

    :return: Absolute path of the repository root.
    :rtype: str

    Example::

        >>> import os
        >>> os.path.isfile(os.path.join(repo_root(), "setup.py"))
        True
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_commit():
    """
    Return the short commit hash of the checkout, or ``unknown``.

    The hash goes into every data record so that a number can be traced to the code
    that produced it. When git is missing or the directory is not a checkout, the
    tool still runs and records the string ``unknown`` instead of failing.

    :return: Eight hexadecimal characters, or ``unknown``.
    :rtype: str

    Example::

        >>> len(git_commit()) in (7, 8)
        True
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=repo_root(),
            capture_output=True,
            text=True,
        )
    except OSError:
        # OSError: git is not installed.
        return "unknown"
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def machine_info():
    """
    Describe the machine, the Python version and the C compiler.

    The description is stored with every record. The processor name comes from
    ``/proc/cpuinfo`` where it exists, otherwise from :func:`platform.processor`.
    ``gcc`` is ``None`` when the compiler is not installed, which only matters for
    the ``e4`` sub-command.

    :return: Dictionary with the keys ``cpu``, ``os``, ``python`` and ``gcc``.
    :rtype: dict

    Example::

        >>> sorted(machine_info())
        ['cpu', 'gcc', 'os', 'python']
    """
    cpu = platform.processor() or "unknown"
    try:
        with open("/proc/cpuinfo") as handle:
            for line in handle:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except OSError:
        # OSError: no /proc/cpuinfo on this platform; keep the generic name.
        pass
    info = {
        "cpu": cpu,
        "os": platform.system() + " " + platform.release(),
        "python": platform.python_version(),
    }
    try:
        out = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
        info["gcc"] = out.stdout.splitlines()[0] if out.stdout else "unknown"
    except OSError:
        # OSError: gcc is not installed; only e4 needs it.
        info["gcc"] = None
    return info


def pin_core(core):
    """
    Pin the process to one core where the platform allows it.

    Pinning removes migration between cores from the timings. On platforms without
    ``os.sched_setaffinity`` (macOS, Windows) the call does nothing, so the
    measurement still runs but is noisier.

    :param core: Core number, or ``None`` to leave the affinity alone.
    :type core: Optional[int]
    :return: ``None``.
    :rtype: None

    Example::

        >>> pin_core(None)
    """
    if core is not None and hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {core})


class Writer:
    """
    Append JSON Lines records that all carry the same provenance fields.

    Every record written through :meth:`write` also contains the fields given at
    construction, the commit of the checkout and the machine description, so a data
    file can be interpreted without the command line that produced it. The file is
    truncated when the writer is created; one writer owns one file.

    :param path: Output file; it is truncated when the writer is created, and its
        directory is created when missing.
    :type path: str
    :param extra: Fields added to every record, defaults to ``None`` (none).
    :type extra: Optional[dict]

    :ivar path: Output file path.
    :vartype path: str
    :ivar base: Fields stamped on every record: ``extra``, ``commit`` and
        ``machine``.
    :vartype base: dict

    Example::

        >>> import json, os, tempfile
        >>> with tempfile.TemporaryDirectory() as directory:
        ...     writer = Writer(os.path.join(directory, "out.jsonl"), {"experiment": "demo"})
        ...     writer.write(value=1)
        ...     with open(writer.path) as handle:
        ...         record = json.loads(handle.readline())
        {"value": 1}
        >>> sorted(record)
        ['commit', 'experiment', 'machine', 'value']
    """

    def __init__(self, path, extra=None):
        """
        Create the output directory, truncate the file and prepare the stamp fields.

        :param path: Output file path.
        :type path: str
        :param extra: Fields added to every record, defaults to ``None`` (none).
        :type extra: Optional[dict]
        :return: ``None``.
        :rtype: None
        """
        self.path = path
        self.base = dict(extra or {})
        self.base["commit"] = git_commit()
        self.base["machine"] = machine_info()
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "w"):
            pass

    def write(self, **fields):
        """
        Append one record and echo it to standard output.

        The record is the stamp fields updated with ``fields``; a key in ``fields``
        wins over a stamp key of the same name. The echo leaves out ``model`` to keep
        progress lines short; the file keeps it. Keys are written sorted so that two
        runs on identical values produce identical lines.

        :param fields: Record fields. All values must be JSON serialisable.
        :type fields: object
        :return: ``None``.
        :rtype: None
        :raises TypeError: If a field value is not JSON serialisable.

        Example::

            >>> import os, tempfile
            >>> with tempfile.TemporaryDirectory() as directory:
            ...     Writer(os.path.join(directory, "out.jsonl")).write(n=3)
            {"n": 3}
        """
        row = dict(self.base)
        row.update(fields)
        with open(self.path, "a") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        print(json.dumps({k: v for k, v in fields.items() if k != "model"}), flush=True)


# ----------------------------------------------------------------------------
# Model generators
# ----------------------------------------------------------------------------


def input_sequence(T, seed=1, length=SEQ_LEN):
    """
    Return the deterministic input sequence shared by all engines.

    Each value is in ``0..T``: ``0`` makes no transition fire and ``c >= 1`` makes
    the ``c``-th guard of a sweep model true. The simulator, the generated Python
    runtime and the generated C driver all read the same sequence (the C driver
    gets it as a table), so their final variables can be compared.

    :param T: Transitions per state; the largest value in the sequence.
    :type T: int
    :param seed: Random seed, defaults to ``1``.
    :type seed: int
    :param length: Sequence length, defaults to ``SEQ_LEN`` (1024).
    :type length: int
    :return: ``length`` integers in ``0..T``.
    :rtype: list

    Example::

        >>> input_sequence(2, length=6)
        [0, 2, 0, 1, 0, 1]
        >>> input_sequence(2, seed=2, length=6)
        [0, 0, 0, 1, 0, 2]
    """
    rng = random.Random(seed)
    return [rng.randint(0, T) for _ in range(length)]


def _ring(prefix, S, T, V, indent):
    """
    Return the DSL lines of one ring region body for :func:`sweep_model`.

    The ring has ``S`` states ``<prefix>0`` .. ``<prefix>{S-1}``, each with a
    ``during`` that adds one to ``n``, the initial transition to the first state and
    ``T`` guarded transitions per state to the next ``T`` states around the ring.
    Every transition writes ``v0`` .. ``v{V-1}``. The ring must have ``T <= S - 1``
    so that the targets differ; the caller checks that.

    :param prefix: Name prefix of the states.
    :type prefix: str
    :param S: Number of states.
    :type S: int
    :param T: Transitions per state.
    :type T: int
    :param V: Variables written by every transition.
    :type V: int
    :param indent: Indentation put in front of every line.
    :type indent: str
    :return: DSL lines without trailing newlines.
    :rtype: list
    """
    lines = []
    writes = " ".join("v%d = v%d + 1;" % (k, k) for k in range(V))
    for j in range(S):
        lines.append("%sstate %s%d { during { n = n + 1; } }" % (indent, prefix, j))
    lines.append("%s[*] -> %s0;" % (indent, prefix))
    for j in range(S):
        for t in range(T):
            lines.append(
                "%s%s%d -> %s%d : if [a == %d] effect { %s };"
                % (indent, prefix, j, prefix, (j + 1 + t) % S, t + 1, writes)
            )
    return lines


def sweep_model(R, S, T, D, V, with_ring_at_bottom=True):
    """
    Build the FCSTM text of one sweep model.

    The model has ``D`` nested owners. Every owner has ``R`` regions. At every
    level except the deepest, region ``N`` holds the next owner and the other
    ``R - 1`` regions are rings; the deepest owner has ``R`` rings. A ring has
    ``S`` states, every state has ``T`` outgoing transitions guarded by
    ``a == 1`` .. ``a == T`` and every transition writes ``V`` variables. With
    ``R = 1`` and ``D > 1`` the model is a pure chain of owners. The input ``a`` is
    the only input, so one input sequence drives the whole family.

    :param R: Regions per owner.
    :type R: int
    :param S: States per region.
    :type S: int
    :param T: Transitions per state, at most ``S - 1``.
    :type T: int
    :param D: Nesting levels of owners, at least 1.
    :type D: int
    :param V: Variables written by every transition.
    :type V: int
    :param with_ring_at_bottom: Kept for readability of callers; always true,
        defaults to ``True``.
    :type with_ring_at_bottom: bool
    :return: DSL text.
    :rtype: str
    :raises ValueError: If ``T`` is larger than ``S - 1``.

    Example::

        >>> sweep_model(1, 3, 1, 1, 1).splitlines()[:3]
        ['input int a;', 'def int n = 0;', 'def int v0 = 0;']
        >>> sweep_model(2, 8, 2, 3, 1).count("region ")
        6
    """
    if T > S - 1:
        raise ValueError("T must be at most S - 1")
    head = ["input int a;", "def int n = 0;"]
    head += ["def int v%d = 0;" % k for k in range(V)]

    def owner(level, indent):
        pad = indent + "    "
        lines = ["%sstate L%d {" % (indent, level)]
        deepest = level == D - 1
        first_ring = 0 if deepest else 1
        if not deepest:
            lines.append("%sregion N {" % pad)
            lines.append("%s    [*] -> L%d;" % (pad, level + 1))
            lines += owner(level + 1, pad + "    ")
            lines.append("%s}" % pad)
        for i in range(first_ring, R):
            lines.append("%sregion G%d {" % (pad, i))
            lines += _ring("S", S, T, V, pad + "    ")
            lines.append("%s}" % pad)
        lines.append("%s}" % indent)
        return lines

    body = ["state Root {", "    [*] -> L0;"] + owner(0, "    ") + ["}"]
    return "\n".join(head + body) + "\n"


def product_model(R, S, T):
    """
    Build the region form of the unconstrained model used by experiment 1.

    One owner with ``R`` regions of ``S`` states. Region ``i`` reads only its own
    input ``x<i>`` (values ``0..T``): value ``c >= 1`` fires the ``c``-th
    transition of the current state, which adds ``c`` to counter ``c<i>``; ``0``
    fires none and the ``during`` action adds one to ``u<i>``. Because no region
    reads another region's variables, the model is the "independent regions" case
    whose counts the page derives exactly.

    :param R: Number of regions.
    :type R: int
    :param S: States per region.
    :type S: int
    :param T: Transitions per state, at most ``S - 1``.
    :type T: int
    :return: DSL text.
    :rtype: str

    Example::

        >>> text = product_model(2, 3, 1)
        >>> text.count("region "), text.count(" -> ")
        (2, 9)
    """
    lines = ["input int x%d;" % i for i in range(R)]
    lines += ["def int c%d = 0;\ndef int u%d = 0;" % (i, i) for i in range(R)]
    lines += ["state Root {", "    [*] -> P;", "    state P {"]
    for i in range(R):
        lines.append("        region G%d {" % i)
        lines.append("            [*] -> S0;")
        for j in range(S):
            lines.append(
                "            state S%d { during { u%d = u%d + 1; } }" % (j, i, i)
            )
        for j in range(S):
            for t in range(T):
                lines.append(
                    "            S%d -> S%d : if [x%d == %d] effect { c%d = c%d + %d; };"
                    % (j, (j + 1 + t) % S, i, t + 1, i, i, t + 1)
                )
        lines.append("        }")
    lines += ["    }", "}"]
    return "\n".join(lines) + "\n"


def expanded_model(R, S, T):
    """
    Build the flat state machine equivalent to :func:`product_model`.

    One state per tuple of region states and, for every product state, one
    transition per non-empty choice of "region ``i`` fires its transition ``c_i``
    or stays". The guard is the conjunction of the chosen input values and the
    effect applies the fired effects. The ``during`` of a product state applies
    every region's action: a cycle that takes a transition runs the ``during`` of
    the state it arrives in, so the regions that stay and the regions that fired
    each get one ``during`` in that cycle, as in the region form. The size grows as
    ``S**R`` states, so keep ``R`` and ``S`` small.

    :param R: Number of regions.
    :type R: int
    :param S: States per region.
    :type S: int
    :param T: Transitions per state.
    :type T: int
    :return: DSL text.
    :rtype: str

    Example::

        >>> text = expanded_model(2, 3, 1)
        >>> text.count("state P_"), text.count(" -> ")
        (9, 28)
    """
    import itertools

    def name(tup):
        return "P_" + "_".join(str(j) for j in tup)

    lines = ["input int x%d;" % i for i in range(R)]
    lines += ["def int c%d = 0;\ndef int u%d = 0;" % (i, i) for i in range(R)]
    lines += ["state Root {", "    [*] -> %s;" % name((0,) * R)]
    during = " ".join("u%d = u%d + 1;" % (i, i) for i in range(R))
    for tup in itertools.product(range(S), repeat=R):
        lines.append("    state %s { during { %s } }" % (name(tup), during))
    for tup in itertools.product(range(S), repeat=R):
        for choice in itertools.product(range(T + 1), repeat=R):
            if not any(choice):
                continue
            target = tuple(
                (tup[i] + choice[i]) % S if choice[i] else tup[i] for i in range(R)
            )
            guard = " && ".join("x%d == %d" % (i, choice[i]) for i in range(R))
            effect = " ".join(
                "c%d = c%d + %d;" % (i, i, choice[i]) for i in range(R) if choice[i]
            )
            lines.append(
                "    %s -> %s : if [%s] effect { %s };"
                % (name(tup), name(target), guard, effect)
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def coupled_models():
    """
    Return the coupled-read models of experiment 1 as ``{label: text}``.

    Region ``W`` writes ``p = x0`` in its ``during``. Region ``V`` has two states
    that switch on ``p``. ``region`` forms put ``W`` before or after ``V``. The
    flat forms are the naive expansion (the guard reads ``p`` as it was before the
    cycle) and the substituted expansion (the guard reads ``x0``, which is what
    ``W`` writes to ``p`` earlier in the same cycle).

    :return: Mapping from label to DSL text. The labels are
        ``regions_reader_after_writer``, ``regions_reader_before_writer``,
        ``flat_naive`` and ``flat_substituted``.
    :rtype: dict

    Example::

        >>> sorted(coupled_models())
        ['flat_naive', 'flat_substituted', 'regions_reader_after_writer', 'regions_reader_before_writer']
    """
    decl = "input int x0;\ndef int p = 0;\ndef int c = 0;\ndef int d = 0;\n"

    def region_w():
        return "region W { [*] -> A; state A { during { p = x0; } } }"

    def region_v():
        return (
            "region V { [*] -> B0;\n"
            "  state B0 { during { d = d + 1; } }\n"
            "  state B1 { during { d = d + 1; } }\n"
            "  B0 -> B1 : if [p != 0] effect { c = c + 1; };\n"
            "  B1 -> B0 : if [p == 0] effect { c = c + 1; };\n}"
        )

    def regions(first, second):
        return decl + "state Root { [*] -> P; state P {\n%s\n%s\n} }\n" % (
            first,
            second,
        )

    def flat(guard0, guard1):
        return (
            decl + "state Root { [*] -> B0;\n"
            "  state B0 { during { p = x0; d = d + 1; } }\n"
            "  state B1 { during { p = x0; d = d + 1; } }\n"
            "  B0 -> B1 : if [%s] effect { c = c + 1; };\n"
            "  B1 -> B0 : if [%s] effect { c = c + 1; };\n}\n" % (guard0, guard1)
        )

    return {
        "regions_reader_after_writer": regions(region_w(), region_v()),
        "regions_reader_before_writer": regions(region_v(), region_w()),
        "flat_naive": flat("p != 0", "p == 0"),
        "flat_substituted": flat("x0 != 0", "x0 == 0"),
    }


# ----------------------------------------------------------------------------
# Model loading and counting
# ----------------------------------------------------------------------------


def load_model(text):
    """
    Parse FCSTM text into a state machine model.

    This is the public parse path (grammar entry ``state_machine_dsl`` followed by
    the model conversion) written out so that the tool does not depend on a
    convenience wrapper.

    :param text: DSL text.
    :type text: str
    :return: Model.
    :rtype: pyfcstm.model.model.StateMachine
    :raises pyfcstm.dsl.error.GrammarParseError: If the text is not valid FCSTM.

    Example::

        >>> model = load_model(product_model(2, 3, 1))
        >>> [state.name for state in model.walk_states()][:3]
        ['Root', 'P', 'S0']
    """
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine

    ast = parse_with_grammar_entry(text, entry_name="state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def count_model(model):
    """
    Count leaf states, ordinary transitions and regions of a model.

    Transitions that start at the initial pseudo state ``[*]`` are not counted,
    because they only choose where an owner or a state machine starts. Transitions
    are read from states and from regions, since a region owns its transitions.

    :param model: Model.
    :type model: pyfcstm.model.model.StateMachine
    :return: Dictionary with ``leaf_states``, ``all_states``, ``transitions`` and
        ``regions``.
    :rtype: dict

    Example::

        >>> count_model(load_model(product_model(2, 3, 1)))
        {'leaf_states': 6, 'all_states': 8, 'transitions': 6, 'regions': 2}
    """
    states = list(model.walk_states())
    leaves = [s for s in states if s.is_leaf_state]
    transitions = 0
    for state in states:
        transitions += sum(
            1
            for t in state.transitions
            if t.from_state is not None and _is_state_name(t.from_state)
        )
        for region in getattr(state, "regions", {}).values():
            transitions += sum(
                1 for t in region.transitions if _is_state_name(t.from_state)
            )
    return {
        "leaf_states": len(leaves),
        "all_states": len(states),
        "transitions": transitions,
        "regions": len(list(model.walk_regions())),
    }


def _is_state_name(from_state):
    # ``[*]`` is represented by a non-string marker; real sources are names.
    """
    Tell a real transition source from the initial marker.

    The model stores the source of an initial transition as a marker object and the
    source of every other transition as the state name string, so a ``str`` check
    separates them.

    :param from_state: ``Transition.from_state`` value.
    :type from_state: object
    :return: ``True`` for a named source state.
    :rtype: bool
    """
    return isinstance(from_state, str)


# ----------------------------------------------------------------------------
# Timing helpers
# ----------------------------------------------------------------------------


def summarize(samples):
    """
    Summarize repeated measurements.

    :param samples: Measured values, at least one.
    :type samples: list
    :return: ``min``, ``median`` and ``max``.
    :rtype: dict
    :raises ValueError: If ``samples`` is empty.

    Example::

        >>> summarize([3, 1, 2])
        {'min': 1, 'median': 2, 'max': 3}
    """
    return {
        "min": min(samples),
        "median": statistics.median(samples),
        "max": max(samples),
    }


def pick_cycles(per_cycle_s, target_s=0.2, lo=20, hi=200000):
    """
    Choose how many cycles one repeat runs so that it lasts about ``target_s``.

    A repeat that is too short is dominated by timer resolution and one that is too
    long wastes time, so the count is derived from a probe of the per-cycle cost and
    then clamped.

    :param per_cycle_s: Estimated seconds per cycle.
    :type per_cycle_s: float
    :param target_s: Wanted seconds per repeat, defaults to ``0.2``.
    :type target_s: float
    :param lo: Lower bound, defaults to ``20``.
    :type lo: int
    :param hi: Upper bound, defaults to ``200000``.
    :type hi: int
    :return: Cycle count.
    :rtype: int

    Example::

        >>> pick_cycles(0.001)
        200
        >>> pick_cycles(1.0), pick_cycles(1e-9)
        (20, 200000)
    """
    return max(lo, min(hi, int(target_s / max(per_cycle_s, 1e-9))))


def sweep_points(only=None, depth=True):
    """
    Enumerate ``(sweep_name, params)`` of the one-dimensional sweeps.

    Each sweep changes one parameter of ``BASE`` and keeps the others; points with
    ``T > S - 1`` are skipped because a ring cannot have that many distinct targets.
    The depth sweeps ``D_chain`` (``R = 1``) and ``D_branch`` (``R = 2``) follow the
    four parameter sweeps.

    :param only: Restrict to these sweep names, or ``None`` for all, defaults to
        ``None``.
    :type only: Optional[list]
    :param depth: Include the depth sweeps, defaults to ``True``.
    :type depth: bool
    :return: List of pairs of a sweep name and a parameter dictionary.
    :rtype: list

    Example::

        >>> len(sweep_points()), len(sweep_points(depth=False))
        (47, 29)
        >>> sweep_points(["D_chain"])[0]
        ('D_chain', {'R': 1, 'S': 8, 'T': 2, 'D': 1, 'V': 1})
    """
    points = []
    for name, values in SWEEPS.items():
        for value in values:
            params = dict(BASE)
            params[name] = value
            if params["T"] > params["S"] - 1:
                continue
            points.append((name, params))
    if depth:
        for variant, regions in (("D_chain", 1), ("D_branch", 2)):
            for value in DEPTHS:
                params = dict(BASE)
                params["D"] = value
                params["R"] = regions
                points.append((variant, params))
    if only:
        points = [p for p in points if p[0] in only]
    return points


# ----------------------------------------------------------------------------
# E1: model size and equivalence
# ----------------------------------------------------------------------------


def _run_vars(model, seq_by_cycle, names):
    """
    Run a model on given inputs and record the variables after every cycle.

    The runtime keeps one history entry (``history_size=1``) so that long runs do not
    grow memory. The inputs are supplied per cycle, so the construction-time source
    only needs a placeholder value for each name.

    :param model: Model with the inputs named in ``names``.
    :type model: pyfcstm.model.model.StateMachine
    :param seq_by_cycle: One input mapping per cycle.
    :type seq_by_cycle: list
    :param names: Input names of the model.
    :type names: list
    :return: One variable dictionary per cycle, in order.
    :rtype: list
    """
    from pyfcstm.simulate import SimulationRuntime

    runtime = SimulationRuntime(
        model,
        input_source={n: 0 for n in names},
        history_size=1,
    )
    trace = []
    for inputs in seq_by_cycle:
        runtime.cycle(inputs=inputs)
        trace.append(dict(runtime.vars))
    return trace


def _time_plain(model, names, seq, repeats, cycles=100):
    """
    Time simulator cycles of a model on a given input sequence.

    The sequence repeats when it is shorter than the run. Thirty warm-up cycles run
    first; the index into the sequence is shared between warm-up and batches so
    that the batches continue where the warm-up stopped.

    :param model: Model with the inputs named in ``names``.
    :type model: pyfcstm.model.model.StateMachine
    :param names: Input names of the model.
    :type names: list
    :param seq: Per-cycle input mappings.
    :type seq: list
    :param repeats: Number of timed batches.
    :type repeats: int
    :param cycles: Cycles per batch, defaults to ``100``.
    :type cycles: int
    :return: ``min``, ``median`` and ``max`` seconds per cycle.
    :rtype: dict
    """
    from pyfcstm.simulate import SimulationRuntime

    runtime = SimulationRuntime(
        model, input_source={n: 0 for n in names}, history_size=1
    )
    index = [0]

    def step(count):
        for _ in range(count):
            runtime.cycle(inputs=seq[index[0] % len(seq)])
            index[0] += 1

    step(30)
    return summarize(_time_cycles(step, cycles, repeats))


def cmd_e1(args):
    """
    Run experiment 1.

    For every grid point it builds the region form and the flat expansion, counts
    both, compares the counts with the closed formulas, checks that both give the
    same variables after every cycle on random input sequences, and (with
    ``--repeats`` above zero) times the two forms. It then runs the coupled-read
    models and compares their variables pairwise. One JSON line is written per
    grid point and per comparison.

    :param args: Parsed command line with ``out``, ``cycles``, ``seeds``,
        ``max_flat_transitions``, ``repeats`` and ``core``.
    :type args: argparse.Namespace
    :return: ``None``.
    :rtype: None

    Example::

        $ python tools/measure_region_performance.py e1 --out data/e1.jsonl --core 3
    """
    pin_core(args.core)
    writer = Writer(args.out, {"experiment": "e1"})
    cycles, seeds = args.cycles, args.seeds
    for T in (1, 2):
        for R in (1, 2, 3, 4):
            for S in (2, 3, 4):
                if T > S - 1:
                    continue
                flat_states = S**R
                flat_trans = flat_states * ((T + 1) ** R - 1)
                if flat_trans > args.max_flat_transitions:
                    continue
                region_model = load_model(product_model(R, S, T))
                flat_model = load_model(expanded_model(R, S, T))
                rc, fc = count_model(region_model), count_model(flat_model)
                names = ["x%d" % i for i in range(R)]
                equivalent, first_diff = True, None
                for seed in range(seeds):
                    rng = random.Random(seed)
                    seq = [{n: rng.randint(0, T) for n in names} for _ in range(cycles)]
                    a = _run_vars(region_model, seq, names)
                    b = _run_vars(flat_model, seq, names)
                    if a != b:
                        equivalent = False
                        first_diff = next(i for i in range(cycles) if a[i] != b[i])
                        break
                timing = {}
                if args.repeats:
                    seq = [
                        {n: rng.randint(0, T) for n in names} for _ in range(SEQ_LEN)
                    ]
                    for label, model in (
                        ("region", region_model),
                        ("flat", flat_model),
                    ):
                        timing[label] = _time_plain(model, names, seq, args.repeats)
                writer.write(
                    kind="product",
                    model={"R": R, "S": S, "T": T},
                    region_leaf_states=rc["leaf_states"],
                    region_transitions=rc["transitions"],
                    flat_leaf_states=fc["leaf_states"],
                    flat_transitions=fc["transitions"],
                    formula_region_states=R * S,
                    formula_region_transitions=R * S * T,
                    formula_flat_states=flat_states,
                    formula_flat_transitions=flat_trans,
                    equivalent=equivalent,
                    first_difference_cycle=first_diff,
                    cycles=cycles,
                    seeds=seeds,
                    repeats=args.repeats,
                    stat="median",
                    region_seconds_per_cycle=(timing.get("region") or {}).get("median"),
                    flat_seconds_per_cycle=(timing.get("flat") or {}).get("median"),
                )
    for label, text in coupled_models().items():
        model = load_model(text)
        counts = count_model(model)
        writer.write(kind="coupled", label=label, counts=counts)
    texts = coupled_models()
    pairs = [
        ("regions_reader_after_writer", "regions_reader_before_writer"),
        ("regions_reader_after_writer", "flat_naive"),
        ("regions_reader_after_writer", "flat_substituted"),
        ("regions_reader_before_writer", "flat_naive"),
        ("regions_reader_before_writer", "flat_substituted"),
    ]
    for ref_label, label in pairs:
        reference, other = load_model(texts[ref_label]), load_model(texts[label])
        mismatches, total, first = 0, 0, None
        for seed in range(args.seeds):
            rng = random.Random(100 + seed)
            seq = [{"x0": rng.randint(0, 1)} for _ in range(args.cycles)]
            a = _run_vars(reference, seq, ["x0"])
            b = _run_vars(other, seq, ["x0"])
            for i in range(args.cycles):
                total += 1
                if a[i] != b[i]:
                    mismatches += 1
                    if first is None:
                        first = i
        writer.write(
            kind="coupled_compare",
            reference=ref_label,
            label=label,
            compared_cycles=total,
            cycles_with_different_variables=mismatches,
            first_difference_cycle=first,
        )


# ----------------------------------------------------------------------------
# E2 and E3: simulator and generated Python
# ----------------------------------------------------------------------------


def _time_cycles(step, cycles, repeats):
    """
    Time ``step`` in batches and return seconds per cycle for each batch.

    :param step: Callable that runs the given number of cycles.
    :type step: Callable[[int], None]
    :param cycles: Cycles per batch; the divisor of the batch time.
    :type cycles: int
    :param repeats: Number of batches.
    :type repeats: int
    :return: One value per batch, in seconds per cycle.
    :rtype: list
    """
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        step(cycles)
        samples.append((time.perf_counter() - start) / cycles)
    return samples


def _sim_factory(model, seq):
    """
    Return a function that builds a fresh simulator runtime for ``model``.

    Every runtime reads the input ``a`` from the looped sequence ``seq`` and keeps
    one history entry, so the runtimes are independent and equally configured.

    :param model: Model with the single input ``a``.
    :type model: pyfcstm.model.model.StateMachine
    :param seq: Input values for ``a``; the sequence loops when exhausted.
    :type seq: list
    :return: Zero-argument factory.
    :rtype: Callable[[], pyfcstm.simulate.runtime.SimulationRuntime]
    """
    from pyfcstm.simulate import SequenceInput, SimulationRuntime

    def make():
        return SimulationRuntime(
            model,
            input_source={"a": SequenceInput(seq, end="loop")},
            history_size=1,
        )

    return make


def measure_sim(model, T, repeats, warmup=50):
    """
    Time :meth:`pyfcstm.simulate.SimulationRuntime.cycle` on one model.

    The first cycle is timed on freshly built runtimes (it enters every owner) and
    the steady state on one runtime after a warm-up. The number of cycles per batch
    is chosen from a probe by :func:`pick_cycles`. The final variables after
    ``SEQ_LEN`` cycles are returned so that other engines can be compared.

    :param model: Model with one input ``a``.
    :type model: pyfcstm.model.model.StateMachine
    :param T: Transitions per state, which bounds the input values.
    :type T: int
    :param repeats: Number of timed batches.
    :type repeats: int
    :param warmup: Cycles run before timing, defaults to ``50``.
    :type warmup: int
    :return: ``steady`` summary in seconds per cycle, ``first_cycle`` summary in
        seconds, ``cycles`` per batch and the final variables.
    :rtype: dict

    Example::

        >>> result = measure_sim(load_model(sweep_model(1, 3, 1, 1, 1)), 1, 1)
        >>> sorted(result)
        ['cycles', 'final_vars', 'first_cycle', 'steady']
    """
    seq = input_sequence(T)
    make = _sim_factory(model, seq)
    firsts = []
    for _ in range(max(3, min(repeats, 5))):
        runtime = make()
        start = time.perf_counter()
        runtime.cycle()
        firsts.append(time.perf_counter() - start)
    runtime = make()
    for _ in range(warmup):
        runtime.cycle()
    probe = time.perf_counter()
    for _ in range(10):
        runtime.cycle()
    cycles = pick_cycles((time.perf_counter() - probe) / 10)

    def step(count):
        for _ in range(count):
            runtime.cycle()

    steady = _time_cycles(step, cycles, repeats)
    final = make()
    for _ in range(SEQ_LEN):
        final.cycle()
    return {
        "steady": summarize(steady),
        "first_cycle": summarize(firsts),
        "cycles": cycles,
        "final_vars": dict(final.vars),
    }


def cmd_e2(args):
    """
    Run experiment 2.

    Measures the simulator on every point of :func:`sweep_points` and writes one
    record per point with the steady-state and first-cycle summaries and the final
    variables.

    :param args: Parsed command line with ``out``, ``core``, ``repeats`` and
        ``only``.
    :type args: argparse.Namespace
    :return: ``None``.
    :rtype: None

    Example::

        $ python tools/measure_region_performance.py e2 --out data/e2.jsonl --core 3 --only R
    """
    pin_core(args.core)
    writer = Writer(args.out, {"experiment": "e2", "engine": "simulator"})
    for name, params in sweep_points(args.only):
        model = load_model(sweep_model(**params))
        counts = count_model(model)
        res = measure_sim(model, params["T"], args.repeats)
        writer.write(
            sweep=name,
            model=params,
            counts=counts,
            repeats=args.repeats,
            stat="median",
            cycles_per_repeat=res["cycles"],
            seconds_per_cycle=res["steady"]["median"],
            steady=res["steady"],
            first_cycle=res["first_cycle"],
            final_vars=res["final_vars"],
        )


def _import_generated(path, name):
    """
    Import a generated ``machine.py`` from a path under a private module name.

    :param path: Path of the generated module.
    :type path: str
    :param name: Module name to register the import under.
    :type name: str
    :return: The executed module.
    :rtype: types.ModuleType
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate_with_cli(text, template, directory):
    """
    Generate a runtime with ``python -m pyfcstm generate --template``.

    The model text is written next to ``directory`` (as ``<directory>.fcstm``) and
    the command is run with the current interpreter, so the same code path as a
    user's command line is measured. A built-in template needs the packaged
    templates (``make tpl``); a directory is passed with ``-t``.

    :param text: DSL text.
    :type text: str
    :param template: Built-in template name or ``-t`` directory.
    :type template: str
    :param directory: Output directory; the model is written next to it.
    :type directory: str
    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If ``pyfcstm generate`` fails.

    Example::

        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as workdir:
        ...     out = os.path.join(workdir, "out")
        ...     generate_with_cli(sweep_model(1, 3, 1, 1, 1), "python", out)
        ...     os.path.isfile(os.path.join(out, "machine.py"))
        True
    """
    src = directory + ".fcstm"
    with open(src, "w") as handle:
        handle.write(text)
    flag = ["-t", template] if os.path.isdir(template) else ["--template", template]
    subprocess.run(
        [sys.executable, "-m", "pyfcstm", "generate", "-i", src]
        + flag
        + ["-o", directory],
        check=True,
        capture_output=True,
    )


def measure_python_runtime(text, T, repeats, workdir, warmup=50):
    """
    Generate the Python runtime of ``text`` and time its ``cycle``.

    The runtime is generated with :func:`generate_with_cli`, imported, and driven
    with ``cycle(inputs={"a": ...})`` from the shared input sequence. As in
    :func:`measure_sim` the first cycle is timed on fresh machines, the steady state
    after a warm-up, and the final variables after ``SEQ_LEN`` cycles are returned.

    :param text: DSL text with one input ``a``.
    :type text: str
    :param T: Transitions per state.
    :type T: int
    :param repeats: Timed batches.
    :type repeats: int
    :param workdir: Scratch directory.
    :type workdir: str
    :param warmup: Warm-up cycles, defaults to ``50``.
    :type warmup: int
    :return: Dictionary like :func:`measure_sim` plus ``import_seconds`` and
        ``machine_bytes``.
    :rtype: dict
    :raises subprocess.CalledProcessError: If the runtime cannot be generated.

    Example::

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as workdir:
        ...     result = measure_python_runtime(sweep_model(1, 3, 1, 1, 1), 1, 1, workdir)
        >>> sorted(result)
        ['cycles', 'final_vars', 'first_cycle', 'import_seconds', 'machine_bytes', 'steady']
    """
    out = os.path.join(workdir, "py")
    generate_with_cli(text, "python", out)
    path = os.path.join(out, "machine.py")
    start = time.perf_counter()
    module = _import_generated(path, "region_perf_machine")
    import_seconds = time.perf_counter() - start
    cls = next(
        v
        for v in vars(module).values()
        if isinstance(v, type)
        and v.__module__ == module.__name__
        and hasattr(v, "cycle")
        and v.__name__.endswith("Machine")
    )
    seq = input_sequence(T)

    def make():
        machine = cls()
        machine._seq_index = 0
        return machine

    def run(machine, count):
        index = machine._seq_index
        for _ in range(count):
            machine.cycle(inputs={"a": seq[index % SEQ_LEN]})
            index += 1
        machine._seq_index = index

    firsts = []
    for _ in range(max(3, min(repeats, 5))):
        machine = make()
        start = time.perf_counter()
        run(machine, 1)
        firsts.append(time.perf_counter() - start)
    machine = make()
    run(machine, warmup)
    probe = time.perf_counter()
    run(machine, 10)
    cycles = pick_cycles((time.perf_counter() - probe) / 10)
    steady = _time_cycles(lambda c: run(machine, c), cycles, repeats)
    final = make()
    run(final, SEQ_LEN)
    return {
        "steady": summarize(steady),
        "first_cycle": summarize(firsts),
        "cycles": cycles,
        "final_vars": dict(final.vars),
        "import_seconds": import_seconds,
        "machine_bytes": os.path.getsize(path),
    }


def cmd_e3(args):
    """
    Run experiment 3.

    Measures the generated Python runtime on every point of :func:`sweep_points`.
    With ``--sim-data`` it also records whether the final variables equal those of
    the simulator measurement of the same point.

    :param args: Parsed command line with ``out``, ``core``, ``repeats``, ``only``
        and ``sim_data``.
    :type args: argparse.Namespace
    :return: ``None``.
    :rtype: None

    Example::

        $ python tools/measure_region_performance.py e3 --out data/e3.jsonl --core 3 --sim-data data/e2.jsonl
    """
    pin_core(args.core)
    writer = Writer(args.out, {"experiment": "e3", "engine": "generated_python"})
    sim = {}
    if args.sim_data:
        with open(args.sim_data) as handle:
            for line in handle:
                row = json.loads(line)
                sim[(row["sweep"], tuple(sorted(row["model"].items())))] = row
    for name, params in sweep_points(args.only):
        text = sweep_model(**params)
        with tempfile.TemporaryDirectory() as workdir:
            res = measure_python_runtime(text, params["T"], args.repeats, workdir)
        reference = sim.get((name, tuple(sorted(params.items()))))
        writer.write(
            sweep=name,
            model=params,
            repeats=args.repeats,
            stat="median",
            cycles_per_repeat=res["cycles"],
            seconds_per_cycle=res["steady"]["median"],
            steady=res["steady"],
            first_cycle=res["first_cycle"],
            import_seconds=res["import_seconds"],
            machine_bytes=res["machine_bytes"],
            final_vars=res["final_vars"],
            simulator_final_vars_equal=(
                reference["final_vars"] == res["final_vars"] if reference else None
            ),
        )


# ----------------------------------------------------------------------------
# E4: generated C
# ----------------------------------------------------------------------------

DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>
#include "machine.h"
static const int SEQ[%(seq_len)d] = {%(seq)s};
#ifdef %(macro)s_ARENA_CAPACITY
#define CAP_ARENA ((long)%(macro)s_ARENA_CAPACITY)
#define CAP_TRAIL ((long)%(macro)s_TRAIL_CAPACITY)
#define CAP_STORAGE ((long)%(macro)s_STORAGE_BYTES)
#else
#define CAP_ARENA (-1L)
#define CAP_TRAIL (-1L)
#define CAP_STORAGE (-1L)
#endif
static double cpu_ns(void) { struct timespec t; clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t); return 1e9 * t.tv_sec + t.tv_nsec; }
static double mono_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC_RAW, &t); return 1e9 * t.tv_sec + t.tv_nsec; }
int main(int argc, char **argv)
{
    long cycles = argc > 1 ? atol(argv[1]) : 100000L, i;
    static %(cls)s machine;
    %(cls)s *m = &machine;
    %(cls)sInputs inputs;
    double t0, t1, f0, f1;
    const unsigned char *bytes; size_t k; uint64_t h = 1469598103934665603ULL;
    memset(&inputs, 0, sizeof(inputs));
    %(cls)s_init(m);
    f0 = mono_ns();
    inputs.a = SEQ[0];
    if (!%(cls)s_cycle_with_inputs(m, NULL, 0, &inputs)) return 1;
    f1 = mono_ns();
    t0 = cpu_ns();
    for (i = 1; i <= cycles; ++i) {
        inputs.a = SEQ[i %% %(seq_len)d];
        if (!%(cls)s_cycle_with_inputs(m, NULL, 0, &inputs)) return 2;
    }
    t1 = cpu_ns();
    bytes = (const unsigned char *)%(cls)s_vars(m);
    for (k = 0; k < sizeof(%(cls)sVars); ++k) { h ^= bytes[k]; h *= 1099511628211ULL; }
    printf("{\"ns_per_cycle\": %%.3f, \"first_cycle_ns\": %%.0f, \"vars_hash\": \"%%016llx\", \"sizeof_machine\": %%zu, \"arena\": %%ld, \"trail\": %%ld, \"storage_bytes\": %%ld}\n",
           (t1 - t0) / (double)cycles, f1 - f0, (unsigned long long)h, sizeof(*m),
           CAP_ARENA, CAP_TRAIL, CAP_STORAGE);
    return 0;
}
"""


def c_names(text):
    """
    Return the C class prefix and macro prefix of a generated machine.

    Every sweep model has the root state ``Root``, so the names are constants; the
    parameter exists so that a model with another root can be supported by changing
    one function.

    :param text: DSL text whose root state is ``Root``.
    :type text: str
    :return: Class prefix and macro prefix.
    :rtype: tuple

    Example::

        >>> c_names(sweep_model(1, 3, 1, 1, 1))
        ('RootMachine', 'ROOT_MACHINE')
    """
    return "RootMachine", "ROOT_MACHINE"


def build_c(text, template, workdir, T):
    """
    Generate the C runtime, compile it with the driver and measure its size.

    The driver (``DRIVER``) is written next to the generated files, filled with the
    class and macro names and the shared input table, and compiled with
    ``gcc -O2 -std=c99``. The sizes come from ``size`` on a separate object built
    from ``machine.c`` alone, so the driver is not counted.

    :param text: DSL text with input ``a`` and root ``Root``.
    :type text: str
    :param template: Built-in template name or a template directory.
    :type template: str
    :param workdir: Scratch directory.
    :type workdir: str
    :param T: Transitions per state; bounds the input values.
    :type T: int
    :return: ``exe``, ``text``, ``data``, ``bss`` and ``generate_seconds``.
    :rtype: dict
    :raises subprocess.CalledProcessError: If generation, compilation or ``size``
        fails (for example when ``gcc`` is missing the C library headers).

    Example::

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as workdir:
        ...     built = build_c(sweep_model(1, 3, 1, 1, 1), "c", workdir, 1)
        >>> sorted(built)
        ['bss', 'data', 'exe', 'generate_seconds', 'text']
    """
    out = os.path.join(workdir, "c")
    start = time.perf_counter()
    generate_with_cli(text, template, out)
    gen_seconds = time.perf_counter() - start
    cls, macro = c_names(text)
    seq = input_sequence(T)
    with open(os.path.join(out, "driver.c"), "w") as handle:
        handle.write(
            DRIVER
            % {
                "cls": cls,
                "macro": macro,
                "seq_len": SEQ_LEN,
                "seq": ",".join(str(v) for v in seq),
            }
        )
    flags = ["-O2", "-std=c99", "-D_POSIX_C_SOURCE=200809L"]
    exe = os.path.join(out, "drv")
    subprocess.run(
        ["gcc"]
        + flags
        + [
            os.path.join(out, "machine.c"),
            os.path.join(out, "driver.c"),
            "-lm",
            "-o",
            exe,
        ],
        check=True,
        capture_output=True,
    )
    obj = os.path.join(out, "machine_sz.o")
    subprocess.run(
        ["gcc"] + flags[:2] + ["-c", os.path.join(out, "machine.c"), "-o", obj],
        check=True,
        capture_output=True,
    )
    row = subprocess.run(["size", obj], check=True, capture_output=True, text=True)
    cols = row.stdout.splitlines()[1].split()
    return {
        "exe": exe,
        "text": int(cols[0]),
        "data": int(cols[1]),
        "bss": int(cols[2]),
        "generate_seconds": gen_seconds,
    }


def run_c(exe, cycles, core, repeats):
    """
    Run the compiled driver several times and keep every result.

    Each run prints one JSON line; the lines are parsed in order. With ``core`` set
    the run is wrapped in ``taskset -c``.

    :param exe: Executable built by :func:`build_c`.
    :type exe: str
    :param cycles: Cycles per run.
    :type cycles: int
    :param core: Core to pin to, or ``None`` for no pinning.
    :type core: Optional[int]
    :param repeats: Number of runs.
    :type repeats: int
    :return: Parsed JSON results, one dictionary per run.
    :rtype: list
    :raises subprocess.CalledProcessError: If a run exits with a non-zero status.

    Example::

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as workdir:
        ...     built = build_c(sweep_model(1, 3, 1, 1, 1), "c", workdir, 1)
        ...     results = run_c(built["exe"], 2000, None, 1)
        >>> sorted(results[0])
        ['arena', 'first_cycle_ns', 'ns_per_cycle', 'sizeof_machine', 'storage_bytes', 'trail', 'vars_hash']
    """
    results = []
    for _ in range(repeats):
        cmd = [exe, str(cycles)]
        if core is not None:
            cmd = ["taskset", "-c", str(core)] + cmd
        out = subprocess.run(cmd, check=True, capture_output=True, text=True)
        results.append(json.loads(out.stdout.strip().splitlines()[-1]))
    return results


def measure_c(text, template, T, core, repeats, workdir):
    """
    Measure one model in generated C.

    A probe run of 2000 cycles fixes the cycle count of the measured runs so that
    each lasts about 0.25 s; the reported time per cycle is the minimum over
    ``repeats`` runs, because noise on a shared machine only ever adds time.

    :param text: DSL text.
    :type text: str
    :param template: Template name or directory.
    :type template: str
    :param T: Transitions per state.
    :type T: int
    :param core: Core to pin to, or ``None``.
    :type core: Optional[int]
    :param repeats: Number of runs; the minimum is the reported value.
    :type repeats: int
    :param workdir: Scratch directory.
    :type workdir: str
    :return: Dictionary of fields for a record, among them ``ns_per_cycle``,
        ``first_cycle_ns``, ``sizeof_machine``, the capacity macros and the code
        sizes.
    :rtype: dict
    :raises subprocess.CalledProcessError: If building or running fails.

    Example::

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as workdir:
        ...     result = measure_c(sweep_model(1, 3, 1, 1, 1), "c", 1, None, 1, workdir)
        >>> result["stat"], result["repeats"]
        ('min', 1)
    """
    built = build_c(text, template, workdir, T)
    probe = run_c(built["exe"], 2000, core, 1)[0]
    cycles = pick_cycles(
        probe["ns_per_cycle"] * 1e-9, target_s=0.25, lo=2000, hi=5000000
    )
    runs = run_c(built["exe"], cycles, core, repeats)
    ns = [r["ns_per_cycle"] for r in runs]
    return {
        "stat": "min",
        "repeats": repeats,
        "cycles_per_repeat": cycles,
        "ns_per_cycle": min(ns),
        "ns_summary": summarize(ns),
        "first_cycle_ns": min(r["first_cycle_ns"] for r in runs),
        "vars_hash": runs[0]["vars_hash"],
        "sizeof_machine": runs[0]["sizeof_machine"],
        "arena_capacity": runs[0]["arena"],
        "trail_capacity": runs[0]["trail"],
        "storage_bytes": runs[0]["storage_bytes"],
        "text": built["text"],
        "data": built["data"],
        "bss": built["bss"],
        "generate_seconds": built["generate_seconds"],
    }


def flat_family(n):
    """
    Build a region-free ring of ``n`` sibling states (input ``a``).

    The ring is the baseline family for comparing the current C template with the
    one before regions: no regions, one transition per state and one written
    variable.

    :param n: Number of states.
    :type n: int
    :return: DSL text.
    :rtype: str

    Example::

        >>> flat_family(4).count("state S")
        4
    """
    lines = ["input int a;", "def int n = 0;", "state Root {"]
    lines += _ring("S", n, 1, 1, "    ")
    lines[1:1] = ["def int v0 = 0;"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def cmd_e4(args):
    """
    Run experiment 4.

    ``--part speed`` measures the sweep models in generated C, ``capacity`` reads
    the default capacity macros of a model grid from the generated header without
    compiling, and ``baseline`` compares the current C template with an earlier one
    (``--old-template``) on region-free rings.

    :param args: Parsed command line with ``out``, ``core``, ``repeats``, ``part``
        and ``old_template``.
    :type args: argparse.Namespace
    :return: ``None``.
    :rtype: None
    :raises SystemExit: If ``baseline`` is requested without ``--old-template``.

    Example::

        $ python tools/measure_region_performance.py e4 --out data/e4.jsonl --core 3 --part speed capacity
    """
    pin_core(args.core)
    writer = Writer(args.out, {"experiment": "e4", "engine": "generated_c"})
    parts = set(args.part)
    if "speed" in parts:
        points = []
        for name, values in C_SWEEPS.items():
            for value in values:
                params = dict(BASE)
                params[name] = value
                if params["T"] > params["S"] - 1:
                    continue
                points.append((name, params))
        for value in [1, 2, 3, 4, 5, 6, 8, 10, 12]:
            params = dict(BASE)
            params.update(D=value, R=1)
            points.append(("D_chain", params))
        for name, params in points:
            with tempfile.TemporaryDirectory() as workdir:
                res = measure_c(
                    sweep_model(**params),
                    "c",
                    params["T"],
                    args.core,
                    args.repeats,
                    workdir,
                )
            counts = count_model(load_model(sweep_model(**params)))
            writer.write(part="speed", sweep=name, model=params, counts=counts, **res)
    if "capacity" in parts:
        for R in (1, 2, 4, 8, 16, 32, 64):
            for S in (3, 8, 32):
                for D in (1, 2, 4):
                    if R == 1 and D == 1:
                        pass
                    params = dict(BASE)
                    params.update(R=R, S=S, D=D, T=min(2, S - 1))
                    with tempfile.TemporaryDirectory() as workdir:
                        out = os.path.join(workdir, "c")
                        generate_with_cli(sweep_model(**params), "c", out)
                        header = open(os.path.join(out, "machine.h")).read()
                    macros = {}
                    for key in ("ARENA_CAPACITY", "TRAIL_CAPACITY"):
                        found = re.search(
                            r"#define ROOT_MACHINE_%s (\d+)" % key, header
                        )
                        macros[key.lower()] = int(found.group(1))
                    counts = count_model(load_model(sweep_model(**params)))
                    writer.write(part="capacity", model=params, counts=counts, **macros)
    if "baseline" in parts:
        if not args.old_template:
            raise SystemExit("--old-template is required for the baseline part")
        for n in (4, 16, 64):
            for tag, template in (("new", "c"), ("old", args.old_template)):
                with tempfile.TemporaryDirectory() as workdir:
                    res = measure_c(
                        flat_family(n), template, 1, args.core, args.repeats, workdir
                    )
                writer.write(part="baseline", family="flat", n=n, template=tag, **res)


# ----------------------------------------------------------------------------
# Fits
# ----------------------------------------------------------------------------


def linear_fit(xs, ys):
    """
    Fit ``y = a + b x`` by least squares.

    :param xs: Abscissae, at least two distinct values.
    :type xs: list
    :param ys: Ordinates, as many as ``xs``.
    :type ys: list
    :return: ``intercept``, ``slope`` and ``r2``.
    :rtype: dict
    :raises ZeroDivisionError: If all abscissae are equal.

    Example::

        >>> {k: round(v, 6) for k, v in linear_fit([1, 2, 3], [2, 4, 6]).items()}
        {'intercept': 0.0, 'slope': 2.0, 'r2': 1.0}
    """
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return {
        "intercept": intercept,
        "slope": slope,
        "r2": 1 - ss_res / ss_tot if ss_tot else 1.0,
    }


def poly_fit(xs, ys, degree):
    """
    Fit a polynomial by least squares (normal equations, no dependencies).

    The normal equations are solved by Gauss-Jordan elimination with partial
    pivoting. They are ill-conditioned for high degrees and wide abscissae; the tool
    only uses degree two.

    :param xs: Abscissae.
    :type xs: list
    :param ys: Ordinates.
    :type ys: list
    :param degree: Polynomial degree.
    :type degree: int
    :return: ``coefficients`` from the constant term up and ``r2``.
    :rtype: dict
    :raises ZeroDivisionError: If the system is singular (fewer distinct abscissae
        than ``degree + 1``).

    Example::

        >>> fit = poly_fit([1, 2, 3, 4], [1, 4, 9, 16], 2)
        >>> [round(c, 6) + 0.0 for c in fit["coefficients"]], round(fit["r2"], 6)
        ([0.0, 0.0, 1.0], 1.0)
    """
    n = degree + 1
    mat = [
        [sum(x ** (i + j) for x in xs) for j in range(n)]
        + [sum(y * x**i for x, y in zip(xs, ys))]
        for i in range(n)
    ]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(mat[r][col]))
        mat[col], mat[pivot] = mat[pivot], mat[col]
        for r in range(n):
            if r != col:
                factor = mat[r][col] / mat[col][col]
                mat[r] = [a - factor * b for a, b in zip(mat[r], mat[col])]
    coef = [mat[i][n] / mat[i][i] for i in range(n)]
    fit = [sum(c * x**k for k, c in enumerate(coef)) for x in xs]
    my = sum(ys) / len(ys)
    ss_res = sum((y - f) ** 2 for y, f in zip(ys, fit))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return {"coefficients": coef, "r2": 1 - ss_res / ss_tot if ss_tot else 1.0}


def power_fit(xs, ys):
    """
    Fit ``y = c x^k`` on log-log axes.

    :param xs: Positive abscissae.
    :type xs: list
    :param ys: Positive ordinates.
    :type ys: list
    :return: ``exponent``, ``coefficient`` and ``r2`` on log axes.
    :rtype: dict
    :raises ValueError: If a value is not positive.

    Example::

        >>> {k: round(v, 6) for k, v in power_fit([1, 2, 4], [2, 16, 128]).items()}
        {'exponent': 3.0, 'coefficient': 2.0, 'r2': 1.0}
    """
    fit = linear_fit([math.log(x) for x in xs], [math.log(y) for y in ys])
    return {
        "exponent": fit["slope"],
        "coefficient": math.exp(fit["intercept"]),
        "r2": fit["r2"],
    }


def _rows(path):
    """
    Read a JSON Lines file into a list of dictionaries, skipping blank lines.

    :param path: File to read.
    :type path: str
    :return: One dictionary per non-empty line.
    :rtype: list
    """
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def cmd_fit(args):
    """
    Fit the sweeps in the data directory.

    For each of ``e2.jsonl``, ``e3.jsonl`` and ``e4.jsonl`` that exists, and for
    every sweep in it with at least three points, a linear, a quadratic and a power
    fit are computed and written to one JSON file keyed ``<experiment>/<sweep>``.

    :param args: Parsed command line with ``data_dir`` and ``out``.
    :type args: argparse.Namespace
    :return: ``None``.
    :rtype: None

    Example::

        $ python tools/measure_region_performance.py fit --data-dir data --out data/fits.json
    """
    result = {}
    for exp, key in (
        ("e2", "seconds_per_cycle"),
        ("e3", "seconds_per_cycle"),
        ("e4", "ns_per_cycle"),
    ):
        path = os.path.join(args.data_dir, exp + ".jsonl")
        if not os.path.exists(path):
            continue
        rows = [r for r in _rows(path) if r.get("part", "speed") == "speed"]
        for sweep in sorted({r["sweep"] for r in rows}):
            group = [r for r in rows if r["sweep"] == sweep]
            axis = sweep[0] if sweep[0] != "D" else "D"
            xs = [r["model"][axis] for r in group]
            ys = [r[key] for r in group]
            if len(xs) < 3:
                continue
            result["%s/%s" % (exp, sweep)] = {
                "points": len(xs),
                "linear": linear_fit(xs, ys),
                "quadratic": poly_fit(xs, ys, 2),
                "power": power_fit(xs, ys),
            }
    with open(args.out, "w") as handle:
        json.dump(result, handle, indent=1, sort_keys=True)
        handle.write("\n")


def build_parser():
    """
    Build the command line parser.

    The parser has one sub-command per experiment (``e1`` .. ``e4``) and ``fit``.
    The description is the first paragraph of the module docstring, so keep that
    paragraph stable: it is part of the ``--help`` output.

    :return: Parser.
    :rtype: argparse.ArgumentParser

    Example::

        >>> build_parser().parse_args(["fit", "--data-dir", "d", "--out", "o"]).command
        'fit'
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("e1", help="model size and equivalence")
    p.add_argument("--out", required=True)
    p.add_argument("--cycles", type=int, default=200)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--max-flat-transitions", type=int, default=25000)
    p.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="timed batches per model and form; 0 skips timing",
    )
    p.add_argument("--core", type=int, default=None)
    p.set_defaults(func=cmd_e1)
    for name, func in (("e2", cmd_e2), ("e3", cmd_e3)):
        p = sub.add_parser(name, help="time per cycle (%s)" % name)
        p.add_argument("--out", required=True)
        p.add_argument("--core", type=int, default=None)
        p.add_argument("--repeats", type=int, default=7)
        p.add_argument(
            "--only",
            nargs="*",
            default=None,
            help="sweep names: R S T V D_chain D_branch",
        )
        if name == "e3":
            p.add_argument(
                "--sim-data",
                default=None,
                help="e2 data file to compare final variables with",
            )
        p.set_defaults(func=func)
    p = sub.add_parser("e4", help="generated C runtime")
    p.add_argument("--out", required=True)
    p.add_argument("--core", type=int, default=None)
    p.add_argument("--repeats", type=int, default=7)
    p.add_argument(
        "--part",
        nargs="+",
        default=["speed", "capacity", "baseline"],
        choices=["speed", "capacity", "baseline"],
    )
    p.add_argument(
        "--old-template",
        default=None,
        help="directory of the earlier c template for the baseline part",
    )
    p.set_defaults(func=cmd_e4)
    p = sub.add_parser("fit", help="least-squares fits over the data files")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_fit)
    return parser


def main(argv=None):
    """
    Entry point.

    :param argv: Arguments, or ``None`` for ``sys.argv``, defaults to ``None``.
    :type argv: Optional[list]
    :return: Exit code, always ``0``; failures raise.
    :rtype: int

    Example::

        $ python tools/measure_region_performance.py --help
    """
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
