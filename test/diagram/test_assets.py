"""Runtime checks for the PR-B renderer and official resvg asset boundary."""

import base64
import json
import re
import builtins
import hashlib
import struct
import zlib

import pytest

from pyfcstm.diagram import (
    DiagramAssetEngine,
    DiagramAssetError,
    DiagramEngineConflictError,
    DiagramEngineMetadataError,
    DiagramRenderError,
    DiagramRenderLimitError,
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


def _canonical_svg(svg):
    """Create a validated private SVG fixture for bridge-only tests."""
    import importlib

    return importlib.import_module("pyfcstm.diagram.engine")._validate_canonical_svg(
        svg
    )


def _png_ink_bbox(data):
    """Decode the RGBA rows and return the non-white pixel bounding box."""
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    position = 8
    width = height = bit_depth = color_type = None
    compressed = []
    while position < len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        chunk = data[position + 8 : position + 8 + length]
        position += length + 12
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(
                ">IIBBBBB", chunk
            )
        elif chunk_type == b"IDAT":
            compressed.append(chunk)
        elif chunk_type == b"IEND":
            break
    assert (bit_depth, color_type) == (8, 6)
    assert width and height
    raw = zlib.decompress(b"".join(compressed))
    stride = width * 4
    rows = []
    offset = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = raw[offset]
        encoded = raw[offset + 1 : offset + 1 + stride]
        offset += stride + 1
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - 4] if index >= 4 else 0
            above = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (
                    abs(estimate - left),
                    abs(estimate - above),
                    abs(estimate - upper_left),
                )
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            else:
                raise AssertionError("unsupported PNG filter: %s" % filter_type)
            row[index] = (value + predictor) & 0xFF
        rows.append(row)
        previous = row
    points = []
    for y, row in enumerate(rows):
        for x in range(width):
            red, green, blue, alpha = row[x * 4 : x * 4 + 4]
            if alpha and (red < 245 or green < 245 or blue < 245):
                points.append((x, y))
    assert points, "PNG contains no visible ink"
    xs, ys = zip(*points)
    return width, height, (min(xs), min(ys), max(xs), max(ys))


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


def test_resvg_operations_reject_raw_svg_inputs():
    engine = DiagramAssetEngine()
    raw_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    with pytest.raises(ValueError, match="DiagramData request"):
        engine.render_png(raw_svg)
    with pytest.raises(ValueError, match="DiagramData request"):
        engine.expand_svg(raw_svg)


@pytest.mark.parametrize(
    "svg",
    (
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><use href="file:///tmp/x"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>*{fill:red}</style></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0" onload="evil()"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(https://evil)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><unknown/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(#missing)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><marker orient="auto-start-reverse"/></svg>',
        '<svg xmlns="urn:not-svg"><path/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path>',
    ),
)
def test_canonical_svg_validator_rejects_unsupported_structures(svg):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    with pytest.raises(DiagramAssetError, match="closed SVG dialect"):
        engine_module._validate_canonical_svg(svg)


@pytest.mark.parametrize(
    "svg",
    (
        '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/>EVIL</svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/>vbscript:evil</svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(vbscript:evil)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(blob:evil)"/></svg>',
    ),
)
def test_canonical_svg_validator_rejects_tail_text_and_dangerous_urls(svg):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    with pytest.raises(DiagramAssetError, match="closed SVG dialect"):
        engine_module._validate_canonical_svg(svg)


def test_renderer_request_errors_are_bounded_and_actionable():
    import copy

    request = copy.deepcopy(_request())
    del request["diagram"]["rootState"]["children"][0]["events"]
    with pytest.raises(
        DiagramRenderError,
        match=r"DiagramData shape and renderer options",
    ) as captured:
        DiagramAssetEngine(timeout=3.0).render_svg(request)
    message = str(captured.value)
    assert len(message) < 512
    assert "renderer-core" not in message


def test_canonical_svg_validator_accepts_renderer_output_and_marker_contract():
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    engine = DiagramAssetEngine()
    canonical = engine_module._validate_canonical_svg(engine.render_svg(_request()))
    assert canonical.startswith("<svg")
    assert 'orient="auto"' in canonical
    assert 'refX="10"' in canonical
    assert "auto-start-reverse" not in canonical


def test_expanded_svg_validator_rejects_non_path_output(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine, "_ensure_resvg", lambda _locale: None)
    monkeypatch.setattr(
        engine,
        "_eval_asset",
        lambda *_args, **_kwargs: (
            '<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>'
        ),
    )
    monkeypatch.setattr(
        engine,
        "_canonical_input",
        lambda _request: engine_module._CanonicalSvg(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
        ),
    )
    with pytest.raises(DiagramAssetError, match="closed SVG dialect"):
        engine.expand_svg(_request())


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


def test_physical_missing_runtime_asset_reports_issue_url(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def missing_renderer(package, resource):
        if resource == "renderer.js":
            raise FileNotFoundError("renderer.js disappeared from the package")
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
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
                '<text font-family="Noto Sans SC">中</text></svg>'
            )
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
        engine.render_png(_request())


@pytest.mark.parametrize(
    "invalid_data,reason",
    (
        (
            b"OTTO" + b"invalid-font-data",
            "failed OpenType table, bounds, or checksum validation",
        ),
        (
            b"OTTO" + b"\x00" * 8,
            "failed OpenType table, bounds, or checksum validation",
        ),
        ("not-bytes", "non-binary data instead of bytes"),
    ),
)
def test_invalid_font_data_reports_resource_data_failure(
    monkeypatch, invalid_data, reason
):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def invalid_font(package, resource):
        if resource == "fonts/NotoSansTC-Regular.otf":
            return invalid_data
        return real_get_data(package, resource)

    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine_module.pkgutil, "get_data", invalid_font)
    with pytest.raises(
        DiagramAssetError,
        match=r"NotoSansTC-Regular\.otf.*%s.*make build_assets" % re.escape(reason),
    ):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
                '<text font-family="Noto Sans TC">繁</text></svg>'
            )
        )


def test_corrupt_font_payload_reports_resource_data_failure(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data
    original = real_get_data("pyfcstm.diagram.assets", "fonts/NotoSansTC-Regular.otf")
    corrupted = bytearray(original)
    corrupted[-1] ^= 1

    def corrupt_font(package, resource):
        if resource == "fonts/NotoSansTC-Regular.otf":
            return bytes(corrupted)
        return real_get_data(package, resource)

    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine_module.pkgutil, "get_data", corrupt_font)
    monkeypatch.setattr(engine_module, "_is_development_checkout", lambda: False)
    with pytest.raises(
        DiagramAssetError,
        match=r"NotoSansTC-Regular\.otf.*failed OpenType table, bounds, or checksum validation.*github.com/HansBug/pyfcstm/issues",
    ):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
                '<text font-family="Noto Sans TC">繁</text></svg>'
            )
        )


def test_corrupt_font_checksum_adjustment_reports_resource_data_failure(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data
    original = real_get_data("pyfcstm.diagram.assets", "fonts/NotoSansTC-Regular.otf")
    corrupted = bytearray(original)
    table_count = struct.unpack(">H", corrupted[4:6])[0]
    for offset in range(12, 12 + table_count * 16, 16):
        if corrupted[offset : offset + 4] == b"head":
            head_offset = struct.unpack(">I", corrupted[offset + 8 : offset + 12])[0]
            # Keep the head table structurally valid; only the whole-font
            # checkSumAdjustment is damaged, which table-level checks alone
            # intentionally cannot detect.
            corrupted[head_offset + 8] ^= 1
            break
    else:
        raise AssertionError("fixture font has no head table")

    def corrupt_font(package, resource):
        if resource == "fonts/NotoSansTC-Regular.otf":
            return bytes(corrupted)
        return real_get_data(package, resource)

    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine_module.pkgutil, "get_data", corrupt_font)
    with pytest.raises(
        DiagramAssetError,
        match=r"NotoSansTC-Regular\.otf.*failed OpenType table, bounds, or checksum validation.*make build_assets",
    ):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
                '<text font-family="Noto Sans TC">繁</text></svg>'
            )
        )


def test_zero_length_required_font_table_reports_resource_data_failure(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data
    original = real_get_data("pyfcstm.diagram.assets", "fonts/NotoSansTC-Regular.otf")
    corrupted = bytearray(original)
    table_count = struct.unpack(">H", corrupted[4:6])[0]
    for offset in range(12, 12 + table_count * 16, 16):
        if corrupted[offset : offset + 4] == b"head":
            # Keep the tag present and make the zero-length table checksum
            # self-consistent; the structural minimum must reject it.
            corrupted[offset + 4 : offset + 8] = b"\x00" * 4
            corrupted[offset + 12 : offset + 16] = b"\x00" * 4
            break
    else:
        raise AssertionError("fixture font has no head table")

    def corrupt_font(package, resource):
        if resource == "fonts/NotoSansTC-Regular.otf":
            return bytes(corrupted)
        return real_get_data(package, resource)

    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine_module.pkgutil, "get_data", corrupt_font)
    with pytest.raises(
        DiagramAssetError,
        match=r"NotoSansTC-Regular\.otf.*failed OpenType table, bounds, or checksum validation.*make build_assets",
    ):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
                '<text font-family="Noto Sans TC">繁</text></svg>'
            )
        )


def test_invalid_expanded_svg_reports_resource_data_failure(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine, "_ensure_resvg", lambda _locale: None)
    monkeypatch.setattr(engine, "_eval_asset", lambda *_args, **_kwargs: "not-svg")
    monkeypatch.setattr(
        engine,
        "_canonical_input",
        lambda _request: engine_module._CanonicalSvg(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
        ),
    )
    with pytest.raises(
        DiagramAssetError,
        match=r"resvg\.wasm.*malformed expanded SVG output.*make build_assets",
    ):
        engine.expand_svg(_request())


def test_model_render_embeds_cjk_fallback_and_keeps_glyphs_distinct():
    request = _request()
    request["diagram"]["rootState"]["children"][0]["displayName"] = "启动"
    request["diagram"]["rootState"]["children"][1]["displayName"] = "状态"
    engine = DiagramAssetEngine()

    svg = engine.render_svg(request)
    assert "启动" in svg
    assert "状态" in svg
    assert "Noto Sans SC" in svg
    png = engine.render_png(_canonical_svg(svg))
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    expanded = engine.expand_svg(_canonical_svg(svg))
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
    rendered = {
        text: engine.render_png(_canonical_svg(glyph_svg(text))) for text in glyphs
    }
    hashes = {text: hashlib.sha256(data).hexdigest() for text, data in rendered.items()}
    assert len(set(hashes.values())) == len(glyphs)
    expanded_hashes = {
        text: hashlib.sha256(
            engine.expand_svg(_canonical_svg(glyph_svg(text))).encode("utf-8")
        ).hexdigest()
        for text in glyphs
    }
    assert len(set(expanded_hashes.values())) == len(glyphs)
    assert (
        hashlib.sha256(
            engine.render_png(_canonical_svg(glyph_svg("状", weight=700)))
        ).hexdigest()
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
        png = engine.render_png(_canonical_svg(svg))
        assert png.startswith(b"\x89PNG\r\n\x1a\n"), locale
        expanded = engine.expand_svg(_canonical_svg(svg))
        assert text not in expanded, locale
        assert "<path" in expanded, locale


@pytest.mark.parametrize(
    "locale,text",
    (
        ("sc", "简体中文"),
        ("tc", "繁體中文"),
        ("hk", "香港中文"),
        ("jp", "日本語"),
        ("kr", "한국어"),
    ),
)
def test_each_locale_regular_and_bold_have_visible_distinct_glyphs(locale, text):
    engine = DiagramAssetEngine()
    family = "Noto Sans " + locale.upper()

    def glyph_svg(weight):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">'
            '<rect width="640" height="120" fill="white"/>'
            '<text x="24" y="82" font-family="%s" font-size="64" '
            'font-weight="%s">%s</text></svg>' % (family, weight, text)
        )

    regular = engine.render_png(_canonical_svg(glyph_svg(400)))
    bold = engine.render_png(_canonical_svg(glyph_svg(700)))
    regular_width, regular_height, regular_box = _png_ink_bbox(regular)
    bold_width, bold_height, bold_box = _png_ink_bbox(bold)
    assert (regular_width, regular_height) == (640, 120)
    assert (bold_width, bold_height) == (640, 120)
    for box in (regular_box, bold_box):
        left, top, right, bottom = box
        assert left > 0 and top > 0
        assert right < 639 and bottom < 119
    assert hashlib.sha256(regular).digest() != hashlib.sha256(bold).digest(), locale
    assert "<path" in engine.expand_svg(_canonical_svg(glyph_svg(400)))
    assert "<path" in engine.expand_svg(_canonical_svg(glyph_svg(700)))


def test_locale_switch_rebuilds_context_for_each_font_pair(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    engine = DiagramAssetEngine()
    first_context = engine._context
    discarded = []

    def fake_discard():
        discarded.append(engine._context)
        engine._context = None
        engine._resvg_ready = False
        engine._resvg_locale = None

    monkeypatch.setattr(engine, "_discard_context", fake_discard)
    monkeypatch.setattr(engine_module, "_asset_bytes", lambda _name: b"asset")
    monkeypatch.setattr(
        engine,
        "_eval_asset",
        lambda _name, _source, timeout=None: "ok",
    )

    engine._resvg_ready = True
    engine._resvg_locale = "sc"
    engine._ensure_resvg("tc")
    assert discarded == [first_context]
    assert engine._resvg_locale == "tc"
    engine._ensure_resvg("sc")
    assert len(discarded) == 2
    assert discarded[1] is None
    assert engine._resvg_locale == "sc"


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
    normalized = engine.expand_svg(_canonical_svg(svg))
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
    png = engine.render_png(_canonical_svg(svg))
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    normalized = engine.expand_svg(_canonical_svg(svg))
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
    engine = DiagramAssetEngine()

    with pytest.raises(DiagramAssetError, match="marker endpoint contract"):
        _canonical_svg(svg.replace('refX="10"', 'refX="9"'))
    with pytest.raises(DiagramAssetError, match="marker orientation contract"):
        _canonical_svg(svg.replace('orient="auto"', 'orient="auto-start-reverse"'))
    normalized = engine.expand_svg(_canonical_svg(svg))
    transforms = re.findall(r'transform="matrix\(([^)]+)\)"', normalized)
    assert len(transforms) == 4
    for transform, direction in zip(transforms, ((1, 0), (0, 1), (-1, 0), (0, -1))):
        a, b, c, d, tx, ty = [float(part) for part in transform.split()]
        length = (a * a + b * b) ** 0.5
        assert (a * direction[0] + b * direction[1]) / length > 0.999


def test_render_png_rejects_non_finite_scale():
    engine = DiagramAssetEngine()
    svg = _canonical_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    )
    for scale in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite positive"):
            engine.render_png(svg, scale=scale)


def test_render_png_rejects_scale_and_canvas_limits_before_wasm():
    engine = DiagramAssetEngine()
    with pytest.raises(DiagramRenderLimitError, match=r"scale .* > 4"):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
            ),
            scale=4.0001,
        )
    with pytest.raises(DiagramRenderLimitError, match="per dimension"):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="16385" height="1"/>'
            )
        )
    with pytest.raises(DiagramRenderLimitError, match="pixels"):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="4097" height="4097"/>'
            )
        )


def test_render_png_rejects_structurally_valid_blank_png(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine, "_ensure_resvg", lambda _locale: None)

    def chunk(kind, payload):
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", checksum)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    blank = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
        + chunk(b"IEND", b"")
    )
    assert engine_module._valid_png(blank) is False
    monkeypatch.setattr(
        engine,
        "_eval_asset",
        lambda *_args, **_kwargs: base64.b64encode(blank).decode("ascii"),
    )
    with pytest.raises(DiagramRenderError, match="no visible ink"):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
            )
        )


def test_render_png_rejects_truncated_or_corrupt_png_payload(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    engine = DiagramAssetEngine()
    monkeypatch.setattr(engine, "_ensure_resvg", lambda _locale: None)
    malformed = base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x00").decode("ascii")
    monkeypatch.setattr(engine, "_eval_asset", lambda *_args, **_kwargs: malformed)
    with pytest.raises(
        DiagramAssetError,
        match=r"resvg\.wasm.*invalid PNG data.*make build_assets",
    ):
        engine.render_png(
            _canonical_svg(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
            )
        )
    assert not engine_module._valid_png(b"\x89PNG\r\n\x1a\n")

    def chunk(kind, payload):
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", checksum)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    invalid_filter = b"\x09\x00\x00\x00\x00"
    filtered_png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(invalid_filter))
        + chunk(b"IEND", b"")
    )
    assert not engine_module._valid_png(filtered_png)

    duplicate_ihdr = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff"))
        + chunk(b"IEND", b"")
    )
    assert not engine_module._valid_png(duplicate_ihdr)


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


def test_engine_tracks_one_active_context_and_restarts_after_discard():
    engine = DiagramAssetEngine()
    assert engine._active_context_count == 1
    first_metrics = json.loads(engine._eval("__pyfcstm_resvg_metrics()"))
    assert first_metrics["activeContext"] == 1
    assert first_metrics["contextToken"] == engine._context_token
    engine._eval("globalThis.__pyfcstm_active_context_count = 7;")
    assert json.loads(engine._eval("__pyfcstm_resvg_metrics()"))["activeContext"] == 1
    engine._discard_context()
    assert engine._active_context_count == 0
    assert engine._eval("6 * 7") == 42
    assert engine._active_context_count == 1
    second_metrics = json.loads(engine._eval("__pyfcstm_resvg_metrics()"))
    assert second_metrics["activeContext"] == 1
    assert second_metrics["contextToken"] == engine._context_token
    assert second_metrics["contextToken"] != first_metrics["contextToken"]


def test_render_svg_rejects_non_json_request():
    engine = DiagramAssetEngine()
    with pytest.raises(ValueError, match="JSON-compatible"):
        engine.render_svg({"diagram": {"invalid": {1, 2, 3}}})


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
    svg = _canonical_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    )
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
