"""Static inventory and first-party callbacks for the self-check runner.

The registry is deliberately data-driven but remains static at runtime: every
worker key is created by this module and every check identifier is frozen in
``EXPECTED_CHECK_IDS``.  Callbacks perform small, deterministic probes against
the installed package and its packaged resources.  They return semantic
outcomes only; process isolation, report formatting, and exit-code policy stay
in the supervisor/worker layers.
"""

import importlib
import json
import os
import platform
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import urlsplit
import zipfile
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

from .model import CheckOutcome, CheckSpec


try:
    import ssl
except ImportError:
    # Frozen Windows builds may lack a loadable OpenSSL extension; keep the
    # core registry importable so HTTPS remains an explicit capability WARN.
    ssl = None


Worker = Callable[[], CheckOutcome]
Probe = Callable[[], CheckOutcome]

_FUNCTION_DSL = """def int counter = 0;
state Root {
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done :: Go effect { counter = counter + 1; }
}
"""
_BMC_REACH_QUERY = 'check reach <= 1: active("Root");'
_BMC_TERMINATED_QUERY = "check reach <= 1: terminated();"
_BMC_FORBID_QUERY = 'check forbid <= 1: active("Root");'
_PROCESS_OUTPUT_LIMIT = 64 * 1024
_PROCESS_OUTPUT_HARD_LIMIT = 2 * 1024 * 1024
_PROCESS_POLL_INTERVAL = 0.01
_PLANTUML_JAR_ENV = "PLANTUML_JAR"
_PLANTUML_HOST_ENV = "PLANTUML_HOST"
_OFFICIAL_PLANTUML_HOST = "http://www.plantuml.com/plantuml"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class _ProcessOutputLimitExceeded(OSError):
    """Raised after an external probe exceeds its bounded output budget."""

    def __init__(self, command, stdout: bytes, stderr: bytes) -> None:
        super().__init__("external process output exceeded 2 MiB")
        self.cmd = command
        self.output = stdout
        self.stderr = stderr

REGISTRY_SCHEMA_VERSION = "pyfcstm-selfcheck-registry/v1"
REGISTRY_VERSION = "pr3-v3"
CAPABILITY_CHECK_IDS = frozenset(
    (
        "visualize.python_stack",
        "visualize.java",
        "visualize.plantuml_jar",
        "visualize.local_version",
        "visualize.remote_tls",
    )
)

# This tuple is a public audit anchor.  Keep its order stable: it is also the
# order used by the human and JSON reports.
EXPECTED_CHECK_IDS = (
    "env.python",
    "env.os",
    "env.locale",
    "env.console",
    "env.process",
    "env.temp",
    "env.filesystem",
    "env.win.loader",
    "env.linux.libc",
    "env.macos.runtime",
    "identity.package",
    "identity.source",
    "identity.build_info_module",
    "identity.artifact",
    "resource.diagnostics.codes",
    "resource.diagnostics.schemas",
    "resource.templates.index",
    "resource.templates.archives",
    "resource.templates.extract",
    "resource.llm.guide",
    "resource.grammar.fcstm",
    "resource.grammar.fbmcq",
    "resource.pygments",
    "resource.random_user_agent",
    "native.z3.load",
    "native.z3.solve",
    "native.lxml.parse",
    "native.yaml.backend",
    "native.markupsafe.backend",
    "native.charset_normalizer.backend",
    "native.ssl.certifi",
    "runtime.unidecode.tables",
    "core.dsl.parse",
    "core.model.build",
    "core.model.roundtrip",
    "core.render.expr",
    "core.render.statement",
    "core.template.python",
    "core.template.catalog",
    "core.simulate.cycle",
    "core.solver.translation",
    "core.verify.solve",
    "core.cli.help",
    "core.cli.generate",
    "core.cli.simulate",
    "core.cli.plantuml",
    "bmc.query.parse",
    "bmc.verification.prepare",
    "bmc.property.solve",
    "bmc.module.closure",
    "visualize.python_stack",
    "visualize.java",
    "visualize.plantuml_jar",
    "visualize.local_version",
    "visualize.local_render",
    "visualize.remote_tls",
    "visualize.remote_render",
)

if len(EXPECTED_CHECK_IDS) != 57:  # pragma: no cover - immutable contract guard
    raise RuntimeError("self-check registry must contain exactly 57 fixed IDs")


def _pass(summary: str, expected: Optional[str] = None, observed: Optional[str] = None):
    return CheckOutcome("PASS", summary, expected=expected, observed=observed)


def _skip(summary: str, reason: str = "not_applicable", observed=None):
    return CheckOutcome("SKIP", summary, reason=reason, observed=observed)


def _warn(
    summary: str,
    reason: str,
    expected: Optional[str] = None,
    observed: Optional[str] = None,
    evidence: str = "",
    remediation: Optional[str] = None,
    exception: Optional[str] = None,
):
    return CheckOutcome(
        "WARN",
        summary,
        reason=reason,
        expected=expected,
        observed=observed,
        evidence=evidence,
        remediation=remediation,
        exception=exception,
    )


def _fail(
    summary: str,
    reason: str,
    expected: Optional[str] = None,
    observed=None,
    evidence: str = "",
    remediation: Optional[str] = None,
    exception: Optional[str] = None,
):
    return CheckOutcome(
        "FAIL",
        summary,
        reason=reason,
        expected=expected,
        observed=observed,
        evidence=evidence,
        remediation=remediation,
        exception=exception,
    )


def _exception_diagnostic(
    status: str,
    summary: str,
    reason: str,
    err: BaseException,
    expected: Optional[str] = None,
    remediation: Optional[str] = None,
    evidence_prefix: str = "",
) -> CheckOutcome:
    """Preserve one caught exception and its full active traceback."""
    traceback_text = traceback.format_exc()
    evidence = "\n".join(
        item for item in (evidence_prefix.rstrip(), traceback_text.rstrip()) if item
    )
    constructor = _warn if status == "WARN" else _fail
    return constructor(
        summary,
        reason,
        expected=expected,
        observed="{}: {}".format(type(err).__name__, err),
        evidence=evidence,
        remediation=remediation,
        exception=traceback_text,
    )


def _decode_process_output(value: Any) -> str:
    """Decode subprocess output without allowing diagnostic decoding to fail."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "backslashreplace")
    return str(value)


def _bounded_process_output(value: Any) -> Tuple[str, int, str]:
    """Return bounded head/tail process output and its omitted size."""
    if value is None:
        return "", 0, "bytes"
    if isinstance(value, bytes):
        total = len(value)
        unit = "bytes"
        if total <= _PROCESS_OUTPUT_LIMIT:
            sample = value
        else:
            half = _PROCESS_OUTPUT_LIMIT // 2
            omitted = total - _PROCESS_OUTPUT_LIMIT
            marker = "\n...<{} bytes omitted>...\n".format(omitted).encode("ascii")
            sample = value[:half] + marker + value[-half:]
        return _decode_process_output(sample), max(0, total - _PROCESS_OUTPUT_LIMIT), unit
    text = str(value)
    total = len(text)
    unit = "characters"
    if total <= _PROCESS_OUTPUT_LIMIT:
        return text, 0, unit
    half = _PROCESS_OUTPUT_LIMIT // 2
    omitted = total - _PROCESS_OUTPUT_LIMIT
    marker = "\n...<{} characters omitted>...\n".format(omitted)
    return text[:half] + marker + text[-half:], omitted, unit


def _read_bounded_process_file(stream) -> bytes:
    """Read bounded head/tail bytes from one seekable process-output file."""
    stream.flush()
    stream.seek(0, os.SEEK_END)
    total = stream.tell()
    stream.seek(0)
    if total <= _PROCESS_OUTPUT_LIMIT:
        return stream.read()
    half = _PROCESS_OUTPUT_LIMIT // 2
    head = stream.read(half)
    stream.seek(-half, os.SEEK_END)
    tail = stream.read(half)
    marker = "\n...<{} bytes omitted>...\n".format(
        total - _PROCESS_OUTPUT_LIMIT
    ).encode("ascii")
    return head + marker + tail


def _run_subprocess_bounded(command, timeout: float, input_data=None, cwd=None):
    """Run one external command and kill it when output exceeds a hard limit."""
    with tempfile.TemporaryFile(prefix="pyfcstm-process-stdout-") as stdout_stream:
        with tempfile.TemporaryFile(prefix="pyfcstm-process-stderr-") as stderr_stream:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
                cwd=cwd,
            )
            if input_data is not None:
                try:
                    process.stdin.write(input_data)
                    process.stdin.close()
                except (AttributeError, OSError, ValueError):
                    # PIPE setup, writes, and closes can fail if the child exits
                    # before consuming the fixed probe input.
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=1.0)
                    raise

            deadline = time.monotonic() + timeout
            while True:
                return_code = process.poll()
                stdout_size = os.fstat(stdout_stream.fileno()).st_size
                stderr_size = os.fstat(stderr_stream.fileno()).st_size
                if (
                    stdout_size > _PROCESS_OUTPUT_HARD_LIMIT
                    or stderr_size > _PROCESS_OUTPUT_HARD_LIMIT
                ):
                    if return_code is None:
                        process.kill()
                        process.wait(timeout=1.0)
                    raise _ProcessOutputLimitExceeded(
                        command,
                        _read_bounded_process_file(stdout_stream),
                        _read_bounded_process_file(stderr_stream),
                    )
                if return_code is not None:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    process.kill()
                    process.wait(timeout=1.0)
                    raise subprocess.TimeoutExpired(
                        command,
                        timeout,
                        output=_read_bounded_process_file(stdout_stream),
                        stderr=_read_bounded_process_file(stderr_stream),
                    )
                time.sleep(min(_PROCESS_POLL_INTERVAL, remaining))

            return subprocess.CompletedProcess(
                command,
                return_code,
                stdout=_read_bounded_process_file(stdout_stream),
                stderr=_read_bounded_process_file(stderr_stream),
            )


def _process_evidence(
    command: Iterable[str],
    return_code: Optional[int] = None,
    stdout: Any = None,
    stderr: Any = None,
) -> str:
    """Format a bounded subprocess command and its captured output."""
    lines = ["command={}".format(repr(list(command)))]
    if return_code is not None:
        lines.append("returncode={}".format(return_code))
    stdout_text, stdout_omitted, stdout_unit = _bounded_process_output(stdout)
    stderr_text, stderr_omitted, stderr_unit = _bounded_process_output(stderr)
    if stdout_text:
        lines.extend(("stdout:", stdout_text.rstrip()))
    if stdout_omitted:
        lines.append("stdout_truncated_{}={}".format(stdout_unit, stdout_omitted))
    if stderr_text:
        lines.extend(("stderr:", stderr_text.rstrip()))
    if stderr_omitted:
        lines.append("stderr_truncated_{}={}".format(stderr_unit, stderr_omitted))
    return "\n".join(lines)


def _click_failure(arguments: Iterable[str], result) -> CheckOutcome:
    """Return a CLI failure with Click output and exception diagnostics."""
    exception_text = ""
    if result.exc_info:
        exception_text = "".join(traceback.format_exception(*result.exc_info))
    try:
        stderr = result.stderr
    except ValueError:
        # Click releases without separately captured stderr expose only output.
        stderr = ""
    evidence = _process_evidence(
        ["pyfcstm", *arguments],
        return_code=result.exit_code,
        stdout=result.output,
        stderr=stderr,
    )
    if exception_text:
        evidence += "\nexception:\n" + exception_text.rstrip()
    return _fail(
        "CLI command returned a non-zero status",
        "cli_failed",
        expected="exit_code=0",
        observed="exit_code={}".format(result.exit_code),
        evidence=evidence,
        exception=exception_text or None,
        remediation="rerun the recorded command and inspect its captured output",
    )


def _probe_import(module_name: str, attribute: Optional[str] = None) -> CheckOutcome:
    """Import a package module and optionally verify one exported attribute."""
    try:
        module = importlib.import_module(module_name)
        if attribute is not None:
            getattr(module, attribute)
    except (ImportError, AttributeError) as err:
        # ImportError covers unavailable modules; AttributeError covers missing exports.
        return _exception_diagnostic(
            "FAIL",
            "required import is unavailable",
            "import_unavailable",
            expected=module_name,
            err=err,
            remediation="reinstall pyfcstm and the named runtime dependency",
        )
    location = getattr(module, "__file__", None) or "built-in module"
    export = ".{}".format(attribute) if attribute else ""
    return _pass(
        "import {}{}".format(module_name, export),
        expected="import succeeds",
        observed=location,
    )


def _optional_import(module_name: str, attribute: Optional[str] = None) -> CheckOutcome:
    try:
        module = importlib.import_module(module_name)
        if attribute is not None:
            getattr(module, attribute)
    except (ImportError, AttributeError) as err:
        # ImportError covers unavailable optional modules; AttributeError covers missing exports.
        return _exception_diagnostic(
            "WARN",
            "optional dependency is unavailable",
            "capability_unavailable",
            expected=module_name,
            err=err,
            remediation="install the optional visualization dependencies when needed",
        )
    location = getattr(module, "__file__", None) or "built-in module"
    export = ".{}".format(attribute) if attribute else ""
    return _pass(
        "import optional {}{}".format(module_name, export),
        expected="optional import succeeds when installed",
        observed=location,
    )


def _path_probe(path: Path, label: str, required: bool = True) -> CheckOutcome:
    if path.is_file():
        return _pass(
            "read packaged {}".format(label),
            expected="regular file",
            observed="{} ({} bytes)".format(path, path.stat().st_size),
        )
    if required:
        return _fail("{} is missing".format(label), "resource_missing", str(path))
    return _warn("{} is unavailable".format(label), "capability_unavailable", str(path))


def _package_root() -> Path:
    import pyfcstm

    return Path(pyfcstm.__file__).resolve().parent


def _resource(name: str) -> Path:
    return _package_root() / name


def _artifact_self_dispatch() -> CheckOutcome:
    """Confirm the worker can import the package without CLI recursion."""
    import pyfcstm

    version = getattr(pyfcstm, "__version__", None)
    if not version:
        raise RuntimeError("package version is unavailable")
    return _pass(
        "import pyfcstm through the hidden self-check dispatch",
        expected="non-empty package version without ordinary CLI dispatch",
        observed="pyfcstm.__version__={}".format(version),
    )


def _runtime_metadata() -> CheckOutcome:
    """Validate cheap runtime metadata in the supervisor process."""
    from pyfcstm.config.meta import __VERSION__

    if not __VERSION__:
        raise RuntimeError("package version is unavailable")
    observed = "pyfcstm {} on Python {} ({})".format(
        __VERSION__, platform.python_version(), sys.platform
    )
    return _pass(
        "runtime metadata is available",
        expected="package version and Python runtime metadata",
        observed=observed,
    )


def _env_python() -> CheckOutcome:
    return _pass(
        "read the running Python version",
        expected="non-empty sys.version",
        observed=sys.version.split()[0],
    )


def _env_os() -> CheckOutcome:
    return _pass(
        "read operating-system metadata through platform.platform",
        expected="non-empty platform description",
        observed=platform.platform(),
    )


def _env_locale() -> CheckOutcome:
    import locale

    encoding = locale.getpreferredencoding(False)
    return _pass(
        "read locale.getpreferredencoding(False)",
        expected="non-empty preferred encoding",
        observed=encoding,
    )


def _env_console() -> CheckOutcome:
    return _pass(
        "query stdout/stderr terminal capability through isatty",
        expected="two boolean terminal flags",
        observed="stdout_tty={} stderr_tty={}".format(
            bool(getattr(sys.stdout, "isatty", lambda: False)()),
            bool(getattr(sys.stderr, "isatty", lambda: False)()),
        ),
    )


def _env_process() -> CheckOutcome:
    return _pass(
        "read the current process ID through os.getpid",
        expected="positive integer PID",
        observed=str(os.getpid()),
    )


def _env_temp() -> CheckOutcome:
    with tempfile.TemporaryDirectory(prefix="pyfcstm-selfcheck-") as path:
        probe = Path(path) / "probe"
        probe.write_text("ok", encoding="utf-8")
        if probe.read_text(encoding="utf-8") != "ok":
            return _fail("temporary directory roundtrip failed", "temp_roundtrip")
    return _pass(
        "write and read a UTF-8 probe in tempfile.TemporaryDirectory",
        expected="probe text 'ok' roundtrips",
        observed="probe text 'ok' roundtripped",
    )


def _env_filesystem() -> CheckOutcome:
    root = _package_root()
    return (
        _pass(
            "resolve the imported pyfcstm package directory",
            expected="existing directory",
            observed=str(root),
        )
        if root.is_dir()
        else _fail("package filesystem is missing", "filesystem_missing")
    )


def _platform_specific(platform_name: str) -> CheckOutcome:
    if sys.platform.startswith(platform_name):
        return _pass(
            "match sys.platform against the {} platform probe".format(platform_name),
            expected="prefix {}".format(platform_name),
            observed=sys.platform,
        )
    return CheckOutcome(
        "SKIP", "{} platform check is not applicable".format(platform_name),
        reason="not_applicable",
    )


def _identity_package() -> CheckOutcome:
    import pyfcstm
    from pyfcstm.config.meta import __VERSION__

    if not pyfcstm.__version__ or pyfcstm.__version__ != __VERSION__:
        return _fail("package version metadata disagrees", "identity_mismatch")
    return _pass(
        "compare pyfcstm.__version__ with config.meta.__VERSION__",
        expected=__VERSION__,
        observed=pyfcstm.__version__,
    )


def _identity_source() -> CheckOutcome:
    from pyfcstm import config

    if config.BUILD_INFO_ERROR:
        return _warn(
            "generated source identity is invalid",
            "identity_invalid",
            observed=config.BUILD_INFO_ERROR,
        )
    if config.BUILD_COMMIT is None:
        return _warn("source build identity is unavailable", "identity_unavailable")
    fields = ("BUILD_COMMIT", "BUILD_DIRTY", "BUILD_REF")
    missing = [field for field in fields if getattr(config, field, None) is None]
    if missing:
        return _warn("source build identity is incomplete", "identity_incomplete", observed=repr(missing))
    git_dir = _package_root().parent / ".git"
    if not git_dir.exists():
        return _pass("source build identity is readable")
    try:
        live = _live_source_identity()
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        UnicodeError,
        ValueError,
    ) as err:
        # Git can fail, time out, exceed its output budget, or return malformed text.
        command = getattr(err, "cmd", None)
        process_evidence = (
            _process_evidence(
                command,
                return_code=getattr(err, "returncode", None),
                stdout=getattr(err, "output", None),
                stderr=getattr(err, "stderr", None),
            )
            if command is not None
            else ""
        )
        return _exception_diagnostic(
            "WARN",
            "live source identity cannot be read",
            "identity_unavailable",
            err,
            remediation="regenerate build_info.py from the current checkout when identity is needed",
            evidence_prefix=process_evidence,
        )
    expected = {
        "commit": config.BUILD_COMMIT,
        "dirty": config.BUILD_DIRTY,
        "ref": config.BUILD_REF,
    }
    mismatch = [key for key in expected if expected[key] is not None and live.get(key) != expected[key]]
    if mismatch:
        return _warn(
            "generated source identity is stale",
            "identity_stale",
            expected=repr({key: live.get(key) for key in mismatch}),
            observed=repr({key: expected[key] for key in mismatch}),
        )
    return _pass("source build identity agrees with live HEAD", observed=repr(live))


def _live_source_identity() -> Dict[str, Any]:
    """Read live git identity and package version for source diagnostics."""
    root = str(_package_root().parent)

    def git_output(*arguments):
        command = ["git", *arguments]
        completed = _run_subprocess_bounded(command, timeout=5.0, cwd=root)
        if completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode,
                command,
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return completed.stdout

    commit = git_output("rev-parse", "HEAD").decode("ascii").strip()
    status = git_output("status", "--porcelain").decode("utf-8", "replace")
    ref = git_output("symbolic-ref", "--short", "HEAD").decode(
        "utf-8", "replace"
    ).strip()
    from pyfcstm.config.meta import __VERSION__

    return {"commit": commit, "dirty": bool(status), "ref": ref, "version": __VERSION__}


def _identity_build_info_module() -> CheckOutcome:
    from pyfcstm import config

    if config.BUILD_INFO_ERROR:
        return _warn(
            "generated build-info data is invalid",
            "identity_invalid",
            expected="literal build identity accepted by pyfcstm.config",
            observed=config.BUILD_INFO_ERROR,
            remediation="remove the damaged generated module and rerun make build_info",
        )
    if config.BUILD_COMMIT is None:
        return _warn(
            "generated build-info data is unavailable",
            "identity_unavailable",
            expected="literal build identity parsed by pyfcstm.config",
            observed="BUILD_COMMIT=None",
            remediation="run make build_info before packaging or release validation",
        )
    return _pass(
        "read generated identity through pyfcstm.config without module execution",
        expected="literal build identity parsed safely",
        observed="source={} commit={}".format(
            config.BUILD_SOURCE or "unknown", config.BUILD_COMMIT
        ),
    )


def _identity_artifact() -> CheckOutcome:
    return _identity_build_info_module()


def _json_resource(relative: str, label: str) -> CheckOutcome:
    path = _resource(relative)
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as err:
        # Resource reads can fail, decoding can fail, and json.loads can reject content.
        return _exception_diagnostic(
            "FAIL",
            "{} is invalid".format(label),
            "resource_invalid",
            err,
            expected="readable UTF-8 JSON at {}".format(relative),
        )
    return _pass(
        "parse packaged {} as JSON".format(label),
        expected="readable UTF-8 JSON",
        observed="{} ({} bytes)".format(relative, path.stat().st_size),
    )


def _diagnostics_schemas() -> CheckOutcome:
    """Check that every shipped diagnostics schema is readable JSON."""
    schemas = (
        "diagnostics/schema.json",
        "diagnostics/inspect_llm_report_schema.json",
    )
    for relative in schemas:
        outcome = _json_resource(relative, "diagnostic schema {}".format(relative))
        if outcome.status != "PASS":
            return outcome
    return _pass(
        "parse both packaged diagnostic schemas as JSON",
        expected="2 readable UTF-8 JSON documents",
        observed=repr(schemas),
    )


def _yaml_resource(relative: str, label: str) -> CheckOutcome:
    path = _resource(relative)
    try:
        import yaml
    except ImportError as err:
        # PyYAML is required to parse the packaged YAML resource.
        return _exception_diagnostic(
            "FAIL", "{} is invalid".format(label), "resource_invalid", err
        )
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError, yaml.YAMLError) as err:
        # Reads/decoding/type validation and yaml.safe_load expose these failures.
        return _exception_diagnostic(
            "FAIL",
            "{} is invalid".format(label),
            "resource_invalid",
            err,
            expected="readable UTF-8 YAML at {}".format(relative),
        )
    return _pass(
        "parse packaged {} as YAML".format(label),
        expected="readable UTF-8 YAML",
        observed="{} ({} bytes)".format(relative, path.stat().st_size),
    )


def _template_index() -> CheckOutcome:
    outcome = _json_resource("template/index.json", "template index")
    if outcome.status != "PASS":
        return outcome
    try:
        from pyfcstm.template import list_templates

        names = list_templates()
    except (OSError, ValueError, KeyError, TypeError) as err:
        # The public template catalog reads JSON and validates required metadata fields.
        return _exception_diagnostic(
            "FAIL", "template catalog cannot be loaded", "resource_invalid", err
        )
    return _pass(
        "parse the template index through list_templates",
        expected="at least one named built-in template",
        observed=repr(names),
    )


def _template_archives() -> CheckOutcome:
    relative = "template/index.json"
    try:
        index = json.loads(_resource(relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as err:
        # The index can disappear, become undecodable, or contain invalid JSON
        # after its prerequisite was checked.
        return _exception_diagnostic(
            "FAIL",
            "template archive index is invalid",
            "resource_invalid",
            err,
            expected="readable UTF-8 JSON at {}".format(relative),
        )
    missing = []
    for item in index.get("templates", []):
        archive = _resource("template") / str(item.get("archive", ""))
        if not archive.is_file():
            missing.append(str(archive))
            continue
        try:
            with zipfile.ZipFile(str(archive)) as handle:
                if handle.testzip() is not None:
                    return _fail(
                        "template archive is corrupted",
                        "archive_invalid",
                        observed=str(archive),
                    )
        except (OSError, zipfile.BadZipFile) as err:
            # Archive reads can fail and ZipFile rejects malformed central directories.
            return _exception_diagnostic(
                "FAIL", "template archive is invalid", "archive_invalid", err
            )
    return (
        _fail("template archives are missing", "resource_missing", observed=repr(missing))
        if missing
        else _pass(
            "open every indexed template archive and verify CRCs",
            expected="all indexed archives exist and testzip returns None",
            observed="{} archives verified".format(len(index.get("templates", []))),
        )
    )


def _template_extract() -> CheckOutcome:
    try:
        from pyfcstm.template import extract_template

        with tempfile.TemporaryDirectory(prefix="pyfcstm-template-") as target:
            extract_template("python", target)
            if not (Path(target) / "python" / "config.yaml").is_file():
                return _fail("python template extraction is incomplete", "extract_invalid")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as err:
        # Extraction reads catalog/archive data and validates the resulting directory.
        return _exception_diagnostic(
            "FAIL", "python template extraction failed", "extract_failed", err
        )
    return _pass(
        "extract the packaged Python template through its public API",
        expected="python/config.yaml exists after extraction",
        observed="config.yaml present",
    )


def _resource_llm_guide() -> CheckOutcome:
    """Load both packaged LLM guides through their strict public APIs."""
    try:
        from pyfcstm.llm import (
            get_fbmcq_language_guide_prompt_metadata_for_llm,
            get_grammar_guide_prompt_metadata_for_llm,
        )

        metadata = (
            get_grammar_guide_prompt_metadata_for_llm(
                raise_on_integrity_error=True
            ),
            get_fbmcq_language_guide_prompt_metadata_for_llm(
                raise_on_integrity_error=True
            ),
        )
    except (
        ImportError,
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as err:
        # Public guide APIs read UTF-8 text and strict SHA-256 sidecars.
        return _exception_diagnostic(
            "FAIL",
            "packaged LLM guide or checksum is invalid",
            "resource_invalid",
            err=err,
            remediation="restore the packaged guides and regenerate their SHA-256 sidecars",
        )
    return _pass(
        "packaged LLM guides and SHA-256 sidecars are valid",
        expected="strict public loaders accept both guide/sidecar pairs",
        observed=repr([item["resource_name"] for item in metadata]),
    )


_FCSTM_GRAMMAR_ASSETS = (
    "dsl/grammar/GrammarLexer.g4",
    "dsl/grammar/GrammarLexer.interp",
    "dsl/grammar/GrammarLexer.tokens",
    "dsl/grammar/GrammarParser.g4",
    "dsl/grammar/GrammarParser.interp",
    "dsl/grammar/GrammarParser.tokens",
)
_FBMCQ_GRAMMAR_ASSETS = (
    "bmc/grammar/BmcQueryLexer.g4",
    "bmc/grammar/BmcQueryLexer.interp",
    "bmc/grammar/BmcQueryLexer.tokens",
    "bmc/grammar/BmcQueryParser.g4",
    "bmc/grammar/BmcQueryParser.interp",
    "bmc/grammar/BmcQueryParser.tokens",
)


def _grammar_assets(assets: Iterable[str], label: str) -> CheckOutcome:
    """Check the generated grammar data shipped with the package."""
    assets = tuple(assets)
    missing = [str(_resource(path)) for path in assets if not _resource(path).is_file()]
    if missing:
        return _fail(
            "{} grammar assets are missing".format(label),
            "resource_missing",
            observed=repr(missing),
        )
    return _pass("{} grammar assets are present".format(label), observed=str(len(assets)))


def _grammar_fcstm() -> CheckOutcome:
    assets = _grammar_assets(_FCSTM_GRAMMAR_ASSETS, "FCSTM")
    if assets.status != "PASS":
        return assets
    try:
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.dsl.parse import parse_state_machine_dsl

        parse_state_machine_dsl("state Root;")
    except ImportError as err:
        # The packaged public grammar modules can be absent from a damaged install.
        return _exception_diagnostic("FAIL", "FCSTM grammar probe failed", "grammar_invalid", err)
    except (GrammarParseError, AttributeError, TypeError, ValueError) as err:
        # GrammarParseError is the public parser diagnostic; the remaining
        # classes cover malformed entry points, values, and return shapes.
        return _exception_diagnostic("FAIL", "FCSTM grammar probe failed", "grammar_invalid", err)
    return _pass(
        "load six FCSTM grammar assets and parse state Root",
        expected="6 assets and a valid StateMachineDSLProgram",
        observed="6 assets; parse succeeded",
    )


def _grammar_fbmcq() -> CheckOutcome:
    assets = _grammar_assets(_FBMCQ_GRAMMAR_ASSETS, "FBMCQ")
    if assets.status != "PASS":
        return assets
    try:
        from pyfcstm.bmc.errors import BmcError
        from pyfcstm.bmc.parse import parse_bmc_query

        parse_bmc_query('check reach <= 1: active("Root");')
    except ImportError as err:
        # The packaged public BMC grammar modules can be absent from a damaged install.
        return _exception_diagnostic("FAIL", "FBMCQ grammar probe failed", "grammar_invalid", err)
    except (BmcError, AttributeError, TypeError, ValueError) as err:
        # BmcError covers public FBMCQ parser diagnostics; the remaining
        # classes cover malformed entry points, values, and return shapes.
        return _exception_diagnostic("FAIL", "FBMCQ grammar probe failed", "grammar_invalid", err)
    return _pass(
        "load six FBMCQ grammar assets and parse reach bound 1",
        expected="6 assets and a valid BmcQuery",
        observed="6 assets; reach query parsed",
    )


def _resource_optional_import(module_name: str) -> CheckOutcome:
    return _optional_import(module_name)


def _z3_load() -> CheckOutcome:
    return _probe_import("z3", "Solver")


def _z3_solve() -> CheckOutcome:
    try:
        import z3

        solver = z3.Solver()
        x = z3.Int("selfcheck_x")
        solver.add(x == 1)
        status = solver.check()
        value = solver.model().eval(x).as_long() if status == z3.sat else None
        if status != z3.sat or value != 1:
            return _fail(
                "Z3 solver returned an unexpected result",
                "solver_failed",
                expected="status=sat model[selfcheck_x]=1",
                observed="status={} model[selfcheck_x]={}".format(status, value),
            )
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as err:
        # Z3 imports, native loading, expression construction, and model decoding fail here.
        return _exception_diagnostic("FAIL", "Z3 solver probe failed", "solver_failed", err)
    return _pass(
        "solve Int selfcheck_x constrained by selfcheck_x == 1",
        expected="status=sat model[selfcheck_x]=1",
        observed="status=sat model[selfcheck_x]=1",
    )


def _yaml_backend() -> CheckOutcome:
    try:
        import yaml
    except ImportError as err:
        # PyYAML may be absent from a damaged installation.
        return _exception_diagnostic(
            "WARN", "YAML backend is unavailable", "capability_unavailable", err
        )
    try:
        if yaml.safe_load("key: value")["key"] != "value":
            return _warn("YAML backend returned an unexpected value", "capability_unavailable")
    except (AttributeError, TypeError, ValueError, yaml.YAMLError) as err:
        # safe_load can reject malformed inputs or return values with invalid types.
        return _exception_diagnostic(
            "WARN", "YAML backend is unavailable", "capability_unavailable", err
        )
    return _pass(
        "parse YAML 'key: value' through yaml.safe_load",
        expected="mapping key -> value",
        observed="{'key': 'value'}",
    )


def _lxml_parse() -> CheckOutcome:
    try:
        from lxml import etree

        root = etree.fromstring(b"<selfcheck />")
        if root.tag != "selfcheck":
            return _warn("lxml parser returned an unexpected root", "capability_unavailable")
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as err:
        # lxml imports/native loading and etree parsing expose these failures.
        return _exception_diagnostic(
            "WARN", "lxml parser is unavailable", "capability_unavailable", err
        )
    return _pass(
        "parse b'<selfcheck />' through lxml.etree",
        expected="root tag selfcheck",
        observed="root tag selfcheck",
    )


def _markupsafe_backend() -> CheckOutcome:
    try:
        from markupsafe import escape

        if str(escape("<selfcheck>")) != "&lt;selfcheck&gt;":
            return _warn("MarkupSafe returned an unexpected escape", "capability_unavailable")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        # MarkupSafe import and escape conversion expose these failures.
        return _exception_diagnostic(
            "WARN", "MarkupSafe is unavailable", "capability_unavailable", err
        )
    return _pass(
        "escape '<selfcheck>' through MarkupSafe",
        expected="&lt;selfcheck&gt;",
        observed="&lt;selfcheck&gt;",
    )


def _charset_normalizer_backend() -> CheckOutcome:
    try:
        from charset_normalizer import from_bytes

        match = from_bytes(b"self-check").best()
        if match is None:
            return _warn("charset-normalizer found no encoding", "capability_unavailable")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        # charset-normalizer import and byte matching expose these failures.
        return _exception_diagnostic(
            "WARN", "charset-normalizer is unavailable", "capability_unavailable", err
        )
    return _pass(
        "detect the encoding of b'self-check' with charset-normalizer",
        expected="one best encoding match",
        observed="encoding={}".format(match.encoding),
    )


def _ssl_certifi() -> CheckOutcome:
    outcome = _optional_import("certifi", "where")
    if outcome.status != "PASS":
        return outcome
    try:
        import certifi

        path = certifi.where()
        return _path_probe(Path(path), "certifi CA bundle", required=False)
    except (OSError, AttributeError, TypeError, ValueError) as err:
        # certifi.where and filesystem validation expose these failures.
        return _exception_diagnostic(
            "WARN", "certifi CA bundle is unavailable", "capability_unavailable", err
        )


def _core_dsl_parse() -> CheckOutcome:
    try:
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.dsl.node import StateMachineDSLProgram
        from pyfcstm.dsl.parse import parse_state_machine_dsl

        program = parse_state_machine_dsl(_FUNCTION_DSL)
        rendered = str(program)
        if not isinstance(program, StateMachineDSLProgram):
            return _fail(
                "DSL parser returned an unexpected AST type",
                "dsl_parse_failed",
                expected="StateMachineDSLProgram",
                observed=type(program).__name__,
            )
        required_fragments = ("def int counter = 0;", "state Idle", "Idle -> Done :: Go")
        missing = [fragment for fragment in required_fragments if fragment not in rendered]
        if missing:
            return _fail(
                "DSL AST is missing expected declarations",
                "dsl_parse_failed",
                expected=repr(required_fragments),
                observed="missing={}".format(repr(missing)),
            )
    except ImportError as err:
        # Public parser modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "DSL parser probe failed", "dsl_parse_failed", err)
    except (GrammarParseError, AttributeError, TypeError, ValueError) as err:
        # GrammarParseError is the parser's public diagnostic; shape/type/value
        # failures indicate a broken functional probe path.
        return _exception_diagnostic("FAIL", "DSL parser probe failed", "dsl_parse_failed", err)
    return _pass(
        "parse representative FCSTM text into its typed AST",
        expected="StateMachineDSLProgram with counter, Idle, Done and Go",
        observed="{} characters of canonical DSL".format(len(rendered)),
    )


def _core_model_build() -> CheckOutcome:
    try:
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import StateMachine, load_state_machine_from_text
        from pyfcstm.utils.validate import ModelValidationError

        model = load_state_machine_from_text(_FUNCTION_DSL)
        if not isinstance(model, StateMachine):
            return _fail(
                "model loader returned an unexpected type",
                "model_invalid",
                expected="StateMachine",
                observed=type(model).__name__,
            )
        state_paths = tuple(state.path for state in model.walk_states())
        transitions = model.root_state.transitions
        transition = transitions[1] if len(transitions) > 1 else None
        valid = (
            state_paths == (("Root",), ("Root", "Idle"), ("Root", "Done"))
            and tuple(model.defines) == ("counter",)
            and transition is not None
            and transition.from_state == "Idle"
            and transition.to_state == "Done"
            and transition.event is not None
            and transition.event.name == "Go"
            and len(transition.effects) == 1
        )
        if not valid:
            return _fail(
                "model structure differs from the representative FCSTM input",
                "model_invalid",
                expected="Root.[Idle,Done], counter, Idle->Done::Go with one effect",
                observed="paths={} vars={} transitions={}".format(
                    state_paths, tuple(model.defines), len(transitions)
                ),
            )
    except ImportError as err:
        # Public model/parser modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "model build probe failed", "model_build_failed", err)
    except (
        GrammarParseError,
        ModelValidationError,
        AttributeError,
        TypeError,
        ValueError,
    ) as err:
        # GrammarParseError and ModelValidationError are the documented loader
        # diagnostics; the remaining classes cover malformed model shapes.
        return _exception_diagnostic("FAIL", "model build probe failed", "model_build_failed", err)
    return _pass(
        "load FCSTM text into a usable StateMachine",
        expected="3 states, 1 variable and Idle->Done::Go",
        observed="paths={} counter=0 transition_effects=1".format(state_paths),
    )


def _core_model_roundtrip() -> CheckOutcome:
    try:
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
        from pyfcstm.utils.validate import ModelValidationError

        model = load_state_machine_from_text(_FUNCTION_DSL)
        canonical_dsl = str(model.to_ast_node())
        rebuilt = parse_dsl_node_to_state_machine(model.to_ast_node())
        plantuml = rebuilt.to_plantuml()
        expected_paths = tuple(state.path for state in model.walk_states())
        rebuilt_paths = tuple(state.path for state in rebuilt.walk_states())
        if (
            rebuilt_paths != expected_paths
            or "Idle -> Done :: Go" not in canonical_dsl
            or "@startuml" not in plantuml
            or "root__idle --> root__done" not in plantuml
        ):
            return _fail(
                "model roundtrip lost DSL or PlantUML structure",
                "model_invalid",
                expected="same state paths plus Idle->Done in DSL and PlantUML",
                observed="paths={} dsl_transition={} plantuml_transition={}".format(
                    rebuilt_paths,
                    "Idle -> Done :: Go" in canonical_dsl,
                    "root__idle --> root__done" in plantuml,
                ),
            )
    except ImportError as err:
        # Public model/parser modules can be absent from a damaged installation.
        return _exception_diagnostic(
            "FAIL", "model roundtrip probe failed", "model_roundtrip_failed", err
        )
    except (
        GrammarParseError,
        ModelValidationError,
        AttributeError,
        TypeError,
        ValueError,
    ) as err:
        # Public parse/model diagnostics and malformed conversion shapes are
        # semantic probe failures rather than generic worker exceptions.
        return _exception_diagnostic(
            "FAIL", "model roundtrip probe failed", "model_roundtrip_failed", err
        )
    return _pass(
        "roundtrip model through AST, DSL and PlantUML",
        expected="state paths preserved and Idle->Done rendered twice",
        observed="paths={} dsl_chars={} plantuml_chars={}".format(
            rebuilt_paths, len(canonical_dsl), len(plantuml)
        ),
    )


def _render_expr() -> CheckOutcome:
    try:
        from jinja2 import TemplateError
        from pyfcstm.dsl import BinaryOp, Integer, Name
        from pyfcstm.render import render_expr_node

        rendered = render_expr_node(
            BinaryOp(Name("counter"), "+", Integer("1")), lang_style="python"
        )
        if rendered != "counter + 1":
            return _fail(
                "expression renderer returned unexpected output",
                "render_failed",
                expected="counter + 1",
                observed=rendered,
            )
    except ImportError as err:
        # Public renderer modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "expression renderer probe failed", "render_failed", err)
    except (TemplateError, AttributeError, KeyError, TypeError, ValueError, RuntimeError) as err:
        # TemplateError is the renderer's public template diagnostic; the
        # remaining classes cover style lookup and malformed AST values.
        return _exception_diagnostic("FAIL", "expression renderer probe failed", "render_failed", err)
    return _pass(
        "render BinaryOp(counter + 1) with the Python expression style",
        expected="counter + 1",
        observed=rendered,
    )


def _render_statement() -> CheckOutcome:
    try:
        from jinja2 import TemplateError
        from pyfcstm.dsl import BinaryOp, Integer, Name, OperationAssignment
        from pyfcstm.render import render_stmt_nodes

        statement = OperationAssignment(
            "counter", BinaryOp(Name("counter"), "+", Integer("1"))
        )
        rendered = render_stmt_nodes([statement], lang_style="python")
        if rendered != "counter = counter + 1":
            return _fail(
                "statement renderer returned unexpected output",
                "render_failed",
                expected="counter = counter + 1",
                observed=rendered,
            )
    except ImportError as err:
        # Public renderer modules can be absent from a damaged installation.
        return _exception_diagnostic(
            "FAIL", "statement rendering environment failed", "render_failed", err
        )
    except (TemplateError, AttributeError, KeyError, TypeError, ValueError) as err:
        # TemplateError is the renderer's public template diagnostic; the
        # remaining classes cover style lookup and malformed AST values.
        return _exception_diagnostic(
            "FAIL", "statement rendering environment failed", "render_failed", err
        )
    return _pass(
        "render counter assignment with the Python statement style",
        expected="counter = counter + 1",
        observed=rendered,
    )


def _template_python() -> CheckOutcome:
    try:
        import runpy

        from jinja2 import TemplateError
        from yaml import YAMLError
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.render import StateMachineCodeRenderer
        from pyfcstm.template import extract_template
        from pyfcstm.utils.validate import ModelValidationError

        with tempfile.TemporaryDirectory(prefix="pyfcstm-template-python-") as directory:
            template_dir = extract_template("python", str(Path(directory) / "template"))
            output_dir = Path(directory) / "generated"
            StateMachineCodeRenderer(template_dir).render(
                load_state_machine_from_text(_FUNCTION_DSL),
                str(output_dir),
                clear_previous_directory=True,
            )
            machine_file = output_dir / "machine.py"
            namespace = runpy.run_path(str(machine_file))
            machine_class = namespace.get("RootMachine")
            if not isinstance(machine_class, type):
                return _fail(
                    "generated Python runtime class is missing",
                    "template_invalid",
                    expected="RootMachine class",
                    observed=type(machine_class).__name__,
                )
            runtime = machine_class()
            runtime.cycle()
            runtime.cycle(["Root.Idle.Go"])
            observed = "state={} counter={}".format(
                ".".join(runtime.current_state_path), runtime.vars.get("counter")
            )
            if runtime.current_state_path != ("Root", "Done") or runtime.vars.get("counter") != 1:
                return _fail(
                    "generated Python runtime produced unexpected behavior",
                    "template_invalid",
                    expected="state=Root.Done counter=1",
                    observed=observed,
                )
    except ImportError as err:
        # Public template/runtime modules can be absent from a damaged installation.
        return _exception_diagnostic(
            "FAIL", "python template runtime probe failed", "template_invalid", err
        )
    except (
        TemplateError,
        YAMLError,
        GrammarParseError,
        ModelValidationError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
    ) as err:
        # Public template, YAML, DSL, and model diagnostics plus filesystem and
        # generated-runtime failures remain typed functional outcomes.
        return _exception_diagnostic(
            "FAIL", "python template runtime probe failed", "template_invalid", err
        )
    return _pass(
        "extract, render, import and execute the built-in Python template",
        expected="Go moves Root.Idle to Root.Done and counter 0->1",
        observed=observed,
    )


def _template_catalog() -> CheckOutcome:
    try:
        from jinja2 import TemplateError
        from yaml import YAMLError
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.render import StateMachineCodeRenderer
        from pyfcstm.template import extract_template, list_templates
        from pyfcstm.utils.validate import ModelValidationError

        names = list_templates()
        if not names:
            return _fail("built-in template catalog is empty", "template_missing")
        model = load_state_machine_from_text("state Root;")
        generated = {}
        with tempfile.TemporaryDirectory(prefix="pyfcstm-template-catalog-") as directory:
            for name in names:
                template_dir = extract_template(
                    name, str(Path(directory) / "templates" / name)
                )
                output_dir = Path(directory) / "outputs" / name
                StateMachineCodeRenderer(template_dir).render(
                    model, str(output_dir), clear_previous_directory=True
                )
                files = tuple(
                    path.name
                    for path in output_dir.rglob("*")
                    if path.is_file() and path.stat().st_size > 0
                )
                if not files:
                    return _fail(
                        "built-in template rendered no non-empty files",
                        "template_invalid",
                        expected="at least one non-empty output file",
                        observed="template={}".format(name),
                    )
                generated[name] = len(files)
    except ImportError as err:
        # Public template/renderer modules can be absent from a damaged installation.
        return _exception_diagnostic(
            "FAIL", "built-in template catalog probe failed", "template_invalid", err
        )
    except (
        TemplateError,
        YAMLError,
        GrammarParseError,
        ModelValidationError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as err:
        # Public catalog/template/YAML/model diagnostics and filesystem work
        # remain typed functional outcomes.
        return _exception_diagnostic(
            "FAIL", "built-in template catalog probe failed", "template_invalid", err
        )
    return _pass(
        "extract and render every built-in template",
        expected="non-empty outputs for every catalog entry",
        observed=repr(generated),
    )


def _simulate_cycle() -> CheckOutcome:
    try:
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.simulate import SimulationRuntime
        from pyfcstm.utils.validate import ModelValidationError

        runtime = SimulationRuntime(load_state_machine_from_text(_FUNCTION_DSL))
        runtime.cycle()
        initial = (runtime.current_state.path, dict(runtime.vars))
        runtime.cycle(["Root.Idle.Go"])
        observed = "initial={}/{} final={}/{}".format(
            ".".join(initial[0]),
            initial[1].get("counter"),
            ".".join(runtime.current_state.path),
            runtime.vars.get("counter"),
        )
        if initial != (("Root", "Idle"), {"counter": 0}) or (
            runtime.current_state.path != ("Root", "Done")
            or runtime.vars.get("counter") != 1
        ):
            return _fail(
                "simulation runtime produced unexpected state or variables",
                "simulation_failed",
                expected="Root.Idle/0 -> Go -> Root.Done/1",
                observed=observed,
            )
    except ImportError as err:
        # Public model/runtime modules can be absent from a damaged installation.
        return _exception_diagnostic(
            "FAIL", "simulation cycle probe failed", "simulation_failed", err
        )
    except (
        GrammarParseError,
        ModelValidationError,
        AttributeError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as err:
        # Public model/parser diagnostics and runtime construction/cycle errors
        # remain typed functional outcomes.
        return _exception_diagnostic(
            "FAIL", "simulation cycle probe failed", "simulation_failed", err
        )
    return _pass(
        "initialize, deliver Go, and observe state plus variables",
        expected="Root.Idle/0 -> Root.Done/1",
        observed=observed,
    )


def _solver_translation() -> CheckOutcome:
    try:
        from pyfcstm.model import BinaryOp, Integer, Variable
        from pyfcstm.solver import expr_to_z3, solve
        import z3

        x = z3.Int("x")
        expression = BinaryOp(x=Variable("x"), op="+", y=Integer(5))
        translated = expr_to_z3(expression, {"x": x})
        result = solve([translated == 10], max_solutions=1)
        observed = "status={} x={}".format(
            result.status,
            result.solutions[0].get("x") if result.solutions else None,
        )
        if result.status != "sat" or not result.solutions or result.solutions[0].get("x") != 5:
            return _fail(
                "translated solver expression produced an unexpected model",
                "solver_translation_failed",
                expected="status=sat x=5",
                observed=observed,
            )
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as err:
        # Public solver imports, translation, and native Z3 calls expose these failures.
        return _exception_diagnostic(
            "FAIL", "solver translation probe failed", "solver_translation_failed", err
        )
    return _pass(
        "translate x + 5 and solve translated == 10",
        expected="status=sat x=5",
        observed=observed,
    )


def _verify_solve() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.entry.cli import cli
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.utils.validate import ModelValidationError
        from pyfcstm.verify import run_inspect_algorithms

        results = run_inspect_algorithms(
            load_state_machine_from_text("state Root;"),
            max_complexity_tier="smt_linear",
        )
        kinds = {result.algorithm_name: result.result_kind for result in results}
        expected_kinds = {
            "topological_reachable_set": "sat",
            "composite_init_guards_incomplete": "unsat",
        }
        if any(kinds.get(name) != kind for name, kind in expected_kinds.items()):
            return _fail(
                "verify algorithms returned unexpected SAT/UNSAT results",
                "verify_failed",
                expected=repr(expected_kinds),
                observed=repr({name: kinds.get(name) for name in expected_kinds}),
            )
        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-inspect-") as directory:
            source = Path(directory) / "machine.fcstm"
            source.write_text("state Root;\n", encoding="utf-8")
            arguments = [
                "inspect",
                "-i",
                str(source),
                "--format",
                "json",
                "--enable-verify",
                "--max-complexity-tier",
                "smt_linear",
            ]
            cli_result = CliRunner().invoke(cli, arguments)
            if cli_result.exit_code != 0:
                return _click_failure(arguments, cli_result)
            inspect_payload = json.loads(cli_result.output)
            if inspect_payload.get("root_state_path") != "Root":
                return _fail(
                    "CLI inspect returned an unexpected report",
                    "cli_failed",
                    expected="root_state_path=Root",
                    observed=repr(inspect_payload.get("root_state_path")),
                )
    except ImportError as err:
        # Public verify/CLI/model modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "verify and inspect probe failed", "verify_failed", err)
    except (
        GrammarParseError,
        ModelValidationError,
        OSError,
        AttributeError,
        TypeError,
        ValueError,
    ) as err:
        # Public parser/model diagnostics, filesystem access, JSON parsing, and
        # typed verify results remain semantic failures.
        return _exception_diagnostic("FAIL", "verify and inspect probe failed", "verify_failed", err)
    return _pass(
        "run verify SAT/UNSAT algorithms and the inspect CLI",
        expected=repr(expected_kinds),
        observed="{}; inspect root=Root".format(repr(expected_kinds)),
    )


def _cli_help() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        arguments = ["--help"]
        result = CliRunner().invoke(cli, arguments)
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        # Click imports and command construction expose these documented failures.
        return _exception_diagnostic("FAIL", "CLI help probe failed", "cli_failed", err)
    if result.exit_code != 0:
        return _click_failure(arguments, result)
    commands = ("bmc", "generate", "inspect", "plantuml", "simulate", "visualize")
    missing = [command for command in commands if "  {} ".format(command) not in result.output]
    if missing:
        return _fail(
            "CLI help is missing expected top-level commands",
            "cli_failed",
            expected=repr(commands),
            observed="missing={}".format(repr(missing)),
            evidence=result.output,
        )
    return _pass(
        "load CLI help and enumerate every top-level command",
        expected=repr(commands),
        observed="all 6 commands registered",
    )


def _cli_generate() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-") as directory:
            root = Path(directory)
            source = root / "machine.fcstm"
            output = root / "generated"
            source.write_text(_FUNCTION_DSL, encoding="utf-8")
            arguments = [
                "generate",
                "-i",
                str(source),
                "--template",
                "python",
                "-o",
                str(output),
            ]
            result = CliRunner().invoke(cli, arguments)
            if result.exit_code != 0:
                return _click_failure(arguments, result)
            machine_file = output / "machine.py"
            if not machine_file.is_file() or "class RootMachine" not in machine_file.read_text(
                encoding="utf-8"
            ):
                return _fail(
                    "CLI generate produced no usable machine.py",
                    "cli_failed",
                    expected="non-empty machine.py containing RootMachine",
                    observed=str(machine_file),
                )
            generated_size = machine_file.stat().st_size
    except (ImportError, OSError, AttributeError, TypeError, ValueError) as err:
        # Click imports, temporary files, generation, and output reads expose these failures.
        return _exception_diagnostic("FAIL", "CLI generate probe failed", "cli_failed", err)
    return _pass(
        "run CLI generate with the built-in Python template",
        expected="machine.py containing RootMachine",
        observed="generated {} bytes".format(generated_size),
    )


def _cli_simulate() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-") as directory:
            source = Path(directory) / "machine.fcstm"
            source.write_text(_FUNCTION_DSL, encoding="utf-8")
            arguments = [
                "simulate",
                "-i",
                str(source),
                "-e",
                "cycle; cycle Root.Idle.Go; current",
                "--no-color",
            ]
            result = CliRunner().invoke(cli, arguments)
            if result.exit_code != 0:
                return _click_failure(arguments, result)
            if "Current State: Root.Done" not in result.output or "counter = 1" not in result.output:
                return _fail(
                    "CLI simulate returned unexpected state or variables",
                    "cli_failed",
                    expected="Current State: Root.Done and counter = 1",
                    observed=result.output,
                )
    except (ImportError, OSError, AttributeError, TypeError, ValueError) as err:
        # Click imports, temporary files, and batch simulation expose these failures.
        return _exception_diagnostic("FAIL", "CLI simulate probe failed", "cli_failed", err)
    return _pass(
        "run CLI batch simulation through the Go transition",
        expected="Root.Done with counter=1",
        observed="Current State: Root.Done; counter = 1",
    )


def _cli_plantuml() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-") as directory:
            source = Path(directory) / "machine.fcstm"
            source.write_text(_FUNCTION_DSL, encoding="utf-8")
            arguments = ["plantuml", "-i", str(source)]
            result = CliRunner().invoke(cli, arguments)
            if result.exit_code != 0:
                return _click_failure(arguments, result)
            required = ("@startuml", "root__idle --> root__done", "counter")
            missing = [fragment for fragment in required if fragment not in result.output]
            if missing:
                return _fail(
                    "CLI plantuml returned incomplete PlantUML text",
                    "cli_failed",
                    expected=repr(required),
                    observed="missing={}".format(repr(missing)),
                    evidence=result.output,
                )
    except (ImportError, OSError, AttributeError, TypeError, ValueError) as err:
        # Click imports, temporary files, and PlantUML text generation fail here.
        return _exception_diagnostic("FAIL", "CLI plantuml probe failed", "cli_failed", err)
    return _pass(
        "run CLI PlantUML text generation without Java or a JAR",
        expected="@startuml, Idle->Done and counter legend",
        observed="{} characters".format(len(result.output)),
    )


def _bmc_query_parse() -> CheckOutcome:
    try:
        from pyfcstm.bmc.errors import BmcError
        from pyfcstm.bmc.query import BmcQuery
        from pyfcstm.bmc.parse import parse_bmc_query

        query = parse_bmc_query(_BMC_REACH_QUERY)
        observed = "type={} kind={} bound={}".format(
            type(query).__name__,
            getattr(getattr(query, "property", None), "kind", None),
            getattr(getattr(query, "property", None), "bound", None),
        )
        if (
            not isinstance(query, BmcQuery)
            or query.property.kind != "reach"
            or query.property.bound != 1
            or not str(query).endswith(_BMC_REACH_QUERY)
        ):
            return _fail(
                "BMC query parser returned unexpected query",
                "bmc_parse_failed",
                expected="BmcQuery kind=reach bound=1 with canonical source",
                observed=observed,
            )
    except ImportError as err:
        # Public BMC parser modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "BMC query parser probe failed", "bmc_parse_failed", err)
    except (BmcError, AttributeError, TypeError, ValueError) as err:
        # BmcError covers all public BMC parse/query diagnostics; the remaining
        # classes cover malformed result shapes and primitive arguments.
        return _exception_diagnostic("FAIL", "BMC query parser probe failed", "bmc_parse_failed", err)
    return _pass(
        "parse FBMCQ reach text into a typed query model",
        expected="BmcQuery kind=reach bound=1",
        observed=observed,
    )


def _bmc_prepare() -> CheckOutcome:
    """Compile a BMC formula while proving no solver is started."""
    try:
        import z3
        from pyfcstm.bmc.errors import BmcError
        from pyfcstm.bmc.parse import parse_bmc_query
        from pyfcstm.bmc.pipeline import compile_bmc_query
        from pyfcstm.bmc.properties import BmcPropertyFormula
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.utils.validate import ModelValidationError

        calls = {"construct": 0, "check": 0}
        original_solver = z3.Solver
        original_check = getattr(original_solver, "check", None)

        def _forbidden_solver(*args, **kwargs):
            calls["construct"] += 1
            raise AssertionError("BMC preparation constructed a solver")

        def _forbidden_check(*args, **kwargs):
            calls["check"] += 1
            raise AssertionError("BMC preparation called Solver.check")

        z3.Solver = _forbidden_solver
        if original_check is not None:
            original_solver.check = _forbidden_check
        try:
            formula = compile_bmc_query(
                load_state_machine_from_text("state Root;"),
                parse_bmc_query(_BMC_REACH_QUERY),
            )
        finally:
            z3.Solver = original_solver
            if original_check is not None:
                original_solver.check = original_check
        if (
            not isinstance(formula, BmcPropertyFormula)
            or not hasattr(formula, "solve_formula")
            or formula.kind != "reach"
            or formula.polarity != "witness"
        ):
            return _fail(
                "BMC formula is not the expected solve-ready type",
                "bmc_prepare_failed",
                expected="BmcPropertyFormula kind=reach polarity=witness",
                observed="type={} kind={} polarity={}".format(
                    type(formula).__name__,
                    getattr(formula, "kind", None),
                    getattr(formula, "polarity", None),
                ),
            )
    except ImportError as err:
        # Public BMC/Z3 modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "BMC prepare probe failed", "bmc_prepare_failed", err)
    except (
        BmcError,
        GrammarParseError,
        ModelValidationError,
        AttributeError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as err:
        # BmcError covers documented query/domain/build failures; the remaining
        # classes cover malformed objects and the temporary Z3 monitor.
        return _exception_diagnostic("FAIL", "BMC prepare probe failed", "bmc_prepare_failed", err)
    except AssertionError as err:
        # The local monitor raises only when preparation constructs or checks a solver.
        return _exception_diagnostic(
            "FAIL", "BMC preparation started a solver", "bmc_prepare_solved", err
        )
    return _pass(
        "compile StateMachine + parsed BmcQuery without solving",
        expected="BmcPropertyFormula reach/witness; Solver construct/check=0/0",
        observed="type={} kind={} polarity={}; Solver construct/check=0/0".format(
            type(formula).__name__, formula.kind, formula.polarity
        ),
    )


def _bmc_solve() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli
        from pyfcstm.bmc.errors import BmcError
        from pyfcstm.bmc.pipeline import compile_bmc_query
        from pyfcstm.bmc.witness import solve_bmc_property
        from pyfcstm.dsl.error import GrammarParseError
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.utils.validate import ModelValidationError

        formula = compile_bmc_query(
            load_state_machine_from_text("state Root;"),
            _BMC_REACH_QUERY,
        )
        result = solve_bmc_property(formula)
        if (
            result.status != "sat"
            or result.property_satisfied is not True
            or result.outcome != "witness_found"
            or not result.witness_found
        ):
            return _fail(
                "BMC reach probe has unexpected polarity",
                "bmc_solve_failed",
                expected="sat/property_satisfied/witness_found",
                observed="{}/{}/{}".format(
                    result.status, result.property_satisfied, result.outcome
                ),
            )
        terminated = solve_bmc_property(
            compile_bmc_query(
                load_state_machine_from_text("state Root;"),
                _BMC_TERMINATED_QUERY,
            )
        )
        forbidden = solve_bmc_property(
            compile_bmc_query(
                load_state_machine_from_text("state Root;"),
                _BMC_FORBID_QUERY,
            )
        )
        if (
            terminated.status != "unsat"
            or terminated.property_satisfied is not False
            or terminated.outcome != "no_witness"
            or forbidden.status != "sat"
            or forbidden.property_satisfied is not False
            or forbidden.outcome != "property_violated"
        ):
            return _fail(
                "BMC polarity probe has unexpected result",
                "bmc_solve_failed",
                expected="reach active=sat/true; reach terminated=unsat/false; forbid active=sat/false",
                observed="reach={}/{}/{} terminated={}/{}/{} forbid={}/{}/{}".format(
                    result.status,
                    result.property_satisfied,
                    result.outcome,
                    terminated.status,
                    terminated.property_satisfied,
                    terminated.outcome,
                    forbidden.status,
                    forbidden.property_satisfied,
                    forbidden.outcome,
                ),
            )
        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-bmc-") as directory:
            model_file = Path(directory) / "machine.fcstm"
            query_file = Path(directory) / "property.fbmcq"
            model_file.write_text("state Root;\n", encoding="utf-8")
            query_file.write_text(_BMC_REACH_QUERY + "\n", encoding="utf-8")
            arguments = [
                "bmc",
                "-i",
                str(model_file),
                "-q",
                str(query_file),
                "--json",
                "--color",
                "never",
            ]
            cli_result = CliRunner().invoke(cli, arguments)
            if cli_result.exit_code != 0:
                return _click_failure(arguments, cli_result)
            payload = json.loads(cli_result.output)
            cli_solve = payload.get("result", {})
            if (
                payload.get("schema_version") != "bmc-cli/v1"
                or cli_solve.get("status") != "sat"
                or cli_solve.get("property_satisfied") is not True
                or cli_solve.get("outcome") != "witness_found"
            ):
                return _fail(
                    "BMC CLI returned an unexpected JSON result",
                    "bmc_solve_failed",
                    expected="bmc-cli/v1 sat/true/witness_found",
                    observed=repr(
                        {
                            "schema_version": payload.get("schema_version"),
                            "status": cli_solve.get("status"),
                            "property_satisfied": cli_solve.get("property_satisfied"),
                            "outcome": cli_solve.get("outcome"),
                        }
                    ),
                )
    except ImportError as err:
        # Public BMC/CLI modules can be absent from a damaged installation.
        return _exception_diagnostic("FAIL", "BMC solve probe failed", "bmc_solve_failed", err)
    except (
        BmcError,
        GrammarParseError,
        ModelValidationError,
        AttributeError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as err:
        # BmcError covers documented compile/solve/replay failures; the
        # remaining classes cover malformed CLI and JSON result shapes.
        return _exception_diagnostic("FAIL", "BMC solve probe failed", "bmc_solve_failed", err)
    return _pass(
        "solve three property polarities and run the BMC CLI",
        expected="reach active=sat/true; terminated=unsat/false; forbid=sat/false",
        observed="sat/true/witness; unsat/false/no_witness; sat/false/violated; CLI=sat/true",
    )


def _bmc_closure() -> CheckOutcome:
    modules = (
        "pyfcstm.bmc.binding",
        "pyfcstm.bmc.domain",
        "pyfcstm.bmc.engine",
        "pyfcstm.bmc.parse",
        "pyfcstm.bmc.pipeline",
        "pyfcstm.bmc.properties",
        "pyfcstm.bmc.relation",
        "pyfcstm.bmc.witness",
    )
    for module in modules:
        outcome = _probe_import(module)
        if outcome.status != "PASS":
            return outcome
    return _pass(
        "import the complete BMC lazy-module closure",
        expected="8 binding-to-witness modules",
        observed="8 modules imported",
    )


def _java() -> CheckOutcome:
    executable = shutil.which("java")
    if executable is None:
        return _warn(
            "Java executable is unavailable",
            "capability_unavailable",
            expected="java executable on PATH",
            observed="not found",
            remediation="install a compatible JRE to enable local image rendering",
        )
    command = [executable, "-version"]
    try:
        completed = _run_subprocess_bounded(
            command,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        # Process creation can fail and a damaged Java executable can hang.
        return _exception_diagnostic(
            "WARN",
            "Java executable is unavailable",
            "capability_unavailable",
            err,
            expected="java -version exits 0 within 15 seconds",
            remediation="repair the configured JRE or remove the broken executable from PATH",
            evidence_prefix=_process_evidence(
                command,
                stdout=getattr(err, "output", None),
                stderr=getattr(err, "stderr", None),
            ),
        )
    if completed.returncode != 0:
        return _warn(
            "Java executable returned a non-zero status",
            "capability_unavailable",
            expected="returncode=0",
            observed="returncode={}".format(completed.returncode),
            evidence=_process_evidence(
                command,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            ),
            remediation="repair the configured JRE or remove the broken executable from PATH",
        )
    version_output = _decode_process_output(completed.stdout + completed.stderr).strip()
    return _pass(
        "run java -version",
        expected="returncode=0 and version output",
        observed="{}; {}".format(executable, version_output or "no version text"),
    )


def _plantuml_jar_candidates() -> Tuple[Path, ...]:
    """Return PlantUML JAR candidates in the same order as the CLI."""
    configured = os.environ.get(_PLANTUML_JAR_ENV)
    fallback = (_package_root() / "plantuml.jar", Path.cwd() / "plantuml.jar")
    if configured and configured.strip():
        return (Path(configured).expanduser(),) + fallback
    return fallback


def _configured_plantuml_host() -> str:
    """Return the configured remote host or the CLI's official fallback."""
    configured = os.environ.get(_PLANTUML_HOST_ENV)
    if configured and configured.strip():
        return configured.strip()
    return _OFFICIAL_PLANTUML_HOST


def _remote_host_endpoint():
    """Parse the configured PlantUML endpoint and validate its transport."""
    host = _configured_plantuml_host()
    parsed = urlsplit(host)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            "{} must be an absolute http(s) URL: {!r}".format(
                _PLANTUML_HOST_ENV, host
            )
        )
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, parsed, port


def _plantuml_jar() -> CheckOutcome:
    candidates = _plantuml_jar_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return _pass(
                "locate the optional PlantUML JAR",
                expected="regular file",
                observed="{} ({} bytes)".format(candidate, candidate.stat().st_size),
            )
    return _warn(
        "PlantUML JAR is unavailable",
        "capability_unavailable",
        expected=repr([str(candidate) for candidate in candidates]),
        observed="no candidate is a regular file",
        remediation="set up plantuml.jar only when local image rendering is required",
    )


def _python_stack() -> CheckOutcome:
    return _optional_import("plantumlcli")


def _visual_local_version() -> CheckOutcome:
    java = shutil.which("java")
    candidates = _plantuml_jar_candidates()
    jar = next((candidate for candidate in candidates if candidate.is_file()), None)
    if java is None or jar is None:
        return _warn(
            "local PlantUML version is unavailable",
            "capability_unavailable",
            expected="java executable and plantuml.jar",
            observed="java={} jar={}".format(java, jar),
            remediation="install Java and configure plantuml.jar for local rendering",
        )
    command = [java, "-jar", str(jar), "-version"]
    try:
        completed = _run_subprocess_bounded(
            command,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        # Process creation can fail and Java/JAR startup can exceed the deadline.
        return _exception_diagnostic(
            "WARN",
            "local PlantUML version is unavailable",
            "capability_unavailable",
            err,
            expected="PlantUML -version exits 0 within 15 seconds",
            remediation="repair Java/plantuml.jar or use the optional remote renderer",
            evidence_prefix=_process_evidence(
                command,
                stdout=getattr(err, "output", None),
                stderr=getattr(err, "stderr", None),
            ),
        )
    output = completed.stdout + completed.stderr
    if completed.returncode != 0 or not output.strip():
        return _warn(
            "local PlantUML version is unavailable",
            "capability_unavailable",
            expected="returncode=0 and non-empty version output",
            observed="returncode={} output_bytes={}".format(
                completed.returncode, len(output)
            ),
            evidence=_process_evidence(
                command,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            ),
            remediation="repair Java/plantuml.jar or use the optional remote renderer",
        )
    return _pass(
        "run PlantUML -version through Java",
        expected="returncode=0 and non-empty version output",
        observed=output.decode("utf-8", "backslashreplace").strip(),
    )


def _visual_local_render() -> CheckOutcome:
    java = shutil.which("java")
    candidates = _plantuml_jar_candidates()
    jar = next((candidate for candidate in candidates if candidate.is_file()), None)
    if java is None or jar is None:
        return _warn(
            "local image rendering requires optional Java/PlantUML",
            "capability_unavailable",
            expected="java executable and plantuml.jar",
            observed="java={} jar={}".format(java, jar),
            remediation="install Java and configure plantuml.jar for local rendering",
        )
    source = b"@startuml\nAlice -> Bob\n@enduml\n"
    command = [java, "-jar", str(jar), "-pipe", "-tpng"]
    try:
        completed = _run_subprocess_bounded(
            command,
            input_data=source,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        # Process creation can fail and image rendering can exceed the deadline.
        return _exception_diagnostic(
            "WARN",
            "local PlantUML rendering is unavailable",
            "capability_unavailable",
            err,
            expected="PNG bytes within 15 seconds",
            remediation="repair Java/plantuml.jar or use the optional remote renderer",
            evidence_prefix=_process_evidence(
                command,
                stdout=getattr(err, "output", None),
                stderr=getattr(err, "stderr", None),
            ),
        )
    if completed.returncode != 0 or not completed.stdout:
        return _warn(
            "local PlantUML rendering is unavailable",
            "capability_unavailable",
            expected="returncode=0 and non-empty PNG stdout",
            observed="returncode={} stdout_bytes={}".format(
                completed.returncode, len(completed.stdout)
            ),
            evidence=_process_evidence(
                command,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            ),
            remediation="repair Java/plantuml.jar or use the optional remote renderer",
        )
    return _pass(
        "render Alice -> Bob through local PlantUML -pipe -tpng",
        expected="returncode=0 and non-empty PNG stdout",
        observed="{} image bytes".format(len(completed.stdout)),
    )


def _visual_remote_tls() -> CheckOutcome:
    if os.environ.get("PYFCSTM_SELFCHECK_NETWORK") != "1":
        return CheckOutcome(
            "SKIP",
            "remote network checks are disabled by default",
            reason="network_disabled",
        )
    try:
        host, parsed, port = _remote_host_endpoint()
        address = (parsed.hostname, port)
        if parsed.scheme == "https":
            if ssl is None:
                raise ImportError("Python ssl module is unavailable")
            context = ssl.create_default_context()
            with socket.create_connection(address, timeout=5.0) as raw:
                with context.wrap_socket(raw, server_hostname=parsed.hostname) as tls:
                    observed = "transport=tls host={} version={}".format(
                        host, tls.version() or "TLS"
                    )
        else:
            with socket.create_connection(address, timeout=5.0):
                observed = "transport=plain host={} endpoint=reachable".format(host)
    except (AttributeError, ImportError, OSError, ValueError) as err:
        # URL parsing, socket setup, and TLS certificate validation expose these failures.
        return _exception_diagnostic(
            "WARN",
            "PlantUML remote service is unavailable",
            "capability_unavailable",
            err,
            expected="configured PlantUML host is reachable",
            remediation="check DNS, firewall, certificates, and the explicit --network opt-in",
        )
    return _pass(
        "probe the configured PlantUML remote service",
        expected="configured HTTP(S) endpoint is reachable",
        observed=observed,
    )


def _visual_remote_render() -> CheckOutcome:
    if os.environ.get("PYFCSTM_SELFCHECK_NETWORK") != "1":
        return CheckOutcome(
            "SKIP", "remote rendering requires --network", reason="network_disabled"
        )
    host = _configured_plantuml_host()
    source = "@startuml\nAlice -> Bob\n@enduml\n"
    try:
        from pyfcstm.entry.visualize import create_remote_plantuml_backend
        from plantumlcli.models.base import PlantumlResourceType

        backend = create_remote_plantuml_backend(remote_host=host)
        try:
            backend.check()
        except UnicodeDecodeError:
            # PlantUML PicoWeb may return a binary PNG for its root page;
            # validate the real render below instead of decoding that page.
            pass
        with tempfile.TemporaryDirectory(prefix="pyfcstm-plantuml-") as directory:
            output = Path(directory) / "selfcheck.png"
            backend.dump(str(output), PlantumlResourceType.PNG, source)
            payload = output.read_bytes()
    except (AttributeError, ImportError, OSError, ValueError) as err:
        # AttributeError/ValueError: plantumlcli can reject an unexpected
        # service homepage shape; ImportError: optional backend unavailable;
        # OSError: request or temporary output failure. Unexpected classes
        # still propagate so implementation bugs remain visible.
        return _exception_diagnostic(
            "WARN",
            "remote PlantUML rendering is unavailable",
            "capability_unavailable",
            err,
            expected="configured PlantUML service returns a PNG for Alice -> Bob",
            remediation="check network policy and the remote PlantUML service",
        )
    if not payload.startswith(_PNG_SIGNATURE):
        return _warn(
            "remote PlantUML rendering returned an invalid image",
            "capability_unavailable",
            expected="PNG signature {}".format(_PNG_SIGNATURE),
            observed="host={} response_bytes={} signature={!r}".format(
                host, len(payload), payload[:8]
            ),
            remediation="check the configured PlantUML service and renderer endpoint",
        )
    return _pass(
        "render Alice -> Bob through the configured PlantUML service",
        expected="PNG signature and non-empty image",
        observed="host={} transport={} PNG response_bytes={} signature=valid".format(
            host, "tls" if urlsplit(host).scheme == "https" else "plain", len(payload)
        ),
    )


def _resource_random_user_agent() -> CheckOutcome:
    return _optional_import("random_user_agent")


def _resource_pygments() -> CheckOutcome:
    return _probe_import("pygments")


def _resource_unidecode() -> CheckOutcome:
    try:
        from unidecode import unidecode

        samples = ("é", "Ж", "中")
        observed = tuple(unidecode(item) for item in samples)
        if not all(observed):
            return _fail("Unidecode tables returned an empty mapping", "tables_invalid")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        # Unidecode import and dynamic mapping-table lookup expose these failures.
        return _exception_diagnostic(
            "FAIL", "Unidecode tables are unavailable", "tables_invalid", err
        )
    return _pass(
        "transliterate samples from Latin, Cyrillic and CJK tables",
        expected="three non-empty transliterations",
        observed=repr(observed),
    )


def _make_probe_worker(check_id: str) -> Worker:
    """Bind a fixed check ID to one package-defined probe."""

    probe = _PROBES[check_id]

    def _worker() -> CheckOutcome:
        return probe()

    _worker.__name__ = "worker_{}".format(check_id.replace(".", "_"))
    return _worker


_PROBES: Dict[str, Probe] = {
    "env.python": _env_python,
    "env.os": _env_os,
    "env.locale": _env_locale,
    "env.console": _env_console,
    "env.process": _env_process,
    "env.temp": _env_temp,
    "env.filesystem": _env_filesystem,
    "env.win.loader": partial(_platform_specific, "win"),
    "env.linux.libc": partial(_platform_specific, "linux"),
    "env.macos.runtime": partial(_platform_specific, "darwin"),
    "identity.package": _identity_package,
    "identity.source": _identity_source,
    "identity.build_info_module": _identity_build_info_module,
    "identity.artifact": _identity_artifact,
    "resource.diagnostics.codes": partial(_yaml_resource, "diagnostics/codes.yaml", "diagnostic codes"),
    "resource.diagnostics.schemas": _diagnostics_schemas,
    "resource.templates.index": _template_index,
    "resource.templates.archives": _template_archives,
    "resource.templates.extract": _template_extract,
    "resource.llm.guide": _resource_llm_guide,
    "resource.grammar.fcstm": _grammar_fcstm,
    "resource.grammar.fbmcq": _grammar_fbmcq,
    "resource.pygments": _resource_pygments,
    "resource.random_user_agent": _resource_random_user_agent,
    "native.z3.load": _z3_load,
    "native.z3.solve": _z3_solve,
    "native.lxml.parse": _lxml_parse,
    "native.yaml.backend": _yaml_backend,
    "native.markupsafe.backend": _markupsafe_backend,
    "native.charset_normalizer.backend": _charset_normalizer_backend,
    "native.ssl.certifi": _ssl_certifi,
    "runtime.unidecode.tables": _resource_unidecode,
    "core.dsl.parse": _core_dsl_parse,
    "core.model.build": _core_model_build,
    "core.model.roundtrip": _core_model_roundtrip,
    "core.render.expr": _render_expr,
    "core.render.statement": _render_statement,
    "core.template.python": _template_python,
    "core.template.catalog": _template_catalog,
    "core.simulate.cycle": _simulate_cycle,
    "core.solver.translation": _solver_translation,
    "core.verify.solve": _verify_solve,
    "core.cli.help": _cli_help,
    "core.cli.generate": _cli_generate,
    "core.cli.simulate": _cli_simulate,
    "core.cli.plantuml": _cli_plantuml,
    "bmc.query.parse": _bmc_query_parse,
    "bmc.verification.prepare": _bmc_prepare,
    "bmc.property.solve": _bmc_solve,
    "bmc.module.closure": _bmc_closure,
    "visualize.python_stack": _python_stack,
    "visualize.java": _java,
    "visualize.plantuml_jar": _plantuml_jar,
    "visualize.local_version": _visual_local_version,
    "visualize.local_render": _visual_local_render,
    "visualize.remote_tls": _visual_remote_tls,
    "visualize.remote_render": _visual_remote_render,
}


if set(_PROBES) != set(EXPECTED_CHECK_IDS):  # pragma: no cover - import guard
    raise RuntimeError("self-check probe inventory does not match fixed IDs")


_WORKERS: Dict[str, Worker] = {
    "runtime_metadata": _runtime_metadata,
    "self_dispatch": _artifact_self_dispatch,
}
for _check_id in EXPECTED_CHECK_IDS:
    _WORKERS["check_" + _check_id.replace(".", "_")] = _make_probe_worker(_check_id)


_VISUAL_IDS = frozenset(item for item in EXPECTED_CHECK_IDS if item.startswith("visualize."))
_OPTIONAL_IDS = frozenset(
    {
        "identity.source",
        "identity.build_info_module",
        "identity.artifact",
        "resource.random_user_agent",
        "native.lxml.parse",
        "native.yaml.backend",
        "native.markupsafe.backend",
        "native.charset_normalizer.backend",
        "native.ssl.certifi",
    }
    | _VISUAL_IDS
)


def _timeout_for(check_id: str) -> float:
    group = check_id.split(".", 1)[0]
    if group in ("env", "identity", "resource", "runtime"):
        return 10.0
    if check_id.startswith("core.cli.") or check_id.startswith("core.template."):
        return 30.0
    if group == "native" or group == "core":
        return 20.0
    if group == "visualize":
        return 30.0 if "remote" in check_id else 60.0
    return 30.0


def _prerequisites(check_id: str) -> Tuple[str, ...]:
    explicit = {
        "identity.artifact": ("identity.package",),
        "resource.templates.archives": ("resource.templates.index",),
        "resource.templates.extract": ("resource.templates.archives",),
        "native.z3.solve": ("native.z3.load",),
        "core.template.python": ("resource.templates.extract",),
        "core.template.catalog": ("resource.templates.index",),
        "core.solver.translation": ("native.z3.load",),
        "bmc.verification.prepare": ("bmc.query.parse",),
        "bmc.property.solve": ("bmc.verification.prepare",),
        "visualize.local_render": ("visualize.java", "visualize.plantuml_jar"),
        "visualize.remote_render": ("visualize.remote_tls",),
    }
    return explicit.get(check_id, ())


def get_worker(worker_key: str) -> Worker:
    """Return one statically registered callback.

    :param worker_key: Static worker key.
    :type worker_key: str
    :return: Registered callable.
    :rtype: Worker
    :raises KeyError: If the key is not registered.

    Example::

        >>> callable(get_worker("runtime_metadata"))
        True
    """
    return _WORKERS[worker_key]


def registry_metadata(
    profile: str = "default", explicit_skipped_ids: Iterable[str] = ()
) -> Mapping[str, Any]:
    """Return stable registry metadata for a profile and explicit skips.

    :param profile: ``default``, ``full``, or ``visualize``.
    :type profile: str
    :param explicit_skipped_ids: Fixed IDs intentionally skipped by a caller.
    :type explicit_skipped_ids: Iterable[str]
    :return: JSON-compatible registry metadata.
    :rtype: Mapping[str, Any]
    :raises ValueError: If the profile or an explicit ID is unknown.

    Example::

        >>> registry_metadata("visualize")["schema_version"]
        'pyfcstm-selfcheck-registry/v1'
    """
    if profile not in ("default", "full", "visualize"):
        raise ValueError("unknown self-check profile: {}".format(profile))
    skipped = tuple(explicit_skipped_ids)
    unknown = sorted(set(skipped) - set(EXPECTED_CHECK_IDS))
    if unknown:
        raise ValueError("unknown explicit self-check IDs: {}".format(", ".join(unknown)))
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "version": REGISTRY_VERSION,
        "expected_ids": list(EXPECTED_CHECK_IDS),
        "selected_ids": list(EXPECTED_CHECK_IDS),
        "explicit_skipped_ids": list(skipped),
    }


def selected_specs(
    profile: str = "default",
    explicit_skipped_ids: Iterable[str] = (),
) -> Tuple[CheckSpec, ...]:
    """Return stable compatibility and fixed checks for ``profile``.

    All 57 fixed IDs remain selected even when optional or explicitly skipped;
    the compatibility-only ``runtime.metadata`` result is prepended.  A later
    supervisor layer records the resulting ``SKIP`` state.  This keeps the
    report's result set stable across profiles.

    :param profile: ``default``, ``full``, or ``visualize``.
    :type profile: str
    :param explicit_skipped_ids: IDs intentionally skipped by the caller.
    :type explicit_skipped_ids: Iterable[str]
    :return: Ordered check specifications.
    :rtype: Tuple[CheckSpec, ...]

    Example::

        >>> len(selected_specs("default"))
        58
        >>> len([s for s in selected_specs("default") if s.check_id.startswith("visualize.")])
        7
    """
    explicit_skipped_ids = tuple(explicit_skipped_ids)
    metadata = registry_metadata(profile, explicit_skipped_ids)
    del metadata
    skipped = frozenset(explicit_skipped_ids)
    specs = [
        CheckSpec(
            "runtime.metadata",
            "runtime_metadata",
            title="runtime metadata",
            required=True,
            execution="local",
            timeout_seconds=10.0,
            safety="pure",
        )
    ]
    for check_id in EXPECTED_CHECK_IDS:
        required = check_id not in _OPTIONAL_IDS or profile == "visualize"
        if check_id in skipped:
            required = False
        specs.append(
            CheckSpec(
                check_id,
                "check_" + check_id.replace(".", "_"),
                title=check_id.replace(".", " "),
                required=required,
                prerequisites=_prerequisites(check_id),
                execution="worker",
                timeout_seconds=_timeout_for(check_id),
                safety=("external" if check_id.startswith("visualize.remote") else "blocking" if check_id.startswith("visualize") else "pure"),
                prerequisite_policy=("skip_on_warn" if _prerequisites(check_id) else "allow_warn"),
                explicit_skip=check_id in skipped,
            )
        )
    return tuple(specs)


__all__ = [
    "CAPABILITY_CHECK_IDS",
    "EXPECTED_CHECK_IDS",
    "REGISTRY_SCHEMA_VERSION",
    "REGISTRY_VERSION",
    "get_worker",
    "registry_metadata",
    "selected_specs",
]
