"""Run candidate diagnostics through public simulator APIs.

Execute this file with pyfcstm installed; its model lives beside it. Assertions
verify speculative values against the committed boundary. Standard output is
human-readable evidence; a Delta warning may also appear on standard error.
"""

from pathlib import Path

from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

model = load_state_machine_from_file(Path(__file__).with_name("delta_diagnostics.fcstm"))
runtime = SimulationRuntime(
    model, parameters={"limit": 10},
    input_source={"sensor": SequenceInput([3, 12])},
)
reports = []

for sensor, score, reading, delta in [(3, 0, 0, True), (12, 1110, 12, False)]:
    result = runtime.cycle(trace=True, diagnostics=True)
    report = result.diagnostics
    reports.append(report)
    guards = [d for d in report.decisions if d.guard is not None]
    transitions = [e.transition_label for e in result.trace if e.kind == "transition"]

    assert result.inputs["sensor"] == sensor
    assert result.delta is delta
    assert runtime.vars == {"score": score, "reading": reading}
    assert guards[0].vars == {"score": 110, "reading": sensor}
    assert guards[0].guard_result is (not delta)
    if delta:
        assert report.state_after == ("Root",)
        assert result.trace == ()
        assert not any(d.committed for d in report.decisions)
    else:
        assert report.state_after == ("Root", "Ready")
        assert len(transitions) == 2

    print("\n=== sensor =", sensor, "===")
    print(report)
    print("guard vars:", dict(guards[0].vars))
    print("final vars:", dict(report.vars_after))
    print("delta:", result.delta)
    print("committed transitions:", transitions)

assert runtime.cycle_count == 2
assert reports[0].outcome == "delta"  # Later cycles cannot rewrite old evidence.
