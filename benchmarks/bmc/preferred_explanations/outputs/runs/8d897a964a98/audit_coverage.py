import hashlib
import json
import re
import subprocess
from pathlib import Path
coverage = json.loads(Path('/tmp/preferred-final-coverage.json').read_text())
diff = subprocess.check_output(['git', 'diff', 'a20d8e6d5b00efbf58edeb4db9890a05bef4e74e', '--unified=0', '--', 'pyfcstm'], text=True)
changed = {}
for line in diff.splitlines():
    if line.startswith('+++ b/'):
        path = line[6:]
        changed[path] = set()
    elif line.startswith('@@'):
        match = re.search(r'\+(\d+)(?:,(\d+))?', line)
        start, count = int(match[1]), int(match[2] or 1)
        changed[path].update(range(start, start + count))
report = {}
for path, lines in changed.items():
    measured = coverage['files'][path]
    report[path] = {
        'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'covered_statements': sorted(lines.intersection(measured['executed_lines'])),
        'missing_statements': sorted(lines.intersection(measured['missing_lines'])),
        'covered_arcs': [arc for arc in measured['executed_branches'] if arc[0] in lines],
        'missing_arcs': [arc for arc in measured['missing_branches'] if arc[0] in lines],
    }
    assert not report[path]['missing_statements'], path
    assert not report[path]['missing_arcs'], path
print(json.dumps(report, indent=2))
