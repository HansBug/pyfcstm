"""Runtime checks for the PR-A shared renderer and resvg asset boundary."""

import re
import math
import builtins
import hashlib

import pytest

from pyfcstm.diagram import (
    DiagramAssetEngine,
    DiagramAssetError,
    DiagramEngineConflictError,
    DiagramEngineMetadataError,
)


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


def test_missing_runtime_asset_reports_recovery_instructions(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def missing_renderer(package, resource):
        if resource == "renderer.js":
            return None
        return real_get_data(package, resource)

    monkeypatch.setattr(engine_module.pkgutil, "get_data", missing_renderer)
    with pytest.raises(
        DiagramAssetError,
        match=r"renderer\.js.*expected packaged resource is missing.*make build_assets",
    ):
        DiagramAssetEngine()


def test_missing_runtime_asset_reports_issue_url_for_installed_package(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def missing_renderer(package, resource):
        if resource == "renderer.js":
            return None
        return real_get_data(package, resource)

    monkeypatch.setattr(engine_module.pkgutil, "get_data", missing_renderer)
    monkeypatch.setattr(engine_module, "_is_development_checkout", lambda: False)
    with pytest.raises(
        DiagramAssetError,
        match=r"renderer\.js.*expected packaged resource is missing.*github.com/HansBug/pyfcstm/issues",
    ):
        DiagramAssetEngine()


def test_invalid_runtime_asset_reports_data_failure(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def invalid_renderer(package, resource):
        if resource == "renderer.js":
            return b"\xff\xfe"
        return real_get_data(package, resource)

    monkeypatch.setattr(engine_module.pkgutil, "get_data", invalid_renderer)
    with pytest.raises(
        DiagramAssetError,
        match=r"renderer\.js.*not valid UTF-8.*make build_assets",
    ):
        DiagramAssetEngine()


def test_missing_cjk_font_reports_recovery_instructions(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def missing_font(package, resource):
        if resource == "fonts/NotoSansSC-Regular.otf":
            return None
        return real_get_data(package, resource)

    monkeypatch.setattr(engine_module.pkgutil, "get_data", missing_font)
    engine = DiagramAssetEngine()
    with pytest.raises(
        DiagramAssetError,
        match=r"NotoSansSC-Regular\.otf.*expected packaged resource is missing.*make build_assets",
    ):
        engine.render_png(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
            '<text font-family="Noto Sans SC">中</text></svg>'
        )


def test_invalid_wasm_reports_resource_data_failure(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_asset_bytes = engine_module._asset_bytes

    def invalid_wasm(name):
        if name == "resvg.wasm":
            return b"not-wasm"
        return real_asset_bytes(name)

    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine_module, "_asset_bytes", invalid_wasm)
    with pytest.raises(
        DiagramAssetError,
        match=r"(?s)resvg\.wasm.*WASM initialization failed.*expected magic word.*make build_assets",
    ):
        engine.render_png(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
        )


def test_model_render_embeds_cjk_fallback_and_keeps_glyphs_distinct():
    request = _request()
    request["diagram"]["rootState"]["children"][0]["displayName"] = "启动"
    request["diagram"]["rootState"]["children"][1]["displayName"] = "状态"
    engine = DiagramAssetEngine()

    svg = engine.render_svg(request)
    assert "启动" in svg
    assert "状态" in svg
    assert "Noto Sans SC" in svg
    png = engine.render_png(svg)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    expanded = engine.expand_svg(svg)
    assert "启动" not in expanded
    assert "状态" not in expanded
    assert "<path" in expanded

    # Keep the canvas geometry fixed so a hash difference proves a different
    # glyph outline, rather than a different ELK box size. A missing CJK font
    # would make distinct characters collapse to the same replacement outline.
    def glyph_svg(text, family="Noto Sans SC", weight=None):
        weight_attr = ' font-weight="%s"' % weight if weight else ""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">'
            '<text x="4" y="28" font-family="%s" font-size="24"%s>%s</text>'
            "</svg>" % (family, weight_attr, text)
        )

    glyphs = ["状", "态", "中", "文", "�"]
    rendered = {text: engine.render_png(glyph_svg(text)) for text in glyphs}
    hashes = {text: hashlib.sha256(data).hexdigest() for text, data in rendered.items()}
    assert len(set(hashes.values())) == len(glyphs)
    expanded_hashes = {
        text: hashlib.sha256(
            engine.expand_svg(glyph_svg(text)).encode("utf-8")
        ).hexdigest()
        for text in glyphs
    }
    assert len(set(expanded_hashes.values())) == len(glyphs)
    assert (
        hashlib.sha256(engine.render_png(glyph_svg("状", weight=700))).hexdigest()
        != hashes["状"]
    )


def test_model_render_cjk_scripts_work_in_each_locked_locale_face():
    engine = DiagramAssetEngine()
    samples = {
        "sc": "中文",
        "tc": "繁體",
        "hk": "香港",
        "jp": "日本語",
        "kr": "한국어",
    }
    for locale, text in samples.items():
        family = "Noto Sans " + locale.upper()
        request = _request()
        request["cjkLocale"] = locale
        request["diagram"]["rootState"]["children"][0]["displayName"] = text
        model_svg = engine.render_svg(request)
        assert text in model_svg, locale
        assert family in model_svg, locale
        assert engine.render_png(model_svg).startswith(b"\x89PNG\r\n\x1a\n"), locale

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">'
            '<text x="4" y="28" font-family="%s" font-size="24">%s</text>'
            "</svg>" % (family, text)
        )
        png = engine.render_png(svg)
        assert png.startswith(b"\x89PNG\r\n\x1a\n"), locale
        expanded = engine.expand_svg(svg)
        assert text not in expanded, locale
        assert "<path" in expanded, locale


def test_long_cjk_model_label_expands_its_node_without_render_failure():
    request = _request()
    long_label = "这是一个非常长的中文状态标签用于验证布局不会溢出"
    request["diagram"]["rootState"]["children"][0]["displayName"] = long_label
    engine = DiagramAssetEngine()
    svg = engine.render_svg(request)
    assert long_label in svg
    match = re.search(
        r'<g data-fcstm-kind="state" data-fcstm-id="Machine\.A".*?'
        r'<rect x="[0-9.]+" y="[0-9.]+" width="([0-9.]+)"',
        svg,
        re.S,
    )
    assert match
    assert float(match.group(1)) >= 400
    assert engine.render_png(svg).startswith(b"\x89PNG\r\n\x1a\n")


def test_rendered_a_to_b_resvg_tip_meets_target_border():
    engine = DiagramAssetEngine()
    svg = engine.render_svg(_request())
    target = re.search(
        r'<g data-fcstm-kind="state" data-fcstm-id="Machine\.B".*?'
        r'<rect x="([0-9.]+)" y="([0-9.]+)" width="([0-9.]+)" '
        r'height="([0-9.]+)"',
        svg,
        re.S,
    )
    assert target
    edge = re.search(
        r'<path d="M[0-9.]+,[0-9.]+ L([0-9.]+),([0-9.]+)"[^>]*'
        r'data-fcstm-id="a-b"',
        svg,
    )
    assert edge
    end_x, end_y = map(float, edge.groups())
    target_x, target_y, _target_width, target_height = map(float, target.groups())
    assert end_x == pytest.approx(target_x)
    normalized = engine.expand_svg(svg)
    transforms = re.findall(r'transform="matrix\(([^)]+)\)"', normalized)
    assert len(transforms) == 2
    a, b, c, d, tx, ty = [float(part) for part in transforms[1].split()]
    tip = (tx + a * 10 + c * 5, ty + b * 10 + d * 5)
    assert tip[0] == pytest.approx(target_x, abs=1e-3)
    assert tip[1] == pytest.approx(target_y + target_height / 2, abs=1e-3)


def test_resvg_png_and_vector_expansion_keep_marker_direction():
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

    legacy = engine.expand_svg(svg.replace('refX="10"', 'refX="9"'))
    legacy_transforms = re.findall(r'transform="matrix\(([^)]+)\)"', legacy)
    assert len(legacy_transforms) == len(endpoints)
    legacy_errors = []
    for transform, endpoint in zip(legacy_transforms, endpoints):
        a, b, c, d, tx, ty = [float(part) for part in transform.split()]
        tip = (tx + a * 10 + c * 5, ty + b * 10 + d * 5)
        legacy_errors.append(math.hypot(tip[0] - endpoint[0], tip[1] - endpoint[1]))
    assert legacy_errors == pytest.approx([1.0] * len(endpoints), abs=1e-3)

    normalized = engine.expand_svg(svg)
    transforms = re.findall(r'transform="matrix\(([^)]+)\)"', normalized)
    assert len(transforms) == len(endpoints)
    for transform, endpoint in zip(transforms, endpoints):
        a, b, c, d, tx, ty = [float(part) for part in transform.split()]
        tip = (tx + a * 10 + c * 5, ty + b * 10 + d * 5)
        assert math.hypot(tip[0] - endpoint[0], tip[1] - endpoint[1]) < 1e-3


def test_render_png_rejects_non_finite_scale():
    engine = DiagramAssetEngine()
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    for scale in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite positive"):
            engine.render_png(svg, scale=scale)


def test_engine_rejects_non_finite_timeout():
    for timeout in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite positive"):
            DiagramAssetEngine(timeout=timeout)


def test_engine_restarts_context_after_native_timeout():
    # A cold Windows runner can need more than 0.2 seconds to load the
    # generated bundle; apply the eval budget after startup for this test.
    engine = DiagramAssetEngine()
    engine.timeout = 0.2
    with pytest.raises(DiagramAssetError, match="time or memory limit"):
        engine._eval("while (true) {}")
    # The interrupted context must be rebuilt with a normal startup budget;
    # the short budget above is only the intentional infinite-loop trigger.
    engine.timeout = 30.0
    assert engine._eval("6 * 7") == 42


def test_engine_discards_context_after_renderer_deadline(monkeypatch):
    engine = DiagramAssetEngine()
    # Keep the native MiniRacer evaluation budget above startup cost.  Advance
    # only Python's deadline clock so this probe is independent of V8 timing.
    engine.timeout = 30.0
    engine._eval(
        "globalThis.__pyfcstm_render_start = function(_request, id) { return id; };"
    )
    engine._eval(
        "globalThis.__pyfcstm_render_poll = function(_id) "
        "{ return JSON.stringify({status: 'pending'}); };"
    )
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_time = engine_module.time
    ticks = iter((100.0, 131.0))

    class DeadlineClock:
        def monotonic(self):
            return next(ticks)

        def __getattr__(self, name):
            return getattr(real_time, name)

    monkeypatch.setattr(engine_module, "time", DeadlineClock())
    with pytest.raises(DiagramAssetError, match="renderer timed out"):
        engine.render_svg(_request())
    assert engine._context is None
    engine.timeout = 30.0
    assert engine._eval("6 * 7") == 42


def test_engine_discards_context_after_resvg_deadline(monkeypatch):
    engine = DiagramAssetEngine()
    # Keep the native MiniRacer evaluation budget comfortably above startup
    # cost.  Advance only Python's deadline clock so this probe tests the
    # resvg polling deadline rather than a platform-dependent V8 interrupt.
    engine.timeout = 30.0
    engine._eval(
        "globalThis.__pyfcstm_resvg_init = function(_wasm) "
        "{ globalThis.__pyfcstm_resvg_status = 'pending'; };"
    )
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_time = engine_module.time
    ticks = iter((100.0, 131.0))

    class DeadlineClock:
        def monotonic(self):
            return next(ticks)

        def __getattr__(self, name):
            return getattr(real_time, name)

    # Replace only the engine module's reference.  Mutating the standard
    # library time module itself would also change MiniRacer's asyncio event
    # loop clock on modern runtimes and can leave native eval waiting forever.
    monkeypatch.setattr(engine_module, "time", DeadlineClock())
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    with pytest.raises(DiagramAssetError, match="resvg WASM initialization timed out"):
        engine.render_png(svg)
    assert engine._context is None
    engine.timeout = 30.0
    assert engine._eval("6 * 7") == 42


def test_engine_rejects_invalid_memory_limit(monkeypatch):
    for value in (
        0,
        -1,
        True,
        1.5,
        "1024",
        float("nan"),
        float("inf"),
        float("-inf"),
    ):
        with pytest.raises(ValueError, match="max_memory"):
            DiagramAssetEngine(max_memory=value)
    # Avoid asking V8 to reserve an impractically large heap while checking
    # that Python preserves the exact integer without float conversion.
    monkeypatch.setattr(DiagramAssetEngine, "_ensure_context", lambda _self: None)
    engine = DiagramAssetEngine(max_memory=2**53 + 1)
    assert engine.max_memory == 2**53 + 1


def test_engine_rejects_dual_miniracer_distributions(monkeypatch):
    def both_installed(_name):
        return True

    monkeypatch.setattr(
        DiagramAssetEngine,
        "_distribution_installed",
        staticmethod(both_installed),
    )
    monkeypatch.setattr(
        DiagramAssetEngine,
        "_distribution_version",
        staticmethod(lambda name: "0.14.1" if name == "mini-racer" else "0.6.0"),
    )
    with pytest.raises(
        DiagramEngineConflictError,
        match=r"mini-racer 0\.14\.1 and py-mini-racer 0\.6\.0.*installed together",
    ):
        DiagramAssetEngine()


def test_engine_rejects_unavailable_distribution_metadata(monkeypatch):
    real_import = builtins.__import__

    def unavailable(name, globals=None, locals=None, fromlist=(), level=0):
        if name in ("importlib_metadata", "pkg_resources") or (
            name == "importlib" and "metadata" in fromlist
        ):
            raise ImportError("metadata unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    with pytest.raises(DiagramEngineMetadataError, match="cannot inspect"):
        DiagramAssetEngine._distribution_version("mini-racer")


def test_host_shim_blocks_dynamic_code_creation():
    engine = DiagramAssetEngine()
    with pytest.raises(Exception):
        engine._eval("eval('1 + 1')")
    with pytest.raises(Exception):
        engine._eval("Function('return 3')()")
