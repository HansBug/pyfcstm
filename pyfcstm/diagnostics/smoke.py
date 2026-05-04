"""
End-to-end smoke-test runner for the :mod:`pyfcstm` package.

This module powers the ``pyfcstm --smoke-test`` CLI flag. Its single
responsibility is to verify, on a real running install, that every
component pyfcstm relies on is present and minimally functional:

* Python runtime + critical stdlib modules
* Every required third-party library (``click``, ``jinja2``,
  ``antlr4``, ``z3-solver``, ``hbutils``, ...) and the sysdesim-render
  optional extras (``py-mini-racer`` / ``mini-racer``)
* Native binary smoke for the deps that ship a compiled component
  (``z3-solver``, ``py-mini-racer``'s V8 isolate, the V8 ``WebAssembly``
  surface and the bundled ``resvg-wasm`` rasterizer)
* Bundled static resources: ANTLR grammar generated assets, built-in
  template archives, the SysDeSim JS render bundle and DejaVu Sans font
* Minimum end-to-end paths through DSL parsing, model building,
  expression / statement renderers, the simulator, the Z3 solver
  translation, and the four SysDeSim CLI subcommands

The runner is the **last line of defence** for diagnosing a broken
install: every case is isolated, every exception is caught and reported,
and the runner finishes even when most cases fail. The output uses
``click.style`` ANSI coloring (``[PASS]`` green, ``[FAIL]`` red,
``[INFO]`` cyan) and is structured so a human or an LLM debugger can act
on it directly.

The module contains:

* :class:`SmokeCase` - One isolated verification step.
* :class:`SmokeResult` - Outcome of running one ``SmokeCase``.
* :func:`run_smoke_test` - Public runner used by the CLI flag.
"""

from __future__ import annotations

import base64
import importlib
import io
import json
import os
import platform
import struct
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #


@dataclass
class SmokeCase:
    """One isolated smoke-test verification step.

    :param name: Short stable identifier (e.g. ``"dep_click"``).
    :type name: str
    :param method: Human-readable description of *how* the case
        verifies (e.g. ``"import click"``).
    :type method: str
    :param func: Zero-argument callable that performs the verification.
        Must raise on failure; returning normally counts as PASS.
    :type func: Callable[[], None]
    :param remediation: Optional one-line remediation hint that will be
        printed verbatim under a FAIL block. Phrase as an actionable
        suggestion (e.g. ``"pip install pyyaml"``).
    :type remediation: str, optional
    """

    name: str
    method: str
    func: Callable[[], None]
    remediation: Optional[str] = None


@dataclass
class SmokeResult:
    """Outcome of running one :class:`SmokeCase`.

    :param case: The originating case.
    :type case: SmokeCase
    :param status: ``"PASS"`` or ``"FAIL"``.
    :type status: str
    :param elapsed_ms: How many milliseconds the case took.
    :type elapsed_ms: float
    :param error: Captured exception when ``status == "FAIL"``,
        ``None`` otherwise.
    :type error: BaseException, optional
    :param error_traceback: Captured ``traceback.format_exc()`` text
        when ``status == "FAIL"``.
    :type error_traceback: str, optional
    """

    case: SmokeCase
    status: str
    elapsed_ms: float
    error: Optional[BaseException] = None
    error_traceback: Optional[str] = None


# --------------------------------------------------------------------------- #
# Tiny SysDeSim XMI fixture used by sysdesim end-to-end smoke cases.
# Inlined so the smoke runner has zero dependency on test fixture files.
# Two ASCII lifelines, two messages, no temporal constraints, no
# dropped-signal warnings - the simplest sysdesim shape the converter
# / validator / static-check / sequence-render pipeline can consume.
# --------------------------------------------------------------------------- #


_SMOKE_SYSDESIM_XMI = """<?xml version="1.0" encoding="UTF-8"?>
<xmi:XMI xmi:version="20131001"
         xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
         xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
  <uml:Model xmi:id="m1" name="m1">
    <packagedElement xmi:type="uml:Class" xmi:id="cls1" name="SmokeMachine" classifierBehavior="machine_1">
      <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="SmokeMachine">
        <region xmi:type="uml:Region" xmi:id="region_root" name="">
          <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_idle"/>
          <transition xmi:type="uml:Transition" xmi:id="tx_idle_done" source="state_idle" target="state_done">
            <trigger xmi:type="uml:Trigger" xmi:id="trigger_go" event="signal_evt_go"/>
          </transition>
          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
          <subvertex xmi:type="uml:State" xmi:id="state_idle" name="Idle"/>
          <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
        </region>
      </ownedBehavior>
      <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="SmokeScenario">
        <ownedAttribute xmi:type="uml:Property" xmi:id="prop_send" name="sender"/>
        <ownedAttribute xmi:type="uml:Property" xmi:id="prop_recv" name="receiver"/>
        <lifeline xmi:type="uml:Lifeline" xmi:id="ll_send" name="sender" represents="prop_send"/>
        <lifeline xmi:type="uml:Lifeline" xmi:id="ll_recv" name="receiver" represents="prop_recv"/>
        <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_send" covered="ll_send" message="msg_go"/>
        <fragment xmi:type="uml:MessageOccurrenceSpecification" xmi:id="go_recv" covered="ll_recv" message="msg_go"/>
        <message xmi:type="uml:Message" xmi:id="msg_go" sendEvent="go_send" receiveEvent="go_recv" signature="signal_go"/>
      </ownedBehavior>
    </packagedElement>
    <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Go"/>
    <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_go" signal="signal_go"/>
  </uml:Model>
</xmi:XMI>
"""


# --------------------------------------------------------------------------- #
# Verification helpers (each one is a SmokeCase ``func`` body).
# Every helper imports its dependencies inside the function body so an
# import failure in one case never poisons the rest of the run.
# --------------------------------------------------------------------------- #


def _verify_python_runtime() -> None:
    if sys.version_info < (3, 7):
        raise RuntimeError(
            "Python {} is below the supported floor (3.7+). pyfcstm targets "
            "the 3.7-3.14 envelope.".format(sys.version.split()[0])
        )


def _verify_core_stdlib() -> None:
    # Touch every stdlib module that pyfcstm reaches for at import time.
    for mod in (
        "json", "re", "pathlib", "hashlib", "base64", "struct",
        "importlib", "threading", "tempfile", "subprocess", "shutil",
        "zipfile", "io", "os", "sys", "time", "traceback",
    ):
        importlib.import_module(mod)


def _make_dep_check(import_name: str) -> Callable[[], None]:
    """Build a callable that verifies the dep is importable.

    We do not read ``__version__`` at this stage because some deps (e.g.
    Click 9.1+) emit a ``DeprecationWarning`` when that attribute is
    accessed. The import itself is the ground-truth smoke we care about
    here; native binary checks live in the ``Native binaries`` group.
    """

    def _check() -> None:
        importlib.import_module(import_name)

    return _check


def _verify_z3_native() -> None:
    import z3  # noqa: F401

    solver = z3.Solver()
    x = z3.Int("x")
    solver.add(x > 0)
    solver.add(x < 5)
    result = solver.check()
    if str(result) != "sat":
        raise RuntimeError(
            "z3 trivial SAT (0 < x < 5) returned {!r}; expected sat. The "
            "z3 native library may be miscompiled or stripped.".format(str(result))
        )
    model = solver.model()
    val = model[x].as_long()
    if not (0 < val < 5):
        raise RuntimeError(
            "z3 returned model x={} outside (0,5).".format(val)
        )


def _import_mini_racer():
    # Both ``py-mini-racer`` (Python 3.7) and ``mini-racer`` (Python 3.8+)
    # land at the same import path. We surface a clearer error here so a
    # FAIL on this case immediately points at the install command.
    return importlib.import_module("py_mini_racer").MiniRacer


def _verify_v8_isolate() -> None:
    MiniRacer = _import_mini_racer()
    ctx = MiniRacer()
    result = ctx.eval("40 + 2")
    if result != 42:
        raise RuntimeError(
            "V8 isolate returned {!r} for ``40 + 2``; expected 42. "
            "The mini-racer binding is mis-installed.".format(result)
        )


def _verify_v8_webassembly() -> None:
    # Minimal wasm module exporting ``add(i32, i32) -> i32``. If the V8
    # isolate cannot instantiate this, the resvg-wasm path will fail too.
    MiniRacer = _import_mini_racer()
    ctx = MiniRacer()
    js = """
    const wasmBytes = new Uint8Array([
      0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
      0x01, 0x07, 0x01, 0x60, 0x02, 0x7f, 0x7f, 0x01, 0x7f,
      0x03, 0x02, 0x01, 0x00,
      0x07, 0x07, 0x01, 0x03, 0x61, 0x64, 0x64, 0x00, 0x00,
      0x0a, 0x09, 0x01, 0x07, 0x00, 0x20, 0x00, 0x20, 0x01, 0x6a, 0x0b
    ]);
    const m = new WebAssembly.Module(wasmBytes);
    const i = new WebAssembly.Instance(m, {});
    i.exports.add(7, 35);
    """
    result = ctx.eval(js)
    if result != 42:
        raise RuntimeError(
            "WebAssembly.Module + Instance smoke returned {!r}; expected "
            "42. The V8 isolate is missing wasm support.".format(result)
        )


def _verify_dsl_parser() -> None:
    from pyfcstm.dsl import parse_with_grammar_entry

    src = "def int counter = 0;\nstate Active;\n"
    ast = parse_with_grammar_entry(src, "state_machine_dsl")
    if ast is None:
        raise RuntimeError("Grammar entry returned a None AST node.")


def _verify_model_build() -> None:
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model.model import parse_dsl_node_to_state_machine

    src = (
        "def int counter = 0;\n"
        "state System {\n"
        "    [*] -> Idle;\n"
        "    state Idle;\n"
        "    state Running;\n"
        "    Idle -> Running :: Start;\n"
        "}\n"
    )
    ast = parse_with_grammar_entry(src, "state_machine_dsl")
    machine = parse_dsl_node_to_state_machine(ast)
    walked = list(machine.walk_states())
    if not walked:
        raise RuntimeError("State machine walk_states() returned no states.")
    if "counter" not in machine.defines:
        raise RuntimeError(
            "State machine missing the declared 'counter' variable: defines={}".format(
                sorted(machine.defines.keys())
            )
        )


def _verify_render_expression_styles() -> None:
    from pyfcstm.dsl.node import BinaryOp, Integer, Name
    from pyfcstm.render.expr import render_expr_node

    # Build ``x + 1 > 0`` directly as DSL nodes so the case has zero
    # dependence on parser / model layers (those are exercised by their
    # own dedicated cases). The renderer must support the full nine-style
    # matrix declared in the templating layer.
    add_node = BinaryOp(Name("x"), "+", Integer("1"))
    cmp_node = BinaryOp(add_node, ">", Integer("0"))
    for style in ("dsl", "c", "cpp", "python", "java", "js", "ts", "rust", "go"):
        rendered = render_expr_node(cmp_node, lang_style=style)
        if not isinstance(rendered, str) or not rendered:
            raise RuntimeError(
                "render_expr_node(style={!r}) returned {!r}; expected non-empty string.".format(
                    style, rendered
                )
            )


def _verify_simulator_runtime() -> None:
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model.model import parse_dsl_node_to_state_machine
    from pyfcstm.simulate.runtime import SimulationRuntime

    src = (
        "def int counter = 0;\n"
        "state System {\n"
        "    [*] -> Idle;\n"
        "    state Idle { during { counter = counter + 1; } }\n"
        "}\n"
    )
    machine = parse_dsl_node_to_state_machine(parse_with_grammar_entry(src, "state_machine_dsl"))
    runtime = SimulationRuntime(machine)
    runtime.cycle()
    runtime.cycle()
    counter = dict(runtime.vars).get("counter", 0)
    if counter <= 0:
        raise RuntimeError(
            "Simulator did not advance counter; got vars={!r}".format(dict(runtime.vars))
        )


def _verify_solver_z3_translation() -> None:
    import z3

    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model.model import parse_dsl_node_to_state_machine
    from pyfcstm.solver.expr import expr_to_z3

    src = (
        "def int x = 0;\n"
        "state Sys {\n"
        "    [*] -> A;\n"
        "    state A;\n"
        "    state B;\n"
        "    A -> B : if [x > 0 && x < 10];\n"
        "}\n"
    )
    machine = parse_dsl_node_to_state_machine(parse_with_grammar_entry(src, "state_machine_dsl"))
    guard = None
    for state in machine.walk_states():
        for transition in getattr(state, "transitions", []) or []:
            if getattr(transition, "guard", None) is not None:
                guard = transition.guard
                break
        if guard is not None:
            break
    if guard is None:
        raise RuntimeError("No guarded transition to translate.")
    z3_vars = {"x": z3.Int("x")}
    z3_expr = expr_to_z3(guard, z3_vars)
    if z3_expr is None:
        raise RuntimeError("expr_to_z3 returned None.")


def _verify_resource_grammar() -> None:
    # Each generated file ships as a ``.py`` so under PyInstaller it lives
    # inside the PYZ archive, not on the filesystem. We verify by import,
    # which works equally for source layouts, wheels, and frozen exes.
    needed = ("GrammarLexer", "GrammarParser", "GrammarListener")
    missing = []
    for stem in needed:
        try:
            importlib.import_module("pyfcstm.dsl.grammar." + stem)
        except ImportError:
            missing.append(stem)
    if missing:
        raise RuntimeError(
            "Generated ANTLR grammar modules missing/unimportable under "
            "pyfcstm.dsl.grammar: {}".format(", ".join(missing))
        )


def _verify_resource_template_index() -> None:
    import pyfcstm.template as template_pkg

    pkg_dir = os.path.dirname(os.path.abspath(template_pkg.__file__))
    index_path = os.path.join(pkg_dir, "index.json")
    if not os.path.exists(index_path):
        raise RuntimeError(
            "Built-in template index missing at {}. The wheel did not "
            "ship templates/index.json.".format(index_path)
        )
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("templates") or []
    if not entries:
        raise RuntimeError("template/index.json declares zero templates.")
    missing_archives = []
    for entry in entries:
        archive_name = entry.get("archive")
        if not archive_name:
            missing_archives.append(repr(entry))
            continue
        if not os.path.exists(os.path.join(pkg_dir, archive_name)):
            missing_archives.append(archive_name)
    if missing_archives:
        raise RuntimeError(
            "Built-in template archives missing under {}: {}".format(
                pkg_dir, ", ".join(missing_archives)
            )
        )


def _verify_resource_template_extract() -> None:
    import tempfile

    from pyfcstm.template import extract_template, list_templates

    names = list_templates()
    if not names:
        raise RuntimeError(
            "list_templates() returned an empty set; index.json may be empty."
        )
    failures = []
    for name in names:
        with tempfile.TemporaryDirectory(prefix="pyfcstm-smoke-tpl-") as out_dir:
            try:
                target = extract_template(name, out_dir)
            except Exception as exc:
                failures.append("{}: extract raised {!r}".format(name, exc))
                continue
            if target is None or not os.path.isdir(target):
                failures.append("{}: extract returned {!r}".format(name, target))
                continue
            config = os.path.join(target, "config.yaml")
            if not os.path.exists(config):
                failures.append("{}: missing config.yaml at {}".format(name, config))
    if failures:
        raise RuntimeError(
            "Built-in template extract failures: {}".format("; ".join(failures))
        )


def _verify_text_identifier_safety() -> None:
    """Verify the multilingual identifier helpers from PR #75.

    The helpers must rewrap language reserved words and ASCII-ize
    non-Latin input so generated code is always a syntactically valid
    identifier in the target language.
    """
    from pyfcstm.utils.text import (
        normalize,
        to_c_identifier,
        to_cpp_identifier,
        to_java_identifier,
        to_python_identifier,
    )

    # Plain normalization keeps printable ASCII and replaces gaps.
    norm = normalize("Hello World!")
    if not norm or "Hello" not in norm:
        raise RuntimeError(
            "normalize('Hello World!') returned {!r}; expected a non-empty "
            "ASCII identifier-like string.".format(norm)
        )

    # Language keyword safety: ``class`` must NOT come back as ``class``
    # in any of these languages because it is a reserved word.
    py_ident = to_python_identifier("class")
    if py_ident == "class":
        raise RuntimeError(
            "to_python_identifier('class') returned the reserved word "
            "verbatim ({!r}); the keyword-safety pass is broken.".format(py_ident)
        )
    java_ident = to_java_identifier("class")
    if java_ident == "class":
        raise RuntimeError(
            "to_java_identifier('class') returned the reserved word "
            "verbatim ({!r}).".format(java_ident)
        )
    cpp_ident = to_cpp_identifier("class")
    if cpp_ident == "class":
        raise RuntimeError(
            "to_cpp_identifier('class') returned the reserved word "
            "verbatim ({!r}).".format(cpp_ident)
        )

    # CJK -> ASCII via the unidecode pass (PR #75).
    c_ident = to_c_identifier("中文 var")
    if not c_ident:
        raise RuntimeError(
            "to_c_identifier('中文 var') returned an empty string; "
            "unidecode round-trip is broken."
        )
    # Result must be ASCII (Python str.isascii is 3.7+, fall back to
    # ASCII codec encoding for safety on older builds).
    try:
        c_ident.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeError(
            "to_c_identifier('中文 var') returned non-ASCII {!r}: {!r}".format(
                c_ident, exc
            )
        )


def _verify_plantuml_export() -> None:
    """Verify the model -> PlantUML export pipeline.

    Covers ``pyfcstm plantuml`` end-to-end *core*: parse a tiny DSL,
    build the model, call ``to_plantuml()`` and assert the output is
    well-shaped (``@startuml`` / ``@enduml`` envelope + the declared
    state names appear in the body).
    """
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model.model import parse_dsl_node_to_state_machine

    src = (
        "def int x = 0;\n"
        "state Sys {\n"
        "    [*] -> Idle;\n"
        "    state Idle;\n"
        "    state Done;\n"
        "    Idle -> Done :: Go;\n"
        "}\n"
    )
    machine = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(src, "state_machine_dsl")
    )
    puml = machine.to_plantuml()
    if not isinstance(puml, str) or not puml:
        raise RuntimeError(
            "to_plantuml() returned {!r}; expected a non-empty string.".format(puml)
        )
    if "@startuml" not in puml:
        raise RuntimeError(
            "PlantUML output missing @startuml prologue; first 80 chars: {!r}".format(
                puml[:80]
            )
        )
    if "@enduml" not in puml:
        raise RuntimeError(
            "PlantUML output missing @enduml epilogue; last 80 chars: {!r}".format(
                puml[-80:]
            )
        )
    for state_name in ("Idle", "Done"):
        if state_name not in puml:
            raise RuntimeError(
                "PlantUML output missing declared state {!r}.".format(state_name)
            )


def _verify_generate_python_template() -> None:
    """Verify the full generate pipeline against the built-in python template.

    This case wires together: built-in template extraction, the
    Jinja2 environment in ``pyfcstm.render``, the expression and
    statement style renderers, and ``StateMachineCodeRenderer``. A
    failure here means at least one of those layers regressed even
    when their isolated cases pass.
    """
    import tempfile

    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model.model import parse_dsl_node_to_state_machine
    from pyfcstm.render.render import StateMachineCodeRenderer
    from pyfcstm.template import extract_template

    src = (
        "def int counter = 0;\n"
        "state Sys {\n"
        "    [*] -> Idle;\n"
        "    state Idle { during { counter = counter + 1; } }\n"
        "    state Done;\n"
        "    Idle -> Done :: Stop;\n"
        "}\n"
    )
    machine = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(src, "state_machine_dsl")
    )
    with tempfile.TemporaryDirectory(prefix="pyfcstm-smoke-tpl-") as tpl_root:
        target = extract_template("python", tpl_root)
        if target is None or not os.path.isdir(target):
            raise RuntimeError(
                "extract_template('python', ...) returned {!r}".format(target)
            )
        with tempfile.TemporaryDirectory(prefix="pyfcstm-smoke-out-") as out_dir:
            renderer = StateMachineCodeRenderer(target)
            renderer.render(machine, out_dir, clear_previous_directory=True)
            machine_py = os.path.join(out_dir, "machine.py")
            if not os.path.exists(machine_py):
                raise RuntimeError(
                    "Render did not produce machine.py at {}".format(machine_py)
                )
            text = open(machine_py, "r", encoding="utf-8").read()
            for needle in ("class", "SysMachine"):
                if needle not in text:
                    raise RuntimeError(
                        "Generated machine.py is missing token {!r}; "
                        "first 200 chars: {!r}".format(needle, text[:200])
                    )


def _verify_resource_render_bundle_present() -> None:
    import pyfcstm.convert.sysdesim as sysdesim_pkg

    pkg_dir = os.path.dirname(os.path.abspath(sysdesim_pkg.__file__))
    bundle_path = os.path.join(pkg_dir, "_render_assets", "pyfcstm-sysdesim-render.js")
    if not os.path.exists(bundle_path):
        raise RuntimeError(
            "SysDeSim render bundle missing at {}. The wheel did not "
            "ship _render_assets/pyfcstm-sysdesim-render.js.".format(bundle_path)
        )
    size = os.path.getsize(bundle_path)
    if size < 1_000_000:  # ~4 MB expected, refuse anything below 1 MB.
        raise RuntimeError(
            "SysDeSim render bundle is implausibly small ({} bytes) - the "
            "resvg-wasm payload may have been stripped.".format(size)
        )


def _verify_resource_render_bundle_loadable() -> None:
    from pyfcstm.convert.sysdesim import render as render_module

    # Reset the cache so we exercise the actual load path.
    render_module._runtime_cached = None
    ctx, version = render_module._get_runtime()
    if not version:
        raise RuntimeError(
            "PyfcstmSysdesim.version() returned an empty version string."
        )


def _verify_sysdesim_xml_parse() -> None:
    import tempfile

    from pyfcstm.convert.sysdesim import build_sysdesim_phase56_report

    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_SMOKE_SYSDESIM_XMI)
        path = tmp.name
    try:
        report = build_sysdesim_phase56_report(path)
        if not report or not getattr(report, "interaction", None):
            raise RuntimeError("Phase 5/6 report has no interaction.")
    finally:
        try:
            os.unlink(path)
        except OSError:  # pragma: no cover - tmp cleanup
            pass


def _verify_sysdesim_static_check() -> None:
    import tempfile

    from pyfcstm.convert import run_sysdesim_static_pre_checks

    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_SMOKE_SYSDESIM_XMI)
        path = tmp.name
    try:
        diagnostics = run_sysdesim_static_pre_checks(xml_path=path)
        # We don't care whether diagnostics is empty - we only want the
        # call to complete without raising.
        _ = list(diagnostics)
    finally:
        try:
            os.unlink(path)
        except OSError:  # pragma: no cover - tmp cleanup
            pass


def _verify_sysdesim_validate() -> None:
    import tempfile

    from pyfcstm.convert import build_sysdesim_timeline_import_report

    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_SMOKE_SYSDESIM_XMI)
        path = tmp.name
    try:
        report = build_sysdesim_timeline_import_report(xml_path=path)
        if not report or "phase78" not in report:
            raise RuntimeError(
                "validate report missing phase78 key: {}".format(
                    sorted(report.keys()) if isinstance(report, dict) else type(report)
                )
            )
    finally:
        try:
            os.unlink(path)
        except OSError:  # pragma: no cover - tmp cleanup
            pass


def _verify_sysdesim_svg_render() -> None:
    import tempfile

    from pyfcstm.convert import render_sysdesim_timeline_svg

    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_SMOKE_SYSDESIM_XMI)
        path = tmp.name
    try:
        svg = render_sysdesim_timeline_svg(xml_path=path)
        if not isinstance(svg, str):
            raise RuntimeError("render returned non-str: {}".format(type(svg)))
        if not svg.startswith("<?xml"):
            raise RuntimeError(
                "Render output missing XML prolog (first 80 chars): {!r}".format(svg[:80])
            )
        if "<svg" not in svg or "</svg>" not in svg:
            raise RuntimeError("Render output missing svg tags.")
    finally:
        try:
            os.unlink(path)
        except OSError:  # pragma: no cover - tmp cleanup
            pass


def _verify_sysdesim_png_render() -> None:
    import tempfile

    from pyfcstm.convert import render_sysdesim_timeline_png

    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_SMOKE_SYSDESIM_XMI)
        path = tmp.name
    try:
        png = render_sysdesim_timeline_png(xml_path=path)
        if not isinstance(png, (bytes, bytearray)):
            raise RuntimeError("render returned non-bytes: {}".format(type(png)))
        if png[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(
                "Render output missing PNG magic bytes: got {!r}".format(png[:16])
            )
        # Parse IHDR for a sanity dimension check.
        width, height = struct.unpack(">II", png[16:24])
        if width <= 0 or height <= 0:
            raise RuntimeError(
                "PNG IHDR reported degenerate dimensions {}x{}".format(width, height)
            )
    finally:
        try:
            os.unlink(path)
        except OSError:  # pragma: no cover - tmp cleanup
            pass


# --------------------------------------------------------------------------- #
# Case registry. Order matters: groups run top-down, cases inside a group
# also run in the order declared. We put cheap pure-Python imports first
# so a botched env yields a fast, structured failure list rather than
# hanging at the first heavy native check.
# --------------------------------------------------------------------------- #


def _build_case_groups() -> List[Tuple[str, List[SmokeCase]]]:
    return [
        ("Python runtime", [
            SmokeCase(
                name="python_runtime",
                method="sys.version_info >= (3, 7)",
                func=_verify_python_runtime,
                remediation=(
                    "Upgrade to Python 3.7+; pyfcstm targets 3.7-3.14."
                ),
            ),
            SmokeCase(
                name="core_stdlib",
                method="import json/re/pathlib/hashlib/base64/struct/...",
                func=_verify_core_stdlib,
                remediation=(
                    "Some required stdlib modules are missing; this points at "
                    "a heavily stripped Python install (e.g. minimal CPython "
                    "build, slim Docker base image). Use a stock CPython distribution."
                ),
            ),
        ]),
        ("Third-party libraries", [
            SmokeCase(
                name="dep_click",
                method="import click",
                func=_make_dep_check("click"),
                remediation="pip install 'click>=8'",
            ),
            SmokeCase(
                name="dep_jinja2",
                method="import jinja2",
                func=_make_dep_check("jinja2"),
                remediation="pip install 'jinja2>=3'",
            ),
            SmokeCase(
                name="dep_antlr4_runtime",
                method="import antlr4",
                func=_make_dep_check("antlr4"),
                remediation="pip install antlr4-python3-runtime==4.9.3",
            ),
            SmokeCase(
                name="dep_z3_solver",
                method="import z3",
                func=_make_dep_check("z3"),
                remediation="pip install 'z3-solver<=4.15.4'",
            ),
            SmokeCase(
                name="dep_hbutils",
                method="import hbutils",
                func=_make_dep_check("hbutils"),
                remediation="pip install 'hbutils>=0.14.0'",
            ),
            SmokeCase(
                name="dep_pyyaml",
                method="import yaml",
                func=_make_dep_check("yaml"),
                remediation="pip install pyyaml",
            ),
            SmokeCase(
                name="dep_pathspec",
                method="import pathspec",
                func=_make_dep_check("pathspec"),
                remediation="pip install pathspec",
            ),
            SmokeCase(
                name="dep_pygments",
                method="import pygments",
                func=_make_dep_check("pygments"),
                remediation="pip install 'pygments>=2.10.0'",
            ),
            SmokeCase(
                name="dep_unidecode",
                method="import unidecode",
                func=_make_dep_check("unidecode"),
                remediation="pip install unidecode",
            ),
            SmokeCase(
                name="dep_chardet",
                method="import chardet",
                func=_make_dep_check("chardet"),
                remediation="pip install chardet",
            ),
            SmokeCase(
                name="dep_prompt_toolkit",
                method="import prompt_toolkit",
                func=_make_dep_check("prompt_toolkit"),
                remediation="pip install 'prompt_toolkit>=3.0.0'",
            ),
            SmokeCase(
                name="dep_rich",
                method="import rich",
                func=_make_dep_check("rich"),
                remediation="pip install 'rich>=13,<14'",
            ),
            SmokeCase(
                name="dep_natsort",
                method="import natsort",
                func=_make_dep_check("natsort"),
                remediation="pip install natsort",
            ),
            SmokeCase(
                name="dep_plantumlcli",
                method="import plantumlcli",
                func=_make_dep_check("plantumlcli"),
                remediation="pip install 'plantumlcli>=0.2.0'",
            ),
            SmokeCase(
                name="dep_mini_racer",
                method="import py_mini_racer (covers both py-mini-racer and mini-racer)",
                func=lambda: _import_mini_racer(),
                remediation=(
                    "pip install -r requirements-sysdesim_render.txt or "
                    "directly: pip install 'py-mini-racer; python_version<\"3.8\"' "
                    "'mini-racer; python_version>=\"3.8\"'"
                ),
            ),
        ]),
        ("Native binaries", [
            SmokeCase(
                name="native_z3_sat",
                method="z3.Solver(): 0 < x < 5 -> sat",
                func=_verify_z3_native,
                remediation=(
                    "z3 imported but the native solver mis-fired. Reinstall "
                    "z3-solver from a wheel that matches your Python ABI: "
                    "pip install --force-reinstall 'z3-solver<=4.15.4'"
                ),
            ),
            SmokeCase(
                name="native_v8_isolate",
                method="MiniRacer().eval('40 + 2') == 42",
                func=_verify_v8_isolate,
                remediation=(
                    "V8 isolate failed to instantiate. py-mini-racer's native "
                    "library is missing or incompatible. On Win7 install the "
                    "Visual C++ 2015 redistributable; on stripped Linux make "
                    "sure you have a glibc-based platform (musl is unsupported)."
                ),
            ),
            SmokeCase(
                name="native_v8_webassembly",
                method="V8: WebAssembly.Module + Instance instantiate trivial wasm",
                func=_verify_v8_webassembly,
                remediation=(
                    "V8 isolate runs but cannot host WebAssembly. The "
                    "py-mini-racer wheel may have shipped a stripped V8 "
                    "build. Reinstall: pip install --force-reinstall mini-racer"
                ),
            ),
        ]),
        ("Internal modules", [
            SmokeCase(
                name="pyfcstm_dsl_parser",
                method="parse_with_grammar_entry('def int counter = 0; state Active;', 'state_machine_dsl')",
                func=_verify_dsl_parser,
                remediation=(
                    "DSL parser failed. Possible causes: ANTLR-generated "
                    "files (GrammarLexer.py / GrammarParser.py / "
                    "GrammarListener.py) missing under pyfcstm/dsl/grammar/, "
                    "or antlr4-python3-runtime version mismatch (we pin 4.9.3)."
                ),
            ),
            SmokeCase(
                name="pyfcstm_model_build",
                method="parse_dsl_node_to_state_machine on a 2-state hierarchy",
                func=_verify_model_build,
                remediation=(
                    "Model layer failed to consume the AST. Check that "
                    "pyfcstm.model.model imports without ImportError and "
                    "that the listener emits the expected node tree."
                ),
            ),
            SmokeCase(
                name="pyfcstm_render_expression_styles",
                method="expr_render(style=...) for dsl/c/cpp/python/java/js/ts/rust/go",
                func=_verify_render_expression_styles,
                remediation=(
                    "Expression renderer styles failed. One language style "
                    "may be unregistered or its handler raises. Run with "
                    "--smoke-test under a verbose Python (PYTHONUNBUFFERED=1) "
                    "and inspect the traceback above."
                ),
            ),
            SmokeCase(
                name="pyfcstm_simulator_runtime",
                method="SimulationRuntime(machine).cycle() x2 advances vars",
                func=_verify_simulator_runtime,
                remediation=(
                    "Simulator did not advance state. Check that "
                    "pyfcstm.simulate.runtime is importable and that the "
                    "model layer produces a stack-style hierarchical machine."
                ),
            ),
            SmokeCase(
                name="pyfcstm_solver_z3_translation",
                method="to_z3_expression(guard) on 'x > 0 && x < 10'",
                func=_verify_solver_z3_translation,
                remediation=(
                    "Z3 expression translator failed. Likely either the z3 "
                    "import works but the solver translation layer "
                    "(pyfcstm.solver.expr) hit an unsupported node, or the "
                    "z3 native ABI is incompatible (see native_z3_sat)."
                ),
            ),
            SmokeCase(
                name="pyfcstm_text_identifier_safety",
                method="to_{python,c,cpp,java}_identifier on reserved + CJK input",
                func=_verify_text_identifier_safety,
                remediation=(
                    "Multilingual identifier helper broken. Either "
                    "``unidecode`` is missing (see dep_unidecode) or "
                    "``pyfcstm.utils.text``'s keyword-safety table got "
                    "corrupted. Reinstall pyfcstm or check that unidecode "
                    "is on the same Python that runs the CLI."
                ),
            ),
            SmokeCase(
                name="pyfcstm_plantuml_export",
                method="machine.to_plantuml() returns @startuml..@enduml + state names",
                func=_verify_plantuml_export,
                remediation=(
                    "PlantUML export broke. Likely either model.to_plantuml "
                    "regressed, or the model layer dropped a state during "
                    "build (see pyfcstm_model_build). Run "
                    "``pyfcstm plantuml -i x.fcstm -o x.puml`` for the full "
                    "traceback."
                ),
            ),
        ]),
        ("Static resources", [
            SmokeCase(
                name="resource_antlr_grammar",
                method="import pyfcstm.dsl.grammar.{GrammarLexer,GrammarParser,GrammarListener}",
                func=_verify_resource_grammar,
                remediation=(
                    "ANTLR-generated grammar modules missing. Run "
                    "`make antlr_build` from a development checkout to "
                    "(re)generate them, or install pyfcstm from a wheel "
                    "(the generated files are part of the distributable, "
                    "not of the .g4 source)."
                ),
            ),
            SmokeCase(
                name="resource_template_index",
                method="template/index.json + every declared archive present",
                func=_verify_resource_template_index,
                remediation=(
                    "Built-in template archives missing. Run `make tpl` from "
                    "a development checkout, or install pyfcstm from a wheel "
                    "(`pip install --force-reinstall pyfcstm`)."
                ),
            ),
            SmokeCase(
                name="resource_template_extract",
                method="extract_template(name, tmp) for every template in index.json",
                func=_verify_resource_template_extract,
                remediation=(
                    "One or more built-in template zips are unreadable or "
                    "missing config.yaml. Re-build via `make tpl` or "
                    "reinstall the wheel. The error message above lists "
                    "exactly which template(s) failed - do NOT delete the "
                    "ones that did succeed when triaging."
                ),
            ),
            SmokeCase(
                name="resource_render_bundle_present",
                method="_render_assets/pyfcstm-sysdesim-render.js exists, > 1 MB",
                func=_verify_resource_render_bundle_present,
                remediation=(
                    "SysDeSim render bundle missing or stripped. Rebuild via "
                    "`cd js/sysdesim_render && npm install && npm run build` "
                    "and copy dist/pyfcstm-sysdesim-render.js into "
                    "pyfcstm/convert/sysdesim/_render_assets/, or install "
                    "pyfcstm from a wheel."
                ),
            ),
            SmokeCase(
                name="resource_render_bundle_loadable",
                method="MiniRacer eval(bundle) -> PyfcstmSysdesim.version() returns a string",
                func=_verify_resource_render_bundle_loadable,
                remediation=(
                    "Bundle file present but V8 cannot evaluate it. Either "
                    "the bundle is corrupted (re-extract the wheel) or the "
                    "embedded V8 isolate's parser is too old; rebuild the "
                    "bundle with esbuild --target=es2015."
                ),
            ),
        ]),
        ("End-to-end render pipelines", [
            SmokeCase(
                name="generate_python_template_pipeline",
                method="parse + extract_template('python') + StateMachineCodeRenderer.render -> machine.py",
                func=_verify_generate_python_template,
                remediation=(
                    "Built-in python template generation pipeline broke. "
                    "This wires together: extract_template, the Jinja2 "
                    "environment, expr/stmt renderers, and the python "
                    "template archive. Run "
                    "``pyfcstm generate -i x.fcstm --template python -o out`` "
                    "for the full traceback. Common root causes: a "
                    "regression in the python template (templates/python/), "
                    "a Jinja2 filter unregistered, or the template zip "
                    "shipped without the .j2 files (see "
                    "resource_template_extract)."
                ),
            ),
        ]),
        ("End-to-end SysDeSim CLI paths", [
            SmokeCase(
                name="sysdesim_xml_parse",
                method="build_sysdesim_phase56_report(inline minimal XMI)",
                func=_verify_sysdesim_xml_parse,
                remediation=(
                    "SysDeSim phase 5/6 import broke. Check pyfcstm.convert."
                    "sysdesim.timeline imports + xmi parser are intact."
                ),
            ),
            SmokeCase(
                name="sysdesim_static_check",
                method="run_sysdesim_static_pre_checks(inline minimal XMI)",
                func=_verify_sysdesim_static_check,
                remediation=(
                    "Static pre-check pipeline failed. Inspect "
                    "pyfcstm.convert.sysdesim.static_check imports."
                ),
            ),
            SmokeCase(
                name="sysdesim_validate",
                method="build_sysdesim_timeline_import_report(inline minimal XMI)",
                func=_verify_sysdesim_validate,
                remediation=(
                    "Phase 7-10 timeline validation pipeline failed. May "
                    "involve z3 (see native_z3_sat) or sysdesim model layer."
                ),
            ),
            SmokeCase(
                name="sysdesim_svg_render",
                method="render_sysdesim_timeline_svg(inline minimal XMI)",
                func=_verify_sysdesim_svg_render,
                remediation=(
                    "SVG renderer failed. Most often the bundle eval inside "
                    "MiniRacer threw - re-run with PYFCSTM_SMOKE_VERBOSE=1 or "
                    "see the traceback above for the JS-side error."
                ),
            ),
            SmokeCase(
                name="sysdesim_png_render",
                method="render_sysdesim_timeline_png(inline minimal XMI) -> PNG magic",
                func=_verify_sysdesim_png_render,
                remediation=(
                    "PNG renderer failed. Likely root causes: missing V8 "
                    "wasm support (see native_v8_webassembly), missing "
                    "icudtl.dat sidecar (PyInstaller hook in tools/generate_spec.py), "
                    "or a corrupt resvg-wasm bundle."
                ),
            ),
        ]),
    ]


# --------------------------------------------------------------------------- #
# Output formatting. Click is the canonical way to print colored output in
# this codebase, but because click MUST be importable for the CLI flag to
# even fire, importing it here is safe. We still wrap the import in a
# try/except to fall back to bare ASCII output if click fails for any
# unforeseen reason - the runner's contract is "always finishes".
# --------------------------------------------------------------------------- #


class _Painter:
    """Best-effort ANSI color helper.

    Falls back to identity (no color) when click cannot be imported or
    when the destination stream is not a TTY.
    """

    def __init__(self) -> None:
        self._click = None
        try:
            import click
        except Exception:  # pragma: no cover - click is required by the CLI flag
            self._click = None
        else:
            self._click = click

    def style(self, text: str, **kwargs) -> str:
        if self._click is None:
            return text
        try:
            return self._click.style(text, **kwargs)
        except Exception:  # pragma: no cover - defensive
            return text

    def echo(self, text: str = "") -> None:
        if self._click is None:
            print(text)
            return
        try:
            self._click.echo(text)
        except Exception:  # pragma: no cover - defensive
            print(text)


def _format_traceback(exc: BaseException, tb_text: str, max_frames: int = 5) -> List[str]:
    """Pretty-print the most actionable frames of a captured traceback."""
    lines = tb_text.rstrip().splitlines()
    if not lines:
        return ["(no traceback captured)"]
    if len(lines) <= max_frames * 2 + 2:
        return lines
    head = lines[:1]
    tail = lines[-(max_frames * 2 + 1) :]
    return head + ["... <{} earlier frames trimmed>".format(len(lines) - len(head) - len(tail))] + tail


def _safe_env_value(fn) -> str:
    """Call ``fn`` and stringify the result; turn any exception into a
    structured ``(unavailable: ...)`` placeholder.

    The whole environment dump must never raise: a failure to read one
    fact (because some weird OS, a sandbox, a stripped Python build,
    ...) is itself useful debug data, but it must not block the rest
    of the diagnostics. Callers do not see exceptions.
    """
    try:
        value = fn()
    except BaseException as exc:  # noqa: BLE001 - intentional broad catch
        return "(unavailable: {}: {})".format(type(exc).__name__, exc)
    if value is None:
        return "(none)"
    if isinstance(value, str):
        return value
    return str(value)


def _collect_environment_facts() -> List[Tuple[str, List[Tuple[str, str]]]]:
    """
    Collect a deep environment dump for the diagnostic header.

    Returns a list of ``(section_label, [(key, value), ...])`` rows.
    Every value is read through :func:`_safe_env_value` so a failure
    in one reader yields a placeholder string rather than aborting the
    block. The collector itself swallows top-level exceptions in its
    caller (:func:`run_smoke_test`), so even a catastrophic failure
    here cannot prevent the case battery from running.
    """
    sections: List[Tuple[str, List[Tuple[str, str]]]] = []

    def _add(rows: List[Tuple[str, str]], label: str, fn) -> None:
        rows.append((label, _safe_env_value(fn)))

    # --- Python interpreter --------------------------------------------------
    py_rows: List[Tuple[str, str]] = []
    _add(py_rows, "implementation", lambda: platform.python_implementation())
    _add(py_rows, "version", lambda: sys.version.split()[0])
    _add(py_rows, "build", lambda: " / ".join(platform.python_build()))
    _add(py_rows, "compiler", lambda: platform.python_compiler())
    _add(py_rows, "executable", lambda: sys.executable)
    _add(py_rows, "prefix", lambda: sys.prefix)
    _add(py_rows, "base prefix", lambda: getattr(sys, "base_prefix", sys.prefix))
    _add(py_rows, "maxsize bits", lambda: 64 if sys.maxsize > (1 << 32) else 32)
    _add(py_rows, "byteorder", lambda: sys.byteorder)
    _add(py_rows, "recursion limit", lambda: sys.getrecursionlimit())
    sections.append(("Python interpreter", py_rows))

    # --- OS / platform -------------------------------------------------------
    os_rows: List[Tuple[str, str]] = []
    _add(os_rows, "system", lambda: platform.system())
    _add(os_rows, "release", lambda: platform.release())
    _add(os_rows, "version", lambda: platform.version())
    _add(os_rows, "machine", lambda: platform.machine())
    _add(os_rows, "processor", lambda: platform.processor() or "(unknown)")
    _add(os_rows, "platform", lambda: platform.platform())
    _add(os_rows, "node", lambda: platform.node())
    if sys.platform.startswith("linux"):
        _add(os_rows, "libc", lambda: " ".join(s for s in platform.libc_ver() if s) or "(unknown)")
    elif sys.platform == "darwin":
        _add(os_rows, "mac_ver", lambda: " ".join(s for s in platform.mac_ver() if s) or "(unknown)")
    elif sys.platform == "win32":
        _add(os_rows, "win32_ver", lambda: " ".join(s for s in platform.win32_ver() if s) or "(unknown)")
        _add(os_rows, "win32_edition", lambda: platform.win32_edition() or "(unknown)")
    sections.append(("OS / platform", os_rows))

    # --- Process -------------------------------------------------------------
    proc_rows: List[Tuple[str, str]] = []
    _add(proc_rows, "pid", lambda: os.getpid())
    _add(proc_rows, "cwd", lambda: os.getcwd())
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        _add(proc_rows, "uid/gid", lambda: "{}/{}".format(os.getuid(), os.getgid()))
        if hasattr(os, "geteuid") and hasattr(os, "getegid"):
            _add(
                proc_rows, "euid/egid",
                lambda: "{}/{}".format(os.geteuid(), os.getegid()),
            )
    _add(proc_rows, "argv[0]", lambda: sys.argv[0] if sys.argv else "(none)")
    _add(proc_rows, "stdin tty?", lambda: bool(sys.stdin and sys.stdin.isatty()))
    _add(proc_rows, "stdout tty?", lambda: bool(sys.stdout and sys.stdout.isatty()))
    sections.append(("Process", proc_rows))

    # --- Locale / encoding ---------------------------------------------------
    loc_rows: List[Tuple[str, str]] = []

    def _preferred_encoding() -> str:
        import locale
        return locale.getpreferredencoding(False)

    def _locale_setting() -> str:
        import locale
        parts = [p for p in locale.getlocale() if p]
        return " / ".join(parts) if parts else "(C)"

    _add(loc_rows, "preferred encoding", _preferred_encoding)
    _add(loc_rows, "locale", _locale_setting)
    _add(loc_rows, "stdout encoding", lambda: getattr(sys.stdout, "encoding", "(none)"))
    _add(loc_rows, "stderr encoding", lambda: getattr(sys.stderr, "encoding", "(none)"))
    _add(loc_rows, "filesystem encoding", lambda: sys.getfilesystemencoding())
    _add(loc_rows, "LC_ALL", lambda: os.environ.get("LC_ALL", "(unset)"))
    _add(loc_rows, "LANG", lambda: os.environ.get("LANG", "(unset)"))
    sections.append(("Locale / encoding", loc_rows))

    # --- Environment variables (relevant subset) -----------------------------
    env_vars = (
        "VIRTUAL_ENV", "CONDA_PREFIX",
        "PYTHONPATH", "PYTHONHOME", "PYTHONIOENCODING",
        "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED",
        "TERM", "COLORTERM", "TZ",
        "DISPLAY", "BROWSER",
        "CI", "GITHUB_ACTIONS",
    )
    env_rows: List[Tuple[str, str]] = []
    for var in env_vars:
        _add(env_rows, var, lambda v=var: os.environ.get(v, "(unset)"))

    def _path_preview() -> str:
        path = os.environ.get("PATH", "")
        parts = path.split(os.pathsep)
        if len(parts) <= 3:
            return path or "(unset)"
        return os.pathsep.join(parts[:3]) + "  (... {} more entries)".format(len(parts) - 3)

    _add(env_rows, "PATH (head)", _path_preview)
    sections.append(("Environment variables", env_rows))

    # --- Time / timezone -----------------------------------------------------
    time_rows: List[Tuple[str, str]] = []

    def _utc_now() -> str:
        import datetime
        return datetime.datetime.utcnow().isoformat() + "Z"

    _add(time_rows, "UTC now", _utc_now)
    _add(time_rows, "tzname", lambda: " / ".join(time.tzname) if hasattr(time, "tzname") else "(unknown)")
    _add(time_rows, "monotonic clock res (us)",
         lambda: int(time.get_clock_info("monotonic").resolution * 1_000_000))
    sections.append(("Time", time_rows))

    # --- Frozen / PyInstaller ------------------------------------------------
    frozen_rows: List[Tuple[str, str]] = []
    _add(frozen_rows, "frozen", lambda: getattr(sys, "frozen", False))
    _add(frozen_rows, "_MEIPASS",
         lambda: getattr(sys, "_MEIPASS", "(not running under PyInstaller)"))
    sections.append(("Frozen / PyInstaller", frozen_rows))

    # --- pyfcstm package install --------------------------------------------
    pyf_rows: List[Tuple[str, str]] = []

    def _pyfcstm_version() -> str:
        import pyfcstm  # safe; pyfcstm/__init__.py is a one-liner
        return getattr(pyfcstm, "__version__", "(unknown)")

    def _pyfcstm_install_path() -> str:
        import pyfcstm
        return os.path.dirname(os.path.abspath(pyfcstm.__file__))

    _add(pyf_rows, "version", _pyfcstm_version)
    _add(pyf_rows, "install path", _pyfcstm_install_path)
    sections.append(("pyfcstm package", pyf_rows))

    # --- Git checkout (when running from a dev tree) -------------------------
    git_rows = _collect_git_facts()
    if git_rows:
        sections.append(("Git checkout", git_rows))

    return sections


def _find_git_dir() -> Optional[str]:
    """Return the ``.git`` path nearest to the pyfcstm install, or ``None``."""
    try:
        import pyfcstm
        path = os.path.dirname(os.path.abspath(pyfcstm.__file__))
    except BaseException:  # noqa: BLE001 - import-time failures are out of scope here
        path = os.getcwd()
    for _ in range(6):  # walk up at most six levels
        candidate = os.path.join(path, ".git")
        if os.path.isdir(candidate) or os.path.isfile(candidate):
            return candidate
        new_path = os.path.dirname(path)
        if new_path == path:
            break
        path = new_path
    return None


def _collect_git_facts() -> List[Tuple[str, str]]:
    """
    Best-effort git introspection (branch / commit / dirty flag).

    Returns ``[]`` when the diagnostics module is not running from a
    development checkout (no ``.git`` reachable, ``git`` binary
    missing, subprocess fails, ...). Never raises.
    """
    git_dir = _find_git_dir()
    if not git_dir:
        return []
    repo_root = os.path.dirname(git_dir)

    rows: List[Tuple[str, str]] = []

    def _run_git(*args: str) -> str:
        try:
            import subprocess
            result = subprocess.run(
                ["git", *args],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip().splitlines()
                tail = stderr[-1] if stderr else "exit {}".format(result.returncode)
                return "(git error: {})".format(tail)
            return (result.stdout or "").strip() or "(empty)"
        except BaseException as exc:  # noqa: BLE001 - subprocess can fail in many ways
            return "(unavailable: {}: {})".format(type(exc).__name__, exc)

    rows.append(("repo root", repo_root))
    rows.append(("branch", _run_git("rev-parse", "--abbrev-ref", "HEAD")))
    rows.append(("commit", _run_git("rev-parse", "HEAD")))

    def _dirty_flag() -> str:
        status = _run_git("status", "--porcelain")
        if status.startswith("(unavailable") or status.startswith("(git error"):
            return status
        return "yes" if status and status != "(empty)" else "no"

    rows.append(("dirty", _dirty_flag()))
    return rows


def _print_environment(painter: _Painter) -> None:
    """Print the (deep) environment dump.

    Wrapped in a top-level ``try/except`` in :func:`run_smoke_test`,
    so a defect inside the collector cannot prevent the case battery
    from running. Each individual fact reader is also defensive.
    """
    sections = _collect_environment_facts()
    for section_label, rows in sections:
        painter.echo(painter.style(section_label, fg="cyan", bold=True))
        if not rows:
            painter.echo("  (no facts collected)")
            painter.echo("")
            continue
        # Right-pad labels for readability.
        label_width = max(len(label) for label, _ in rows)
        for label, value in rows:
            label_styled = painter.style(label.ljust(label_width), fg="white", bold=True)
            painter.echo("  " + label_styled + " : " + value)
        painter.echo("")


def _print_group_header(painter: _Painter, label: str) -> None:
    bar = painter.style("|", fg="cyan", bold=True)
    painter.echo(bar + " " + painter.style(label, fg="cyan", bold=True))


def _print_pass(painter: _Painter, result: SmokeResult) -> None:
    tag = painter.style("[PASS]", fg="green", bold=True)
    name = painter.style(result.case.name, fg="white", bold=True)
    sep = painter.style("::", fg="white")
    painter.echo("  {tag} {name} {sep} {method} ({elapsed:.1f} ms)".format(
        tag=tag, name=name, sep=sep, method=result.case.method,
        elapsed=result.elapsed_ms,
    ))


def _print_fail(painter: _Painter, result: SmokeResult) -> None:
    tag = painter.style("[FAIL]", fg="red", bold=True)
    name = painter.style(result.case.name, fg="white", bold=True)
    sep = painter.style("::", fg="white")
    painter.echo("  {tag} {name} {sep} {method} ({elapsed:.1f} ms)".format(
        tag=tag, name=name, sep=sep, method=result.case.method,
        elapsed=result.elapsed_ms,
    ))
    label = painter.style("        ↳", fg="red")
    if result.error is not None:
        category = type(result.error).__name__
        message = str(result.error) or "(no error message)"
        painter.echo(
            "{prefix} category: {value}".format(
                prefix=label, value=painter.style(category, fg="yellow", bold=True),
            )
        )
        painter.echo(
            "{prefix} message:  {value}".format(
                prefix=label, value=painter.style(message, fg="yellow"),
            )
        )
    if result.error_traceback:
        painter.echo("{prefix} traceback (most actionable frames):".format(prefix=label))
        for tb_line in _format_traceback(result.error, result.error_traceback):
            painter.echo("           " + tb_line)
    if result.case.remediation:
        painter.echo(
            "{prefix} remediation: {value}".format(
                prefix=label,
                value=painter.style(result.case.remediation, fg="green"),
            )
        )


def _print_summary(
    painter: _Painter, results: List[SmokeResult], elapsed: float
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = total - passed
    painter.echo("")
    painter.echo(painter.style("=" * 70, fg="cyan", dim=True))
    if failed == 0:
        painter.echo(
            painter.style("Smoke test summary: ", fg="cyan", bold=True)
            + painter.style("{} PASS".format(passed), fg="green", bold=True)
            + " (out of {}, {:.2f}s wall)".format(total, elapsed)
        )
        painter.echo(
            painter.style(
                "All checks passed - the install can run pyfcstm features without "
                "any extra setup.",
                fg="green",
            )
        )
    else:
        painter.echo(
            painter.style("Smoke test summary: ", fg="cyan", bold=True)
            + painter.style("{} PASS".format(passed), fg="green", bold=True)
            + ", "
            + painter.style("{} FAIL".format(failed), fg="red", bold=True)
            + " (out of {}, {:.2f}s wall)".format(total, elapsed)
        )
        painter.echo(painter.style("Failed cases:", fg="red", bold=True))
        for result in results:
            if result.status == "FAIL":
                painter.echo(
                    "  - "
                    + painter.style(result.case.name, fg="red", bold=True)
                    + ": "
                    + (str(result.error) if result.error else "(no error)")
                )
    painter.echo(painter.style("=" * 70, fg="cyan", dim=True))


# --------------------------------------------------------------------------- #
# Public runner.
# --------------------------------------------------------------------------- #


def _run_one(case: SmokeCase) -> SmokeResult:
    """Run one case under maximally defensive isolation.

    No exception escapes - including ``KeyboardInterrupt`` and
    ``SystemExit`` - because the smoke runner's whole purpose is to keep
    going when individual checks blow up. The captured traceback is
    formatted via :func:`traceback.format_exc` so we can show the user
    the same frames the case would print under normal invocation.
    """
    started = time.time()
    try:
        case.func()
    except BaseException as exc:  # noqa: BLE001 - intentional broad catch
        elapsed = (time.time() - started) * 1000
        return SmokeResult(
            case=case,
            status="FAIL",
            elapsed_ms=elapsed,
            error=exc,
            error_traceback=traceback.format_exc(),
        )
    elapsed = (time.time() - started) * 1000
    return SmokeResult(case=case, status="PASS", elapsed_ms=elapsed)


def run_smoke_test() -> int:
    """
    Run every registered smoke-test case and print a structured PASS/FAIL
    report on stdout.

    The runner never propagates exceptions out of individual cases - even
    fatal errors during ``KeyboardInterrupt`` / ``SystemExit`` are caught
    and rendered as ``[FAIL]`` rows. The exit code returned to the caller
    is the count of FAIL cases (``0`` on a fully-clean install). The CLI
    glue translates that into the process exit code.

    :return: Number of failed cases.
    :rtype: int

    Example::

        >>> from pyfcstm.diagnostics import run_smoke_test
        >>> exit_code = run_smoke_test()  # doctest: +SKIP
    """
    painter = _Painter()
    painter.echo(painter.style("=" * 70, fg="cyan", dim=True))
    painter.echo(painter.style("pyfcstm --smoke-test", fg="cyan", bold=True))
    painter.echo(painter.style("=" * 70, fg="cyan", dim=True))
    painter.echo("")

    # The environment block is best-effort: even reading sys / platform
    # is cheap enough to never realistically fail, but we still wrap it.
    try:
        _print_environment(painter)
    except BaseException:  # pragma: no cover - defensive
        painter.echo("(environment introspection failed; continuing)")
        painter.echo("")

    try:
        groups = _build_case_groups()
    except BaseException as exc:  # pragma: no cover - case definitions live in this module
        painter.echo(painter.style(
            "Catastrophic: smoke runner failed to assemble its own case list: {!r}".format(exc),
            fg="red", bold=True,
        ))
        return 1

    overall_started = time.time()
    all_results: List[SmokeResult] = []
    for group_label, cases in groups:
        _print_group_header(painter, group_label)
        for case in cases:
            result = _run_one(case)
            if result.status == "PASS":
                _print_pass(painter, result)
            else:
                _print_fail(painter, result)
            all_results.append(result)
        painter.echo("")
    elapsed = time.time() - overall_started
    _print_summary(painter, all_results, elapsed)
    return sum(1 for r in all_results if r.status == "FAIL")
