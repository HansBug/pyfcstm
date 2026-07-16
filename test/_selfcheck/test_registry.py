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


def _install_build_info(monkeypatch, **overrides):
    """Install deterministic generated identity without reading an ignored file."""
    import pyfcstm.config as config

    values = {
        "BUILD_COMMIT": "generated-commit",
        "BUILD_DIRTY": False,
        "BUILD_REF": "generated-ref",
        "BUILD_SOURCE": "generated-test",
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setattr(config, name, value)
    monkeypatch.setattr(config, "BUILD_INFO_ERROR", None)
    return config


@pytest.mark.unittest
def test_registry_contains_the_exact_frozen_57_ids():
    """The fixed result inventory is complete, unique, and ordered."""
    assert len(EXPECTED_CHECK_IDS) == 57
    assert len(set(EXPECTED_CHECK_IDS)) == 57
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
def test_source_checkout_keeps_identity_checks_optional():
    """A source checkout keeps missing generated identity metadata diagnostic-only."""
    specs = {item.check_id: item for item in selected_specs("default")}
    assert specs["identity.source"].required is False
    assert specs["identity.build_info_module"].required is False
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

    _install_build_info(monkeypatch)
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
    _install_build_info(monkeypatch)
    monkeypatch.setattr(registry, "_live_source_identity", lambda: (_ for _ in ()).throw(OSError("git unavailable")))
    assert registry._identity_source().reason == "identity_unavailable"
    monkeypatch.setattr(registry, "_package_root", lambda: tmp_path / "pyfcstm")
    (tmp_path / "pyfcstm").mkdir()
    assert registry._identity_source().status == "PASS"


@pytest.mark.unittest
def test_build_info_module_import_failure_is_structured(monkeypatch):
    """Missing generated data is reported without importing its module."""
    import pyfcstm.config as config

    monkeypatch.setattr(config, "BUILD_COMMIT", None)
    monkeypatch.setattr(config, "BUILD_INFO_ERROR", None)
    outcome = registry._identity_build_info_module()
    assert outcome.status == "WARN"
    assert outcome.reason == "identity_unavailable"


@pytest.mark.unittest
def test_build_info_module_syntax_failure_is_structured(monkeypatch):
    """Malformed generated data becomes a safe identity diagnostic."""
    import pyfcstm.config as config

    monkeypatch.setattr(config, "BUILD_INFO_ERROR", "SyntaxError: malformed")
    outcome = registry._identity_build_info_module()
    assert outcome.status == "WARN"
    assert outcome.reason == "identity_invalid"


@pytest.mark.unittest
def test_build_info_check_never_imports_or_executes_generated_module(monkeypatch):
    """Identity checks consume only config's statically parsed literal values."""
    _install_build_info(monkeypatch)
    monkeypatch.setattr(
        registry.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(AssertionError("module executed")),
    )
    outcome = registry._identity_build_info_module()
    assert outcome.status == "PASS"
    assert "without module execution" in outcome.summary


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
def test_resource_llm_guide_reports_sidecar_mismatch_through_public_api(monkeypatch):
    """The registry uses strict public guide APIs for sidecar verification."""
    from pyfcstm.llm import _resources as guide_resources

    def fake_loader(_package, resource):
        if resource.endswith(".sha256"):
            return (64 * "0").encode("ascii")
        if resource.endswith(".md"):
            return b"# guide\n"
        return None

    monkeypatch.setattr(guide_resources.pkgutil, "get_data", fake_loader)

    outcome = registry._resource_llm_guide()

    assert outcome.status == "FAIL"
    assert outcome.reason == "resource_invalid"
    assert "integrity verification failed" in outcome.observed


@pytest.mark.unittest
def test_diagnostics_schema_probe_accepts_parseable_json(monkeypatch):
    """The resource check stops at JSON readability rather than schema policy."""
    path = Path(__file__).parents[2] / "pyfcstm" / "template" / "index.json"
    monkeypatch.setattr(registry, "_resource", lambda _name: path)
    outcome = registry._diagnostics_schemas()
    assert outcome.status == "PASS"


@pytest.mark.unittest
def test_identity_source_checks_dirty_ref_and_version(monkeypatch):
    """Live source identity mismatch includes more than the commit hash."""
    _install_build_info(monkeypatch)
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
def test_disabled_remote_probe_is_skipped(monkeypatch):
    """Offline default mode does not execute a remote capability probe."""
    monkeypatch.delenv("PYFCSTM_SELFCHECK_NETWORK", raising=False)
    outcome = registry._visual_remote_tls()
    assert outcome.status == "SKIP"
    assert outcome.reason == "network_disabled"


@pytest.mark.unittest
def test_grammar_asset_probes_cover_both_generated_grammars():
    """Grammar checks require the packaged source and generated data files."""
    assert registry._grammar_assets(registry._FCSTM_GRAMMAR_ASSETS, "FCSTM").status == "PASS"
    assert registry._grammar_assets(registry._FBMCQ_GRAMMAR_ASSETS, "FBMCQ").status == "PASS"
    assert registry._resource_unidecode().status == "PASS"


@pytest.mark.unittest
def test_grammar_asset_probe_reports_the_missing_relative_path(tmp_path, monkeypatch):
    """A missing generated grammar asset is named in the failure evidence."""
    assets = registry._FCSTM_GRAMMAR_ASSETS
    for relative in assets[:-1]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("present", encoding="utf-8")
    monkeypatch.setattr(registry, "_resource", lambda relative: tmp_path / relative)

    outcome = registry._grammar_assets(assets, "FCSTM")

    assert outcome.status == "FAIL"
    assert outcome.reason == "resource_missing"
    assert "GrammarParser.tokens" in outcome.observed


@pytest.mark.unittest
def test_template_archive_probe_reports_crc_corruption(monkeypatch):
    """A readable archive with a bad CRC is reported as corrupted, not absent."""
    original_testzip = registry.zipfile.ZipFile.testzip
    monkeypatch.setattr(
        registry.zipfile.ZipFile,
        "testzip",
        lambda handle: "broken-entry",
    )
    try:
        outcome = registry._template_archives()
    finally:
        monkeypatch.setattr(registry.zipfile.ZipFile, "testzip", original_testzip)
    assert outcome.status == "FAIL"
    assert outcome.reason == "archive_invalid"
