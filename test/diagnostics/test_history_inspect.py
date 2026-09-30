"""Inspect reports on history models describe what the author wrote.

History lowering adds variables, gate states, route initials and restore
conditions.  Inspect findings, statistics and metrics must be those of the same
model written without history; only the defaults a history entry reaches may
change reachability.
"""

import dataclasses
import json
import random
import re
from pathlib import Path

import pytest

import pyfcstm.diagnostics
from pyfcstm.diagnostics.inspect import inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
from pyfcstm.verify.topology import unreachable_states

from test.model import test_history_lowering as lowering
from test.model.test_history_lowering import BLOCKED, BLOCKED_INITIALS, WASHER

EVENTED = """
state R {
    state Off;
    state O {
        event Kick;
        state A;
        state B;
        [*] -> A :: Kick;
        [H] -> B;
        A -> B :: Next;
    }
    [*] -> Off;
    Off -> O :: Fresh;
    Off -> O.[H] :: Resume;
    !O -> Off :: Stop;
}
"""

MODELS = {
    "washer": WASHER,
    "blocked-merged": BLOCKED % BLOCKED_INITIALS["merged"],
    "blocked-gated": BLOCKED % BLOCKED_INITIALS["gated"],
    "evented": EVENTED,
}


def _without_history(text):
    """The same model with every history construct blanked out in place.

    Replacing with spaces keeps every other span on the same line and column.
    """
    blank = lambda match: " " * len(match.group(0))  # noqa: E731
    text = re.sub(r"\[H\*?\] -> [\w.]+;", blank, text)
    return re.sub(r"\.\[H\*?\]", blank, text)


def _report(text):
    machine, diagnostics = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(text, "state_machine_dsl"), collect=True
    )
    return inspect_model(machine, model_diagnostics=diagnostics)


def _findings(report):
    out = []
    for item in report.diagnostics:
        if "HISTORY" in item.code:
            continue
        refs = dict(item.refs)
        if isinstance(refs.get("forced_origin"), str):
            # the forced declaration's own text still spells its history target
            refs["forced_origin"] = re.sub(r"\.\[H\*?\]", "", refs["forced_origin"])
        out.append((item.code, item.message, repr(sorted(refs.items()))))
    return sorted(out)


def _summary(report):
    return (
        _findings(report),
        dataclasses.asdict(report.structure_statistics),
        dataclasses.asdict(report.metrics),
    )


_GUARDS = ["x > 0", "1 > 2", "y == 3", "x + y > 1", "true"]


def _random_model(rng):
    """A random model whose history defaults follow its unconditional initials.

    Defaults its plain twin also reaches keep reachability identical, so the
    whole inspect summary of the model and of its twin must agree.
    """
    counter = [0]

    def fresh(prefix):
        counter[0] += 1
        return "%s%d" % (prefix, counter[0])

    def composite(name, depth, is_root, indent):
        pad = indent + "    "
        body, paths, kids = [], {}, []
        for _ in range(rng.randint(2, 3)):
            child = fresh("S")
            if depth < 2 and rng.random() < 0.45:
                text, declared, path = composite(child, depth + 1, False, pad)
                body.append(text)
                kids.append((child, declared))
                paths[child] = [child] + path
            else:
                body.append("%sstate %s;" % (pad, child))
                kids.append((child, ()))
                paths[child] = [child]
        names = [child for child, _ in kids]
        # a guarded or evented initial before the unconditional one, or an
        # unconditional initial with an effect, or a plain one
        plain = rng.choice(names)
        shape = rng.random()
        if shape < 0.25:
            body.append("%s[*] -> %s : if [%s];" % (pad, rng.choice(names), rng.choice(_GUARDS)))
        elif shape < 0.4:
            body.append("%s[*] -> %s :: %s;" % (pad, rng.choice(names), fresh("e")))
        if shape < 0.4 or shape >= 0.55:
            body.append("%s[*] -> %s;" % (pad, plain))
        else:
            body.append("%s[*] -> %s effect { y = y + 1; }" % (pad, plain))
        declared = ()
        if not is_root and rng.random() < 0.8:
            declared = tuple(rng.choice([["H"], ["H*"], ["H", "H*"]]))
            for kind in declared:
                path = paths[plain]
                path = path[:1] if kind == "H" else path[: rng.randint(1, len(path))]
                body.append("%s[%s] -> %s;" % (pad, kind, ".".join(path)))
        for source, _ in kids:
            for _ in range(rng.choice([0, 1, 1, 2])):
                target, kinds = rng.choice(kids)
                if kinds and rng.random() < 0.8:
                    target += ".[%s]" % rng.choice(kinds)
                trigger = rng.choice(
                    [
                        ":: %s" % fresh("e"),
                        ": if [%s]" % rng.choice(_GUARDS),
                        ":: %s effect { x = x + 1; }" % fresh("e"),
                    ]
                )
                written = source
                if len(paths[source]) > 1:
                    # a composite source is written as a forced transition,
                    # which cannot carry an effect
                    written = "!" + source
                    trigger = trigger.split(" effect")[0]
                body.append("%s%s -> %s %s;" % (pad, written, target, trigger))
        text = "%sstate %s {\n%s\n%s}" % (indent, name, "\n".join(body), indent)
        return text, declared, paths[plain]

    text, _, _ = composite("R", 0, True, "")
    return "def int x = 0;\ndef int y = 0;\n" + text


def _random_models(count, seed):
    rng = random.Random(seed)
    models = []
    while len(models) < count:
        text = _random_model(rng)
        if ".[H" in text:
            models.append(text)
    return models


@pytest.mark.unittest
@pytest.mark.parametrize("name", sorted(MODELS))
def test_lowering_adds_or_hides_no_inspect_finding(name):
    text = MODELS[name]
    plain = _without_history(text)
    assert "[H" not in plain
    assert _summary(_report(text)) == _summary(_report(plain))


@pytest.mark.unittest
def test_random_history_models_report_what_their_plain_twins_report():
    for text in _random_models(120, seed=20260930):
        report = _report(text)
        assert _summary(report) == _summary(_report(_without_history(text))), text
        for item in report.diagnostics:
            assert "__hist" not in item.message, (item.code, item.message)


@pytest.mark.unittest
def test_guard_warnings_on_owner_initials_survive_lowering():
    text = """
    def int x = 0;
    state R {
        state Off;
        state O { state A; state B; [*] -> A : if [1 > 2]; [*] -> B : if [x > 0]; [H] -> A; }
        [*] -> Off;
        Off -> O.[H] :: Resume;
        !O -> Off :: Stop;
    }
    """
    codes = [item.code for item in _report(text).diagnostics]
    assert "W_GUARD_CONST_FALSE" in codes
    assert "W_GUARD_VARS_NEVER_CHANGE" in codes
    assert _summary(_report(text)) == _summary(_report(_without_history(text)))


@pytest.mark.unittest
def test_hidden_variables_count_toward_no_metric():
    text = """
    def int a = 0;
    def int b = 0;
    def int c = 0;
    state R {
        state Off;
        state O { state A; [*] -> A; [H] -> A; A -> A :: Tick effect { a = b + c; } }
        [*] -> Off;
        Off -> O.[H] :: Resume;
        !O -> Off :: Stop;
    }
    """
    report = _report(text)
    assert report.metrics.n_variables == 3
    assert report.metrics.var_to_leaf_ratio == 1.5
    assert "W_HIGH_VAR_TO_LEAF_RATIO" not in {item.code for item in report.diagnostics}
    assert {item.name for item in report.variables} >= {"__hist_O", "__hist_goto"}


@pytest.mark.unittest
def test_structure_statistics_count_only_authored_effects():
    stats = _report(WASHER).structure_statistics
    assert stats == _report(_without_history(WASHER)).structure_statistics
    assert stats.missing_effect_transitions == stats.effect_eligible_transitions


@pytest.mark.unittest
def test_an_evented_initial_is_reported_as_written():
    report = _report(EVENTED)
    owner = {state.path: state for state in report.states}["R.O"]
    authored = [item for item in owner.initial_targets if item.get("history_role") != "route"]
    assert authored == [
        {
            "target": "R.O.A",
            "guard": None,
            "event": "Kick",
            "is_unconditional": False,
            "history_role": "gated",
        }
    ]
    (initial,) = [t for t in report.transitions if t.history_role == "gated"]
    assert (initial.from_path, initial.to_path, initial.event) == ("[*]", "R.O.A", "R.O.Kick")
    (gate,) = [t for t in report.transitions if t.history_role == "gate"]
    assert gate.to_path.startswith("R.O.__hist_gate_")


@pytest.mark.unittest
def test_transition_records_show_authored_guards_and_effects():
    text = """
    def int n = 0;
    def int x = 0;
    state R {
        state Off;
        state O { state A; state B; [*] -> A : if [x > 0]; [*] -> B; [H] -> B; }
        [*] -> Off;
        Off -> O.[H] :: Resume effect { n = n + 1; }
        !O -> Off :: Stop;
    }
    """
    transitions = _report(text).transitions
    (entry,) = [t for t in transitions if t.target_history is not None]
    assert (entry.to_path, entry.target_history, entry.effect) == ("R.O", "shallow", "n = n + 1;")
    merged = [t for t in transitions if t.history_role == "merged"]
    assert [t.guard for t in merged] == ["x > 0", None]
    assert all(t.history_role is None for t in transitions if t.from_path != "[*]")


@pytest.mark.unittest
@pytest.mark.parametrize(
    ["inner", "outer", "unreachable"],
    [
        # a child only a restore route leads to is unreachable; the default is not
        ("[*] -> A; [H] -> Def;", "Off -> O.[H] :: Go;", ["R.O.Lost"]),
        ("[*] -> A; [H*] -> Def;", "Off -> O.[H*] :: Go;", ["R.O.Lost"]),
        # a declared kind no transition enters reaches nothing
        ("[*] -> A; [H] -> Def; [H*] -> Lost;", "Off -> O.[H] :: Go;", ["R.O.Lost"]),
        # without history both are unreachable
        ("[*] -> A;", "Off -> O :: Go;", ["R.O.Def", "R.O.Lost"]),
    ],
)
def test_only_history_defaults_add_reachability(inner, outer, unreachable):
    text = (
        "state R { state Off; state O { state A; state Lost; state Def; %s } "
        "[*] -> Off; %s !O -> Off :: Stop; }" % (inner, outer)
    )
    report = _report(text)
    found = sorted(
        item.refs["state_path"]
        for item in report.diagnostics
        if item.code == "W_UNREACHABLE_STATE"
    )
    assert found == unreachable
    assert list(unreachable_states(load_state_machine_from_text(text))) == unreachable
    assert "R.O.Lost" not in report.reachability_graph["R"]


@pytest.mark.unittest
def test_a_deep_default_reaches_its_whole_path():
    text = """
    state R {
        state Off;
        state O {
            state A;
            state W { state W1; state W2; state W3; [*] -> W1; }
            [*] -> A;
            [H*] -> W.W2;
        }
        [*] -> Off;
        Off -> O.[H*] :: Go;
        !O -> Off :: Stop;
    }
    """
    report = _report(text)
    assert {"R.O.W", "R.O.W.W2"} <= set(report.reachability_graph["R"])
    assert list(unreachable_states(load_state_machine_from_text(text))) == ["R.O.W.W3"]
    found = [item.refs["state_path"] for item in report.diagnostics if item.code == "W_UNREACHABLE_STATE"]
    assert found == ["R.O.W.W3"]


@pytest.mark.unittest
def test_history_defaults_make_their_targets_reachable():
    # Without history, R.O.S1 is only named by the ``[H] -> S1`` default and is
    # unreachable; with history it is the shallow default, so the report drops
    # exactly that warning and adds nothing else.
    text = lowering.TestNestedOwners.TEXT
    lowered = _findings(_report(text))
    plain = _findings(_report(_without_history(text)))
    removed = [item for item in plain if item not in lowered]
    assert [code for code, _, _ in removed] == ["W_UNREACHABLE_STATE"]
    assert "R.O.S1" in removed[0][2]
    assert all(item in plain for item in lowered)


@pytest.mark.unittest
@pytest.mark.parametrize("name", sorted(MODELS))
def test_history_reports_validate_against_the_shipped_schema(name):
    import jsonschema

    payload = _report(MODELS[name]).to_json()
    schema = json.loads(Path(pyfcstm.diagnostics.__file__).with_name("schema.json").read_text())
    jsonschema.Draft7Validator(schema).validate(payload)
    roles = {item["history_role"] for item in payload["transitions"]}
    assert roles & {"route", "merged", "gated", "gate"}
    assert roles <= {None, "route", "merged", "gated", "gate"}
    kinds = {item["target_history"] for item in payload["transitions"]}
    assert kinds - {None} and kinds <= {None, "shallow", "deep"}
