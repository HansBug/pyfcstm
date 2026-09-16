"""Readable diagnostic reports preserve execution facts and call context."""

import json

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SequenceInput, SimulationRuntime

pytestmark = pytest.mark.unittest


def machine(source, **kwargs):
    return SimulationRuntime(load_state_machine_from_text(source), **kwargs)


def test_no_candidates_still_has_detached_call_context():
    runtime = machine(
        """
        input int sensor; param int gain = 2; output int reading = 0;
        state Root { state A { during { reading = sensor * gain; } } [*] -> A; }
    """,
        input_source={"sensor": SequenceInput([3, 5, 7])},
    )
    runtime.cycle()
    report = runtime.cycle(diagnostics=True).diagnostics
    assert report.decisions == ()
    assert report.input_events == ()
    assert report.inputs == {"sensor": 5}
    assert report.parameters == {"gain": 2}
    assert report.vars_before == {"reading": 6}
    assert report.vars_after == {"reading": 10}
    data = json.loads(json.dumps(report.to_dict()))
    assert data["vars_after"] == {"reading": 10}
    data["inputs"]["sensor"] = 999
    with pytest.raises(TypeError):
        report.vars_after["reading"] = 999
    runtime.cycle()
    assert report.inputs == {"sensor": 5}
    assert report.vars_after == {"reading": 10}
    assert "No candidate checks" in str(report)
    assert "'reading': 10" in str(report)


def test_committed_loop_occurrences_and_distinct_snapshots_are_never_folded():
    runtime = machine("""
        control int x = 0;
        state Root {
            state A; pseudo state P; state Done;
            [*] -> A; A -> P;
            P -> P : if [x < 3] effect { x = x + 1; }
            P -> Done : if [x >= 3];
        }
    """)
    runtime.cycle()
    result = runtime.cycle(trace=True, diagnostics=True)
    report = result.diagnostics
    text = str(report)
    committed = [d for d in report.decisions if d.committed]
    assert [d.transition_label for d in committed] == [
        e.transition_label for e in result.trace if e.kind == "transition"
    ]
    loops = [d for d in committed if d.guard == "x < 3"]
    assert [d.vars["x"] for d in loops] == [0, 1, 2]
    evidence = text.split("Candidate evidence", 1)[1]
    for d in loops:
        assert "#%s " % d.id in evidence
    for value in [0, 1, 2, 3]:
        assert "'x': %s" % value in text


COMBO = """
input int sensor;
param int limit = 10;
control int score = 0;
output int reading = 0;
state Root {
    state Start { exit { score = score + 1; } }
    state Target {
        enter { score = score + 10000; }
        state Good { enter { score = score + 1000; } }
        [*] -> Good : if [reading >= limit];
    }
    state Fallback { enter { score = score + 100; } }
    [*] -> Start;
    Start -> Target :: A + B effect { reading = sensor; score = score + 10; }
    Start -> Fallback :: A effect { score = score + 20; }
}
"""


@pytest.mark.parametrize(
    "sensor, events, target, score, reading",
    [
        (12, ["Root.Start.A"], "Fallback", 121, 0),
        (3, ["Root.Start.A", "Root.Start.B"], "Fallback", 121, 0),
        (12, ["Root.Start.A", "Root.Start.B"], "Target.Good", 11011, 12),
    ],
)
def test_combo_report_explains_authored_path_and_committed_boundary(
    sensor, events, target, score, reading
):
    runtime = machine(COMBO, input_source={"sensor": sensor})
    runtime.cycle()
    report = runtime.cycle(events, diagnostics=True).diagnostics
    text = str(report)
    assert report.input_events == tuple(events)
    assert report.vars_before == {"score": 0, "reading": 0}
    assert report.vars_after == {"score": score, "reading": reading}
    assert ".".join(report.state_after) == "Root." + target
    assert "Root.Start -> Root.Target [combo: A + B]" in text
    assert "__combo_" not in text
    assert "__combo_" in report.to_text(verbose=True)
    origin = report.decisions[0].combo_origins[0]
    assert origin["source_path"] == "Root.Start"
    assert origin["target_path"] == "Root.Target"
    assert origin["trigger"] == "A + B"
    with pytest.raises(TypeError):
        origin["trigger"] = "changed"
    data = report.to_dict()
    data["decisions"][0]["combo_origins"][0]["trigger"] = "changed"
    assert origin["trigger"] == "A + B"
    if sensor == 3:
        guard = next(d for d in report.decisions if d.guard_result is False)
        assert guard.vars == {"score": 10011, "reading": 3}
        assert "10011" in text
        assert "speculative writes were not committed" in text
        focused = report.to_text(check_id=guard.id)
        assert "#%s " % guard.parent_id in focused
        assert "Root.Start -> Root.Target [combo: A + B]" in focused
        assert "folded" in text
        assert "folded" not in report.to_text(verbose=True)
    if target == "Target.Good":
        skipped = next(d for d in report.decisions if d.blocked_by is not None)
        focused = report.to_text(check_id=skipped.id)
        assert "#%s " % skipped.blocked_by in focused
        assert "not evaluated" in focused
        assert "-> None" not in focused


def test_delta_context_and_next_input_are_distinct_from_speculative_values():
    runtime = machine(
        """
        input int sensor; param int limit = 10;
        control int score = 0; output int reading = 0;
        state Root {
            enter { score = score + 100; }
            pseudo state Prepare { enter { score = score + 10; } }
            state Ready { enter { score = score + 1000; } }
            [*] -> Prepare effect { reading = sensor; }
            Prepare -> Ready : if [reading >= limit];
        }
    """,
        input_source={"sensor": SequenceInput([3, 12])},
    )
    first = runtime.cycle(diagnostics=True, trace=True)
    report = first.diagnostics
    assert report.outcome == "delta" and first.trace == ()
    assert report.vars_before == report.vars_after == {"score": 0, "reading": 0}
    assert report.inputs == {"sensor": 3}
    assert "state and persistent values unchanged" in str(report)
    assert any(d.vars["score"] == 110 for d in report.decisions)
    second = runtime.cycle(diagnostics=True).diagnostics
    assert second.inputs == {"sensor": 12}
    assert second.vars_after == {"score": 1110, "reading": 12}
    assert report.inputs == {"sensor": 3}


def test_shared_combo_prefix_keeps_all_authored_origins():
    runtime = machine("""
        state Root {
            state A; state B; state C;
            [*] -> A;
            A -> B :: Go + Left;
            A -> C :: Go + Right;
        }
    """)
    runtime.cycle()
    report = runtime.cycle(["Root.A.Go", "Root.A.Right"], diagnostics=True).diagnostics
    prefix = report.decisions[0]
    assert {r["trigger"] for r in prefix.combo_origins} == {"Go + Left", "Go + Right"}
    assert {r["target_path"] for r in prefix.combo_origins} == {"Root.B", "Root.C"}
    assert "Root.A -> Root.B [combo: Go + Left]" in str(report)
    assert "Root.A -> Root.C [combo: Go + Right]" in str(report)
    assert report.state_after == ("Root", "C")


def test_query_labels_ids_unknowns_and_mutually_exclusive_selectors():
    runtime = machine(COMBO, input_source={"sensor": 3})
    runtime.cycle()
    report = runtime.cycle(
        ["Root.Start.A", "Root.Start.B"], diagnostics=True
    ).diagnostics
    guard = next(d for d in report.decisions if d.guard_result is False)
    for focused in [
        report.to_text(check_id=guard.id),
        report.to_text(check_id=str(guard.id)),
        report.to_text(transition=guard.transition_label),
    ]:
        assert "Root.Start -> Root.Target [combo: A + B]" in focused
        assert "reading >= limit" in focused
    assert "No recorded evidence" in report.to_text(check_id=999)
    with pytest.raises(ValueError, match="either"):
        report.to_text(transition=guard.transition_label, check_id=guard.id)


def test_noop_context_does_not_claim_a_new_sample():
    runtime = machine(
        """
        input int sensor; param int gain = 2; output int reading = 0;
        state Root { state A { enter { reading = sensor * gain; } }
            [*] -> A; A -> [*]; }
    """,
        input_source={"sensor": SequenceInput([3, 5])},
    )
    runtime.cycle()
    ended = runtime.cycle(diagnostics=True).diagnostics
    assert ended.outcome == "terminated"
    assert ended.inputs == {"sensor": 5}
    report = runtime.cycle("ignored event", diagnostics=True).diagnostics
    assert report.outcome == "noop"
    assert report.inputs is None
    assert report.input_events == ()
    assert report.parameters == {"gain": 2}
    assert report.vars_before == report.vars_after == {"reading": 6}
    assert report.to_dict()["inputs"] is None
    assert "not sampled" in str(report)


def test_initial_and_exit_combo_origins_are_preserved():
    runtime = machine("""
        control int x = 1;
        state Root {
            state A;
            [*] -> A : Entry + [x > 0];
            A -> [*] :: Leave + [x > 0];
        }
    """)
    initial = runtime.cycle("Root.Entry", diagnostics=True).diagnostics
    refs = [r for d in initial.decisions for r in d.combo_origins]
    assert all(r["source_path"] == "Root.[*]" for r in refs)
    assert {r["trigger"] for r in refs} == {"Entry + [x > 0]"}
    assert "Root.[*] -> Root.A [combo: Entry + [x > 0]]" in str(initial)
    final = runtime.cycle("Root.A.Leave", diagnostics=True).diagnostics
    assert final.outcome == "terminated"
    refs = [r for d in final.decisions for r in d.combo_origins]
    assert all(r["target_path"] == "[*]" for r in refs)
    assert "Root.A -> [*] [combo: Leave + [x > 0]]" in str(final)


def test_shared_complete_trigger_retains_distinct_terminal_effects():
    runtime = machine("""
        control int x = 0;
        state Root {
            state A; state B; state C;
            [*] -> A;
            A -> B :: Go + Next effect { x = 1; }
            A -> C :: Go + Next effect { x = 2; }
        }
    """)
    runtime.cycle()
    report = runtime.cycle(["Root.A.Go", "Root.A.Next"], diagnostics=True).diagnostics
    refs = [r for d in report.decisions for r in d.combo_origins]
    assert {r["target_path"] for r in refs} == {"Root.B", "Root.C"}
    assert "Shared expanded edge for:" in str(report)
    assert report.vars_after == {"x": 1}
    assert report.state_after == ("Root", "B")


def test_imported_combo_origins_use_parent_paths_and_events(tmp_path):
    from pyfcstm.model import load_state_machine_from_file

    (tmp_path / "child.fcstm").write_text("""
        state Child { state A; state B; [*] -> A; A -> B :: Go + Next; }
    """)
    host = tmp_path / "host.fcstm"
    host.write_text("""
        state Root { import "./child.fcstm" as Worker; [*] -> Worker; }
    """)
    runtime = SimulationRuntime(load_state_machine_from_file(host))
    runtime.cycle()
    report = runtime.cycle(
        ["Root.Worker.A.Go", "Root.Worker.A.Next"], diagnostics=True
    ).diagnostics
    refs = [r for d in report.decisions for r in d.combo_origins]
    assert {r["source_path"] for r in refs} == {"Root.Worker.A"}
    assert {r["target_path"] for r in refs} == {"Root.Worker.B"}
    assert report.state_after == ("Root", "Worker", "B")
    assert "child.fcstm" in report.to_text(verbose=True)
