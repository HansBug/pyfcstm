"""Inspect two conditional editor steps without claiming an UNSAT derivation."""

from pathlib import Path

from pyfcstm.bmc import BmcOptions, compile_bmc_query
from pyfcstm.bmc.construction import get_bmc_construction
from pyfcstm.model import load_state_machine_from_file


directory = Path(__file__).resolve().parent
model = load_state_machine_from_file(str(directory / 'dose_editor.fcstm'))
query = (directory / 'dose_editor.fbmcq').read_text(encoding='utf-8')
compiled = compile_bmc_query(
    model, query, options=BmcOptions(record_construction=True),
    query_source_path=str(directory / 'dose_editor.fbmcq'),
)
# Select Review -> Trim at step 2 and Trim -> Ready at step 3.
# These are construction examples, not an asserted feasible trace or solver core.
group_ids = tuple(
    'transition.case.%04d.%04d' % (step, index)
    for step in (2, 3)
    for index, relation in enumerate(compiled.core.steps[step].case_relations)
    if (step == 2 and relation.case.source_state_path.endswith('.Review')
        and relation.case.target_state_path.endswith('.Trim'))
    or (step == 3 and relation.case.source_state_path.endswith('.Trim')
        and relation.case.target_state_path.endswith('.Ready'))
)
report = get_bmc_construction(compiled.core, group_ids)
checked = report.check(timeout_ms=10000)
print('Construction binding:', checked.status)
print('This script does not compute a property verdict or an UNSAT derivation.')
print('\n'.join(report.text_lines()))
# Use report.text_lines(expanded=True) for actual expanded values, boundaries
# without local definitions/aliases, and the complete submitted case formulas.
