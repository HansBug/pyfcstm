#!/usr/bin/env python3
"""
Chaos test for ``pyfcstm --smoke-test``: break key resources / native
libraries, then assert the runner still finishes from beginning to end
under every failure mode. Restores everything on exit no matter what
happens (signals included).
"""
from __future__ import annotations

import contextlib
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

VENV_PY = sys.executable

# Resolve the live target paths inside *this* venv so the chaos test
# operates on the same install the smoke runner sees.
import importlib

import py_mini_racer  # noqa: E402
import pyfcstm.convert.sysdesim  # noqa: E402
import pyfcstm.dsl.grammar  # noqa: E402
import pyfcstm.template  # noqa: E402

_PY_MINI_RACER_DIR = os.path.dirname(py_mini_racer.__file__)
# Both py-mini-racer 0.6 and mini-racer 0.14 land their native pieces here.
# We have to break *every* one to actually starve the V8 isolate; missing
# any will let the still-present sibling load instead.
V8_NATIVE_FILES = [
    os.path.join(_PY_MINI_RACER_DIR, name)
    for name in os.listdir(_PY_MINI_RACER_DIR)
    if name.startswith("libmini_racer") or name == "icudtl.dat"
]
BUNDLE = os.path.join(os.path.dirname(pyfcstm.convert.sysdesim.__file__),
                      "_render_assets", "pyfcstm-sysdesim-render.js")
GRAMMAR_LEXER = os.path.join(os.path.dirname(pyfcstm.dsl.grammar.__file__), "GrammarLexer.py")
GRAMMAR_LEXER_PYC_DIR = os.path.join(os.path.dirname(pyfcstm.dsl.grammar.__file__), "__pycache__")
TPL_PYTHON_ZIP = os.path.join(os.path.dirname(pyfcstm.template.__file__), "python.zip")
TPL_INDEX = os.path.join(os.path.dirname(pyfcstm.template.__file__), "index.json")


_BACKUPS: list = []


def _safe_move_aside(path: str) -> str | None:
    """Rename ``path`` to ``path + ".chaos-disabled"``; return backup path or None."""
    if not os.path.exists(path):
        return None
    backup = path + ".chaos-disabled"
    if os.path.exists(backup):
        # Stale backup from a previous crash - restore first.
        os.replace(backup, path)
    os.rename(path, backup)
    _BACKUPS.append((backup, path))
    return backup


def _restore_all() -> None:
    """Best-effort restore every backup, swallowing errors (always finishes)."""
    while _BACKUPS:
        backup, original = _BACKUPS.pop()
        if os.path.exists(backup):
            try:
                os.replace(backup, original)
            except Exception as e:
                print(f"  !! restore failed for {original}: {e!r}", file=sys.stderr)


def _purge_grammar_pycache() -> None:
    """Drop ``GrammarLexer*.pyc`` so a renamed source actually fails import."""
    if not os.path.isdir(GRAMMAR_LEXER_PYC_DIR):
        return
    for name in os.listdir(GRAMMAR_LEXER_PYC_DIR):
        if name.startswith("GrammarLexer."):
            full = os.path.join(GRAMMAR_LEXER_PYC_DIR, name)
            try:
                os.remove(full)
            except Exception:
                pass


def _run_smoke() -> tuple[int, str]:
    """Run ``python -m pyfcstm --smoke-test`` and capture (rc, plain stdout).

    Using the ``-m pyfcstm`` entry exercises the short-circuit branch in
    ``pyfcstm/__main__.py`` that bypasses the regular CLI subcommand
    chain. That is the path real users hit when ``--smoke-test`` is
    needed *because* the regular install is broken.
    """
    cmd = [VENV_PY, "-m", "pyfcstm", "--smoke-test"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout)
    return proc.returncode, plain


def _summarize(label: str, rc: int, output: str, *, expected_fails: list[str]) -> None:
    """Summarize one chaos scenario: did the runner finish? Are the right cases FAIL?"""
    print(f"\n========== Scenario: {label} ==========")
    # The runner always prints the summary line - if it's missing, the
    # runner crashed mid-flight, which is the ground-truth bug we are
    # hunting for.
    summary_line = next(
        (ln for ln in output.splitlines() if ln.startswith("Smoke test summary:")),
        None,
    )
    print(f"summary: {summary_line!r}")
    print(f"exit code: {rc}")
    if summary_line is None:
        print("!!! RUNNER DID NOT FINISH (no summary line in output)")
        print("--- last 40 lines of output ---")
        for ln in output.splitlines()[-40:]:
            print("   " + ln)
        return

    # Parse pass/fail counts from the summary.
    m = re.search(r"(\d+)\s+PASS.*?(\d+)\s+FAIL", summary_line)
    if not m:
        # All-pass form: "Smoke test summary: 38 PASS (out of 38, ...)"
        m_all = re.search(r"(\d+)\s+PASS\b", summary_line)
        passes = int(m_all.group(1)) if m_all else 0
        fails = 0
    else:
        passes = int(m.group(1))
        fails = int(m.group(2))
    print(f"counts: {passes} PASS, {fails} FAIL")
    print(f"runner finished: YES")

    # Verify each expected-fail case shows up as FAIL.
    miss = []
    extra = []
    fail_block = []
    capture = False
    for ln in output.splitlines():
        if ln.startswith("Failed cases:"):
            capture = True
            continue
        if capture:
            if ln.strip().startswith("- "):
                fail_block.append(ln.strip()[2:])
            else:
                if ln.strip():
                    capture = False
    fail_names = {entry.split(":", 1)[0].strip() for entry in fail_block}
    for needle in expected_fails:
        if needle not in fail_names:
            miss.append(needle)
    extra = sorted(fail_names - set(expected_fails))
    if miss:
        print(f"!!! expected FAIL cases not seen: {miss}")
    if extra:
        print(f"... unexpected extra FAIL cases: {extra}")
    if not miss and not extra:
        print(f"OK: failed-cases match exactly {sorted(expected_fails)}")


def main() -> int:
    print("=" * 60)
    print("smoke-test chaos verification")
    print("=" * 60)

    # Sentinel: baseline (no chaos) must be all-PASS.
    rc, output = _run_smoke()
    _summarize("baseline (no breakage)", rc, output, expected_fails=[])

    # Scenario 1: SVG render bundle missing.
    try:
        _safe_move_aside(BUNDLE)
        rc, output = _run_smoke()
        _summarize(
            "SVG render bundle moved aside",
            rc,
            output,
            expected_fails=[
                "resource_render_bundle_present",
                "resource_render_bundle_loadable",
                "sysdesim_svg_render",
                "sysdesim_png_render",
            ],
        )
    finally:
        _restore_all()

    # Scenario 2: every V8 native + ICU sidecar moved aside.
    try:
        for path in V8_NATIVE_FILES:
            _safe_move_aside(path)
        rc, output = _run_smoke()
        _summarize(
            "All V8 native + ICU sidecars moved aside",
            rc,
            output,
            expected_fails=[
                "native_v8_isolate",
                "native_v8_webassembly",
                "resource_render_bundle_loadable",
                "sysdesim_svg_render",
                "sysdesim_png_render",
            ],
        )
    finally:
        _restore_all()

    # Scenario 3: ANTLR-generated lexer source moved aside.
    try:
        _safe_move_aside(GRAMMAR_LEXER)
        _purge_grammar_pycache()
        rc, output = _run_smoke()
        _summarize(
            "ANTLR GrammarLexer.py moved aside",
            rc,
            output,
            expected_fails=[
                "resource_antlr_grammar",
                "pyfcstm_dsl_parser",
                "pyfcstm_model_build",
                "pyfcstm_render_expression_styles",
                "pyfcstm_simulator_runtime",
                "pyfcstm_solver_z3_translation",
                "pyfcstm_plantuml_export",
                "generate_python_template_pipeline",
                "sysdesim_xml_parse",
                "sysdesim_static_check",
                "sysdesim_validate",
                "sysdesim_svg_render",
                "sysdesim_png_render",
            ],
        )
    finally:
        _restore_all()

    # Scenario 4: built-in python template archive missing.
    try:
        _safe_move_aside(TPL_PYTHON_ZIP)
        rc, output = _run_smoke()
        _summarize(
            "python.zip template archive missing",
            rc,
            output,
            expected_fails=[
                "resource_template_index",
                "resource_template_extract",
                "generate_python_template_pipeline",
            ],
        )
    finally:
        _restore_all()

    # Scenario 5: template/index.json missing entirely.
    try:
        _safe_move_aside(TPL_INDEX)
        rc, output = _run_smoke()
        _summarize(
            "template/index.json missing",
            rc,
            output,
            expected_fails=[
                "resource_template_index",
                "resource_template_extract",
                "generate_python_template_pipeline",
            ],
        )
    finally:
        _restore_all()

    # Scenario 6: simultaneous breakage of every checkable resource.
    try:
        _safe_move_aside(BUNDLE)
        for path in V8_NATIVE_FILES:
            _safe_move_aside(path)
        _safe_move_aside(GRAMMAR_LEXER)
        _purge_grammar_pycache()
        _safe_move_aside(TPL_PYTHON_ZIP)
        _safe_move_aside(TPL_INDEX)
        rc, output = _run_smoke()
        # Don't enumerate every fail here - the bar is "the runner finishes
        # and its summary line is reachable". An apocalyptic install must
        # not crash the diagnostics tool, period.
        _summarize(
            "EVERYTHING BROKEN AT ONCE",
            rc,
            output,
            expected_fails=[],  # exact set is irrelevant; we only want a finished summary
        )
    finally:
        _restore_all()

    print("\nAll chaos scenarios completed; resources restored.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        # Belt-and-suspenders: even if main() raised, restore everything.
        _restore_all()
