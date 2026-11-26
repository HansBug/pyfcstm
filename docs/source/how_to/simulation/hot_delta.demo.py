from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime

model = load_state_machine_from_file("hot_stuck.fcstm")
for flag in (0, 1):
    runtime = SimulationRuntime(
        model,
        initial_state="Root.Pair{Left: Busy}",
        initial_vars={"flag": flag, "work": 0},
    )
    print(f"flag={flag} at start: {runtime.configuration}")
    result = runtime.cycle(diagnostics=True)
    print(f"  delta={result.delta} outcome={result.diagnostics.outcome}")
    print(f"  after cycle: {runtime.configuration} vars={dict(runtime.vars)}")
    for item in result.diagnostics.decisions:
        print(
            f"  check #{item.id} {item.transition_label.split('::')[0]} -> "
            f"{item.outcome}; guard={item.guard} result={item.guard_result}"
        )
