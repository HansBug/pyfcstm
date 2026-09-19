"""Summarize every retained pair without dropping timing or outcome outliers."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def summary(values):
    return dict(median=statistics.median(values), minimum=min(values), maximum=max(values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.samples.read_text().splitlines()]
    protocol, samples = records[0], records[1:]
    assert len(samples) == 2*protocol['pairs']
    grouped = defaultdict(dict)
    rss = defaultdict(list)
    observations = ('status', 'satisfied', 'incomplete_status', 'infeasible_stage',
                    'achieved', 'explanation_status', 'solver_calls')
    metrics = ('api_ms', 'api_cpu_ms', 'parse_ms', 'compile_ms', 'solve_ms',
               'render_ms', 'gc_ms', 'text_chars')
    for record in samples:
        revision = record['revision']
        rss[revision].append(record['rss_kib'])
        for row in record['rows']:
            key = row['case'], row['mode']
            pair = record['repetition'], revision
            assert pair not in grouped[key]
            grouped[key][pair] = row
    result = []
    for (case, mode), pairs in sorted(grouped.items()):
        assert len(pairs) == 2*protocol['pairs']
        base = [pairs[i, 'baseline'] for i in range(protocol['pairs'])]
        candidate = [pairs[i, 'candidate'] for i in range(protocol['pairs'])]
        medians = {label: {metric: summary([row[metric] for row in rows]) for metric in metrics}
                   for label,rows in (('baseline',base),('candidate',candidate))}
        base_ms = medians['baseline']['api_ms']['median']
        candidate_ms = medians['candidate']['api_ms']['median']
        threshold = max(base_ms*1.05, base_ms+2) if mode == 'none' else max(base_ms*1.15, base_ms+5)
        signatures = {label: sorted({json.dumps({key:row[key] for key in observations}, sort_keys=True)
                                    for row in rows})
                      for label,rows in (('baseline',base),('candidate',candidate))}
        paired_changes = [(c['api_ms']/b['api_ms']-1)*100 for b,c in zip(base,candidate)]
        result.append(dict(case=case,mode=mode,metrics=medians,
                           change_percent=(candidate_ms/base_ms-1)*100,
                           paired_change_percent=summary(paired_changes),
                           slower_pairs=sum(value>0 for value in paired_changes),
                           gate='PASS' if candidate_ms<=threshold else 'FAIL',
                           threshold_ms=threshold,
                           observations={label:[json.loads(s) for s in values]
                                         for label,values in signatures.items()},
                           observations_match=all(
                               all(b[key]==c[key] for key in observations)
                               for b,c in zip(base,candidate)),
                           semantic_observations_match=all(
                               all(b[key]==c[key] for key in observations if key != 'solver_calls')
                               for b,c in zip(base,candidate)),
                           same_core_pairs=sum(b['core_ids']==c['core_ids'] for b,c in zip(base,candidate))))
    rss_summary = {label: summary(values) for label,values in rss.items()}
    rss_gate = rss_summary['candidate']['median'] <= max(
        rss_summary['baseline']['median']*1.10, rss_summary['baseline']['median']+8192)
    payload = dict(protocol=protocol,combinations=len(result), rows=result,
                   rss_kib=rss_summary,rss_gate='PASS' if rss_gate else 'FAIL')
    args.output.write_text(json.dumps(payload,indent=2)+'\n')
    print('Combinations:',len(result),'timing failures:',sum(row['gate']=='FAIL' for row in result))
    print('Outcome/call-count mismatches:',sum(not row['observations_match'] for row in result))
    print('RSS:',rss_summary,'gate:',payload['rss_gate'])
    for row in result:
        print('%s/%s: %+.2f%% %s, %d slower pairs' %
              (row['case'],row['mode'],row['change_percent'],row['gate'],row['slower_pairs']))


if __name__ == '__main__':
    main()
