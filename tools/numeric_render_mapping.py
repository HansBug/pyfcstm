"""
Build render-mapping snapshots for numeric semantics research.

This module inspects the repository's production expression renderer,
statement renderer, built-in template source directories, and packaged template
metadata. The resulting JSON snapshot is the baseline input for the numeric
render-semantics research line: probe runners should consume this mapping
instead of hand-copying assumptions about how FCSTM expressions are rendered.

The module contains:

* :func:`build_render_mapping` - Collect the in-memory mapping dictionary.
* :func:`write_render_mapping` - Write a stable JSON snapshot to disk.
* :func:`check_render_mapping` - Validate the research mapping contract.
* :func:`main` - Command-line entry point used by maintainers and CI.

Example::

    >>> from tools.numeric_render_mapping import build_render_mapping
    >>> mapping = build_render_mapping('.')
    >>> mapping['schema_version']
    1
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

import yaml

_REPO_ROOT_FOR_SCRIPT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT_FOR_SCRIPT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_SCRIPT))

_JSON_OBJECT = Dict[str, Any]
_RESEARCH_PATH = "research/numeric-render-semantics"
_TOOL_PATH = "tools/numeric_render_mapping.py"
_SNAPSHOT_PATH = "%s/results/snapshots/render_mapping.json" % _RESEARCH_PATH


def _builtin_expr_styles() -> Mapping[str, Mapping[str, Any]]:
    """
    Return built-in expression renderer styles.

    The import is intentionally lazy so this script remains directly
    executable from ``tools/`` while still allowing normal module imports.

    :return: Built-in expression style mapping.
    :rtype: Mapping[str, Mapping[str, Any]]

    Example::

        >>> 'python' in _builtin_expr_styles()
        True
    """
    from pyfcstm.render.expr import _KNOWN_STYLES

    return _KNOWN_STYLES


def _builtin_expr_aliases() -> Mapping[str, str]:
    """
    Return built-in expression style aliases.

    :return: Alias mapping.
    :rtype: Mapping[str, str]

    Example::

        >>> _builtin_expr_aliases()['py']
        'python'
    """
    from pyfcstm.render.expr import _STYLE_ALIASES

    return _STYLE_ALIASES


def _builtin_stmt_styles() -> Mapping[str, Mapping[str, Any]]:
    """
    Return built-in statement renderer styles.

    :return: Built-in statement style mapping.
    :rtype: Mapping[str, Mapping[str, Any]]

    Example::

        >>> _builtin_stmt_styles()['c']['base_lang']
        'c'
    """
    from pyfcstm.render.statement import _KNOWN_STMT_STYLES

    return _KNOWN_STMT_STYLES


def _builtin_stmt_aliases() -> Mapping[str, str]:
    """
    Return built-in statement style aliases.

    :return: Alias mapping.
    :rtype: Mapping[str, str]

    Example::

        >>> _builtin_stmt_aliases()['c++']
        'cpp'
    """
    from pyfcstm.render.statement import _STMT_STYLE_ALIASES

    return _STMT_STYLE_ALIASES


class MappingBuildError(RuntimeError):
    """
    Report an invalid repository layout during mapping construction.

    :param message: Human-readable failure reason.
    :type message: str

    Example::

        >>> raise MappingBuildError('missing templates directory')
        Traceback (most recent call last):
        ...
        tools.numeric_render_mapping.MappingBuildError: missing templates directory
    """


def _as_repo_path(repo_root: Union[str, Path]) -> Path:
    """
    Normalize a repository root path.

    :param repo_root: Repository root path supplied by a caller or CLI.
    :type repo_root: Union[str, pathlib.Path]
    :return: Absolute repository root path.
    :rtype: pathlib.Path

    Example::

        >>> _as_repo_path('.').is_absolute()
        True
    """
    return Path(repo_root).resolve()


def _relpath(path: Path, repo_root: Path) -> str:
    """
    Return a POSIX-style path relative to the repository root.

    :param path: File or directory path.
    :type path: pathlib.Path
    :param repo_root: Absolute repository root path.
    :type repo_root: pathlib.Path
    :return: POSIX relative path.
    :rtype: str

    Example::

        >>> root = Path('/tmp/example')
        >>> _relpath(root / 'a' / 'b.txt', root)
        'a/b.txt'
    """
    return path.resolve().relative_to(repo_root).as_posix()


def _sha256_bytes(payload: bytes) -> str:
    """
    Return a SHA-256 digest for bytes.

    :param payload: Bytes to hash.
    :type payload: bytes
    :return: Hex-encoded SHA-256 digest.
    :rtype: str

    Example::

        >>> _sha256_bytes(b'fcstm')[:8]
        '9d550fa8'
    """
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    """
    Return a SHA-256 digest for one file.

    :param path: File path.
    :type path: pathlib.Path
    :return: Hex-encoded SHA-256 digest.
    :rtype: str

    Example::

        >>> digest = _sha256_file(Path('pyfcstm/template/index.json'))
        >>> len(digest)
        64
    """
    return _sha256_bytes(path.read_bytes())


def _iter_source_files(root: Path) -> Iterable[Path]:
    """
    Yield source files under a directory in deterministic order.

    :param root: Directory to walk.
    :type root: pathlib.Path
    :return: Iterator of file paths.
    :rtype: Iterable[pathlib.Path]

    Example::

        >>> any(path.name == 'config.yaml' for path in _iter_source_files(Path('templates/python')))
        True
    """
    for current_root, dirs, files in os.walk(str(root)):
        dirs[:] = sorted(item for item in dirs if item != "__pycache__")
        for file_name in sorted(files):
            yield Path(current_root) / file_name


def _tree_digest(root: Path) -> _JSON_OBJECT:
    """
    Build a stable digest for a directory tree.

    Symlink targets are included as metadata and the resolved file payload is
    included when the symlink points to a regular file. This keeps C++ wrapper
    templates honest: their checked-in symlinks and reused C template payloads
    are both represented.

    :param root: Directory to hash.
    :type root: pathlib.Path
    :return: Digest metadata with a file count and SHA-256 digest.
    :rtype: Dict[str, Any]

    Example::

        >>> digest = _tree_digest(Path('templates/python'))
        >>> digest['file_count'] > 0
        True
    """
    hasher = hashlib.sha256()
    file_count = 0
    for file_path in _iter_source_files(root):
        rel_file = file_path.relative_to(root).as_posix()
        hasher.update(rel_file.encode("utf-8"))
        hasher.update(b"\0")
        if file_path.is_symlink():
            link_target = os.readlink(str(file_path)).replace(os.sep, "/")
            hasher.update(b"symlink\0")
            hasher.update(link_target.encode("utf-8"))
            hasher.update(b"\0")
        else:
            hasher.update(b"file\0")
        hasher.update(file_path.read_bytes())
        hasher.update(b"\0")
        file_count += 1
    return {"sha256": hasher.hexdigest(), "file_count": file_count}


def _canonical_json(data: _JSON_OBJECT) -> bytes:
    """
    Serialize JSON data for stable digesting.

    :param data: JSON-compatible object.
    :type data: Dict[str, Any]
    :return: Canonical UTF-8 JSON bytes.
    :rtype: bytes

    Example::

        >>> _canonical_json({'b': 1, 'a': 2}).decode('utf-8')
        '{"a":2,"b":1}'
    """
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _copy_mapping(mapping: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Deep-copy a renderer mapping into JSON-compatible data.

    :param mapping: Renderer style mapping.
    :type mapping: Mapping[str, Any]
    :return: JSON-compatible copy.
    :rtype: Dict[str, Any]

    Example::

        >>> copied = _copy_mapping({'x': {'y': 1}})
        >>> copied == {'x': {'y': 1}}
        True
    """
    return copy.deepcopy(dict(mapping))


def _load_yaml_mapping(config_path: Path) -> _JSON_OBJECT:
    """
    Load a YAML file whose root must be a mapping.

    :param config_path: YAML file path.
    :type config_path: pathlib.Path
    :return: YAML root mapping.
    :rtype: Dict[str, Any]
    :raises MappingBuildError: If the YAML root is not a mapping.
    :raises yaml.YAMLError: If the YAML parser rejects the file.

    Example::

        >>> config = _load_yaml_mapping(Path('templates/python/config.yaml'))
        >>> 'expr_styles' in config
        True
    """
    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise MappingBuildError("YAML root in %s must be a mapping." % config_path)
    return loaded


def _split_style(style_config: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Split a renderer style into base language and overrides.

    :param style_config: Style configuration from a template ``config.yaml``.
    :type style_config: Mapping[str, Any]
    :return: Split style representation.
    :rtype: Dict[str, Any]

    Example::

        >>> _split_style({'base_lang': 'python', 'Name': 'x'})
        {'base_lang': 'python', 'overrides': {'Name': 'x'}}
    """
    base_lang = style_config.get("base_lang")
    overrides = {
        key: copy.deepcopy(value)
        for key, value in sorted(style_config.items())
        if key != "base_lang"
    }
    return {"base_lang": base_lang, "overrides": overrides}


def _split_stmt_style(style_config: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Split a statement style into base fields and expression overrides.

    :param style_config: Statement style configuration from ``config.yaml``.
    :type style_config: Mapping[str, Any]
    :return: Split statement style representation.
    :rtype: Dict[str, Any]

    Example::

        >>> style = _split_stmt_style({'base_lang': 'python', 'expr_templates': {'Name': 'x'}})
        >>> style['expr_templates']
        {'Name': 'x'}
    """
    result = _split_style(style_config)
    overrides = result["overrides"]
    expr_templates = copy.deepcopy(overrides.pop("expr_templates", {}) or {})
    result["stmt_overrides"] = overrides
    result["expr_templates"] = expr_templates
    return result


def _classify_template_files(
    template_dir: Path, repo_root: Path
) -> Tuple[List[str], List[str]]:
    """
    Return all template files and generated-artifact template files.

    :param template_dir: One built-in template source directory.
    :type template_dir: pathlib.Path
    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: Tuple of all files and generated artifact templates.
    :rtype: Tuple[List[str], List[str]]

    Example::

        >>> files, artifacts = _classify_template_files(Path('templates/python'), Path('.').resolve())
        >>> 'config.yaml' in files and any(item.endswith('.j2') for item in artifacts)
        True
    """
    files = []
    generated_artifacts = []
    for file_path in _iter_source_files(template_dir):
        rel_from_template = file_path.relative_to(template_dir).as_posix()
        files.append(rel_from_template)
        if file_path.suffix == ".j2" and not rel_from_template.startswith("README"):
            generated_artifacts.append(_relpath(file_path, repo_root))
    return sorted(files), sorted(generated_artifacts)


def _collect_template_config(template_dir: Path, repo_root: Path) -> _JSON_OBJECT:
    """
    Collect mapping metadata for one repository-source built-in template.

    :param template_dir: Template source directory.
    :type template_dir: pathlib.Path
    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: Template mapping metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> info = _collect_template_config(Path('templates/python'), Path('.').resolve())
        >>> info['expr_styles']['python_expr']['base_lang']
        'python'
    """
    config_path = template_dir / "config.yaml"
    if not config_path.exists():
        raise MappingBuildError("Missing template config: %s" % config_path)
    config = _load_yaml_mapping(config_path)
    files, generated_artifacts = _classify_template_files(template_dir, repo_root)
    expr_styles = {
        key: _split_style(value)
        for key, value in sorted((config.get("expr_styles") or {}).items())
    }
    stmt_styles = {
        key: _split_stmt_style(value)
        for key, value in sorted((config.get("stmt_styles") or {}).items())
    }
    return {
        "name": template_dir.name,
        "path": _relpath(template_dir, repo_root),
        "config_path": _relpath(config_path, repo_root),
        "source_digest": _tree_digest(template_dir),
        "files": files,
        "expr_styles": expr_styles,
        "stmt_styles": stmt_styles,
        "generated_artifacts": generated_artifacts,
        "ignored_static_files": sorted(config.get("ignores") or []),
    }


def _collect_templates(repo_root: Path) -> _JSON_OBJECT:
    """
    Collect repository-source built-in template metadata.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: Mapping keyed by template name.
    :rtype: Dict[str, Any]

    Example::

        >>> templates = _collect_templates(Path('.').resolve())
        >>> 'python' in templates
        True
    """
    templates_root = repo_root / "templates"
    if not templates_root.is_dir():
        raise MappingBuildError("Missing templates directory: %s" % templates_root)
    templates = {}
    for item in sorted(templates_root.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            templates[item.name] = _collect_template_config(item, repo_root)
    return templates


def _packaged_sync_status(
    name: Optional[str], archive_declared: bool, source_exists: bool
) -> str:
    """
    Classify packaged-template availability against repository source.

    :param name: Template name from ``index.json``.
    :type name: Optional[str]
    :param archive_declared: Whether ``index.json`` declares an archive.
    :type archive_declared: bool
    :param source_exists: Whether the repository-source template exists.
    :type source_exists: bool
    :return: Human-readable sync status.
    :rtype: str

    Example::

        >>> _packaged_sync_status('python', True, True)
        'source-and-archive-declared'
    """
    if not name:
        return "missing-template-name"
    if source_exists and archive_declared:
        return "source-and-archive-declared"
    if source_exists and not archive_declared:
        return "source-present-archive-undeclared"
    if archive_declared and not source_exists:
        return "archive-declared-source-missing"
    return "index-entry-without-source-or-archive"


def _collect_packaged_templates(
    repo_root: Path, source_templates: Mapping[str, Any]
) -> _JSON_OBJECT:
    """
    Collect packaged built-in template index and archive metadata.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :param source_templates: Repository-source template metadata keyed by name.
    :type source_templates: Mapping[str, Any]
    :return: Packaged template metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> packaged = _collect_packaged_templates(Path('.').resolve(), _collect_templates(Path('.').resolve()))
        >>> 'entries' in packaged
        True
    """
    template_pkg = repo_root / "pyfcstm" / "template"
    index_path = template_pkg / "index.json"
    if not index_path.exists():
        return {
            "index_path": _relpath(index_path, repo_root),
            "index_exists": False,
            "entries": [],
        }

    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    entries = []
    for entry in sorted(
        index_data.get("templates", []), key=lambda item: item.get("name", "")
    ):
        archive = entry.get("archive")
        archive_path = template_pkg / archive if archive else None
        archive_declared = archive_path is not None
        archive_relpath = (
            _relpath(archive_path, repo_root) if archive_path is not None else None
        )
        name = entry.get("name")
        source_digest = None
        source_exists = name in source_templates
        if source_exists:
            source_digest = source_templates[name]["source_digest"]
        entries.append(
            {
                "name": name,
                "language": entry.get("language"),
                "archive": archive,
                "archive_path": archive_relpath,
                "archive_declared": archive_declared,
                "archive_snapshot_policy": (
                    "archive zip files are gitignored build outputs; the "
                    "committed snapshot records index metadata and source "
                    "digests instead of hashing local archive payloads"
                ),
                "root_dir": entry.get("root_dir"),
                "source_digest": source_digest,
                "source_archive_sync_status": _packaged_sync_status(
                    name,
                    archive_declared,
                    source_exists,
                ),
                "metadata": copy.deepcopy(entry),
            }
        )

    return {
        "index_path": _relpath(index_path, repo_root),
        "index_exists": True,
        "index_sha256": _sha256_file(index_path),
        "entries": entries,
    }


def _collect_builtin_expr_styles() -> _JSON_OBJECT:
    """
    Collect built-in expression renderer styles.

    :return: Built-in expression style metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> styles = _collect_builtin_expr_styles()
        >>> styles['styles']['python']['templates']['UFunc(round)']
        'round({{ node.expr | expr_render }})'
    """
    return {
        "aliases": dict(sorted(_builtin_expr_aliases().items())),
        "styles": {
            name: {"base_lang": name, "templates": _copy_mapping(style)}
            for name, style in sorted(_builtin_expr_styles().items())
        },
    }


def _collect_builtin_stmt_styles() -> _JSON_OBJECT:
    """
    Collect built-in statement renderer styles.

    :return: Built-in statement style metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> styles = _collect_builtin_stmt_styles()
        >>> styles['styles']['c']['base_lang']
        'c'
    """
    return {
        "aliases": dict(sorted(_builtin_stmt_aliases().items())),
        "styles": {
            name: _copy_mapping(style)
            for name, style in sorted(_builtin_stmt_styles().items())
        },
    }


def _collect_renderer_helper_inventory() -> List[_JSON_OBJECT]:
    """
    Return helper functions that affect numeric render/probe semantics.

    :return: Helper inventory entries.
    :rtype: List[Dict[str, Any]]

    Example::

        >>> any(item['name'] == 'go_abs_expr' for item in _collect_renderer_helper_inventory())
        True
    """
    return [
        {
            "name": "py_condition_operand",
            "layer": "builtin expression renderer",
            "module": "pyfcstm.render.expr",
            "purpose": "Parenthesizes Python condition-valued comparison operands.",
        },
        {
            "name": "go_expr_type",
            "layer": "builtin expression renderer",
            "module": "pyfcstm.render.expr",
            "purpose": "Chooses the Go conditional-expression closure return type.",
        },
        {
            "name": "go_abs_expr",
            "layer": "builtin expression renderer",
            "module": "pyfcstm.render.expr",
            "purpose": "Chooses integer or floating Go abs rendering based on inferred DSL type.",
        },
        {
            "name": "python_round_to_z3",
            "layer": "solver helper",
            "module": "pyfcstm.solver.expr",
            "purpose": "Encodes Python half-even single-argument round semantics for Z3.",
        },
        {
            "name": "render_c_action_body",
            "layer": "C runtime template helper",
            "module": "pyfcstm.render.c_runtime",
            "purpose": "Renders fallible generated C action bodies with runtime diagnostics.",
        },
        {
            "name": "render_c_condition_body",
            "layer": "C runtime template helper",
            "module": "pyfcstm.render.c_runtime",
            "purpose": "Renders fallible generated C transition-guard condition bodies.",
        },
        {
            "name": "_sign",
            "layer": "Python generated runtime helper",
            "module": "templates/python/machine.py.j2",
            "purpose": "Implements sign for Python generated runtime expression paths.",
        },
        {
            "name": "_s",
            "layer": "Python generated runtime helper alias",
            "module": "templates/python/machine.py.j2",
            "purpose": "Local alias used by python_runtime statement expr_templates for sign.",
        },
    ]


def _collect_cxx_paths(templates: Mapping[str, Any]) -> _JSON_OBJECT:
    """
    Collect the two distinct C++ render paths used by the mapping snapshot.

    :param templates: Repository-source template metadata keyed by name.
    :type templates: Mapping[str, Any]
    :return: C++ path metadata.
    :rtype: Dict[str, Any]

    Example::

        >>> paths = _collect_cxx_paths(_collect_templates(Path('.').resolve()))
        >>> paths['builtin_cpp_style']['base_lang']
        'cpp'
    """
    return {
        "builtin_cpp_style": {
            "source": "pyfcstm.render.expr._CPP_STYLE",
            "base_lang": "cpp",
            "templates": _copy_mapping(_builtin_expr_styles()["cpp"]),
            "notes": [
                "Standalone renderer path emits std::* expressions such as std::pow.",
            ],
        },
        "template_generated_paths": [
            {
                "template": name,
                "source": info["config_path"],
                "expr_styles": copy.deepcopy(info["expr_styles"]),
                "stmt_styles": copy.deepcopy(info["stmt_styles"]),
                "generated_artifacts": list(info["generated_artifacts"]),
                "notes": [
                    "Current C++ wrapper template path reuses C-style expression configuration via base_lang: c.",
                ],
            }
            for name, info in sorted(templates.items())
            if name in {"cpp", "cpp_poll"}
        ],
    }


def _runtime_semantics_notes() -> _JSON_OBJECT:
    """
    Return hand-authored runtime semantic notes for mapping consumers.

    :return: Runtime semantic note mapping.
    :rtype: Dict[str, Any]

    Example::

        >>> _runtime_semantics_notes()['bitwise_not']['operator']
        '~'
    """
    return {
        "bitwise_not": {
            "operator": "~",
            "current_dsl_numeric_unary_rule": "PLUS | MINUS",
            "status": "not inferred from runtime; current parser grammar does not accept numeric unary '~'",
            "reason": (
                "The mapping records '~' explicitly so solver and template work "
                "does not guess from Z3 or C semantics."
            ),
        }
    }


def _attach_mapping_digest(mapping: _JSON_OBJECT) -> _JSON_OBJECT:
    """
    Attach a stable digest to a mapping payload.

    :param mapping: Mapping payload without ``mapping_sha256``.
    :type mapping: Dict[str, Any]
    :return: Mapping payload with ``mapping_sha256``.
    :rtype: Dict[str, Any]

    Example::

        >>> payload = _attach_mapping_digest({'schema_version': 1})
        >>> len(payload['mapping_sha256'])
        64
    """
    payload = copy.deepcopy(mapping)
    payload.pop("mapping_sha256", None)
    payload["mapping_sha256"] = _sha256_bytes(_canonical_json(payload))
    return payload


def _load_snapshot_mapping(repo_root: Path) -> _JSON_OBJECT:
    """
    Load the committed render-mapping snapshot.

    The snapshot is intentionally version-controlled as a small research
    artifact. Loading it during ``--check`` makes drift between the tool and the
    submitted JSON visible without adding files under ``test/``.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: Committed snapshot mapping.
    :rtype: Dict[str, Any]
    :raises MappingBuildError: If the snapshot is missing or is not a JSON object.
    :raises json.JSONDecodeError: If the snapshot is not valid JSON.

    Example::

        >>> snapshot = _load_snapshot_mapping(Path('.').resolve())
        >>> snapshot['schema_version']
        1
    """
    snapshot_path = repo_root / _SNAPSHOT_PATH
    if not snapshot_path.exists():
        raise MappingBuildError("Missing committed snapshot: %s" % snapshot_path)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise MappingBuildError(
            "Committed snapshot must be a JSON object: %s" % snapshot_path
        )
    return snapshot


def _format_json_path(path: Tuple[Union[str, int], ...]) -> str:
    """
    Format a nested JSON path for diagnostics.

    :param path: Nested dictionary keys and list indexes.
    :type path: Tuple[Union[str, int], ...]
    :return: Human-readable JSON path.
    :rtype: str

    Example::

        >>> _format_json_path(('templates', 'python', 'files', 0))
        'templates.python.files[0]'
    """
    result = []
    for item in path:
        if isinstance(item, int):
            if result:
                result[-1] = "%s[%d]" % (result[-1], item)
            else:
                result.append("[%d]" % item)
        else:
            result.append(item)
    return ".".join(result) if result else "<root>"


def _first_json_differences(
    expected: Any, actual: Any, path: Tuple[Union[str, int], ...] = (), limit: int = 5
) -> List[str]:
    """
    Return the first nested differences between two JSON-compatible values.

    :param expected: Expected value.
    :type expected: Any
    :param actual: Actual value.
    :type actual: Any
    :param path: Current nested JSON path, defaults to the root path.
    :type path: Tuple[Union[str, int], ...], optional
    :param limit: Maximum number of diagnostics to return, defaults to ``5``.
    :type limit: int, optional
    :return: Human-readable difference diagnostics.
    :rtype: List[str]

    Example::

        >>> _first_json_differences({'a': [1]}, {'a': [2]})
        ['snapshot mismatch at a[0]: expected 1, got 2']
    """
    if limit <= 0:
        return []
    if type(expected) is not type(actual):
        return [
            "snapshot mismatch at %s: expected %s, got %s"
            % (_format_json_path(path), type(expected).__name__, type(actual).__name__)
        ]
    if isinstance(expected, dict):
        diagnostics = []
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            diagnostics.append(
                "snapshot missing key at %s" % _format_json_path(path + (key,))
            )
            if len(diagnostics) >= limit:
                return diagnostics
        for key in sorted(actual_keys - expected_keys):
            diagnostics.append(
                "snapshot extra key at %s" % _format_json_path(path + (key,))
            )
            if len(diagnostics) >= limit:
                return diagnostics
        for key in sorted(expected_keys & actual_keys):
            diagnostics.extend(
                _first_json_differences(
                    expected[key], actual[key], path + (key,), limit - len(diagnostics)
                )
            )
            if len(diagnostics) >= limit:
                return diagnostics
        return diagnostics
    if isinstance(expected, list):
        diagnostics = []
        if len(expected) != len(actual):
            diagnostics.append(
                "snapshot mismatch at %s: expected list length %d, got %d"
                % (_format_json_path(path), len(expected), len(actual))
            )
            if len(diagnostics) >= limit:
                return diagnostics
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            diagnostics.extend(
                _first_json_differences(
                    expected_item,
                    actual_item,
                    path + (index,),
                    limit - len(diagnostics),
                )
            )
            if len(diagnostics) >= limit:
                return diagnostics
        return diagnostics
    if expected != actual:
        return [
            "snapshot mismatch at %s: expected %r, got %r"
            % (_format_json_path(path), expected, actual)
        ]
    return []


def _validate_snapshot_matches(
    mapping: Mapping[str, Any], repo_root: Path
) -> List[str]:
    """
    Validate that the committed snapshot matches the live mapping.

    :param mapping: Fresh mapping payload built from repository sources.
    :type mapping: Mapping[str, Any]
    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: Snapshot drift diagnostics.
    :rtype: List[str]

    Example::

        >>> result = _validate_snapshot_matches(build_render_mapping('.'), Path('.').resolve())
        >>> result
        []
    """
    snapshot = _load_snapshot_mapping(repo_root)
    return _first_json_differences(dict(mapping), snapshot)


def build_render_mapping(repo_root: Union[str, Path] = ".") -> _JSON_OBJECT:
    """
    Build the numeric render-semantics mapping snapshot.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :return: JSON-compatible mapping snapshot.
    :rtype: Dict[str, Any]
    :raises MappingBuildError: If required repository directories are missing.

    Example::

        >>> mapping = build_render_mapping('.')
        >>> 'python' in mapping['templates']
        True
    """
    root = _as_repo_path(repo_root)
    templates = _collect_templates(root)
    mapping = {
        "schema_version": 1,
        "generated_at_utc": None,
        "generator": {
            "tool": _TOOL_PATH,
            "research_path": _RESEARCH_PATH,
            "provenance": "stable snapshot; repository identity is captured by source and packaged-template digests",
        },
        "repository": {
            "root": ".",
            "template_source_root": "templates",
            "packaged_template_root": "pyfcstm/template",
        },
        "builtin_expr_styles": _collect_builtin_expr_styles(),
        "builtin_stmt_styles": _collect_builtin_stmt_styles(),
        "templates": templates,
        "packaged_templates": _collect_packaged_templates(root, templates),
        "renderer_helper_inventory": _collect_renderer_helper_inventory(),
        "cxx_paths": _collect_cxx_paths(templates),
        "runtime_semantics_notes": _runtime_semantics_notes(),
    }
    return _attach_mapping_digest(mapping)


def _require_mapping_path(
    root: Mapping[str, Any], path: Iterable[Union[str, int]], expected: Any
) -> Optional[str]:
    """
    Validate one nested mapping path.

    :param root: Root mapping to inspect.
    :type root: Mapping[str, Any]
    :param path: Nested keys or indexes to traverse.
    :type path: Iterable[Union[str, int]]
    :param expected: Expected value at the nested path.
    :type expected: Any
    :return: ``None`` when the value matches, otherwise a diagnostic string.
    :rtype: Optional[str]

    Example::

        >>> _require_mapping_path({'a': {'b': 1}}, ['a', 'b'], 1) is None
        True
    """
    current: Any = root
    visited = []
    for item in path:
        visited.append(str(item))
        if isinstance(item, int):
            if not isinstance(current, list) or item >= len(current):
                return "missing mapping path: %s" % ".".join(visited)
            current = current[item]
        else:
            if not isinstance(current, dict) or item not in current:
                return "missing mapping path: %s" % ".".join(visited)
            current = current[item]
    if current != expected:
        return "unexpected value at %s: expected %r, got %r" % (
            ".".join(str(item) for item in path),
            expected,
            current,
        )
    return None


def _validate_render_mapping(mapping: Mapping[str, Any]) -> List[str]:
    """
    Validate the numeric render mapping contract without repository unit tests.

    The research tooling keeps validation close to the tool instead of adding
    files under ``test/``. The checks intentionally cover production renderer
    facts that probe runners depend on: template overrides, C++ dual paths,
    packaged-template digests, helper inventory, and semantic notes.

    :param mapping: Mapping payload returned by :func:`build_render_mapping`.
    :type mapping: Mapping[str, Any]
    :return: Human-readable validation diagnostics.
    :rtype: List[str]

    Example::

        >>> _validate_render_mapping({'schema_version': 1})
        ['missing mapping path: generator.tool', 'missing mapping path: builtin_expr_styles.styles.cpp.templates.UFunc', 'missing mapping path: builtin_expr_styles.styles.c.templates.BinaryOp(**)', 'missing mapping path: builtin_stmt_styles.styles.go.base_lang', 'missing template: python', 'missing template: cpp', 'missing C++ template path: cpp', 'missing C++ template path: cpp_poll', 'packaged template index is missing', 'missing helper inventory entry: go_abs_expr', 'missing helper inventory entry: python_round_to_z3', 'missing helper inventory entry: render_c_action_body', 'missing helper inventory entry: _sign', 'missing mapping path: runtime_semantics_notes.bitwise_not.operator']
    """
    errors = []
    expected_paths = [
        (["generator", "tool"], _TOOL_PATH),
        (
            ["builtin_expr_styles", "styles", "cpp", "templates", "UFunc"],
            "std::{{ node.func }}({{ node.expr | expr_render }})",
        ),
        (
            ["builtin_expr_styles", "styles", "c", "templates", "BinaryOp(**)"],
            "pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})",
        ),
        (["builtin_stmt_styles", "styles", "go", "base_lang"], "go"),
    ]
    for path, expected in expected_paths:
        error = _require_mapping_path(mapping, path, expected)
        if error:
            errors.append(error)

    templates = mapping.get("templates", {})
    if not isinstance(templates, dict):
        errors.append("templates must be a mapping")
        templates = {}

    python_template = templates.get("python")
    if not isinstance(python_template, dict):
        errors.append("missing template: python")
    else:
        python_checks = [
            (
                ["expr_styles", "python_expr", "base_lang"],
                "python",
            ),
            (
                ["expr_styles", "python_expr", "overrides", "UFunc(sign)"],
                "self._sign({{ node.expr | expr_render }})",
            ),
            (
                ["expr_styles", "python_scope_expr", "overrides", "Name"],
                "scope[{{ node.name | tojson }}]",
            ),
            (
                ["stmt_styles", "python_runtime", "expr_templates", "UFunc(sign)"],
                "_s({{ node.expr | expr_render }})",
            ),
        ]
        for path, expected in python_checks:
            error = _require_mapping_path(python_template, path, expected)
            if error:
                errors.append("python template: %s" % error)

    cpp_template = templates.get("cpp")
    if not isinstance(cpp_template, dict):
        errors.append("missing template: cpp")
    else:
        if not cpp_template.get("source_digest", {}).get("sha256"):
            errors.append("cpp template source digest is missing")
        if not cpp_template.get("generated_artifacts"):
            errors.append("cpp template generated artifacts are missing")
        if "config.yaml" not in cpp_template.get("files", []):
            errors.append("cpp template config.yaml is missing from file inventory")

    cxx_paths = mapping.get("cxx_paths", {})
    if isinstance(cxx_paths, dict):
        builtin_cpp = cxx_paths.get("builtin_cpp_style", {})
        if builtin_cpp.get("base_lang") != "cpp":
            errors.append("builtin C++ style base_lang must be cpp")
        pow_template = builtin_cpp.get("templates", {}).get("BinaryOp(**)")
        if not isinstance(pow_template, str) or not pow_template.startswith(
            "std::pow("
        ):
            errors.append("builtin C++ power template must use std::pow")
        template_paths = {
            item.get("template"): item
            for item in cxx_paths.get("template_generated_paths", [])
            if isinstance(item, dict)
        }
        for template_name in ["cpp", "cpp_poll"]:
            template_path = template_paths.get(template_name)
            if not template_path:
                errors.append("missing C++ template path: %s" % template_name)
                continue
            base_lang = (
                template_path.get("expr_styles", {})
                .get("c_scope_expr", {})
                .get("base_lang")
            )
            if base_lang != "c":
                errors.append(
                    "C++ template %s c_scope_expr must inherit C base_lang"
                    % template_name
                )
    else:
        errors.append("cxx_paths must be a mapping")

    packaged = mapping.get("packaged_templates", {})
    packaged_entries = packaged.get("entries") if isinstance(packaged, dict) else None
    allowed_statuses = {
        "source-and-archive-declared",
        "source-present-archive-undeclared",
        "archive-declared-source-missing",
        "index-entry-without-source-or-archive",
        "missing-template-name",
    }
    if not isinstance(packaged_entries, list):
        errors.append("packaged template index is missing")
    else:
        packaged_names = {
            entry.get("name") for entry in packaged_entries if isinstance(entry, dict)
        }
        required_names = {"c", "cpp", "cpp_poll", "python"}
        missing = sorted(required_names - packaged_names)
        if missing:
            errors.append("missing packaged template entries: %s" % ", ".join(missing))
        for entry in packaged_entries:
            if not isinstance(entry, dict):
                errors.append("packaged template entry must be a mapping")
                continue
            if "archive_declared" not in entry:
                errors.append(
                    "packaged template %r missing archive_declared" % entry.get("name")
                )
            if "archive_snapshot_policy" not in entry:
                errors.append(
                    "packaged template %r missing archive_snapshot_policy"
                    % entry.get("name")
                )
            if "source_digest" not in entry:
                errors.append(
                    "packaged template %r missing source_digest" % entry.get("name")
                )
            status = entry.get("source_archive_sync_status")
            if status not in allowed_statuses:
                errors.append(
                    "packaged template %r has invalid sync status %r"
                    % (entry.get("name"), status)
                )

    helpers = mapping.get("renderer_helper_inventory", [])
    helper_names = {item.get("name") for item in helpers if isinstance(item, dict)}
    for required in [
        "go_abs_expr",
        "python_round_to_z3",
        "render_c_action_body",
        "_sign",
    ]:
        if required not in helper_names:
            errors.append("missing helper inventory entry: %s" % required)

    error = _require_mapping_path(
        mapping, ["runtime_semantics_notes", "bitwise_not", "operator"], "~"
    )
    if error:
        errors.append(error)

    return errors


def check_render_mapping(repo_root: Union[str, Path] = ".") -> _JSON_OBJECT:
    """
    Build and validate the numeric render mapping snapshot.

    This self-check entry point validates both the live renderer/template
    contract and the committed snapshot without adding anything under the
    repository ``test/`` tree.

    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :return: Check result with ``ok``, ``errors`` and ``mapping_sha256`` fields.
    :rtype: Dict[str, Any]

    Example::

        >>> result = check_render_mapping('.')
        >>> result['ok']
        True
    """
    root = _as_repo_path(repo_root)
    mapping = build_render_mapping(root)
    errors = _validate_render_mapping(mapping)
    errors.extend(_validate_snapshot_matches(mapping, root))
    return {
        "ok": not errors,
        "errors": errors,
        "mapping_sha256": mapping["mapping_sha256"],
        "schema_version": mapping["schema_version"],
    }


def write_render_mapping(
    output_path: Union[str, Path], repo_root: Union[str, Path] = "."
) -> _JSON_OBJECT:
    """
    Write the render mapping snapshot as stable JSON.

    :param output_path: Destination JSON file path.
    :type output_path: Union[str, pathlib.Path]
    :param repo_root: Repository root path, defaults to the current directory.
    :type repo_root: Union[str, pathlib.Path], optional
    :return: Mapping snapshot that was written.
    :rtype: Dict[str, Any]

    Example::

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     path = Path(tmp) / 'mapping.json'
        ...     mapping = write_render_mapping(path, '.')
        ...     path.exists() and mapping['schema_version'] == 1
        True
    """
    output = Path(output_path)
    mapping = build_render_mapping(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return mapping


def _build_arg_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser

    Example::

        >>> parser = _build_arg_parser()
        >>> parser.prog
        'numeric_render_mapping.py'
    """
    parser = argparse.ArgumentParser(
        prog="numeric_render_mapping.py",
        description="Build a JSON mapping of FCSTM numeric expression render paths.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect, defaults to the current directory.",
    )
    parser.add_argument(
        "--output",
        help="Destination JSON path. When omitted, JSON is printed to stdout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the numeric render mapping contract without using test/.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Run the render-mapping command-line interface.

    :param argv: Optional argument vector excluding the executable name.
    :type argv: Optional[List[str]], optional
    :return: Process exit status.
    :rtype: int

    Example::

        >>> main(['--repo-root', '.', '--output', '/tmp/pyfcstm-render-mapping-example.json'])
        0
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.check:
        result = check_render_mapping(args.repo_root)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    if args.output:
        write_render_mapping(args.output, repo_root=args.repo_root)
    else:
        mapping = build_render_mapping(args.repo_root)
        print(json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
