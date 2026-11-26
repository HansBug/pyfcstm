"""Print the region positions and the values handed from region to region."""

import re

import z3

from pyfcstm.bmc import (
    REGION_DONE_ID,
    REGION_INACTIVE_ID,
    BmcEngine,
    build_bmc_core_formula,
)
from pyfcstm.model import load_state_machine_from_text

# Four cycles: cold start, /Start, a request, then a fault that arrives together
# with the request.
CYCLES = [
    {"fault": 0, "requested": 0, "start": False},
    {"fault": 0, "requested": 0, "start": True},
    {"fault": 0, "requested": 1, "start": False},
    {"fault": 1, "requested": 1, "start": False},
]

for name in ("controller", "controller_swapped"):
    with open("../../tutorials/regions/%s.fcstm" % name, encoding="utf-8") as stream:
        model = load_state_machine_from_text(stream.read())
    with open("interlock.fbmcq", encoding="utf-8") as stream:
        core = build_bmc_core_formula(BmcEngine(model).prepare(stream.read()))
    symbols = core.symbols
    labels = {entry.id: entry.path.split(".")[-1] for entry in core.context.domain.states}
    labels.update({REGION_DONE_ID: "DONE", REGION_INACTIVE_ID: "INACTIVE"})

    solver = z3.Solver()
    solver.add(core.core)
    for step, cycle in enumerate(CYCLES):
        solver.add(symbols.step_inputs[step]["fault"] == cycle["fault"])
        solver.add(symbols.step_inputs[step]["requested"] == cycle["requested"])
        for event in core.context.domain.events:
            literal = symbols.event_input(step, event.path)
            solver.add(literal if cycle["start"] and event.name == "Start" else z3.Not(literal))
    assert solver.check() == z3.sat
    model = solver.model()

    print("== %s" % name)
    for frame in range(len(CYCLES) + 1):
        positions = ", ".join(
            "%s=%s" % (path.split(".")[-1], labels[model.eval(symbols.region_position(frame, path), True).as_long()])
            for path in [item.path for item in sorted(core.context.domain.regions, key=lambda item: item.ordinal)]
        )
        values = ", ".join(
            "%s=%d" % (var, model.eval(symbols.frame_var(frame, var), True).as_long())
            for var in ("permit", "motor")
        )
        print("frame %d: %s | %s" % (frame, positions, values))
    print("values handed on in the fault cycle (step 3), after each region in written order:")
    handed = {}
    for decl in model.decls():
        found = re.match(r"R_3_\d+_g\d+_e(\d+)_(permit|motor)$", decl.name())
        if found:
            handed.setdefault(int(found.group(1)), {})[found.group(2)] = model[decl]
    for index in sorted(handed):
        print("  after region %d: permit=%s, motor=%s" % (index + 1, handed[index]["permit"], handed[index]["motor"]))
