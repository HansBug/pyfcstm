#!/usr/bin/env python3
"""Check CLI reference documentation markers against Click command facts.

This tools-only maintenance command verifies synchronization markers in
``docs/source/reference/cli/``.  It intentionally checks inventory markers, not
human prose quality.

Marker grammar
--------------

Markers are Sphinx-safe comment-shaped lines.  Each marker must fit on one
physical line and start with ``.. `` followed by an unregistered marker name::

    .. cli-ref-command: name=visualize
    .. cli-ref-option: command=visualize option=--renderer choices=local,remote,auto
    .. cli-ref-boundary: command=visualize stdout stderr exit-status side-effects cache suffix open headless check-mode

Arguments use shell-like ``key=value`` tokens.  Token order does not matter.
Unknown marker groups, missing required keys, malformed tokens, and unknown
optional keys are reported as documentation errors.

The checker derives command names, option names, choice lists, and stable
choice-option defaults from Click.  Semantic facts such as stdout, stderr, exit
status, file side effects, and failure taxonomy are human marker commitments;
Click cannot infer them reliably, so this checker verifies that the
corresponding markers exist and are associated with the right command.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Dict, List, Mapping, MutableMapping, Sequence, Set, Tuple

import click

_REPO_ROOT = Path(__file__).resolve().parents[1]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pyfcstm.entry.cli import pyfcstmcli  # noqa: E402

_OptionFact = Dict[str, str]

_LANG_FILES = {
    "en": _REPO_ROOT / "docs/source/reference/cli/index.rst",
    "zh": _REPO_ROOT / "docs/source/reference/cli/index_zh.rst",
}

_MARKER_SCHEMAS = {
    "cli-ref-command": (frozenset(("name",)), frozenset()),
    "cli-ref-option": (
        frozenset(("command", "option")),
        frozenset(("choices", "default")),
    ),
    "cli-ref-boundary": (frozenset(("command",)), frozenset()),
}

_REQUIRED_BOUNDARIES = {
    "generate": frozenset(
        (
            "stdout",
            "stderr",
            "exit-status",
            "side-effects",
            "success-signal",
            "failure-taxonomy",
            "clear",
        )
    ),
    "inspect": frozenset(
        (
            "stdout",
            "stderr",
            "exit-status",
            "side-effects",
            "success-signal",
            "failure-taxonomy",
            "output-formats",
            "verify-policy",
        )
    ),
    "plantuml": frozenset(
        (
            "stdout",
            "stderr",
            "exit-status",
            "side-effects",
            "success-signal",
            "failure-taxonomy",
            "source-only",
        )
    ),
    "simulate": frozenset(
        (
            "stdout",
            "stderr",
            "exit-status",
            "side-effects",
            "success-signal",
            "failure-taxonomy",
            "interactive",
            "batch",
        )
    ),
    "visualize": frozenset(
        (
            "stdout",
            "stderr",
            "exit-status",
            "side-effects",
            "success-signal",
            "failure-taxonomy",
            "cache",
            "suffix",
            "open",
            "headless",
            "check-mode",
        )
    ),
}

_MANUAL_TOP_LEVEL_OPTIONS = {
    "--version",
    "--help",
}

_MANUAL_COMMAND_HELP_OPTION = "--help"


class CheckFailure(Exception):
    """Raised when CLI reference marker checks find one or more failures."""


def _option_strings(option: click.Option) -> List[str]:
    values = []
    for opt in tuple(option.opts) + tuple(option.secondary_opts):
        if opt:
            values.append(str(opt))
    return values


def _stable_default(option: click.Option) -> str:
    value = option.default
    if isinstance(value, tuple):
        return ",".join(str(item) for item in value)
    return str(value)


def _command_option_facts() -> Dict[str, Dict[str, _OptionFact]]:
    facts: Dict[str, Dict[str, _OptionFact]] = {}
    for command_name, command in sorted(pyfcstmcli.commands.items()):
        options: Dict[str, _OptionFact] = {}
        for param in command.params:
            if isinstance(param, click.Option):
                choices = ""
                if isinstance(param.type, click.Choice):
                    choices = ",".join(str(choice) for choice in param.type.choices)
                for opt in _option_strings(param):
                    options[opt] = {
                        "choices": choices,
                        "default": _stable_default(param),
                    }
        options[_MANUAL_COMMAND_HELP_OPTION] = {"choices": "", "default": ""}
        facts[command_name] = options
    return facts


def _read_lines(path: Path) -> List[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as err:
        # OSError: Path.read_text() raises this for missing or unreadable docs.
        raise CheckFailure("%s cannot be read: %s" % (path, err))


def _parse_marker_line(
    path: Path, lineno: int, line: str
) -> Tuple[str, Dict[str, str], Set[str]]:
    content = line[3:].strip()
    group, sep, rest = content.partition(":")
    if not sep:
        raise CheckFailure("%s:%s marker must contain ':' separator." % (path, lineno))
    group = group.strip()
    if group not in _MARKER_SCHEMAS:
        raise CheckFailure("%s:%s unknown CLI marker group %r." % (path, lineno, group))
    try:
        tokens = shlex.split(rest.strip())
    except ValueError as err:
        # ValueError: shlex.split() raises this for malformed marker quoting.
        raise CheckFailure(
            "%s:%s invalid marker token syntax: %s" % (path, lineno, err)
        )

    values: Dict[str, str] = {}
    flags: Set[str] = set()
    required, optional = _MARKER_SCHEMAS[group]
    allowed = required | optional
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            if key not in allowed:
                raise CheckFailure(
                    "%s:%s unknown key %r for marker %s." % (path, lineno, key, group)
                )
            if not value:
                raise CheckFailure(
                    "%s:%s key %r must not be empty." % (path, lineno, key)
                )
            values[key] = value
        else:
            flags.add(token)

    missing = required - set(values)
    if missing:
        raise CheckFailure(
            "%s:%s marker %s missing required keys: %s."
            % (path, lineno, group, ", ".join(sorted(missing)))
        )
    return group, values, flags


def _collect_markers(
    path: Path,
) -> MutableMapping[str, List[Tuple[Dict[str, str], Set[str]]]]:
    markers: MutableMapping[str, List[Tuple[Dict[str, str], Set[str]]]] = {
        name: [] for name in _MARKER_SCHEMAS
    }
    for lineno, line in enumerate(_read_lines(path), start=1):
        if line.startswith(".. cli-ref-"):
            group, values, flags = _parse_marker_line(path, lineno, line)
            markers[group].append((values, flags))
    return markers


def _option_markers(
    markers: Mapping[str, List[Tuple[Dict[str, str], Set[str]]]],
) -> Dict[Tuple[str, str], Dict[str, str]]:
    result: Dict[Tuple[str, str], Dict[str, str]] = {}
    duplicates: List[Tuple[str, str]] = []
    for values, _flags in markers["cli-ref-option"]:
        key = (values["command"], values["option"])
        if key in result:
            duplicates.append(key)
        result[key] = values
    if duplicates:
        duplicate_text = ", ".join(
            "command=%s option=%s" % (command, option)
            for command, option in sorted(duplicates)
        )
        raise CheckFailure("duplicate cli-ref-option marker(s): %s" % duplicate_text)
    return result


def _boundary_markers(
    markers: Mapping[str, List[Tuple[Dict[str, str], Set[str]]]],
) -> Dict[str, Set[str]]:
    result: Dict[str, Set[str]] = {}
    for values, flags in markers["cli-ref-boundary"]:
        command = values["command"]
        result.setdefault(command, set()).update(flags)
    return result


def _check_one(
    path: Path, command_facts: Mapping[str, Mapping[str, _OptionFact]]
) -> List[str]:
    errors: List[str] = []
    try:
        markers = _collect_markers(path)
    except CheckFailure as err:
        # CheckFailure: marker parsing detected malformed documentation syntax.
        return [str(err)]

    found_commands = {values["name"] for values, _flags in markers["cli-ref-command"]}
    expected_commands = set(command_facts)
    for command in sorted(expected_commands - found_commands):
        errors.append("%s missing cli-ref-command for %s" % (path, command))
    for command in sorted(found_commands - expected_commands):
        errors.append("%s has stale cli-ref-command for %s" % (path, command))

    try:
        option_markers = _option_markers(markers)
    except CheckFailure as err:
        # CheckFailure: duplicate option markers make exact metadata ambiguous.
        return [str(err)]
    found_options = set(option_markers)
    expected_options = {
        (command, option)
        for command, options in command_facts.items()
        for option in options
    }
    expected_options.update(
        ("top-level", option) for option in _MANUAL_TOP_LEVEL_OPTIONS
    )
    for command, option in sorted(expected_options - found_options):
        errors.append(
            "%s missing cli-ref-option command=%s option=%s" % (path, command, option)
        )
    for command, option in sorted(found_options - expected_options):
        errors.append(
            "%s has stale cli-ref-option command=%s option=%s" % (path, command, option)
        )
    for command, option in sorted(found_options & expected_options):
        values = option_markers[(command, option)]
        fact = command_facts.get(command, {}).get(option, {})
        expected_choices = fact.get("choices", "")
        found_choices = values.get("choices", "")
        if expected_choices and not found_choices:
            errors.append(
                "%s missing cli-ref-option choices for command=%s option=%s"
                % (path, command, option)
            )
        elif expected_choices != found_choices:
            errors.append(
                "%s has stale cli-ref-option choices for command=%s option=%s: "
                "expected %s, found %s"
                % (path, command, option, expected_choices or "<none>", found_choices)
            )

        expected_default = fact.get("default", "")
        found_default = values.get("default")
        if (
            expected_choices
            and expected_default
            and expected_default != "Sentinel.UNSET"
        ):
            if found_default is None:
                errors.append(
                    "%s missing cli-ref-option default for command=%s option=%s"
                    % (path, command, option)
                )
            elif expected_default != found_default:
                errors.append(
                    "%s has stale cli-ref-option default for command=%s option=%s: "
                    "expected %s, found %s"
                    % (path, command, option, expected_default, found_default)
                )
        elif found_default is not None and expected_default != found_default:
            errors.append(
                "%s has stale cli-ref-option default for command=%s option=%s: "
                "expected %s, found %s"
                % (path, command, option, expected_default or "<none>", found_default)
            )

    found_boundaries = _boundary_markers(markers)
    for command, required in sorted(_REQUIRED_BOUNDARIES.items()):
        missing = required - found_boundaries.get(command, set())
        if missing:
            errors.append(
                "%s missing cli-ref-boundary command=%s tokens=%s"
                % (path, command, ",".join(sorted(missing)))
            )
    return errors


def check() -> None:
    """Run all CLI reference marker checks."""
    errors: List[str] = []
    command_facts = _command_option_facts()
    for path in _LANG_FILES.values():
        errors.extend(_check_one(path, command_facts))
    if errors:
        raise CheckFailure(
            "CLI reference documentation is out of sync:\n" + "\n".join(errors)
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run marker checks and print a short success message.",
    )
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("Only --check mode is supported.")
    try:
        check()
    except CheckFailure as err:
        # CheckFailure: one or more documentation markers are stale or missing.
        print(str(err), file=sys.stderr)
        return 1
    print("CLI reference documentation markers are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
