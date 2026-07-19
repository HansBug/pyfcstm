#!/usr/bin/env python3
"""Validate BMC documentation structure, equations, and landing surfaces."""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[1]

_EQUATION_LABELS = (
    "bmc-trace-frame-domain",
    "bmc-trace-event-domain",
    "bmc-trace-variable-domain",
    "bmc-trace-selector-domain",
    "bmc-domain-formula",
    "bmc-initial-control",
    "bmc-initial-retained",
    "bmc-initial-havoc",
    "bmc-initial-where",
    "bmc-case-antecedent",
    "bmc-case-selector",
    "bmc-case-relation",
    "bmc-case-post-control",
    "bmc-case-variable-write",
    "bmc-case-variable-carry",
    "bmc-step-fallback",
    "bmc-step-terminated-absorb",
    "bmc-step-delta-gamma",
    "bmc-transition-formula",
    "bmc-environment-formula",
    "bmc-core-formula",
    "bmc-predicate-defined",
    "bmc-predicate-good",
    "bmc-predicate-bad-true",
    "bmc-predicate-bad-false",
    "bmc-objective-reach",
    "bmc-objective-forbid",
    "bmc-objective-invariant",
    "bmc-objective-must-reach",
    "bmc-objective-exists-always",
    "bmc-call-count",
    "bmc-objective-cover",
    "bmc-response-violation",
    "bmc-response-trigger-undefined",
    "bmc-response-incomplete",
    "bmc-solve-formulas",
    "bmc-verdict-map",
    "bmc-witness-projection",
    "bmc-replay-agreement",
    "bmc-symbol-growth",
)

_PAGE_PAIRS = (
    "tutorials/bmc/index",
    "how_to/bmc/index",
    "explanations/bmc_semantics/index",
    "explanations/bmc_properties/index",
    "explanations/bmc_solving/index",
    "reference/bmc_query/index",
    "reference/bmc_results/index",
)

_EQUATION_PAIRS = (
    "explanations/bmc_semantics/index",
    "explanations/bmc_properties/index",
    "explanations/bmc_solving/index",
)

_SCHEMA_RELATIVE_PATH = Path("reference/bmc_results/bmc_cli.schema.json")
_SCHEMA_ID = (
    "https://github.com/HansBug/pyfcstm/blob/main/"
    "docs/source/reference/bmc_results/bmc_cli.schema.json"
)

_TUTORIAL_DIAGRAMS = (
    ("bmc_pipeline.puml", "bmc_pipeline_zh.puml"),
    ("first_check_en.puml", "first_check_zh.puml"),
)


class CheckFailure(Exception):
    """Raised when one or more BMC documentation contracts fail."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        # OSError: the required source is missing/unreadable;
        # UnicodeDecodeError: documentation sources must be UTF-8.
        raise CheckFailure("%s cannot be read as UTF-8: %s" % (path, err))


def _extract_equations(path: Path) -> List[Tuple[str, str]]:
    lines = _read(path).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    equations: List[Tuple[str, str]] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != ".. math::":
            index += 1
            continue
        index += 1
        label = None
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith(":"):
                if stripped.startswith(":label:"):
                    label = stripped.partition(":label:")[2].strip()
                index += 1
                continue
            break
        body: List[str] = []
        while index < len(lines) and (
            not lines[index] or lines[index].startswith("   ")
        ):
            body.append(lines[index])
            index += 1
        if label is None:
            raise CheckFailure("%s has an unlabeled math block." % path)
        latex = textwrap.dedent("\n".join(body)).strip("\n")
        latex = "\n".join(line.rstrip() for line in latex.split("\n"))
        if not latex.strip():
            raise CheckFailure("%s equation %s is empty." % (path, label))
        equations.append((label, latex))
    return equations


def _check_equations(errors: List[str]) -> None:
    english: List[Tuple[str, str]] = []
    chinese: List[Tuple[str, str]] = []
    source = _REPO_ROOT / "docs/source"
    for relative in _EQUATION_PAIRS:
        english.extend(_extract_equations(source / (relative + ".rst")))
        chinese.extend(_extract_equations(source / (relative + "_zh.rst")))
    english_labels = tuple(label for label, _latex in english)
    chinese_labels = tuple(label for label, _latex in chinese)
    if english_labels != _EQUATION_LABELS:
        errors.append(
            "English BMC equation ledger does not match the frozen 40 labels."
        )
    if chinese_labels != _EQUATION_LABELS:
        errors.append(
            "Chinese BMC equation ledger does not match the frozen 40 labels."
        )
    if english != chinese:
        errors.append("English and Chinese BMC equation labels/LaTeX differ.")


def _check_pages(errors: List[str]) -> None:
    source = _REPO_ROOT / "docs/source"
    root_en = _read(source / "index_en.rst")
    root_zh = _read(source / "index_zh.rst")
    for relative in _PAGE_PAIRS:
        english = source / (relative + ".rst")
        chinese = source / (relative + "_zh.rst")
        for path in (english, chinese):
            text = _read(path)
            if ".. toctree::" in text:
                errors.append("%s must not own sibling pages through a toctree." % path)
        if relative not in root_en:
            errors.append("English root index does not directly list %s." % relative)
        if relative + "_zh" not in root_zh:
            errors.append("Chinese root index does not directly list %s_zh." % relative)

    roadmap_requirements: Dict[str, Tuple[str, ...]] = {
        "tutorials/index.rst": ("bmc/index",),
        "tutorials/index_zh.rst": ("bmc/index_zh",),
        "how_to/index.rst": ("bmc/index",),
        "how_to/index_zh.rst": ("bmc/index_zh",),
        "explanations/index.rst": (
            "bmc_semantics/index",
            "bmc_properties/index",
            "bmc_solving/index",
        ),
        "explanations/index_zh.rst": (
            "bmc_semantics/index_zh",
            "bmc_properties/index_zh",
            "bmc_solving/index_zh",
        ),
        "reference/index.rst": ("bmc_query/index", "bmc_results/index"),
        "reference/index_zh.rst": (
            "bmc_query/index_zh",
            "bmc_results/index_zh",
        ),
    }
    for relative, required in roadmap_requirements.items():
        text = _read(source / relative)
        for target in required:
            if target not in text:
                errors.append("%s does not link to %s." % (relative, target))


def _check_readme(errors: List[str]) -> None:
    text = _read(_REPO_ROOT / "README.md")
    requirements = (
        "def int latch_engaged = 1;",
        "Locked -> Unlocked : Unlock effect {",
        "latch_engaged = 0;",
        "Unlocked -> Open : OpenDoor;",
        "Locked -> Open : ServiceOverride;",
        'active("Door.Open") && latch_engaged == 1;',
        "pyfcstm bmc -i door.fcstm -q door_latch_safety.fbmcq",
        "BMC forbid <= 2: PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND",
        "Door.Locked -> Door.Open",
        "events=Door.ServiceOverride",
        "Running the same query now reports `PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE`",
        "--json -o bmc-result.json",
        "--color auto|always|never",
        "Every result is bounded",
        "replayed through the runtime",
    )
    for requirement in requirements:
        if requirement not in text:
            errors.append("README.md is missing BMC landing fact: %s" % requirement)
    for relative in _PAGE_PAIRS:
        url_path = relative.replace("/index", "/index.html")
        if url_path not in text:
            errors.append("README.md is missing BMC documentation link: %s" % url_path)


def _check_localized_diagrams(errors: List[str]) -> None:
    source = _REPO_ROOT / "docs/source/tutorials/bmc"
    english = _read(source / "index.rst")
    chinese = _read(source / "index_zh.rst")
    for english_name, chinese_name in _TUTORIAL_DIAGRAMS:
        if english_name + ".svg" not in english:
            errors.append("English BMC tutorial does not use %s.svg." % english_name)
        if chinese_name + ".svg" not in chinese:
            errors.append("Chinese BMC tutorial does not use %s.svg." % chinese_name)
        if chinese_name + ".svg" in english:
            errors.append(
                "English BMC tutorial uses Chinese diagram %s." % chinese_name
            )
        if english_name + ".svg" in chinese:
            errors.append(
                "Chinese BMC tutorial uses English diagram %s." % english_name
            )
        for name in (english_name, chinese_name):
            for suffix in ("", ".png", ".svg"):
                path = source / (name + suffix)
                if not path.is_file():
                    errors.append("BMC tutorial diagram asset is missing: %s" % path)


def _check_schema(errors: List[str]) -> None:
    docs_schema = _REPO_ROOT / "docs/source" / _SCHEMA_RELATIVE_PATH
    legacy_schemas = sorted(
        path
        for path in docs_schema.parent.glob("bmc_cli_*.schema.json")
        if path != docs_schema
    )
    for legacy_schema in legacy_schemas:
        errors.append("Legacy BMC JSON schema path still exists: %s" % legacy_schema)
    package_schemas = sorted((_REPO_ROOT / "pyfcstm").rglob("bmc_cli.schema.json"))
    for package_schema in package_schemas:
        errors.append(
            "BMC JSON schema must not be shipped inside pyfcstm: %s"
            % package_schema.relative_to(_REPO_ROOT)
        )
    docs_text = _read(docs_schema)
    try:
        schema = json.loads(docs_text)
    except json.JSONDecodeError as err:
        errors.append("BMC documentation schema is invalid JSON: %s" % err)
    else:
        if schema.get("$id") != _SCHEMA_ID:
            errors.append("BMC documentation schema has an unexpected $id.")
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(
                "BMC documentation schema must retain the standard dialect URI."
            )
        properties = schema.get("properties", {})
        if any("version" in str(name).casefold() for name in properties):
            errors.append(
                "BMC documentation schema must not expose version properties."
            )
        runtime_step = schema.get("$defs", {}).get("runtimeStep", {})
        if "delta" not in runtime_step.get("required", []):
            errors.append("BMC runtime-step schema must require delta.")
    for relative in (
        "reference/bmc_results/index.rst",
        "reference/bmc_results/index_zh.rst",
    ):
        text = _read(_REPO_ROOT / "docs/source" / relative)
        if "<bmc_cli.schema.json>" not in text:
            errors.append("%s does not expose the schema download." % relative)
        schema_references = set(
            re.findall(r"bmc_cli_[A-Za-z0-9_.-]+\.schema\.json", text)
        )
        if (
            any(reference != docs_schema.name for reference in schema_references)
            or "pyfcstm/entry/bmc_cli.schema.json" in text
            or "pkgutil.get_data" in text
        ):
            errors.append("%s still describes the removed package resource." % relative)


def check() -> None:
    """Run every deterministic BMC documentation contract check."""
    errors: List[str] = []
    _check_equations(errors)
    _check_pages(errors)
    _check_readme(errors)
    _check_localized_diagrams(errors)
    _check_schema(errors)
    if errors:
        raise CheckFailure("BMC documentation check failed:\n" + "\n".join(errors))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the tools-only command-line checker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("Only --check mode is supported.")
    try:
        check()
    except CheckFailure as err:
        # CheckFailure: one or more deterministic documentation contracts failed.
        print(str(err))
        return 1
    print("BMC documentation structure, diagrams, and equation ledger are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
