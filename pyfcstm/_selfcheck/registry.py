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
import ssl
import subprocess
import sys
import tempfile
import zipfile
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

from .model import CheckOutcome, CheckSpec


Worker = Callable[[], CheckOutcome]
Probe = Callable[[], CheckOutcome]

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
):
    return CheckOutcome(
        "WARN", summary, reason=reason, expected=expected, observed=observed
    )


def _fail(summary: str, reason: str, expected: Optional[str] = None, observed=None):
    return CheckOutcome(
        "FAIL", summary, reason=reason, expected=expected, observed=observed
    )


def _probe_import(module_name: str, attribute: Optional[str] = None) -> CheckOutcome:
    """Import a package module and optionally verify one exported attribute."""
    try:
        module = importlib.import_module(module_name)
        if attribute is not None:
            getattr(module, attribute)
    except (ImportError, AttributeError) as err:
        return _fail(
            "required import is unavailable",
            "import_unavailable",
            expected=module_name,
            observed="{}: {}".format(type(err).__name__, err),
        )
    return _pass("imported {}".format(module_name), expected=module_name)


def _optional_import(module_name: str, attribute: Optional[str] = None) -> CheckOutcome:
    try:
        module = importlib.import_module(module_name)
        if attribute is not None:
            getattr(module, attribute)
    except (ImportError, AttributeError) as err:
        return _warn(
            "optional dependency is unavailable",
            "capability_unavailable",
            expected=module_name,
            observed="{}: {}".format(type(err).__name__, err),
        )
    return _pass("optional dependency {} is available".format(module_name))


def _path_probe(path: Path, label: str, required: bool = True) -> CheckOutcome:
    if path.is_file():
        return _pass("{} is present".format(label), expected=str(path))
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

    if not getattr(pyfcstm, "__version__", None):
        raise RuntimeError("package version is unavailable")
    return _pass("worker imported pyfcstm and stopped at hidden dispatch")


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
    return _pass("Python runtime is available", observed=sys.version.split()[0])


def _env_os() -> CheckOutcome:
    return _pass("operating-system metadata is available", observed=platform.platform())


def _env_locale() -> CheckOutcome:
    import locale

    encoding = locale.getpreferredencoding(False)
    return _pass("preferred locale encoding is available", observed=encoding)


def _env_console() -> CheckOutcome:
    return _pass(
        "console capability is reportable",
        observed="stdout_tty={} stderr_tty={}".format(
            bool(getattr(sys.stdout, "isatty", lambda: False)()),
            bool(getattr(sys.stderr, "isatty", lambda: False)()),
        ),
    )


def _env_process() -> CheckOutcome:
    return _pass("current process identity is available", observed=str(os.getpid()))


def _env_temp() -> CheckOutcome:
    with tempfile.TemporaryDirectory(prefix="pyfcstm-selfcheck-") as path:
        probe = Path(path) / "probe"
        probe.write_text("ok", encoding="utf-8")
        if probe.read_text(encoding="utf-8") != "ok":
            return _fail("temporary directory roundtrip failed", "temp_roundtrip")
    return _pass("temporary directory is writable")


def _env_filesystem() -> CheckOutcome:
    root = _package_root()
    return _pass("package filesystem is readable", observed=str(root)) if root.is_dir() else _fail("package filesystem is missing", "filesystem_missing")


def _platform_specific(platform_name: str) -> CheckOutcome:
    if sys.platform.startswith(platform_name):
        return _pass("{} platform capability is applicable".format(platform_name))
    return CheckOutcome(
        "SKIP", "{} platform check is not applicable".format(platform_name),
        reason="not_applicable",
    )


def _identity_package() -> CheckOutcome:
    import pyfcstm
    from pyfcstm.config.meta import __VERSION__

    if not pyfcstm.__version__ or pyfcstm.__version__ != __VERSION__:
        return _fail("package version metadata disagrees", "identity_mismatch")
    return _pass("package identity agrees", observed=pyfcstm.__version__)


def _identity_source() -> CheckOutcome:
    from pyfcstm import config

    if config.BUILD_INFO_ERROR:
        return _warn(
            "generated source identity is invalid",
            "identity_invalid",
            observed=config.BUILD_INFO_ERROR,
        )
    try:
        import pyfcstm.config.build_info as build_info
    except ImportError:
        return _warn("source build identity is unavailable", "identity_unavailable")
    fields = ("BUILD_COMMIT", "BUILD_DIRTY", "BUILD_REF")
    missing = [field for field in fields if not hasattr(build_info, field)]
    if missing:
        return _warn("source build identity is incomplete", "identity_incomplete", observed=repr(missing))
    git_dir = _package_root().parent / ".git"
    if not git_dir.exists():
        return _pass("source build identity is readable")
    try:
        live = _live_source_identity()
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as err:
        return _warn("live source identity cannot be read", "identity_unavailable", observed=str(err))
    expected = {
        "commit": getattr(build_info, "BUILD_COMMIT", None),
        "dirty": getattr(build_info, "BUILD_DIRTY", None),
        "ref": getattr(build_info, "BUILD_REF", None),
        "version": getattr(build_info, "BUILD_VERSION", None),
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
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.STDOUT
    ).decode("ascii").strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, stderr=subprocess.STDOUT
    ).decode("utf-8", "replace")
    ref = subprocess.check_output(
        ["git", "symbolic-ref", "--short", "HEAD"], cwd=root, stderr=subprocess.STDOUT
    ).decode("utf-8", "replace").strip()
    from pyfcstm.config.meta import __VERSION__

    return {"commit": commit, "dirty": bool(status), "ref": ref, "version": __VERSION__}


def _identity_build_info_module() -> CheckOutcome:
    try:
        importlib.import_module("pyfcstm.config.build_info")
    except ImportError as err:
        return _warn(
            "generated build-info module is unavailable",
            "identity_unavailable",
            expected="pyfcstm.config.build_info",
            observed="{}: {}".format(type(err).__name__, err),
        )
    except (OSError, SyntaxError, ValueError) as err:
        # OSError: the generated module cannot be read; SyntaxError: its
        # source is malformed; ValueError: its loader rejects the file.
        return _warn(
            "generated build-info module is invalid",
            "identity_invalid",
            expected="valid pyfcstm.config.build_info",
            observed="{}: {}".format(type(err).__name__, err),
        )
    return _pass("generated build-info module is importable")


def _identity_artifact() -> CheckOutcome:
    return _identity_build_info_module()


def collect_dependency_diagnostics() -> Tuple[Mapping[str, Any], ...]:
    """Collect version, import path, and absence diagnostics for dependencies."""
    dependencies = (
        ("antlr4-python3-runtime", "antlr4"),
        ("click", "click"),
        ("jinja2", "jinja2"),
        ("pyyaml", "yaml"),
        ("z3-solver", "z3"),
        ("plantumlcli", "plantumlcli"),
        ("pygments", "pygments"),
        ("unidecode", "unidecode"),
        ("lxml", "lxml"),
        ("certifi", "certifi"),
    )
    diagnostics = []
    for distribution_name, module_name in dependencies:
        version = None
        path = None
        reason = None
        try:
            try:
                from importlib import metadata
            except ImportError:
                import importlib_metadata as metadata
            version = metadata.version(distribution_name)
        except (ImportError, KeyError, OSError, ValueError) as err:
            reason = "version_unavailable:{}".format(type(err).__name__)
        try:
            module = importlib.import_module(module_name)
            path = getattr(module, "__file__", None)
        except (ImportError, AttributeError) as err:
            reason = reason or "missing:{}".format(type(err).__name__)
        diagnostics.append(
            {
                "name": distribution_name,
                "status": "PASS" if path else "WARN",
                "importable": bool(path),
                "version": version,
                "path": path,
                "reason": reason,
                "error": reason,
            }
        )
    return tuple(diagnostics)


def _json_resource(relative: str, label: str) -> CheckOutcome:
    path = _resource(relative)
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as err:
        return _fail("{} is invalid".format(label), "resource_invalid", observed=str(err))
    return _pass("{} is valid".format(label))


def _diagnostics_schemas() -> CheckOutcome:
    """Validate every shipped diagnostics schema, not only the primary one."""
    for relative in ("diagnostics/schema.json", "diagnostics/inspect_llm_report_schema.json"):
        path = _resource(relative)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as err:
            return _fail(
                "diagnostic schema {} is invalid".format(relative),
                "resource_invalid",
                observed=str(err),
            )
        if not isinstance(document, dict):
            return _fail(
                "diagnostic schema {} is not an object".format(relative),
                "schema_invalid",
            )
        if not isinstance(document.get("$schema"), str) or not document["$schema"].startswith(
            "https://json-schema.org/"
        ):
            return _fail(
                "diagnostic schema {} has no JSON Schema dialect".format(relative),
                "schema_invalid",
            )
        if not isinstance(document.get("$id"), str) or not document["$id"]:
            return _fail(
                "diagnostic schema {} has no stable ID".format(relative),
                "schema_invalid",
            )
        if document.get("type") != "object":
            return _fail(
                "diagnostic schema {} has an unexpected root type".format(relative),
                "schema_invalid",
            )
        required = document.get("required")
        properties = document.get("properties")
        if (
            not isinstance(required, list)
            or not required
            or not all(isinstance(item, str) and item for item in required)
            or not isinstance(properties, dict)
            or any(item not in properties for item in required)
        ):
            return _fail(
                "diagnostic schema {} has an invalid required/properties contract".format(relative),
                "schema_invalid",
            )
    return _pass("diagnostic schemas are valid", observed="2 schemas")


def _yaml_resource(relative: str, label: str) -> CheckOutcome:
    path = _resource(relative)
    try:
        import yaml
    except ImportError as err:
        return _fail("{} is invalid".format(label), "resource_invalid", observed=str(err))
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError, yaml.YAMLError) as err:
        return _fail("{} is invalid".format(label), "resource_invalid", observed=str(err))
    return _pass("{} is valid".format(label))


def _template_index() -> CheckOutcome:
    outcome = _json_resource("template/index.json", "template index")
    if outcome.status != "PASS":
        return outcome
    try:
        from pyfcstm.template import list_templates

        names = list_templates()
    except (OSError, ValueError, KeyError, TypeError) as err:
        return _fail("template catalog cannot be loaded", "resource_invalid", observed=str(err))
    return _pass("template catalog is readable", observed=repr(names))


def _template_archives() -> CheckOutcome:
    index = json.loads(_resource("template/index.json").read_text(encoding="utf-8"))
    missing = []
    for item in index.get("templates", []):
        archive = _resource("template") / str(item.get("archive", ""))
        if not archive.is_file():
            missing.append(str(archive))
            continue
        try:
            with zipfile.ZipFile(str(archive)) as handle:
                if handle.testzip() is not None:
                    missing.append(str(archive))
        except (OSError, zipfile.BadZipFile) as err:
            return _fail("template archive is invalid", "archive_invalid", observed=str(err))
    return _fail("template archives are missing", "resource_missing", observed=repr(missing)) if missing else _pass("template archives are readable")


def _template_extract() -> CheckOutcome:
    try:
        from pyfcstm.template import extract_template

        with tempfile.TemporaryDirectory(prefix="pyfcstm-template-") as target:
            extract_template("python", target)
            if not (Path(target) / "python" / "config.yaml").is_file():
                return _fail("python template extraction is incomplete", "extract_invalid")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as err:
        return _fail("python template extraction failed", "extract_failed", observed=str(err))
    return _pass("python template extracts successfully")


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
        return _fail(
            "packaged LLM guide or checksum is invalid",
            "resource_invalid",
            observed="{}: {}".format(type(err).__name__, err),
        )
    return _pass(
        "packaged LLM guides and SHA-256 sidecars are valid",
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
        from pyfcstm.dsl.parse import parse_state_machine_dsl

        parse_state_machine_dsl("state Root;")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("FCSTM grammar probe failed", "grammar_invalid", observed=str(err))
    return _pass("FCSTM grammar parsed a minimal document")


def _grammar_fbmcq() -> CheckOutcome:
    assets = _grammar_assets(_FBMCQ_GRAMMAR_ASSETS, "FBMCQ")
    if assets.status != "PASS":
        return assets
    try:
        from pyfcstm.bmc.parse import parse_bmc_query

        parse_bmc_query('check reach <= 1: active("Root");')
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("FBMCQ grammar probe failed", "grammar_invalid", observed=str(err))
    return _pass("FBMCQ grammar parsed a minimal query")


def _resource_optional_import(module_name: str) -> CheckOutcome:
    return _optional_import(module_name)


def _z3_load() -> CheckOutcome:
    return _probe_import("z3", "Solver")


def _z3_solve() -> CheckOutcome:
    try:
        import z3

        solver = z3.Solver()
        solver.add(z3.Int("selfcheck_x") == 1)
        if solver.check() != z3.sat:
            return _fail("Z3 solver returned an unexpected result", "solver_failed")
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as err:
        return _fail("Z3 solver probe failed", "solver_failed", observed=str(err))
    return _pass("Z3 solver can solve a simple constraint")


def _yaml_backend() -> CheckOutcome:
    try:
        import yaml
    except ImportError as err:
        return _warn("YAML backend is unavailable", "capability_unavailable", observed=str(err))
    try:
        if yaml.safe_load("key: value")["key"] != "value":
            return _warn("YAML backend returned an unexpected value", "capability_unavailable")
    except (AttributeError, TypeError, ValueError, yaml.YAMLError) as err:
        return _warn("YAML backend is unavailable", "capability_unavailable", observed=str(err))
    return _pass("YAML backend parsed a mapping")


def _lxml_parse() -> CheckOutcome:
    try:
        from lxml import etree

        root = etree.fromstring(b"<selfcheck />")
        if root.tag != "selfcheck":
            return _warn("lxml parser returned an unexpected root", "capability_unavailable")
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as err:
        return _warn("lxml parser is unavailable", "capability_unavailable", observed=str(err))
    return _pass("lxml parsed a minimal XML document")


def _markupsafe_backend() -> CheckOutcome:
    try:
        from markupsafe import escape

        if str(escape("<selfcheck>")) != "&lt;selfcheck&gt;":
            return _warn("MarkupSafe returned an unexpected escape", "capability_unavailable")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _warn("MarkupSafe is unavailable", "capability_unavailable", observed=str(err))
    return _pass("MarkupSafe escaped a minimal value")


def _charset_normalizer_backend() -> CheckOutcome:
    try:
        from charset_normalizer import from_bytes

        match = from_bytes(b"self-check").best()
        if match is None:
            return _warn("charset-normalizer found no encoding", "capability_unavailable")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _warn("charset-normalizer is unavailable", "capability_unavailable", observed=str(err))
    return _pass("charset-normalizer detected a byte encoding")


def _ssl_certifi() -> CheckOutcome:
    outcome = _optional_import("certifi", "where")
    if outcome.status != "PASS":
        return outcome
    try:
        import certifi

        path = certifi.where()
        return _path_probe(Path(path), "certifi CA bundle", required=False)
    except (OSError, AttributeError, TypeError, ValueError) as err:
        return _warn("certifi CA bundle is unavailable", "capability_unavailable", observed=str(err))


def _core_dsl_parse() -> CheckOutcome:
    outcome = _probe_import("pyfcstm.dsl.parse", "parse_state_machine_dsl")
    if outcome.status != "PASS":
        return outcome
    try:
        from pyfcstm.dsl.parse import parse_state_machine_dsl

        parse_state_machine_dsl("state Root;")
    except (AttributeError, TypeError, ValueError) as err:
        return _fail("DSL parser probe failed", "dsl_parse_failed", observed=str(err))
    return _pass("DSL parser accepts a minimal state machine")


def _core_model_build() -> CheckOutcome:
    try:
        from pyfcstm.model import StateMachine, load_state_machine_from_text

        model = load_state_machine_from_text("state Root;")
        if not isinstance(model, StateMachine):
            return _fail("model loader returned an unexpected type", "model_invalid")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("model build probe failed", "model_build_failed", observed=str(err))
    return _pass("model builds from DSL text")


def _core_model_roundtrip() -> CheckOutcome:
    try:
        from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine

        model = load_state_machine_from_text("state Root;")
        rebuilt = parse_dsl_node_to_state_machine(model.to_ast_node())
        if not getattr(rebuilt, "root_state", None) or rebuilt.root_state.name != model.root_state.name:
            return _fail("model roundtrip has no root state", "model_invalid")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("model roundtrip probe failed", "model_roundtrip_failed", observed=str(err))
    return _pass("model root state is available")


def _render_expr() -> CheckOutcome:
    try:
        from pyfcstm.model import Integer
        from pyfcstm.render import render_expr_node

        rendered = render_expr_node(Integer(1), lang_style="python")
        if not rendered:
            return _fail("expression renderer returned empty output", "render_failed")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("expression renderer probe failed", "render_failed", observed=str(err))
    return _pass("expression renderer returned output", observed=str(rendered))


def _render_statement() -> CheckOutcome:
    try:
        from pyfcstm.model import Integer, Operation
        from pyfcstm.render import render_stmt_nodes

        rendered = render_stmt_nodes([Operation("counter", Integer(1))], lang_style="python")
        if "counter" not in rendered:
            return _fail("statement renderer returned unexpected output", "render_failed")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("statement rendering environment failed", "render_failed", observed=str(err))
    return _pass("statement rendering environment is available")


def _template_python() -> CheckOutcome:
    try:
        from pyfcstm.template import has_template

        if not has_template("python"):
            return _fail("python built-in template is missing", "template_missing")
    except (OSError, ValueError, KeyError, TypeError) as err:
        return _fail("python template catalog probe failed", "template_invalid", observed=str(err))
    return _pass("python built-in template is registered")


def _template_catalog() -> CheckOutcome:
    try:
        from pyfcstm.template import list_templates

        names = list_templates()
        if not names:
            return _fail("built-in template catalog is empty", "template_missing")
    except (OSError, ValueError, KeyError, TypeError) as err:
        return _fail("built-in template catalog probe failed", "template_invalid", observed=str(err))
    return _pass("built-in template catalog is available", observed=repr(names))


def _simulate_cycle() -> CheckOutcome:
    try:
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.simulate import SimulationRuntime

        runtime = SimulationRuntime(load_state_machine_from_text("state Root;"))
        runtime.cycle()
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as err:
        return _fail("simulation cycle probe failed", "simulation_failed", observed=str(err))
    return _pass("simulation runtime completed one cycle")


def _solver_translation() -> CheckOutcome:
    try:
        from pyfcstm.model import Integer
        from pyfcstm.solver import expr_to_z3
        import z3

        expr_to_z3(Integer(1), {})
        z3.Int("selfcheck_translation")
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as err:
        return _fail("solver translation probe failed", "solver_translation_failed", observed=str(err))
    return _pass("solver expression translation is available")


def _verify_solve() -> CheckOutcome:
    try:
        from pyfcstm.model import load_state_machine_from_text
        from pyfcstm.verify import REGISTRY, run_inspect_algorithms

        if not REGISTRY:
            return _fail("verify algorithm registry is empty", "verify_registry_empty")
        results = run_inspect_algorithms(load_state_machine_from_text("state Root;"))
        if not results:
            return _fail("verify execution returned no results", "verify_failed")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("verify registry probe failed", "verify_failed", observed=str(err))
    return _pass("verify algorithm registry is available")


def _cli_help() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        result = CliRunner().invoke(cli, ["--help"])
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("CLI help probe failed", "cli_failed", observed=str(err))
    if result.exit_code != 0:
        return _fail("CLI help returned a non-zero status", "cli_failed", observed=result.output)
    return _pass("CLI help returned successfully")


def _cli_generate() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-") as directory:
            root = Path(directory)
            source = root / "machine.fcstm"
            output = root / "generated"
            source.write_text("state Root;\n", encoding="utf-8")
            result = CliRunner().invoke(
                cli,
                [
                    "generate",
                    "-i",
                    str(source),
                    "--template",
                    "python",
                    "-o",
                    str(output),
                ],
            )
            if result.exit_code != 0:
                return _fail("CLI generate returned a non-zero status", "cli_failed", observed=result.output)
            if not (output / "machine.py").is_file():
                return _fail("CLI generate produced no machine.py", "cli_failed")
    except (ImportError, OSError, AttributeError, TypeError, ValueError) as err:
        return _fail("CLI generate probe failed", "cli_failed", observed=str(err))
    return _pass("CLI generate produced machine.py")


def _cli_simulate() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-") as directory:
            source = Path(directory) / "machine.fcstm"
            source.write_text("state Root;\n", encoding="utf-8")
            result = CliRunner().invoke(
                cli,
                ["simulate", "-i", str(source), "-e", "cycle; current", "--no-color"],
            )
            if result.exit_code != 0:
                return _fail("CLI simulate returned a non-zero status", "cli_failed", observed=result.output)
    except (ImportError, OSError, AttributeError, TypeError, ValueError) as err:
        return _fail("CLI simulate probe failed", "cli_failed", observed=str(err))
    return _pass("CLI simulate completed a batch cycle")


def _cli_plantuml() -> CheckOutcome:
    try:
        from click.testing import CliRunner
        from pyfcstm.entry.cli import cli

        with tempfile.TemporaryDirectory(prefix="pyfcstm-cli-") as directory:
            source = Path(directory) / "machine.fcstm"
            source.write_text("state Root;\n", encoding="utf-8")
            result = CliRunner().invoke(cli, ["plantuml", "-i", str(source)])
            if result.exit_code != 0:
                return _fail("CLI plantuml returned a non-zero status", "cli_failed", observed=result.output)
            if "@startuml" not in result.output:
                return _fail("CLI plantuml returned no PlantUML text", "cli_failed")
    except (ImportError, OSError, AttributeError, TypeError, ValueError) as err:
        return _fail("CLI plantuml probe failed", "cli_failed", observed=str(err))
    return _pass("CLI plantuml returned PlantUML text")


def _bmc_query_parse() -> CheckOutcome:
    try:
        from pyfcstm.bmc.parse import parse_bmc_query

        query = parse_bmc_query('check reach <= 1: active("Root");')
        if getattr(getattr(query, "property", None), "kind", None) != "reach":
            return _fail("BMC query parser returned unexpected query", "bmc_parse_failed")
    except (ImportError, AttributeError, TypeError, ValueError) as err:
        return _fail("BMC query parser probe failed", "bmc_parse_failed", observed=str(err))
    return _pass("BMC query parser accepts a minimal query")


def _bmc_prepare() -> CheckOutcome:
    """Compile a BMC formula while proving no solver is started."""
    try:
        import z3
        from pyfcstm.bmc.pipeline import compile_bmc_query
        from pyfcstm.model import load_state_machine_from_text

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
                'check reach <= 1: active("Root");',
            )
        finally:
            z3.Solver = original_solver
            if original_check is not None:
                original_solver.check = original_check
        if not hasattr(formula, "solve_formula"):
            return _fail("BMC formula is not solve-ready", "bmc_prepare_failed")
        if calls["construct"] or calls["check"]:
            return _fail("BMC preparation started a solver", "bmc_prepare_solved")
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as err:
        return _fail("BMC prepare probe failed", "bmc_prepare_failed", observed=str(err))
    except AssertionError as err:
        return _fail("BMC preparation started a solver", "bmc_prepare_solved", observed=str(err))
    return _pass("BMC query compiles without solving")


def _bmc_solve() -> CheckOutcome:
    try:
        from pyfcstm.bmc.pipeline import compile_bmc_query
        from pyfcstm.bmc.witness import solve_bmc_property
        from pyfcstm.model import load_state_machine_from_text

        formula = compile_bmc_query(
            load_state_machine_from_text("state Root;"),
            'check reach <= 1: active("Root");',
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
                "check reach <= 1: terminated();",
            )
        )
        forbidden = solve_bmc_property(
            compile_bmc_query(
                load_state_machine_from_text("state Root;"),
                'check forbid <= 1: active("Root");',
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
            return _fail("BMC polarity probe has unexpected result", "bmc_solve_failed")
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as err:
        return _fail("BMC solve probe failed", "bmc_solve_failed", observed=str(err))
    return _pass("BMC property solver returned a typed result")


def _bmc_closure() -> CheckOutcome:
    modules = ("pyfcstm.bmc.parse", "pyfcstm.bmc.pipeline", "pyfcstm.bmc.witness")
    for module in modules:
        outcome = _probe_import(module)
        if outcome.status != "PASS":
            return outcome
    return _pass("BMC module closure is importable")


def _java() -> CheckOutcome:
    executable = shutil.which("java")
    if executable is None:
        return _warn("Java executable is unavailable", "capability_unavailable")
    try:
        completed = subprocess.run(
            [executable, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return _warn("Java executable is unavailable", "capability_unavailable", observed=str(err))
    if completed.returncode != 0:
        return _warn(
            "Java executable returned a non-zero status",
            "capability_unavailable",
            observed="returncode={}".format(completed.returncode),
        )
    return _pass("Java executable is available", observed=executable)


def _plantuml_jar() -> CheckOutcome:
    candidates = (_package_root() / "plantuml.jar", Path.cwd() / "plantuml.jar")
    for candidate in candidates:
        if candidate.is_file():
            return _pass("PlantUML JAR is available", observed=str(candidate))
    return _warn("PlantUML JAR is unavailable", "capability_unavailable")


def _python_stack() -> CheckOutcome:
    return _optional_import("plantumlcli")


def _visual_local_version() -> CheckOutcome:
    java = shutil.which("java")
    candidates = (_package_root() / "plantuml.jar", Path.cwd() / "plantuml.jar")
    jar = next((candidate for candidate in candidates if candidate.is_file()), None)
    if java is None or jar is None:
        return _warn("local PlantUML version is unavailable", "capability_unavailable")
    try:
        completed = subprocess.run(
            [java, "-jar", str(jar), "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return _warn(
            "local PlantUML version is unavailable",
            "capability_unavailable",
            observed="{}: {}".format(type(err).__name__, err),
        )
    output = completed.stdout + completed.stderr
    if completed.returncode != 0 or not output.strip():
        return _warn("local PlantUML version is unavailable", "capability_unavailable")
    return _pass("local PlantUML version is available", observed=output.decode("utf-8", "backslashreplace").strip())


def _visual_local_render() -> CheckOutcome:
    java = shutil.which("java")
    candidates = (_package_root() / "plantuml.jar", Path.cwd() / "plantuml.jar")
    jar = next((candidate for candidate in candidates if candidate.is_file()), None)
    if java is None or jar is None:
        return _warn(
            "local image rendering requires optional Java/PlantUML",
            "capability_unavailable",
        )
    source = b"@startuml\nAlice -> Bob\n@enduml\n"
    try:
        completed = subprocess.run(
            [java, "-jar", str(jar), "-pipe", "-tpng"],
            input=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return _warn(
            "local PlantUML rendering is unavailable",
            "capability_unavailable",
            observed="{}: {}".format(type(err).__name__, err),
        )
    if completed.returncode != 0 or not completed.stdout:
        return _warn(
            "local PlantUML rendering is unavailable",
            "capability_unavailable",
            observed="returncode={} stderr={}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", "backslashreplace"),
            ),
        )
    return _pass("local PlantUML rendering returned image bytes", observed=str(len(completed.stdout)))


def _visual_remote_tls() -> CheckOutcome:
    if os.environ.get("PYFCSTM_SELFCHECK_NETWORK") != "1":
        return CheckOutcome(
            "SKIP",
            "remote network checks are disabled by default",
            reason="network_disabled",
        )
    try:
        context = ssl.create_default_context()
        with socket.create_connection(("www.plantuml.com", 443), timeout=5.0) as raw:
            with context.wrap_socket(raw, server_hostname="www.plantuml.com") as tls:
                observed = tls.version() or "TLS"
    except (AttributeError, OSError, ssl.SSLError, ValueError) as err:
        return _warn("TLS context is unavailable", "capability_unavailable", observed=str(err))
    return _pass("remote PlantUML TLS endpoint is reachable", observed=observed)


def _visual_remote_render() -> CheckOutcome:
    if os.environ.get("PYFCSTM_SELFCHECK_NETWORK") != "1":
        return CheckOutcome(
            "SKIP", "remote rendering requires --network", reason="network_disabled"
        )
    try:
        from urllib.request import urlopen

        with urlopen(
            "https://www.plantuml.com/plantuml/txt/Syp9J4vLqBLJSCp9oGS0", timeout=10.0
        ) as response:
            payload = response.read(64 * 1024)
        if not payload:
            return _warn("remote PlantUML response is empty", "capability_unavailable")
    except (OSError, ValueError, TypeError, UnicodeError) as err:
        return _warn("remote PlantUML rendering is unavailable", "capability_unavailable", observed=str(err))
    return _pass("remote PlantUML rendering endpoint returned data", observed=str(len(payload)))


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
        return _fail("Unidecode tables are unavailable", "tables_invalid", observed=str(err))
    return _pass("Unidecode mapping tables are readable", observed=repr(observed))


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
    "collect_dependency_diagnostics",
    "registry_metadata",
    "selected_specs",
]
