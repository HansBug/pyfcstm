"""Tests for packaged resource and JSON build manifests."""

import json
from datetime import datetime, timezone

import pytest

from pyfcstm.config import _build_identity
from pyfcstm.config._resource_manifest import (
    BUILD_INFO_JSON_FILENAME,
    RESOURCE_MANIFEST_FILENAME,
    ResourceManifestError,
    build_resource_manifest,
    load_build_info_json,
    load_resource_manifest,
    verify_build_info_json,
    verify_resource_manifest,
    write_build_info_json,
    write_resource_manifest,
)


def _identity():
    return _build_identity._identity_from_commit(
        "a" * 40,
        False,
        "main",
        datetime(2026, 7, 15, tzinfo=timezone.utc),
        "git",
    )


def _package_tree(tmp_path):
    package = tmp_path / "pyfcstm"
    (package / "config").mkdir(parents=True)
    (package / "__init__.py").write_text("__version__ = 'test'\n", encoding="utf-8")
    (package / "config" / "build_info.py").write_text(
        "BUILD_COMMIT = None\n", encoding="utf-8"
    )
    (package / "data.json").write_text("{}\n", encoding="utf-8")
    return package


@pytest.mark.unittest
def test_manifest_is_sorted_and_excludes_generated_json(tmp_path):
    _package_tree(tmp_path)
    manifest_path, manifest = write_resource_manifest(tmp_path, "wheel")

    paths = [entry["path"] for entry in manifest["resources"]]
    assert paths == sorted(paths)
    assert "pyfcstm/_resource_manifest.json" not in paths
    assert "pyfcstm/_build_info.json" not in paths
    assert manifest_path.name == RESOURCE_MANIFEST_FILENAME
    assert load_resource_manifest(manifest_path) == manifest
    assert verify_resource_manifest(manifest_path, tmp_path) == manifest


@pytest.mark.unittest
def test_build_info_hashes_manifest_and_matches_python_identity(tmp_path):
    package = _package_tree(tmp_path)
    identity = _identity()
    _build_identity.write_build_identity_file(
        package / "config" / "build_info.py", identity
    )
    manifest_path, _ = write_resource_manifest(tmp_path, "sdist")
    build_path, build_info = write_build_info_json(
        tmp_path, identity, "sdist", manifest_path
    )

    assert build_path.name == BUILD_INFO_JSON_FILENAME
    assert build_info["identity"] == identity.values()
    assert build_info["build_time_utc"] == identity.time_utc
    assert set(build_info["pyinstaller"]) == {"available", "version"}
    assert load_build_info_json(build_path) == build_info
    assert (
        verify_build_info_json(
            build_path,
            manifest_path,
            package / "config" / "build_info.py",
        )
        == build_info
    )


@pytest.mark.unittest
def test_manifest_rejects_path_traversal_and_hash_mismatch(tmp_path):
    _package_tree(tmp_path)
    manifest_path, _ = write_resource_manifest(tmp_path, "source")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["resources"][0]["path"] = "C:/outside"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ResourceManifestError, match="normalized relative path"):
        load_resource_manifest(manifest_path)

    manifest_path, _ = write_resource_manifest(tmp_path, "source")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["resources"][0]["path"] = "../outside"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ResourceManifestError, match="normalized relative path"):
        load_resource_manifest(manifest_path)

    manifest_path, _ = write_resource_manifest(tmp_path, "source")
    (tmp_path / "pyfcstm" / "data.json").write_text("x!\n", encoding="utf-8")
    with pytest.raises(ResourceManifestError, match="sha256 mismatch"):
        verify_resource_manifest(manifest_path, tmp_path)


@pytest.mark.unittest
def test_manifest_requires_a_package_root(tmp_path):
    with pytest.raises(ResourceManifestError, match="pyfcstm package directory"):
        build_resource_manifest(tmp_path, "source")


@pytest.mark.unittest
def test_manifest_matches_wheel_and_frozen_resource_closures(tmp_path):
    package = _package_tree(tmp_path)
    (package / "diagnostics").mkdir()
    (package / "diagnostics" / "README.md").write_text("docs\n", encoding="utf-8")
    (package / "llm").mkdir()
    (package / "llm" / "guide.md").write_text("guide\n", encoding="utf-8")
    (package / "module.py").write_text("value = 1\n", encoding="utf-8")

    wheel = build_resource_manifest(tmp_path, "wheel")
    wheel_paths = {entry["path"] for entry in wheel["resources"]}
    assert "pyfcstm/diagnostics/README.md" in wheel_paths
    assert "pyfcstm/llm/guide.md" in wheel_paths
    assert "pyfcstm/module.py" in wheel_paths

    frozen = build_resource_manifest(tmp_path, "frozen-onefile")
    frozen_paths = {entry["path"] for entry in frozen["resources"]}
    assert "pyfcstm/diagnostics/README.md" in frozen_paths
    assert "pyfcstm/module.py" not in frozen_paths
