"""Run sequential baseline/candidate pairs; retain every worker observation.

Source snapshots are supplied explicitly. This Linux measurement script uses
the worker's process-wide ru_maxrss in KiB and does not time interpreter import.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pairs', type=int, default=9)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    worker = Path(__file__).with_name('worker.py')
    files = (worker, Path(__file__), worker.with_name('workloads.json'))
    environment = dict(os.environ, PYTHONHASHSEED='0')
    extra = [item for name in args.case or () for item in ('--case', name)]
    source_hashes = {}
    for label in ('baseline', 'candidate'):
        root = getattr(args, label).resolve()
        digest = hashlib.sha256()
        for path in sorted((root/'pyfcstm').rglob('*.py')):
            digest.update(str(path.relative_to(root)).encode('utf-8'))
            digest.update(b'\0')
            digest.update(path.read_bytes())
        source_hashes[label] = digest.hexdigest()
    with args.output.open('x', encoding='utf-8') as stream:
        header = dict(kind='protocol', pairs=args.pairs, first_seed=19200,
                      hashes={path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in files},
                      baseline=str(args.baseline.resolve()),
                      candidate=str(args.candidate.resolve()), cases=args.case,
                      python_source_sha256=source_hashes,
                      timeout_ms=30000, python_hash_seed=0)
        stream.write(json.dumps(header)+'\n')
        stream.flush()
        for repetition in range(args.pairs):
            order = ('baseline', 'candidate') if repetition % 2 == 0 else ('candidate', 'baseline')
            for label in order:
                completed = subprocess.run(
                    [sys.executable, str(worker), str(getattr(args, label)),
                     str(19200+repetition)] + extra,
                    text=True, stdout=subprocess.PIPE,
                    env=environment, check=True, timeout=1200,
                )
                result = json.loads(completed.stdout)
                result.update(kind='sample', revision=label, repetition=repetition)
                stream.write(json.dumps(result)+'\n')
                stream.flush()
                print('pair %d/%d %s: %d rows' %
                      (repetition+1, args.pairs, label, len(result['rows'])), flush=True)


if __name__ == '__main__':
    main()
