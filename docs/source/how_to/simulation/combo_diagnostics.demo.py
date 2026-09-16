"""Run candidate diagnostics through public simulator APIs.

Execute this file with pyfcstm installed; its model lives beside it. Assertions
verify speculative values against the committed boundary. Standard output is
human-readable evidence; a Delta warning may also appear on standard error.
"""

from pathlib import Path

from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime

model = load_state_machine_from_file(Path(__file__).with_name("combo_diagnostics.fcstm"))
cases = [
    ("missing B", 12, ["Root.Start.A"], "Root.Fallback", 121, 0),
    ("target guard false", 3, ["Root.Start.A", "Root.Start.B"], "Root.Fallback", 121, 0),
    ("complete path", 12, ["Root.Start.A", "Root.Start.B"], "Root.Target.Good", 11011, 12),
]

for title, sensor, events, state, score, reading in cases:
    runtime = SimulationRuntime(
        model, parameters={"limit": 10}, input_source={"sensor": sensor}
    )
    runtime.cycle()  # Initialize into Root.Start.
    result = runtime.cycle(events, trace=True, diagnostics=True)
    report = result.diagnostics
    transitions = [e.transition_label for e in result.trace if e.kind == "transition"]

    assert ".".join(report.state_after) == state
    assert runtime.vars == {"score": score, "reading": reading}
    assert not result.delta
    assert [d.transition_label for d in report.decisions if d.committed] == transitions
    if state == "Root.Fallback":
        assert transitions == ["Root.Start::1::Start->Fallback"]
    else:
        assert len(transitions) == 3
    guards = [d for d in report.decisions if d.guard is not None]
    if title == "target guard false":
        assert all(d.vars == {"score": 10011, "reading": 3} for d in guards)
        assert all(d.guard_result is False for d in guards)

    print("\n===", title, "===")
    print(report)
    if guards:
        d = guards[0]
        print("guard snapshot:", {
            "id": d.id, "parent_id": d.parent_id,
            "vars": dict(d.vars), "inputs": dict(d.inputs),
            "parameters": dict(d.parameters),
        })
    print("final vars:", dict(report.vars_after))
    print("delta:", result.delta)
    print("committed transitions:", transitions)

    # Optional full evidence for the first candidate and its nested checks:
    # print(report.to_text(transition=report.decisions[0].transition_label, verbose=True))
