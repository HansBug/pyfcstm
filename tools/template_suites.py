"""
Detect built-in template test suites affected by repository changes.

This repo-local tools module decides which built-in template full test
suites should be requested by maintainer commands or later CI workflow
steps. It combines three sources of information:

* changed repository paths, which produce protected suites that ordinary skip
  requests cannot remove;
* explicit include tokens such as ``[tpl:c]`` or command-line suite values;
* explicit skip tokens such as ``[skip-tpl:c]`` that only remove manually
  selected dynamic suites.

The detector deliberately returns JSON-compatible dictionaries instead of
GitHub Actions expressions. Keeping the implementation under ``tools`` avoids
exposing CI routing policy as part of the public :mod:`pyfcstm` runtime API
while later workflow changes can consume the stable output schema.

The module contains:

* :class:`TemplateSuiteDetectionError` - Invalid detector input.
* :func:`detect_template_suites` - Build a JSON-compatible selection result.
* :func:`main` - CLI entry point for ``tools/detect_template_suites.py``.

Example::

    >>> result = detect_template_suites(["templates/c/machine.c.j2"], "", "local")
    >>> result["matrix"]["include"]
    [{'suite': 'c', 'reason': 'path:templates/c/machine.c.j2'}, {'suite': 'cpp', 'reason': 'path:templates/c/machine.c.j2'}]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

SCHEMA_VERSION = "template-suite-detector/v1"
FIXED_SUITES = ("default", "template_core", "template_representative")
DYNAMIC_SUITES = ("python", "c", "c_poll", "cpp", "cpp_poll")
SUITE_ORDER = FIXED_SUITES + DYNAMIC_SUITES
LEGAL_INPUT_SUITES = SUITE_ORDER + ("all",)
_DYNAMIC_SUITE_SET = set(DYNAMIC_SUITES)
_FIXED_SUITE_SET = set(FIXED_SUITES)
_LEGAL_INPUT_SUITE_SET = set(LEGAL_INPUT_SUITES)
_EVENT_NAMES = ("push", "pull_request", "workflow_dispatch", "local")
_EVENT_NAME_SET = set(_EVENT_NAMES)
_LABEL_RE = re.compile(r"\[(tpl|skip-tpl):([^\]]*)\]")
_BRACKET_RE = re.compile(r"\[([^\]]*)\]")
_LABEL_LIKE_RE = re.compile(r"^\s*(tpl|skip-tpl)(?:\s*:|\s+\S|$)")

PathRule = Tuple[Tuple[str, ...], Tuple[str, ...], str]

_PATH_RULES = (  # type: Tuple[PathRule, ...]
    (("templates/python/**",), ("python",), "path:{path}"),
    (("templates/c/**",), ("c", "cpp"), "path:{path}"),
    (("templates/c_poll/**",), ("c_poll", "cpp_poll"), "path:{path}"),
    (("templates/cpp/**",), ("cpp",), "path:{path}"),
    (("templates/cpp_poll/**",), ("cpp_poll",), "path:{path}"),
    (
        (
            "pyfcstm/render/render.py",
            "pyfcstm/render/env.py",
            "pyfcstm/render/expr.py",
            "pyfcstm/render/statement.py",
            "pyfcstm/render/func.py",
        ),
        DYNAMIC_SUITES,
        "path:{path}",
    ),
    (
        ("pyfcstm/render/c_runtime.py",),
        ("c", "c_poll", "cpp", "cpp_poll"),
        "path:{path}",
    ),
    (
        (
            "pyfcstm/utils/text.py",
            "pyfcstm/utils/jinja2.py",
            "pyfcstm/utils/safe.py",
        ),
        ("c", "c_poll", "cpp", "cpp_poll"),
        "path:{path}",
    ),
    (
        ("pyfcstm/dsl/**", "pyfcstm/model/**", "test/fixtures/simulate_semantics/**"),
        DYNAMIC_SUITES,
        "path:{path}",
    ),
    (
        ("pyfcstm/simulate/**", "test/testings/simulate_semantics.py"),
        DYNAMIC_SUITES,
        "path:{path}",
    ),
    (
        ("test/testings/native_semantic_alignment.py",),
        ("c", "c_poll", "cpp", "cpp_poll"),
        "path:{path}",
    ),
    (
        (
            "test/template/test_template.py",
            "test/template/test_template_structure.py",
            "test/template/test_c_family_helper_scope.py",
            "test/template/test_cpp_wrapper_harness_guard.py",
            "test/template/test_native_semantic_alignment_framework.py",
        ),
        ("template_core",),
        "path:{path}",
    ),
    (("test/template/python/**",), ("python",), "path:{path}"),
    (("test/template/c/**",), ("c", "cpp"), "path:{path}"),
    (("test/template/c_poll/**",), ("c_poll", "cpp_poll"), "path:{path}"),
    (("test/template/cpp/**",), ("cpp",), "path:{path}"),
    (("test/template/cpp_poll/**",), ("cpp_poll",), "path:{path}"),
    (
        ("test/template/cpp_shared.py", "test/template/cpp_readme_utils.py"),
        ("cpp", "cpp_poll"),
        "path:{path}",
    ),
    (
        (
            "test/conftest.py",
            "pytest.ini",
            "Makefile",
            "requirements*.txt",
            ".github/workflows/test.yml",
        ),
        DYNAMIC_SUITES,
        "path:{path}",
    ),
    (
        ("test/testings/native_toolchain_alignment/**",),
        ("c", "c_poll", "cpp", "cpp_poll"),
        "path:{path}",
    ),
    (
        ("tools/package_templates.py", "pyfcstm/template/**"),
        DYNAMIC_SUITES,
        "path:{path}",
    ),
)
_TEMPLATE_METADATA_PATTERNS = (
    "templates/{suite}/README.md",
    "templates/{suite}/README_zh.md",
    "templates/{suite}/template.json",
)
_TEMPLATE_METADATA_SUITES = {
    "python": ("template_core", "python"),
    "c": ("template_core", "c"),
    "c_poll": ("template_core", "c_poll"),
    "cpp": ("template_core", "cpp"),
    "cpp_poll": ("template_core", "cpp_poll"),
}
_UNSCOPED_TEMPLATE_METADATA_PATHS = ("templates/README.md", "templates/README_zh.md")


class TemplateSuiteDetectionError(ValueError):
    """
    Report invalid input for template suite detection.

    :param message: Human-readable validation failure.
    :type message: str

    Example::

        >>> TemplateSuiteDetectionError("unknown suite: java").args[0]
        'unknown suite: java'
    """


def _normalize_path(path: str) -> str:
    """
    Normalize one repository-relative path for detector matching.

    :param path: Raw path from a changed-files list.
    :type path: str
    :return: Normalized path using forward slashes and no leading ``./``.
    :rtype: str

    Example::

        >>> _normalize_path(r".\\templates\\c\\machine.c.j2")
        'templates/c/machine.c.j2'
    """
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _matches(pattern: str, path: str) -> bool:
    """
    Return whether one normalized path matches one detector glob.

    :param pattern: Glob-style repository-relative pattern.
    :type pattern: str
    :param path: Normalized repository-relative path.
    :type path: str
    :return: ``True`` when the pattern applies to ``path``.
    :rtype: bool

    Example::

        >>> _matches("templates/c/**", "templates/c/machine.c.j2")
        True
    """
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def _expand_suite_token(token: str) -> Tuple[str, ...]:
    """
    Expand one validated suite token into concrete output suites.

    :param token: Legal suite token, including the special ``all`` token.
    :type token: str
    :return: Concrete suite names represented by ``token``.
    :rtype: tuple[str, ...]
    :raises TemplateSuiteDetectionError: If ``token`` is unknown or empty.

    Example::

        >>> _expand_suite_token("all")
        ('python', 'c', 'c_poll', 'cpp', 'cpp_poll')
    """
    value = token.strip()
    if not value:
        raise TemplateSuiteDetectionError("empty suite token")
    if value not in _LEGAL_INPUT_SUITE_SET:
        raise TemplateSuiteDetectionError("unknown template suite: {0}".format(value))
    if value == "all":
        return DYNAMIC_SUITES
    return (value,)


def _ordered(suites: Iterable[str]) -> List[str]:
    """
    Return concrete suites in the detector's stable suite order.

    :param suites: Suite names to order and deduplicate.
    :type suites: collections.abc.Iterable[str]
    :return: Ordered unique suite names.
    :rtype: list[str]

    Example::

        >>> _ordered(["cpp", "c", "cpp"])
        ['c', 'cpp']
    """
    suite_set = set(suites)
    return [suite for suite in SUITE_ORDER if suite in suite_set]


def _add_reason(
    reasons: MutableMapping[str, List[str]], suite: str, reason: str
) -> None:
    """
    Record one reason for one suite without duplicates.

    :param reasons: Mutable reason mapping.
    :type reasons: dict[str, list[str]]
    :param suite: Concrete suite name.
    :type suite: str
    :param reason: Reason string such as ``path:templates/c/machine.c.j2``.
    :type reason: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> mapping = {}
        >>> _add_reason(mapping, "c", "label:[tpl:c]")
        >>> mapping
        {'c': ['label:[tpl:c]']}
    """
    values = reasons.setdefault(suite, [])
    if reason not in values:
        values.append(reason)


def _parse_suite_list(raw: Optional[str], source: str) -> Tuple[Tuple[str, str], ...]:
    """
    Parse comma-separated suite tokens from CLI or environment text.

    :param raw: Raw comma-separated suite value, or ``None`` for no value.
    :type raw: str, optional
    :param source: Reason prefix to associate with parsed suites.
    :type source: str
    :return: Pairs of concrete suite and reason strings.
    :rtype: tuple[tuple[str, str], ...]
    :raises TemplateSuiteDetectionError: If any token is empty or unknown.

    Example::

        >>> _parse_suite_list("c,c_poll", "include")
        (('c', 'include:c'), ('c_poll', 'include:c_poll'))
    """
    if raw is None:
        return ()
    if raw == "":
        raise TemplateSuiteDetectionError("empty {0} suite token".format(source))
    parsed = []
    for token in raw.split(","):
        value = token.strip()
        if not value:
            raise TemplateSuiteDetectionError("empty {0} suite token".format(source))
        for suite in _expand_suite_token(value):
            parsed.append((suite, "{0}:{1}".format(source, value)))
    return tuple(parsed)


def _parse_message_labels(
    message: str,
) -> Tuple[Tuple[Tuple[str, str], ...], Tuple[Tuple[str, str], ...]]:
    """
    Parse template include and skip labels from one message string.

    The parser is intentionally context-free: labels found in prose or code
    blocks are still treated as commands. Documentation should therefore warn
    maintainers not to include live labels unintentionally.

    :param message: Commit, PR, or dispatch message text.
    :type message: str
    :return: Include pairs and skip pairs as ``(suite, reason)`` tuples.
    :rtype: tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]
    :raises TemplateSuiteDetectionError: If any label is malformed or uses
        an empty or unknown suite token.

    Example::

        >>> _parse_message_labels("[tpl:c] [skip-tpl:cpp]")
        ((('c', 'label:[tpl:c]'),), (('cpp', 'skip:cpp'),))
    """
    includes = []
    skips = []
    for bracket_match in _BRACKET_RE.finditer(message or ""):
        label_text = bracket_match.group(0)
        label_body = bracket_match.group(1)
        if _LABEL_RE.fullmatch(label_text):
            continue
        if _LABEL_LIKE_RE.match(label_body):
            raise TemplateSuiteDetectionError(
                "malformed template label: {0}".format(label_text)
            )
    for match in _LABEL_RE.finditer(message or ""):
        kind = match.group(1)
        raw_token = match.group(2)
        token = raw_token.strip()
        if not token:
            raise TemplateSuiteDetectionError(
                "empty {0} label suite token".format(kind)
            )
        if raw_token != token:
            raise TemplateSuiteDetectionError(
                "whitespace is not allowed in {0} label suite token: {1!r}".format(
                    kind, raw_token
                )
            )
        expanded = _expand_suite_token(token)
        label_text = match.group(0)
        if kind == "tpl":
            includes.extend(
                (suite, "label:{0}".format(label_text)) for suite in expanded
            )
        else:
            skips.extend((suite, "skip:{0}".format(token)) for suite in expanded)
    return tuple(includes), tuple(skips)


def _detect_path_suites(changed_files: Sequence[str]) -> Tuple[Tuple[str, str], ...]:
    """
    Detect protected suites implied by changed repository paths.

    :param changed_files: Repository-relative changed paths.
    :type changed_files: collections.abc.Sequence[str]
    :return: Pairs of concrete suite and reason strings.
    :rtype: tuple[tuple[str, str], ...]

    Example::

        >>> _detect_path_suites(["templates/c/machine.c.j2"])
        (('c', 'path:templates/c/machine.c.j2'), ('cpp', 'path:templates/c/machine.c.j2'))
    """
    detected = []
    for raw_path in changed_files:
        path = _normalize_path(raw_path)
        if not path:
            continue
        metadata_detected = _detect_template_metadata_suites(path)
        if metadata_detected:
            detected.extend(metadata_detected)
            continue
        for patterns, suites, reason_template in _PATH_RULES:
            if any(_matches(pattern, path) for pattern in patterns):
                reason = reason_template.format(path=path)
                detected.extend((suite, reason) for suite in suites)
    return tuple(detected)


def _detect_template_metadata_suites(path: str) -> Tuple[Tuple[str, str], ...]:
    """
    Detect suites for maintainer-only template metadata paths.

    :param path: Normalized repository-relative path.
    :type path: str
    :return: Pairs of concrete suite and reason strings.
    :rtype: tuple[tuple[str, str], ...]

    Example::

        >>> _detect_template_metadata_suites("templates/c/template.json")
        (('template_core', 'path:templates/c/template.json'), ('c', 'path:templates/c/template.json'))
    """
    if path in _UNSCOPED_TEMPLATE_METADATA_PATHS:
        reason = "path:{0}".format(path)
        return tuple((suite, reason) for suite in ("template_core",) + DYNAMIC_SUITES)
    for template_name, suites in _TEMPLATE_METADATA_SUITES.items():
        for pattern_template in _TEMPLATE_METADATA_PATTERNS:
            pattern = pattern_template.format(suite=template_name)
            if _matches(pattern, path):
                reason = "path:{0}".format(path)
                return tuple((suite, reason) for suite in suites)
    return ()


def detect_template_suites(
    changed_files: Sequence[str],
    message: str,
    event_name: str,
    include_suites: Optional[str] = None,
    skip_suites: Optional[str] = None,
) -> Dict[str, object]:
    """
    Return template suite selection as JSON-compatible data.

    :param changed_files: Repository-relative paths changed by the current
        event.
    :type changed_files: collections.abc.Sequence[str]
    :param message: Commit, PR, dispatch, or local message text to scan for
        ``[tpl:*]`` and ``[skip-tpl:*]`` labels.
    :type message: str
    :param event_name: Event source. Must be one of ``push``,
        ``pull_request``, ``workflow_dispatch``, or ``local``.
    :type event_name: str
    :param include_suites: Optional comma-separated include suite override.
        When omitted, ``PYFCSTM_TEMPLATE_SUITES`` is read from the environment.
    :type include_suites: str, optional
    :param skip_suites: Optional comma-separated skip suite override. When
        omitted, ``PYFCSTM_SKIP_TEMPLATE_SUITES`` is read from the environment.
    :type skip_suites: str, optional
    :return: JSON-compatible detector result following schema
        ``template-suite-detector/v1``.
    :rtype: dict[str, object]
    :raises TemplateSuiteDetectionError: If any input token, label, or event
        name is invalid.

    Example::

        >>> detect_template_suites(["templates/c/machine.c.j2"], "", "local")["selected_suites"]
        ['c', 'cpp']
    """
    if event_name not in _EVENT_NAME_SET:
        raise TemplateSuiteDetectionError("unknown event name: {0}".format(event_name))

    reasons = {}  # type: Dict[str, List[str]]
    protected = []  # type: List[str]
    manual = []  # type: List[str]
    skipped_manual = []  # type: List[str]
    legacy_skip_slow = "[skip-slow]" in (message or "")

    for suite, reason in _detect_path_suites(changed_files):
        protected.append(suite)
        _add_reason(reasons, suite, reason)

    label_includes, label_skips = _parse_message_labels(message)
    env_include = include_suites
    if env_include is None:
        env_include = os.environ.get("PYFCSTM_TEMPLATE_SUITES")
    env_skip = skip_suites
    if env_skip is None:
        env_skip = os.environ.get("PYFCSTM_SKIP_TEMPLATE_SUITES")

    include_pairs = label_includes + _parse_suite_list(env_include, "include")
    skip_pairs = label_skips + _parse_suite_list(env_skip, "skip")

    for suite, reason in include_pairs:
        manual.append(suite)
        _add_reason(reasons, suite, reason)

    protected_set = set(protected)
    skip_set = set(suite for suite, _ in skip_pairs)
    for suite, reason in skip_pairs:
        _add_reason(reasons, suite, reason)

    for suite in manual:
        if suite in _FIXED_SUITE_SET:
            continue
        if suite in skip_set and suite not in protected_set:
            skipped_manual.append(suite)

    selected_set = protected_set | set(manual)
    selected_set.difference_update(set(skipped_manual))

    selected = _ordered(selected_set)
    protected_suites = _ordered(protected_set)
    manual_suites = _ordered(manual)
    skipped = _ordered(skipped_manual)
    fixed = _ordered(suite for suite in selected if suite in _FIXED_SUITE_SET)
    if legacy_skip_slow:
        for suite in selected:
            if suite in _DYNAMIC_SUITE_SET:
                _add_reason(reasons, suite, "legacy:skip-slow")

    matrix_include = []
    for suite in selected:
        if suite not in _DYNAMIC_SUITE_SET:
            continue
        suite_reasons = reasons.get(suite, [])
        reason = suite_reasons[0] if suite_reasons else "include:{0}".format(suite)
        matrix_include.append({"suite": suite, "reason": reason})

    ordered_reasons = {
        suite: reasons[suite] for suite in SUITE_ORDER if suite in reasons
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "selected_suites": selected,
        "protected_suites": protected_suites,
        "manual_suites": manual_suites,
        "skipped_manual_suites": skipped,
        "fixed_suites": fixed,
        "reasons": ordered_reasons,
        "matrix": {"include": matrix_include},
        "warnings": [],
    }


def _read_changed_files(path: str) -> List[str]:
    """
    Read changed file paths from a newline-delimited file.

    :param path: File containing repository-relative paths.
    :type path: str
    :return: Changed paths without trailing newline characters.
    :rtype: list[str]
    :raises OSError: If the file cannot be opened or read.
    :raises UnicodeError: If the file is not valid UTF-8 text.

    Example::

        >>> _read_changed_files.__name__
        '_read_changed_files'
    """
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _read_message(path: str) -> str:
    """
    Read detector message text from a file.

    :param path: File containing message text.
    :type path: str
    :return: Message text.
    :rtype: str
    :raises OSError: If the file cannot be opened or read.
    :raises UnicodeError: If the file is not valid UTF-8 text.

    Example::

        >>> _read_message.__name__
        '_read_message'
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    """
    Require one self-check value to match its expected value.

    :param actual: Observed value.
    :type actual: typing.Any
    :param expected: Expected value.
    :type expected: typing.Any
    :param label: Human-readable check label.
    :type label: str
    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteDetectionError: If the two values differ.

    Example::

        >>> _require_equal(["c"], ["c"], "example")
    """
    if actual != expected:
        raise TemplateSuiteDetectionError(
            "self-check failed for {0}: expected {1!r}, got {2!r}".format(
                label, expected, actual
            )
        )


def _check_selected(
    label: str,
    changed_files: Sequence[str],
    message: str,
    expected: Sequence[str],
    include_suites: Optional[str] = None,
    skip_suites: Optional[str] = None,
) -> None:
    """
    Run one detector self-check case for selected suites.

    :param label: Human-readable check label.
    :type label: str
    :param changed_files: Repository-relative changed paths.
    :type changed_files: collections.abc.Sequence[str]
    :param message: Message text to scan for labels.
    :type message: str
    :param expected: Expected ordered selected suites.
    :type expected: collections.abc.Sequence[str]
    :param include_suites: Optional comma-separated include suites.
    :type include_suites: str, optional
    :param skip_suites: Optional comma-separated skip suites.
    :type skip_suites: str, optional
    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteDetectionError: If the check fails.

    Example::

        >>> _check_selected("c core", ["templates/c/machine.c.j2"], "", ["c", "cpp"])
    """
    result = detect_template_suites(
        changed_files,
        message,
        "local",
        include_suites=include_suites,
        skip_suites=skip_suites,
    )
    _require_equal(result["selected_suites"], list(expected), label)


def _check_detection_result(
    label: str,
    changed_files: Sequence[str],
    message: str,
    selected_suites: Optional[Sequence[str]] = None,
    protected_suites: Optional[Sequence[str]] = None,
    manual_suites: Optional[Sequence[str]] = None,
    skipped_manual_suites: Optional[Sequence[str]] = None,
    fixed_suites: Optional[Sequence[str]] = None,
    matrix_suites: Optional[Sequence[str]] = None,
    reasons: Optional[Dict[str, Sequence[str]]] = None,
    include_suites: Optional[str] = None,
    skip_suites: Optional[str] = None,
) -> Dict[str, object]:
    """
    Run one detector self-check case for selected schema fields.

    :param label: Human-readable check label.
    :type label: str
    :param changed_files: Repository-relative changed paths.
    :type changed_files: collections.abc.Sequence[str]
    :param message: Message text to scan for labels.
    :type message: str
    :param selected_suites: Expected ordered ``selected_suites`` value.
    :type selected_suites: collections.abc.Sequence[str], optional
    :param protected_suites: Expected ordered ``protected_suites`` value.
    :type protected_suites: collections.abc.Sequence[str], optional
    :param manual_suites: Expected ordered ``manual_suites`` value.
    :type manual_suites: collections.abc.Sequence[str], optional
    :param skipped_manual_suites: Expected ordered ``skipped_manual_suites``
        value.
    :type skipped_manual_suites: collections.abc.Sequence[str], optional
    :param fixed_suites: Expected ordered ``fixed_suites`` value.
    :type fixed_suites: collections.abc.Sequence[str], optional
    :param matrix_suites: Expected ordered dynamic suite names from
        ``matrix.include``.
    :type matrix_suites: collections.abc.Sequence[str], optional
    :param reasons: Expected reason lists for selected suites.
    :type reasons: dict[str, collections.abc.Sequence[str]], optional
    :param include_suites: Optional comma-separated include suites.
    :type include_suites: str, optional
    :param skip_suites: Optional comma-separated skip suites.
    :type skip_suites: str, optional
    :return: Detector result produced by the checked case.
    :rtype: dict[str, object]
    :raises TemplateSuiteDetectionError: If the check fails.

    Example::

        >>> _check_detection_result(
        ...     "manual skip",
        ...     [],
        ...     "[tpl:c] [skip-tpl:c]",
        ...     selected_suites=[],
        ...     manual_suites=["c"],
        ...     skipped_manual_suites=["c"],
        ... )["matrix"]["include"]
        []
    """
    result = detect_template_suites(
        changed_files,
        message,
        "local",
        include_suites=include_suites,
        skip_suites=skip_suites,
    )
    expected_fields = (
        ("selected_suites", selected_suites),
        ("protected_suites", protected_suites),
        ("manual_suites", manual_suites),
        ("skipped_manual_suites", skipped_manual_suites),
        ("fixed_suites", fixed_suites),
    )
    for field_name, expected in expected_fields:
        if expected is not None:
            _require_equal(
                result[field_name],
                list(expected),
                "{0} {1}".format(label, field_name),
            )
    if matrix_suites is not None:
        _require_equal(
            [item["suite"] for item in result["matrix"]["include"]],
            list(matrix_suites),
            "{0} matrix.include suites".format(label),
        )
    if reasons is not None:
        expected_reasons = {
            suite: list(suite_reasons) for suite, suite_reasons in reasons.items()
        }
        _require_equal(
            result["reasons"],
            expected_reasons,
            "{0} reasons".format(label),
        )
    return result


def _expect_detection_error(label: str, func: Any) -> None:
    """
    Require a callable to fail with :class:`TemplateSuiteDetectionError`.

    :param label: Human-readable check label.
    :type label: str
    :param func: Zero-argument callable under check.
    :type func: typing.Any
    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteDetectionError: If ``func`` does not raise the
        expected detector error.

    Example::

        >>> _expect_detection_error("bad suite", lambda: _expand_suite_token("java"))
    """
    try:
        func()
    except TemplateSuiteDetectionError:
        return
    raise TemplateSuiteDetectionError(
        "self-check failed for {0}: expected detector error".format(label)
    )


def run_self_check() -> None:
    """
    Run the built-in detector contract self-check.

    The self-check intentionally lives in ``tools`` instead of the pytest
    unit-test tree because this detector is maintainer CI tooling rather than
    part of the public :mod:`pyfcstm` runtime package.

    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteDetectionError: If any detector contract check fails.

    Example::

        >>> run_self_check()
    """
    saved_include = os.environ.pop("PYFCSTM_TEMPLATE_SUITES", None)
    saved_skip = os.environ.pop("PYFCSTM_SKIP_TEMPLATE_SUITES", None)
    try:
        _run_self_check_cases()
    finally:
        if saved_include is not None:
            os.environ["PYFCSTM_TEMPLATE_SUITES"] = saved_include
        if saved_skip is not None:
            os.environ["PYFCSTM_SKIP_TEMPLATE_SUITES"] = saved_skip


def _run_self_check_cases() -> None:
    """
    Execute the self-check cases with suite-selection env vars cleared.

    :return: ``None``.
    :rtype: None
    :raises TemplateSuiteDetectionError: If any detector contract check fails.

    Example::

        >>> _run_self_check_cases()
    """
    dynamic = list(DYNAMIC_SUITES)
    c_family = ["c", "c_poll", "cpp", "cpp_poll"]
    path_cases = [
        ("templates/python/machine.py.j2", ["python"]),
        ("templates/c/machine.c.j2", ["c", "cpp"]),
        ("templates/c_poll/machine.c.j2", ["c_poll", "cpp_poll"]),
        ("templates/cpp/machine.cpp.j2", ["cpp"]),
        ("templates/cpp_poll/machine.cpp.j2", ["cpp_poll"]),
        ("pyfcstm/render/render.py", dynamic),
        ("pyfcstm/render/env.py", dynamic),
        ("pyfcstm/render/expr.py", dynamic),
        ("pyfcstm/render/statement.py", dynamic),
        ("pyfcstm/render/func.py", dynamic),
        ("pyfcstm/render/c_runtime.py", c_family),
        ("pyfcstm/utils/text.py", c_family),
        ("pyfcstm/utils/jinja2.py", c_family),
        ("pyfcstm/utils/safe.py", c_family),
        ("pyfcstm/dsl/node.py", dynamic),
        ("pyfcstm/model/model.py", dynamic),
        ("test/fixtures/simulate_semantics/case.json", dynamic),
        ("pyfcstm/simulate/runtime.py", dynamic),
        ("test/testings/simulate_semantics.py", dynamic),
        ("test/testings/native_semantic_alignment.py", c_family),
        ("test/template/test_template.py", ["template_core"]),
        ("test/template/test_template_structure.py", ["template_core"]),
        ("test/template/test_c_family_helper_scope.py", ["template_core"]),
        ("test/template/test_cpp_wrapper_harness_guard.py", ["template_core"]),
        (
            "test/template/test_native_semantic_alignment_framework.py",
            ["template_core"],
        ),
        ("test/template/python/test_runtime.py", ["python"]),
        ("test/template/c/test_runtime.py", ["c", "cpp"]),
        ("test/template/c/test_native_toolchain_alignment.py", ["c", "cpp"]),
        ("test/template/c_poll/test_runtime.py", ["c_poll", "cpp_poll"]),
        (
            "test/template/c_poll/test_native_toolchain_alignment.py",
            ["c_poll", "cpp_poll"],
        ),
        ("test/template/cpp/test_cpp_wrapper.py", ["cpp"]),
        ("test/template/cpp_poll/test_cpp_poll_wrapper.py", ["cpp_poll"]),
        ("test/template/cpp_shared.py", ["cpp", "cpp_poll"]),
        ("test/template/cpp_readme_utils.py", ["cpp", "cpp_poll"]),
        ("test/conftest.py", dynamic),
        ("pytest.ini", dynamic),
        ("Makefile", dynamic),
        ("requirements.txt", dynamic),
        ("requirements-test.txt", dynamic),
        (".github/workflows/test.yml", dynamic),
        ("test/testings/native_toolchain_alignment/profiles.py", c_family),
        ("tools/package_templates.py", dynamic),
        ("pyfcstm/template/__init__.py", dynamic),
        ("templates/c/template.json", ["template_core", "c"]),
        ("templates/python/README.md", ["template_core", "python"]),
        ("templates/README.md", ["template_core"] + dynamic),
    ]
    for path, expected in path_cases:
        result = detect_template_suites([path], "", "local")
        _require_equal(
            result["protected_suites"], expected, "protected path {0}".format(path)
        )
        _require_equal(
            result["selected_suites"], expected, "selected path {0}".format(path)
        )
        _require_equal(
            [item["suite"] for item in result["matrix"]["include"]],
            [suite for suite in expected if suite in _DYNAMIC_SUITE_SET],
            "matrix path {0}".format(path),
        )

    _check_selected(
        "normalized path", ["./templates/c/machine.c.j2", "", " "], "", ["c", "cpp"]
    )
    _check_selected("multiple c labels", [], "[tpl:c] [tpl:c_poll]", ["c", "c_poll"])
    _check_selected(
        "multiple cpp labels", [], "[tpl:cpp] [tpl:cpp_poll]", ["cpp", "cpp_poll"]
    )
    _check_selected("all label", [], "[tpl:all]", dynamic)
    _check_selected("c boundary", [], "[tpl:c_poll] [skip-tpl:c]", ["c_poll"])
    _check_selected("cpp boundary", [], "[tpl:cpp_poll] [skip-tpl:cpp]", ["cpp_poll"])
    _check_selected("include all", [], "", dynamic, include_suites="all")
    _check_selected(
        "include skip manual", [], "", ["cpp"], include_suites="c,cpp", skip_suites="c"
    )
    os.environ["PYFCSTM_TEMPLATE_SUITES"] = "c,c_poll"
    os.environ["PYFCSTM_SKIP_TEMPLATE_SUITES"] = "c"
    try:
        _check_detection_result(
            "environment values",
            [],
            "",
            selected_suites=["c_poll"],
            protected_suites=[],
            manual_suites=["c", "c_poll"],
            skipped_manual_suites=["c"],
            fixed_suites=[],
            matrix_suites=["c_poll"],
            reasons={
                "c": ["include:c", "skip:c"],
                "c_poll": ["include:c_poll"],
            },
        )
    finally:
        os.environ.pop("PYFCSTM_TEMPLATE_SUITES", None)
        os.environ.pop("PYFCSTM_SKIP_TEMPLATE_SUITES", None)
    _check_detection_result(
        "skip slow explicit",
        [],
        "[tpl:c] [skip-slow]",
        selected_suites=["c"],
        protected_suites=[],
        manual_suites=["c"],
        skipped_manual_suites=[],
        fixed_suites=[],
        matrix_suites=["c"],
        reasons={"c": ["label:[tpl:c]", "legacy:skip-slow"]},
    )
    _check_detection_result(
        "skip cannot remove protected",
        ["templates/c/machine.c.j2"],
        "[skip-slow] [skip-tpl:c]",
        selected_suites=["c", "cpp"],
        protected_suites=["c", "cpp"],
        manual_suites=[],
        skipped_manual_suites=[],
        fixed_suites=[],
        matrix_suites=["c", "cpp"],
        reasons={
            "c": ["path:templates/c/machine.c.j2", "skip:c", "legacy:skip-slow"],
            "cpp": ["path:templates/c/machine.c.j2", "legacy:skip-slow"],
        },
    )
    _check_detection_result(
        "manual skip",
        [],
        "[tpl:c] [skip-tpl:c]",
        selected_suites=[],
        protected_suites=[],
        manual_suites=["c"],
        skipped_manual_suites=["c"],
        fixed_suites=[],
        matrix_suites=[],
        reasons={"c": ["label:[tpl:c]", "skip:c"]},
    )
    _check_detection_result(
        "all with skip slow",
        [],
        "[tpl:all] [skip-slow]",
        selected_suites=dynamic,
        protected_suites=[],
        manual_suites=dynamic,
        skipped_manual_suites=[],
        fixed_suites=[],
        matrix_suites=dynamic,
        reasons={suite: ["label:[tpl:all]", "legacy:skip-slow"] for suite in dynamic},
    )
    _check_selected(
        "environment skip cannot remove protected",
        ["templates/cpp/machine.cpp.j2"],
        "",
        ["cpp"],
        skip_suites="cpp",
    )
    _check_detection_result(
        "fixed skip remains fixed",
        [],
        "[tpl:default] [skip-tpl:default]",
        selected_suites=["default"],
        protected_suites=[],
        manual_suites=["default"],
        skipped_manual_suites=[],
        fixed_suites=["default"],
        matrix_suites=[],
        reasons={"default": ["label:[tpl:default]", "skip:default"]},
    )
    _check_detection_result(
        "representative fixed skip remains fixed",
        [],
        "[tpl:template_representative] [skip-tpl:template_representative]",
        selected_suites=["template_representative"],
        protected_suites=[],
        manual_suites=["template_representative"],
        skipped_manual_suites=[],
        fixed_suites=["template_representative"],
        matrix_suites=[],
        reasons={
            "template_representative": [
                "label:[tpl:template_representative]",
                "skip:template_representative",
            ]
        },
    )
    _check_detection_result(
        "all self cancel",
        [],
        "[tpl:all] [skip-tpl:all]",
        selected_suites=[],
        protected_suites=[],
        manual_suites=dynamic,
        skipped_manual_suites=dynamic,
        fixed_suites=[],
        matrix_suites=[],
        reasons={suite: ["label:[tpl:all]", "skip:all"] for suite in dynamic},
    )

    result = detect_template_suites(
        ["templates/c/machine.c.j2"], "[tpl:template_core]", "local"
    )
    _require_equal(result["fixed_suites"], ["template_core"], "fixed suite reporting")
    _require_equal(
        [item["suite"] for item in result["matrix"]["include"]],
        ["c", "cpp"],
        "fixed suite excluded from dynamic matrix",
    )

    result = detect_template_suites(
        ["templates/c/machine.c.j2"], "[tpl:c] [skip-slow]", "local"
    )
    _require_equal(
        result["matrix"]["include"],
        [
            {"suite": "c", "reason": "path:templates/c/machine.c.j2"},
            {"suite": "cpp", "reason": "path:templates/c/machine.c.j2"},
        ],
        "protected path reason precedence",
    )

    empty = detect_template_suites([], "", "local")
    _require_equal(
        empty,
        {
            "schema_version": SCHEMA_VERSION,
            "selected_suites": [],
            "protected_suites": [],
            "manual_suites": [],
            "skipped_manual_suites": [],
            "fixed_suites": [],
            "reasons": {},
            "matrix": {"include": []},
            "warnings": [],
        },
        "empty schema",
    )

    _expect_detection_error(
        "unknown label", lambda: detect_template_suites([], "[tpl:java]", "local")
    )
    _expect_detection_error(
        "empty label", lambda: detect_template_suites([], "[tpl:]", "local")
    )
    _expect_detection_error(
        "leading label whitespace",
        lambda: detect_template_suites([], "[tpl: c]", "local"),
    )
    _expect_detection_error(
        "trailing label whitespace",
        lambda: detect_template_suites([], "[tpl:c ]", "local"),
    )
    _expect_detection_error(
        "skip label whitespace",
        lambda: detect_template_suites([], "[skip-tpl: c]", "local"),
    )
    _expect_detection_error(
        "label name whitespace",
        lambda: detect_template_suites([], "[tpl :c]", "local"),
    )
    _expect_detection_error(
        "label name and token whitespace",
        lambda: detect_template_suites([], "[tpl : c]", "local"),
    )
    _expect_detection_error(
        "skip label name whitespace",
        lambda: detect_template_suites([], "[skip-tpl :c]", "local"),
    )
    _expect_detection_error(
        "leading bracket whitespace",
        lambda: detect_template_suites([], "[ tpl:c]", "local"),
    )
    _expect_detection_error(
        "missing label colon",
        lambda: detect_template_suites([], "[tpl c]", "local"),
    )
    _expect_detection_error(
        "unknown include",
        lambda: detect_template_suites([], "", "local", include_suites="java"),
    )
    _expect_detection_error(
        "empty include token",
        lambda: detect_template_suites([], "", "local", include_suites="c,,cpp"),
    )
    _expect_detection_error(
        "empty skip value",
        lambda: detect_template_suites([], "", "local", skip_suites=""),
    )
    _expect_detection_error(
        "unknown event", lambda: detect_template_suites([], "", "schedule")
    )


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    :return: Configured argument parser for the detector CLI.
    :rtype: argparse.ArgumentParser

    Example::

        >>> parser = _build_parser()
        >>> parser.prog
        'detect_template_suites'
    """
    parser = argparse.ArgumentParser(
        prog="detect_template_suites",
        description="Detect pyfcstm template test suites affected by changed paths and labels.",
    )
    parser.add_argument("--changed-files", help="Newline-delimited changed files list.")
    parser.add_argument(
        "--commit-message-file",
        help="Message file to scan for [tpl:*] labels.",
    )
    parser.add_argument(
        "--event-name",
        choices=_EVENT_NAMES,
        help="Event source: push, pull_request, workflow_dispatch, or local.",
    )
    parser.add_argument(
        "--include-suites", help="Comma-separated suite include override."
    )
    parser.add_argument("--skip-suites", help="Comma-separated suite skip override.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the repository-tool self-check instead of detecting one event.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the template suite detector command-line interface.

    :param argv: Optional argument vector without the program name. ``None``
        reads arguments from :data:`sys.argv`.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process-style exit code. ``0`` means success, ``2`` invalid
        detector input, ``3`` unreadable or non-UTF-8 input files, and ``4``
        JSON output failure.
    :rtype: int

    Example::

        $ python tools/detect_template_suites.py --check
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.check:
        try:
            run_self_check()
        except TemplateSuiteDetectionError as err:
            parser.exit(2, "detect_template_suites: {0}\n".format(err))
        sys.stdout.write("template suite detector self-check passed\n")
        return 0

    if not args.changed_files:
        parser.error("--changed-files is required unless --check is used")
    if not args.commit_message_file:
        parser.error("--commit-message-file is required unless --check is used")
    if not args.event_name:
        parser.error("--event-name is required unless --check is used")

    try:
        changed_files = _read_changed_files(args.changed_files)
        message = _read_message(args.commit_message_file)
    except (OSError, UnicodeError) as err:
        # OSError: the changed-files or message input path cannot be read.
        # UnicodeError: those input files must be UTF-8 text.
        parser.exit(
            3, "detect_template_suites: cannot read input file: {0}\n".format(err)
        )

    try:
        result = detect_template_suites(
            changed_files=changed_files,
            message=message,
            event_name=args.event_name,
            include_suites=args.include_suites,
            skip_suites=args.skip_suites,
        )
    except TemplateSuiteDetectionError as err:
        parser.exit(2, "detect_template_suites: {0}\n".format(err))

    if args.json:
        try:
            json.dump(result, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        except (TypeError, ValueError) as err:
            # TypeError/ValueError: json.dump can reject non-serializable or
            # invalid JSON values if the schema implementation regresses.
            parser.exit(
                4, "detect_template_suites: cannot write JSON: {0}\n".format(err)
            )
    else:
        sys.stdout.write(
            "selected_suites={0}\n".format(",".join(result["selected_suites"]))
        )
    return 0
