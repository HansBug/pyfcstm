"""Count the paths one working cycle lowers to, for one to eight toggling regions."""

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
from pyfcstm.model import load_state_machine_from_text


def machine(regions):
    """Return a state with ``regions`` regions, each toggling on its own event."""
    events = "".join("event Go%d;" % index for index in range(regions))
    body = "".join(
        "region R%d { [*] -> Off; state Off; state On;"
        " Off -> On :: Go%d; On -> Off :: Go%d; } " % (index, index, index)
        for index in range(regions)
    )
    return "state Root { %s %s }" % (events, body)


print("regions  lowered paths of a working cycle  4**regions")
for regions in range(1, 9):
    model = load_state_machine_from_text(machine(regions))
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 2: terminated();")
    )
    # Step 0 is the cold start; step 1 is the first cycle in which the regions work.
    working = core.region_steps[1]
    print("%7d  %33d  %10d" % (regions, len(working.cases), 4**regions))
