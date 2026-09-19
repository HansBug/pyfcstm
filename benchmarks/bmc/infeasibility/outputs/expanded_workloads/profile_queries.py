"""Profile public query execution; diagnostic times are not benchmark samples."""

import argparse
import cProfile
import json
import pstats
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source.resolve()))
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    cases = {c['name']: c for c in json.loads(Path(__file__).with_name('workloads.json').read_text())}
    rows = []
    for name, mode in (('counter_bound_128', 'none'), ('pool', 'formal'), ('dose_editor', 'formal')):
        case = cases[name]

        def execute():
            model = load_state_machine_from_text(case['model'])
            return solve_bmc_property(compile_bmc_query(model, case['query']),
                                      infeasibility_explanation=mode, timeout_ms=30000)

        execute()
        for repetition in range(3):
            profiler = cProfile.Profile()
            result = profiler.runcall(execute)
            stats = pstats.Stats(profiler)
            functions = []
            for (file, line, function), (primitive, total, own, cumulative, callers) in stats.stats.items():
                if '/pyfcstm/' in file:
                    functions.append(dict(file='pyfcstm/'+file.split('/pyfcstm/',1)[1],
                                          line=line, function=function, primitive=primitive,
                                          calls=total, own_ms=own*1000,
                                          cumulative_ms=cumulative*1000))
            functions.sort(key=lambda r:r['cumulative_ms'], reverse=True)
            rows.append(dict(case=name,mode=mode,repetition=repetition,status=result.status,
                             total_ms=stats.total_tt*1000, functions=functions))
    args.output.write_text(json.dumps(rows,indent=2)+'\n')


if __name__ == '__main__':
    main()
