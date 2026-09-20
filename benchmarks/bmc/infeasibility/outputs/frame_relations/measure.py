"""Measure explicit text rendering; compilation/checking are outside the timer.

Run from the repository root. This is an experiment, not a performance gate.
The report includes every case for all bounded steps, not a selected trace.
"""

import argparse
import cProfile
import hashlib
import json
import platform
import statistics
import time
import subprocess
import types
from pathlib import Path

import z3

from pyfcstm.bmc import BmcOptions, compile_bmc_query
from pyfcstm.bmc.construction import get_bmc_construction
from pyfcstm.model import load_state_machine_from_file


root = Path(__file__).resolve().parents[5]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', required=True, help='Local Git revision of the previous text renderer')
args = parser.parse_args()
baseline_source = subprocess.check_output(
    ['git', 'show', args.baseline + ':pyfcstm/bmc/_construction_text.py'], cwd=str(root), text=True)
baseline = types.ModuleType('pyfcstm.bmc._baseline_construction_text')
baseline.__package__ = 'pyfcstm.bmc'
exec(compile(baseline_source, '<baseline construction renderer>', 'exec'), baseline.__dict__)
results = {}
for name, bound in [('dose_editor', 6), ('pool', 8)]:
    model = load_state_machine_from_file(str(root / 'test/bmc/fixtures/construction' / (name + '.fcstm')))
    compiled = compile_bmc_query(model, 'init cold havoc *; check reach <= %d: true;' % bound,
                                 options=BmcOptions(record_construction=True))
    report = get_bmc_construction(compiled.core, tuple('transition.step.%04d' % i for i in range(bound)))
    assert report.check(timeout_ms=30000).status == 'verified'
    formula_before = compiled.solve_formula.sexpr()
    selected_ids = tuple(
        'transition.case.%04d.%04d' % (step, index)
        for step in (2, 3) for index, relation in enumerate(compiled.core.steps[step].case_relations)
        if name == 'dose_editor' and (
            (step == 2 and relation.case.source_state_path.endswith('.Review')
             and relation.case.target_state_path.endswith('.Trim'))
            or (step == 3 and relation.case.source_state_path.endswith('.Trim')
                and relation.case.target_state_path.endswith('.Ready')))
    )
    selected = get_bmc_construction(compiled.core, selected_ids)
    variants = {'baseline_compact': lambda: baseline._report_text(report),
                'compact': lambda: report.text_lines(),
                'baseline_expanded': lambda: baseline._report_text(report, expanded=True),
                'expanded': lambda: report.text_lines(expanded=True)}
    if selected_ids:
        variants['baseline_selected_compact'] = lambda: baseline._report_text(selected)
        variants['selected_compact'] = lambda: selected.text_lines()
        variants['selected_expanded'] = lambda: selected.text_lines(expanded=True)
    for run in variants.values():
        run()
    samples = {key: [] for key in variants}
    texts = {}
    for repeat in range(7):
        order = tuple(variants) if repeat % 2 == 0 else tuple(reversed(variants))
        for variant in order:
            start = time.perf_counter()
            text = variants[variant]()
            samples[variant].append((time.perf_counter() - start) * 1000)
            texts[variant] = text
    solver_checks = {}
    for variant, run in variants.items():
        profiler = cProfile.Profile()
        profiler.runcall(run)
        solver_checks[variant] = sum(entry.callcount for entry in profiler.getstats()
                                    if not isinstance(entry.code, str) and entry.code.co_name == 'check'
                                    and entry.code.co_filename.endswith('/z3.py'))
        assert solver_checks[variant] == 0
    assert compiled.solve_formula.sexpr() == formula_before
    results[name] = {
        'bound': bound, 'cases': len(report.cases), 'selected_ids': selected_ids, 'solver_checks': solver_checks,
        'variants': {variant: {'samples_ms': values, 'median_ms': statistics.median(values),
                               'lines': len(texts[variant]),
                               'characters': len('\n'.join(texts[variant]))}
                     for variant, values in samples.items()},
    }
payload = {'python': platform.python_version(), 'platform': platform.platform(),
           'z3': z3.get_version_string(), 'baseline': args.baseline,
           'baseline_source_sha256': hashlib.sha256(baseline_source.encode()).hexdigest(),
           'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                             for name in ('pyfcstm/bmc/construction.py', 'pyfcstm/bmc/_construction_text.py',
                                          'pyfcstm/bmc/_construction_formula.py')},
           'results': results}
Path(__file__).with_name('samples.json').write_text(json.dumps(payload, indent=2) + '\n')
print(json.dumps(results, indent=2))
