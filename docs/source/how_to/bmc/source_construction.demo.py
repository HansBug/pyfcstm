"""Inspect an actual editor action without claiming an UNSAT derivation."""

from pathlib import Path

from pyfcstm.bmc import BmcOptions, compile_bmc_query
from pyfcstm.bmc.construction import get_bmc_construction
from pyfcstm.model import load_state_machine_from_file


directory = Path(__file__).resolve().parent
model = load_state_machine_from_file(str(directory / 'dose_editor.fcstm'))
query = (directory / 'dose_editor.fbmcq').read_text(encoding='utf-8')
compiled = compile_bmc_query(model, query, options=BmcOptions(record_construction=True))
report = get_bmc_construction(compiled.core, ('transition.step.0002',))
checked = report.check(timeout_ms=10000)
print('Construction binding:', checked.status)
print('This script does not compute a property verdict or an UNSAT derivation.')

case, action = next(
    (case, action)
    for case in report.cases for action in case.actions
    if action.block.owner_state_path.endswith('.Trim')
)
print('Frame:', case.step_index)
print('Case:', case.case.label)
print('Case scope:', compiled.core.symbols.names.render(case.antecedent))
print('\n'.join(action.text_lines(compiled.core.symbols.names)))
