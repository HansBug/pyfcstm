import gc
import json
import random
import resource
import sys
import time

sys.path.insert(0, sys.argv[1])
import z3
from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.model import load_state_machine_from_text

MODEL = '''def int x = 0;
state Root { state A; state B; [*] -> A;
A -> A effect { x = x + 1; }; A -> B; }
'''
CASES = {
    'sat_reach': 'check reach <= 8: x > 3;',
    'unsat_objective': 'check invariant <= 8: x >= 0;',
    'assumption_conflict': 'assume at 1: x > 2; assume at 1: x < 1; check reach <= 8: x > 0;',
    'transition_conflict': 'assume at 1: x == 0; assume at 2: x == 99; check reach <= 8: x > 0;',
}
original_check = z3.Solver.check
calls = []
collections = []
gc_started = {}


def check(self, *args):
    calls.append(1)
    return original_check(self, *args)


def on_gc(phase, info):
    now = time.perf_counter()
    if phase == 'start':
        gc_started[info['generation']] = now
    else:
        collections.append((gc_started.pop(info['generation']), now, info['generation']))


z3.Solver.check = check
gc.callbacks.append(on_gc)
seed = int(sys.argv[2])
order = [(name, mode) for name in CASES for mode in ('none', 'formal', 'proof')]
random.Random(seed).shuffle(order)
rows = []
for warmup in (True, False):
    for name, mode in order:
        calls.clear()
        start = time.perf_counter()
        model = load_state_machine_from_text(MODEL)
        result = solve_bmc_property(
            compile_bmc_query(model, CASES[name]), infeasibility_explanation=mode
        )
        elapsed = (time.perf_counter() - start) * 1000
        explanation = result.feasibility.explanation
        if not warmup:
            rows.append(dict(
                case=name, mode=mode, ms=elapsed, solver_calls=len(calls),
                gc_ms=sum((end-begin)*1000 for begin,end,_ in collections if begin >= start),
                gc_generations=[generation for begin,_,generation in collections if begin >= start],
                status=result.status, satisfied=result.property_satisfied,
                achieved=explanation.achieved_mode if explanation else None,
            ))
print(json.dumps(dict(seed=seed, rows=rows, rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
