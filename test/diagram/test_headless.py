"""Tests for the synchronous export surface and its output limits.

The four export methods on :class:`pyfcstm.diagram.api.Diagram` were published
with their signatures frozen while the capability behind them was absent, so
these tests pin the contract from both sides: what a caller gets when the
optional rendering runtime is installed, and what they get when it is not.

The limit tests matter more than they look. The documented caps exist so an
oversized request is refused by a checked multiplication in Python rather than
by the rasteriser running out of memory, and a test that only asserts "raises"
cannot tell those two apart -- so the ones here assert the refusal happens
before the renderer is reached.
"""

import json
import re
import struct
import subprocess
import sys
from unittest import mock
import zlib

import pytest

from pyfcstm.diagram import (
    DiagramError,
    DiagramRenderLimitError,
    DiagramUnavailableError,
)
from pyfcstm.diagram.engine import DiagramAssetEngine
from pyfcstm.model import load_state_machine_from_text

SIMPLE = "state Root { state A; state B; [*] -> A; A -> B; B -> A; }"

#: Caps frozen by the umbrella plan.  They live here as literals rather than
#: being imported from the implementation, so a test failure names the number a
#: reader can compare against the plan instead of comparing a constant to itself.
MAX_SCALE = 4
MAX_EDGE_PX = 16384
MAX_PIXELS = 16777216
MAX_RAW_RGBA_BYTES = 67108864
MAX_ENCODED_PNG_BYTES = 33554432
MAX_ENCODED_TEXT_BYTES = 67108864


def _runtime_installed():
    """
    Report whether an optional rendering runtime is importable here.

    :return: ``True`` when a supported distribution is installed.
    :rtype: bool
    """
    try:
        DiagramAssetEngine()
    except DiagramUnavailableError:
        return False
    return True


needs_runtime = pytest.mark.skipif(
    not _runtime_installed(),
    reason="the optional rendering runtime is not installed in this environment",
)
needs_no_runtime = pytest.mark.skipif(
    _runtime_installed(),
    reason="this environment has the optional rendering runtime installed",
)


def _wide_source(states=30):
    """
    Build a left-to-right chain wide enough to reach the export limits.

    A limit test on a small diagram silently degrades into a skip, so the caps
    need a fixture whose scaled size genuinely exceeds them.  A long chain laid
    out horizontally is the cheapest ordinary model that does: 30 states measure
    about 4974px wide, which passes the edge cap at scale 4.

    :param states: Number of chained states, defaults to ``30``.
    :type states: int, optional
    :return: FCSTM source text.
    :rtype: str
    """
    declarations = " ".join("state S%d;" % index for index in range(states))
    links = " ".join("S%d -> S%d;" % (i, i + 1) for i in range(states - 1))
    return "state Root { %s [*] -> S0; %s }" % (declarations, links)


def _diagram(source=SIMPLE, **options):
    """
    Build a diagram snapshot from FCSTM source through the public entry points.

    :param source: FCSTM source text, defaults to a three-state machine.
    :type source: str, optional
    :param options: Renderer options forwarded to
        :meth:`pyfcstm.model.model.StateMachine.diagram`.
    :return: An immutable diagram snapshot.
    :rtype: pyfcstm.diagram.api.Diagram
    """
    return load_state_machine_from_text(source).diagram(**options)


@pytest.mark.unittest
class TestExportLimitTaxonomy:
    def test_the_limit_error_is_part_of_the_public_failure_surface(self):
        # A caller distinguishing "too big" from "the renderer broke" needs the
        # limit to be its own class, and needs it reachable from the package
        # root the same way every other diagram failure is.
        import pyfcstm.diagram as package

        assert package.DiagramRenderLimitError is DiagramRenderLimitError
        assert issubclass(DiagramRenderLimitError, DiagramError)
        assert "DiagramRenderLimitError" in package.__all__

    def test_the_module_roadmap_documents_the_limit_error(self):
        # ``__init__`` carries the table a reader uses to find the right class,
        # so a new failure surface that is absent from it is undiscoverable.
        import pyfcstm.diagram as package

        assert "DiagramRenderLimitError" in (package.__doc__ or "")


@pytest.mark.unittest
class TestScaleValidation:
    @pytest.mark.parametrize("scale", [0, -1, -0.5, float("nan"), float("inf")])
    def test_a_scale_outside_the_finite_positive_range_is_a_value_error(self, scale):
        with pytest.raises(ValueError):
            _diagram().to_png(scale=scale)

    @pytest.mark.parametrize("scale", [4.0001, 5, 100])
    def test_a_scale_above_the_documented_ceiling_is_a_value_error(self, scale):
        # The ceiling is an argument contract, not a size outcome: it holds even
        # for a diagram small enough that the pixel caps would not fire.
        with pytest.raises(ValueError) as info:
            _diagram().to_png(scale=scale)
        assert str(MAX_SCALE) in str(info.value)

    @pytest.mark.parametrize("scale", [1, 2, 4])
    def test_the_documented_ceiling_itself_is_accepted(self, scale):
        # Rejecting exactly 4 would contradict the ``0 < scale <= 4`` contract.
        # Only the argument check is under test, so an absent runtime is fine.
        try:
            _diagram().to_png(scale=scale)
        except DiagramUnavailableError:
            pass

    def test_a_non_default_scale_is_refused_for_formats_that_have_no_scale(
        self, tmp_path
    ):
        with pytest.raises(ValueError):
            _diagram().save(tmp_path / "x.svg", scale=2)


@pytest.mark.unittest
@needs_runtime
class TestExpandedSvgContract:
    def test_the_exported_svg_carries_no_text_marker_or_font_dependency(self):
        # The exported form is the expanded one: glyphs and arrow heads are
        # already paths, so the file renders identically somewhere with none of
        # this project's fonts installed.
        svg = _diagram().to_svg()
        assert svg.lstrip().startswith("<svg") or svg.lstrip().startswith("<?xml")
        assert "<text" not in svg
        assert "<marker" not in svg
        assert "font-family" not in svg
        assert "<path" in svg

    def test_the_exported_svg_reaches_out_to_nothing(self):
        # An ``xmlns`` value is a namespace name rather than something a viewer
        # fetches, so the check is for references that would actually leave the
        # document: linked resources, images, and CSS URLs.
        svg = _diagram().to_svg()
        assert "<script" not in svg
        assert not re.search(r'(?:href|src)\s*=\s*"[^"]*//', svg)
        assert not re.search(r"url\(\s*['\"]?\s*(?:https?:)?//", svg)
        assert "<image" not in svg

    def test_the_notebook_representation_is_the_same_expanded_form(self):
        view = _diagram()
        assert view._repr_svg_() == view.to_svg()


@pytest.mark.unittest
@needs_runtime
class TestPresentationOptionsReachTheRenderer:
    @pytest.mark.parametrize("palette", ["nord", "solarized"])
    def test_a_palette_choice_alone_changes_the_exported_svg(self, palette):
        # The renderer reads presentation choices from the request root.  When an
        # export forgets to put them there the output silently stays on the
        # default palette, which looks like success from every other angle.
        #
        # Only ``palette`` varies here.  Varying ``mode`` at the same time made
        # this pass even with the palette field removed from the request, because
        # the mode alone was enough to change the bytes -- the test proved that
        # something reached the renderer, not that the palette did.
        default = _diagram(palette="default", mode="light").to_svg()
        other = _diagram(palette=palette, mode="light").to_svg()
        assert default != other

    def test_a_mode_choice_alone_changes_the_exported_svg(self):
        assert _diagram(mode="light").to_svg() != _diagram(mode="dark").to_svg()

    def test_the_cjk_locale_alone_reaches_the_renderer(self):
        # Same isolation as the palette case: vary only the locale, so removing
        # the locale from the request cannot be masked by a neighbouring field.
        source = (
            'state Root named "\u6839\u72b6\u614b" '
            '{ state Ready named "\u6e96\u5099"; [*] -> Ready; }'
        )
        assert (
            _diagram(source, cjk_locale="sc").to_svg()
            != _diagram(source, cjk_locale="kr").to_svg()
        )

    @pytest.mark.parametrize("locale", ["jp", "kr", "tc"])
    def test_a_cjk_locale_choice_changes_the_exported_svg(self, locale):
        # The locale selects which CJK face supplies the glyphs.  In the exported
        # form those glyphs are already outlines, so the difference only shows on
        # a label that actually contains CJK text -- a Latin-only diagram is
        # legitimately identical across locales.
        source = (
            'state Root named "\u6839\u72b6\u614b" '
            '{ state Ready named "\u6e96\u5099"; [*] -> Ready; }'
        )
        assert (
            _diagram(source, cjk_locale="sc").to_svg()
            != _diagram(source, cjk_locale=locale).to_svg()
        )

    def test_the_palette_alone_reaches_the_raster_output_too(self):
        # Colour parity has to hold for every format, not only the one whose test
        # was easiest to write; and here too only the palette may vary.
        assert (
            _diagram(palette="default", mode="light").to_png()
            != _diagram(palette="nord", mode="light").to_png()
        )


@pytest.mark.unittest
@needs_runtime
class TestRasterOutput:
    @pytest.mark.parametrize("scale", [1, 2, 4])
    def test_the_png_is_structurally_valid_and_scaled(self, scale):
        data = _diagram().to_png(scale=scale)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        length, kind = struct.unpack(">I4s", data[8:16])
        assert kind == b"IHDR"
        width, height = struct.unpack(">II", data[16:24])
        assert data[-12:-8] == struct.pack(">I", 0)
        assert data[-8:-4] == b"IEND"
        one = _diagram().to_png(scale=1)
        base_width, base_height = struct.unpack(">II", one[16:24])
        assert width == base_width * scale
        assert height == base_height * scale

    def test_every_png_chunk_carries_an_intact_checksum(self):
        # A rasteriser that emits a truncated or mis-framed chunk still starts
        # with the right eight bytes, so checking the signature alone would
        # accept a file no decoder can read.
        data = _diagram().to_png()
        offset = 8
        seen = []
        while offset < len(data):
            (length,) = struct.unpack(">I", data[offset : offset + 4])
            kind = data[offset + 4 : offset + 8]
            payload = data[offset + 8 : offset + 8 + length]
            (declared,) = struct.unpack(
                ">I", data[offset + 8 + length : offset + 12 + length]
            )
            assert zlib.crc32(kind + payload) & 0xFFFFFFFF == declared
            seen.append(kind)
            offset += 12 + length
        assert seen[0] == b"IHDR" and seen[-1] == b"IEND"
        assert b"IDAT" in seen

    def test_the_raster_output_is_opaque(self):
        data = _diagram().to_png()
        (colour_type,) = struct.unpack(">B", data[25:26])
        # 6 is RGBA; the alpha channel has to be fully opaque rather than the
        # diagram being transparent over whatever the viewer's background is.
        assert colour_type in (2, 6)


@pytest.mark.unittest
@needs_runtime
class TestOutputLimits:
    def test_an_oversized_request_is_refused_before_the_renderer_runs(self):
        # The point of the caps is that the refusal is a multiplication in
        # Python, not the rasteriser dying.  Asserting only that it raises
        # cannot tell those apart, so assert the renderer was never asked.
        view = _diagram(_wide_source(), direction="LR")
        with mock.patch.object(
            DiagramAssetEngine, "render_png", autospec=True
        ) as render:
            with pytest.raises(DiagramRenderLimitError):
                view.to_png(scale=_scale_that_exceeds_the_edge_cap(view))
        assert render.call_args_list == []

    def test_the_limit_message_tells_the_caller_what_to_change(self):
        view = _diagram(_wide_source(), direction="LR")
        scale = _scale_that_exceeds_the_edge_cap(view)
        with pytest.raises(DiagramRenderLimitError) as info:
            view.to_png(scale=scale)
        message = str(info.value)
        assert "scale" in message
        # The original size, the scaled size and the cap that fired, so the
        # caller can work out which scale would have fitted.
        assert str(MAX_EDGE_PX) in message or str(MAX_PIXELS) in message
        assert re.search(r"\d+\s*[x×]\s*\d+", message)

    def test_a_limit_failure_is_not_reported_as_a_generic_render_failure(self):
        from pyfcstm.diagram import DiagramRenderError

        view = _diagram(_wide_source(), direction="LR")
        with pytest.raises(DiagramRenderLimitError) as info:
            view.to_png(scale=_scale_that_exceeds_the_edge_cap(view))
        # ``DiagramRenderLimitError`` must not be a subclass of the generic
        # render failure, or ``except DiagramRenderError`` would swallow a
        # caller error that has a specific remedy.
        assert not isinstance(info.value, DiagramRenderError)


def _scale_that_exceeds_the_edge_cap(view):
    """
    Find the smallest documented-range scale whose output breaks a cap.

    :param view: Diagram snapshot whose base geometry sets the starting size.
    :type view: pyfcstm.diagram.api.Diagram
    :return: A scale within ``0 < scale <= 4`` that exceeds an output cap.
    :rtype: float
    :raises pytest.skip.Exception: If no in-range scale can exceed a cap for
        this diagram, which means the caps cannot be reached from here.
    """
    svg = DiagramAssetEngine().render_svg(
        {"diagram": view.to_dict(), "options": view.options.to_dict()}
    )
    width = float(re.search(r'width="([\d.]+)', svg).group(1))
    height = float(re.search(r'height="([\d.]+)', svg).group(1))
    for scale in (2, 3, 4):
        if max(width, height) * scale > MAX_EDGE_PX:
            return scale
        if width * scale * height * scale > MAX_PIXELS:
            return scale
    pytest.skip(
        "this diagram is %gx%g, so no scale within the documented range can "
        "exceed a cap; the caps need a larger fixture" % (width, height)
    )


@pytest.mark.unittest
class TestCapabilityIsDetectedLazily:
    def test_importing_the_package_does_not_load_the_optional_runtime(self):
        # A base installation must behave exactly as it did before this
        # capability existed, and the cheapest way to break that is a module
        # level import that turns an optional dependency into a required one.
        code = (
            "import sys; import pyfcstm.diagram; "
            "print(any(name in sys.modules for name in "
            "('mini_racer', 'py_mini_racer')))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "False", result.stdout

    def test_building_a_snapshot_does_not_load_the_optional_runtime(self):
        code = (
            "import sys\n"
            "from pyfcstm.model import load_state_machine_from_text\n"
            "view = load_state_machine_from_text('state Root;').diagram()\n"
            "view.to_dict(); view.to_json()\n"
            "print(any(n in sys.modules for n in ('mini_racer', 'py_mini_racer')))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "False", result.stdout


@pytest.mark.unittest
@needs_no_runtime
class TestBaseInstallationStaysUnchanged:
    def test_the_export_methods_name_the_missing_capability(self):
        view = _diagram()
        for call in (view.to_svg, view.to_png, view.to_pdf):
            with pytest.raises(DiagramUnavailableError) as info:
                call()
            assert "pyfcstm[viz]" in str(info.value)

    def test_the_notebook_representation_degrades_instead_of_raising(self):
        # A repr hook that raises poisons the whole cell output, so the absent
        # capability has to come back as "no representation" here.
        assert _diagram()._repr_svg_() is None

    def test_saving_a_capability_format_names_the_missing_capability(self, tmp_path):
        with pytest.raises(DiagramUnavailableError):
            _diagram().save(tmp_path / "out.png")


@pytest.mark.unittest
@needs_runtime
class TestSaveRoutesEveryFormat:
    @pytest.mark.parametrize("suffix", ["svg", "png", "pdf"])
    def test_a_capability_format_lands_on_disk(self, tmp_path, suffix):
        target = tmp_path / ("machine." + suffix)
        assert _diagram().save(target) == target
        assert target.stat().st_size > 0

    def test_the_saved_svg_is_the_expanded_form(self, tmp_path):
        target = tmp_path / "machine.svg"
        _diagram().save(target)
        text = target.read_text(encoding="utf-8")
        assert "<text" not in text and "<marker" not in text


@pytest.mark.unittest
class TestEveryCapHasAThreshold:
    """
    Pin each documented cap at its boundary.

    An ordinary diagram cannot be made large enough to cross all six caps, so
    the thresholds are exercised directly on the helpers the export path calls.
    The values are written out rather than imported, so a test failure names the
    number a reader can compare against the documented limit.
    """

    def test_the_edge_cap_fires_one_pixel_over_and_not_at_the_boundary(self):
        from pyfcstm.diagram.engine import check_export_size

        assert check_export_size(MAX_EDGE_PX, 1, 1) == (MAX_EDGE_PX, 1)
        with pytest.raises(DiagramRenderLimitError) as info:
            check_export_size(MAX_EDGE_PX + 1, 1, 1)
        assert info.value.limit_name == "edge"

    def test_the_pixel_cap_fires_for_a_shape_no_single_edge_would_catch(self):
        from pyfcstm.diagram.engine import check_export_size

        # 4096 x 4096 is exactly the cap and neither edge is near its own limit,
        # so this is the case an edge-only check would wave through.
        side = 4096
        assert side * side == MAX_PIXELS
        assert check_export_size(side, side, 1) == (side, side)
        with pytest.raises(DiagramRenderLimitError) as info:
            check_export_size(side + 1, side, 1)
        assert info.value.limit_name == "pixels"

    def test_the_raw_buffer_figure_is_derived_from_the_pixel_cap(self):
        # Four bytes per pixel, so the raw buffer bound is the pixel bound and not
        # a second boundary. It used to have its own branch, which could never
        # run: any request large enough to reach it had already been refused by the
        # pixel check. The number is kept as a derived figure because the
        # documented limit set names a buffer size.
        from pyfcstm.diagram.engine import (
            MAX_EXPORT_PIXELS,
            MAX_EXPORT_RAW_RGBA_BYTES,
        )

        assert MAX_EXPORT_RAW_RGBA_BYTES == MAX_EXPORT_PIXELS * 4
        assert MAX_PIXELS * 4 == MAX_RAW_RGBA_BYTES

    def test_no_limit_reports_a_name_the_documentation_does_not_list(self):
        # A caller may branch on ``limit_name``, so the set of names it can take
        # has to be the set the reference documents. A name that can never appear
        # is as much of a defect as one that is missing.
        from pyfcstm.diagram.engine import check_export_size

        seen = set()
        for width, height, scale in (
            (5000, 100, 4),
            (4097, 4096, 1),
            (100, 5000, 4),
            (20000, 20000, 1),
        ):
            try:
                check_export_size(width, height, scale)
            except DiagramRenderLimitError as error:
                seen.add(error.limit_name)
        assert seen == {"edge", "pixels"}, seen

    def test_the_encoded_output_limits_name_their_own_format(self):
        # ``check_export_bytes`` derives the name from the format, so the full set
        # a caller can observe is larger than the one ``check_export_size``
        # produces. Pinning only the latter left three names undocumented.
        from pyfcstm.diagram.engine import check_export_bytes

        seen = set()
        for kind in ("PNG", "PDF", "SVG"):
            try:
                check_export_bytes(b"x" * 4, kind, 2)
            except DiagramRenderLimitError as error:
                seen.add(error.limit_name)
        assert seen == {"png", "pdf", "svg"}, seen

    def test_the_scale_is_applied_before_the_caps_are_compared(self):
        from pyfcstm.diagram.engine import check_export_size

        assert check_export_size(5000, 100, 1) == (5000, 100)
        with pytest.raises(DiagramRenderLimitError):
            check_export_size(5000, 100, 4)

    def test_a_fractional_scale_rounds_up_rather_than_truncating(self):
        from pyfcstm.diagram.engine import check_export_size

        # Truncating would under-report the buffer the rasteriser allocates.
        assert check_export_size(100.5, 100.5, 1) == (101, 101)

    @pytest.mark.parametrize(
        "kind,limit",
        [("PNG", MAX_ENCODED_PNG_BYTES), ("SVG", MAX_ENCODED_TEXT_BYTES)],
    )
    def test_the_encoded_output_caps_fire_one_byte_over(self, kind, limit):
        from pyfcstm.diagram.engine import check_export_bytes

        payload = b"x" * 8
        assert check_export_bytes(payload, kind, limit) is payload
        with pytest.raises(DiagramRenderLimitError) as info:
            check_export_bytes(b"x" * (limit + 1), kind, limit)
        assert str(limit) in str(info.value)

    @pytest.mark.parametrize("bad", ["", "abc", None, object()])
    def test_a_non_numeric_scale_is_a_value_error(self, bad):
        from pyfcstm.diagram.engine import check_export_scale

        with pytest.raises(ValueError):
            check_export_scale(bad)

    def test_a_non_finite_canvas_is_a_value_error_not_a_limit_failure(self):
        from pyfcstm.diagram.engine import check_export_size

        # A renderer that returned a NaN viewBox is broken, and that is a
        # different problem from an oversized request.
        for width, height in ((float("nan"), 10), (10, float("inf")), (0, 10)):
            with pytest.raises(ValueError):
                check_export_size(width, height, 1)


@pytest.mark.unittest
@needs_runtime
class TestVectorPdf:
    def test_the_document_is_a_single_page_pdf(self):
        data = _diagram().to_pdf()
        assert data[:5] == b"%PDF-"
        # One page per diagram: a writer that silently paginated would still
        # produce a valid file, and the caller would only find out on print.
        assert data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") <= 2

    def test_the_page_matches_the_diagram_and_carries_no_raster(self):
        # These two properties are what "vector" means here, and both are
        # checkable without a PDF library: the page box comes from the diagram's
        # own size, and an image XObject would mean something was rasterised.
        view = _diagram()
        data = view.to_pdf()
        assert b"/Subtype /Image" not in data
        assert b"/Subtype/Image" not in data
        canonical = DiagramAssetEngine().render_svg(
            {"diagram": view.to_dict(), "options": view.options.to_dict()}
        )
        width = float(re.search(r'width="([\d.]+)', canonical).group(1))
        box = re.search(rb"/MediaBox\s*\[([\d.\s-]+)\]", data)
        assert box is not None
        numbers = [float(part) for part in box.group(1).split()]
        assert abs((numbers[2] - numbers[0]) - width) < 2.0

    def test_rendering_the_same_diagram_twice_gives_the_same_drawing(self):
        # The PDF carries a creation timestamp, so the bytes differ run to run.
        # What has to be stable is the drawing, which is the content stream.
        first = _diagram().to_pdf()
        second = _diagram().to_pdf()
        pattern = re.compile(rb"stream\r?\n(.*?)endstream", re.S)
        assert pattern.findall(first) == pattern.findall(second)

    def test_a_palette_choice_reaches_the_pdf(self):
        assert (
            _diagram(palette="default", mode="light").to_pdf()
            != _diagram(palette="nord", mode="light").to_pdf()
        )

    def test_an_oversized_diagram_is_refused_before_the_writer_runs(self):
        view = _diagram(_wide_source(200), direction="LR")
        with mock.patch.object(
            DiagramAssetEngine, "render_pdf", autospec=True
        ) as writer:
            with pytest.raises(DiagramRenderLimitError):
                view.to_pdf()
        assert writer.call_args_list == []


@pytest.mark.unittest
@needs_runtime
class TestTheDomAdapterFailsLoudly:
    """
    Guard the one failure mode the adapter cannot show through an export.

    ``xmldom`` has no CSS selector engine, so the adapter answers the two
    selectors the export core actually uses.  If an unknown selector returned an
    empty list instead of raising, the halo removal in ``prepareSvgForPdf`` would
    quietly do nothing: a PDF would still be produced, with a stroke halo baked
    into every transition label, and every other assertion here would pass.
    """

    def test_an_unknown_selector_is_refused_rather_than_answered_emptily(self):
        from py_mini_racer import MiniRacer

        from pyfcstm.diagram.engine import _asset_bytes

        context = MiniRacer()
        context.eval(_asset_bytes("host-shim.js").decode("utf-8"))
        context.eval(_asset_bytes("pdf-writer.js").decode("utf-8"))
        probe = (
            "(function () {"
            "  var element = new DOMParser()"
            "    .parseFromString('<svg><g/></svg>', 'image/svg+xml').documentElement;"
            "  try { element.querySelectorAll('g.unknown-thing'); return 'answered'; }"
            "  catch (error) { return 'refused:' + error.message; }"
            "})()"
        )
        outcome = str(context.eval(probe))
        assert outcome.startswith("refused:"), outcome
        assert "selector" in outcome

    def test_the_selectors_the_export_core_uses_are_all_answered(self):
        from py_mini_racer import MiniRacer

        from pyfcstm.diagram.engine import _asset_bytes

        context = MiniRacer()
        context.eval(_asset_bytes("host-shim.js").decode("utf-8"))
        context.eval(_asset_bytes("pdf-writer.js").decode("utf-8"))
        document = (
            '<svg><g data-fcstm-kind="transition-label">'
            '<text paint-order="stroke">x</text></g><style/></svg>'
        )
        probe = (
            "(function () {"
            "  var element = new DOMParser()"
            "    .parseFromString(%s, 'image/svg+xml').documentElement;"
            "  var halos = element.querySelectorAll("
            '    \'[data-fcstm-kind="transition-label"] text[paint-order="stroke"]\');'
            "  var sheets = element.querySelectorAll('style,link');"
            "  return halos.length + ',' + sheets.length;"
            "})()" % json.dumps(document)
        )
        # Both selectors must find their target: an adapter that answered them
        # with an empty list would leave the halo in place, and this is the only
        # place that difference is visible.
        assert str(context.eval(probe)) == "1,1"


@pytest.mark.unittest
class TestTheCanvasSizeIsReadDefensively:
    """
    Cover how the export sizes a document it did not write itself.

    The limits are computed from the canvas the renderer declared, so a document
    that declares no usable size cannot be checked -- and passing it on unchecked
    is the one outcome that must not happen quietly.
    """

    def test_the_declared_width_and_height_are_used_when_present(self):
        from pyfcstm.diagram.api import _canonical_canvas_size

        assert _canonical_canvas_size('<svg width="120" height="80"></svg>') == (
            120.0,
            80.0,
        )

    def test_the_view_box_is_used_when_there_is_no_width(self):
        from pyfcstm.diagram.api import _canonical_canvas_size

        # A renderer is free to size a document by its view box alone, and the
        # limits still have to be computable from it.
        assert _canonical_canvas_size('<svg viewBox="0 0 200 150"></svg>') == (
            200.0,
            150.0,
        )

    def test_a_document_with_no_usable_size_is_refused(self):
        from pyfcstm.diagram.api import _canonical_canvas_size
        from pyfcstm.diagram import DiagramRenderError

        # Passing it on would mean exporting something whose size was never
        # checked against any limit.
        with pytest.raises(DiagramRenderError):
            _canonical_canvas_size("<svg></svg>")


@pytest.mark.unittest
class TestTheCommandLineTranslatesExportFailures:
    """
    Cover the three failures a caller meets on the command line.

    Each has a different remedy, so each has to arrive as a message rather than a
    stack: a scale out of range is a usage error, an oversized diagram names the
    limit, and a missing optional runtime names the extra to install.
    """

    def _source(self, tmp_path, text=SIMPLE):
        path = tmp_path / "machine.fcstm"
        path.write_text(text, encoding="utf-8")
        return path

    def test_an_out_of_range_scale_is_a_usage_error(self, tmp_path):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        result = CliRunner().invoke(
            pyfcstmcli,
            [
                "diagram",
                "-i",
                str(self._source(tmp_path)),
                "-o",
                str(tmp_path / "out.png"),
                "--scale",
                "9",
            ],
        )
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "4" in result.output

    @needs_runtime
    def test_an_oversized_diagram_names_the_limit(self, tmp_path):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        # The command uses the default top-to-bottom layout, where a chain grows
        # in height: 200 states measure 296x15800 and still fit, 400 measure
        # 296x31400 and do not. An ordinary large model, not a contrived one.
        result = CliRunner().invoke(
            pyfcstmcli,
            [
                "diagram",
                "-i",
                str(self._source(tmp_path, _wide_source(400))),
                "-o",
                str(tmp_path / "out.png"),
            ],
        )
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert str(MAX_EDGE_PX) in result.output or str(MAX_PIXELS) in result.output

    @needs_no_runtime
    def test_a_missing_runtime_names_the_extra(self, tmp_path):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        result = CliRunner().invoke(
            pyfcstmcli,
            [
                "diagram",
                "-i",
                str(self._source(tmp_path)),
                "-o",
                str(tmp_path / "out.svg"),
            ],
        )
        assert result.exit_code != 0
        assert "pyfcstm[viz]" in result.output


@pytest.mark.unittest
class TestTheCommandExplainsAnUnusableInput:
    """
    A bad input file is reported, not raised through.

    Every failure here is one an ordinary user reaches by typing a path or a
    flag combination: a typo in the machine, a rule the model forbids, a path
    that turned out to be a binary, a flag that contradicts the requested
    format.  Each has to arrive as a message naming the problem, because a
    traceback tells a DSL author nothing they can act on.
    """

    def _run(self, *arguments):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        return CliRunner().invoke(pyfcstmcli, ["diagram"] + list(arguments))

    def test_a_syntax_error_names_the_file_and_the_parse_failure(self, tmp_path):
        source = tmp_path / "broken.fcstm"
        source.write_text("state Root { state A; [*] -> A", encoding="utf-8")

        result = self._run("-i", str(source), "-o", str(tmp_path / "out.json"))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Failed to parse" in result.output
        assert "broken.fcstm" in result.output

    def test_a_model_rule_violation_names_the_file(self, tmp_path):
        # A composite state has to choose an initial child. Leaving that out
        # parses cleanly and fails when the model is built, which is a different
        # stage with a different message.
        source = tmp_path / "no-initial.fcstm"
        source.write_text("state Root { state Inner { state A; } }", encoding="utf-8")

        result = self._run("-i", str(source), "-o", str(tmp_path / "out.json"))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "no-initial.fcstm" in result.output

    def test_a_binary_file_is_reported_rather_than_decoded(self, tmp_path):
        # Pointing -i at the wrong file is an ordinary mistake, and the bytes of
        # a compiled artefact fit no text encoding.
        source = tmp_path / "not-a-machine.fcstm"
        source.write_bytes(bytes(range(256)) * 8)

        result = self._run("-i", str(source), "-o", str(tmp_path / "out.json"))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Failed to decode" in result.output
        assert "not-a-machine.fcstm" in result.output


@pytest.mark.unittest
class TestContradictoryFormatRequestsAreUsageErrors:
    """
    A flag combination that cannot be honoured is refused before any work.

    These are usage errors rather than failures: nothing is wrong with the
    machine, and the command can say exactly which two requests conflict.  Doing
    the work first and failing afterwards would leave a half-written file for a
    request that was never satisfiable.
    """

    def _run(self, tmp_path, *arguments):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        source = tmp_path / "machine.fcstm"
        source.write_text(SIMPLE, encoding="utf-8")
        return CliRunner().invoke(
            pyfcstmcli, ["diagram", "-i", str(source)] + list(arguments)
        )

    def test_open_with_a_non_html_format_is_refused(self, tmp_path):
        result = self._run(tmp_path, "--open", "--format", "json")

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "--open requires HTML output" in result.output

    def test_open_with_a_non_html_path_is_refused(self, tmp_path):
        result = self._run(tmp_path, "--open", "-o", str(tmp_path / "out.png"))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "--open requires an .html or .htm output path" in result.output

    def test_only_json_can_go_to_standard_output(self, tmp_path):
        # Without -o there is nowhere to put bytes, and an SVG on a terminal is
        # not what the flag combination asks for.
        result = self._run(tmp_path, "--format", "svg")

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "JSON is the only format" in result.output


@pytest.mark.unittest
class TestTheDocumentedJsonPathsWork:
    """
    The two ways of asking for portable JSON, and what each one prints.

    ``pyfcstm diagram -i machine.fcstm`` writing JSON to standard output is the
    first form the command's help documents, and the form a caller pipes into
    something else.  With ``-o`` the document goes to the file and the path is
    printed instead, so a shell can capture it.
    """

    def _run(self, tmp_path, *arguments):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        source = tmp_path / "machine.fcstm"
        source.write_text(SIMPLE, encoding="utf-8")
        return CliRunner().invoke(
            pyfcstmcli, ["diagram", "-i", str(source)] + list(arguments)
        )

    def test_without_an_output_path_json_goes_to_standard_output(self, tmp_path):
        import json

        result = self._run(tmp_path)

        assert result.exit_code == 0, result.output
        document = json.loads(result.output)
        assert document["kind"] == "diagram"
        assert document["machineName"] == "Root"
        # Three states in the source, so three in the snapshot: a document that
        # parsed but lost the machine would still be valid JSON.
        assert document["summary"]["states"] == 3
        assert [child["id"] for child in document["rootState"]["children"]] == [
            "Root.A",
            "Root.B",
        ]

    def test_with_an_output_path_the_file_is_written_and_the_path_printed(
        self, tmp_path
    ):
        import json

        target = tmp_path / "out.json"

        result = self._run(tmp_path, "-o", str(target))

        assert result.exit_code == 0, result.output
        assert result.output.strip() == str(target)
        written = json.loads(target.read_text(encoding="utf-8"))
        assert written["kind"] == "diagram"
        assert written["summary"]["states"] == 3


@pytest.mark.unittest
class TestAnUnusableDestinationIsReported:
    """
    A destination the command cannot write is named, not raised through.

    A suffix nothing can be inferred from, a scale asked for alongside a format
    that has no scale, and a directory that does not exist are all things a user
    types.  Each one has to come back as a sentence about the path.
    """

    def _run(self, tmp_path, *arguments):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        source = tmp_path / "machine.fcstm"
        source.write_text(SIMPLE, encoding="utf-8")
        return CliRunner().invoke(
            pyfcstmcli, ["diagram", "-i", str(source)] + list(arguments)
        )

    def test_an_unrecognised_suffix_lists_the_ones_that_work(self, tmp_path):
        result = self._run(tmp_path, "-o", str(tmp_path / "out.txt"))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "cannot infer an output format" in result.output
        assert ".png" in result.output

    def test_a_path_with_no_suffix_says_so(self, tmp_path):
        result = self._run(tmp_path, "-o", str(tmp_path / "out"))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "no suffix" in result.output

    def test_scale_is_refused_for_a_format_that_has_no_scale(self, tmp_path):
        result = self._run(tmp_path, "-o", str(tmp_path / "out.json"), "--scale", "2")

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "--scale is only supported for PNG output" in result.output

    def test_a_missing_destination_directory_names_the_path(self, tmp_path):
        target = tmp_path / "absent" / "out.json"

        result = self._run(tmp_path, "-o", str(target))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Failed to write" in result.output
        assert str(target) in result.output


@pytest.mark.unittest
class TestAnUnusableBrowserChoiceIsReported:
    """
    ``PYFCSTM_BROWSER`` is honoured or reported, never quietly replaced.

    The error text for a machine with no browser installed names this variable,
    so pointing it at a browser is part of the documented way out.  A typo in it
    therefore has to say the variable is the problem: falling through to whatever
    else happened to be installed would present the variable as authoritative
    while ignoring it.

    ``--open`` writes the viewer before launching the window, so what happens to
    that document is the other half of the contract: with ``-o`` it is the
    caller's file and stays, and its path is worth printing even though the
    window failed.
    """

    def _run(self, tmp_path, monkeypatch, *arguments):
        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        # Setting an environment variable is how this knob is used; nothing about
        # the library is being replaced.
        monkeypatch.setenv("PYFCSTM_BROWSER", str(tmp_path / "no-such-browser"))
        source = tmp_path / "machine.fcstm"
        source.write_text(SIMPLE, encoding="utf-8")
        return CliRunner().invoke(
            pyfcstmcli, ["diagram", "-i", str(source), "--open"] + list(arguments)
        )

    def test_a_bad_browser_path_names_the_variable(self, tmp_path, monkeypatch):
        target = tmp_path / "viewer.html"

        result = self._run(tmp_path, monkeypatch, "-o", str(target))

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "PYFCSTM_BROWSER" in result.output
        # The document was written before the window was attempted, and an
        # explicit path is never temporary, so it is still there to be opened by
        # hand -- which is why the failure prints it.
        assert str(target) in result.output
        assert target.is_file()

    def test_without_an_output_path_the_failure_points_at_the_flag(
        self, tmp_path, monkeypatch
    ):
        result = self._run(tmp_path, monkeypatch)

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "PYFCSTM_BROWSER" in result.output
        # No window opened, so nothing ever read the temporary document and it
        # was removed. There is no path to offer, only the flag that keeps one.
        assert "-o PATH" in result.output


@pytest.mark.unittest
class TestAnExplicitFormatGovernsTheSuffix:
    """
    ``--format`` overrides suffix inference rather than being checked against it.

    Inference exists for the common case; an explicit format is the caller
    stating what they want, so a suffix that would otherwise be unrecognised is
    their choice to make.
    """

    def test_an_unrecognised_suffix_is_accepted_with_an_explicit_format(self, tmp_path):
        import json

        from click.testing import CliRunner

        from pyfcstm.entry.cli import pyfcstmcli

        source = tmp_path / "machine.fcstm"
        source.write_text(SIMPLE, encoding="utf-8")
        target = tmp_path / "diagram.data"

        result = CliRunner().invoke(
            pyfcstmcli,
            ["diagram", "-i", str(source), "-o", str(target), "--format", "json"],
        )

        assert result.exit_code == 0, result.output
        assert json.loads(target.read_text(encoding="utf-8"))["kind"] == "diagram"
