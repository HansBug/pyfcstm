"""Candidate evidence through the public simulator API."""

import json
from dataclasses import FrozenInstanceError

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

CANDIDATES = """
control int x = 0;
state Root {
    state A;
    state Blocked {
        enter { x = 100; }
        state Inner;
        [*] -> Inner : if [x < 0];
    }
    state B { enter { x = 1; } }
    state C;
    [*] -> A;
    A -> Blocked :: Go;
    A -> B :: Go;
    A -> C :: Go;
}
"""


def runtime(source=CANDIDATES, **kwargs):
    return SimulationRuntime(load_state_machine_from_text(source), **kwargs)


def test_rejected_successor_has_evidence_without_polluting_committed_trace():
    machine = runtime()
    assert machine.cycle().diagnostics is None
    result = machine.cycle("Root.A.Go", trace=True, diagnostics=True)
    report = result.diagnostics
    assert report.outcome == "cycle"
    assert report.cycle_count == 2
    assert report.state_before == ("Root", "A")
    assert report.state_after == ("Root", "B")
    assert [e.transition_label for e in result.trace if e.kind == "transition"] == [
        "Root.A::1::A->B"
    ]
    rejected = [d for d in report.decisions if d.outcome == "successor_rejected"]
    assert rejected
    for decision in rejected:
        assert decision.transition_label == "Root.A::0::A->Blocked"
        assert decision.event_result is True
        assert decision.successor_result is False
        assert not decision.committed
        children = [d for d in report.decisions if d.parent_id == decision.id]
        assert any(d.guard_result is False and d.vars["x"] == 100 for d in children)
    committed = [d for d in report.decisions if d.committed]
    assert [d.transition_label for d in committed] == ["Root.A::1::A->B"]
    skipped = [d for d in report.decisions if d.outcome == "not_evaluated"]
    assert skipped
    assert all(d.guard_result is None and d.blocked_by is not None for d in skipped)
    assert len({d.id for d in report.decisions}) == len(report.decisions)
    assert "successor_rejected" in str(report)
    assert "x < 0" in report.to_text(verbose=True)
    assert "100" in report.to_text(transition="Root.A::0::A->Blocked", verbose=True)
    assert "No recorded evidence" in report.to_text(transition="unknown")
    data = json.loads(json.dumps(report.to_dict()))
    data["decisions"][0]["vars"]["x"] = 999
    assert report.decisions[0].vars["x"] == 0
    with pytest.raises(TypeError):
        report.decisions[0].vars["x"] = 999
    with pytest.raises(FrozenInstanceError):
        report.outcome = "delta"
    machine.cycle()
    assert report.state_after == ("Root", "B")


def test_delta_termination_and_noop_are_distinct():
    blocked = runtime("""
        control int x = 0;
        state Root { state A; [*] -> A : if [x > 0]; }
    """)
    result = blocked.cycle(trace=True, diagnostics=True)
    assert result.delta and result.trace == ()
    assert result.diagnostics.outcome == "delta"
    assert any(d.guard_result is False for d in result.diagnostics.decisions)
    assert not any(d.committed for d in result.diagnostics.decisions)

    machine = runtime("state Root { state A; [*] -> A; A -> [*]; }")
    machine.cycle()
    ended = machine.cycle(diagnostics=True)
    assert ended.diagnostics.outcome == "terminated"
    assert ended.diagnostics.state_after is None
    noop = machine.cycle(diagnostics=True)
    assert noop.diagnostics.outcome == "noop"
    assert noop.diagnostics.cycle_count == 2
    assert noop.diagnostics.decisions == ()
    assert noop.diagnostics.state_before is None
    assert machine.cycle().diagnostics is None


def test_missing_event_is_not_a_false_guard_and_plain_cycle_can_stay_put():
    machine = runtime()
    machine.cycle()
    report = machine.cycle(diagnostics=True).diagnostics
    assert report.outcome == "cycle"
    assert report.state_before == report.state_after
    assert all(d.outcome == "event_missing" for d in report.decisions)
    assert all(d.guard_result is None for d in report.decisions)


def test_role_snapshots_sampling_and_handlers_are_observational():
    from dataclasses import replace
    from pyfcstm.simulate import BaseScalarInputPattern

    class Sensor(BaseScalarInputPattern):
        def __init__(self):
            super().__init__()
            self.samples = []

        def _sample(self, step):
            self.samples.append(step)
            return step + 1

    source = """
        input int sensor;
        param int threshold = 2;
        output int reading = 0;
        control int x = 0;
        state Root {
            state A { during { reading = sensor; } during abstract Read; }
            state B { enter { x = 7; } }
            [*] -> A;
            A -> B : if [sensor >= threshold];
        }
    """
    plain_sensor, observed_sensor = Sensor(), Sensor()
    plain = runtime(source, input_source={"sensor": plain_sensor})
    observed = runtime(source, input_source={"sensor": observed_sensor})
    calls = [[], []]
    plain.register_abstract_handler(
        "Root.A.Read", lambda ctx: calls[0].append(ctx.get_var("reading"))
    )
    observed.register_abstract_handler(
        "Root.A.Read", lambda ctx: calls[1].append(ctx.get_var("reading"))
    )
    for _ in range(3):
        expected = plain.cycle(trace=True)
        result = observed.cycle(trace=True, diagnostics=True)
        assert replace(result, diagnostics=None) == expected
        assert observed.vars == plain.vars
        assert observed.history == plain.history
        report = result.diagnostics
        assert report.roles == {
            "sensor": "input",
            "threshold": "param",
            "reading": "output",
            "x": "control",
        }
        for decision in report.decisions:
            assert decision.inputs == result.inputs
            assert decision.parameters == {"threshold": 2}
        before = report.to_dict()
        for _ in range(2):
            str(report)
            report.to_text(verbose=True)
        assert report.to_dict() == before
    assert plain_sensor.samples == observed_sensor.samples == [0, 1, 2]
    assert calls[0] == calls[1] == [1]


def test_exception_cleans_collection_and_retry_uses_new_inputs():
    from pyfcstm.simulate import SimulationRuntimeExpressionError

    machine = runtime(
        """
        input int divisor;
        control int value = 0;
        state Root {
            state A;
            state B { enter { value = 8 / divisor; } }
            [*] -> A;
            A -> B;
        }
    """,
        input_source={"divisor": 0},
    )
    machine.cycle()
    with pytest.raises(SimulationRuntimeExpressionError):
        machine.cycle(diagnostics=True)
    result = machine.cycle(inputs={"divisor": 2}, diagnostics=True)
    assert machine.vars == {"value": 4}
    assert result.diagnostics.decisions[0].id == 1
    assert all(d.inputs == {"divisor": 2} for d in result.diagnostics.decisions)
    assert machine.cycle().diagnostics is None


def test_error_state_noop_and_metadata_without_file_loader():
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine
    from pyfcstm.simulate import SimulationRuntimeInputSourceError

    class BrokenAdvance:
        def get(self):
            return 1

        def cycle(self):
            raise OSError("sensor disconnected")

    machine = SimulationRuntime(
        parse_dsl_node_to_state_machine(
            parse_with_grammar_entry(
                "input int sensor; state Root { state A; [*] -> A; }",
                "state_machine_dsl",
            )
        ),
        input_source={"sensor": BrokenAdvance()},
    )
    with pytest.raises(SimulationRuntimeInputSourceError):
        machine.cycle(diagnostics=True)
    assert machine.cycle(diagnostics=True).diagnostics.outcome == "noop"
    assert machine.cycle().diagnostics is None
    healthy = SimulationRuntime(machine.state_machine, input_source={"sensor": 1})
    report = healthy.cycle(diagnostics=True).diagnostics
    assert "source=" in report.to_text(verbose=True)
    assert all("path" not in d.location for d in report.decisions)


def test_search_branches_do_not_turn_one_failure_into_total_rejection():
    machine = runtime("""
        control int x = 0;
        state Root {
            state A;
            state C {
                pseudo state P;
                state Done;
                [*] -> P;
                P -> Done : if [x > 0];
                P -> Done;
            }
            [*] -> A;
            A -> C;
        }
    """)
    machine.cycle()
    report = machine.cycle(diagnostics=True).diagnostics
    assert report.state_after == ("Root", "C", "Done")
    assert any(d.guard_result is False for d in report.decisions)
    assert any(
        d.successor_result is True and d.transition_label == "Root.A::0::A->C"
        for d in report.decisions
    )
    assert any(d.outcome == "enabled" for d in report.decisions)
    assert "folded" in str(report)
    assert "folded" not in report.to_text(verbose=True)


def test_imported_input_mapped_to_control_records_final_role(tmp_path):
    from pyfcstm.model import load_state_machine_from_file

    (tmp_path / "child.fcstm").write_text("""
        input int sensor;
        state Child { state A; state B; [*] -> A; A -> B : if [sensor > 0]; }
    """)
    path = tmp_path / "host.fcstm"
    path.write_text("""
        control int local = 1;
        state Host {
            import "./child.fcstm" as Worker { var sensor -> local; }
            [*] -> Worker;
        }
    """)
    machine = SimulationRuntime(load_state_machine_from_file(path))
    machine.cycle()
    report = machine.cycle(diagnostics=True).diagnostics
    assert report.roles == {"local": "control"}
    decision = next(d for d in report.decisions if d.guard is not None)
    assert decision.inputs == {}
    assert decision.vars == {"local": 1}
    assert decision.guard_result is True
    assert decision.location["path"].endswith("child.fcstm")


def test_synthetic_root_exit_has_no_authored_location():
    machine = runtime("state Root;")
    machine.cycle()
    report = machine.cycle(diagnostics=True).diagnostics
    assert report.outcome == "terminated"
    assert any(not d.location for d in report.decisions)
    assert "committed" in report.to_text(verbose=True)


def test_post_child_exit_rejection_is_retained_under_successor():
    machine = runtime(
        """
        control int x = 0;
        state Root {
            state A;
            state C {
                state D { state Inner; [*] -> Inner; Inner -> [*]; }
                state Done;
                [*] -> D;
                D -> Done : if [x > 0];
            }
            [*] -> A;
            A -> C;
        }
    """,
        initial_state="Root.C.D.Inner",
        initial_vars={"x": 0},
    )
    report = machine.cycle(diagnostics=True).diagnostics
    assert report.outcome == "cycle"
    assert any(d.outcome == "successor_rejected" for d in report.decisions)
    assert any(
        d.transition_label == "Root.C.D::0::D->Done" and d.guard_result is False
        for d in report.decisions
    )


def test_large_values_do_not_break_human_diagnostics():
    machine = runtime(
        """
        control int huge = 0;
        state Root { state A; state B; [*] -> A; A -> B : if [huge > 0]; }
    """,
        initial_state="Root.A",
        initial_vars={"huge": 10**5000},
    )
    report = machine.cycle(diagnostics=True).diagnostics
    assert "int<5001 digits>" in str(report)
    assert "int<5001 digits>" in report.to_text(verbose=True)
    assert report.to_dict()["decisions"][0]["vars"]["huge"] == 10**5000
