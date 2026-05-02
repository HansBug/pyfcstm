"""
Unit tests for :mod:`pyfcstm.convert.sysdesim.render`.

These tests exercise the SVG renderer end-to-end through the embedded
``mini-racer`` runtime. They use a synthetic SysDeSim XML fixture (the
canonical phase9_11 fixture, also used by :mod:`test_static_check`) so the
test suite remains self-contained and ships no real user data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyfcstm.convert.sysdesim import build_sysdesim_phase10_report
from pyfcstm.convert.sysdesim import render as render_module
from pyfcstm.convert.sysdesim.render import (
    SysdesimRenderError,
    _build_timeline_json,
    render_sysdesim_timeline_svg,
)


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
