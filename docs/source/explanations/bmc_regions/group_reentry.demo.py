"""Show how many laps a group may take inside one cycle before the build stops."""

from pyfcstm.bmc import BmcBuildError, BmcEngine, BmcOptions, build_bmc_core_formula
from pyfcstm.model import load_state_machine_from_text

with open("laps.fcstm", encoding="utf-8") as stream:
    model = load_state_machine_from_text(stream.read())
with open("spin.fbmcq", encoding="utf-8") as stream:
    query = stream.read()

for limit in (16, 7, 6):
    engine = BmcEngine(model, BmcOptions(max_group_reentries=limit))
    try:
        core = build_bmc_core_formula(engine.prepare(query))
    except BmcBuildError as err:
        print("max_group_reentries=%d: BmcBuildError: %s" % (limit, err))
    else:
        print("max_group_reentries=%d: built, %d step(s)" % (limit, len(core.region_steps)))
