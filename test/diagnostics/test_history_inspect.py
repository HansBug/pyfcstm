"""Inspect reports on history models describe the model as written.

History lowering adds variables, gate states, route initials, exit actions and
restore conditions.  None of them may reach an inspect report: its findings,
statistics and metrics -- with or without the verify run -- must be those of
the same model written without history, and only the defaults a history entry
reaches may change reachability.
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


def _report(text, **options):
    machine, diagnostics = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(text, "state_machine_dsl"), collect=True
    )
    return inspect_model(machine, model_diagnostics=diagnostics, **options)


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


VERIFY_STRUCTURAL = {"enable_verify": True}
VERIFY_SMT = {"enable_verify": True, "max_complexity_tier": "smt_linear"}

# Shapes where analysing the lowered machine used to change a finding.
COUNTEREXAMPLES = {
    # the guards of initials that lowering extends
    "owner-initial-guards": """
    def int x = 0;
    state R {
        state Off;
        state O { state A; state B; [*] -> A : if [1 > 2]; [*] -> B : if [x > 0]; [H] -> A; }
        [*] -> Off;
        Off -> O.[H] :: Resume;
        !O -> Off :: Stop;
    }
    """,
    # route edges escaping an initial livelock
    "initial-livelock": """
    state R {
        state Off;
        state O {
            state A;
            state K { pseudo state P; state Z; [*] -> P; P -> [*]; }
            [*] -> A;
            A -> K :: Go;
            K -> K;
            A -> [*] :: Leave;
            [H*] -> A;
        }
        [*] -> Off;
        Off -> O.[H*] :: Resume;
        O -> Off;
    }
    """,
    # generated exit actions hiding a no-op self transition
    "self-transition": """
    state R {
        state Off;
        state O { state A; state B; [*] -> A; [H] -> A; A -> A; A -> B :: Next; }
        [*] -> Off;
        Off -> O.[H] :: Resume;
        !O -> Off :: Stop;
    }
    """,
    # a gate state counted as a child
    "large-composite": """
    state R {
        state Off;
        state O {
            state c1; state c2; state c3; state c4; state c5; state c6;
            state c7; state c8; state c9; state c10; state c11; state c12;
            [*] -> c1 :: Kick;
            [*] -> c2;
            [H] -> c2;
            c1 -> c2 :: Next;
        }
        [*] -> Off;
        Off -> O.[H] :: Resume;
        !O -> Off :: Stop;
    }
    """,
    # a gate state counted as a level
    "deep-hierarchy": """
    state R {
        state Off;
        state L1 {
            state L2 { state L3 { state L4 { state L5 {
                state L6 { state a; state b; [*] -> a :: Kick; [*] -> b; a -> b :: Next; }
                [*] -> L6; } [*] -> L5; } [*] -> L4; } [*] -> L3; }
            [*] -> L2;
            [H*] -> L2.L3.L4.L5.L6.b;
        }
        [*] -> Off;
        Off -> L1.[H*] :: Resume;
        !L1 -> Off :: Stop;
    }
    """,
    # restore routes in verify's topology and event reachability
    "verify-topology": """
    state R {
        state Off;
        state O { state A; state C; [*] -> A; [H] -> A; C -> A :: Poke; }
        [*] -> Off;
        Off -> O.[H] :: Go;
        !O -> Off :: Stop;
    }
    """,
    # restore conditions in verify's SMT checks
    "verify-smt": """
    def int x = 0;
    def int y = 0;
    state R {
        state Off;
        state O {
            state A; state B; state C;
            [*] -> A : if [x > 0 && x < 0];
            [*] -> B : if [x > 0 || x <= 0];
            [*] -> C;
            [H] -> C;
            A -> B :: Next;
            B -> C :: Go effect { y = y; }
            C -> A :: Back effect { x = x + 1; }
        }
        state P {
            state P1; state P2;
            [*] -> P1 : if [x > 0];
            [*] -> P2 : if [x <= 0];
            [H] -> P1;
            P1 -> P2 :: Flip;
        }
        [*] -> Off;
        Off -> O.[H] :: Resume;
        Off -> P.[H] :: ResumeP;
        Off -> O.[H] : if [y == 0] effect { y = 0; }
        !O -> Off :: Stop;
        !P -> Off :: StopP;
    }
    """,
}


@pytest.mark.unittest
@pytest.mark.parametrize("options", [{}, VERIFY_STRUCTURAL, VERIFY_SMT], ids=["plain", "verify", "verify-smt"])
@pytest.mark.parametrize("name", sorted({**MODELS, **COUNTEREXAMPLES}))
def test_history_adds_or_hides_no_inspect_finding(name, options):
    text = {**MODELS, **COUNTEREXAMPLES}[name]
    plain = _without_history(text)
    assert "[H" not in plain
    assert _summary(_report(text, **options)) == _summary(_report(plain, **options))


@pytest.mark.unittest
@pytest.mark.parametrize("options", [{}, VERIFY_STRUCTURAL], ids=["plain", "verify"])
def test_random_history_models_report_what_their_plain_twins_report(options):
    for text in _random_models(120 if not options else 40, seed=20260930):
        report = _report(text, **options)
        assert _summary(report) == _summary(_report(_without_history(text), **options)), text
        assert "__hist" not in json.dumps(report.to_json()), text


@pytest.mark.unittest
@pytest.mark.parametrize("name", sorted({**MODELS, **COUNTEREXAMPLES}))
def test_reports_name_no_lowered_construct(name):
    payload = _report({**MODELS, **COUNTEREXAMPLES}[name], **VERIFY_STRUCTURAL).to_json()
    assert "__hist" not in json.dumps(payload)
    kinds = {item["target_history"] for item in payload["transitions"]}
    assert kinds - {None} and kinds <= {None, "shallow", "deep"}


@pytest.mark.unittest
def test_transition_records_mark_history_entries():
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
    report = _report(text)
    (entry,) = [t for t in report.transitions if t.target_history is not None]
    assert (entry.to_path, entry.target_history, entry.effect) == ("R.O", "shallow", "n = n + 1;")
    owner = {state.path: state for state in report.states}["R.O"]
    assert [(item["target"], item["guard"]) for item in owner.initial_targets] == [
        ("R.O.A", "x > 0"),
        ("R.O.B", None),
    ]
    assert report.metrics.n_variables == 2


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
    report = _report(text, **VERIFY_STRUCTURAL)
    found = sorted(
        item.refs["state_path"]
        for item in report.diagnostics
        if item.code == "W_UNREACHABLE_STATE"
    )
    assert found == unreachable
    machine = load_state_machine_from_text(text)
    assert list(unreachable_states(machine)) == unreachable
    assert "R.O.Lost" not in report.reachability_graph["R"]


@pytest.mark.unittest
def test_a_deep_default_skips_the_initials_on_its_path():
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
    reachable = set(report.reachability_graph["R"])
    assert {"R.O.W", "R.O.W.W2"} <= reachable and "R.O.W.W1" not in reachable
    found = [item.refs["state_path"] for item in report.diagnostics if item.code == "W_UNREACHABLE_STATE"]
    assert found == ["R.O.W.W1", "R.O.W.W3"]
    machine = load_state_machine_from_text(text)
    assert list(unreachable_states(machine)) == ["R.O.W.W1", "R.O.W.W3"]


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
