#!/usr/bin/env python3
"""Differential check of FCSTM history against XState.

This maintenance command generates random statecharts from the semantic subset
FCSTM and XState share -- nested composites, leaves, event-triggered sibling
transitions (forced ``!X -> Y`` for composite sources, FCSTM's spelling of a UML
transition that leaves a composite), external self transitions, and shallow and
deep history with arbitrary defaults -- and runs each one on both engines.
Every transition has its own event and one event is sent per cycle, so
priority rules never come into play.  After every event it compares the active
leaf path and the ordered state exit/entry sequence.

It calls Node.js, so it is not part of the pytest suite.  The XState reference
lives in ``tools/history_xstate``; install it once with
``npm ci --prefix tools/history_xstate``.

Example::

    $ npm ci --prefix tools/history_xstate
    $ python tools/check_history_xstate.py --models 300 --events 60
    models=300 steps=18300 transitions=... restores=... mismatching_models=0
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _REPO_ROOT / "tools" / "history_xstate" / "run_xstate.mjs"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pyfcstm.model import load_state_machine_from_text  # noqa: E402
from pyfcstm.simulate import SimulationRuntime  # noqa: E402


class _Node:
    def __init__(self, name, parent):
        self.name, self.parent, self.children = name, parent, []
        self.path = (parent.path if parent else ()) + (name,)
        self.history = {}  # "H" / "Hs" -> default path
        self.transitions = []  # (source, target, kind, event)
        self.initial = None

    @property
    def id(self):
        return ".".join(self.path)


def _generate(rng, max_depth=3):
    counter = [0]

    def name():
        counter[0] += 1
        return "S%d" % counter[0]

    def build(node, depth):
        if depth < max_depth and (depth == 0 or rng.random() < 0.55):
            for _ in range(rng.randint(1 if depth else 2, 3)):
                child = _Node(name(), node)
                node.children.append(child)
                build(child, depth + 1)
            node.initial = rng.choice(node.children).name

    root = _Node("R", None)
    build(root, 0)
    events = [0]

    def connect(node):
        if not node.children:
            return
        for child in node.children:
            connect(child)
        if node.parent is not None and rng.random() < 0.7:
            for kind in rng.choice([["H"], ["Hs"], ["H", "Hs"]]):
                if kind == "H":
                    node.history[kind] = (rng.choice(node.children).name,)
                else:
                    path, current = [], node
                    while current.children and (not path or rng.random() < 0.6):
                        current = rng.choice(current.children)
                        path.append(current.name)
                    node.history[kind] = tuple(path)
        for source in node.children:
            for _ in range(rng.choice([0, 1, 1, 2])):
                target = source if rng.random() < 0.15 else rng.choice(node.children)
                events[0] += 1
                kind = rng.choice(["plain"] + list(target.history))
                node.transitions.append((source, target, kind, "ev%d" % events[0]))

    connect(root)
    return root


def _fcstm(node, indent=""):
    if not node.children:
        return "%sstate %s;\n" % (indent, node.name)
    body = "".join(_fcstm(c, indent + "    ") for c in node.children)
    body += "%s    [*] -> %s;\n" % (indent, node.initial)
    for kind, default in node.history.items():
        body += "%s    [%s] -> %s;\n" % (indent, "H" if kind == "H" else "H*", ".".join(default))
    for source, target, kind, event in node.transitions:
        to = target.name + {"plain": "", "H": ".[H]", "Hs": ".[H*]"}[kind]
        body += "%s    %s%s -> %s :: %s;\n" % (indent, "!" if source.children else "", source.name, to, event)
    return "%sstate %s {\n%s%s}\n" % (indent, node.name, body, indent)


def _xstate(node):
    return {
        "name": node.name,
        "id": node.id,
        "children": [_xstate(c) for c in node.children],
        "initial": node.initial,
        "on": {},
        "history": [
            {"key": "__" + kind, "kind": "shallow" if kind == "H" else "deep", "target": ".".join(default)}
            for kind, default in node.history.items()
        ],
    }


def _attach_events(root, specs):
    def walk(node):
        for source, target, kind, event in node.transitions:
            to = "#" + target.id + {"plain": "", "H": ".__H", "Hs": ".__Hs"}[kind]
            specs[source.id]["on"][source.id + "." + event] = {"target": to, "reenter": source is target}
        for child in node.children:
            walk(child)

    walk(root)


def _index(spec, out):
    out[spec["id"]] = spec
    for child in spec["children"]:
        _index(child, out)
    return out


def _events(root):
    found = []

    def walk(node):
        for source, _, _, event in node.transitions:
            found.append((source.path, source.id + "." + event))
        for child in node.children:
            walk(child)

    walk(root)
    return found


def _run_fcstm(text, root, rng, count):
    machine = load_state_machine_from_text(text)
    runtime = SimulationRuntime(machine)
    events = _events(root)
    steps, sent = [], []

    def observe(result):
        log = [
            "%s %s" % ("enter" if e.kind == "state_enter" else "exit", ".".join(e.state_path))
            for e in result.trace
            if e.kind in ("state_enter", "state_exit")
        ]
        for owner in machine.history_owners:
            assert runtime.vars[owner.goto_variable] == 0, "a restore survived a stable point"
        steps.append({"leaf": ".".join(runtime.current_state.path), "log": log})

    observe(runtime.cycle(trace=True))
    for _ in range(count):
        current = runtime.current_state.path
        live = [e for p, e in events if current[: len(p)] == p]
        event = rng.choice(live) if live and rng.random() < 0.85 else rng.choice(events)[1]
        sent.append(event)
        observe(runtime.cycle([event], trace=True))
    return steps, sent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--models", type=int, default=300, help="random models to generate")
    parser.add_argument("--events", type=int, default=60, help="events sent to each model")
    parser.add_argument("--seed", type=int, default=20260929, help="random seed")
    parser.add_argument("--check", action="store_true", help="present for consistency with other tools")
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    cases, results, sources = [], [], []
    restores = transitions = 0
    for _ in range(args.models):
        root = _generate(rng)
        if not _events(root):
            continue
        text = _fcstm(root)
        steps, sent = _run_fcstm(text, root, rng, args.events)
        spec = _xstate(root)
        _attach_events(root, _index(spec, {}))
        cases.append({"spec": spec, "events": sent})
        results.append(steps)
        sources.append(text)
        history_events = {s.id + "." + e for s, _, k, e in _walk_transitions(root) if k != "plain"}
        restores += sum(1 for e, s in zip(sent, steps[1:]) if e in history_events and s["log"])
        transitions += sum(1 for s in steps[1:] if s["log"])

    with tempfile.TemporaryDirectory() as workdir:
        cases_path = Path(workdir) / "cases.json"
        out_path = Path(workdir) / "results.json"
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        subprocess.run(["node", str(_RUNNER), str(cases_path), str(out_path)], check=True)
        reference = json.loads(out_path.read_text(encoding="utf-8"))

    mismatches = 0
    for index, (ours, theirs) in enumerate(zip(results, reference)):
        for step, (a, b) in enumerate(zip(ours, theirs)):
            if a != b:
                mismatches += 1
                if mismatches <= 3:
                    print("MISMATCH model %d step %d" % (index, step))
                    print(sources[index])
                    print(" fcstm :", a)
                    print(" xstate:", b)
                break
    print(
        "models=%d steps=%d transitions=%d restores=%d mismatching_models=%d"
        % (len(cases), sum(len(r) for r in results), transitions, restores, mismatches)
    )
    return 1 if mismatches else 0


def _walk_transitions(node):
    yield from node.transitions
    for child in node.children:
        yield from _walk_transitions(child)


if __name__ == "__main__":
    sys.exit(main())
