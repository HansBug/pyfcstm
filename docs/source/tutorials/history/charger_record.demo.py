"""Print the Session history record after every cycle of one charging day."""

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

with open("charger.fcstm") as f:
    machine = load_state_machine_from_text(f.read())
runtime = SimulationRuntime(machine)

# One event per cycle; None runs a cycle without an event.
events = [
    None,
    "Idle.PlugIn",
    "Session.Authenticating.Authorized",
    "Session.Charging.Precharge.Ready",
    "Session.Charging.ConstantCurrent.NearFull",
    "Session.OverTemp",
    "Fault.Cleared",
    "Session.OverTemp",
    "Fault.ManualReset",
    "Session.Charging.Precharge.Ready",
    "Session.Unplug",
    "Idle.PlugIn",
]

row = "{:>2}  {:<12} {:<32} {:>9} {:>6}  {}"
print(
    row.format(
        "#", "event", "state below Charger", "precharge", "energy", "Session record"
    )
)
for step, event in enumerate(events):
    runtime.cycle(["Charger." + event] if event else [])
    state = ".".join(runtime.current_state.path[1:])
    if state.startswith("Session."):
        record = "(Session active)"
    else:
        record = machine.history_record(runtime.vars, "Charger.Session") or "none"
    print(
        row.format(
            step,
            event.split(".")[-1] if event else "-",
            state,
            runtime.vars["precharge_runs"],
            runtime.vars["energy"],
            record,
        )
    )
