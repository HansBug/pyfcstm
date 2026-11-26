from pyfcstm.bmc import BmcOptions, compile_bmc_query
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.model import load_state_machine_from_file

QUERY = "check reach <= 1: terminated();"
for name, limits in (("region_reentry_six", (16, 7, 6)), ("region_reentry_loop", (16, 64))):
    model = load_state_machine_from_file(f"{name}.fcstm")
    for limit in limits:
        try:
            compile_bmc_query(model, QUERY, options=BmcOptions(max_group_reentries=limit))
        except BmcBuildError as error:
            # BmcBuildError: the owner re-enters itself more often than the limit allows.
            print(f"{name} max_group_reentries={limit}: BmcBuildError: {error}")
        else:
            print(f"{name} max_group_reentries={limit}: compiled")
