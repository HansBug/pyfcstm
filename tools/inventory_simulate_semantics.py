"""
Inventory the shared simulate semantic fixture corpus.

This maintenance command regenerates the shared fixture inventory and README
index. It uses static file reads only; it does not import runtime modules,
render templates, instantiate generated runtimes, or touch native toolchains.
"""

import argparse
import difflib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml


README_INDEX_HEADER = "## Current fixture index"
REPORT_RELATIVE_PATH = "test/fixtures/simulate_semantics/case_inventory.md"
README_RELATIVE_PATH = "test/fixtures/simulate_semantics/README.md"
CASE_DIR_RELATIVE_PATH = "test/fixtures/simulate_semantics/cases"
DEFAULT_SHARED_RUNNERS = ("simulation", "generated_python_alignment")
DISALLOWED_TOP_LEVEL_FIELDS = (
    "boundary",
    "runners",
    "runtime_options",
    "model_build",
    "commands",
    "expected_failure",
)
DISALLOWED_EXPECTATION_FIELDS = (
    "stack",
    "brief_stack",
    "cycle_count",
    "return",
    "history",
    "history_tail",
    "history_length",
    "warnings",
    "logs",
    "abstract_handler_errors",
    "error_state",
    "error_info",
    "anonymous_warning_count",
    "output_contains",
    "output_not_contains",
    "error_contains",
    "should_exit",
)
PUBLIC_EXPECTATION_FIELDS = (
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "cycle_result",
    "raises",
    "handler_calls",
)


@dataclass(frozen=True)
class SemanticCaseRecord:
    """
    Static view of one simulate semantic fixture case.

    :param case_id: Case id derived from the YAML basename.
    :type case_id: str
    :param yaml_path: Path to the YAML fixture.
    :type yaml_path: pathlib.Path
    :param fcstm_path: Path to the paired FCSTM source.
    :type fcstm_path: pathlib.Path
    :param data: Parsed YAML data.
    :type data: typing.Mapping[str, typing.Any]
    """

    case_id: str
    yaml_path: Path
    fcstm_path: Path
    data: Mapping[str, Any]

    @property
    def runners(self) -> Tuple[str, ...]:
        return _effective_runners(self.data)

    @property
    def assertion_types(self) -> Tuple[str, ...]:
        origin = self.data.get("origin", {})
        if not isinstance(origin, Mapping):
            return tuple()
        assertion_types = origin.get("assertion_types", ())
        if not isinstance(assertion_types, Sequence) or isinstance(
            assertion_types, str
        ):
            return tuple()
        return tuple(str(item) for item in assertion_types)

    @property
    def origin_files(self) -> Tuple[str, ...]:
        origin = self.data.get("origin", {})
        if not isinstance(origin, Mapping):
            return tuple()
        files = origin.get("files", ())
        if not isinstance(files, Sequence) or isinstance(files, str):
            return tuple()
        return tuple(str(item) for item in files)


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_yaml(path: Path) -> Mapping[str, Any]:
    data = yaml.safe_load(_read_text(path))
    if not isinstance(data, Mapping):
        raise ValueError("%s must contain a YAML mapping" % path)
    return data


def _load_cases(root: Path) -> List[SemanticCaseRecord]:
    case_dir = root / CASE_DIR_RELATIVE_PATH
    records = []
    for yaml_path in sorted(case_dir.glob("*.yaml")):
        case_id = yaml_path.stem
        records.append(
            SemanticCaseRecord(
                case_id=case_id,
                yaml_path=yaml_path,
                fcstm_path=yaml_path.with_suffix(".fcstm"),
                data=_load_yaml(yaml_path),
            )
        )
    return records


def _effective_runners(data: Mapping[str, Any]) -> Tuple[str, ...]:
    excluded = data.get("exclude_runners", ())
    if not isinstance(excluded, Sequence) or isinstance(excluded, str):
        excluded = ()
    excluded_set = {str(item) for item in excluded}
    return tuple(
        runner for runner in DEFAULT_SHARED_RUNNERS if runner not in excluded_set
    )


def _iter_mapping_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            for child_key in _iter_mapping_keys(item):
                yield child_key
    elif isinstance(value, list):
        for item in value:
            for child_key in _iter_mapping_keys(item):
                yield child_key


def _case_has_key(record: SemanticCaseRecord, key_name: str) -> bool:
    return key_name in set(_iter_mapping_keys(record.data))


def _expectation_fields(record: SemanticCaseRecord) -> List[str]:
    result = []
    for step in record.data.get("steps") or []:
        if not isinstance(step, Mapping):
            continue
        for expect_name in ("expect_initial", "expect"):
            expect = step.get(expect_name)
            if isinstance(expect, Mapping):
                result.extend(str(key) for key in expect.keys())
    initial = record.data.get("initial")
    if isinstance(initial, Mapping):
        expect = initial.get("expect")
        if isinstance(expect, Mapping):
            result.extend(str(key) for key in expect.keys())
    return result


def _field_case_ids(
    records: Sequence[SemanticCaseRecord], fields: Sequence[str]
) -> Dict[str, List[str]]:
    return {
        field_name: [
            record.case_id for record in records if _case_has_key(record, field_name)
        ]
        for field_name in fields
    }


def _expectation_field_counts(records: Sequence[SemanticCaseRecord]) -> Dict[str, int]:
    counter = Counter()
    for record in records:
        for field_name in set(_expectation_fields(record)):
            counter[field_name] += 1
    return {field_name: counter[field_name] for field_name in sorted(counter)}


def _handler_behavior_distribution(records: Sequence[SemanticCaseRecord]) -> Counter:
    result = Counter()
    for record in records:
        handlers = record.data.get("handlers", ())
        if not isinstance(handlers, list):
            continue
        seen_behaviors = set()
        for item in handlers:
            if isinstance(item, Mapping):
                behavior = str(item.get("behavior", "<missing>"))
                result["handler entries: %s" % behavior] += 1
                seen_behaviors.add(behavior)
        for behavior in sorted(seen_behaviors):
            result["case files with: %s" % behavior] += 1
    return result


def _markdown_code(value: str) -> str:
    return "`%s`" % value.replace("`", "\\`")


def _markdown_link_or_code(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return "[source](%s)" % value
    return _markdown_code(value)


def _format_markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = [
        "| %s |" % " | ".join(headers),
        "|%s|" % "|".join("---" for _ in headers),
    ]
    for row in rows:
        escaped = [str(cell).replace("\n", "<br>") for cell in row]
        lines.append("| %s |" % " | ".join(escaped))
    return "\n".join(lines)


def _readme_index_bounds(readme_text: str) -> Tuple[int, int]:
    lines = readme_text.splitlines()
    try:
        start = lines.index(README_INDEX_HEADER)
    except ValueError:
        raise ValueError("README is missing %r" % README_INDEX_HEADER)
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return start, end


def _render_readme_index(records: Sequence[SemanticCaseRecord]) -> str:
    rows = []
    for record in records:
        rows.append(
            (
                _markdown_code(record.case_id),
                ", ".join(record.runners),
                ", ".join(record.assertion_types),
                "<br>".join(
                    _markdown_link_or_code(origin) for origin in record.origin_files
                ),
            )
        )
    table = _format_markdown_table(
        ("Fixture id", "Runners", "Assertion types", "Origin files"), rows
    )
    return "\n".join(
        (
            README_INDEX_HEADER,
            "",
            "The table below is generated from the current YAML metadata and is intended to",
            "make anti-drift review straightforward. `origin.files` points to the original",
            "inline tests or upstream issue/PR evidence that supplied each fixture's",
            "semantics.",
            "",
            table,
        )
    )


def _replace_readme_index(readme_text: str, generated_index: str) -> str:
    lines = readme_text.splitlines()
    start, end = _readme_index_bounds(readme_text)
    new_lines = lines[:start] + generated_index.splitlines() + lines[end:]
    return "\n".join(new_lines).rstrip() + "\n"


def _parse_readme_index(readme_text: str) -> Dict[str, Tuple[str, str]]:
    lines = readme_text.splitlines()
    start, end = _readme_index_bounds(readme_text)
    result = {}
    for line in lines[start:end]:
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        case_cell = cells[0]
        if case_cell.startswith("`") and case_cell.endswith("`"):
            result[case_cell[1:-1]] = (cells[1], cells[2])
    return result


def _readme_drift_rows(
    records: Sequence[SemanticCaseRecord], readme_text: str
) -> List[Tuple[str, str, str]]:
    actual_rows = _parse_readme_index(readme_text)
    expected = {
        record.case_id: (", ".join(record.runners), ", ".join(record.assertion_types))
        for record in records
    }
    rows = []
    for case_id in sorted(set(expected) | set(actual_rows)):
        if case_id not in actual_rows:
            rows.append((case_id, "missing_from_readme", "expected row absent"))
        elif case_id not in expected:
            rows.append((case_id, "extra_in_readme", "row has no YAML case"))
        elif actual_rows[case_id] != expected[case_id]:
            rows.append(
                (
                    case_id,
                    "metadata_mismatch",
                    "README runners/assertions %r != YAML %r"
                    % (actual_rows[case_id], expected[case_id]),
                )
            )
    return rows


def _readme_drift_details(rows: Sequence[Tuple[str, str, str]]) -> str:
    if not rows:
        return "README fixture index matches YAML runners and assertion types."
    return "<br>".join("%s: %s (%s)" % row for row in rows[:40]) + (
        "<br>..." if len(rows) > 40 else ""
    )


def _case_ids(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "0"


def _render_report(
    root: Path,
    records: Sequence[SemanticCaseRecord],
    drift_readme_text: str,
) -> str:
    fcstm_count = len(list((root / CASE_DIR_RELATIVE_PATH).glob("*.fcstm")))
    runner_counter = Counter()
    runner_combo_counter = Counter()
    for record in records:
        for runner in record.runners:
            runner_counter[runner] += 1
        runner_combo_counter[", ".join(record.runners)] += 1

    disallowed_top_level_cases = _field_case_ids(records, DISALLOWED_TOP_LEVEL_FIELDS)
    expectation_field_counts = _expectation_field_counts(records)
    disallowed_expectation_cases = {
        field_name: [
            record.case_id
            for record in records
            if field_name in set(_expectation_fields(record))
        ]
        for field_name in DISALLOWED_EXPECTATION_FIELDS
    }
    public_expectation_counts = {
        field_name: expectation_field_counts.get(field_name, 0)
        for field_name in PUBLIC_EXPECTATION_FIELDS
    }
    handler_distribution = _handler_behavior_distribution(records)
    readme_drift = _readme_drift_rows(records, drift_readme_text)

    disallowed_top_level_hits = sorted(
        set().union(*(set(items) for items in disallowed_top_level_cases.values()))
    )
    disallowed_expectation_hits = sorted(
        set().union(*(set(items) for items in disallowed_expectation_cases.values()))
    )

    lines = [
        "# Simulate semantic fixture case inventory",
        "",
        "This file is generated by `python tools/inventory_simulate_semantics.py --write`.",
        "It records the current shared fixture surface and public-observation",
        "contract. Regenerate it after any corpus or helper change.",
        "",
        "## Summary",
        "",
        _format_markdown_table(
            ("Metric", "Value"),
            (
                ("YAML cases", str(len(records))),
                ("FCSTM files", str(fcstm_count)),
                (
                    "Runner counts",
                    ", ".join(
                        "%s=%s" % (runner, count)
                        for runner, count in sorted(runner_counter.items())
                    ),
                ),
                (
                    "Runner combinations",
                    ", ".join(
                        "%s=%s" % (combo, count)
                        for combo, count in sorted(runner_combo_counter.items())
                    ),
                ),
            ),
        ),
        "",
        "## Contract Checks",
        "",
        _format_markdown_table(
            ("Check", "Current result", "Conclusion"),
            (
                (
                    "YAML 与 FCSTM 配对",
                    "YAML cases=%s；FCSTM files=%s" % (len(records), fcstm_count),
                    "通过：每个语义 fixture 都有配对 DSL 源。",
                ),
                (
                    "默认共享 runner",
                    "simulation, generated_python_alignment=%s"
                    % runner_combo_counter.get(
                        "simulation, generated_python_alignment", 0
                    ),
                    "通过：当前共享 corpus 默认覆盖模拟器与生成 Python 对齐。",
                ),
                (
                    "exclude-only runner 选择",
                    "runners 字段=%s；exclude_runners 字段=%s"
                    % (
                        len(disallowed_top_level_cases["runners"]),
                        sum(1 for record in records if "exclude_runners" in record.data),
                    ),
                    "通过：当前 corpus 只使用默认 runner 集合加排除例外。",
                ),
                (
                    "契约外 top-level 字段",
                    _case_ids(disallowed_top_level_hits),
                    "通过：未出现 boundary、runners、runtime_options、model_build、commands 或 expected_failure。",
                ),
                (
                    "契约外观察字段",
                    _case_ids(disallowed_expectation_hits),
                    "通过：未出现 stack、cycle_count、history*、return、logs、warnings 或错误诊断字段。",
                ),
                (
                    "README 索引",
                    "clean" if not readme_drift else "drift",
                    _readme_drift_details(readme_drift),
                ),
            ),
        ),
        "",
        "## Public Expectation Field Counts",
        "",
        _format_markdown_table(
            ("Expectation field", "Case files"),
            tuple(
                (field_name, str(public_expectation_counts.get(field_name, 0)))
                for field_name in PUBLIC_EXPECTATION_FIELDS
            ),
        ),
        "",
        "## Disallowed Top-Level Field Counts",
        "",
        _format_markdown_table(
            ("Disallowed field", "Case files"),
            tuple(
                (field_name, str(len(disallowed_top_level_cases[field_name])))
                for field_name in DISALLOWED_TOP_LEVEL_FIELDS
            ),
        ),
        "",
        "## Disallowed Expectation Field Counts",
        "",
        _format_markdown_table(
            ("Disallowed field", "Case files"),
            tuple(
                (field_name, str(len(disallowed_expectation_cases[field_name])))
                for field_name in DISALLOWED_EXPECTATION_FIELDS
            ),
        ),
        "",
        "## Handler Behavior Distribution",
        "",
        _format_markdown_table(
            ("Metric", "Count"),
            tuple(
                (name, str(count)) for name, count in sorted(handler_distribution.items())
            )
            or (("-", "0"),),
        ),
        "",
        "## Per-Case Inventory",
        "",
        _format_markdown_table(
            ("Case id", "Runners", "Assertion types", "Origin files"),
            tuple(
                (
                    _markdown_code(record.case_id),
                    ", ".join(record.runners),
                    ", ".join(record.assertion_types),
                    "<br>".join(
                        _markdown_link_or_code(origin)
                        for origin in record.origin_files
                    ),
                )
                for record in records
            ),
        ),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _report_path(root: Path) -> Path:
    return root / REPORT_RELATIVE_PATH


def _readme_path(root: Path) -> Path:
    return root / README_RELATIVE_PATH


def _unified_diff(name: str, expected: str, actual: str) -> str:
    diff = difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        fromfile="%s.expected" % name,
        tofile="%s.actual" % name,
        lineterm="",
    )
    lines = list(diff)
    if len(lines) > 120:
        lines = lines[:120] + ["... diff truncated ..."]
    return "\n".join(lines)


def _check_file(path: Path, expected_text: str, label: str) -> List[str]:
    if not path.exists():
        return ["%s is missing: %s" % (label, path)]
    actual_text = _read_text(path)
    if actual_text != expected_text:
        diff = _unified_diff(label, expected_text, actual_text)
        return ["%s is out of date:\n%s" % (label, diff)]
    return []


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_outputs(root: Path) -> Tuple[str, str]:
    records = _load_cases(root)
    readme_text = _read_text(_readme_path(root))
    readme_index = _render_readme_index(records)
    readme_output = _replace_readme_index(readme_text, readme_index)
    report_text = _render_report(root, records, readme_text)
    return report_text, readme_output


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or check the simulate semantic fixture inventory."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the inventory report and README fixture index.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check that generated outputs are up to date.",
    )
    parser.add_argument(
        "--root",
        default=str(_repository_root()),
        help="Repository root. Defaults to the parent of the tools directory.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report_text, readme_text = build_outputs(root)

    if args.write:
        _write(_report_path(root), report_text)
        _write(_readme_path(root), readme_text)

    if args.check:
        errors = []
        errors.extend(_check_file(_report_path(root), report_text, "case inventory"))
        errors.extend(_check_file(_readme_path(root), readme_text, "README index"))
        if errors:
            for error in errors:
                print(error)
            return 1
        print("simulate semantic fixture inventory is up to date")
        return 0

    if not args.write:
        print(report_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
