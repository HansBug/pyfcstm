"""Show rejected successor evidence while preserving the committed trace.

Run with the repository's installed Python package. The model lives beside this
script. Standard output is the report; no runtime state is saved or replayed.
"""

from pathlib import Path

from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime

model = load_state_machine_from_file(Path(__file__).with_name('candidate_failure.fcstm'))
runtime = SimulationRuntime(model)
runtime.cycle()
result = runtime.cycle('Root.A.Go', trace=True, diagnostics=True)
assert runtime.vars == {'x': 1}
assert [e.transition_label for e in result.trace if e.kind == 'transition'] == ['Root.A::1::A->B']
assert any(d.guard_result is False and d.vars['x'] == 100 for d in result.diagnostics.decisions)
print(result.diagnostics)
