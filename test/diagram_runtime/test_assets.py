"""Runtime checks for the PR-A shared renderer and resvg asset boundary."""

import re
import math

import pytest

from pyfcstm.diagram_runtime import DiagramAssetEngine


pytestmark = pytest.mark.unittest


def _range(line):
    return {
        "start": {"line": line, "character": 0},
        "end": {"line": line, "character": 1},
    }


def _state(name, qualified_name, line):
    return {
        "id": "state:" + qualified_name,
        "name": name,
        "qualifiedName": qualified_name,
        "pseudo": False,
        "leaf": True,
        "root": False,
        "range": _range(line),
        "events": [],
        "actions": [],
        "transitions": [],
        "children": [],
    }


def _request():
    first = _state("A", "Machine.A", 1)
    second = _state("B", "Machine.B", 2)
    root = {
        "id": "state:Machine",
        "name": "Machine",
        "qualifiedName": "Machine",
        "pseudo": False,
        "leaf": False,
        "root": True,
        "range": _range(0),
        "events": [],
        "actions": [],
        "transitions": [
            {
                "id": "init",
                "sourceLabel": "[*]",
                "targetLabel": "A",
                "label": "",
                "effectLines": [],
                "forced": False,
                "sourceKind": "init",
                "targetKind": "state",
                "range": _range(3),
                "targetStatePath": ["Machine", "A"],
            },
            {
                "id": "a-b",
                "sourceLabel": "A",
                "targetLabel": "B",
                "label": "",
                "effectLines": [],
                "forced": False,
                "sourceKind": "state",
                "targetKind": "state",
                "range": _range(4),
                "sourceStatePath": ["Machine", "A"],
                "targetStatePath": ["Machine", "B"],
            },
        ],
        "children": [first, second],
    }
    return {
        "diagram": {
            "kind": "diagram",
            "filePath": "",
            "machineName": "Machine",
            "summary": {
                "variables": 0,
                "states": 3,
                "events": 0,
                "transitions": 2,
                "actions": 0,
            },
            "variables": [],
            "eventLegend": [],
            "rootState": root,
        },
        "options": {"direction": "LR", "detailLevel": "normal"},
        "palette": "default",
        "mode": "light",
    }


def test_renderer_is_deterministic_and_escapes_hostile_labels():
    pytest.importorskip("py_mini_racer")
    request = _request()
    request["diagram"]["rootState"]["children"][0]["displayName"] = (
        "启动 <ready> & 继续"
    )
    engine = DiagramAssetEngine()
    first = engine.render_svg(request)
    second = engine.render_svg(request)
    assert first == second
    assert 'orient="auto"' in first
    assert 'refX="10"' in first
    assert "auto-start-reverse" not in first
    assert "启动 &lt;ready&gt; &amp; 继续" in first
    assert "</script><script>" not in first


def test_resvg_png_and_vector_expansion_keep_marker_direction():
    pytest.importorskip("py_mini_racer")
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="240" height="240">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
        markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>
      <path d="M30,60 L190,60" marker-end="url(#arrow)"/>
      <path d="M180,30 L180,190" marker-end="url(#arrow)"/>
      <path d="M210,180 L50,180" marker-end="url(#arrow)"/>
      <path d="M60,210 L60,50" marker-end="url(#arrow)"/>
    </svg>
    """
    engine = DiagramAssetEngine()
    png = engine.render_png(svg)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    normalized = engine.expand_svg(svg)
    assert "<marker" not in normalized
    transforms = re.findall(r'transform="matrix\(([^)]+)\)"', normalized)
    assert len(transforms) == 4
    expected = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for transform, direction in zip(transforms, expected):
        values = [float(part) for part in transform.split()]
        length = (values[0] ** 2 + values[1] ** 2) ** 0.5
        dot = (values[0] * direction[0] + values[1] * direction[1]) / length
        assert dot > 0.999


def test_resvg_marker_tip_lands_on_path_endpoint():
    pytest.importorskip("py_mini_racer")
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="240" height="240">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
        markerWidth="10" markerHeight="10" orient="auto"
        markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>
      <path d="M30,60 L190,60" marker-end="url(#arrow)"/>
      <path d="M180,30 L180,190" marker-end="url(#arrow)"/>
      <path d="M210,180 L50,180" marker-end="url(#arrow)"/>
      <path d="M60,210 L60,50" marker-end="url(#arrow)"/>
    </svg>
    """
    endpoints = [(190.0, 60.0), (180.0, 190.0), (50.0, 180.0), (60.0, 50.0)]
    engine = DiagramAssetEngine()
    normalized = engine.expand_svg(svg)
    transforms = re.findall(r'transform="matrix\(([^)]+)\)"', normalized)
    assert len(transforms) == len(endpoints)
    for transform, endpoint in zip(transforms, endpoints):
        a, b, c, d, tx, ty = [float(part) for part in transform.split()]
        tip = (tx + a * 10 + c * 5, ty + b * 10 + d * 5)
        assert math.hypot(tip[0] - endpoint[0], tip[1] - endpoint[1]) < 1e-3


def test_render_png_rejects_non_finite_scale():
    pytest.importorskip("py_mini_racer")
    engine = DiagramAssetEngine()
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    for scale in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite positive"):
            engine.render_png(svg, scale=scale)
