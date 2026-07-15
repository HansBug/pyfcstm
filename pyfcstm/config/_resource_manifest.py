"""
Strict resource and build metadata manifests for packaged artifacts.

The build commands write these JSON files next to the package files.  This
module deliberately uses only the Python standard library so a damaged or
partially installed artifact can still report a useful diagnostic without
importing optional runtime dependencies.

The generated files are:

* ``pyfcstm/_resource_manifest.json`` - deterministic first-party resource
  inventory with size and SHA-256 information.
* ``pyfcstm/_build_info.json`` - build identity, artifact kind, environment,
  and the hash of the resource manifest.
"""

import hashlib
import importlib.util
import json
import ntpath
import os
import platform
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from ._build_identity import BuildIdentity, load_build_identity_file
from .meta import __VERSION__


RESOURCE_MANIFEST_FILENAME = "_resource_manifest.json"
BUILD_INFO_JSON_FILENAME = "_build_info.json"
RESOURCE_MANIFEST_SCHEMA = "resource-manifest/v1"
BUILD_INFO_JSON_SCHEMA = "build-info/v1"
ARTIFACT_KINDS = frozenset(
    ("source", "wheel", "sdist", "frozen-onefile", "frozen-onedir")
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _is_safe_relative_path(value: str) -> bool:
    """Reject POSIX, Windows-drive, and traversal paths in JSON metadata."""
    normalized = PurePosixPath(value)
    return not (
        normalized.is_absolute()
        or ntpath.isabs(value)
        or ntpath.splitdrive(value)[0]
        or ".." in normalized.parts
        or "\\" in value
        or normalized.as_posix() != value
    )


class ResourceManifestError(ValueError):
    """Raised when a resource or build manifest cannot satisfy its contract."""


def _atomic_write_json(path: os.PathLike, payload: Mapping[str, object]) -> None:
    """Write JSON deterministically and replace ``path`` atomically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(
        prefix="." + target.name + ".", suffix=".tmp", dir=str(target.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary_path), str(target))
        if os.name != "nt":
            directory_fd = os.open(str(target.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            # ``os.replace`` already consumed the temporary name.
            pass


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one regular file."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, ValueError) as err:
        # OSError: the file disappeared or could not be read; ValueError:
        # an invalid path/stream state was supplied by a platform adapter.
        raise ResourceManifestError(
            "cannot hash resource {!s}: {}: {}".format(
                path, type(err).__name__, err
            )
        ) from err
    return digest.hexdigest()


def _resolve_roots(output_root: os.PathLike) -> Tuple[Path, Path]:
    """Resolve project and package roots from a build output root."""
    root = Path(output_root).absolute()
    package_root = root / "pyfcstm"
    if package_root.is_dir():
        return root, package_root
    if root.name == "pyfcstm" and root.is_dir():
        return root.parent, root
    raise ResourceManifestError(
        "output root {!s} must contain a pyfcstm package directory".format(root)
    )


def _resource_kind(path: str) -> str:
    """Classify a package resource using its stable relative path."""
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in (".json", ".yaml", ".yml"):
        return "data"
    if suffix in (".g4", ".tokens", ".interp"):
        return "grammar"
    if suffix in (".zip", ".tar", ".gz"):
        return "archive"
    if suffix in (".png", ".jpg", ".jpeg", ".svg"):
        return "visual"
    return "other"


def _is_packaged_resource(relative: str, artifact_kind: str) -> bool:
    """Return whether a file belongs to the final artifact closure.

    Wheel and sdist packaging include Python modules plus the explicit
    ``package_data``/``MANIFEST.in`` resource suffixes.  PyInstaller receives
    non-Python package files through ``tools.resources``; Python source files
    are compiled into the PYZ archive and therefore must not be represented as
    required on-disk resources.
    """
    suffix = Path(relative).suffix.lower()
    if artifact_kind in ("frozen-onefile", "frozen-onedir"):
        return suffix != ".py"
    if suffix == ".py":
        return True
    if relative.startswith("pyfcstm/llm/") and suffix in (".md", ".sha256"):
        return True
    if relative.startswith("pyfcstm/diagnostics/") and suffix == ".md":
        return True
    return suffix in (
        ".json",
        ".yaml",
        ".yml",
        ".png",
        ".g4",
        ".tokens",
        ".interp",
        ".zip",
    )


def _iter_resource_paths(
    project_root: Path, package_root: Path, artifact_kind: str
) -> Iterable[Tuple[str, Path]]:
    """Yield final-artifact files in deterministic relative-path order."""
    generated = {RESOURCE_MANIFEST_FILENAME, BUILD_INFO_JSON_FILENAME}
    paths = []
    try:
        iterator = package_root.rglob("*")
        for path in iterator:
            if not path.is_file():
                continue
            if path.is_symlink():
                raise ResourceManifestError(
                    "resource symlink is not reproducible: {!s}".format(path)
                )
            if "__pycache__" in path.parts or path.name in generated:
                continue
            relative = path.relative_to(project_root).as_posix()
            if not _is_packaged_resource(relative, artifact_kind):
                continue
            if not _is_safe_relative_path(relative):
                raise ResourceManifestError(
                    "resource path escapes output root: {!s}".format(relative)
                )
            paths.append((relative, path))
    except (OSError, ValueError) as err:
        # OSError: directory enumeration failed; ValueError: a path was not
        # below the declared project root.
        if isinstance(err, ResourceManifestError):
            raise
        raise ResourceManifestError(
            "cannot enumerate package resources under {!s}: {}: {}".format(
                package_root, type(err).__name__, err
            )
        ) from err
    for relative, path in sorted(paths, key=lambda item: item[0]):
        yield relative, path


def build_resource_manifest(
    output_root: os.PathLike, artifact_kind: str
) -> Dict[str, object]:
    """Build a deterministic first-party resource manifest in memory.

    :param output_root: Project root containing the ``pyfcstm`` package.
    :type output_root: os.PathLike
    :param artifact_kind: Current build kind from :data:`ARTIFACT_KINDS`.
    :type artifact_kind: str
    :return: Validated manifest payload.
    :rtype: dict
    :raises ResourceManifestError: If paths or resources cannot be enumerated.

    Example::

        >>> manifest = build_resource_manifest('.', 'wheel')
        >>> manifest['schema_version']
        'resource-manifest/v1'
    """
    if artifact_kind not in ARTIFACT_KINDS:
        raise ResourceManifestError(
            "unknown artifact kind {!r}; expected one of {}".format(
                artifact_kind, ", ".join(sorted(ARTIFACT_KINDS))
            )
        )
    project_root, package_root = _resolve_roots(output_root)
    resources: List[Dict[str, object]] = []
    for relative, path in _iter_resource_paths(
        project_root, package_root, artifact_kind
    ):
        try:
            size = path.stat().st_size
        except (OSError, ValueError) as err:
            # OSError: resource vanished or metadata is inaccessible; ValueError:
            # invalid path supplied by a platform filesystem adapter.
            raise ResourceManifestError(
                "cannot stat resource {!s}: {}: {}".format(
                    path, type(err).__name__, err
                )
            ) from err
        resources.append(
            {
                "path": relative,
                "size": size,
                "sha256": _sha256(path),
                "kind": _resource_kind(relative),
                "required": True,
                "artifact_kinds": [artifact_kind],
            }
        )
    if not resources:
        raise ResourceManifestError(
            "no package resources found below {!s}".format(package_root)
        )
    return {
        "schema_version": RESOURCE_MANIFEST_SCHEMA,
        "artifact_kind": artifact_kind,
        "root": ".",
        "resources": resources,
    }


def write_resource_manifest(
    output_root: os.PathLike, artifact_kind: str
) -> Tuple[Path, Dict[str, object]]:
    """Build and atomically write ``pyfcstm/_resource_manifest.json``.

    :param output_root: Project root containing the ``pyfcstm`` package.
    :type output_root: os.PathLike
    :param artifact_kind: Package or frozen-artifact kind.
    :type artifact_kind: str
    :return: The written path and its validated payload.
    :rtype: Tuple[pathlib.Path, dict]
    :raises ResourceManifestError: If resources cannot be enumerated or encoded.

    Example::

        >>> path, payload = write_resource_manifest('.', 'source')
        >>> path.name
        '_resource_manifest.json'
    """
    project_root, package_root = _resolve_roots(output_root)
    manifest = build_resource_manifest(project_root, artifact_kind)
    target = package_root / RESOURCE_MANIFEST_FILENAME
    _atomic_write_json(target, manifest)
    return target, manifest


def _manifest_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except (OSError, ValueError) as err:
        # OSError: manifest is absent/unreadable; ValueError: invalid path.
        raise ResourceManifestError(
            "cannot read resource manifest {!s}: {}: {}".format(
                path, type(err).__name__, err
            )
        ) from err


def load_resource_manifest(path: os.PathLike) -> Dict[str, object]:
    """Load and structurally validate a resource manifest without imports.

    :param path: JSON manifest path.
    :type path: os.PathLike
    :return: Parsed and schema-validated manifest payload.
    :rtype: dict
    :raises ResourceManifestError: If the file is unreadable or malformed.

    Example::

        >>> payload = load_resource_manifest('pyfcstm/_resource_manifest.json')
        >>> payload['schema_version']
        'resource-manifest/v1'
    """
    manifest_path = Path(path)
    raw = _manifest_bytes(manifest_path)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as err:
        # UnicodeDecodeError: non-UTF-8 data; JSONDecodeError/TypeError:
        # malformed JSON values.
        raise ResourceManifestError(
            "resource manifest {!s} is invalid JSON: {}: {}".format(
                manifest_path, type(err).__name__, err
            )
        ) from err
    if not isinstance(payload, dict):
        raise ResourceManifestError("resource manifest must be a JSON object")
    if payload.get("schema_version") != RESOURCE_MANIFEST_SCHEMA:
        raise ResourceManifestError("unsupported resource manifest schema")
    artifact_kind = payload.get("artifact_kind")
    if artifact_kind not in ARTIFACT_KINDS:
        raise ResourceManifestError("resource manifest has an invalid artifact_kind")
    resources = payload.get("resources")
    if not isinstance(resources, list) or not resources:
        raise ResourceManifestError("resource manifest resources must be non-empty")
    seen = set()
    for entry in resources:
        if not isinstance(entry, dict):
            raise ResourceManifestError("resource manifest entry must be an object")
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            raise ResourceManifestError("resource manifest entry path must be text")
        if not path_value.startswith("pyfcstm/"):
            raise ResourceManifestError(
                "resource manifest path is not a normalized relative path under the pyfcstm package"
            )
        if not _is_safe_relative_path(path_value):
            raise ResourceManifestError(
                "resource manifest path is not a normalized relative path: {!r}".format(
                    path_value
                )
            )
        if path_value in seen:
            raise ResourceManifestError(
                "resource manifest contains duplicate path {!r}".format(path_value)
            )
        seen.add(path_value)
        size = entry.get("size")
        if type(size) is not int or size < 0:
            raise ResourceManifestError("resource manifest size must be non-negative")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
            raise ResourceManifestError("resource manifest sha256 is invalid")
        if not isinstance(entry.get("kind"), str):
            raise ResourceManifestError("resource manifest kind is required")
        if type(entry.get("required")) is not bool:
            raise ResourceManifestError("resource manifest required must be boolean")
        artifact_kinds = entry.get("artifact_kinds")
        if not isinstance(artifact_kinds, list) or not artifact_kinds:
            raise ResourceManifestError("resource manifest artifact_kinds is required")
        if any(kind not in ARTIFACT_KINDS for kind in artifact_kinds):
            raise ResourceManifestError("resource manifest has an invalid artifact kind")
        if artifact_kind not in artifact_kinds:
            raise ResourceManifestError(
                "resource manifest entry does not apply to artifact kind {!r}".format(
                    artifact_kind
                )
            )
    return payload


def verify_resource_manifest(
    manifest_path: os.PathLike, output_root: os.PathLike
) -> Dict[str, object]:
    """Verify every manifest file exists with its recorded size and digest.

    :param manifest_path: JSON manifest to validate and replay.
    :type manifest_path: os.PathLike
    :param output_root: Root against which manifest-relative paths are resolved.
    :type output_root: os.PathLike
    :return: The validated manifest payload.
    :rtype: dict
    :raises ResourceManifestError: If any entry is missing or mismatched.

    Example::

        >>> verify_resource_manifest('pyfcstm/_resource_manifest.json', '.')
        {'schema_version': 'resource-manifest/v1', ...}
    """
    manifest = load_resource_manifest(manifest_path)
    root = Path(output_root).absolute()
    for entry in manifest["resources"]:  # type: ignore[index]
        relative = entry["path"]  # type: ignore[index]
        path = root.joinpath(*PurePosixPath(relative).parts)
        if not path.is_file() or path.is_symlink():
            raise ResourceManifestError("resource is missing or not regular: {!s}".format(path))
        try:
            actual_size = path.stat().st_size
        except (OSError, ValueError) as err:
            raise ResourceManifestError(
                "cannot stat manifest resource {!s}: {}: {}".format(
                    path, type(err).__name__, err
                )
            ) from err
        if actual_size != entry["size"]:  # type: ignore[index]
            raise ResourceManifestError("resource size mismatch: {!s}".format(path))
        if _sha256(path) != entry["sha256"]:  # type: ignore[index]
            raise ResourceManifestError("resource sha256 mismatch: {!s}".format(path))
    return manifest


def build_build_info(
    identity: BuildIdentity,
    artifact_kind: str,
    manifest_path: os.PathLike,
) -> Dict[str, object]:
    """Create build metadata from one immutable identity snapshot.

    :param identity: Validated identity captured before packaging starts.
    :type identity: BuildIdentity
    :param artifact_kind: Package or frozen-artifact kind.
    :type artifact_kind: str
    :param manifest_path: Manifest whose digest is recorded in the payload.
    :type manifest_path: os.PathLike
    :return: JSON-compatible build metadata.
    :rtype: dict
    :raises ResourceManifestError: If the artifact kind or manifest is invalid.

    Example::

        >>> info = build_build_info(BuildIdentity.unknown(), 'source', 'manifest.json')
        >>> info['artifact_kind']
        'source'
    """
    if artifact_kind not in ARTIFACT_KINDS:
        raise ResourceManifestError("invalid artifact kind {!r}".format(artifact_kind))
    manifest_file = Path(manifest_path)
    manifest_raw = _manifest_bytes(manifest_file)
    values = identity.values()
    payload: Dict[str, object] = {
        "schema_version": BUILD_INFO_JSON_SCHEMA,
        "artifact_kind": artifact_kind,
        "version": __VERSION__,
        "build_time_utc": identity.time_utc,
        "identity": values,
        "resource_manifest": {
            "path": manifest_file.name,
            "sha256": hashlib.sha256(manifest_raw).hexdigest(),
        },
        "environment": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "pyinstaller": {
            "available": importlib.util.find_spec("PyInstaller") is not None,
            "version": None,
        },
    }
    # Keep the generated identity fields available at the top level for
    # consumers that cannot or do not want to traverse nested JSON objects.
    payload.update(values)
    return payload


def write_build_info_json(
    output_root: os.PathLike,
    identity: BuildIdentity,
    artifact_kind: str,
    manifest_path: Optional[os.PathLike] = None,
) -> Tuple[Path, Dict[str, object]]:
    """Atomically write ``pyfcstm/_build_info.json`` beside the manifest.

    :param output_root: Project root containing the package directory.
    :type output_root: os.PathLike
    :param identity: Validated identity captured before packaging starts.
    :type identity: BuildIdentity
    :param artifact_kind: Package or frozen-artifact kind.
    :type artifact_kind: str
    :param manifest_path: Existing manifest path, defaults to the package path.
    :type manifest_path: os.PathLike, optional
    :return: The written path and its payload.
    :rtype: Tuple[pathlib.Path, dict]
    :raises ResourceManifestError: If metadata cannot be generated.

    Example::

        >>> path, _ = write_build_info_json('.', BuildIdentity.unknown(), 'source')
        >>> path.name
        '_build_info.json'
    """
    _, package_root = _resolve_roots(output_root)
    manifest_file = Path(manifest_path) if manifest_path is not None else package_root / RESOURCE_MANIFEST_FILENAME
    payload = build_build_info(identity, artifact_kind, manifest_file)
    target = package_root / BUILD_INFO_JSON_FILENAME
    _atomic_write_json(target, payload)
    return target, payload


def load_build_info_json(path: os.PathLike) -> Dict[str, object]:
    """Load and validate generated JSON build metadata.

    :param path: Generated build metadata path.
    :type path: os.PathLike
    :return: Parsed and schema-validated build metadata.
    :rtype: dict
    :raises ResourceManifestError: If the file is unreadable or inconsistent.

    Example::

        >>> payload = load_build_info_json('pyfcstm/_build_info.json')
        >>> payload['schema_version']
        'build-info/v1'
    """
    build_path = Path(path)
    raw = _manifest_bytes(build_path)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as err:
        raise ResourceManifestError(
            "build info {!s} is invalid JSON: {}: {}".format(
                build_path, type(err).__name__, err
            )
        ) from err
    if not isinstance(payload, dict) or payload.get("schema_version") != BUILD_INFO_JSON_SCHEMA:
        raise ResourceManifestError("unsupported build info JSON schema")
    if payload.get("artifact_kind") not in ARTIFACT_KINDS:
        raise ResourceManifestError("build info has an invalid artifact_kind")
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        raise ResourceManifestError("build info identity must be an object")
    for key, value in identity.items():
        if payload.get(key) != value:
            raise ResourceManifestError("build info identity field {!r} disagrees".format(key))
    resource_manifest = payload.get("resource_manifest")
    if not isinstance(resource_manifest, dict) or not isinstance(resource_manifest.get("sha256"), str):
        raise ResourceManifestError("build info resource manifest hash is missing")
    manifest_name = resource_manifest.get("path")
    if not isinstance(manifest_name, str):
        raise ResourceManifestError("build info resource manifest path is missing")
    if not _is_safe_relative_path(manifest_name):
        raise ResourceManifestError("build info resource manifest path is invalid")
    if not _SHA256_PATTERN.fullmatch(resource_manifest["sha256"]):
        raise ResourceManifestError("build info resource manifest hash is invalid")
    return payload


def verify_build_info_json(
    build_info_path: os.PathLike,
    manifest_path: os.PathLike,
    build_identity_path: Optional[os.PathLike] = None,
) -> Dict[str, object]:
    """Verify JSON metadata against the manifest and generated Python identity.

    :param build_info_path: Generated JSON build metadata path.
    :type build_info_path: os.PathLike
    :param manifest_path: Resource manifest referenced by the metadata.
    :type manifest_path: os.PathLike
    :param build_identity_path: Optional generated ``build_info.py`` path.
    :type build_identity_path: os.PathLike, optional
    :return: The validated build metadata payload.
    :rtype: dict
    :raises ResourceManifestError: If hashes or identity values disagree.

    Example::

        >>> verify_build_info_json(
        ...     'pyfcstm/_build_info.json', 'pyfcstm/_resource_manifest.json'
        ... )['schema_version']
        'build-info/v1'
    """
    payload = load_build_info_json(build_info_path)
    manifest_file = Path(manifest_path)
    manifest_raw = _manifest_bytes(manifest_file)
    expected_hash = hashlib.sha256(manifest_raw).hexdigest()
    recorded = payload["resource_manifest"]["sha256"]  # type: ignore[index]
    if recorded != expected_hash:
        raise ResourceManifestError("build info resource manifest hash mismatch")
    if build_identity_path is not None:
        try:
            identity = load_build_identity_file(build_identity_path)
        except FileNotFoundError:
            # Frozen PYZ modules have no on-disk ``build_info.py``.  Reuse the
            # static loader in ``pyfcstm.config`` rather than executing code.
            from . import _load_frozen_build_identity

            identity, error = _load_frozen_build_identity()
            if error:
                raise ResourceManifestError(
                    "frozen build identity is unavailable: {}".format(error)
                )
        if payload["identity"] != identity.values():  # type: ignore[index]
            raise ResourceManifestError("build info identity disagrees with build_info.py")
    return payload
