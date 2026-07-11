"""Render concise evidence from the fixed dynamic-validation checker."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_dynamic_validation import (  # noqa: E402
    DEFAULT_CASES_ROOT,
    run_checker,
)


def _case_evidence(case):
    data = case.to_json()
    expected = dict(data["key_expected"])
    expected.pop("source", None)
    return {
        "case": data["case_id"],
        "detected_problem": data["detected_problem"],
        "expected_actual": {
            "expected": expected,
            "actual": data["actual"],
        },
        "matched": data["matched"],
        "matched_evidence": data["matched_evidence"],
    }


def main():
    """Run the four immutable fixtures and print report-backed evidence."""
    result = run_checker(DEFAULT_CASES_ROOT, check=True)
    mutation_phase = next(
        phase for phase in result.phases if phase.name == "negative_mutation"
    )
    mutation_case = mutation_phase.cases[0].to_json()
    integrity = {
        "status": result.source_fixture_integrity["status"],
        "algorithm": result.source_fixture_integrity["algorithm"],
        "read_only": result.source_fixture_integrity["read_only"],
        "files": [
            {
                "file": Path(item["path"]).name,
                "before_sha256": item["before_sha256"],
                "after_sha256": item["after_sha256"],
                "unchanged": item["unchanged"],
            }
            for item in result.source_fixture_integrity["files"]
        ],
    }
    evidence = {
        "status": result.status,
        "required_cases": list(result.required_cases),
        "cases": [_case_evidence(case) for case in result.cases],
        "mutation_counterexample": {
            "status": mutation_phase.status,
            "message": mutation_phase.message,
            "case": mutation_case["case_id"],
            "error_type": mutation_case["error_type"],
            "matched": mutation_case["matched"],
            "raw_message": mutation_case["raw_message"],
            "matched_evidence": mutation_case["matched_evidence"],
        },
        "source_fixture_integrity": integrity,
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
