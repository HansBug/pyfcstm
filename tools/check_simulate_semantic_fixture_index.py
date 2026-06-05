"""
Validate the simulate semantic fixture README inventory.

This maintenance command checks that the ``Current migration index`` table in
``test/fixtures/simulate_semantics/README.md`` lists exactly the fixture case
files under ``test/fixtures/simulate_semantics/cases``.
"""

import argparse
import os
from collections import Counter


def _repository_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_case_dir():
    return os.path.join(
        _repository_root(),
        "test",
        "fixtures",
        "simulate_semantics",
        "cases",
    )


def _default_readme_path():
    return os.path.join(
        _repository_root(),
        "test",
        "fixtures",
        "simulate_semantics",
        "README.md",
    )


def _fixture_case_ids(case_dir):
    return sorted(
        os.path.splitext(name)[0]
        for name in os.listdir(case_dir)
        if name.endswith(".yaml")
    )


def _readme_migration_index_case_ids(readme_path):
    with open(readme_path, encoding="utf-8") as file:
        readme_lines = file.read().splitlines()

    start_index = readme_lines.index("## Current migration index") + 1
    end_index = next(
        (
            index
            for index in range(start_index, len(readme_lines))
            if readme_lines[index].startswith("## ")
        ),
        len(readme_lines),
    )
    case_ids = []
    for line in readme_lines[start_index:end_index]:
        if not line.startswith("| `"):
            continue
        first_cell = line.split("|", 2)[1].strip()
        if first_cell.startswith("`") and first_cell.endswith("`"):
            case_ids.append(first_cell[1:-1])
    return case_ids


def _format_items(items):
    if items:
        return ", ".join(items)
    return "[]"


def validate_fixture_index(case_dir, readme_path):
    fixture_case_ids = _fixture_case_ids(case_dir)
    readme_case_ids = _readme_migration_index_case_ids(readme_path)
    readme_case_counter = Counter(readme_case_ids)

    duplicate_readme_ids = sorted(
        case_id for case_id, count in readme_case_counter.items() if count > 1
    )
    fixture_case_id_set = set(fixture_case_ids)
    readme_case_id_set = set(readme_case_ids)
    missing_from_readme = sorted(fixture_case_id_set - readme_case_id_set)
    extra_in_readme = sorted(readme_case_id_set - fixture_case_id_set)

    return {
        "fixture_case_ids": fixture_case_ids,
        "readme_case_ids": readme_case_ids,
        "missing_from_readme": missing_from_readme,
        "extra_in_readme": extra_in_readme,
        "duplicate_readme_ids": duplicate_readme_ids,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the simulate semantic fixture README inventory."
    )
    parser.add_argument(
        "--case-dir",
        default=_default_case_dir(),
        help="Directory containing simulate semantic fixture YAML files.",
    )
    parser.add_argument(
        "--readme",
        default=_default_readme_path(),
        help="Path to the simulate semantic fixture README.",
    )
    args = parser.parse_args(argv)

    result = validate_fixture_index(args.case_dir, args.readme)
    print("yaml cases: {count}".format(count=len(result["fixture_case_ids"])))
    print("README rows: {count}".format(count=len(result["readme_case_ids"])))
    print("missing: {items}".format(items=_format_items(result["missing_from_readme"])))
    print("extra: {items}".format(items=_format_items(result["extra_in_readme"])))
    print(
        "duplicates: {items}".format(
            items=_format_items(result["duplicate_readme_ids"])
        )
    )

    has_errors = any(
        result[key]
        for key in (
            "missing_from_readme",
            "extra_in_readme",
            "duplicate_readme_ids",
        )
    )
    if has_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
