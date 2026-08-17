"""Check that Python and jsfcstm structure-statistics fixtures stay identical."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PYTHON_FIXTURE = ROOT / "test" / "diagnostics" / "fixtures" / "structure_statistics_parity.json"
JS_FIXTURE = ROOT / "editors" / "jsfcstm" / "test" / "fixtures" / "structure_statistics_parity.json"


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        # OSError identifies a missing or unreadable fixture.
        raise SystemExit(f"cannot read {path}: {error}") from error


def _load(raw: bytes, path: Path):
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        # UnicodeDecodeError identifies a non-UTF-8 fixture; JSONDecodeError
        # identifies a hand-edited fixture that is no longer valid JSON.
        raise SystemExit(f"cannot parse {path}: {error}") from error


def main() -> int:
    python_raw = _read(PYTHON_FIXTURE)
    js_raw = _read(JS_FIXTURE)
    if python_raw != js_raw:
        print("structure-statistics parity fixtures differ:", file=sys.stderr)
        print(f"  Python: {PYTHON_FIXTURE}", file=sys.stderr)
        print(f"  JS:     {JS_FIXTURE}", file=sys.stderr)
        return 1
    python_fixture = _load(python_raw, PYTHON_FIXTURE)
    js_fixture = _load(js_raw, JS_FIXTURE)
    if python_fixture != js_fixture:
        print("structure-statistics parity fixtures differ semantically:", file=sys.stderr)
        return 1
    if not isinstance(python_fixture, list) or not python_fixture:
        print("structure-statistics parity fixture must be a non-empty list", file=sys.stderr)
        return 1
    for index, case in enumerate(python_fixture):
        if not isinstance(case, dict):
            print(f"fixture case {index} is not an object", file=sys.stderr)
            return 1
        missing = {"name", "dsl", "policy", "expected"} - set(case)
        if missing:
            print(f"fixture case {index} is missing {sorted(missing)}", file=sys.stderr)
            return 1
    print(f"structure-statistics parity fixtures match ({len(python_fixture)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
