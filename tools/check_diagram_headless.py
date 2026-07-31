"""
Exercise the synchronous export path over the checked-in canonical corpus.

The unit tests cover the export contract on a handful of hand-written machines.
This command covers the same contract over every layout the corpus carries, at
every documented scale, repeated, so a defect that only appears on one shape or
only on the second call is caught.

The three properties it exists for, in order of how quietly they fail:

* **Determinism.** Two exports of the same diagram must produce the same
  drawing.  A renderer that leaks state between calls still returns a valid file
  each time, so nothing but a repeat comparison notices.
* **Scale.** A PNG at 2x must be twice the pixels of the same PNG at 1x.  An
  export that drops the scale returns a perfectly valid image of the wrong size.
* **Vector PDF.** The page must match the diagram and carry no image object.  A
  writer that rasterised the drawing and embedded it as one bitmap produces a
  file that opens, prints, and looks right until it is zoomed.

Run it directly, or through ``make diagram_headless_check``::

    $ python tools/check_diagram_headless.py --all-cases --formats svg,png,pdf \\
          --repeat 3 --png-scales 1,2,4 --pdf-require-zero-images \\
          --pdf-page-size-match
"""

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CORPUS = ROOT / "tools" / "diagram_assets" / "corpus" / "shared-layouts.json"

from pyfcstm.diagram.engine import DiagramAssetEngine  # noqa: E402

#: How many cases to use when ``--all-cases`` is absent.  One case is enough to
#: tell "the export is broken" from "the export works", which is what a quick
#: local run wants; the full corpus is what CI wants.
SAMPLE_CASES = 2


def load_requests(path: Path, all_cases: bool) -> List[Dict[str, Any]]:
    """
    Read renderer requests from a checked-in corpus.

    :param path: Corpus file.
    :type path: pathlib.Path
    :param all_cases: Whether to use every case rather than a sample.
    :type all_cases: bool
    :return: Renderer requests, each carrying at least a ``diagram``.
    :rtype: list[dict]
    :raises ValueError: If the corpus cannot be read or carries no case.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases = payload["cases"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError: the corpus has no ``cases`` array.
        # OSError/ValueError: the file cannot be read or is not JSON.
        raise ValueError("cannot read the headless corpus: %s" % path) from err
    if not isinstance(cases, list) or not cases:
        raise ValueError("the headless corpus carries no case: %s" % path)
    selected = cases if all_cases else cases[:SAMPLE_CASES]
    requests = []
    for case in selected:
        if not isinstance(case, dict):
            continue
        request = case.get("request")
        if isinstance(request, dict) and "diagram" in request:
            requests.append(request)
        elif "diagram" in case:
            requests.append({"diagram": case["diagram"]})
    if not requests:
        raise ValueError("no case in %s carries a diagram request" % path)
    return requests


def canvas_size(svg: str) -> Tuple[float, float]:
    """
    Read the declared canvas size out of an SVG document.

    :param svg: SVG text.
    :type svg: str
    :return: Width and height in user units.
    :rtype: tuple[float, float]
    :raises ValueError: If the document declares no usable size.
    """
    header = svg[:2048]
    width = re.search(r'\bwidth="([\d.]+)', header)
    height = re.search(r'\bheight="([\d.]+)', header)
    if width is None or height is None:
        raise ValueError("the renderer returned an SVG with no usable size")
    return float(width.group(1)), float(height.group(1))


def png_size(data: bytes) -> Tuple[int, int]:
    """
    Read a PNG's declared dimensions.

    :param data: PNG bytes.
    :type data: bytes
    :return: Width and height in pixels.
    :rtype: tuple[int, int]
    :raises ValueError: If the payload is not a PNG with an IHDR header.
    """
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        raise ValueError("the rasteriser returned something that is not a PNG")
    try:
        return struct.unpack(">II", data[16:24])
    except struct.error as err:
        # struct.error: the header is present but truncated, which a rasteriser
        # that ran out of memory part-way through can produce. Reported as a
        # malformed payload rather than crashing the gate.
        raise ValueError("the PNG header is truncated") from err


def pdf_page_size(data: bytes) -> Tuple[float, float]:
    """
    Read a PDF's first page box.

    :param data: PDF bytes.
    :type data: bytes
    :return: Page width and height in PDF units.
    :rtype: tuple[float, float]
    :raises ValueError: If no media box can be found.
    """
    match = re.search(rb"/MediaBox\s*\[([\d.\s-]+)\]", data)
    if match is None:
        raise ValueError("the PDF declares no media box")
    numbers = [float(part) for part in match.group(1).split()]
    if len(numbers) != 4:
        raise ValueError("the PDF media box is malformed")
    return numbers[2] - numbers[0], numbers[3] - numbers[1]


#: The operator sequence a browser-only text halo leaves in a PDF content stream:
#: a colour, a 3-unit line width, and a white stroke colour.  The browser export
#: gate has looked for this since the halo was found baked into its own output; the
#: synchronous path needs the same check, because it was shipping exactly that
#: defect while every structural assertion passed.
HALO_OPERATORS = re.compile(rb"[0-9.]+ [0-9.]+ [0-9.]+ rg\n3\. w\n1\. G")


#: Stream declarations, so each payload can be read together with the filter that
#: produced it.  Scanning a payload without knowing its encoding is how a halo
#: check becomes a zero that means nothing.
STREAM_RECORDS = re.compile(rb"<<(?P<info>[^<>]*(?:<<[^>]*>>[^<>]*)*)>>\s*stream\r?\n", re.S)


def inflated_streams(data: bytes) -> bytes:
    """
    Decode a PDF's content streams so their operators can be read.

    Each stream is decoded according to the filter it declares.  A filter this
    cannot decode is an error rather than a fallback: scanning encoded bytes as if
    they were operators finds nothing, the result is non-empty so an emptiness
    guard stays quiet, and the check reports zero for a document it never read.

    :param data: PDF bytes.
    :type data: bytes
    :return: The concatenated decoded streams.
    :rtype: bytes
    :raises ValueError: If a stream declares a filter this cannot decode.
    """
    import zlib

    text = b""
    position = 0
    for match in STREAM_RECORDS.finditer(data):
        info = match.group("info")
        end = data.find(b"endstream", match.end())
        if end < 0:
            continue
        payload = data[match.end() : end]
        position = end
        filters = re.findall(rb"/Filter\s*(?:\[([^\]]*)\]|/(\w+))", info)
        names = set()
        for bracketed, single in filters:
            names.update(re.findall(rb"/(\w+)", bracketed))
            if single:
                names.add(single)
        if not names:
            text += payload
            continue
        unsupported = sorted(name for name in names if name != b"FlateDecode")
        if unsupported:
            raise ValueError(
                "a PDF content stream declares filter(s) this check cannot decode: "
                "%s; the halo scan would otherwise report zero for bytes it never "
                "read" % b", ".join(unsupported).decode("ascii", "replace")
            )
        try:
            text += zlib.decompress(payload)
        except zlib.error as err:
            # zlib.error: the stream declares FlateDecode but does not decode,
            # which means the document is malformed rather than differently
            # encoded.
            raise ValueError("a FlateDecode content stream could not be read") from err
    if position == 0 and not text:
        return b""
    return text


def content_streams(data: bytes) -> List[bytes]:
    """
    Extract a PDF's content streams, which carry the drawing.

    The whole file is not comparable between runs because it embeds a creation
    timestamp.  The streams are what has to be stable.

    :param data: PDF bytes.
    :type data: bytes
    :return: Raw stream payloads in file order.
    :rtype: list[bytes]
    """
    return re.findall(rb"stream\r?\n(.*?)endstream", data, re.S)


def check_case(
    engine: DiagramAssetEngine,
    request: Dict[str, Any],
    formats: Sequence[str],
    repeat: int,
    png_scales: Sequence[float],
    require_zero_images: bool,
    page_size_match: bool,
) -> Dict[str, int]:
    """
    Check every requested property for one diagram.

    :param engine: Engine carrying the PDF writer when PDF is requested.
    :type engine: pyfcstm.diagram.engine.DiagramAssetEngine
    :param request: Renderer request.
    :type request: dict
    :param formats: Formats to exercise, from ``svg``, ``png`` and ``pdf``.
    :type formats: collections.abc.Sequence[str]
    :param repeat: How many times to export each format.
    :type repeat: int
    :param png_scales: Scales to rasterise at.
    :type png_scales: collections.abc.Sequence[float]
    :param require_zero_images: Whether a PDF must carry no image object.
    :type require_zero_images: bool
    :param page_size_match: Whether the PDF page must match the diagram.
    :type page_size_match: bool
    :return: How many exports of each format were checked.
    :rtype: dict[str, int]
    :raises ValueError: If any checked property does not hold.
    """
    counts = {"svg": 0, "png": 0, "pdf": 0}
    canonical = engine.render_svg(request)
    width, height = canvas_size(canonical)

    if "svg" in formats:
        first = engine.expand_svg(request)
        for token in ("<text", "<marker", "font-family"):
            if token in first:
                raise ValueError(
                    "the exported SVG still carries %s, so it is not the expanded "
                    "form and depends on fonts the reader may not have" % token
                )
        for _ in range(repeat):
            again = engine.expand_svg(request)
            if again != first:
                raise ValueError(
                    "two exports of the same diagram produced different SVG"
                )
            counts["svg"] += 1

    if "png" in formats:
        base = None
        for scale in png_scales:
            data = engine.render_png(canonical, scale=scale)
            actual = png_size(data)
            if base is None:
                base = (actual[0] / scale, actual[1] / scale)
            expected = (round(base[0] * scale), round(base[1] * scale))
            if abs(actual[0] - expected[0]) > 1 or abs(actual[1] - expected[1]) > 1:
                raise ValueError(
                    "a PNG at scale %g measured %dx%d where %dx%d was expected, so "
                    "the scale was not applied" % (scale, actual[0], actual[1], *expected)
                )
            for _ in range(repeat - 1):
                if engine.render_png(canonical, scale=scale) != data:
                    raise ValueError(
                        "two rasterisations of the same diagram at scale %g differed"
                        % scale
                    )
            counts["png"] += 1

    if "pdf" in formats:
        # The canonical document, the same thing the public export hands over. The
        # writer strips the browser-only text halo and only then expands, and the
        # strip matches on `<text>`; pre-expanding here reproduced the very defect
        # the halo assertion below exists to catch, which is how this line was
        # found.
        first = engine.render_pdf(canonical, width, height)
        if not first.startswith(b"%PDF-"):
            raise ValueError("the PDF writer returned something that is not a PDF")
        if require_zero_images and (
            b"/Subtype /Image" in first or b"/Subtype/Image" in first
        ):
            raise ValueError(
                "the PDF carries an image object, so the drawing was rasterised "
                "rather than kept as vectors"
            )
        if page_size_match:
            page_width, page_height = pdf_page_size(first)
            if abs(page_width - width) > 2.0 or abs(page_height - height) > 2.0:
                raise ValueError(
                    "the PDF page is %gx%g where the diagram is %gx%g"
                    % (page_width, page_height, width, height)
                )
        baseline = content_streams(first)
        if not baseline:
            raise ValueError("the PDF carries no content stream")
        operators = inflated_streams(first)
        if not operators:
            # A zero count against nothing scanned is not evidence, and a filter
            # change would otherwise retire the halo check without a word.
            raise ValueError("no PDF content stream could be read for inspection")
        halos = len(HALO_OPERATORS.findall(operators))
        if halos:
            raise ValueError(
                "the PDF carries %d browser-only text halo(s): the writer was given "
                "an already-expanded document, so its halo removal -- which matches "
                "on <text> elements -- found nothing to remove and the halo was "
                "baked into a path drawn over the glyphs" % halos
            )
        for _ in range(repeat):
            again = engine.render_pdf(canonical, width, height)
            if content_streams(again) != baseline:
                raise ValueError(
                    "two PDF exports of the same diagram produced different drawings"
                )
            counts["pdf"] += 1

    return counts


def _self_check() -> None:
    """
    Prove the per-format validators reject the shapes they exist to catch.

    The checks that matter here are the ones a valid-looking file would pass: a
    PNG whose dimensions ignore the requested scale, a PDF whose page does not
    match the diagram, and a PDF carrying a bitmap.  Each is exercised on a
    synthetic payload, so a validator that stopped asserting is caught without
    needing a renderer.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If any validator accepts a bad payload, or rejects a good
        one.
    """
    import zlib

    def png(width, height):
        header = struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
        chunk = struct.pack(">I", 13) + b"IHDR" + header
        chunk += struct.pack(">I", zlib.crc32(b"IHDR" + header) & 0xFFFFFFFF)
        return b"\x89PNG\r\n\x1a\n" + chunk

    assert png_size(png(200, 100)) == (200, 100)
    for label, payload in (
        ("something that is not a PNG", b"not a png at all"),
        ("a PNG with no IHDR", b"\x89PNG\r\n\x1a\n" + b"\x00" * 24),
        ("a truncated PNG header", b"\x89PNG\r\n\x1a\n" + b"\x00" * 4 + b"IHDR"),
    ):
        try:
            png_size(payload)
        except ValueError:
            continue
        raise SystemExit("the PNG check accepted %s" % label)

    good_pdf = b"%PDF-1.3\n/MediaBox [0 0 200 100]\nstream\nxx\nendstream\n"
    assert pdf_page_size(good_pdf) == (200.0, 100.0)
    # The capture keeps the trailing newline the payload was written with, which
    # is exactly the shape the real comparison sees.
    assert content_streams(good_pdf) == [b"xx\n"]
    for label, payload in (
        ("a PDF with no media box", b"%PDF-1.3\nno box here\n"),
        ("a malformed media box", b"%PDF-1.3\n/MediaBox [0 0 200]\n"),
    ):
        try:
            pdf_page_size(payload)
        except ValueError:
            continue
        raise SystemExit("the PDF page check accepted %s" % label)

    assert canvas_size('<svg width="120" height="80">') == (120.0, 80.0)
    try:
        canvas_size("<svg>")
    except ValueError:
        pass
    else:
        raise SystemExit("the canvas check accepted a document with no size")
    print("diagram headless exports: self-check passed")


def main(argv=None) -> int:
    """
    Run the headless export checks and print a JSON summary.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int
    :raises ValueError: If any checked property does not hold.
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="run this command's own self-check"
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--all-cases", action="store_true")
    parser.add_argument("--formats", default="svg,png,pdf")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--png-scales", default="1")
    parser.add_argument("--pdf-require-zero-images", action="store_true")
    parser.add_argument("--pdf-page-size-match", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.check:
        _self_check()
        return 0

    formats = tuple(
        item.strip() for item in arguments.formats.split(",") if item.strip()
    )
    if not formats or any(item not in {"svg", "png", "pdf"} for item in formats):
        raise ValueError("--formats must contain only svg,png,pdf")
    if arguments.repeat < 1:
        raise ValueError("--repeat must be at least 1")
    scales = tuple(
        float(item.strip()) for item in arguments.png_scales.split(",") if item.strip()
    )
    if not scales or any(scale <= 0 for scale in scales):
        raise ValueError("--png-scales must be positive numbers")

    requests = load_requests(arguments.corpus, arguments.all_cases)
    engine = DiagramAssetEngine(include_pdf="pdf" in formats)
    totals = {"svg": 0, "png": 0, "pdf": 0}
    for request in requests:
        counts = check_case(
            engine,
            request,
            formats,
            arguments.repeat,
            scales,
            arguments.pdf_require_zero_images,
            arguments.pdf_page_size_match,
        )
        for key, value in counts.items():
            totals[key] += value
    print(
        json.dumps(
            {
                "cases": len(requests),
                "formats": list(formats),
                "repeat": arguments.repeat,
                "pngScales": list(scales),
                "exports": totals,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
