"""Tests for the static built-in self-check registry."""

import json
from pathlib import Path

import pytest

from pyfcstm._selfcheck import registry
from pyfcstm._selfcheck.model import CheckOutcome, CheckSpec
from pyfcstm._selfcheck.registry import (
    EXPECTED_CHECK_IDS,
    REGISTRY_SCHEMA_VERSION,
    get_worker,
    registry_metadata,
    selected_specs,
)


@pytest.mark.unittest
def test_registry_contains_the_exact_frozen_69_ids():
    """The fixed result inventory is complete, unique, and ordered."""
    assert len(EXPECTED_CHECK_IDS) == 69
    assert len(set(EXPECTED_CHECK_IDS)) == 69
    specs = selected_specs("default")
    assert [item.check_id for item in specs[1:]] == list(EXPECTED_CHECK_IDS)
    assert specs[0].check_id == "runtime.metadata"


@pytest.mark.unittest
def test_registry_profiles_keep_results_stable_and_raise_visual_requirements():
    """Profiles preserve the fixed set while visualize requires optional checks."""
    default = selected_specs("default")
    full = selected_specs("full")
    visualize = selected_specs("visualize")
    assert [item.check_id for item in default] == [item.check_id for item in full]
    assert [item.check_id for item in full] == [item.check_id for item in visualize]
    default_by_id = {item.check_id: item for item in default}
    visualize_by_id = {item.check_id: item for item in visualize}
    for check_id in EXPECTED_CHECK_IDS:
        if check_id.startswith("visualize."):
            assert default_by_id[check_id].required is False
            assert visualize_by_id[check_id].required is True
    assert default_by_id["native.z3.solve"].prerequisites == ("native.z3.load",)
    assert default_by_id["native.z3.solve"].prerequisite_policy == "skip_on_warn"
    assert default_by_id["env.python"].timeout_seconds == 10.0
    assert default_by_id["core.cli.help"].timeout_seconds == 30.0
    assert default_by_id["visualize.local_render"].timeout_seconds == 60.0


@pytest.mark.unittest
@pytest.mark.parametrize(
    "artifact_kind",
    ["wheel", "sdist", "frozen-onefile", "frozen-onedir", "frozen-unknown"],
)
def test_release_artifacts_require_identity_checks(artifact_kind):
    """Release and frozen artifacts cannot downgrade stale identity to a warning."""
    specs = {item.check_id: item for item in selected_specs("default", artifact_kind=artifact_kind)}
    assert specs["identity.source"].required is True
    assert specs["identity.artifact"].required is True


@pytest.mark.unittest
def test_installable_artifacts_require_distribution_contract():
    """Wheel and sdist workers cannot downgrade missing install metadata."""
    source = {item.check_id: item for item in selected_specs("default", artifact_kind="source")}
    wheel = {item.check_id: item for item in selected_specs("default", artifact_kind="wheel")}
    for check_id in ("install.metadata", "install.record", "install.requirements", "install.entrypoints"):
        assert source[check_id].required is False
        assert wheel[check_id].required is True


@pytest.mark.unittest
def test_missing_install_metadata_is_failure_for_wheel(monkeypatch):
    """A wheel worker treats absent distribution metadata as a required failure."""
    class MissingMetadata:
        @staticmethod
        def version(name):
            raise KeyError(name)

        @staticmethod
        def files(name):
            raise KeyError(name)

    monkeypatch.setenv("PYFCSTM_SELFCHECK_ARTIFACT_KIND", "wheel")
    monkeypatch.setattr(registry.importlib, "metadata", MissingMetadata, raising=False)
    assert registry._distribution_metadata().status == "FAIL"
    assert registry._distribution_metadata().reason == "metadata_unavailable"


@pytest.mark.unittest
def test_frozen_distribution_version_mismatch_is_failure(monkeypatch):
    """A frozen executable cannot report stale distribution metadata as valid."""
    class StaleMetadata:
        @staticmethod
        def version(name):
            assert name == "pyfcstm"
            return "0.5.0"

    monkeypatch.setitem(registry.sys.modules, "importlib.metadata", StaleMetadata)
    monkeypatch.setattr(registry.importlib, "metadata", StaleMetadata, raising=False)
    monkeypatch.setattr(registry.sys, "frozen", True, raising=False)
    assert registry._distribution_metadata().reason == "metadata_version_mismatch"


@pytest.mark.unittest
def test_editable_egg_info_direct_url_is_recognized(tmp_path, monkeypatch):
    """Legacy egg-info direct_url metadata receives the same parser as dist-info."""
    egg = tmp_path / "pyfcstm.egg-info"
    egg.mkdir()
    (egg / "direct_url.json").write_text(
        '{"url": "file:///src/pyfcstm", "dir_info": {"editable": true}}',
        encoding="utf-8",
    )
    (egg / "INSTALLER").write_text("pip\n", encoding="utf-8")
    monkeypatch.setattr(registry, "_distribution_root", lambda: tmp_path)
    monkeypatch.setattr(
        registry,
        "_distribution_file",
        lambda *_args, **_kwargs: registry._pass("metadata"),
    )
    outcome = registry._distribution_requirements()
    assert outcome.status == "PASS"
    assert outcome.observed == "editable_direct_url"


@pytest.mark.unittest
def test_source_checkout_keeps_identity_checks_optional():
    """A source checkout keeps missing generated identity metadata diagnostic-only."""
    specs = {item.check_id: item for item in selected_specs("default", artifact_kind="source")}
    assert specs["identity.source"].required is False
    assert specs["identity.artifact"].required is False


@pytest.mark.unittest
def test_registry_metadata_records_explicit_skips_without_removing_ids():
    """Explicit skips are metadata while the stable result inventory remains intact."""
    metadata = registry_metadata("full", ("visualize.java", "native.z3.solve"))
    assert metadata["schema_version"] == REGISTRY_SCHEMA_VERSION
    assert metadata["expected_ids"] == list(EXPECTED_CHECK_IDS)
    assert metadata["selected_ids"] == list(EXPECTED_CHECK_IDS)
    assert metadata["explicit_skipped_ids"] == ["visualize.java", "native.z3.solve"]
    specs = {item.check_id: item for item in selected_specs("full", metadata["explicit_skipped_ids"])}
    assert specs["visualize.java"].explicit_skip is True
    assert specs["native.z3.solve"].explicit_skip is True
    generated = selected_specs("full", (item for item in ("visualize.java",)))
    assert {item.check_id for item in generated if item.explicit_skip} == {"visualize.java"}
    with pytest.raises(ValueError, match="unknown explicit"):
        registry_metadata("default", ("unknown.check",))


@pytest.mark.unittest
def test_builtin_callbacks_return_typed_outcomes():
    """Registered callbacks expose semantic outcomes rather than marker strings."""
    for spec in selected_specs("default"):
        outcome = get_worker(spec.worker_key)()
        assert isinstance(outcome, CheckOutcome)
        assert outcome.status in ("PASS", "WARN", "SKIP", "FAIL")


@pytest.mark.unittest
def test_unknown_registry_key_is_not_dynamically_imported():
    """Arbitrary module/callable paths are rejected by the static map."""
    with pytest.raises(KeyError):
        get_worker("package.module:callable")


@pytest.mark.unittest
def test_builtin_workers_report_missing_runtime_identity(monkeypatch):
    """Compatibility callbacks diagnose missing package metadata."""
    import pyfcstm
    import pyfcstm.config.meta as meta

    monkeypatch.setattr(pyfcstm, "__version__", None)
    with pytest.raises(RuntimeError, match="version is unavailable"):
        get_worker("self_dispatch")()

    monkeypatch.setattr(meta, "__VERSION__", "")
    with pytest.raises(RuntimeError, match="version is unavailable"):
        get_worker("runtime_metadata")()


@pytest.mark.unittest
def test_source_identity_reports_stale_live_head(monkeypatch):
    """A generated identity never silently masks a different live commit."""
    import pyfcstm._selfcheck.registry as registry

    monkeypatch.setattr(registry.subprocess, "check_output", lambda *args, **kwargs: b"deadbeef\n")
    outcome = get_worker("check_identity_source")()
    assert isinstance(outcome, CheckOutcome)
    assert outcome.status == "WARN"
    assert outcome.reason == "identity_stale"


@pytest.mark.unittest
def test_source_identity_reports_invalid_and_unavailable_states(monkeypatch, tmp_path):
    """Source identity diagnostics preserve invalid, unavailable, and no-git states."""
    import pyfcstm.config as config

    monkeypatch.setattr(config, "BUILD_INFO_ERROR", "broken identity")
    assert registry._identity_source().reason == "identity_invalid"
    monkeypatch.setattr(config, "BUILD_INFO_ERROR", None)
    monkeypatch.setattr(registry, "_live_source_identity", lambda: (_ for _ in ()).throw(OSError("git unavailable")))
    assert registry._identity_source().reason == "identity_unavailable"
    monkeypatch.setattr(registry, "_package_root", lambda: tmp_path / "pyfcstm")
    (tmp_path / "pyfcstm").mkdir()
    assert registry._identity_source().status == "PASS"


@pytest.mark.unittest
def test_build_info_module_import_failure_is_structured(monkeypatch):
    """Missing generated modules are reported without leaking ImportError."""
    monkeypatch.setattr(
        registry.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError(name)),
    )
    outcome = registry._identity_build_info_module()
    assert outcome.status == "WARN"
    assert outcome.reason == "identity_unavailable"


@pytest.mark.unittest
def test_resource_callbacks_report_corrupt_json_and_yaml(tmp_path, monkeypatch):
    """Corrupt packaged resource payloads become explicit failures."""
    import pyfcstm._selfcheck.registry as registry

    broken = tmp_path / "broken-resource"
    broken.write_text("not: [valid", encoding="utf-8")
    monkeypatch.setattr(registry, "_resource", lambda _name: broken)
    json_outcome = get_worker("check_resource_diagnostics_schemas")()
    yaml_outcome = get_worker("check_resource_diagnostics_codes")()
    assert json_outcome.status == "FAIL"
    assert json_outcome.reason == "resource_invalid"
    assert yaml_outcome.status == "FAIL"
    assert yaml_outcome.reason == "resource_invalid"


@pytest.mark.unittest
def test_dependency_diagnostics_are_structured_without_result_ids():
    """Dependency inventory is metadata, not an additional fixed check."""
    diagnostics = registry.collect_dependency_diagnostics()
    assert diagnostics
    assert all(
        set(item) >= {"name", "status", "version", "path", "reason"}
        for item in diagnostics
    )
    assert all(not item["name"].startswith("dep.") for item in diagnostics)


@pytest.mark.unittest
def test_install_record_validates_hashes(tmp_path, monkeypatch):
    """A RECORD row with a bad digest is reported as a deterministic failure."""
    payload = tmp_path / "module.py"
    payload.write_text("ok", encoding="utf-8")
    record = tmp_path / "RECORD"
    record.write_text("module.py,sha256=AAAAAAAA,2\n", encoding="utf-8")
    monkeypatch.setattr(registry, "_record_path", lambda: record)
    monkeypatch.setattr(registry, "_distribution_root", lambda: tmp_path)
    outcome = get_worker("check_install_record")()
    assert outcome.status == "FAIL"
    assert outcome.reason == "record_hash_mismatch"


@pytest.mark.unittest
def test_install_requirements_distinguishes_editable_direct_url(tmp_path, monkeypatch):
    """Editable direct-url metadata is parsed without requiring wheel RECORD semantics."""
    dist = tmp_path / "pyfcstm-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Name: pyfcstm\n", encoding="utf-8")
    (dist / "direct_url.json").write_text(
        '{"url": "file:///src/pyfcstm", "dir_info": {"editable": true}}',
        encoding="utf-8",
    )
    (dist / "INSTALLER").write_text("pip\n", encoding="utf-8")
    monkeypatch.setattr(registry, "_distribution_root", lambda: tmp_path)
    monkeypatch.setattr(registry, "_distribution_file", lambda *_args, **_kwargs: registry._pass("metadata"))
    outcome = registry._distribution_requirements()
    assert outcome.status == "PASS"
    assert outcome.observed == "editable_direct_url"


@pytest.mark.unittest
def test_install_requirements_rejects_invalid_direct_url_and_empty_installer(tmp_path, monkeypatch):
    """Direct URL and installer metadata are validated through the real file parser."""
    dist = tmp_path / "pyfcstm-1.0.dist-info"
    dist.mkdir()
    (dist / "direct_url.json").write_text("[]", encoding="utf-8")
    (dist / "INSTALLER").write_text("\n", encoding="utf-8")
    monkeypatch.setattr(registry, "_distribution_root", lambda: tmp_path)
    monkeypatch.setattr(registry, "_distribution_file", lambda *_args, **_kwargs: registry._pass("metadata"))
    assert registry._distribution_requirements().reason == "direct_url_invalid"
    (dist / "direct_url.json").write_text('{"url": "file:///src"}', encoding="utf-8")
    assert registry._distribution_requirements().reason == "install_metadata_invalid"


@pytest.mark.unittest
def test_install_requirements_requires_wheel_metadata_for_artifacts(monkeypatch):
    """A wheel/sdist check cannot pass without its WHEEL metadata file."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_ARTIFACT_KIND", "wheel")

    def distribution_file(filename, required=False):
        del required
        if filename == "METADATA":
            return registry._pass("metadata")
        if filename == "WHEEL":
            return registry._fail("WHEEL is missing", "record_missing")
        return registry._pass(filename)

    monkeypatch.setattr(registry, "_distribution_file", distribution_file)
    outcome = registry._distribution_requirements()
    assert outcome.status == "FAIL"
    assert outcome.reason == "record_missing"


@pytest.mark.unittest
def test_diagnostics_schema_probe_rejects_json_that_is_not_a_schema(monkeypatch):
    """A parseable arbitrary JSON document is not a valid diagnostics schema."""
    path = Path(__file__).parents[2] / "pyfcstm" / "template" / "index.json"
    monkeypatch.setattr(registry, "_resource", lambda _name: path)
    outcome = registry._diagnostics_schemas()
    assert outcome.status == "FAIL"
    assert outcome.reason == "schema_invalid"


@pytest.mark.unittest
def test_required_entrypoint_metadata_missing_is_failure(monkeypatch):
    """A wheel without the pyfcstm console entry point is not healthy."""
    class EmptyEntryPoints:
        @staticmethod
        def entry_points():
            return []

    monkeypatch.setenv("PYFCSTM_SELFCHECK_ARTIFACT_KIND", "wheel")
    monkeypatch.setattr(registry.importlib, "metadata", EmptyEntryPoints, raising=False)
    outcome = registry._distribution_entrypoints()
    assert outcome.status == "FAIL"
    assert outcome.reason == "entrypoint_missing"


@pytest.mark.unittest
def test_identity_source_checks_dirty_ref_and_version(monkeypatch):
    """Live source identity mismatch includes more than the commit hash."""
    monkeypatch.setattr(registry, "_live_source_identity", lambda: {
        "commit": "deadbeef",
        "dirty": False,
        "ref": "other",
        "version": "other",
    })
    outcome = get_worker("check_identity_source")()
    assert outcome.status == "WARN"
    assert outcome.reason == "identity_stale"


@pytest.mark.unittest
def test_registry_validation_is_a_structured_error_and_skips_callbacks(
    monkeypatch, capsys
):
    """Invalid registry input is reported without starting any callback."""
    from pyfcstm._selfcheck import supervisor

    calls = []
    specs = (
        CheckSpec("duplicate", "first"),
        CheckSpec("duplicate", "second"),
    )

    def forbidden_callback():
        calls.append(True)
        return CheckOutcome("PASS", "must not run")

    monkeypatch.setattr(
        supervisor, "selected_specs", lambda profile, **kwargs: specs
    )
    monkeypatch.setitem(registry._WORKERS, "first", forbidden_callback)
    monkeypatch.setitem(registry._WORKERS, "second", forbidden_callback)
    assert supervisor.run_supervisor(("--format", "json")) == 1
    payload = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in payload["results"]] == ["selfcheck.registry"]
    result = payload["results"][0]
    assert result["status"] == "ERROR"
    assert result["reason"] == "registry_invalid"
    assert "duplicate self-check ID" in result["evidence"]
    assert calls == []


@pytest.mark.unittest
def test_registry_small_probe_helpers_cover_missing_and_optional_paths(monkeypatch, tmp_path):
    """Small registry helpers expose deterministic missing-resource outcomes."""
    import sys

    import pyfcstm

    monkeypatch.setattr(
        registry.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError(name)),
    )
    assert registry._probe_import("missing").reason == "import_unavailable"
    assert registry._optional_import("missing").reason == "capability_unavailable"
    assert registry._path_probe(tmp_path / "missing", "required").reason == "resource_missing"
    assert (
        registry._path_probe(tmp_path / "missing", "optional", required=False).reason
        == "capability_unavailable"
    )

    original_version = pyfcstm.__version__
    monkeypatch.setattr(pyfcstm, "__version__", original_version + ".mismatch")
    assert registry._identity_package().reason == "identity_mismatch"
    monkeypatch.setattr(sys, "platform", "win32")
    assert registry._platform_specific("linux").status == "SKIP"
    assert registry._platform_specific("linux").reason == "not_applicable"
    assert registry._platform_specific("win").status == "PASS"


@pytest.mark.unittest
def test_registry_distribution_and_manifest_missing_paths(monkeypatch, tmp_path):
    """Distribution and manifest probes distinguish optional absence from failure."""
    class EmptyDistributionMetadata:
        """Provide deterministic installed metadata with no requested files."""

        @staticmethod
        def files(name):
            return ()

    monkeypatch.setattr(
        registry.importlib,
        "metadata",
        EmptyDistributionMetadata,
        raising=False,
    )
    assert registry._distribution_file("NO_SUCH_RECORD", required=False).reason == "not_applicable"
    assert registry._distribution_file("NO_SUCH_RECORD", required=True).reason == "record_missing"

    class MissingDistributionMetadata:
        """Emulate importlib metadata when running from an uninstalled checkout."""

        @staticmethod
        def files(name):
            raise KeyError(name)

    monkeypatch.setattr(
        registry.importlib,
        "metadata",
        MissingDistributionMetadata,
        raising=False,
    )
    assert registry._distribution_file("METADATA", required=True).reason == "metadata_unavailable"

    class MissingDistributionImportError:
        """Emulate modern importlib metadata's missing-package exception."""

        class PackageNotFoundError(ImportError):
            """Raised when no installed distribution metadata exists."""

        @staticmethod
        def files(name):
            raise MissingDistributionImportError.PackageNotFoundError(name)

    monkeypatch.setattr(
        registry.importlib,
        "metadata",
        MissingDistributionImportError,
        raising=False,
    )
    assert registry._distribution_file("METADATA", required=True).reason == "metadata_unavailable"

    missing = tmp_path / "missing.json"
    monkeypatch.setattr(registry, "_resource", lambda name: missing)
    assert registry._manifest().reason == "manifest_unavailable"


@pytest.mark.unittest
def test_frozen_install_record_is_not_applicable(monkeypatch):
    """A frozen executable has no wheel RECORD contract to validate."""
    monkeypatch.setattr(registry.sys, "frozen", True, raising=False)
    outcome = registry._distribution_record(required=True)
    assert outcome.status == "SKIP"
    assert outcome.reason == "not_applicable"


@pytest.mark.unittest
def test_disabled_remote_probe_is_skipped(monkeypatch):
    """Offline default mode does not execute a remote capability probe."""
    monkeypatch.delenv("PYFCSTM_SELFCHECK_NETWORK", raising=False)
    outcome = registry._visual_remote_tls()
    assert outcome.status == "SKIP"
    assert outcome.reason == "network_disabled"


@pytest.mark.unittest
def test_native_inventory_and_unidecode_tables_are_real_probes():
    """Native and table checks exercise their load-bearing runtime assets."""
    assert registry._artifact_native_inventory().status == "PASS"
    assert registry._resource_unidecode().status == "PASS"


@pytest.mark.unittest
def test_artifact_metadata_rejects_formal_kind_mismatch(monkeypatch, tmp_path):
    """A formal wheel cannot carry source-kind build metadata."""
    import sys
    import types

    build = tmp_path / "_build_info.json"
    manifest = tmp_path / "_resource_manifest.json"
    identity = tmp_path / "config" / "build_info.py"
    identity.parent.mkdir()
    for path in (build, manifest, identity):
        path.write_text("{}", encoding="utf-8")
    fake_manifest_module = types.SimpleNamespace(
        verify_build_info_json=lambda *args, **kwargs: {"artifact_kind": "source"}
    )
    monkeypatch.setitem(sys.modules, "pyfcstm.config._resource_manifest", fake_manifest_module)
    monkeypatch.setattr(registry, "_resource", lambda name: tmp_path / name)
    monkeypatch.setenv("PYFCSTM_SELFCHECK_ARTIFACT_KIND", "wheel")
    outcome = registry._artifact_metadata()
    assert outcome.status == "FAIL"
    assert outcome.reason == "artifact_kind_mismatch"


@pytest.mark.unittest
def test_template_archive_rejects_path_traversal(monkeypatch, tmp_path):
    """Template ZIP members cannot escape their declared extraction root."""
    import json
    import zipfile

    template_root = tmp_path / "template"
    template_root.mkdir()
    (template_root / "index.json").write_text(
        json.dumps({"templates": [{"archive": "bad.zip"}]}), encoding="utf-8"
    )
    with zipfile.ZipFile(str(template_root / "bad.zip"), "w") as archive:
        archive.writestr("../escape.txt", "bad")
    monkeypatch.setattr(
        registry,
        "_resource",
        lambda name: tmp_path / name,
    )
    outcome = registry._template_archives()
    assert outcome.status == "FAIL"
    assert outcome.reason == "archive_invalid"
