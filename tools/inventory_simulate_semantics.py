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
    "id",
    "source",
    "runners",
    "runtime_options",
    "model_build",
    "commands",
    "expected_failure",
)
DISALLOWED_ORIGIN_FIELDS = ("assertion_types",)
DISALLOWED_STEP_FIELDS = ("expect_initial",)
DISALLOWED_EXPECTATION_FIELDS = (
    "stack",
    "brief_stack",
    "cycle_count",
    "cycle_result",
    "return",
    "input_events",
    "consumed_events",
    "unconsumed_events",
    "event_accounting",
    "event_ledger",
    "event_log",
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
LEGACY_CYCLE_SHAPES = (
    "cycle_null",
    "cycle_mapping",
    "cycle_empty_mapping",
    "cycle_events_mapping",
    "cycle_event_descriptor",
)
LEGACY_PATH_SHAPES = (
    "initial_state_list",
    "expect_state_list",
    "handler_active_leaf_list",
)
PUBLIC_EXPECTATION_FIELDS = (
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "delta",
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
        expect = step.get("expect")
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
        field_name: [record.case_id for record in records if field_name in record.data]
        for field_name in fields
    }


def _origin_field_case_ids(
    records: Sequence[SemanticCaseRecord], fields: Sequence[str]
) -> Dict[str, List[str]]:
    return {
        field_name: [
            record.case_id
            for record in records
            if isinstance(record.data.get("origin"), Mapping)
            and field_name in record.data["origin"]
        ]
        for field_name in fields
    }


def _step_field_case_ids(
    records: Sequence[SemanticCaseRecord], fields: Sequence[str]
) -> Dict[str, List[str]]:
    return {
        field_name: [
            record.case_id
            for record in records
            if any(
                isinstance(step, Mapping) and field_name in step
                for step in record.data.get("steps") or []
            )
        ]
        for field_name in fields
    }


def _expectation_field_counts(records: Sequence[SemanticCaseRecord]) -> Dict[str, int]:
    counter = Counter()
    for record in records:
        for field_name in set(_expectation_fields(record)):
            counter[field_name] += 1
    return {field_name: counter[field_name] for field_name in sorted(counter)}


def _unknown_expectation_field_case_ids(
    records: Sequence[SemanticCaseRecord],
) -> Dict[str, List[str]]:
    known_fields = set(PUBLIC_EXPECTATION_FIELDS) | set(DISALLOWED_EXPECTATION_FIELDS)
    result = {}
    for record in records:
        for field_name in set(_expectation_fields(record)) - known_fields:
            result.setdefault(field_name, []).append(record.case_id)
    return {field_name: result[field_name] for field_name in sorted(result)}


def _step_count(records: Sequence[SemanticCaseRecord]) -> int:
    return sum(
        len(record.data.get("steps") or [])
        for record in records
        if isinstance(record.data.get("steps") or [], list)
    )


def _cycle_shape_counts(records: Sequence[SemanticCaseRecord]) -> Counter:
    result = Counter()
    for record in records:
        for step in record.data.get("steps") or []:
            if not isinstance(step, Mapping):
                continue
            if "cycle_count" in step:
                result["steps with cycle_count"] += 1
            if "cycle" not in step:
                result["steps without cycle"] += 1
                continue
            cycle = step["cycle"]
            if cycle is None:
                result["cycle_null"] += 1
            elif isinstance(cycle, str):
                result["cycle_string"] += 1
            elif isinstance(cycle, list):
                if not cycle:
                    result["cycle_empty_list"] += 1
                else:
                    result["cycle_list"] += 1
                if any(isinstance(item, Mapping) for item in cycle):
                    result["cycle_event_descriptor"] += 1
            elif isinstance(cycle, Mapping):
                result["cycle_mapping"] += 1
                if not cycle:
                    result["cycle_empty_mapping"] += 1
                if "events" in cycle:
                    result["cycle_events_mapping"] += 1
                    events = cycle.get("events")
                    if isinstance(events, list) and any(
                        isinstance(item, Mapping) for item in events
                    ):
                        result["cycle_event_descriptor"] += 1
            else:
                result["cycle_other"] += 1
    return result


def _legacy_cycle_shape_case_ids(
    records: Sequence[SemanticCaseRecord],
) -> Dict[str, List[str]]:
    result = {field_name: [] for field_name in LEGACY_CYCLE_SHAPES}
    for record in records:
        found = {field_name: False for field_name in LEGACY_CYCLE_SHAPES}
        for step in record.data.get("steps") or []:
            if not isinstance(step, Mapping) or "cycle" not in step:
                continue
            cycle = step["cycle"]
            if cycle is None:
                found["cycle_null"] = True
            elif isinstance(cycle, Mapping):
                found["cycle_mapping"] = True
                if not cycle:
                    found["cycle_empty_mapping"] = True
                if "events" in cycle:
                    found["cycle_events_mapping"] = True
                    events = cycle.get("events")
                    if isinstance(events, list) and any(
                        isinstance(item, Mapping) for item in events
                    ):
                        found["cycle_event_descriptor"] = True
            elif isinstance(cycle, list) and any(
                isinstance(item, Mapping) for item in cycle
            ):
                found["cycle_event_descriptor"] = True
        for field_name, present in found.items():
            if present:
                result[field_name].append(record.case_id)
    return result


def _legacy_path_shape_case_ids(
    records: Sequence[SemanticCaseRecord],
) -> Dict[str, List[str]]:
    result = {field_name: [] for field_name in LEGACY_PATH_SHAPES}
    for record in records:
        initial = record.data.get("initial")
        if isinstance(initial, Mapping) and isinstance(initial.get("state"), list):
            result["initial_state_list"].append(record.case_id)
        expect_state_hit = False
        handler_active_leaf_hit = False
        for step in record.data.get("steps") or []:
            if not isinstance(step, Mapping):
                continue
            expect = step.get("expect")
            if not isinstance(expect, Mapping):
                continue
            if isinstance(expect.get("state"), list):
                expect_state_hit = True
            calls = expect.get("handler_calls")
            if isinstance(calls, list) and any(
                isinstance(item, Mapping) and isinstance(item.get("active_leaf"), list)
                for item in calls
            ):
                handler_active_leaf_hit = True
        if expect_state_hit:
            result["expect_state_list"].append(record.case_id)
        if handler_active_leaf_hit:
            result["handler_active_leaf_list"].append(record.case_id)
    return result


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


def _format_markdown_table(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> str:
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
    disallowed_origin_cases = _origin_field_case_ids(records, DISALLOWED_ORIGIN_FIELDS)
    disallowed_step_cases = _step_field_case_ids(records, DISALLOWED_STEP_FIELDS)
    expectation_field_counts = _expectation_field_counts(records)
    disallowed_expectation_cases = {
        field_name: [
            record.case_id
            for record in records
            if field_name in set(_expectation_fields(record))
        ]
        for field_name in DISALLOWED_EXPECTATION_FIELDS
    }
    unknown_expectation_cases = _unknown_expectation_field_case_ids(records)
    legacy_cycle_cases = _legacy_cycle_shape_case_ids(records)
    legacy_path_cases = _legacy_path_shape_case_ids(records)
    public_expectation_counts = {
        field_name: expectation_field_counts.get(field_name, 0)
        for field_name in PUBLIC_EXPECTATION_FIELDS
    }
    cycle_shape_counts = _cycle_shape_counts(records)
    handler_distribution = _handler_behavior_distribution(records)

    disallowed_top_level_hits = sorted(
        set().union(*(set(items) for items in disallowed_top_level_cases.values()))
    )
    disallowed_origin_hits = sorted(
        set().union(*(set(items) for items in disallowed_origin_cases.values()))
    )
    disallowed_step_hits = sorted(
        set().union(*(set(items) for items in disallowed_step_cases.values()))
    )
    disallowed_expectation_hits = sorted(
        set().union(*(set(items) for items in disallowed_expectation_cases.values()))
    )
    unknown_expectation_hits = sorted(
        set().union(*(set(items) for items in unknown_expectation_cases.values()))
    )
    legacy_cycle_hits = sorted(
        set().union(*(set(items) for items in legacy_cycle_cases.values()))
    )
    legacy_path_hits = sorted(
        set().union(*(set(items) for items in legacy_path_cases.values()))
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
                ("Runtime steps", str(_step_count(records))),
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
                        sum(
                            1 for record in records if "exclude_runners" in record.data
                        ),
                    ),
                    "通过：当前 corpus 只使用默认 runner 集合加排除例外。",
                ),
                (
                    "契约外 top-level 字段",
                    _case_ids(disallowed_top_level_hits),
                    "通过：未出现 id/source、runners、runtime_options、model_build、commands 或 expected_failure。",
                ),
                (
                    "契约外 origin 字段",
                    _case_ids(disallowed_origin_hits),
                    "通过：未出现 origin.assertion_types 等旧维护提示字段。",
                ),
                (
                    "契约外 step 字段",
                    _case_ids(disallowed_step_hits),
                    "通过：未出现 expect_initial 等 retired step 字段。",
                ),
                (
                    "旧 cycle 形态",
                    _case_ids(legacy_cycle_hits),
                    "通过：未出现 cycle: {}、cycle.events、cycle: null 或 event descriptor。",
                ),
                (
                    "旧 path 形态",
                    _case_ids(legacy_path_hits),
                    "通过：state / active_leaf 均使用 dot-string 或 null。",
                ),
                (
                    "契约外观察字段",
                    _case_ids(
                        sorted(
                            set(disallowed_expectation_hits)
                            | set(unknown_expectation_hits)
                        )
                    ),
                    "通过：只出现 state、vars、vars_exact、vars_keys、vars_absent、ended、delta、raises 和 handler_calls 公开观察字段；未出现 event accounting 或其他私有观察字段。",
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
        "## Cycle Shape Counts",
        "",
        _format_markdown_table(
            ("Cycle shape", "Steps"),
            tuple(
                (name, str(cycle_shape_counts.get(name, 0)))
                for name in (
                    "cycle_empty_list",
                    "cycle_string",
                    "cycle_list",
                    "steps with cycle_count",
                    "steps without cycle",
                    "cycle_null",
                    "cycle_mapping",
                    "cycle_empty_mapping",
                    "cycle_events_mapping",
                    "cycle_event_descriptor",
                    "cycle_other",
                )
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
        "## Disallowed Origin Field Counts",
        "",
        _format_markdown_table(
            ("Disallowed field", "Case files"),
            tuple(
                (field_name, str(len(disallowed_origin_cases[field_name])))
                for field_name in DISALLOWED_ORIGIN_FIELDS
            ),
        ),
        "",
        "## Disallowed Step Field Counts",
        "",
        _format_markdown_table(
            ("Disallowed field", "Case files"),
            tuple(
                (field_name, str(len(disallowed_step_cases[field_name])))
                for field_name in DISALLOWED_STEP_FIELDS
            ),
        ),
        "",
        "## Legacy Cycle Shape Counts",
        "",
        _format_markdown_table(
            ("Legacy shape", "Case files"),
            tuple(
                (field_name, str(len(legacy_cycle_cases[field_name])))
                for field_name in LEGACY_CYCLE_SHAPES
            ),
        ),
        "",
        "## Legacy Path Shape Counts",
        "",
        _format_markdown_table(
            ("Legacy shape", "Case files"),
            tuple(
                (field_name, str(len(legacy_path_cases[field_name])))
                for field_name in LEGACY_PATH_SHAPES
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
        "## Unknown Expectation Field Counts",
        "",
        _format_markdown_table(
            ("Expectation field", "Case files"),
            tuple(
                (field_name, str(len(case_ids)))
                for field_name, case_ids in sorted(unknown_expectation_cases.items())
            )
            or (("-", "0"),),
        ),
        "",
        "## Handler Behavior Distribution",
        "",
        _format_markdown_table(
            ("Metric", "Count"),
            tuple(
                (name, str(count))
                for name, count in sorted(handler_distribution.items())
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
            errors.append(
                "shared fixture 禁止 include-style runners 字段：%s" % yaml_path
            )
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

    disallowed_origin_cases = _origin_field_case_ids(records, DISALLOWED_ORIGIN_FIELDS)
    for field_name in DISALLOWED_ORIGIN_FIELDS:
        case_ids = disallowed_origin_cases[field_name]
        if case_ids:
            errors.append(
                "shared fixture origin 字段 %s 不属于当前契约，命中：%s"
                % (field_name, _case_ids(case_ids))
            )

    disallowed_step_cases = _step_field_case_ids(records, DISALLOWED_STEP_FIELDS)
    for field_name in DISALLOWED_STEP_FIELDS:
        case_ids = disallowed_step_cases[field_name]
        if case_ids:
            errors.append(
                "shared fixture step 字段 %s 不属于当前契约，命中：%s"
                % (field_name, _case_ids(case_ids))
            )

    legacy_cycle_cases = _legacy_cycle_shape_case_ids(records)
    for field_name in LEGACY_CYCLE_SHAPES:
        case_ids = legacy_cycle_cases[field_name]
        if case_ids:
            errors.append(
                "shared fixture cycle 旧形态 %s 不属于当前契约，命中：%s"
                % (field_name, _case_ids(case_ids))
            )

    legacy_path_cases = _legacy_path_shape_case_ids(records)
    for field_name in LEGACY_PATH_SHAPES:
        case_ids = legacy_path_cases[field_name]
        if case_ids:
            errors.append(
                "shared fixture state path 旧形态 %s 不属于当前契约，命中：%s"
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

    unknown_expectation_cases = _unknown_expectation_field_case_ids(records)
    for field_name, case_ids in sorted(unknown_expectation_cases.items()):
        errors.append(
            "shared fixture 观察字段 %s 未在公开观察面中声明，命中：%s"
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
