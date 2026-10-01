"""Random history models checked against an independent history oracle.

Each generated model mixes history with the FCSTM features history has to
coexist with: pseudo states, guards and effects, ``-> [*]`` exit chains,
evented and guarded initial transitions, combo triggers, forced transitions,
several events per cycle, candidates that fail validation and initial
transitions that target a history.  Three checks run on every cycle:

* **oracle** -- history is recomputed from the committed trace with the UML
  rule "an owner's record is its configuration when it is exited", and every
  committed history entry must enter exactly what that record (or the
  default) prescribes.  The oracle never reads the lowered variables.
* **invariants** -- no restore survives a stable point, and the lowered record
  of every inactive owner agrees with the oracle.
* **transparency** -- keeping the declarations but making every target an
  ordinary entry is indistinguishable from dropping the declarations, and the
  exported plain DSL behaves exactly like the model it came from.
"""

import random
import re

import pytest

from pyfcstm.dsl import EXIT_STATE, INIT_STATE
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeDfsError


class _Node:
    def __init__(self, name, parent, pseudo=False):
        self.name, self.parent, self.pseudo = name, parent, pseudo
        self.children, self.history, self.lines = [], {}, []

    @property
    def composite(self):
        return bool(self.children)


def _generate(rng, max_depth=3):
    counter = [0]

    def name(prefix="S"):
        counter[0] += 1
        return "%s%d" % (prefix, counter[0])

    def build(node, depth):
        if depth < max_depth and (depth == 0 or rng.random() < 0.55):
            for _ in range(rng.randint(2 if depth == 0 else 1, 3)):
                child = _Node(name(), node)
                node.children.append(child)
                build(child, depth + 1)
            if rng.random() < 0.35:
                node.children.append(_Node(name("P"), node, pseudo=True))

    root = _Node("R", None)
    build(root, 0)

    def stable(node):
        return [c for c in node.children if not c.pseudo]

    def declare(node):
        if not node.composite:
            return
        for child in node.children:
            declare(child)
        if node.parent is not None and rng.random() < 0.7:
            for kind in rng.choice([["H"], ["H*"], ["H", "H*"]]):
                if kind == "H":
                    node.history[kind] = rng.choice(stable(node)).name
                else:
                    path, current = [], node
                    while current.composite and (not path or rng.random() < 0.6):
                        current = rng.choice(stable(current))
                        path.append(current.name)
                    node.history[kind] = ".".join(path)

    declare(root)

    def target(node):
        return rng.choice([node.name] + ["%s.[%s]" % (node.name, h) for h in node.history])

    def guard(initial=False):
        if initial and rng.random() < 0.6:
            return "[z == %d]" % rng.randint(0, 1)
        return "[%s == %d]" % (rng.choice("xy"), rng.randint(0, 2))

    def effect():
        return rng.choice(["", "", " effect { x = (x + 1) % 3; }", " effect { y = y + 1; }"])

    def connect(node):
        if not node.composite:
            return
        for child in node.children:
            connect(child)
        initials = []
        for _ in range(rng.choice([1, 1, 2])):
            child = rng.choice(node.children)
            form = rng.random()
            if form < 0.2:
                initials.append("[*] -> %s : if %s;" % (target(child), guard(initial=True)))
            elif form < 0.35:
                initials.append("[*] -> %s :: %s;" % (target(child), name("go")))
            else:
                initials.append("[*] -> %s%s" % (target(child), effect() or ";"))
        if rng.random() < 0.6:
            initials.append("[*] -> %s;" % rng.choice(stable(node)).name)
        node.lines.extend(initials)
        for source in node.children:
            if not source.composite and not source.pseudo and rng.random() < 0.3:
                node.lines.append("%s -> %s :: %s effect { z = 1 - z; }" % (source.name, source.name, name("tz")))
            for _ in range(rng.choice([0, 1, 1, 2]) if not source.pseudo else rng.choice([1, 2])):
                chosen = rng.choice(node.children)
                to = "[*]" if rng.random() < 0.15 else target(chosen)
                roll = rng.random()
                if source.pseudo:
                    trigger = rng.choice(["", " : if %s" % guard()])
                elif source.composite and roll < 0.45:
                    trigger = " :: %s" % name("e")
                    if to != "[*]" and rng.random() < 0.8:
                        node.lines.append("!%s -> %s%s;" % (source.name, to, trigger))
                        continue
                elif roll < 0.55:
                    trigger = " :: %s" % name("e")
                elif roll < 0.7:
                    trigger = " :: %s + %s" % (name("e"), guard())
                else:
                    trigger = " : if %s" % guard()
                node.lines.append("%s -> %s%s%s" % (source.name, to, trigger, effect() or ";"))

    connect(root)

    def text(node, indent=""):
        keyword = "pseudo state" if node.pseudo else "state"
        if not node.composite:
            return "%s%s %s;\n" % (indent, keyword, node.name)
        body = "".join(text(c, indent + "    ") for c in node.children)
        body += "".join("%s    [%s] -> %s;\n" % (indent, h, d) for h, d in node.history.items())
        body += "".join("%s    %s\n" % (indent, line) for line in node.lines)
        return "%sstate %s {\n%s%s}\n" % (indent, node.name, body, indent)

    return "def int x = 0;\ndef int y = 0;\ndef int z = 0;\n" + text(root)


def _plain(text, keep_declarations):
    text = re.sub(r"\.\[H\*?\]", "", text)
    if not keep_declarations:
        text = re.sub(r"^\s*\[H\*?\] -> [\w.]+;\n", "", text, flags=re.M)
    return text


def _events(machine):
    return sorted({t.event.path_name for s in machine.walk_states() for t in s.transitions if t.event})


def _script(machine, rng, cycles):
    """Event script biased towards events declared on the active path."""
    events = _events(machine)
    runtime = SimulationRuntime(machine)
    runtime.cycle()
    script = []
    for _ in range(cycles):
        if runtime.is_ended:
            break
        current = ".".join(runtime.current_state.path)
        live = [e for e in events if (current + ".").startswith(e.rsplit(".", 1)[0] + ".")]
        pool = live if live and rng.random() < 0.85 else events
        pick = []
        if pool and rng.random() < 0.9:
            pick = rng.sample(pool, min(len(pool), rng.choice([1, 1, 1, 2])))
        if events and rng.random() < 0.35:
            pick = sorted(set(pick) | {rng.choice(events)})
        script.append(pick)
        runtime.cycle(pick)
    return script


def _run(machine, script):
    runtime = SimulationRuntime(machine)
    yield runtime, None, runtime.cycle(trace=True)
    for events in script:
        if runtime.is_ended:
            return
        before = tuple(runtime.current_state.path)
        yield runtime, before, runtime.cycle(events, trace=True)


def _user_view(runtime, result):
    trace = [
        (e.kind, e.state_path, tuple(sorted((k, v) for k, v in e.vars.items() if not k.startswith("__hist_"))))
        for e in result.trace
        if e.kind in ("state_enter", "state_exit") and not e.state_path[-1].startswith("__hist_")
    ]
    return (
        tuple(runtime.current_state.path) if not runtime.is_ended else None,
        tuple(sorted((k, v) for k, v in runtime.vars.items() if not k.startswith("__hist_"))),
        result.consumed_events,
        result.delta,
        tuple(trace),
    )


def _trace_label(state, transition):
    """The committed-trace address of an edge: ``state::index::from->to``."""
    edges = state.init_transitions if transition.from_state is INIT_STATE else state.transitions_from
    index = next(i for i, item in enumerate(edges) if item is transition)
    to = "[*]" if transition.to_state is EXIT_STATE else transition.to_state
    return "%s::%d::%s->%s" % (".".join(state.path), index, transition.from_state, to)


def _history_entries(machine):
    owners = {owner.owner_path for owner in machine.history_owners}
    entries = {}
    for state in machine.walk_states():
        for transition in state.transitions:
            if transition.target_history is None:
                continue
            owner = state.substates[transition.to_state].path
            if owner in owners:
                source = state if transition.from_state is INIT_STATE else state.substates[transition.from_state]
                entries[_trace_label(source, transition)] = (owner, transition.target_history)
    return entries


def _check(text, script, stats):
    machine = load_state_machine_from_text(text)
    owners = {owner.owner_path: owner for owner in machine.history_owners}
    entries = _history_entries(machine)
    oracle = {path: None for path in owners}
    for runtime, before, result in _run(machine, script):
        entered = set()
        trace = list(result.trace)
        for i, item in enumerate(trace):
            if item.kind == "state_enter":
                entered.add(item.state_path)
            elif item.kind == "state_exit" and item.state_path in owners:
                owner = item.state_path
                if owner not in entered and before is not None and before[: len(owner)] == owner:
                    oracle[owner] = before[len(owner):]
                    stats["records"] += 1
            elif item.kind == "transition" and item.transition_label in entries:
                owner, kind = entries[item.transition_label]
                record = oracle[owner]
                defaults = owners[owner].defaults
                if kind == "deep":
                    want, exact = (record, True) if record is not None else (defaults["deep"], False)
                else:
                    want, exact = (record[:1] if record is not None else defaults["shallow"]), False
                chain = [x.state_path for x in trace[i + 1:] if x.kind == "state_enter"]
                expect = [owner] + [owner + want[:k] for k in range(1, len(want) + 1)]
                assert (chain if exact else chain[: len(expect)]) == expect, (
                    "restore of %s (%s, record %s): entered %s, expected %s"
                    % (".".join(owner), kind, record, chain, expect)
                )
                stats["restores"] += 1
        for path, owner in owners.items():
            assert runtime.vars[owner.goto_variable] == 0
            active = not runtime.is_ended and tuple(runtime.current_state.path)[: len(path)] == path
            if not active:
                assert owner.decode(runtime.vars[owner.record_variable]) == oracle[path]
        stats["cycles"] += 1

    exported = load_state_machine_from_text(str(machine.to_ast_node()))
    assert [_user_view(r, x) for r, _, x in _run(exported, script)] == [
        _user_view(r, x) for r, _, x in _run(machine, script)
    ]

    declared = load_state_machine_from_text(_plain(text, keep_declarations=True))
    plain = load_state_machine_from_text(_plain(text, keep_declarations=False))
    assert [_user_view(r, x) for r, _, x in _run(declared, script)] == [
        _user_view(r, x) for r, _, x in _run(plain, script)
    ]


@pytest.mark.unittest
@pytest.mark.parametrize("seed", [11, 23, 37])
def test_random_history_models_agree_with_the_oracle(seed):
    rng = random.Random(seed)
    stats = {"models": 0, "skipped": 0, "cycles": 0, "records": 0, "restores": 0}
    for _ in range(40):
        text = _generate(rng)
        try:
            machine = load_state_machine_from_text(text)
            script = _script(machine, rng, 30)
            _check(text, script, stats)
        except SimulationRuntimeDfsError:
            # A generated model can loop through pseudo states or exceed the
            # search limits whether or not it uses history.
            stats["skipped"] += 1
            continue
        stats["models"] += 1
    assert stats["models"] >= 30, stats
    assert stats["restores"] >= 20 and stats["records"] >= 20, stats
