"""Failure diagnostics for resource, native, and visualization probes."""

import json
import contextlib
import http.server
import threading
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from pyfcstm._selfcheck import registry


_PNG = b"\x89PNG\r\n\x1a\n" + b"selfcheck"


class _PlantUmlServiceHandler(http.server.BaseHTTPRequestHandler):
    """Serve the minimum real HTTP contract consumed by plantumlcli."""

    def do_GET(self):  # noqa: N802 - stdlib handler hook name
        if self.path.rstrip("/") == "/plantuml":
            payload = b"<html><div id='footer'>PlantUML Server version 1.2023.6</div></html>"
            content_type = "text/html"
        elif self.path.startswith("/plantuml/png/"):
            payload = _PNG
            content_type = "image/png"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A002 - stdlib hook signature
        del format, args


@contextlib.contextmanager
def _plantuml_service():
    """Run a real local HTTP service for the plantumlcli remote backend."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _PlantUmlServiceHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:{}/plantuml".format(server.server_port)
    finally:
        server.shutdown()
        thread.join(timeout=5.0)
        server.server_close()


def _raiser(error):
    def raise_error(*args, **kwargs):
        del args, kwargs
        raise error

    return raise_error


def _assert_traceback(outcome, status, reason, message):
    assert outcome.status == status
    assert outcome.reason == reason
    assert "Traceback (most recent call last)" in outcome.exception
    assert message in outcome.exception
    assert message in outcome.evidence


@pytest.mark.unittest
def test_process_evidence_and_external_capture_are_bounded(tmp_path):
    """Large text and subprocess pipes keep head/tail diagnostic evidence."""
    size = registry._PROCESS_OUTPUT_LIMIT * 2
    evidence = registry._process_evidence(
        ["fake"], stdout="x" * size, stderr=b"y" * size
    )
    assert "stdout_truncated_characters={}".format(size // 2) in evidence
    assert "stderr_truncated_bytes={}".format(size // 2) in evidence
    assert len(evidence) < (registry._PROCESS_OUTPUT_LIMIT * 2) + 1000

    command = [
        sys.executable,
        "-c",
        ("import sys; sys.stdout.write('x' * {0}); sys.stderr.write('y' * {0})").format(
            size
        ),
    ]
    completed = registry._run_subprocess_bounded(command, timeout=10.0)
    assert completed.returncode == 0
    assert b"bytes omitted" in completed.stdout
    assert b"bytes omitted" in completed.stderr
    assert len(completed.stdout) < registry._PROCESS_OUTPUT_LIMIT + 100
    assert len(completed.stderr) < registry._PROCESS_OUTPUT_LIMIT + 100

    hard_limit = registry._PROCESS_OUTPUT_HARD_LIMIT
    pid_file = tmp_path / "hard-limit.pid"
    command = [
        sys.executable,
        "-c",
        (
            "import pathlib, os, sys, time; "
            "pathlib.Path({0!r}).write_text(str(os.getpid())); "
            "sys.stdout.buffer.write(b'x' * {1}); "
            "sys.stdout.flush(); time.sleep(30)"
        ).format(str(pid_file), hard_limit + 1),
    ]
    started = time.monotonic()
    with pytest.raises(registry._ProcessOutputLimitExceeded) as error:
        registry._run_subprocess_bounded(command, timeout=10.0)
    assert time.monotonic() - started < 5.0
    assert b"bytes omitted" in error.value.output
    assert len(error.value.output) < registry._PROCESS_OUTPUT_LIMIT + 100

    timeout_command = [sys.executable, "-c", "import time; time.sleep(30)"]
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as timeout_error:
        registry._run_subprocess_bounded(timeout_command, timeout=0.1)
    assert time.monotonic() - started < 2.0
    assert timeout_error.value.output == b""
    assert timeout_error.value.stderr == b""


@pytest.mark.unittest
def test_resource_catalog_archive_extract_and_grammar_failures(monkeypatch, tmp_path):
    """Resource probes preserve damaged package paths and parser tracebacks."""
    import pyfcstm.bmc.parse as bmc_parse
    import pyfcstm.dsl.parse as dsl_parse
    import pyfcstm.template as template_module

    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")
    real_resource = registry._resource
    monkeypatch.setattr(registry, "_resource", lambda relative: broken)
    outcome = registry._template_index()
    assert outcome.reason == "resource_invalid"
    assert "JSONDecodeError" in outcome.exception
    outcome = registry._template_archives()
    _assert_traceback(outcome, "FAIL", "resource_invalid", "Expecting value")

    valid = tmp_path / "index.json"
    valid.write_text('{"templates": []}', encoding="utf-8")
    monkeypatch.setattr(registry, "_resource", lambda relative: valid)
    real_list = template_module.list_templates
    monkeypatch.setattr(
        template_module,
        "list_templates",
        _raiser(ValueError("catalog metadata failed")),
    )
    _assert_traceback(
        registry._template_index(), "FAIL", "resource_invalid", "catalog metadata failed"
    )
    monkeypatch.setattr(template_module, "list_templates", real_list)

    archive_root = tmp_path / "template"
    archive_root.mkdir()
    index = tmp_path / "template-index.json"
    index.write_text(
        json.dumps({"templates": [{"archive": "missing.zip"}]}), encoding="utf-8"
    )

    def archive_resource(relative):
        return index if relative == "template/index.json" else archive_root

    monkeypatch.setattr(registry, "_resource", archive_resource)
    outcome = registry._template_archives()
    assert outcome.reason == "resource_missing"
    assert "missing.zip" in outcome.observed

    invalid_archive = archive_root / "invalid.zip"
    invalid_archive.write_bytes(b"not a zip")
    index.write_text(
        json.dumps({"templates": [{"archive": "invalid.zip"}]}), encoding="utf-8"
    )
    _assert_traceback(
        registry._template_archives(), "FAIL", "archive_invalid", "File is not a zip file"
    )

    monkeypatch.setattr(registry, "_resource", real_resource)
    real_extract = template_module.extract_template
    monkeypatch.setattr(template_module, "extract_template", lambda name, target: None)
    outcome = registry._template_extract()
    assert outcome.reason == "extract_invalid"
    monkeypatch.setattr(
        template_module,
        "extract_template",
        _raiser(OSError("archive extraction failed")),
    )
    _assert_traceback(
        registry._template_extract(), "FAIL", "extract_failed", "archive extraction failed"
    )
    monkeypatch.setattr(template_module, "extract_template", real_extract)

    missing = registry._fail("missing grammar", "resource_missing")
    real_grammar_assets = registry._grammar_assets
    monkeypatch.setattr(registry, "_grammar_assets", lambda assets, label: missing)
    assert registry._grammar_fcstm() is missing
    assert registry._grammar_fbmcq() is missing
    monkeypatch.setattr(registry, "_grammar_assets", real_grammar_assets)

    real_fcstm_parse = dsl_parse.parse_state_machine_dsl
    monkeypatch.setattr(
        dsl_parse,
        "parse_state_machine_dsl",
        _raiser(ValueError("FCSTM grammar failed")),
    )
    _assert_traceback(
        registry._grammar_fcstm(), "FAIL", "grammar_invalid", "FCSTM grammar failed"
    )
    monkeypatch.setattr(dsl_parse, "parse_state_machine_dsl", real_fcstm_parse)

    real_bmc_parse = bmc_parse.parse_bmc_query
    monkeypatch.setattr(
        bmc_parse,
        "parse_bmc_query",
        _raiser(ValueError("FBMCQ grammar failed")),
    )
    _assert_traceback(
        registry._grammar_fbmcq(), "FAIL", "grammar_invalid", "FBMCQ grammar failed"
    )
    monkeypatch.setattr(bmc_parse, "parse_bmc_query", real_bmc_parse)

    monkeypatch.setattr(
        registry,
        "_optional_import",
        lambda name: registry._warn("optional missing", "capability_unavailable"),
    )
    assert registry._resource_optional_import("optional").status == "WARN"


@pytest.mark.unittest
def test_native_backend_mismatch_and_exception_diagnostics(monkeypatch):
    """Native and accelerated backends expose wrong values and tracebacks."""
    import certifi
    import charset_normalizer
    from lxml import etree
    import markupsafe
    import yaml
    import z3

    real_solver = z3.Solver

    class UnsatSolver:
        def add(self, expression):
            del expression

        def check(self):
            return z3.unsat

    monkeypatch.setattr(z3, "Solver", UnsatSolver)
    outcome = registry._z3_solve()
    assert outcome.reason == "solver_failed"
    assert outcome.observed == "status=unsat model[selfcheck_x]=None"
    monkeypatch.setattr(z3, "Solver", _raiser(OSError("libz3 load failed")))
    _assert_traceback(
        registry._z3_solve(), "FAIL", "solver_failed", "libz3 load failed"
    )
    monkeypatch.setattr(z3, "Solver", real_solver)

    real_yaml = yaml.safe_load
    monkeypatch.setattr(yaml, "safe_load", lambda text: {"key": "wrong"})
    assert registry._yaml_backend().status == "WARN"
    monkeypatch.setattr(yaml, "safe_load", _raiser(ValueError("YAML backend failed")))
    _assert_traceback(
        registry._yaml_backend(),
        "WARN",
        "capability_unavailable",
        "YAML backend failed",
    )
    monkeypatch.setattr(yaml, "safe_load", real_yaml)

    real_fromstring = etree.fromstring
    monkeypatch.setattr(
        etree, "fromstring", lambda data: SimpleNamespace(tag="unexpected")
    )
    assert registry._lxml_parse().status == "WARN"
    monkeypatch.setattr(etree, "fromstring", _raiser(ValueError("lxml parse failed")))
    _assert_traceback(
        registry._lxml_parse(),
        "WARN",
        "capability_unavailable",
        "lxml parse failed",
    )
    monkeypatch.setattr(etree, "fromstring", real_fromstring)

    real_escape = markupsafe.escape
    monkeypatch.setattr(markupsafe, "escape", lambda value: "wrong")
    assert registry._markupsafe_backend().status == "WARN"
    monkeypatch.setattr(
        markupsafe, "escape", _raiser(ValueError("MarkupSafe failed"))
    )
    _assert_traceback(
        registry._markupsafe_backend(),
        "WARN",
        "capability_unavailable",
        "MarkupSafe failed",
    )
    monkeypatch.setattr(markupsafe, "escape", real_escape)

    real_from_bytes = charset_normalizer.from_bytes
    monkeypatch.setattr(
        charset_normalizer,
        "from_bytes",
        lambda data: SimpleNamespace(best=lambda: None),
    )
    assert registry._charset_normalizer_backend().status == "WARN"
    monkeypatch.setattr(
        charset_normalizer,
        "from_bytes",
        _raiser(ValueError("charset detection failed")),
    )
    _assert_traceback(
        registry._charset_normalizer_backend(),
        "WARN",
        "capability_unavailable",
        "charset detection failed",
    )
    monkeypatch.setattr(charset_normalizer, "from_bytes", real_from_bytes)

    real_optional = registry._optional_import
    monkeypatch.setattr(
        registry,
        "_optional_import",
        lambda *args, **kwargs: registry._warn(
            "certifi missing", "capability_unavailable"
        ),
    )
    assert registry._ssl_certifi().status == "WARN"
    monkeypatch.setattr(registry, "_optional_import", real_optional)
    real_where = certifi.where
    monkeypatch.setattr(certifi, "where", _raiser(OSError("CA bundle failed")))
    _assert_traceback(
        registry._ssl_certifi(),
        "WARN",
        "capability_unavailable",
        "CA bundle failed",
    )
    monkeypatch.setattr(certifi, "where", real_where)


@pytest.mark.unittest
def test_java_and_local_plantuml_diagnostics(monkeypatch, tmp_path):
    """Local visualization keeps command, output, timeout, and result evidence."""
    jar = tmp_path / "plantuml.jar"
    jar.write_bytes(b"jar")
    monkeypatch.setattr(registry, "_package_root", lambda: tmp_path)

    monkeypatch.setattr(registry.shutil, "which", lambda name: None)
    assert registry._java().status == "WARN"
    assert registry._visual_local_version().status == "WARN"
    assert registry._visual_local_render().status == "WARN"

    monkeypatch.setattr(registry.shutil, "which", lambda name: "/usr/bin/java")
    assert registry._plantuml_jar().status == "PASS"

    timeout = subprocess.TimeoutExpired(
        ["/usr/bin/java", "-version"], 15.0, output=b"partial", stderr=b"hung"
    )
    monkeypatch.setattr(registry, "_run_subprocess_bounded", _raiser(timeout))
    outcome = registry._java()
    _assert_traceback(
        outcome, "WARN", "capability_unavailable", "timed out after 15.0 seconds"
    )
    assert "stdout:\npartial" in outcome.evidence
    assert "stderr:\nhung" in outcome.evidence

    nonzero = SimpleNamespace(returncode=2, stdout=b"java out", stderr=b"java err")
    monkeypatch.setattr(
        registry, "_run_subprocess_bounded", lambda *args, **kwargs: nonzero
    )
    outcome = registry._java()
    assert outcome.status == "WARN"
    assert "returncode=2" in outcome.evidence
    assert "java err" in outcome.evidence

    monkeypatch.setattr(
        registry,
        "_run_subprocess_bounded",
        _raiser(OSError("PlantUML version spawn failed")),
    )
    _assert_traceback(
        registry._visual_local_version(),
        "WARN",
        "capability_unavailable",
        "PlantUML version spawn failed",
    )

    empty = SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
    monkeypatch.setattr(
        registry, "_run_subprocess_bounded", lambda *args, **kwargs: empty
    )
    outcome = registry._visual_local_version()
    assert outcome.status == "WARN"
    assert outcome.observed == "returncode=0 output_bytes=0"

    version = SimpleNamespace(returncode=0, stdout=b"PlantUML 1.0", stderr=b"")
    monkeypatch.setattr(
        registry, "_run_subprocess_bounded", lambda *args, **kwargs: version
    )
    assert registry._visual_local_version().status == "PASS"

    monkeypatch.setattr(
        registry,
        "_run_subprocess_bounded",
        _raiser(OSError("PlantUML render spawn failed")),
    )
    _assert_traceback(
        registry._visual_local_render(),
        "WARN",
        "capability_unavailable",
        "PlantUML render spawn failed",
    )

    bad_render = SimpleNamespace(returncode=3, stdout=b"", stderr=b"render err")
    monkeypatch.setattr(
        registry, "_run_subprocess_bounded", lambda *args, **kwargs: bad_render
    )
    outcome = registry._visual_local_render()
    assert outcome.status == "WARN"
    assert "render err" in outcome.evidence

    png = SimpleNamespace(returncode=0, stdout=b"PNG", stderr=b"")
    monkeypatch.setattr(
        registry, "_run_subprocess_bounded", lambda *args, **kwargs: png
    )
    outcome = registry._visual_local_render()
    assert outcome.status == "PASS"
    assert outcome.observed == "3 image bytes"


@pytest.mark.unittest
def test_plantuml_jar_environment_path_has_priority(monkeypatch, tmp_path):
    """The explicit JAR environment follows the same source as the CLI."""
    package_jar = tmp_path / "package" / "plantuml.jar"
    package_jar.parent.mkdir()
    package_jar.write_bytes(b"package")
    env_jar = tmp_path / "configured" / "plantuml.jar"
    env_jar.parent.mkdir()
    env_jar.write_bytes(b"configured")
    monkeypatch.setattr(registry, "_package_root", lambda: package_jar.parent)
    monkeypatch.setenv("PLANTUML_JAR", str(env_jar))

    outcome = registry._plantuml_jar()

    assert outcome.status == "PASS"
    assert str(env_jar) in outcome.observed
    assert str(package_jar) not in outcome.observed


@pytest.mark.unittest
def test_plantuml_jar_invalid_environment_path_falls_back(monkeypatch, tmp_path):
    """A stale explicit path does not hide a valid packaged JAR candidate."""
    package_jar = tmp_path / "package" / "plantuml.jar"
    package_jar.parent.mkdir()
    package_jar.write_bytes(b"package")
    monkeypatch.setattr(registry, "_package_root", lambda: package_jar.parent)
    monkeypatch.setenv("PLANTUML_JAR", str(tmp_path / "missing" / "plantuml.jar"))

    outcome = registry._plantuml_jar()

    assert outcome.status == "PASS"
    assert str(package_jar) in outcome.observed


@pytest.mark.unittest
def test_plantuml_jar_uses_packaged_candidate_without_environment(monkeypatch, tmp_path):
    """The packaged candidate remains the fallback when no env path exists."""
    package_jar = tmp_path / "package" / "plantuml.jar"
    package_jar.parent.mkdir()
    package_jar.write_bytes(b"package")
    monkeypatch.setattr(registry, "_package_root", lambda: package_jar.parent)
    monkeypatch.delenv("PLANTUML_JAR", raising=False)

    outcome = registry._plantuml_jar()

    assert outcome.status == "PASS"
    assert str(package_jar) in outcome.observed


@pytest.mark.unittest
def test_remote_host_parser_rejects_invalid_scheme(monkeypatch):
    """Malformed PlantUML hosts produce a capability warning, not a crash."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_NETWORK", "1")
    monkeypatch.setenv("PLANTUML_HOST", "ftp://plantuml.example/plantuml")

    outcome = registry._visual_remote_tls()

    assert outcome.status == "WARN"
    assert "PLANTUML_HOST" in (outcome.exception or "")


@pytest.mark.unittest
def test_remote_host_parser_accepts_explicit_port(monkeypatch):
    """An explicit HTTPS port is used for the TLS probe."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_NETWORK", "1")
    monkeypatch.setenv("PLANTUML_HOST", "https://plantuml.example:9443/plantuml")
    calls = []

    class _Socket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback_value):
            del exc_type, exc_value, traceback_value

    class _Tls:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback_value):
            del exc_type, exc_value, traceback_value

        def version(self):
            return "TLSv1.3"

    monkeypatch.setattr(
        registry.socket,
        "create_connection",
        lambda address, timeout: calls.append((address, timeout)) or _Socket(),
    )
    monkeypatch.setattr(
        registry.ssl,
        "create_default_context",
        lambda: type("_Context", (), {"wrap_socket": lambda self, raw, server_hostname: _Tls()})(),
    )

    outcome = registry._visual_remote_tls()

    assert outcome.status == "PASS"
    assert calls == [(('plantuml.example', 9443), 5.0)]
    assert "TLSv1.3" in outcome.observed


@pytest.mark.unittest
def test_remote_host_uses_http_transport_without_tls(monkeypatch):
    """A configured HTTP service is probed on its host and not hard-coded TLS."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_NETWORK", "1")
    monkeypatch.setenv("PLANTUML_HOST", "http://127.0.0.1:18080/plantuml")
    calls = []

    class _Socket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback_value):
            del exc_type, exc_value, traceback_value

    monkeypatch.setattr(
        registry.socket,
        "create_connection",
        lambda address, timeout: calls.append((address, timeout)) or _Socket(),
    )
    monkeypatch.setattr(
        registry.ssl,
        "create_default_context",
        _raiser(AssertionError("HTTP must not create a TLS context")),
    )

    outcome = registry._visual_remote_tls()

    assert outcome.status == "PASS"
    assert "transport=plain" in outcome.observed
    assert "host=http://127.0.0.1:18080/plantuml" in outcome.observed
    assert calls == [(('127.0.0.1', 18080), 5.0)]


@pytest.mark.unittest
def test_remote_render_uses_configured_service_and_validates_png(monkeypatch):
    """Remote rendering follows PLANTUML_HOST and validates a PNG signature."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_NETWORK", "1")
    with _plantuml_service() as host:
        monkeypatch.setenv("PLANTUML_HOST", host)
        outcome = registry._visual_remote_render()

    assert outcome.status == "PASS"
    assert "host={}".format(host) in outcome.observed
    assert "PNG" in outcome.observed


@pytest.mark.unittest
def test_remote_render_backend_shape_failure_is_a_capability_warning(monkeypatch):
    """A malformed PlantUML homepage remains a reportable capability warning."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_NETWORK", "1")

    class _Backend:
        def check(self):
            raise AttributeError("homepage footer is unavailable")

    monkeypatch.setattr(
        "pyfcstm.entry.visualize.create_remote_plantuml_backend",
        lambda remote_host: _Backend(),
    )
    outcome = registry._visual_remote_render()

    assert outcome.status == "WARN"
    assert "homepage footer is unavailable" in (outcome.exception or "")


class _ContextValue:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, exc_type, exc_value, traceback_value):
        del exc_type, exc_value, traceback_value


@pytest.mark.unittest
def test_remote_visualization_and_unidecode_diagnostics(monkeypatch):
    """Opt-in remote and dynamic-table checks retain concrete observations."""
    import unidecode as unidecode_module
    import pyfcstm.entry.visualize as visualize_module

    monkeypatch.setenv("PYFCSTM_SELFCHECK_NETWORK", "1")
    monkeypatch.setenv("PLANTUML_HOST", "https://www.plantuml.com/plantuml")
    monkeypatch.setattr(
        registry.ssl,
        "create_default_context",
        _raiser(OSError("TLS setup failed")),
    )
    _assert_traceback(
        registry._visual_remote_tls(),
        "WARN",
        "capability_unavailable",
        "TLS setup failed",
    )

    tls = SimpleNamespace(version=lambda: "TLSv1.2")
    context = SimpleNamespace(
        wrap_socket=lambda raw, server_hostname: _ContextValue(tls)
    )
    monkeypatch.setattr(registry.ssl, "create_default_context", lambda: context)
    monkeypatch.setattr(
        registry.socket,
        "create_connection",
        lambda address, timeout: _ContextValue(object()),
    )
    outcome = registry._visual_remote_tls()
    assert outcome.status == "PASS"
    assert "transport=tls" in outcome.observed
    assert "host=https://www.plantuml.com/plantuml" in outcome.observed

    class _Backend:
        def __init__(self, payload):
            self.payload = payload

        def check(self):
            return None

        def dump(self, path, type_, code):
            del type_, code
            with open(path, "wb") as handle:
                handle.write(self.payload)

    monkeypatch.setattr(
        visualize_module,
        "create_remote_plantuml_backend",
        lambda remote_host: _Backend(b"not-png"),
    )
    outcome = registry._visual_remote_render()
    assert outcome.status == "WARN"
    assert "not-png" in outcome.observed

    monkeypatch.setattr(
        visualize_module,
        "create_remote_plantuml_backend",
        _raiser(OSError("remote render failed")),
    )
    _assert_traceback(
        registry._visual_remote_render(),
        "WARN",
        "capability_unavailable",
        "remote render failed",
    )

    monkeypatch.setattr(
        visualize_module,
        "create_remote_plantuml_backend",
        lambda remote_host: _Backend(b"\x89PNG\r\n\x1a\nimage"),
    )
    outcome = registry._visual_remote_render()
    assert outcome.status == "PASS"
    assert "transport=tls" in outcome.observed
    assert "PNG response_bytes=13" in outcome.observed

    real_unidecode = unidecode_module.unidecode
    monkeypatch.setattr(unidecode_module, "unidecode", lambda value: "")
    assert registry._resource_unidecode().reason == "tables_invalid"
    monkeypatch.setattr(
        unidecode_module,
        "unidecode",
        _raiser(ValueError("Unidecode table failed")),
    )
    _assert_traceback(
        registry._resource_unidecode(),
        "FAIL",
        "tables_invalid",
        "Unidecode table failed",
    )
    monkeypatch.setattr(unidecode_module, "unidecode", real_unidecode)

    with pytest.raises(ValueError, match="unknown self-check profile"):
        registry.registry_metadata("unknown")
