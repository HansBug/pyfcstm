"""Measure a frozen workload matrix against one package-source snapshot.

Run from the paired runner. Each process warms all selected combinations once,
then measures them in the same seeded order. GC stays enabled. Timing includes
model parsing, compilation, property solving and mandatory SAT replay. Human
explanation rendering is measured separately after the solve.
"""

import argparse
import gc
import json
import os
import platform
import random
import resource
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('seed', type=int)
    parser.add_argument('--case', action='append')
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(args.source.resolve()))
    import pyfcstm
    import z3
    from pyfcstm.bmc import BmcOptions, compile_bmc_query, solve_bmc_property
    from pyfcstm.bmc.explanation import explanation_text_lines
    from pyfcstm.model import load_state_machine_from_text

    Path(pyfcstm.__file__).resolve().relative_to(args.source.resolve())
    cases = json.loads(Path(__file__).with_name('workloads.json').read_text())
    order = [(case, mode) for case in cases for mode in case['modes']
             if not args.case or case['name'] in args.case]
    assert order
    random.Random(args.seed).shuffle(order)
    original_check = z3.Solver.check
    calls = []
    collections = []
    gc_started = {}

    def check(self, *assumptions):
        calls.append(1)
        return original_check(self, *assumptions)

    def on_gc(phase, info):
        now = time.perf_counter()
        generation = info['generation']
        if phase == 'start':
            gc_started[generation] = now
        else:
            collections.append((gc_started.pop(generation), now, generation))

    z3.Solver.check = check
    gc.callbacks.append(on_gc)
    rows = []
    load_start = os.getloadavg()
    for warmup in (True, False):
        for case, mode in order:
            calls.clear()
            collections.clear()
            start = time.perf_counter()
            cpu_start = time.process_time()
            model = load_state_machine_from_text(case['model'])
            parsed = time.perf_counter()
            formula = (compile_bmc_query(model, case['query'], options=BmcOptions(record_construction=True))
                       if args.record else compile_bmc_query(model, case['query']))
            compiled = time.perf_counter()
            compile_solver_calls = len(calls)
            result = solve_bmc_property(
                formula, infeasibility_explanation=mode, timeout_ms=30000,
            )
            solved = time.perf_counter()
            solve_solver_calls = len(calls) - compile_solver_calls
            cpu_solved = time.process_time()
            explanation = result.feasibility.explanation if result.feasibility else None
            text = '\n'.join(explanation_text_lines(explanation)) if explanation else ''
            rendered = time.perf_counter()
            construction_check_ms = construction_render_ms = 0.0
            construction_status = None
            construction_values = 0
            if args.record:
                from pyfcstm.bmc.construction import get_bmc_construction
                report = get_bmc_construction(formula.core, tuple(
                    'transition.step.%04d' % i for i in range(len(formula.core.steps))))
                checked_start = time.perf_counter()
                construction_status = report.check(timeout_ms=30000).status
                checked_end = time.perf_counter()
                construction_check_ms = (checked_end - checked_start) * 1000
                local_text = '\n'.join(line for instance in report.cases for action in instance.actions
                                        for line in action.text_lines(formula.core.symbols.names))
                construction_render_ms = (time.perf_counter() - checked_end) * 1000
                construction_values = sum(len(action.execution.values) for instance in report.cases
                                          for action in instance.actions if action.execution is not None)
                del report, local_text

            print('%s %s/%s: %.1f ms, %s' %
                  ('warmup' if warmup else 'sample', case['name'], mode,
                   (solved-start)*1000, result.status), file=sys.stderr, flush=True)
            if not warmup:
                rows.append(dict(
                    case=case['name'], mode=mode, record=args.record,
                    construction_check_ms=construction_check_ms, construction_render_ms=construction_render_ms,
                    construction_status=construction_status, construction_values=construction_values,
                    api_ms=(solved-start)*1000,
                    api_cpu_ms=(cpu_solved-cpu_start)*1000,
                    parse_ms=(parsed-start)*1000,
                    compile_ms=(compiled-parsed)*1000,
                    solve_ms=(solved-compiled)*1000,
                    render_ms=(rendered-solved)*1000,
                    text_chars=len(text), solver_calls=len(calls),
                    compile_solver_calls=compile_solver_calls, solve_solver_calls=solve_solver_calls,
                    construction_solver_calls=len(calls)-compile_solver_calls-solve_solver_calls,
                    gc_ms=sum((end-begin)*1000 for begin,end,_ in collections),
                    gc_generations=[generation for _,_,generation in collections],
                    status=result.status, satisfied=result.property_satisfied,
                    incomplete_status=result.incomplete_status,
                    infeasible_stage=result.feasibility.infeasible_stage if result.feasibility else None,
                    achieved=explanation.achieved_mode if explanation else None,
                    explanation_status=explanation.status if explanation else None,
                    core_ids=[item.constraint.stable_id for item in explanation.core.items]
                    if explanation and explanation.core else None,
                ))
            del result, formula, model, explanation, text
    print(json.dumps(dict(seed=args.seed, rows=rows,
                          rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          python=platform.python_version(), platform=platform.platform(),
                          load_start=load_start, load_end=os.getloadavg(),
                          z3=z3.get_version_string(), source=str(args.source.resolve()))))


if __name__ == '__main__':
    main()
