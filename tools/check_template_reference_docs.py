#!/usr/bin/env python3
"""Check template reference documentation markers against repository facts.

The checker is intentionally tools-only. It reads repository documentation and
source-template metadata, then verifies that English and Chinese reference pages
carry the synchronization markers required by the documentation-authoring
contract.

Markers prove that the reference pages carry the required synchronized facts.
They do not replace human review of the surrounding prose depth or examples.

Example::

    $ python tools/check_template_reference_docs.py --check
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import (
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from pyfcstm.render.expr import _KNOWN_STYLES, _STYLE_ALIASES
from pyfcstm.render.render import _CONFIG_ALLOWED_TOP_LEVEL_KEYS
from pyfcstm.render.statement import _KNOWN_STMT_STYLES, _STMT_STYLE_ALIASES

ROOT = Path(__file__).resolve().parents[1]
BUILTIN_REFERENCE_DOCS = (
    ROOT / "docs/source/reference/builtin_templates/index.rst",
    ROOT / "docs/source/reference/builtin_templates/index_zh.rst",
)
CONFIG_REFERENCE_DOCS = (
    ROOT / "docs/source/reference/template_config/index.rst",
    ROOT / "docs/source/reference/template_config/index_zh.rst",
)

TEMPLATE_CONTRACT_FIELDS = {
    "generated_files",
    "entry_point",
    "event_model",
    "extension_point",
    "lifecycle",
    "target_boundary",
    "evidence_boundary",
    "generated_readme",
    "experimental_status",
}

TEMPLATE_PROFILE_EXPECTATIONS = {
    "python": {
        "event_input": "cycle_events",
        "wrapper": "false",
        "core": "python",
        "native_evidence": "false",
        "semantic_alignment": "true",
        "formatter": "ruff",
        "poll": "false",
    },
    "c": {
        "event_input": "explicit_event_ids",
        "wrapper": "false",
        "core": "c99",
        "native_evidence": "true",
        "semantic_alignment": "true",
        "formatter": "clang-format",
        "poll": "false",
    },
    "c_poll": {
        "event_input": "event_checks",
        "wrapper": "false",
        "core": "c99",
        "native_evidence": "true",
        "semantic_alignment": "true",
        "formatter": "clang-format",
        "poll": "true",
    },
    "cpp": {
        "event_input": "explicit_event_ids",
        "wrapper": "true",
        "core": "c99",
        "native_evidence": "true",
        "semantic_alignment": "true",
        "formatter": "clang-format",
        "poll": "false",
    },
    "cpp_poll": {
        "event_input": "event_checks",
        "wrapper": "true",
        "core": "c_poll",
        "native_evidence": "true",
        "semantic_alignment": "true",
        "formatter": "clang-format",
        "poll": "true",
    },
}

VALIDATION_MARKERS = {
    "yaml-parse-error",
    "empty-file",
    "root-not-mapping",
    "unknown-top-level-key",
    "expr-styles-not-mapping",
    "stmt-styles-not-mapping",
    "globals-not-mapping",
    "filters-not-mapping",
    "tests-not-mapping",
    "expr-style-not-mapping",
    "expr-style-missing-base-lang",
    "stmt-style-not-mapping",
    "stmt-style-missing-base-lang",
    "ignores-not-list",
    "ignores-item-not-string",
    "object-template-missing-template",
    "object-import-missing-from",
    "object-value-missing-value",
    "object-import-target-failure",
}

STMT_FIELDS = {
    "base_lang",
    "expr_lang",
    "expr_templates",
    "state_var_target",
    "temp_var_target",
    "assign",
    "declare_temp",
    "temp_type_aliases",
    "temp_type_fallback",
    "if",
    "elif",
    "else",
    "block_end",
    "pass",
}

HELPER_MARKERS = {
    "INIT_STATE",
    "EXIT_STATE",
    "expr_render",
    "stmt_render",
    "stmts_render",
    "_stmt_default_state_vars",
    "_stmt_default_var_types",
    "operation_stmt_render",
    "operation_stmts_render",
    "normalize",
    "to_identifier",
    "indent",
    "builtins",
    "environment-variables",
    "render_c_action_body",
    "render_c_condition_body",
    "render_c_reset_vars_body",
    "to_c_identifier",
    "to_c_path_identifier",
    "to_c_public_identifier",
    "to_c_public_macro_identifier",
    "is_c_public_identifier_reserved",
}

OBJECT_FORMS = {
    "template-with-params",
    "template-without-params",
    "import",
    "value",
    "unknown-type",
    "no-type",
    "non-dict",
}

FILE_MAPPING_MARKERS = {
    "j2-render",
    "static-copy",
    "config-samefile-skip",
    "git-ignore-input-only",
    "ignores-gitwildmatch",
    "nested-output-dirs",
    "utf8-lf-render",
    "static-copy-bytes",
    "clear-symlink-unlink",
    "clear-file-remove",
    "clear-directory-rmtree",
    "clear-other-warning",
}


class CheckFailure(Exception):
    """Raised when documentation marker checks find one or more failures."""


def _load_json(path: Path) -> MutableMapping[str, object]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise CheckFailure("JSON file %s must contain an object." % path)
    return data


def _load_template_index() -> List[Dict[str, object]]:
    index = _load_json(ROOT / "pyfcstm/template/index.json")
    templates = index.get("templates")
    if not isinstance(templates, list):
        raise CheckFailure("pyfcstm/template/index.json must contain a templates list.")
    result = []
    for item in templates:
        if not isinstance(item, dict):
            raise CheckFailure("Every template index entry must be an object.")
        result.append(dict(item))
    return result


def _template_source_metadata(name: str) -> Dict[str, object]:
    metadata = _load_json(ROOT / "templates" / name / "template.json")
    return dict(metadata)


def _expected_template_metadata() -> List[Dict[str, str]]:
    expected = []
    for index_item in _load_template_index():
        name = str(index_item["name"])
        source_item = _template_source_metadata(name)
        for field in ("name", "title", "description", "language", "experimental"):
            if source_item.get(field) != index_item.get(field):
                raise CheckFailure(
                    "Template metadata mismatch for %s field %s: index=%r source=%r."
                    % (name, field, index_item.get(field), source_item.get(field))
                )
        expected.append(
            {
                "name": name,
                "title": str(index_item["title"]),
                "language": str(index_item["language"]),
                "archive": str(index_item["archive"]),
                "root_dir": str(index_item["root_dir"]),
                "experimental": str(index_item["experimental"]).lower(),
                "description": str(index_item["description"]),
            }
        )
    return expected


def _parse_marker_payload(payload: str) -> Tuple[Dict[str, str], Set[str]]:
    mapping = {}
    words = set()
    for token in shlex.split(payload):
        if "=" in token:
            key, value = token.split("=", 1)
            mapping[key] = value
        else:
            words.add(token)
    return mapping, words


def _collect_markers(path: Path, prefix: str) -> List[Tuple[Dict[str, str], Set[str]]]:
    markers = []
    marker_prefix = ".. %s:" % prefix
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(marker_prefix):
            payload = stripped[len(marker_prefix) :].strip()
            markers.append(_parse_marker_payload(payload))
    return markers


def _find_marker(
    markers: Sequence[Tuple[Mapping[str, str], Set[str]]],
    name: str,
) -> Tuple[Mapping[str, str], Set[str]]:
    for mapping, words in markers:
        if mapping.get("name") == name:
            return mapping, words
    return {}, set()


def _add_missing(missing: List[str], path: Path, group: str, detail: str) -> None:
    missing.append("%s: missing %s %s" % (path.relative_to(ROOT), group, detail))


def _check_builtin_reference_page(
    path: Path, expected: Sequence[Mapping[str, str]]
) -> List[str]:
    missing = []
    meta_markers = _collect_markers(path, "template-ref-meta")
    contract_markers = _collect_markers(path, "template-ref-contract")
    profile_markers = _collect_markers(path, "template-ref-profile")

    for item in expected:
        name = item["name"]
        meta, _ = _find_marker(meta_markers, name)
        if not meta:
            _add_missing(missing, path, "template-ref-meta", name)
        else:
            for key, value in item.items():
                if meta.get(key) != value:
                    missing.append(
                        "%s: template-ref-meta %s has %s=%r, expected %r"
                        % (path.relative_to(ROOT), name, key, meta.get(key), value)
                    )

        contract, words = _find_marker(contract_markers, name)
        if not contract:
            _add_missing(missing, path, "template-ref-contract", name)
        else:
            for field in sorted(TEMPLATE_CONTRACT_FIELDS - words):
                _add_missing(
                    missing,
                    path,
                    "template-ref-contract field",
                    "%s %s" % (name, field),
                )

        profile, _ = _find_marker(profile_markers, name)
        expected_profile = TEMPLATE_PROFILE_EXPECTATIONS.get(name)
        if expected_profile is None:
            _add_missing(missing, path, "template-ref-profile expectation", name)
        if not profile:
            _add_missing(missing, path, "template-ref-profile", name)
        elif expected_profile is not None:
            for key, value in expected_profile.items():
                if profile.get(key) != value:
                    missing.append(
                        "%s: template-ref-profile %s has %s=%r, expected %r"
                        % (path.relative_to(ROOT), name, key, profile.get(key), value)
                    )
    return missing


def _markers_by_category(
    path: Path,
) -> Dict[str, List[Tuple[Mapping[str, str], Set[str]]]]:
    result = {}
    marker_prefix = ".. template-config-marker:"
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith(marker_prefix):
            continue
        payload = stripped[len(marker_prefix) :].strip()
        tokens = shlex.split(payload)
        if not tokens:
            result.setdefault("", []).append(({}, set()))
            continue
        category = tokens[0]
        mapping = {}
        words = set()
        for token in tokens[1:]:
            if "=" in token:
                key, value = token.split("=", 1)
                mapping[key] = value
            else:
                words.add(token)
        result.setdefault(category, []).append((mapping, words))
    return result


def _category_items(
    categories: Mapping[str, Sequence[Tuple[Mapping[str, str], Set[str]]]],
    category: str,
) -> Set[str]:
    items = set()
    for _, words in categories.get(category, []):
        items.update(words)
    return items


def _category_mappings(
    categories: Mapping[str, Sequence[Tuple[Mapping[str, str], Set[str]]]],
    category: str,
) -> Dict[str, str]:
    result = {}
    for mapping, _ in categories.get(category, []):
        result.update(mapping)
    return result


def _check_set(
    missing: List[str],
    path: Path,
    category: str,
    expected: Iterable[str],
    actual: Set[str],
) -> None:
    for item in sorted(set(expected) - actual):
        _add_missing(missing, path, category, item)


def _check_config_reference_page(path: Path) -> List[str]:
    missing = []
    categories = _markers_by_category(path)

    _check_set(
        missing,
        path,
        "top-level-key",
        _CONFIG_ALLOWED_TOP_LEVEL_KEYS,
        _category_items(categories, "top-level-key"),
    )
    _check_set(
        missing,
        path,
        "validation",
        VALIDATION_MARKERS,
        _category_items(categories, "validation"),
    )

    expr_styles = set(_KNOWN_STYLES.keys())
    stmt_styles = set(_KNOWN_STMT_STYLES.keys())
    if expr_styles != stmt_styles:
        missing.append(
            "implementation style drift: expression styles %r differ from statement styles %r"
            % (sorted(expr_styles), sorted(stmt_styles))
        )
    _check_set(
        missing,
        path,
        "style-name",
        expr_styles,
        _category_items(categories, "style-name"),
    )

    if dict(_STYLE_ALIASES) != dict(_STMT_STYLE_ALIASES):
        missing.append(
            "implementation alias drift: expression aliases %r differ from statement aliases %r"
            % (dict(_STYLE_ALIASES), dict(_STMT_STYLE_ALIASES))
        )
    actual_aliases = _category_mappings(categories, "style-alias")
    for alias, canonical in sorted(_STYLE_ALIASES.items()):
        if actual_aliases.get(alias) != canonical:
            missing.append(
                "%s: style-alias %s has %r, expected %r"
                % (path.relative_to(ROOT), alias, actual_aliases.get(alias), canonical)
            )

    _check_set(
        missing,
        path,
        "stmt-field",
        STMT_FIELDS,
        _category_items(categories, "stmt-field"),
    )
    _check_set(
        missing,
        path,
        "helper",
        HELPER_MARKERS,
        _category_items(categories, "helper"),
    )
    _check_set(
        missing,
        path,
        "object-form",
        OBJECT_FORMS,
        _category_items(categories, "object-form"),
    )
    _check_set(
        missing,
        path,
        "file-mapping",
        FILE_MAPPING_MARKERS,
        _category_items(categories, "file-mapping"),
    )
    return missing


def run_checks() -> None:
    missing = []
    expected_templates = _expected_template_metadata()
    for path in BUILTIN_REFERENCE_DOCS:
        missing.extend(_check_builtin_reference_page(path, expected_templates))
    for path in CONFIG_REFERENCE_DOCS:
        missing.extend(_check_config_reference_page(path))

    if missing:
        raise CheckFailure(
            "Template reference documentation drift check failed.\n"
            + "\n".join(missing)
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run checks and exit nonzero when documentation markers drift.",
    )
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 0
    try:
        run_checks()
    except CheckFailure as err:
        # CheckFailure: malformed metadata or synchronized reference markers
        # drifted from repository facts.
        print(str(err), file=sys.stderr)
        return 1
    print("Template reference documentation markers are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
