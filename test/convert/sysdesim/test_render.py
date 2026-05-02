"""
Unit tests for :mod:`pyfcstm.convert.sysdesim.render`.

These tests exercise the SVG and PNG renderers end-to-end through the
embedded ``mini-racer`` runtime. They use a synthetic SysDeSim XML fixture
(the canonical phase9_11 fixture, also used by :mod:`test_static_check`) so
the test suite remains self-contained and ships no real user data.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from pyfcstm.convert.sysdesim import build_sysdesim_phase10_report
from pyfcstm.convert.sysdesim import render as render_module
from pyfcstm.convert.sysdesim.render import (
    SysdesimRenderError,
    _build_timeline_json,
    _ensure_png_runtime,
    render_sysdesim_timeline_png,
    render_sysdesim_timeline_svg,
)


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_dimensions(data: bytes) -> tuple:
    """Parse width/height from the PNG IHDR chunk."""
    assert data[:8] == _PNG_MAGIC, "missing PNG magic"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _build_parallel_timeline_xml(tmp_path: Path) -> Path:
    """Reuse the canonical phase9_11 fixture for renderer tests."""
    from test.convert.sysdesim.test_phase9_11 import _build_parallel_timeline_xml as _orig

    return _orig(tmp_path)


@pytest.mark.unittest
def test_build_timeline_json_has_expected_top_level_shape(tmp_path: Path):
    """The JSON serializer flattens Phase10 reports into the documented shape."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    timeline = _build_timeline_json(phase10)
    assert isinstance(timeline.get("title"), str)
    assert isinstance(timeline.get("lifelines"), list)
    assert isinstance(timeline.get("steps"), list)
    assert isinstance(timeline.get("temporal_constraints"), list)
    # The fixture has at least 2 lifelines (control + module) and many steps.
    assert len(timeline["lifelines"]) >= 2
    assert len(timeline["steps"]) >= 5
    # Each lifeline carries a display_name.
    for lifeline in timeline["lifelines"]:
        assert "id" in lifeline
        assert "display_name" in lifeline


@pytest.mark.unittest
def test_render_returns_svg_with_xml_prolog(tmp_path: Path):
    """The default render path returns a valid-looking SVG document."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    svg = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    assert svg.startswith('<?xml')
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "viewBox" in svg


@pytest.mark.unittest
def test_render_preserves_signal_names_and_lifeline_labels(tmp_path: Path):
    """The rendered SVG should mention every imported signal name + lifeline label."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    svg = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    # The fixture's lifelines are 控制 / 模块 (Chinese names), kept verbatim
    # in the rendered SVG.
    assert "控制" in svg
    assert "模块" in svg
    # The fixture's interaction is named "Scenario 1"; title should appear.
    assert "Scenario 1" in svg
    # Signal names from the fixture.
    for sig in ("Sig1", "Sig2", "Sig4", "Sig9"):
        assert sig in svg, "expected {} in rendered SVG".format(sig)


@pytest.mark.unittest
def test_render_accepts_pre_built_phase10_report(tmp_path: Path):
    """Caller can pass a Phase10 report directly, skipping XML reimport."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    svg = render_sysdesim_timeline_svg(phase10_report=phase10, title="custom-title")
    assert "custom-title" in svg


@pytest.mark.unittest
def test_render_requires_input():
    """Calling without xml_path or phase10_report raises ValueError."""
    with pytest.raises(ValueError):
        render_sysdesim_timeline_svg()


@pytest.mark.unittest
def test_render_supports_theme_override(tmp_path: Path):
    """Theme overrides flow through to the JS renderer."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    svg = render_sysdesim_timeline_svg(
        xml_path=str(xml_file),
        theme={"actorFill": "#ff00ff"},
    )
    assert "#ff00ff" in svg


@pytest.mark.unittest
def test_renderer_caches_runtime_across_calls(tmp_path: Path):
    """The mini-racer context is loaded once and reused across calls."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    # Reset the module-level cache so the first call instantiates fresh.
    render_module._runtime_cached = None
    svg1 = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    cached_after_first = render_module._runtime_cached
    assert cached_after_first is not None
    svg2 = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    assert render_module._runtime_cached is cached_after_first
    # Both calls produce the same byte-for-byte SVG (deterministic renderer).
    assert svg1 == svg2


@pytest.mark.unittest
def test_render_lifelines_have_actor_boxes_and_dashed_lines(tmp_path: Path):
    """Each lifeline gets exactly one rounded-actor rect and a dashed line."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    svg = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    # Two lifelines in this fixture -> two ``rx="6"`` actor rectangles and
    # at least two dashed lifelines.
    assert svg.count('rx="6"') >= 2
    assert svg.count('stroke-dasharray="4 4"') >= 2


@pytest.mark.unittest
def test_render_includes_message_arrows_with_numbered_labels(tmp_path: Path):
    """Cross-lifeline messages render as numbered ``N:SignalName`` text."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    svg = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    # First message should be ``1:Sig1``.
    assert "1:Sig1" in svg


@pytest.mark.unittest
def test_render_includes_temporal_constraint_brackets(tmp_path: Path):
    """The fixture's DurationConstraint surfaces as a right-margin bracket label."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    svg = render_sysdesim_timeline_svg(xml_path=str(xml_file))
    # The fixture has a ``Sig2 -> Sig4 = 10s`` DurationConstraint; the
    # renderer prints either an ``==`` form or a literal ``10s`` label.
    assert "10s" in svg


# =============================================================================
# PNG rasterizer tests
# =============================================================================


@pytest.mark.unittest
def test_render_png_returns_png_magic_bytes(tmp_path: Path):
    """The PNG renderer returns bytes prefixed with the standard PNG magic."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    png = render_sysdesim_timeline_png(xml_path=str(xml_file))
    assert isinstance(png, bytes)
    assert png[:8] == _PNG_MAGIC
    width, height = _png_dimensions(png)
    # The fixture is at least a couple hundred pixels in both directions
    # because it has actor boxes, several rows, and right-margin annotations.
    assert width > 100
    assert height > 100


@pytest.mark.unittest
def test_render_png_accepts_pre_built_phase10_report(tmp_path: Path):
    """Caller can pass a Phase10 report directly to skip XML reimport."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    phase10 = build_sysdesim_phase10_report(str(xml_file))
    png = render_sysdesim_timeline_png(phase10_report=phase10, title="custom-title")
    assert png[:8] == _PNG_MAGIC


@pytest.mark.unittest
def test_render_png_requires_input():
    """Calling without xml_path or phase10_report raises ValueError."""
    with pytest.raises(ValueError):
        render_sysdesim_timeline_png()


@pytest.mark.unittest
def test_render_png_caches_runtime_across_calls(tmp_path: Path):
    """Repeated PNG calls reuse the same MiniRacer context and PNG init state."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    render_module._runtime_cached = None
    png1 = render_sysdesim_timeline_png(xml_path=str(xml_file))
    cached_after_first = render_module._runtime_cached
    assert cached_after_first is not None
    ctx_first, _version = cached_after_first
    assert getattr(ctx_first, "_pyfcstm_png_initialized", False) is True
    png2 = render_sysdesim_timeline_png(xml_path=str(xml_file))
    assert render_module._runtime_cached is cached_after_first
    # Deterministic renderer: byte-identical output across repeated calls.
    assert png1 == png2


@pytest.mark.unittest
def test_render_png_supports_theme_override(tmp_path: Path):
    """Theme overrides flow through to the JS PNG renderer."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    plain = render_sysdesim_timeline_png(xml_path=str(xml_file))
    themed = render_sysdesim_timeline_png(
        xml_path=str(xml_file),
        theme={"actorFill": "#ff00ff"},
    )
    assert themed[:8] == _PNG_MAGIC
    # Theme override must reach the SVG layout step, producing different bytes.
    assert plain != themed


@pytest.mark.unittest
def test_render_png_supports_resvg_options(tmp_path: Path):
    """``resvg_options`` such as ``fitTo`` change the rasterized output."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    plain = render_sysdesim_timeline_png(xml_path=str(xml_file))
    plain_w, plain_h = _png_dimensions(plain)
    upscaled = render_sysdesim_timeline_png(
        xml_path=str(xml_file),
        resvg_options={"fitTo": {"mode": "zoom", "value": 2}},
    )
    upscaled_w, upscaled_h = _png_dimensions(upscaled)
    assert upscaled[:8] == _PNG_MAGIC
    # ``fitTo: zoom 2x`` doubles both dimensions of the rasterized output.
    assert upscaled_w == plain_w * 2
    assert upscaled_h == plain_h * 2


@pytest.mark.unittest
def test_render_png_supports_font_files(tmp_path: Path):
    """``font_files`` paths are read and forwarded to the JS renderer."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    # Re-use the bundled DejaVu Sans as a stand-in user font: the test only
    # has to confirm the file path round-trips through the JS layer without
    # raising. A second-pass render with the extra font produces a valid PNG.
    extra_font_path = (
        Path(__file__).resolve().parents[3]
        / "js"
        / "sysdesim_render"
        / "src"
        / "fonts"
        / "DejaVuSans.ttf"
    )
    if not extra_font_path.exists():
        pytest.skip("bundled DejaVu Sans not present at expected source path")
    png = render_sysdesim_timeline_png(
        xml_path=str(xml_file),
        font_files=[str(extra_font_path)],
    )
    assert png[:8] == _PNG_MAGIC


@pytest.mark.unittest
def test_render_png_supports_font_buffers(tmp_path: Path):
    """In-memory ``font_buffers`` bytes are accepted and forwarded."""
    xml_file = _build_parallel_timeline_xml(tmp_path)
    extra_font_path = (
        Path(__file__).resolve().parents[3]
        / "js"
        / "sysdesim_render"
        / "src"
        / "fonts"
        / "DejaVuSans.ttf"
    )
    if not extra_font_path.exists():
        pytest.skip("bundled DejaVu Sans not present at expected source path")
    font_bytes = extra_font_path.read_bytes()
    png = render_sysdesim_timeline_png(
        xml_path=str(xml_file),
        font_buffers=[font_bytes],
    )
    assert png[:8] == _PNG_MAGIC


@pytest.mark.unittest
def test_ensure_png_runtime_is_idempotent(tmp_path: Path):
    """Calling _ensure_png_runtime twice on the same context is a no-op."""
    render_module._runtime_cached = None
    # First render kicks off init.
    xml_file = _build_parallel_timeline_xml(tmp_path)
    render_sysdesim_timeline_png(xml_path=str(xml_file))
    ctx, _version = render_module._runtime_cached
    assert getattr(ctx, "_pyfcstm_png_initialized", False) is True
    # Calling again should short-circuit.
    _ensure_png_runtime(ctx)
    assert getattr(ctx, "_pyfcstm_png_initialized", False) is True


@pytest.mark.unittest
def test_ensure_png_runtime_surfaces_js_init_error(monkeypatch, tmp_path: Path):
    """If the JS-side init enters the ``error`` state, we raise SysdesimRenderError."""
    render_module._runtime_cached = None
    xml_file = _build_parallel_timeline_xml(tmp_path)
    # Force fresh runtime then break startPngInit before ensure runs.
    render_sysdesim_timeline_svg(xml_path=str(xml_file))
    ctx, _version = render_module._runtime_cached

    class _FakeCtx:
        """Drop-in stand-in that simulates a JS init that errors out."""

        def eval(self, code: str):
            stripped = code.strip()
            if stripped == "PyfcstmSysdesim.startPngInit()":
                return "pending"
            if stripped == "PyfcstmSysdesim.pngInitState()":
                return "error"
            if stripped == "PyfcstmSysdesim.isPngReady()":
                raise RuntimeError("simulated resvg-wasm init failure")
            return None

    fake_ctx = _FakeCtx()
    with pytest.raises(SysdesimRenderError, match="resvg-wasm init failed"):
        _ensure_png_runtime(fake_ctx)
    # Cached real context still untouched.
    assert render_module._runtime_cached is not None
