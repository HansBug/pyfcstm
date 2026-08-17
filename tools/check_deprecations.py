#!/usr/bin/env python3
"""Audit versioned deprecations in production YAML and Python code.

The runtime deprecation behavior for Python callables is supplied by the
``deprecation`` package.  This command supplies the repository-level inventory
that the package intentionally does not provide: it checks structured YAML
metadata and ``@deprecation.deprecated`` decorators against the current
project version.

The command reports three states:

``scheduled``
    The deprecation starts in a future release.
``ACTION``
    The current release is inside the deprecation window.  Review migration
    documentation and the replacement before the next release.
``OVERDUE``
    The current release has reached ``removed_in``.  The command fails until
    the deprecated surface is removed or its metadata is deliberately moved.

Malformed metadata always fails.  ``make deprecation_check`` is intentionally
small enough to run in a normal source checkout and does not inspect tests,
generated parser files, or third-party source trees.  The default Python
roots include both the package and the top-level CLI shim, so a deprecation in
non-``inspect`` production code is still part of the audit.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml
from packaging.version import InvalidVersion, Version


_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ROOTS = (
    _REPO_ROOT / "pyfcstm",
    _REPO_ROOT / "pyfcstm_cli.py",
    _REPO_ROOT / "templates",
    _REPO_ROOT / "setup.py",
)
_DEPRECATION_KEYS = frozenset(
    ("deprecated_in", "removed_in", "deprecated_since")
)
_ACTION_KEYS = frozenset(
    ("alias_of", "replaced_by", "replacement", "action", "details")
)
_GENERATED_PYTHON_PARTS = frozenset(
    ("pyfcstm/dsl/grammar", "pyfcstm/bmc/grammar")
)


@dataclass
class Finding:
    """One auditable deprecation declaration or metadata problem."""

    path: str
    line: int
    kind: str
    name: str
    deprecated_in: Optional[str] = None
    removed_in: Optional[str] = None
    action: Optional[str] = None
    status: str = "ERROR"
    issues: List[str] = field(default_factory=list)

    @property
    def is_error(self) -> bool:
        """Return whether this finding should make the audit fail."""
        return bool(self.issues) or self.status == "OVERDUE"


def _parse_version(value: Any, *, field_name: str, finding: Finding) -> Optional[Version]:
    """Parse one version value and record a precise metadata error."""
    if not isinstance(value, str) or not value.strip():
        finding.issues.append("{} must be a non-empty version string".format(field_name))
        return None
    try:
        return Version(value.strip())
    except InvalidVersion:
        # InvalidVersion is raised by packaging.version for malformed PEP 440
        # values; other exceptions indicate a bug and must propagate.
        finding.issues.append("{}={!r} is not a valid PEP 440 version".format(field_name, value))
        return None


def _finalize_finding(
        finding: Finding,
        current_version: Version,
        metadata: Mapping[str, Any],
) -> Finding:
    """Validate shared metadata and assign its current-release status."""
    if "deprecated_since" in metadata:
        finding.issues.append(
            "deprecated_since is obsolete; use deprecated_in"
        )

    deprecated = _parse_version(
        metadata.get("deprecated_in"),
        field_name="deprecated_in",
        finding=finding,
    )
    removed_value = metadata.get("removed_in")
    removed = None
    if removed_value is not None:
        removed = _parse_version(
            removed_value,
            field_name="removed_in",
            finding=finding,
        )
    if removed is not None and deprecated is None:
        finding.issues.append("removed_in requires deprecated_in")
    if removed is not None and deprecated is not None and removed < deprecated:
        finding.issues.append("removed_in must not precede deprecated_in")

    action_keys = _ACTION_KEYS.intersection(metadata)
    for action_key in sorted(action_keys):
        action_value = metadata[action_key]
        valid = isinstance(action_value, str) and bool(action_value.strip())
        if not valid:
            finding.issues.append(
                "{} must be a non-empty action description or target".format(action_key)
            )
    has_action = bool(action_keys) or removed is not None
    if not has_action:
        finding.issues.append(
            "deprecation must declare a replacement/action or removed_in"
        )

    if deprecated is None:
        finding.status = "ERROR"
    elif removed is not None and current_version >= removed:
        finding.status = "OVERDUE"
    elif current_version >= deprecated:
        finding.status = "ACTION"
    else:
        finding.status = "scheduled"
    finding.deprecated_in = metadata.get("deprecated_in")
    finding.removed_in = removed_value
    for action_key in ("replaced_by", "replacement", "alias_of", "action", "details"):
        action_value = metadata.get(action_key)
        if isinstance(action_value, str) and action_value.strip():
            finding.action = action_value.strip()
            break
    return finding


def _scalar_value(node: yaml.nodes.Node) -> Any:
    """Return a YAML scalar value without evaluating arbitrary Python."""
    if isinstance(node, yaml.nodes.ScalarNode):
        if node.tag == "tag:yaml.org,2002:null":
            return None
        return node.value
    return None


def _yaml_mappings(
        node: yaml.nodes.Node,
        path: Tuple[str, ...] = (),
) -> Iterable[Tuple[Tuple[str, ...], int, Mapping[str, Any]]]:
    """Yield every YAML mapping together with its source path and line."""
    if isinstance(node, yaml.nodes.MappingNode):
        values: Dict[str, Any] = {}
        children: List[Tuple[str, yaml.nodes.Node]] = []
        for key_node, value_node in node.value:
            key = _scalar_value(key_node)
            if not isinstance(key, str):
                continue
            values[key] = _scalar_value(value_node)
            children.append((key, value_node))
        yield path, node.start_mark.line + 1, values
        for key, child in children:
            yield from _yaml_mappings(child, path + (key,))
    elif isinstance(node, yaml.nodes.SequenceNode):
        for index, child in enumerate(node.value):
            yield from _yaml_mappings(child, path + (str(index),))


def audit_yaml_file(path: Path, current_version: Version) -> List[Finding]:
    """Audit deprecation mappings in one YAML file."""
    text = path.read_text(encoding="utf-8")
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as err:
        # A malformed config cannot be audited and is itself a maintenance
        # failure; YAML parser errors are the expected failure class here.
        return [Finding(
            path=str(path),
            line=getattr(getattr(err, "problem_mark", None), "line", 0) + 1,
            kind="yaml",
            name="<document>",
            issues=["invalid YAML: {}".format(err)],
        )]
    if root is None:
        return []

    findings: List[Finding] = []
    for location, line, values in _yaml_mappings(root):
        if not _DEPRECATION_KEYS.intersection(values):
            continue
        name = ".".join(location) or "<document>"
        finding = Finding(str(path), line, "yaml", name)
        findings.append(_finalize_finding(finding, current_version, values))
    return findings


def _qualified_name(node: ast.AST) -> Optional[str]:
    """Return a dotted name for a simple decorator expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return "{}.{}".format(parent, node.attr) if parent else node.attr
    return None


def _literal_or_issue(
        node: ast.AST,
        field_name: str,
        finding: Finding,
        *,
        allow_dynamic: bool = False,
) -> Any:
    """Read a literal decorator argument and report dynamic values."""
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        # Schedule and details metadata must be statically auditable; the
        # decorator's optional current_version is intentionally supplied by
        # the command, so a dynamic project-version expression is acceptable.
        if allow_dynamic:
            return None
        finding.issues.append("{} must be a literal value".format(field_name))
        return None


def _import_aliases(tree: ast.AST) -> Tuple[set, set]:
    """Collect local names imported from the ``deprecation`` package."""
    decorator_names = set()
    module_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "deprecation":
                    module_names.add(item.asname or item.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "deprecation":
            for item in node.names:
                if item.name == "deprecated":
                    decorator_names.add(item.asname or item.name)
    return decorator_names, module_names


def _deprecation_decorator_info(
        decorator: ast.AST,
        decorator_names: set,
        module_names: set,
        function_name: str,
) -> Optional[Tuple[Mapping[str, Any], Finding]]:
    """Extract metadata from one recognized deprecation decorator."""
    call = decorator if isinstance(decorator, ast.Call) else None
    target = call.func if call is not None else decorator
    qualified = _qualified_name(target)
    if qualified is None:
        return None
    recognized = (
        qualified in decorator_names
        or (
            qualified.rsplit(".", 1)[-1] == "deprecated"
            and qualified.rsplit(".", 1)[0] in module_names
        )
    )
    if not recognized:
        return None

    finding = Finding(
        path="",
        line=getattr(decorator, "lineno", 1),
        kind="python",
        name=function_name,
    )
    metadata: Dict[str, Any] = {}
    if call is None:
        finding.issues.append(
            "deprecation decorator must be called with version metadata"
        )
        return metadata, finding
    positional_names = ("deprecated_in", "removed_in", "current_version", "details")
    if len(call.args) > len(positional_names):
        finding.issues.append("deprecation decorator has too many positional arguments")
    for name, argument in zip(positional_names, call.args):
        metadata[name] = _literal_or_issue(
            argument,
            name,
            finding,
            allow_dynamic=name == "current_version",
        )
    for keyword in call.keywords:
        if keyword.arg is None:
            finding.issues.append("**kwargs are not statically auditable")
            continue
        if keyword.arg not in positional_names:
            finding.issues.append(
                "unsupported deprecation argument {!r}".format(keyword.arg)
            )
            continue
        if keyword.arg in metadata:
            finding.issues.append("duplicate deprecation argument {!r}".format(keyword.arg))
            continue
        metadata[keyword.arg] = _literal_or_issue(
            keyword.value,
            keyword.arg,
            finding,
            allow_dynamic=keyword.arg == "current_version",
        )
    return metadata, finding


def audit_python_file(path: Path, current_version: Version) -> List[Finding]:
    """Audit deprecation decorators in one Python file."""
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as err:
        # SyntaxError is the expected parser failure for a source file that
        # cannot be inspected; all other exceptions should surface.
        return [Finding(
            path=str(path),
            line=err.lineno or 1,
            kind="python",
            name="<module>",
            issues=["invalid Python: {}".format(err.msg)],
        )]

    decorator_names, module_names = _import_aliases(tree)
    findings: List[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for decorator in node.decorator_list:
            info = _deprecation_decorator_info(
                decorator, decorator_names, module_names, node.name
            )
            if info is None:
                continue
            metadata, finding = info
            finding.path = str(path)
            findings.append(_finalize_finding(finding, current_version, metadata))
    return findings


def audit_diagnostic_registry(path: Path) -> List[Finding]:
    """Run the canonical diagnostic-registry validator when present.

    The deprecation scan owns version/action reporting, while ``load_codes``
    owns alias target, severity-prefix, and registry-shape validation. Keeping
    both checks on the same maintenance command prevents a deprecated alias
    from pointing at a removed or malformed code entry.
    """
    from pyfcstm.diagnostics.codes import CodesSchemaError, load_codes
    try:
        load_codes(str(path))
    except CodesSchemaError as err:
        # Registry schema failures are expected maintenance findings; parser
        # and dependency failures outside this contract must propagate.
        return [Finding(
            path=str(path),
            line=1,
            kind="yaml",
            name="<diagnostic-registry>",
            issues=[str(err)],
        )]
    except (OSError, UnicodeError, yaml.YAMLError) as err:
        # These are the expected file/encoding/YAML failures while validating
        # the registry source; all other exceptions remain visible to CI.
        return [Finding(
            path=str(path),
            line=1,
            kind="yaml",
            name="<diagnostic-registry>",
            issues=["unable to validate diagnostic registry: {}".format(err)],
        )]
    return []


def _iter_source_files(root: Path, suffixes: Sequence[str]) -> Iterable[Path]:
    """Yield source files below a root in stable order."""
    if root.is_file():
        if root.suffix in suffixes:
            yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        try:
            relative = path.relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            relative = path.as_posix()
        if any(relative.startswith(prefix + "/") for prefix in _GENERATED_PYTHON_PARTS):
            continue
        yield path


def audit_paths(
        roots: Sequence[Path],
        current_version: Version,
) -> List[Finding]:
    """Audit Python and YAML files below the supplied production roots."""
    findings: List[Finding] = []
    seen: set = set()
    for root in roots:
        if not root.exists():
            findings.append(Finding(
                path=str(root),
                line=1,
                kind="root",
                name=str(root),
                issues=["source root does not exist"],
            ))
            continue
        for path in _iter_source_files(root, (".py", ".yaml", ".yml")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.suffix == ".py":
                findings.extend(audit_python_file(path, current_version))
            else:
                findings.extend(audit_yaml_file(path, current_version))
                if path.name == "codes.yaml" and path.parent.name == "diagnostics":
                    findings.extend(audit_diagnostic_registry(path))
    return findings


def _finding_dict(finding: Finding) -> Dict[str, Any]:
    """Serialize a finding for the optional JSON output."""
    return {
        "path": _display_path(finding.path),
        "line": finding.line,
        "kind": finding.kind,
        "name": finding.name,
        "deprecated_in": finding.deprecated_in,
        "removed_in": finding.removed_in,
        "action": finding.action,
        "status": finding.status,
        "issues": list(finding.issues),
    }


def _display_path(path: str) -> str:
    """Prefer repository-relative paths in human-readable output."""
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path


def run_check(
        *,
        current_version: str,
        roots: Sequence[Path],
        json_output: bool = False,
) -> int:
    """Run the audit and return a process-style status code."""
    try:
        parsed_current = Version(current_version)
    except InvalidVersion:
        print("invalid current project version: {!r}".format(current_version), file=sys.stderr)
        return 2

    findings = audit_paths(roots, parsed_current)
    if json_output:
        print(json.dumps({
            "current_version": str(parsed_current),
            "findings": [_finding_dict(item) for item in findings],
        }, indent=2, sort_keys=True))
    else:
        print("deprecation audit: current version {}".format(parsed_current))
        if not findings:
            print("deprecation audit: no versioned deprecations found")
        for finding in findings:
            prefix = "{}:{} {} {}".format(
                _display_path(finding.path), finding.line, finding.status, finding.name
            )
            versions = "deprecated_in={!r}".format(finding.deprecated_in)
            if finding.removed_in is not None:
                versions += " removed_in={!r}".format(finding.removed_in)
            if finding.action is not None:
                versions += " action={!r}".format(finding.action)
            print("{} ({}, {})".format(prefix, finding.kind, versions))
            for issue in finding.issues:
                print("  ERROR: {}".format(issue))
        action_count = sum(item.status == "ACTION" for item in findings)
        overdue_count = sum(item.status == "OVERDUE" for item in findings)
        if action_count:
            print("deprecation audit: {} ACTION item(s) require review".format(action_count))
        if overdue_count:
            print("deprecation audit: {} OVERDUE item(s) require removal".format(overdue_count))

    return 1 if any(item.is_error for item in findings) else 0


def _self_check() -> None:
    """Exercise positive and adversarial metadata/decorator fixtures."""
    current = Version("0.6.0")

    with tempfile.TemporaryDirectory(prefix="pyfcstm-deprecation-") as directory:
        root = Path(directory)
        yaml_path = root / "config.yaml"
        yaml_path.write_text(textwrap.dedent("""
            old_setting:
              deprecated_in: '0.5.0'
              removed_in: '1.0.0'
              replacement: new_setting
        """), encoding="utf-8")
        active = audit_yaml_file(yaml_path, current)[0]
        assert active.status == "ACTION" and not active.is_error
        assert active.action == "new_setting"
        overdue = audit_yaml_file(yaml_path, Version("1.0.0"))[0]
        assert overdue.status == "OVERDUE" and overdue.is_error

        malformed_path = root / "malformed.yaml"
        malformed_path.write_text(textwrap.dedent("""
            old_setting:
              deprecated_in: '0.5.0'
              replacement: null
        """), encoding="utf-8")
        malformed = audit_yaml_file(malformed_path, current)[0]
        assert malformed.is_error

        python_path = root / "legacy.py"
        python_path.write_text(textwrap.dedent("""
            from deprecation import deprecated

            @deprecated(
                deprecated_in='0.5.0',
                removed_in='1.0.0',
                current_version=__version__,
                details='Use new_api.',
            )
            def old_api():
                return None
        """), encoding="utf-8")
        python_finding = audit_python_file(python_path, current)[0]
        assert python_finding.status == "ACTION"
        assert python_finding.action == "Use new_api."
        assert not python_finding.issues

        unrelated_path = root / "unrelated.py"
        unrelated_path.write_text(textwrap.dedent("""
            def deprecated(value):
                return value

            @deprecated('local marker')
            def helper():
                return None
        """), encoding="utf-8")
        assert audit_python_file(unrelated_path, current) == []

        missing_root = audit_paths([root / "missing"], current)
        assert len(missing_root) == 1 and missing_root[0].is_error


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse command-line arguments and run the repository audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the audit (present for consistency with repository checks).",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Exercise built-in positive and adversarial fixtures before auditing.",
    )
    parser.add_argument(
        "--current-version",
        default=None,
        help="Override the project version used for comparison.",
    )
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        default=None,
        help=(
            "Production source root to scan; may be repeated "
            "(default: pyfcstm, pyfcstm_cli.py, templates, and setup.py)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit machine-readable JSON instead of human-readable lines.",
    )
    args = parser.parse_args(argv)

    if args.current_version is None:
        from pyfcstm.config.meta import __VERSION__

        current_version = __VERSION__
    else:
        current_version = args.current_version
    roots = args.root or list(_DEFAULT_ROOTS)
    if args.self_check:
        _self_check()
        print(
            "deprecation checker self-check passed",
            file=sys.stderr if args.json_output else sys.stdout,
        )
    return run_check(
        current_version=current_version,
        roots=roots,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
