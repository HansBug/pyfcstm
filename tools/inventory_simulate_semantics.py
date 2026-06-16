"""
Inventory the shared simulate semantic fixture corpus.

This maintenance command reports the shared fixture surface and checks the
long-term Markdown and runner-selection contract. It uses static file reads
only; it does not import runtime modules, render templates, instantiate
generated runtimes, or touch native toolchains.
"""

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml


README_RELATIVE_PATH = "test/fixtures/simulate_semantics/README.md"
SCHEMA_RELATIVE_PATH = "test/fixtures/simulate_semantics/schema.md"
FIXTURE_DIR_RELATIVE_PATH = "test/fixtures/simulate_semantics"
CASE_DIR_RELATIVE_PATH = "test/fixtures/simulate_semantics/cases"
DEFAULT_SHARED_RUNNERS = ("simulation", "generated_python_alignment")
ALLOWED_MARKDOWN_FILES = ("README.md", "schema.md")
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
    "cycle_result",
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
            record.case_id for record in records if field_name in record.data
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


def _format_markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = [
        "| %s |" % " | ".join(headers),
        "|%s|" % "|".join("---" for _ in headers),
    ]
    for row in rows:
        escaped = [str(cell).replace("\n", "<br>") for cell in row]
        lines.append("| %s |" % " | ".join(escaped))
    return "\n".join(lines)


def _case_ids(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "0"


def _render_report(
    root: Path,
    records: Sequence[SemanticCaseRecord],
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

    disallowed_top_level_hits = sorted(
        set().union(*(set(items) for items in disallowed_top_level_cases.values()))
    )
    disallowed_expectation_hits = sorted(
        set().union(*(set(items) for items in disallowed_expectation_cases.values()))
    )
    markdown_files = _fixture_markdown_files(root)
    markdown_file_names = [path.name for path in markdown_files]

    lines = [
        "# Simulate semantic fixture inventory",
        "",
        "This command reports the current shared fixture surface and public-observation",
        "contract. Use `--check` as the maintenance gate after any corpus or helper",
        "change; it does not write generated Markdown snapshots into the repository.",
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
                    "通过：未出现 stack、cycle_count、history*、cycle_result、return、logs、warnings 或错误诊断字段。",
                ),
                (
                    "长期 Markdown 文件",
                    ", ".join(markdown_file_names) if markdown_file_names else "0",
                    "通过：顶层只保留 README.md 和 schema.md。"
                    if tuple(markdown_file_names) == ALLOWED_MARKDOWN_FILES
                    else "失败：顶层 Markdown 文件清单不符合长期维护口径。",
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
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _readme_path(root: Path) -> Path:
    return root / README_RELATIVE_PATH


def _schema_path(root: Path) -> Path:
    return root / SCHEMA_RELATIVE_PATH


def _fixture_markdown_files(root: Path) -> List[Path]:
    return sorted((root / FIXTURE_DIR_RELATIVE_PATH).glob("*.md"))


def _paired_file_errors(root: Path, records: Sequence[SemanticCaseRecord]) -> List[str]:
    case_dir = root / CASE_DIR_RELATIVE_PATH
    yaml_ids = {record.case_id for record in records}
    fcstm_ids = {path.stem for path in case_dir.glob("*.fcstm")}
    errors = []
    for case_id in sorted(yaml_ids - fcstm_ids):
        errors.append("YAML fixture 缺少配对 FCSTM：%s.yaml" % case_id)
    for case_id in sorted(fcstm_ids - yaml_ids):
        errors.append("FCSTM fixture 缺少配对 YAML：%s.fcstm" % case_id)
    for record in records:
        source = record.data.get("source")
        if not isinstance(source, Mapping):
            errors.append("%s 缺少 source mapping" % record.case_id)
            continue
        source_fcstm = source.get("fcstm")
        if source_fcstm != record.fcstm_path.name:
            errors.append(
                "%s 的 source.fcstm=%r，应为 %r"
                % (record.case_id, source_fcstm, record.fcstm_path.name)
            )
    return errors


def _markdown_contract_errors(root: Path) -> List[str]:
    errors = []
    readme_path = _readme_path(root)
    schema_path = _schema_path(root)
    if not readme_path.exists():
        errors.append("shared fixture README 缺失：%s" % readme_path)
    if not schema_path.exists():
        errors.append("shared fixture schema 缺失：%s" % schema_path)

    markdown_names = tuple(path.name for path in _fixture_markdown_files(root))
    if markdown_names != ALLOWED_MARKDOWN_FILES:
        errors.append(
            "shared fixture 顶层 Markdown 只能是 %s，当前是 %s"
            % (", ".join(ALLOWED_MARKDOWN_FILES), ", ".join(markdown_names) or "0")
        )

    if readme_path.exists():
        readme_text = _read_text(readme_path)
        if "## Current fixture index" in readme_text:
            errors.append("README 仍包含旧的 generated fixture index 章节")
        if "generated fixture index" in readme_text.lower():
            errors.append("README 仍包含 generated fixture index 口径")
    return errors


def _runner_field_errors(root: Path) -> List[str]:
    errors = []
    pattern = re.compile(r"^[ \t]*runners:", re.MULTILINE)
    for yaml_path in sorted((root / CASE_DIR_RELATIVE_PATH).glob("*.yaml")):
        if pattern.search(_read_text(yaml_path)):
            errors.append("shared fixture 禁止 include-style runners 字段：%s" % yaml_path)
    return errors


def _field_contract_errors(records: Sequence[SemanticCaseRecord]) -> List[str]:
    errors = []
    disallowed_top_level_cases = _field_case_ids(records, DISALLOWED_TOP_LEVEL_FIELDS)
    for field_name in DISALLOWED_TOP_LEVEL_FIELDS:
        case_ids = disallowed_top_level_cases[field_name]
        if case_ids:
            errors.append(
                "shared fixture 顶层字段 %s 不属于长期契约，命中：%s"
                % (field_name, _case_ids(case_ids))
            )

    for field_name in DISALLOWED_EXPECTATION_FIELDS:
        case_ids = [
            record.case_id
            for record in records
            if field_name in set(_expectation_fields(record))
        ]
        if case_ids:
            errors.append(
                "shared fixture 观察字段 %s 不属于公开观察面，命中：%s"
                % (field_name, _case_ids(case_ids))
            )
    return errors


def _contract_errors(root: Path, records: Sequence[SemanticCaseRecord]) -> List[str]:
    errors = []
    errors.extend(_paired_file_errors(root, records))
    errors.extend(_markdown_contract_errors(root))
    errors.extend(_runner_field_errors(root))
    errors.extend(_field_contract_errors(records))
    return errors


def build_report(root: Path) -> str:
    records = _load_cases(root)
    return _render_report(root, records)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report or check the simulate semantic fixture inventory."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the long-term shared fixture maintenance contract.",
    )
    parser.add_argument(
        "--root",
        default=str(_repository_root()),
        help="Repository root. Defaults to the parent of the tools directory.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    records = _load_cases(root)

    if args.check:
        errors = _contract_errors(root, records)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("simulate semantic fixture maintenance checks passed")
        return 0

    print(_render_report(root, records), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
