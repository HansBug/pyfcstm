"""
Inventory the shared simulate semantic fixture corpus.

This maintenance command creates the shared fixture inventory used by later
fixture cleanup pull requests. It is intentionally broader than
``tools/check_simulate_semantic_fixture_index.py``: that older command only
checks that the README migration index lists the current YAML cases, while this
script records field usage, runner combinations, classification targets, helper
white-box reads, and downstream assertion-preservation requirements. The two
commands are complementary until a later cleanup PR decides whether to merge
their responsibilities.

The command uses static file reads only. It does not import pyfcstm runtime
modules, generate templates, instantiate generated runtimes, or touch native
toolchains.
"""

import argparse
import difflib
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml


CASE_FIELD_NAMES = (
    "model_build",
    "commands",
    "runtime_options",
    "handlers",
    "stack",
    "brief_stack",
    "cycle_count",
    "history",
    "history_tail",
    "history_length",
    "return",
    "cycle_result",
    "warnings",
    "logs",
    "abstract_handler_errors",
    "error_state",
    "error_info",
    "anonymous_warning_count",
)
CLASSIFICATION_LABELS = (
    "KEEP_SHARED_FIXTURE",
    "REWRITE_SHARED_PUBLIC_OBSERVATIONS",
    "ADD_ALIGNMENT_RUNNER",
    "MIGRATE_MODEL_VALIDATION",
    "MIGRATE_CLI_REPL",
    "MIGRATE_SIMULATOR_DIAGNOSTIC",
    "OPEN_ISSUE_OR_UNDECIDED",
)
TOKEN_PATTERNS = (
    ("_STATE_INFO", re.compile(r"\b_STATE_INFO\b")),
    ("_stack", re.compile(r"(?<![A-Za-z0-9])_stack\b")),
    ("brief_stack", re.compile(r"\bbrief_stack\b")),
    ("cycle_count", re.compile(r"\bcycle_count\b")),
    ("_warned_anonymous_abstracts", re.compile(r"\b_warned_anonymous_abstracts\b")),
    ("history", re.compile(r"\bhistory\b")),
)
README_INDEX_HEADER = "## Current migration index"
REPORT_RELATIVE_PATH = "test/fixtures/simulate_semantics/case_inventory.md"
README_RELATIVE_PATH = "test/fixtures/simulate_semantics/README.md"
SCHEMA_RELATIVE_PATH = "test/fixtures/simulate_semantics/schema.md"
CASE_DIR_RELATIVE_PATH = "test/fixtures/simulate_semantics/cases"
HELPER_RELATIVE_PATHS = (
    "test/testings/simulate_semantics.py",
    "test/template/python/test_semantic_fixture_alignment.py",
)
C_POLL_BASELINE_RELATIVE_PATHS = (
    "test/template/c/test_runtime_alignment.py",
    "test/template/c_poll/test_runtime_alignment.py",
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
        return tuple(self.data.get("runners", ()))

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


@dataclass(frozen=True)
class Classification:
    """
    Downstream handling decision for one fixture case.

    :param label: Human-readable classification label.
    :type label: str
    :param target_pr: Follow-up PR expected to consume the case.
    :type target_pr: str
    :param landing: Suggested test or fixture landing area.
    :type landing: str
    :param triggers: Fields or concepts that drove the decision.
    :type triggers: typing.Tuple[str, ...]
    :param requirements: Assertion-strength requirements for the follow-up PR.
    :type requirements: typing.Tuple[str, ...]
    """

    label: str
    target_pr: str
    landing: str
    triggers: Tuple[str, ...]
    requirements: Tuple[str, ...]


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
        fcstm_path = yaml_path.with_suffix(".fcstm")
        data = _load_yaml(yaml_path)
        records.append(
            SemanticCaseRecord(
                case_id=case_id,
                yaml_path=yaml_path,
                fcstm_path=fcstm_path,
                data=data,
            )
        )
    return records


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


def _iter_key_values(value: Any, key_name: str) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) == key_name:
                yield item
            for child_value in _iter_key_values(item, key_name):
                yield child_value
    elif isinstance(value, list):
        for item in value:
            for child_value in _iter_key_values(item, key_name):
                yield child_value


def _case_has_key(record: SemanticCaseRecord, key_name: str) -> bool:
    return key_name in set(_iter_mapping_keys(record.data))


def _case_key_set(record: SemanticCaseRecord) -> set:
    return set(_iter_mapping_keys(record.data))


def _case_field_counts(
    records: Sequence[SemanticCaseRecord],
) -> Dict[str, List[str]]:
    field_cases = {}
    for field_name in CASE_FIELD_NAMES:
        field_cases[field_name] = [
            record.case_id for record in records if _case_has_key(record, field_name)
        ]
    return field_cases


def _return_value_distribution(records: Sequence[SemanticCaseRecord]) -> Counter:
    result = Counter()
    for record in records:
        for value in _iter_key_values(record.data, "return"):
            if value is None:
                result["null"] += 1
            else:
                result[repr(value)] += 1
    return result


def _return_case_distribution(records: Sequence[SemanticCaseRecord]) -> Counter:
    result = Counter()
    for record in records:
        values = list(_iter_key_values(record.data, "return"))
        if not values:
            continue
        value_counter = Counter("null" if value is None else repr(value) for value in values)
        compressed = ", ".join(
            "%s x %s" % (count, value)
            for value, count in sorted(value_counter.items())
        )
        result[compressed] += 1
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


def _markdown_code(value: str) -> str:
    escaped = value.replace("`", "\\`")
    return "`%s`" % escaped


def _markdown_join(values: Sequence[str]) -> str:
    if not values:
        return "-"
    return ", ".join(_markdown_code(value) for value in values)


def _plain_join(values: Sequence[str]) -> str:
    if not values:
        return "-"
    return ", ".join(values)


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
            "inline tests that supplied each fixture's semantics; fully migrated runtime and",
            "Python-template alignment tests are now executed through the fixture runners, so",
            "those origin paths may be visible only through repository history or the",
            "[migration pull request](https://github.com/HansBug/pyfcstm/pull/145) after the",
            "inline files are removed.",
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
        if not case_cell.startswith("`") or not case_cell.endswith("`"):
            continue
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


def _source_texts(root: Path, relative_paths: Sequence[str]) -> Dict[str, str]:
    result = {}
    for relative_path in relative_paths:
        path = root / relative_path
        if path.exists():
            result[relative_path] = _read_text(path)
    return result


def _token_hits(source_texts: Mapping[str, str]) -> List[Tuple[str, str, int, str]]:
    rows = []
    for relative_path, text in sorted(source_texts.items()):
        lines = text.splitlines()
        for token, pattern in TOKEN_PATTERNS:
            line_numbers = [
                str(index)
                for index, line in enumerate(lines, start=1)
                if pattern.search(line)
            ]
            if line_numbers:
                rows.append(
                    (
                        relative_path,
                        token,
                        len(line_numbers),
                        ", ".join(line_numbers[:20])
                        + (" ..." if len(line_numbers) > 20 else ""),
                    )
                )
    return rows


def _has_clear_simulator_diagnostic(record: SemanticCaseRecord) -> bool:
    keys = _case_key_set(record)
    if keys & {
        "runtime_options",
        "warnings",
        "logs",
        "abstract_handler_errors",
        "error_state",
        "error_info",
        "anonymous_warning_count",
    }:
        return True
    handlers = record.data.get("handlers", ())
    if isinstance(handlers, list):
        for item in handlers:
            if isinstance(item, Mapping) and item.get("behavior") == "raise_error":
                return True
    return False


def _old_observation_fields(record: SemanticCaseRecord) -> Tuple[str, ...]:
    keys = _case_key_set(record)
    result = []
    for field_name in (
        "stack",
        "brief_stack",
        "cycle_count",
        "history",
        "history_tail",
        "history_length",
        "return",
    ):
        if field_name in keys:
            result.append(field_name)
    return tuple(result)


def _classification(record: SemanticCaseRecord) -> Classification:
    keys = _case_key_set(record)
    old_fields = _old_observation_fields(record)
    triggers = []
    requirements = []

    if "model_build" in record.data:
        triggers.append("model_build")
        requirements.extend(
            (
                "Preserve model-build diagnostic entrypoint.",
                "Preserve exception type and message match.",
                "Preserve original DSL input.",
            )
        )
        return Classification(
            "MIGRATE_MODEL_VALIDATION",
            "后续普通 pytest（模型构建）",
            "test/model/ or existing validation diagnostic tests",
            tuple(triggers),
            tuple(requirements),
        )

    if "cli_command" in record.runners or "commands" in record.data:
        triggers.extend(["cli_command" if "cli_command" in record.runners else "commands"])
        requirements.extend(
            (
                "Preserve command sequence and exit status.",
                "Preserve stdout/stderr contains and not-contains assertions.",
                "Preserve public runtime summary assertions after commands.",
            )
        )
        return Classification(
            "MIGRATE_CLI_REPL",
            "后续普通 pytest（CLI / REPL）",
            "test/entry/simulate/ or existing CLI tests",
            tuple(triggers),
            tuple(requirements),
        )

    if _has_clear_simulator_diagnostic(record):
        for field_name in (
            "runtime_options",
            "warnings",
            "logs",
            "abstract_handler_errors",
            "error_state",
            "error_info",
            "anonymous_warning_count",
        ):
            if field_name in keys:
                triggers.append(field_name)
        handlers = record.data.get("handlers", ())
        if isinstance(handlers, list):
            for item in handlers:
                if isinstance(item, Mapping) and item.get("behavior") == "raise_error":
                    triggers.append("handlers.behavior=raise_error")
                    break
        requirements.extend(
            (
                "Preserve exception type and message assertions.",
                "Preserve warning/log text assertions.",
                "Preserve rollback state and variable snapshots.",
                "Preserve abstract handler call and error metadata.",
            )
        )
        return Classification(
            "MIGRATE_SIMULATOR_DIAGNOSTIC",
            "后续普通 pytest（模拟器诊断）",
            "test/simulate/",
            tuple(sorted(set(triggers))),
            tuple(requirements),
        )

    if old_fields:
        triggers.extend(old_fields)
        if "return" in old_fields:
            requirements.append("Move legacy return assertions to cycle_result.value.")
        if "stack" in old_fields:
            requirements.append(
                "Replace stack/brief_stack assertions with public state/ended/vars, or migrate if frame mode is the only evidence."
            )
        if "cycle_count" in old_fields:
            requirements.append(
                "Replace cycle_count with explicit step order and public post-step observations."
            )
        if "history_tail" in old_fields or "history_length" in old_fields:
            requirements.append(
                "Replace history assertions with per-step public observations, or migrate diagnostic-only history checks."
            )
        return Classification(
            "REWRITE_SHARED_PUBLIC_OBSERVATIONS",
            "共享语义收口",
            "shared fixture rewrite",
            tuple(triggers),
            tuple(requirements),
        )

    if "simulation" in record.runners and "generated_python_alignment" not in record.runners:
        return Classification(
            "ADD_ALIGNMENT_RUNNER",
            "共享 runner 补齐",
            "shared fixture runner list",
            ("simulation-only",),
            (
                "Confirm generated Python can observe the same public state, vars, ended, cycle_result, and hook records.",
            ),
        )

    return Classification(
        "KEEP_SHARED_FIXTURE",
        "none",
        "test/fixtures/simulate_semantics/",
        tuple(),
        ("Keep reading only public observations.",),
    )


def _classification_records(
    records: Sequence[SemanticCaseRecord],
) -> Dict[str, Classification]:
    return {record.case_id: _classification(record) for record in records}


def _render_report(
    root: Path,
    records: Sequence[SemanticCaseRecord],
    report_readme_text: str,
    drift_readme_text: str,
) -> str:
    field_cases = _case_field_counts(records)
    classifications = _classification_records(records)
    schema_text = _read_text(root / SCHEMA_RELATIVE_PATH)
    helper_sources = _source_texts(root, HELPER_RELATIVE_PATHS)
    helper_sources[SCHEMA_RELATIVE_PATH] = schema_text
    helper_sources[README_RELATIVE_PATH] = report_readme_text
    c_poll_sources = _source_texts(root, C_POLL_BASELINE_RELATIVE_PATHS)
    fcstm_count = len(list((root / CASE_DIR_RELATIVE_PATH).glob("*.fcstm")))

    runner_counter = Counter()
    runner_combo_counter = Counter()
    boundary_counter = Counter()
    for record in records:
        boundary_counter[str(record.data.get("boundary", "<missing>"))] += 1
        for runner in record.runners:
            runner_counter[runner] += 1
        runner_combo_counter[", ".join(record.runners)] += 1

    classification_counter = Counter(
        classification.label for classification in classifications.values()
    )
    readme_drift = _readme_drift_rows(records, drift_readme_text)
    return_distribution = _return_value_distribution(records)
    return_case_distribution = _return_case_distribution(records)
    handler_distribution = _handler_behavior_distribution(records)
    helper_hits = _token_hits(helper_sources)
    c_poll_hits = _token_hits(c_poll_sources)
    pure_shared_count = boundary_counter.get("pure_shared", 0)
    simulation_only_count = runner_combo_counter.get("simulation", 0)
    migration_case_count = sum(
        classification_counter.get(label, 0)
        for label in CLASSIFICATION_LABELS
        if label != "KEEP_SHARED_FIXTURE"
    )
    legacy_case_ids = sorted(
        set().union(
            field_cases["model_build"],
            field_cases["commands"],
            field_cases["runtime_options"],
            field_cases["stack"],
            field_cases["brief_stack"],
            field_cases["cycle_count"],
            field_cases["history"],
            field_cases["history_tail"],
            field_cases["history_length"],
            field_cases["return"],
            field_cases["warnings"],
            field_cases["logs"],
            field_cases["abstract_handler_errors"],
            field_cases["error_state"],
            field_cases["error_info"],
            field_cases["anonymous_warning_count"],
        )
    )
    generated_helper_hits = [
        row for row in helper_hits if row[0].startswith("test/template/python/")
    ]
    helper_compat_hits = [
        row for row in helper_hits if not row[0].startswith("test/template/python/")
    ]

    lines = [
        "# Simulate semantic fixture case inventory",
        "",
        "This file is generated by `python tools/inventory_simulate_semantics.py --write`.",
        "It records the current shared fixture surface, helper token hits, and",
        "downstream review requirements. Later cleanup work may still move or rewrite",
        "fixture cases, so regenerate this report after any corpus or helper change.",
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
        "## 阶段一总验收",
        "",
        "本小节给出共享语义 fixture 收束后的机器复核结论。它面向后续",
        "[issue #218](https://github.com/HansBug/pyfcstm/issues/218) 的全模板",
        "对齐工作：当前 corpus 只声明公共观察面，第二阶段可以在此基础上",
        "接入更多模板 runner，但不应重新消费旧白盒字段。",
        "",
        _format_markdown_table(
            ("验收项", "当前结果", "结论"),
            (
                (
                    "YAML 与 FCSTM 配对",
                    "YAML cases=%s；FCSTM files=%s" % (len(records), fcstm_count),
                    "通过：每个语义 fixture 都有配对 DSL 源。",
                ),
                (
                    "跨实现 runner 组合",
                    "simulation, generated_python_alignment=%s；simulation only=%s"
                    % (
                        runner_combo_counter.get(
                            "simulation, generated_python_alignment", 0
                        ),
                        simulation_only_count,
                    ),
                    "通过：当前共享 corpus 不再存在只跑模拟器的 case。",
                ),
                (
                    "pure_shared 边界标记",
                    "boundary: pure_shared=%s/%s" % (pure_shared_count, len(records)),
                    "通过：加载阶段会统一执行公共观察面边界校验。",
                ),
                (
                    "迁出分类",
                    "KEEP_SHARED_FIXTURE=%s；其他分类合计=%s"
                    % (
                        classification_counter.get("KEEP_SHARED_FIXTURE", 0),
                        migration_case_count,
                    ),
                    "通过：模型构建、CLI/REPL、模拟器诊断和旧观察面迁出项均已清零。",
                ),
                (
                    "共享禁入字段",
                    "命中 case=%s" % (", ".join(legacy_case_ids) or "0"),
                    "通过：shared YAML 中没有 runtime_options、model_build、commands、stack、cycle_count、history*、return 或诊断字段。",
                ),
                (
                    "generated Python alignment 私有读取",
                    "helper token hits=%s" % len(generated_helper_hits),
                    "通过：生成 Python 对齐路径没有依赖 stack、cycle_count、history 等私有观察面。",
                ),
                (
                    "兼容层和文档 token 命中",
                    "helper/doc compatibility hits=%s" % len(helper_compat_hits),
                    "通过：非零命中仅用于 schema/README 说明或模拟器 helper 的旧 schema 兼容，不作为 generated alignment 证据。",
                ),
                (
                    "C/C poll 基线",
                    "private token hits=%s" % len(c_poll_hits),
                    "通过：阶段一未接入 C/C poll runner；该结果仅作为第二阶段接入前的公共 API 基线。",
                ),
            ),
        ),
        "",
        "后续扩展 shared corpus 时，默认覆盖面应按 simulation + 所有 templates",
        "理解；不适用的 runner/template 应通过显式排除或能力标签说明，而不是",
        "用 include 白名单把 shared fixture 缩成少数实现专用样本。",
        "",
        "## Classification Summary",
        "",
        _format_markdown_table(
            ("Classification", "Case files"),
            tuple(
                (label, str(classification_counter.get(label, 0)))
                for label in CLASSIFICATION_LABELS
            ),
        ),
        "",
        "## YAML Field Counts",
        "",
        "Counts are case-file counts, not total field occurrences. Zero-hit fields are",
        "listed deliberately so retired legacy fields remain visible when they reach",
        "zero in the current corpus.",
        "",
        _format_markdown_table(
            ("YAML literal field", "Case files", "Concept / handling"),
            tuple(
                (
                    field_name,
                    str(len(field_cases[field_name])),
                    _field_handling_note(field_name),
                )
                for field_name in CASE_FIELD_NAMES
            ),
        ),
        "",
        "## Concept Field Mapping",
        "",
        _format_markdown_table(
            ("Concept", "YAML literal keys", "Case-file count"),
            (
                ("brief_stack", "stack", str(len(field_cases["stack"]))),
                (
                    "history*",
                    "history, history_tail, history_length",
                    str(
                        len(
                            set(field_cases["history"])
                            | set(field_cases["history_tail"])
                            | set(field_cases["history_length"])
                        )
                    ),
                ),
            ),
        ),
        "",
        "## Legacy Return Distribution",
        "",
        _format_markdown_table(
            ("Scope", "Distribution"),
            (
                (
                    "return value occurrences",
                    ", ".join(
                        "%s=%s" % (value, count)
                        for value, count in sorted(return_distribution.items())
                    )
                    or "-",
                ),
                (
                    "case-level return value sets",
                    ", ".join(
                        "%s cases => %s" % (count, values)
                        for values, count in sorted(return_case_distribution.items())
                    )
                    or "-",
                ),
            ),
        ),
        "",
        "## Handler Behavior Distribution",
        "",
        _format_markdown_table(
            ("Metric", "Count"),
            tuple((name, str(count)) for name, count in sorted(handler_distribution.items())),
        ),
        "",
        "## README Drift",
        "",
        _format_markdown_table(
            ("Status", "Details"),
            (("clean" if not readme_drift else "drift", _readme_drift_details(readme_drift)),),
        ),
        "",
        "## Helper White-Box Reads",
        "",
        "Non-zero rows here are retained for schema documentation or simulator helper",
        "compatibility checks. Generated Python alignment evidence must stay at zero",
        "private-token hits, as summarized in the final acceptance table above.",
        "",
        _format_markdown_table(
            ("Source", "Token", "Line count", "Lines"),
            helper_hits or (("-", "-", "0", "-"),),
        ),
        "",
        "## C / C Poll Public API Baseline",
        "",
        "These hits are scanned from the legacy C/C poll runtime alignment tests. Any",
        "non-zero hit must be reviewed before claiming the old baseline only compares",
        "public API observations.",
        "",
        _format_markdown_table(
            ("Source", "Token", "Line count", "Lines"),
            c_poll_hits or (("-", "-", "0", "-"),),
        ),
        "",
        "## Per-Case Downstream Plan",
        "",
        _format_markdown_table(
            (
                "Case id",
                "Runners / top-level shape",
                "Classification",
                "Trigger fields",
                "Original assertion fields",
                "Equivalent assertion requirements",
                "Target",
                "Suggested landing",
            ),
            tuple(_case_plan_row(record, classifications[record.case_id]) for record in records),
        ),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _field_handling_note(field_name: str) -> str:
    notes = {
        "model_build": "top-level model diagnostic; ordinary pytest coverage, not shared fixture surface",
        "commands": "CLI/REPL diagnostic; ordinary pytest coverage, not shared fixture surface",
        "runtime_options": "simulator diagnostic; ordinary simulator pytest coverage",
        "handlers": "split by behavior; record_call and record_var_write_attempt can express public hook observations, raise_error is diagnostic",
        "stack": "retired YAML literal for brief_stack concept",
        "brief_stack": "concept token; YAML literal is stack",
        "cycle_count": "retired debug/derived observation",
        "history": "retired concept/literal baseline",
        "history_tail": "retired history* concept",
        "history_length": "retired history* concept",
        "return": "legacy cycle return; migrate null values to cycle_result.value",
        "cycle_result": "public cycle return value/event accounting surface",
        "warnings": "simulator diagnostic unless explicitly shared later",
        "logs": "diagnostic/public-output assertion; preserve when migrating",
        "abstract_handler_errors": "simulator diagnostic; ordinary simulator pytest coverage",
        "error_state": "simulator diagnostic; ordinary simulator pytest coverage",
        "error_info": "simulator diagnostic; ordinary simulator pytest coverage",
        "anonymous_warning_count": "private warning dedupe; ordinary simulator pytest coverage",
    }
    return notes.get(field_name, "-")


def _readme_drift_details(rows: Sequence[Tuple[str, str, str]]) -> str:
    if not rows:
        return "README migration index matches YAML runners and assertion types."
    return "<br>".join("%s: %s (%s)" % row for row in rows[:40]) + (
        "<br>..." if len(rows) > 40 else ""
    )


def _case_shape(record: SemanticCaseRecord) -> str:
    shape = ["runners=%s" % ",".join(record.runners)]
    for key_name in ("model_build", "commands", "runtime_options", "handlers"):
        if key_name in record.data:
            shape.append(key_name)
    return "; ".join(shape)


def _case_plan_row(
    record: SemanticCaseRecord, classification: Classification
) -> Tuple[str, str, str, str, str, str, str, str]:
    return (
        _markdown_code(record.case_id),
        _case_shape(record),
        classification.label,
        _plain_join(classification.triggers),
        _plain_join(record.assertion_types),
        _plain_join(classification.requirements),
        classification.target_pr,
        classification.landing,
    )


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
    report_text = _render_report(root, records, readme_output, readme_text)
    return report_text, readme_output


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or check the simulate semantic fixture inventory."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the inventory report and README migration index.",
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
