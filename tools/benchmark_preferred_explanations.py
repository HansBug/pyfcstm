"""Compare ordinary and preferred explanations on a fixed synthetic corpus.

Run with --baseline pointing to a source archive of the umbrella commit and
--output pointing to a new directory. Each arm receives one warmup and five
alternating samples in fresh processes. API timing includes load/compile/solve
and result serialization; CLI timing also includes interpreter startup. GNU
/usr/bin/time records process peak RSS. Check counts use separate untimed
observations so instrumentation cannot bias timed samples. No historical run
is overwritten. This measurement runner requires Linux with GNU time.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

BASELINE = 'a20d8e6d5b00efbf58edeb4db9890a05bef4e74e'
MODEL = 'def int x = 0; def int y = 0; state Root;'
MULTIPLE = ('init cold where y == 0; assume at 0: y >= 1; '
            'assume at 1: x >= 1; check reach <= {bound}: true;')
CASES = {
    'multiple_short': MULTIPLE.format(bound=2),
    'multiple_long': MULTIPLE.format(bound=100),
    'single_conflict': 'assume at 0: x == 1; assume at 0: x == 2; check reach <= 30: true;',
    'feasible': 'check reach <= 30: true;',
    'budget_limited': MULTIPLE.format(bound=100),
}
ARMS = ('baseline_default', 'current_default', 'current_preferred')
CHILD = '''
import json, sys, time
from pathlib import Path
from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.model import load_state_machine_from_file
import z3
model_path, query_path, preferred, budget, observe = sys.argv[1:]
calls = []
if observe == 'yes':
    original = z3.Solver.check
    def check(solver, *args):
        calls.append(None)
        return original(solver, *args)
    z3.Solver.check = check
options = {'infeasibility_explanation': 'formal'}
if preferred == 'yes':
    options.update(explanation_preference='editable', feedback_timeout_ms=int(budget))
started = time.perf_counter()
model = load_state_machine_from_file(model_path)
formula = compile_bmc_query(model, Path(query_path).read_text(), query_source_path=query_path)
solve_started = time.perf_counter()
result = solve_bmc_property(formula, **options)
solve_ms = (time.perf_counter() - solve_started) * 1000
payload = result.to_canonical()
elapsed = (time.perf_counter() - started) * 1000
print(json.dumps({'api_ms': elapsed, 'solve_ms': solve_ms, 'checks': len(calls) if observe == 'yes' else None,
                  'result': payload}))
'''


def sample(root, arm, surface, query, directory, observe=False):
    model = directory / 'model.fcstm'
    query_file = directory / 'query.fbmcq'
    model.write_text(MODEL)
    query_file.write_text(query)
    preferred = arm == 'current_preferred'
    budget = 5 if directory.name == 'budget_limited' else 10000
    if surface == 'api':
        command = [sys.executable, '-c', CHILD, str(model), str(query_file),
                   'yes' if preferred else 'no', str(budget), 'yes' if observe else 'no']
    else:
        command = [sys.executable, '-m', 'pyfcstm', 'bmc', '-i', str(model),
                   '-q', str(query_file), '--json', '--explain-infeasibility', 'formal']
        if preferred:
            command += ['--explanation-preference', 'editable', '--feedback-timeout-ms', str(budget)]
    rss_file = directory / 'rss.txt'
    env = dict(os.environ, PYTHONPATH=str(root))
    started = time.perf_counter()
    completed = subprocess.run(['/usr/bin/time', '-f', '%M', '-o', str(rss_file)] + command,
                               cwd=str(directory), env=env, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    wall_ms = (time.perf_counter() - started) * 1000
    if completed.returncode not in (0, 3):
        raise RuntimeError("exit %s: %s %s" % (completed.returncode, completed.stderr, completed.stdout))
    report = json.loads(completed.stdout)
    result = report['result']
    expected = 'witness_found' if query == CASES['feasible'] else 'scenario_infeasible'
    if result['outcome'] != expected:
        raise AssertionError('Unexpected benchmark outcome: %r' % result['outcome'])
    explanation = result['feasibility']['explanation']
    core = explanation['core'] if explanation else None
    return {
        'arm': arm, 'surface': surface, 'wall_ms': wall_ms,
        'api_ms': report.get('api_ms'), 'solve_ms': report.get('solve_ms'), 'rss_kib': int(rss_file.read_text().splitlines()[-1]),
        'checks': report.get('checks'), 'exit_code': completed.returncode,
        'outcome': result['outcome'],
        'auxiliary_ms': explanation['elapsed_ms'] if explanation else 0,
        'preference': result.get('explanation_preference'),
        'core_ids': [i['constraint']['stable_id'] for i in core['items']] if core else [],
        'minimality': core['subset_minimality'] if core else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--rebuild', type=Path)
    args = parser.parse_args()
    if args.rebuild is not None:
        rows = [json.loads(line) for line in (args.rebuild / 'raw.jsonl').read_text().splitlines()]
        write_report(args.rebuild, rows)
        return
    if args.baseline is None or args.output is None:
        parser.error('--baseline and --output are required for a new run')
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_files = ('pyfcstm/bmc/infeasibility.py', 'pyfcstm/bmc/witness.py',
                    'pyfcstm/entry/bmc.py')
    baseline_hashes = {}
    for name in source_files:
        expected = subprocess.check_output(['git', 'show', BASELINE + ':' + name], cwd=root)
        actual = (args.baseline / name).read_bytes()
        if actual != expected:
            raise ValueError('Baseline source does not match %s: %s' % (BASELINE, name))
        baseline_hashes[name] = hashlib.sha256(actual).hexdigest()
    import z3

    manifest = {
        'baseline_sha': BASELINE,
        'current_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'tracked_diff': subprocess.check_output(['git', 'diff', 'HEAD', '--', 'pyfcstm'], cwd=root, text=True),
        'baseline_source_sha256': baseline_hashes,
        'current_source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_files},
        'z3': z3.get_version_string(),
        'cpu_count': os.cpu_count(), 'processor': platform.processor(),
        'python': sys.version, 'platform': platform.platform(), 'warmups': 1, 'repetitions': 5,
        'feedback_timeout_ms_by_case': {name: 5 if name == 'budget_limited' else 10000 for name in CASES},
        'cases': CASES, 'model': MODEL, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'protocol': 'Fresh processes; one warmup then five alternating samples per arm/surface; counts observed separately; no performance threshold.',
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    rows = []
    with tempfile.TemporaryDirectory(prefix='preferred-benchmark-') as temporary:
        for name, query in CASES.items():
            directory = Path(temporary) / name
            directory.mkdir()
            for surface in ('api', 'cli'):
                for repetition in range(-1, 5):
                    arms = ARMS if repetition % 2 == 0 else tuple(reversed(ARMS))
                    for arm in arms:
                        source = args.baseline.resolve() if arm.startswith('baseline') else root
                        row = sample(source, arm, surface, query, directory)
                        row.update(case=name, repetition=repetition, observation=False)
                        rows.append(row)
                for arm in ARMS:
                    if surface == 'api':
                        source = args.baseline.resolve() if arm.startswith('baseline') else root
                        row = sample(source, arm, surface, query, directory, observe=True)
                        row.update(case=name, repetition=None, observation=True)
                        rows.append(row)
            print(name, 'finished', flush=True)
    (output / 'raw.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    write_report(output, rows)


def write_report(output, rows):
    """Rebuild the presentation from immutable raw samples."""
    lines = ['# Preferred explanation measurements', '',
             'Synthetic fixtures only; no claim about a production model distribution. API excludes imports; CLI includes startup. RSS is whole-process peak. Timed samples have no check observer. Reported explanation time is the existing production metric, not a hard wall-clock bound or a complete accounting of late narrative/proof work. API samples also retain full solve_ms in raw data. A 5 ms budget can overrun during Python setup; inspect raw status and elapsed time rather than claiming hard realtime behavior.', '',
             '| Case | Surface | Arm | Time median [min, max] ms | RSS median KiB | Reported explanation median ms |',
             '|---|---|---|---:|---:|---:|']
    for name in CASES:
        for surface in ('api', 'cli'):
            for arm in ARMS:
                values = [r for r in rows if r['case'] == name and r['surface'] == surface
                          and r['arm'] == arm and not r['observation'] and r['repetition'] >= 0]
                times = [r['api_ms' if surface == 'api' else 'wall_ms'] for r in values]
                lines.append('| %s | %s | %s | %.3f [%.3f, %.3f] | %.0f | %.3f |' % (
                    name, surface, arm, statistics.median(times), min(times), max(times),
                    statistics.median(r['rss_kib'] for r in values),
                    statistics.median(r['auxiliary_ms'] for r in values)))
    lines.extend(['', 'Separate untimed check-count / quality observations:', '',
                  '| Case | Arm | Checks | Core member IDs | Minimality | Preference status |',
                  '|---|---|---:|---|---|---|'])
    for row in rows:
        if row['observation']:
            lines.append('| %s | %s | %s | %s | %s | %s |' % (
                row['case'], row['arm'], row['checks'], ', '.join(row['core_ids']),
                row['minimality'], (row['preference'] or {}).get('status', 'off')))
    (output / 'report.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
