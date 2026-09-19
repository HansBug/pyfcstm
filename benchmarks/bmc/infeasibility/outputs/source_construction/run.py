"""Sequential interleaved source snapshots; no concurrent local benchmarks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
baseline = root.parent / 'baseline'
candidate = Path('/home/zhangshaoang/oo-projects/pyfcstm-2')
variants = [('baseline', baseline, False), ('default', candidate, False), ('recorded', candidate, True)]
hashes = {}
for label, source, record in variants:
    digest = hashlib.sha256()
    for path in sorted((source / 'pyfcstm').rglob('*.py')):
        digest.update(str(path.relative_to(source)).encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
    hashes[label] = digest.hexdigest()
with (root / 'samples.jsonl').open('x', encoding='utf-8') as output:
    output.write(json.dumps(dict(kind='protocol', baseline_commit='7cea5bed917fc57fa3524ac866075f4f4ef5db1a',
                                groups=7, warmups_per_worker=1, python_hash_seed=0, source_hashes=hashes,
                                artifact_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                 for p in (Path(__file__), root/'worker.py', root/'workloads.json')},
                                host='shared Linux host; sequential local work; external load not controlled'))+'\n')
    output.flush()
    for group in range(7):
        order = variants[group % 3:] + variants[:group % 3]
        for label, source, record in order:
            args = [sys.executable, str(root / 'worker.py'), str(source), str(19200 + group)]
            if record:
                args.append('--record')
            result = subprocess.run(args, text=True, stdout=subprocess.PIPE, check=True, timeout=600,
                                    env=dict(os.environ, PYTHONHASHSEED='0'))
            output.write(json.dumps(dict(kind='sample', group=group, variant=label, result=json.loads(result.stdout)))+'\n')
            output.flush()
