"""
Detect CI route decisions from repository changed paths.

This repo-local maintenance command decides whether a ``Code Test`` workflow
run needs expensive code-side jobs or can finish through the lightweight route
and gate path. It intentionally keeps CI routing policy outside the public
:mod:`pyfcstm` runtime package while still giving GitHub Actions a stable JSON
schema to consume.

The command classifies changed repository paths into code, JavaScript/editor,
CLI/package, documentation, and documentation-resource groups. Unknown paths
fail closed so a newly added runtime path cannot silently bypass expensive
checks.

The module contains:

* :class:`CiRouteDetectionError` - Invalid detector input or failed self-checks.
* :func:`detect_ci_routes` - Return JSON-compatible routing decisions.
* :func:`main` - CLI entry point for ``.github/scripts/detect_ci_routes.py``.

Example::

    >>> result = detect_ci_routes(["docs/source/tutorials/index.rst"], "local")
    >>> result["run_expensive_code_test"]
    False
    >>> detect_ci_routes(["pyfcstm/model/model.py"], "local")["run_expensive_code_test"]
    True
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence

SCHEMA_VERSION = "ci-route-detector/v1"
_EVENT_NAMES = ("push", "pull_request", "workflow_dispatch", "local")
_EVENT_NAME_SET = set(_EVENT_NAMES)

_CODE_PATTERNS = (
    "pyfcstm/**",
    "test/**",
    "templates/**",
    "tools/**",
    "requirements.txt",
    "requirements-test.txt",
    "requirements-dev.txt",
    "pytest.ini",
    "Makefile",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "MANIFEST.in",
    "pyfcstm_cli.py",
    "antlr_req.py",
    "sample_test_generator.py",
    "sample_test_neg_generator.py",
    "codecov.yml",
    ".github/workflows/test.yml",
    ".github/scripts/detect_ci_routes.py",
    ".github/workflows/release.yml",
    ".github/workflows/release_test.yml",
)
_JS_PATTERNS = (
    "editors/jsfcstm/**",
    "editors/vscode/**",
    "editors/fcstm.tmLanguage.json",
    ".github/linguist/**",
)
_CLI_PATTERNS = (
    "pyfcstm/**",
    "templates/**",
    "tools/**",
    "requirements.txt",
    "requirements-build.txt",
    "Makefile",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "MANIFEST.in",
    "pyfcstm_cli.py",
    "logos/**",
    "docs/source/tutorials/cli/simple_machine.fcstm",
    ".github/workflows/test.yml",
    ".github/workflows/release.yml",
    ".github/workflows/release_test.yml",
)
_DOCS_META_PATTERNS = (
    "docs/**",
    "pyfcstm/*.py",
    "pyfcstm/**/*.py",
    "pyfcstm/diagnostics/codes.yaml",
    "tools/check_docs_pdf.py",
    "requirements.txt",
    "requirements-doc.txt",
    "auto_rst.py",
    "auto_rst_top_index.py",
    "Makefile",
    ".readthedocs.yaml",
    ".github/workflows/docs-check.yml",
    ".github/scripts/detect_ci_routes.py",
    ".github/workflows/doc.yml.deprecated",
    "logos/**",
)
_SAFE_MAINTENANCE_PATTERNS = (
    ".gitattributes",
    ".gitignore",
    ".llmconfig.yaml.example",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "README_*.md",
    "llm_eval/**",
    "mds/**",
    ".github/workflows/badge.yml",
    ".github/workflows/native-toolchain.yml",
)
_DOC_RESOURCE_SUFFIXES = (
    ".fcstm",
    ".puml",
    ".gv",
    ".demo.py",
    ".demox.py",
    ".plot.py",
    ".demo.sh",
    ".demox.sh",
    ".ipynb",
)
_DOC_GENERATED_RESOURCE_SUFFIXES = (
    ".fcstm.puml",
    ".fcstm.puml.png",
    ".fcstm.puml.svg",
    ".puml.png",
    ".puml.svg",
    ".gv.png",
    ".gv.svg",
    ".demo.py.txt",
    ".demox.py.txt",
    ".demox.py.err",
    ".demox.py.exitcode",
    ".plot.py.svg",
    ".demo.sh.txt",
    ".demox.sh.txt",
    ".demox.sh.err",
    ".demox.sh.exitcode",
    ".result.ipynb",
)


class CiRouteDetectionError(ValueError):
    """
    Report invalid input for CI route detection.

    :param message: Human-readable validation failure.
    :type message: str

    Example::

        >>> CiRouteDetectionError("unknown event").args[0]
        'unknown event'
    """


def _normalize_path(path: str) -> str:
    """
    Normalize one repository-relative path for detector matching.

    :param path: Raw path from a changed-files list.
    :type path: str
    :return: Normalized path with forward slashes and no leading ``./``.
    :rtype: str

    Example::

        >>> _normalize_path(r".\\docs\\index.rst")
        'docs/index.rst'
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
    :return: ``True`` when ``pattern`` applies to ``path``.
    :rtype: bool

    Example::

        >>> _matches("docs/**", "docs/source/index.rst")
        True
        >>> _matches("docs/**", "docs")
        False
    """
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def _matches_any(patterns: Sequence[str], path: str) -> bool:
    """
    Return whether one path matches any glob in ``patterns``.

    :param patterns: Glob-style repository-relative patterns.
    :type patterns: collections.abc.Sequence[str]
    :param path: Normalized repository-relative path.
    :type path: str
    :return: ``True`` when at least one pattern matches.
    :rtype: bool

    Example::

        >>> _matches_any(("pyfcstm/**",), "pyfcstm/model/model.py")
        True
    """
    return any(_matches(pattern, path) for pattern in patterns)


def _is_docs_resource_path(path: str) -> bool:
    """
    Return whether one docs path belongs to generated-resource routing.

    :param path: Normalized repository-relative path.
    :type path: str
    :return: ``True`` when documentation contents generation should run.
    :rtype: bool

    Example::

        >>> _is_docs_resource_path("docs/source/tutorials/demo.fcstm")
        True
        >>> _is_docs_resource_path("docs/source/tutorials/index.rst")
        False
    """
    if not path.startswith("docs/"):
        return False
    if path.endswith(".result.ipynb"):
        return True
    return path.endswith(_DOC_RESOURCE_SUFFIXES) or path.endswith(
        _DOC_GENERATED_RESOURCE_SUFFIXES
    )


def _ordered_unique(values: Iterable[str]) -> List[str]:
    """
    Return values in first-seen order without duplicates.

    :param values: Values to deduplicate.
    :type values: collections.abc.Iterable[str]
    :return: Ordered unique values.
    :rtype: list[str]

    Example::

        >>> _ordered_unique(["a", "b", "a"])
        ['a', 'b']
    """
    seen = set()
    ordered = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def detect_ci_routes(
    changed_files: Sequence[str],
    event_name: str,
    fail_closed: bool = False,
) -> Dict[str, object]:
    """
    Return CI route decisions as JSON-compatible data.

    :param changed_files: Repository-relative paths changed by the current event.
    :type changed_files: collections.abc.Sequence[str]
    :param event_name: Event source. Must be one of ``push``,
        ``pull_request``, ``workflow_dispatch``, or ``local``.
    :type event_name: str
    :param fail_closed: Whether to force all expensive routes because the diff
        could not be trusted.
    :type fail_closed: bool, optional
    :return: JSON-compatible detector result following schema
        ``ci-route-detector/v1``.
    :rtype: dict[str, object]
    :raises CiRouteDetectionError: If ``event_name`` is unknown.

    Example::

        >>> detect_ci_routes(["README.md"], "local")["code_test_relevant"]
        False
        >>> detect_ci_routes(["editors/jsfcstm/src/index.ts"], "local")["run_jsfcstm_test"]
        True
    """
    if event_name not in _EVENT_NAME_SET:
        raise CiRouteDetectionError("unknown event name: {0}".format(event_name))

    normalized_files = _ordered_unique(
        path for path in (_normalize_path(path) for path in changed_files) if path
    )
    reasons = []  # type: List[str]
    classifications = []  # type: List[Dict[str, object]]

    if fail_closed or event_name == "workflow_dispatch":
        reason = "fail-closed" if fail_closed else "event:workflow_dispatch"
        return {
            "schema_version": SCHEMA_VERSION,
            "event_name": event_name,
            "changed_files": normalized_files,
            "docs_changed": True,
            "docs_resource_changed": True,
            "code_changed": True,
            "js_changed": True,
            "cli_changed": True,
            "code_test_relevant": True,
            "run_expensive_code_test": True,
            "run_cli_build": True,
            "run_jsfcstm_test": True,
            "run_docs_check": True,
            "fail_closed": True,
            "reasons": [reason],
            "path_classifications": [
                {"path": path, "groups": [reason]} for path in normalized_files
            ],
        }

    docs_changed = False
    docs_resource_changed = False
    code_changed = False
    js_changed = False
    cli_changed = False

    for path in normalized_files:
        groups = []  # type: List[str]
        if _matches_any(_DOCS_META_PATTERNS, path):
            docs_changed = True
            groups.append("docs")
            if _is_docs_resource_path(path) or _matches("logos/**", path):
                docs_resource_changed = True
                groups.append("docs-resource")
        if _matches_any(_JS_PATTERNS, path):
            js_changed = True
            groups.append("js-editor")
        if _matches_any(_CODE_PATTERNS, path):
            code_changed = True
            groups.append("code")
        if _matches_any(_CLI_PATTERNS, path):
            cli_changed = True
            groups.append("cli-package")

        if not groups and _matches_any(_SAFE_MAINTENANCE_PATTERNS, path):
            groups.append("safe-maintenance")

        if not groups:
            code_changed = True
            cli_changed = True
            groups.append("unknown-fail-closed")

        classifications.append({"path": path, "groups": groups})
        for group in groups:
            reasons.append("{0}:{1}".format(group, path))

    run_expensive_code_test = code_changed
    run_cli_build = cli_changed
    run_jsfcstm_test = js_changed
    code_test_relevant = run_expensive_code_test or run_cli_build or run_jsfcstm_test
    run_docs_check = docs_changed

    return {
        "schema_version": SCHEMA_VERSION,
        "event_name": event_name,
        "changed_files": normalized_files,
        "docs_changed": docs_changed,
        "docs_resource_changed": docs_resource_changed,
        "code_changed": code_changed,
        "js_changed": js_changed,
        "cli_changed": cli_changed,
        "code_test_relevant": code_test_relevant,
        "run_expensive_code_test": run_expensive_code_test,
        "run_cli_build": run_cli_build,
        "run_jsfcstm_test": run_jsfcstm_test,
        "run_docs_check": run_docs_check,
        "fail_closed": False,
        "reasons": reasons,
        "path_classifications": classifications,
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

        >>> from tempfile import NamedTemporaryFile
        >>> with NamedTemporaryFile('w+', encoding='utf-8') as f:
        ...     _ = f.write('a.py\n\n b.py \n')
        ...     _ = f.flush()
        ...     _read_changed_files(f.name)
        ['a.py', 'b.py']
    """
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


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
    :raises CiRouteDetectionError: If the two values differ.

    Example::

        >>> _require_equal(True, True, "example")
    """
    if actual != expected:
        raise CiRouteDetectionError(
            "self-check failed for {0}: expected {1!r}, got {2!r}".format(
                label, expected, actual
            )
        )


def _check_case(
    label: str,
    changed_files: Sequence[str],
    code_test_relevant: bool,
    run_expensive_code_test: bool,
    run_cli_build: bool,
    run_jsfcstm_test: bool,
    run_docs_check: bool,
    docs_resource_changed: bool = False,
    event_name: str = "local",
    fail_closed: bool = False,
) -> None:
    """
    Run one route detector self-check case.

    :param label: Human-readable check label.
    :type label: str
    :param changed_files: Repository-relative changed paths.
    :type changed_files: collections.abc.Sequence[str]
    :param code_test_relevant: Expected overall Code Test relevance.
    :type code_test_relevant: bool
    :param run_expensive_code_test: Expected Python/template job route.
    :type run_expensive_code_test: bool
    :param run_cli_build: Expected CLI build route.
    :type run_cli_build: bool
    :param run_jsfcstm_test: Expected jsfcstm route.
    :type run_jsfcstm_test: bool
    :param run_docs_check: Expected docs workflow route.
    :type run_docs_check: bool
    :param docs_resource_changed: Expected docs contents/resource route,
        defaults to ``False``.
    :type docs_resource_changed: bool, optional
    :param event_name: Event name passed to the detector, defaults to ``local``.
    :type event_name: str, optional
    :param fail_closed: Whether to force fail-closed route, defaults to ``False``.
    :type fail_closed: bool, optional
    :return: ``None``.
    :rtype: None
    :raises CiRouteDetectionError: If any expected field differs.

    Example::

        >>> _check_case("readme", ["README.md"], False, False, False, False, False)
    """
    result = detect_ci_routes(changed_files, event_name, fail_closed=fail_closed)
    expected = {
        "code_test_relevant": code_test_relevant,
        "run_expensive_code_test": run_expensive_code_test,
        "run_cli_build": run_cli_build,
        "run_jsfcstm_test": run_jsfcstm_test,
        "run_docs_check": run_docs_check,
        "docs_resource_changed": docs_resource_changed,
    }
    for field_name, expected_value in expected.items():
        _require_equal(
            result[field_name],
            expected_value,
            "{0} {1}".format(label, field_name),
        )


def run_self_check() -> None:
    """
    Run built-in route detector self-checks.

    :return: ``None``.
    :rtype: None
    :raises CiRouteDetectionError: If any self-check fails.

    Example::

        >>> run_self_check()
    """
    _check_case(
        "docs text",
        ["docs/source/tutorials/index.rst"],
        False,
        False,
        False,
        False,
        True,
    )
    _check_case(
        "docs resource",
        ["docs/source/tutorials/example.fcstm"],
        False,
        False,
        False,
        False,
        True,
        docs_resource_changed=True,
    )
    _check_case(
        "autodoc Python source",
        ["pyfcstm/diagnostics/codes.py"],
        True,
        True,
        True,
        False,
        True,
    )
    _check_case(
        "top-level autodoc Python source",
        ["pyfcstm/__init__.py"],
        True,
        True,
        True,
        False,
        True,
    )
    _check_case(
        "autodoc registry data",
        ["pyfcstm/diagnostics/codes.yaml"],
        True,
        True,
        True,
        False,
        True,
    )
    _check_case(
        "PDF validator",
        ["tools/check_docs_pdf.py"],
        True,
        True,
        True,
        False,
        True,
    )
    _check_case(
        "root Makefile PDF entry",
        ["Makefile"],
        True,
        True,
        True,
        False,
        True,
    )
    _check_case(
        "CLI docs fixture",
        ["docs/source/tutorials/cli/simple_machine.fcstm"],
        True,
        False,
        True,
        False,
        True,
        docs_resource_changed=True,
    )
    _check_case("root readme", ["README.md"], False, False, False, False, False)
    _check_case("rst generator", ["auto_rst.py"], False, False, False, False, True)
    _check_case("claude maintenance", ["CLAUDE.md"], False, False, False, False, False)
    _check_case(
        "badge workflow",
        [".github/workflows/badge.yml"],
        False,
        False,
        False,
        False,
        False,
    )
    _check_case(
        "manual native workflow",
        [".github/workflows/native-toolchain.yml"],
        False,
        False,
        False,
        False,
        False,
    )
    _check_case(
        "mds asset", ["mds/research-note.md"], False, False, False, False, False
    )
    _check_case(
        "python code", ["pyfcstm/model/model.py"], True, True, True, False, True
    )
    _check_case(
        "pytest fixture", ["test/model/test_model.py"], True, True, False, False, False
    )
    _check_case(
        "template source", ["templates/c/machine.c.j2"], True, True, True, False, False
    )
    _check_case(
        "CI route helper",
        [".github/scripts/detect_ci_routes.py"],
        True,
        True,
        False,
        False,
        True,
    )
    _check_case("cli metadata", ["setup.py"], True, True, True, False, False)
    _check_case(
        "build requirements",
        ["requirements-build.txt"],
        True,
        False,
        True,
        False,
        False,
    )
    _check_case(
        "js source", ["editors/jsfcstm/src/index.ts"], True, False, False, True, False
    )
    _check_case(
        "vscode source",
        ["editors/vscode/src/extension.ts"],
        True,
        False,
        False,
        True,
        False,
    )
    _check_case(
        "logo runtime asset",
        ["logos/logo.svg"],
        True,
        False,
        True,
        False,
        True,
        docs_resource_changed=True,
    )
    _check_case(
        "mixed docs code",
        ["docs/source/index.rst", "pyfcstm/dsl/node.py"],
        True,
        True,
        True,
        False,
        True,
    )
    _check_case(
        "unknown fail closed",
        ["new_runtime_manifest.toml"],
        True,
        True,
        True,
        False,
        False,
    )
    _check_case(
        "workflow dispatch",
        [],
        True,
        True,
        True,
        True,
        True,
        docs_resource_changed=True,
        event_name="workflow_dispatch",
    )
    _check_case(
        "diff failure",
        [],
        True,
        True,
        True,
        True,
        True,
        docs_resource_changed=True,
        event_name="push",
        fail_closed=True,
    )
    try:
        detect_ci_routes([], "schedule")
    except CiRouteDetectionError:
        pass
    else:
        raise CiRouteDetectionError("self-check failed for unknown event")


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    :return: Configured argument parser for the detector CLI.
    :rtype: argparse.ArgumentParser

    Example::

        >>> parser = _build_parser()
        >>> parser.prog
        'detect_ci_routes'
    """
    parser = argparse.ArgumentParser(
        prog="detect_ci_routes",
        description="Detect pyfcstm CI routes affected by changed paths.",
    )
    parser.add_argument("--changed-files", help="Newline-delimited changed files list.")
    parser.add_argument(
        "--event-name",
        choices=_EVENT_NAMES,
        help="Event source: push, pull_request, workflow_dispatch, or local.",
    )
    parser.add_argument(
        "--fail-closed",
        action="store_true",
        help="Force all expensive routes because the diff could not be trusted.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the repository-tool self-check instead of detecting one event.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the CI route detector command-line interface.

    :param argv: Optional argument vector without the program name. ``None``
        reads arguments from :data:`sys.argv`.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process-style exit code. ``0`` means success, ``2`` invalid
        detector input, ``3`` unreadable or non-UTF-8 input files, and ``4``
        JSON output failure.
    :rtype: int

    Example::

        $ python .github/scripts/detect_ci_routes.py --check
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.check:
        try:
            run_self_check()
        except CiRouteDetectionError as err:
            parser.exit(2, "detect_ci_routes: {0}\n".format(err))
        sys.stdout.write("CI route detector self-check passed\n")
        return 0

    if not args.changed_files:
        parser.error("--changed-files is required unless --check is used")
    if not args.event_name:
        parser.error("--event-name is required unless --check is used")

    try:
        changed_files = _read_changed_files(args.changed_files)
    except (OSError, UnicodeError) as err:
        # OSError: the changed-files input path cannot be read.
        # UnicodeError: the changed-files input file must be UTF-8 text.
        parser.exit(3, "detect_ci_routes: cannot read input file: {0}\n".format(err))

    try:
        result = detect_ci_routes(
            changed_files=changed_files,
            event_name=args.event_name,
            fail_closed=args.fail_closed,
        )
    except CiRouteDetectionError as err:
        parser.exit(2, "detect_ci_routes: {0}\n".format(err))

    if args.json:
        try:
            json.dump(result, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        except (TypeError, ValueError) as err:
            # TypeError/ValueError: json.dump can reject non-serializable or
            # invalid JSON values if the schema implementation regresses.
            parser.exit(4, "detect_ci_routes: cannot write JSON: {0}\n".format(err))
    else:
        sys.stdout.write(
            "code_test_relevant={0}\n".format(str(result["code_test_relevant"]).lower())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
