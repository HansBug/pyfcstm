from machine import ControllerMachine

# (event, fault, requested) for each cycle of the scenario.
SCENARIO = [
    (None, 0, 0),
    ("/Start", 0, 0),
    (None, 0, 1),
    (None, 1, 1),
    (None, 0, 1),
    ("/Stop", 0, 1),
]

machine = ControllerMachine()
for event, fault, requested in SCENARIO:
    machine.cycle(events=event, inputs={"fault": fault, "requested": requested})
    print(
        machine.cycle_count,
        machine.configuration,
        "permit=%d" % machine.vars["permit"],
        "motor=%d" % machine.vars["motor"],
    )
