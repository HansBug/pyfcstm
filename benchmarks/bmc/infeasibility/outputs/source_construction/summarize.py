"""Summarize all measured samples without discarding slow observations."""
import json
from pathlib import Path
from statistics import median
root=Path(__file__).resolve().parent
records=[json.loads(line) for line in (root/'samples.jsonl').read_text().splitlines()]
samples=[row for row in records if row['kind']=='sample']
assert len(samples)==21, len(samples)
rows={}
for sample in samples:
    for row in sample['result']['rows']:
        rows.setdefault(row['case'],{}).setdefault(sample['variant'],[]).append(row)
lines=['# Source construction performance', '',
       'Baseline: 7cea5bed. Seven interleaved groups, one warmup and one measured pass per worker; nine workloads, three modes. Shared Linux host; GC enabled. Times are medians in milliseconds. API includes parse/compile/solve and mandatory replay; capture checking and full local rendering are separate. No samples discarded.', '',
       '| Case | Baseline API | Default API | Change | Recorded API | Capture vs default | Check | Render |',
       '|---|---:|---:|---:|---:|---:|---:|---:|']
summary={}
for name, variants in rows.items():
    assert all(len(values)==7 for values in variants.values())
    signatures={(r['status'],r['satisfied'],r['incomplete_status'],r['infeasible_stage']) for vs in variants.values() for r in vs}
    assert len(signatures)==1,(name,signatures)
    assert all(r['construction_status']=='verified' for r in variants['recorded'])
    # Capture alone must not introduce solver calls.
    calls={(r['compile_solver_calls'],r['solve_solver_calls']) for vs in variants.values() for r in vs}
    assert len(calls)==1,(name,calls)
    b,d,c=[median(r['api_ms'] for r in variants[v]) for v in ('baseline','default','recorded')]
    check=median(r['construction_check_ms'] for r in variants['recorded'])
    render=median(r['construction_render_ms'] for r in variants['recorded'])
    lines.append('| %s | %.3f | %.3f | %+.2f%% | %.3f | %+.2f%% | %.3f | %.3f |' %
                 (name,b,d,(d/b-1)*100,c,(c/d-1)*100,check,render))
    summary[name]={variant:{metric:dict(median=median(r[metric] for r in values),minimum=min(r[metric] for r in values),maximum=max(r[metric] for r in values))
                            for metric in ('api_ms','parse_ms','compile_ms','solve_ms','construction_check_ms','construction_render_ms')}
                   for variant,values in variants.items()}
lines+=['', 'All property/status signatures and compile/solve solver-call counts agree across variants. All captured reports completed their binding checks. This is not evidence of complete UNSAT derivations.', '', 'Process peak RSS includes every workload and, for recorded workers, subsequent checking/rendering; it is not capture-only memory.']
for variant in ('baseline','default','recorded'):
    values=[s['result']['rss_kib'] for s in samples if s['variant']==variant]
    lines.append('- %s: median %d KiB, range %d–%d KiB.' % (variant,median(values),min(values),max(values)))
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'report.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
