"""Persist the Session record across a power loss and resume from it."""

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

OWNER = "Charger.Session"
with open("charger.fcstm") as f:
    machine = load_state_machine_from_text(f.read())

# Charge into ConstantCurrent, then overheat.
runtime = SimulationRuntime(machine)
for event in [
    None,
    "Idle.PlugIn",
    "Session.Authenticating.Authorized",
    "Session.Charging.Precharge.Ready",
    "Session.OverTemp",
]:
    runtime.cycle(["Charger." + event] if event else [])

# What a controller writes to non-volatile storage: the current state, its own
# variables and the source-level record, but no generated __hist_* number.
saved_state = ".".join(runtime.current_state.path)
saved_record = machine.history_record(runtime.vars, OWNER)
saved_vars = {k: v for k, v in runtime.vars.items() if not k.startswith("__hist_")}
print("saved state: ", saved_state)
print("saved record:", saved_record)
print("saved vars:  ", saved_vars)


def resume(record):
    """Hot start at the saved state, then let the fault clear."""
    hidden = machine.history_variables({OWNER: record} if record else None)
    restored = SimulationRuntime(
        machine,
        initial_state=saved_state,
        initial_vars={**saved_vars, **hidden},
    )
    restored.cycle(["Charger.Fault.Cleared"])
    return hidden, ".".join(restored.current_state.path), restored.vars


for label, record in [
    ("with the saved record", saved_record),
    ("without a record", None),
]:
    hidden, state, variables = resume(record)
    print()
    print("After the power loss,", label)
    print("  history variables:", hidden)
    print("  after Cleared:    ", state)
    print("  precharge_runs:   ", variables["precharge_runs"])
