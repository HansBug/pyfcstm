#!/usr/bin/env python3
"""Check visualization reference documentation markers against code facts.

This tools-only maintenance command checks synchronization markers in
``docs/source/reference/visualization_options/``.  It validates inventory
coverage for PlantUML options, renderer modes, render types, parser value forms,
environment variables, and documented failure boundaries.

Marker grammar
--------------

Markers are Sphinx-safe comment-shaped lines.  Each marker must fit on one
physical line and start with ``.. `` followed by an unregistered marker name::

    .. visualization-ref-field: name=show_events default=None
    .. visualization-ref-preset: name=normal defaults=show_variable_definitions=True,show_pseudo_state_style=True,show_lifecycle_actions=False,show_enter_actions=False,show_during_actions=False,show_exit_actions=False,show_aspect_actions=False,show_abstract_actions=False,show_concrete_actions=False,show_transition_guards=True,show_transition_effects=True,show_events=True
    .. visualization-ref-renderer: name=auto
    .. visualization-ref-boundary: renderer-auto-fallback suffix-mismatch check-mode

Arguments use shell-like ``key=value`` tokens.  Token order does not matter.
Unknown marker groups, missing required keys, malformed tokens, and unknown
optional keys are reported as documentation errors.  Boundary and parser-form
markers carry flag tokens after the required key when a group represents a set.

Preset defaults cover every optional boolean display switch resolved by
``PlantUMLOptions.to_config()``.  Markers prove fact inventory coverage; they do
not replace review of examples, prose depth, or target-language diagrams.
"""

from __future__ import annotations

import argparse
import dataclasses
import shlex
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pyfcstm.entry.cli import pyfcstmcli  # noqa: E402
from pyfcstm.model.plantuml import PlantUMLOptions  # noqa: E402

_LANG_FILES = {
    "en": _REPO_ROOT / "docs/source/reference/visualization_options/index.rst",
    "zh": _REPO_ROOT / "docs/source/reference/visualization_options/index_zh.rst",
}

_MARKER_SCHEMAS = {
    "visualization-ref-field": (frozenset(("name",)), frozenset(("default",))),
    "visualization-ref-preset": (frozenset(("name",)), frozenset(("defaults",))),
    "visualization-ref-renderer": (frozenset(("name",)), frozenset()),
    "visualization-ref-render-type": (frozenset(("name",)), frozenset()),
    "visualization-ref-envvar": (frozenset(("name",)), frozenset()),
    "visualization-ref-parser-form": (frozenset(("group",)), frozenset()),
    "visualization-ref-boundary": (frozenset(("group",)), frozenset()),
}

_VISUALIZE_COMMAND = pyfcstmcli.commands["visualize"]
# Fields whose resolved values vary by detail preset or parent visibility switch;
# static dataclass defaults are covered separately by visualization-ref-field markers.
_PRESET_FIELDS = (
    "show_variable_definitions",
    "show_pseudo_state_style",
    "show_lifecycle_actions",
    "show_enter_actions",
    "show_during_actions",
    "show_exit_actions",
    "show_aspect_actions",
    "show_abstract_actions",
    "show_concrete_actions",
    "show_transition_guards",
    "show_transition_effects",
    "show_events",
)
_EXPECTED_PRESETS = frozenset(("minimal", "normal", "full"))
_EXPECTED_PARSER_FORMS = frozenset(
    (
        "bool",
        "int",
        "float",
        "quoted-string",
        "none",
        "null",
        "tuple",
        "optional",
        "invalid-key",
        "invalid-value",
    )
)
_EXPECTED_ENVVARS = frozenset(
    (
        "PLANTUML_JAR",
        "PLANTUML_HOST",
        "PYFCSTM_NO_GUI",
        "CI",
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "MIR_SOCKET",
        "XDG_CACHE_HOME",
        "LOCALAPPDATA",
    )
)
_EXPECTED_BOUNDARIES = frozenset(
    (
        "renderer-auto-fallback",
        "suffix-mismatch",
        "check-mode",
        "headless-open",
        "strict-open",
        "remote-privacy",
        "cache-output",
        "local-backend-failure",
        "remote-network-failure",
        "backend-success-without-output",
        "source-only-plantuml",
        "rendered-image-visualize",
    )
)


class CheckFailure(Exception):
    """Raised when visualization marker checks find one or more failures."""


def _stable_default(field: dataclasses.Field[object]) -> str:
    if field.default is dataclasses.MISSING:
        return "<missing>"
    value = field.default
    if isinstance(value, tuple):
        return ",".join(str(item) for item in value)
    return str(value)


def _click_choice_options() -> Dict[str, Tuple[str, ...]]:
    result: Dict[str, Tuple[str, ...]] = {}
    for param in _VISUALIZE_COMMAND.params:
        if hasattr(param.type, "choices"):
            result[param.name] = tuple(str(choice) for choice in param.type.choices)
    return result


def _expected_renderers() -> Tuple[str, ...]:
    return _click_choice_options()["renderer"]


def _expected_render_types() -> Tuple[str, ...]:
    return _click_choice_options()["render_type"]


def _expected_preset_defaults() -> Dict[str, str]:
    result: Dict[str, str] = {}
    for level in sorted(_EXPECTED_PRESETS):
        config = PlantUMLOptions(detail_level=level).to_config()
        result[level] = ",".join(
            "%s=%s" % (name, getattr(config, name)) for name in _PRESET_FIELDS
        )
    return result


def _expected_fields() -> Dict[str, str]:
    return {
        name: _stable_default(field)
        for name, field in PlantUMLOptions.__dataclass_fields__.items()
    }


def _read_lines(path: Path) -> List[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as err:
        # OSError: Path.read_text() raises this for missing/unreadable docs;
        # UnicodeDecodeError: it raises this when a docs file is not UTF-8.
        raise CheckFailure("%s cannot be read as UTF-8 text: %s" % (path, err))


def _parse_marker_line(
    path: Path, lineno: int, line: str
) -> Tuple[str, Dict[str, str], Set[str]]:
    content = line[3:].strip()
    group, sep, rest = content.partition(":")
    if not sep:
        raise CheckFailure("%s:%s marker must contain ':' separator." % (path, lineno))
    group = group.strip()
    if group not in _MARKER_SCHEMAS:
        raise CheckFailure(
            "%s:%s unknown visualization marker group %r." % (path, lineno, group)
        )
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
        if line.startswith(".. visualization-ref-"):
            group, values, flags = _parse_marker_line(path, lineno, line)
            markers[group].append((values, flags))
    return markers


def _names(
    markers: Mapping[str, List[Tuple[Dict[str, str], Set[str]]]], group: str
) -> Set[str]:
    return {values["name"] for values, _flags in markers[group]}


def _named_values(
    markers: Mapping[str, List[Tuple[Dict[str, str], Set[str]]]], group: str
) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    duplicates: List[str] = []
    for values, _flags in markers[group]:
        name = values["name"]
        if name in result:
            duplicates.append(name)
        result[name] = values
    if duplicates:
        raise CheckFailure(
            "duplicate %s marker(s): %s" % (group, ", ".join(sorted(duplicates)))
        )
    return result


def _flags(
    markers: Mapping[str, List[Tuple[Dict[str, str], Set[str]]]],
    group: str,
    group_name: str,
) -> Set[str]:
    result: Set[str] = set()
    for values, flags in markers[group]:
        if values["group"] == group_name:
            result.update(flags)
    return result


def _check_missing(
    path: Path, label: str, expected: Iterable[str], found: Iterable[str]
) -> List[str]:
    errors: List[str] = []
    expected_set = set(expected)
    found_set = set(found)
    for value in sorted(expected_set - found_set):
        errors.append("%s missing %s %s" % (path, label, value))
    for value in sorted(found_set - expected_set):
        errors.append("%s has stale %s %s" % (path, label, value))
    return errors


def _check_one(path: Path) -> List[str]:
    errors: List[str] = []
    try:
        markers = _collect_markers(path)
    except CheckFailure as err:
        # CheckFailure: marker parsing detected malformed documentation syntax.
        return [str(err)]

    fields = _expected_fields()
    field_markers = _named_values(markers, "visualization-ref-field")
    errors.extend(
        _check_missing(
            path,
            "visualization-ref-field",
            fields,
            field_markers,
        )
    )
    for name in sorted(set(fields) & set(field_markers)):
        expected_default = fields[name]
        found_default = field_markers[name].get("default")
        if found_default is None:
            errors.append(
                "%s missing visualization-ref-field default for %s" % (path, name)
            )
        elif found_default != expected_default:
            errors.append(
                "%s has stale visualization-ref-field default for %s: expected %s, found %s"
                % (path, name, expected_default, found_default)
            )

    preset_defaults = _expected_preset_defaults()
    preset_markers = _named_values(markers, "visualization-ref-preset")
    errors.extend(
        _check_missing(
            path,
            "visualization-ref-preset",
            preset_defaults,
            preset_markers,
        )
    )
    for name in sorted(set(preset_defaults) & set(preset_markers)):
        expected_defaults = preset_defaults[name]
        found_defaults = preset_markers[name].get("defaults")
        if found_defaults is None:
            errors.append(
                "%s missing visualization-ref-preset defaults for %s" % (path, name)
            )
        elif found_defaults != expected_defaults:
            errors.append(
                "%s has stale visualization-ref-preset defaults for %s: expected %s, found %s"
                % (path, name, expected_defaults, found_defaults)
            )
    errors.extend(
        _check_missing(
            path,
            "visualization-ref-renderer",
            _expected_renderers(),
            _names(markers, "visualization-ref-renderer"),
        )
    )
    errors.extend(
        _check_missing(
            path,
            "visualization-ref-render-type",
            _expected_render_types(),
            _names(markers, "visualization-ref-render-type"),
        )
    )
    errors.extend(
        _check_missing(
            path,
            "visualization-ref-envvar",
            _EXPECTED_ENVVARS,
            _names(markers, "visualization-ref-envvar"),
        )
    )

    parser_forms = _flags(markers, "visualization-ref-parser-form", "value")
    errors.extend(
        _check_missing(
            path, "visualization-ref-parser-form", _EXPECTED_PARSER_FORMS, parser_forms
        )
    )
    boundaries = _flags(markers, "visualization-ref-boundary", "behavior")
    errors.extend(
        _check_missing(
            path, "visualization-ref-boundary", _EXPECTED_BOUNDARIES, boundaries
        )
    )
    return errors


def check() -> None:
    """Run all visualization reference marker checks."""
    errors: List[str] = []
    for path in _LANG_FILES.values():
        errors.extend(_check_one(path))
    if errors:
        raise CheckFailure(
            "Visualization reference documentation is out of sync:\n"
            + "\n".join(errors)
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
    print("Visualization reference documentation markers are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
