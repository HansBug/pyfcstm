#!/usr/bin/env python3
"""Check diagnostics reference pages against the diagnostic code registry.

This maintenance command verifies the hand-authored diagnostics reference
metadata that lives under ``docs/source/reference/diagnostics_codes/``.  It is
intentionally outside the pytest unit-test suite because it checks documentation
inventory coverage rather than runtime behavior.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set

_REPO_ROOT = Path(__file__).resolve().parents[1]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pyfcstm.diagnostics.codes import CODE_REGISTRY, CodeFieldSpec, CodeSpec  # noqa: E402

_LANG_FILES = {
    "en": (
        _REPO_ROOT / "docs/source/reference/diagnostics_codes/index.rst",
        _REPO_ROOT / "docs/source/reference/diagnostics_codes/_code_catalog_en.rst.inc",
    ),
    "zh": (
        _REPO_ROOT / "docs/source/reference/diagnostics_codes/index_zh.rst",
        _REPO_ROOT / "docs/source/reference/diagnostics_codes/_code_catalog_zh.rst.inc",
    ),
}

_ALLOWED_EXAMPLE_KINDS = frozenset(
    (
        "repro_cli",
        "repro_api",
        "verify_opt_in",
        "boundary_only",
        "compatibility_only",
    )
)

_META_RE = re.compile(
    r"^\.\. diagnostics-meta (?P<code>\S+) severity=(?P<severity>\S+) "
    r"emit_tier=(?P<emit_tier>\S+) capability=(?P<capability>\S+) "
    r"span_object=(?P<span_object>\S+)$",
    re.MULTILINE,
)
_REF_RE = re.compile(
    r"^\.\. diagnostics-ref (?P<code>\S+) (?P<field>\S+) type=(?P<type>\S+) "
    r"required=(?P<required>true|false) enum=(?P<enum>\S+) "
    r"item_enum=(?P<item_enum>\S+) exact_values=(?P<exact_values>\S+)$",
    re.MULTILINE,
)
_EXAMPLE_RE = re.compile(
    r"^\.\. diagnostics-example (?P<code>\S+) (?P<index>[1-9][0-9]*) (?P<kind>\S+)$",
    re.MULTILINE,
)


def _format_optional_values(values: Optional[Sequence[str]]) -> str:
    """Return the marker representation for an optional string sequence.

    :param values: Optional ordered values from a registry field.
    :type values: Optional[Sequence[str]]
    :return: ``"-"`` when absent, otherwise values joined by ``"|"``.
    :rtype: str
    """
    if values is None:
        return "-"
    return "|".join(values)


def _span_object(spec: CodeSpec) -> str:
    """Return the marker representation for a code span object.

    :param spec: Diagnostic code specification.
    :type spec: pyfcstm.diagnostics.codes.CodeSpec
    :return: Span object name, or ``"none"`` when the registry omits one.
    :rtype: str
    """
    return spec.span_object or "none"


def _load_language_text(paths: Sequence[Path]) -> str:
    """Read and concatenate all source files for one documentation language.

    :param paths: Source files that together form the reference page.
    :type paths: Sequence[pathlib.Path]
    :return: Concatenated source text.
    :rtype: str
    """
    chunks: List[str] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(str(path))
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _collect_metadata(text: str) -> Dict[str, Mapping[str, str]]:
    """Collect diagnostic metadata markers from one language source.

    :param text: Concatenated reference source text.
    :type text: str
    :return: Mapping from code to parsed marker values.
    :rtype: Dict[str, Mapping[str, str]]
    """
    data: Dict[str, Mapping[str, str]] = {}
    for match in _META_RE.finditer(text):
        data[match.group("code")] = match.groupdict()
    return data


def _collect_refs(text: str) -> Dict[str, Dict[str, Mapping[str, str]]]:
    """Collect refs-schema markers from one language source.

    :param text: Concatenated reference source text.
    :type text: str
    :return: Mapping ``code -> field -> parsed marker``.
    :rtype: Dict[str, Dict[str, Mapping[str, str]]]
    """
    data: Dict[str, Dict[str, Mapping[str, str]]] = {}
    for match in _REF_RE.finditer(text):
        code = match.group("code")
        field = match.group("field")
        data.setdefault(code, {})[field] = match.groupdict()
    return data


def _collect_examples(text: str) -> Dict[str, List[Mapping[str, str]]]:
    """Collect example markers from one language source.

    :param text: Concatenated reference source text.
    :type text: str
    :return: Mapping from code to parsed example markers.
    :rtype: Dict[str, List[Mapping[str, str]]]
    """
    data: Dict[str, List[Mapping[str, str]]] = {}
    for match in _EXAMPLE_RE.finditer(text):
        code = match.group("code")
        data.setdefault(code, []).append(match.groupdict())
    return data


def _compare_code_sets(
    language: str,
    metadata: Mapping[str, Mapping[str, str]],
    problems: List[str],
) -> None:
    """Compare documented code markers with the registry key set.

    :param language: Language label for diagnostics.
    :type language: str
    :param metadata: Parsed metadata markers.
    :type metadata: Mapping[str, Mapping[str, str]]
    :param problems: Mutable list that receives problem strings.
    :type problems: List[str]
    :return: ``None``.
    :rtype: None
    """
    expected = set(CODE_REGISTRY)
    actual = set(metadata)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        problems.append("{lang}: missing code metadata markers: {codes}".format(
            lang=language,
            codes=", ".join(missing),
        ))
    if extra:
        problems.append("{lang}: unknown code metadata markers: {codes}".format(
            lang=language,
            codes=", ".join(extra),
        ))


def _check_metadata_fields(
    language: str,
    metadata: Mapping[str, Mapping[str, str]],
    problems: List[str],
) -> None:
    """Check marker metadata values against :data:`CODE_REGISTRY`.

    :param language: Language label for diagnostics.
    :type language: str
    :param metadata: Parsed metadata markers.
    :type metadata: Mapping[str, Mapping[str, str]]
    :param problems: Mutable list that receives problem strings.
    :type problems: List[str]
    :return: ``None``.
    :rtype: None
    """
    for code, spec in CODE_REGISTRY.items():
        actual = metadata.get(code)
        if actual is None:
            continue
        expected = {
            "severity": spec.severity,
            "emit_tier": spec.emit_tier,
            "capability": spec.capability,
            "span_object": _span_object(spec),
        }
        for key, expected_value in expected.items():
            if actual[key] != expected_value:
                problems.append(
                    "{lang}: {code} {key} marker is {actual!r}, expected {expected!r}".format(
                        lang=language,
                        code=code,
                        key=key,
                        actual=actual[key],
                        expected=expected_value,
                    )
                )


def _field_expected_values(field: CodeFieldSpec) -> Mapping[str, str]:
    """Return marker values expected for one refs-schema field.

    :param field: Registry field specification.
    :type field: pyfcstm.diagnostics.codes.CodeFieldSpec
    :return: Expected marker values.
    :rtype: Mapping[str, str]
    """
    return {
        "type": field.type,
        "required": "true" if field.required else "false",
        "enum": _format_optional_values(field.enum),
        "item_enum": _format_optional_values(field.item_enum),
        "exact_values": _format_optional_values(field.exact_values),
    }


def _check_refs(
    language: str,
    refs: Mapping[str, Mapping[str, Mapping[str, str]]],
    problems: List[str],
) -> None:
    """Check refs-schema markers against :data:`CODE_REGISTRY`.

    :param language: Language label for diagnostics.
    :type language: str
    :param refs: Parsed refs markers.
    :type refs: Mapping[str, Mapping[str, Mapping[str, str]]]
    :param problems: Mutable list that receives problem strings.
    :type problems: List[str]
    :return: ``None``.
    :rtype: None
    """
    for code, spec in CODE_REGISTRY.items():
        actual_fields = refs.get(code, {})
        expected_fields = set(spec.refs_schema)
        actual_names = set(actual_fields)
        missing = sorted(expected_fields - actual_names)
        extra = sorted(actual_names - expected_fields)
        if missing:
            problems.append("{lang}: {code} missing refs markers: {fields}".format(
                lang=language,
                code=code,
                fields=", ".join(missing),
            ))
        if extra:
            problems.append("{lang}: {code} has unknown refs markers: {fields}".format(
                lang=language,
                code=code,
                fields=", ".join(extra),
            ))
        for field_name, field in spec.refs_schema.items():
            actual = actual_fields.get(field_name)
            if actual is None:
                continue
            expected = _field_expected_values(field)
            for key, expected_value in expected.items():
                if actual[key] != expected_value:
                    problems.append(
                        "{lang}: {code}.{field} {key} marker is {actual!r}, expected {expected!r}".format(
                            lang=language,
                            code=code,
                            field=field_name,
                            key=key,
                            actual=actual[key],
                            expected=expected_value,
                        )
                    )


def _check_examples(
    language: str,
    examples: Mapping[str, Sequence[Mapping[str, str]]],
    problems: List[str],
) -> None:
    """Check example marker counts and kind labels.

    :param language: Language label for diagnostics.
    :type language: str
    :param examples: Parsed example markers.
    :type examples: Mapping[str, Sequence[Mapping[str, str]]]
    :param problems: Mutable list that receives problem strings.
    :type problems: List[str]
    :return: ``None``.
    :rtype: None
    """
    for code in CODE_REGISTRY:
        markers = list(examples.get(code, ()))
        if len(markers) < 3:
            problems.append("{lang}: {code} has {count} example markers, expected at least 3".format(
                lang=language,
                code=code,
                count=len(markers),
            ))
        seen_indices: Set[str] = set()
        for marker in markers:
            index = marker["index"]
            kind = marker["kind"]
            if index in seen_indices:
                problems.append("{lang}: {code} repeats example marker index {index}".format(
                    lang=language,
                    code=code,
                    index=index,
                ))
            seen_indices.add(index)
            if kind not in _ALLOWED_EXAMPLE_KINDS:
                problems.append("{lang}: {code} has unsupported example kind {kind!r}".format(
                    lang=language,
                    code=code,
                    kind=kind,
                ))


def _check_language(language: str, paths: Sequence[Path]) -> List[str]:
    """Run all reference checks for one language.

    :param language: Language label.
    :type language: str
    :param paths: Reference source files for the language.
    :type paths: Sequence[pathlib.Path]
    :return: List of problems found.
    :rtype: List[str]
    """
    problems: List[str] = []
    text = _load_language_text(paths)
    metadata = _collect_metadata(text)
    refs = _collect_refs(text)
    examples = _collect_examples(text)
    _compare_code_sets(language, metadata, problems)
    _check_metadata_fields(language, metadata, problems)
    _check_refs(language, refs, problems)
    _check_examples(language, examples, problems)
    return problems


def run_check() -> int:
    """Run diagnostics reference documentation checks.

    :return: Process-style status code, ``0`` on success.
    :rtype: int
    """
    problems: List[str] = []
    for language, paths in _LANG_FILES.items():
        problems.extend(_check_language(language, paths))
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print(
        "diagnostics reference docs cover {count} codes in {langs}".format(
            count=len(CODE_REGISTRY),
            langs=", ".join(sorted(_LANG_FILES)),
        )
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse command-line arguments and run the check.

    :param argv: Optional argument list. ``None`` reads :data:`sys.argv`.
    :type argv: Optional[Sequence[str]]
    :return: Process-style status code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the check. Present for consistency with other tools.",
    )
    parser.parse_args(argv)
    return run_check()


if __name__ == "__main__":
    raise SystemExit(main())
