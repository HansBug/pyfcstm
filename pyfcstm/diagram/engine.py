"""
Run the shared offline diagram renderer inside a constrained MiniRacer host.

The module owns the diagram asset boundary:

* :class:`DiagramAssetEngine` loads the generated ES2017 renderer and official
  resvg WebAssembly package, then exposes internal SVG/PNG operations.
* The canonical and expanded SVG validators enforce the closed renderer
  dialect before data reaches the rasterizer or leaves the process.
* Runtime selection, resource recovery guidance, CJK font registration, and
  timeout/context lifecycle handling are kept in one Python boundary.

This is an internal feasibility surface for the asset closure work. The
stable ``StateMachine.diagram`` facade and user-facing export commands remain
follow-up API work.

Example::

    >>> from pyfcstm.diagram import DiagramAssetEngine
    >>> engine = DiagramAssetEngine(timeout=30.0)
    >>> engine.timeout
    30.0
"""

import base64
import binascii
import inspect
import json
import math
import pkgutil
import re
import struct
import time
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class DiagramAssetError(RuntimeError):
    """
    Report a missing, corrupt, or unusable diagram runtime asset.

    Example::

        >>> raise DiagramAssetError("renderer.js is missing")
        Traceback (most recent call last):
        ...
        DiagramAssetError: renderer.js is missing
    """


class DiagramRenderError(DiagramAssetError):
    """
    Report invalid output or a rejected DiagramData request.

    Example::

        >>> raise DiagramRenderError("closed SVG dialect rejected output")
        Traceback (most recent call last):
        ...
        DiagramRenderError: closed SVG dialect rejected output
    """


class DiagramRenderLimitError(DiagramRenderError):
    """
    Report a render request that exceeds the bounded output contract.

    The limit is checked before entering the WebAssembly renderer whenever
    the canonical SVG exposes finite canvas dimensions.

    Example::

        >>> raise DiagramRenderLimitError("scale exceeds 4.0")
        Traceback (most recent call last):
        ...
        DiagramRenderLimitError: scale exceeds 4.0
    """


class DiagramEngineMetadataError(DiagramAssetError):
    """
    Report that installed MiniRacer distribution metadata is unavailable.

    Example::

        >>> raise DiagramEngineMetadataError("runtime metadata unavailable")
        Traceback (most recent call last):
        ...
        DiagramEngineMetadataError: runtime metadata unavailable
    """


class DiagramEngineConflictError(DiagramAssetError):
    """
    Report mutually exclusive MiniRacer distributions.

    This error is raised before a JavaScript context is created when both
    ``mini-racer`` and ``py-mini-racer`` are installed in one environment.

    Example::

        >>> raise DiagramEngineConflictError("install exactly one runtime")
        Traceback (most recent call last):
        ...
        DiagramEngineConflictError: install exactly one runtime
    """


_LATIN_FONT_ASSET_PATHS = (
    "fonts/JetBrainsMono-Regular.ttf",
    "fonts/JetBrainsMono-Medium.ttf",
    "fonts/JetBrainsMono-Bold.ttf",
)

_CJK_FONT_ASSET_PATHS = {
    "sc": ("fonts/NotoSansSC-Regular.otf", "fonts/NotoSansSC-Bold.otf"),
    "tc": ("fonts/NotoSansTC-Regular.otf", "fonts/NotoSansTC-Bold.otf"),
    "hk": ("fonts/NotoSansHK-Regular.otf", "fonts/NotoSansHK-Bold.otf"),
    "jp": ("fonts/NotoSansJP-Regular.otf", "fonts/NotoSansJP-Bold.otf"),
    "kr": ("fonts/NotoSansKR-Regular.otf", "fonts/NotoSansKR-Bold.otf"),
}

_CJK_FONT_FAMILIES = {
    "sc": "Noto Sans SC",
    "tc": "Noto Sans TC",
    "hk": "Noto Sans HK",
    "jp": "Noto Sans JP",
    "kr": "Noto Sans KR",
}
_CJK_LOCALE_PATTERN = re.compile(
    r"Noto Sans(?: Mono CJK|)\s+(SC|TC|HK|JP|KR)\b", re.IGNORECASE
)

_ASSET_ISSUE_URL = "https://github.com/HansBug/pyfcstm/issues"
_SVG_NS = "http://www.w3.org/2000/svg"
_SVG_MAX_BYTES = 16 * 1024 * 1024
_SVG_MAX_ELEMENTS = 100_000
_MAX_RENDER_SCALE = 4.0
_MAX_RENDER_DIMENSION = 16_384
_MAX_RENDER_PIXELS = 16_777_216
_MAX_RENDER_RGBA_BYTES = 67_108_864
_MAX_RENDER_PNG_BYTES = 33_554_432
_PNG_ALLOWED_CHUNKS = {b"IHDR", b"IDAT", b"IEND"}

_SVG_INPUT_ELEMENTS = {
    "svg",
    "defs",
    "marker",
    "filter",
    "feGaussianBlur",
    "feOffset",
    "feComponentTransfer",
    "feFuncA",
    "feFuncR",
    "feFuncG",
    "feFuncB",
    "feMerge",
    "feMergeNode",
    "g",
    "rect",
    "path",
    "line",
    "circle",
    "text",
}
_SVG_OUTPUT_ELEMENTS = {
    "svg",
    "defs",
    "filter",
    "feGaussianBlur",
    "feOffset",
    "feComponentTransfer",
    "feFuncA",
    "feFuncR",
    "feFuncG",
    "feFuncB",
    "feMerge",
    "feMergeNode",
    "clipPath",
    "g",
    "path",
}
_SVG_INPUT_ATTRIBUTES = {
    "svg": {
        "viewBox",
        "width",
        "height",
        "font-family",
        "font-size",
        "data-fcstm-canvas",
        "data-fcstm-direction",
        "data-fcstm-palette",
        "data-fcstm-mode",
    },
    "defs": set(),
    "marker": {
        "id",
        "viewBox",
        "refX",
        "refY",
        "markerWidth",
        "markerHeight",
        "orient",
        "markerUnits",
    },
    "filter": {"id", "x", "y", "width", "height"},
    "feGaussianBlur": {"in", "stdDeviation"},
    "feOffset": {"in", "dx", "dy"},
    "feComponentTransfer": set(),
    "feFuncA": {"type", "slope", "intercept"},
    "feFuncR": {"type", "slope", "intercept"},
    "feFuncG": {"type", "slope", "intercept"},
    "feFuncB": {"type", "slope", "intercept"},
    "feMerge": set(),
    "feMergeNode": {"in"},
    "g": {
        "data-fcstm-kind",
        "data-fcstm-id",
        "data-fcstm-variant",
        "data-fcstm-pseudo",
        "data-fcstm-composite",
        "data-fcstm-collapsed",
        "data-fcstm-range-start-line",
        "data-fcstm-range-start-character",
        "data-fcstm-range-end-line",
        "data-fcstm-range-end-character",
    },
    "rect": {
        "class",
        "x",
        "y",
        "width",
        "height",
        "rx",
        "ry",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-dasharray",
        "filter",
        "pointer-events",
    },
    "path": {
        "d",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-dasharray",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "marker-end",
        "data-fcstm-kind",
        "data-fcstm-id",
        "data-fcstm-range-start-line",
        "data-fcstm-range-start-character",
        "data-fcstm-range-end-line",
        "data-fcstm-range-end-character",
    },
    "line": {
        "x1",
        "y1",
        "x2",
        "y2",
        "stroke",
        "stroke-opacity",
        "stroke-width",
    },
    "circle": {
        "cx",
        "cy",
        "r",
        "fill",
        "stroke",
        "stroke-width",
        "data-fcstm-kind",
        "data-fcstm-id",
    },
    "text": {
        "x",
        "y",
        "fill",
        "font-family",
        "font-size",
        "font-weight",
        "text-anchor",
        "letter-spacing",
        "paint-order",
        "stroke",
        "stroke-width",
        "stroke-linejoin",
    },
}
_SVG_OUTPUT_ATTRIBUTES = {
    "svg": {"width", "height", "viewBox"},
    "defs": set(),
    "filter": {"id", "x", "y", "width", "height"},
    "feGaussianBlur": {"color-interpolation-filters", "in", "stdDeviation", "result"},
    "feOffset": {"color-interpolation-filters", "in", "dx", "dy", "result"},
    "feComponentTransfer": {"color-interpolation-filters", "in", "result"},
    "feFuncA": {"type", "slope", "intercept"},
    "feFuncR": {"type"},
    "feFuncG": {"type"},
    "feFuncB": {"type"},
    "feMerge": {"color-interpolation-filters", "result"},
    "feMergeNode": {"in"},
    "clipPath": {"id"},
    "g": {"clip-path", "filter", "transform"},
    "path": {
        "d",
        "fill",
        "fill-opacity",
        "paint-order",
        "stroke",
        "stroke-dasharray",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "stroke-width",
        "visibility",
    },
}

_DANGEROUS_URI_SCHEME_RE = re.compile(
    r"(?:javascript|vbscript|data|blob|about|file|https?|ftp|ws|wss|"
    r"chrome|chrome-extension):",
    re.IGNORECASE,
)
_URI_REFERENCE_RE = re.compile(r"url\(([^)]*)\)", re.IGNORECASE)


class _CanonicalSvg(str):
    """Private marker for SVG text emitted by the validated shared renderer."""


def _svg_tag(element: ET.Element) -> str:
    """Return an SVG local name, rejecting foreign namespaces."""
    prefix = "{%s}" % _SVG_NS
    if not isinstance(element.tag, str) or not element.tag.startswith(prefix):
        raise DiagramAssetError("closed SVG dialect rejected a non-SVG namespace")
    return element.tag[len(prefix) :]


def _svg_parse(svg: str) -> ET.Element:
    """Parse bounded XML while rejecting DTD, entity, comments, and PIs."""
    if not isinstance(svg, str):
        raise DiagramAssetError("closed SVG dialect requires UTF-8 SVG text")
    if len(svg.encode("utf-8")) > _SVG_MAX_BYTES:
        raise DiagramAssetError("closed SVG dialect rejected an oversized SVG")
    if any(token in svg for token in ("<!DOCTYPE", "<!ENTITY", "<?", "<!--", "<![")):
        raise DiagramAssetError(
            "closed SVG dialect rejected XML declarations or entities"
        )
    try:
        return ET.fromstring(svg)
    except ET.ParseError as err:
        # ParseError: malformed XML or an unsupported entity declaration.
        raise DiagramAssetError(
            "closed SVG dialect rejected malformed XML: %s" % err
        ) from err


def _summarize_exception(error: BaseException, limit: int = 512) -> str:
    """Return a bounded exception summary without embedding evaluated source."""
    text = " ".join(str(error).split())
    if not text:
        return "unspecified error"
    # MiniRacer may append the complete evaluated minified bundle after the
    # JavaScript error. Keep only the native error class and its short message.
    match = re.search(
        r"((?:TypeError|ReferenceError|RangeError|SyntaxError|URIError|"
        r"EvalError|Error):\s*[^`]{0,512}?)(?:\s+at\s+|`|$)",
        text,
    )
    if match:
        text = match.group(1).strip()
    else:
        text = re.split(r"\s+at\s+", text, maxsplit=1)[0].strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _validate_svg_tree(svg: str, output: bool) -> str:
    """Validate one canonical or expanded SVG against its closed dialect."""
    root = _svg_parse(svg)
    allowed_elements = _SVG_OUTPUT_ELEMENTS if output else _SVG_INPUT_ELEMENTS
    allowed_attributes = _SVG_OUTPUT_ATTRIBUTES if output else _SVG_INPUT_ATTRIBUTES
    count = 0
    ids = set()
    references = []
    for element in root.iter():
        count += 1
        if count > _SVG_MAX_ELEMENTS:
            raise DiagramAssetError("closed SVG dialect rejected too many XML elements")
        tag = _svg_tag(element)
        if tag not in allowed_elements:
            raise DiagramAssetError("closed SVG dialect rejected element: %s" % tag)
        attrs = allowed_attributes.get(tag, set())
        for name, value in element.attrib.items():
            if name.startswith("{") or name not in attrs:
                raise DiagramAssetError(
                    "closed SVG dialect rejected attribute %s on <%s>" % (name, tag)
                )
            if name == "id":
                if not value or value in ids:
                    raise DiagramAssetError(
                        "closed SVG dialect rejected duplicate or empty id"
                    )
                ids.add(value)
            if name.lower().startswith("on") or name in {"href", "xlink:href", "style"}:
                raise DiagramAssetError(
                    "closed SVG dialect rejected executable attribute: %s" % name
                )
            if _DANGEROUS_URI_SCHEME_RE.search(value):
                raise DiagramAssetError("closed SVG dialect rejected an external URL")
            for uri in _URI_REFERENCE_RE.findall(value):
                reference = uri.strip().strip("\"'")
                if not reference.startswith("#") or len(reference) == 1:
                    raise DiagramAssetError(
                        "closed SVG dialect rejected a non-local URL reference"
                    )
                references.append(reference[1:])
        if element.text and output and element.text.strip():
            raise DiagramAssetError("closed SVG dialect rejected residual text nodes")
        if element.tail and element.tail.strip():
            raise DiagramAssetError("closed SVG dialect rejected residual tail text")
    if root.tag != "{%s}svg" % _SVG_NS:
        raise DiagramAssetError("closed SVG dialect requires an SVG root element")
    for reference in references:
        if reference not in ids:
            raise DiagramAssetError(
                "closed SVG dialect rejected a broken local reference: %s" % reference
            )
    if not output:
        markers = list(root.iter("{%s}marker" % _SVG_NS))
        marker_refs = [
            element.attrib.get("marker-end")
            for element in root.iter()
            if element.attrib.get("marker-end")
        ]
        if markers:
            if len(markers) != 1 or markers[0].attrib.get("orient") != "auto":
                raise DiagramAssetError(
                    "closed SVG dialect rejected the marker orientation contract"
                )
            if markers[0].attrib.get("refX") != "10":
                raise DiagramAssetError(
                    "closed SVG dialect rejected the marker endpoint contract"
                )
            if any("marker-start" in element.attrib for element in root.iter()):
                raise DiagramAssetError("closed SVG dialect rejected marker-start")
        if marker_refs and not markers:
            raise DiagramAssetError(
                "closed SVG dialect rejected a missing marker definition"
            )
    elif any(_svg_tag(element) in {"text", "marker"} for element in root.iter()):
        raise DiagramAssetError(
            "closed SVG dialect rejected residual text or marker elements"
        )
    return svg


def _validate_canonical_svg(svg: str) -> _CanonicalSvg:
    """Validate and mark SVG emitted by the shared renderer."""
    return _CanonicalSvg(_validate_svg_tree(svg, output=False))


def _validate_expanded_svg(svg: str) -> str:
    """Validate the path-oriented SVG returned by resvg."""
    return _validate_svg_tree(svg, output=True)


_SVG_NUMBER_RE = re.compile(
    r"^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*(?:px)?\s*$"
)


def _svg_canvas_dimensions(svg: str) -> Tuple[float, float]:
    """Return finite positive canonical SVG canvas dimensions."""
    root = _svg_parse(svg)
    view_box = root.attrib.get("viewBox")
    if view_box is not None:
        parts = [item for item in re.split(r"[\s,]+", view_box.strip()) if item]
        if len(parts) != 4:
            raise DiagramRenderLimitError(
                "diagram render limit cannot determine the canonical SVG viewBox"
            )
        try:
            width, height = float(parts[2]), float(parts[3])
        except ValueError as err:
            # ValueError: a shared renderer viewBox contains non-numeric text.
            raise DiagramRenderLimitError(
                "diagram render limit cannot determine the canonical SVG viewBox"
            ) from err
    else:
        raw_width = root.attrib.get("width")
        raw_height = root.attrib.get("height")
        if (
            raw_width is None
            or raw_height is None
            or not (
                _SVG_NUMBER_RE.fullmatch(raw_width)
                and _SVG_NUMBER_RE.fullmatch(raw_height)
            )
        ):
            raise DiagramRenderLimitError(
                "diagram render limit requires finite numeric SVG width and height"
            )
        width, height = float(raw_width.rstrip("px ")), float(raw_height.rstrip("px "))
    if (
        not math.isfinite(width)
        or not math.isfinite(height)
        or width <= 0
        or height <= 0
    ):
        raise DiagramRenderLimitError(
            "diagram render limit requires finite positive SVG dimensions"
        )
    return width, height


def _checked_render_dimensions(svg: str, scale: float) -> Tuple[int, int]:
    """Validate render limits and return the expected scaled pixel size."""
    if scale > _MAX_RENDER_SCALE:
        raise DiagramRenderLimitError(
            "diagram render limit exceeded: scale %.6g > %.1f; reduce scale"
            % (scale, _MAX_RENDER_SCALE)
        )
    width, height = _svg_canvas_dimensions(svg)
    if width > _MAX_RENDER_DIMENSION or height > _MAX_RENDER_DIMENSION:
        raise DiagramRenderLimitError(
            "diagram render limit exceeded: source %.6gx%.6g exceeds %dpx "
            "per dimension; reduce the model size"
            % (width, height, _MAX_RENDER_DIMENSION)
        )
    source_pixels = width * height
    if source_pixels > _MAX_RENDER_PIXELS:
        raise DiagramRenderLimitError(
            "diagram render limit exceeded: source %.6g pixels exceeds %d; "
            "reduce the model size" % (source_pixels, _MAX_RENDER_PIXELS)
        )
    scaled_width = int(math.ceil(width * scale))
    scaled_height = int(math.ceil(height * scale))
    scaled_pixels = scaled_width * scaled_height
    if (
        scaled_width > _MAX_RENDER_DIMENSION
        or scaled_height > _MAX_RENDER_DIMENSION
        or scaled_pixels > _MAX_RENDER_PIXELS
        or scaled_pixels * 4 > _MAX_RENDER_RGBA_BYTES
    ):
        raise DiagramRenderLimitError(
            "diagram render limit exceeded: %.6gx%.6g at scale %.6g produces "
            "%dx%d pixels; limits are %dpx per dimension and %d pixels; "
            "reduce scale"
            % (
                width,
                height,
                scale,
                scaled_width,
                scaled_height,
                _MAX_RENDER_DIMENSION,
                _MAX_RENDER_PIXELS,
            )
        )
    return scaled_width, scaled_height


def _is_development_checkout() -> bool:
    """Return whether the package is running from the repository checkout."""
    root = Path(__file__).resolve().parents[2]
    return (root / "Makefile").is_file() and (
        root / "tools" / "build_diagram_assets.py"
    ).is_file()


def _asset_failure(
    name: str, cause: str, error: Optional[BaseException] = None
) -> DiagramAssetError:
    """Build a loud, actionable error for a missing or unusable asset."""
    detail = str(cause).strip() or "the resource failed validation"
    if error is not None:
        detail = "%s: %s" % (detail, _summarize_exception(error))
    if _is_development_checkout():
        action = (
            "This appears to be a development checkout; run `make build_assets` "
            "and retry."
        )
    else:
        action = (
            "This appears to be an installed package or CLI; report this failure "
            "at %s with the Python version, pyfcstm version, and this full error."
            % _ASSET_ISSUE_URL
        )
    return DiagramAssetError(
        "pyfcstm diagram asset failure for %s: %s. %s" % (name, detail, action)
    )


def _render_failure(
    name: str,
    cause: str,
    error: Optional[BaseException] = None,
    request_error: bool = False,
) -> DiagramRenderError:
    """Build an actionable error for a renderer request after startup."""
    detail = str(cause).strip() or "the renderer request failed"
    if error is not None:
        detail = "%s: %s" % (detail, _summarize_exception(error))
    if request_error:
        action = "check the DiagramData shape and renderer options, then retry"
    elif _is_development_checkout():
        action = "run `make build_assets` and retry after checking the renderer output"
    else:
        action = "report this full error at %s" % _ASSET_ISSUE_URL
    return DiagramRenderError(
        "pyfcstm diagram render failure for %s: %s. %s" % (name, detail, action)
    )


def _asset_bytes(name: str) -> bytes:
    """Load and minimally validate one generated asset."""
    try:
        data = pkgutil.get_data("pyfcstm.diagram.assets", name)
    except FileNotFoundError as err:
        # FileNotFoundError: an installed package physically lacks the
        # requested resource rather than returning a package-loader null.
        raise _asset_failure(
            name, "the expected packaged resource is missing", err
        ) from err
    except OSError as err:
        # OSError: importlib/pkgutil could not read a packaged resource.
        raise _asset_failure(
            name, "the packaged resource could not be read", err
        ) from err
    if data is None:
        raise _asset_failure(name, "the expected packaged resource is missing")
    if not isinstance(data, bytes):
        raise _asset_failure(
            name,
            "the packaged resource returned non-binary data instead of bytes",
        )
    if not data:
        raise _asset_failure(name, "the packaged resource is empty")
    if name.endswith(".js"):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as err:
            raise _asset_failure(
                name, "the JavaScript resource is not valid UTF-8", err
            ) from err
        if not text.strip():
            raise _asset_failure(name, "the JavaScript resource is empty")
    elif name == "resvg.wasm" and not data.startswith(b"\x00asm"):
        raise _asset_failure(name, "the resource is not a WebAssembly binary")
    elif name.startswith("fonts/") and not _valid_opentype(data):
        raise _asset_failure(
            name,
            "the resource failed OpenType table, bounds, or checksum validation",
        )
    return data


def _valid_opentype(data: bytes) -> bool:
    """Validate the bounded SFNT table directory of one OpenType font."""
    if len(data) < 12 or not data.startswith((b"\x00\x01\x00\x00", b"true", b"OTTO")):
        return False
    if len(data) % 4:
        # SFNT checksums cover the complete four-byte-padded font payload.
        return False
    try:
        table_count = struct.unpack(">H", data[4:6])[0]
    except struct.error:
        # struct.error: a truncated SFNT header cannot expose a table count.
        return False
    if table_count == 0:
        return False
    directory_end = 12 + table_count * 16
    if directory_end > len(data):
        return False
    table_tags = set()
    required_tags = {b"cmap", b"head", b"hhea", b"hmtx", b"maxp", b"name"}
    minimum_lengths = {
        b"cmap": 4,
        b"head": 54,
        b"hhea": 36,
        b"hmtx": 4,
        b"maxp": 6,
        b"name": 6,
        b"glyf": 1,
        b"CFF ": 1,
        b"CFF2": 1,
    }
    for offset in range(12, directory_end, 16):
        table_tag = data[offset : offset + 4]
        table_tags.add(table_tag)
        expected_checksum, table_offset, table_length = struct.unpack(
            ">III", data[offset + 4 : offset + 16]
        )
        if table_offset > len(data) or table_length > len(data) - table_offset:
            return False
        if table_length < minimum_lengths.get(table_tag, 0):
            return False
        table_data = bytearray(data[table_offset : table_offset + table_length])
        if table_tag == b"head" and len(table_data) >= 12:
            # OpenType defines head.checkSumAdjustment as zero while the head
            # table checksum is calculated; the directory stores that result.
            table_data[8:12] = b"\x00" * 4
        table_data.extend(b"\x00" * (-len(table_data) % 4))
        actual_checksum = (
            sum(struct.unpack(">%dI" % (len(table_data) // 4), table_data)) & 0xFFFFFFFF
        )
        if actual_checksum != expected_checksum:
            return False
    if not required_tags.issubset(table_tags) or not {
        b"glyf",
        b"CFF ",
        b"CFF2",
    }.intersection(table_tags):
        return False
    # OpenType requires the complete font checksum, including
    # head.checkSumAdjustment, to equal this fixed magic value.  Table-level
    # checksums alone cannot detect a damaged adjustment field.
    total_checksum = (
        sum(word[0] for word in struct.iter_unpack(">I", data)) & 0xFFFFFFFF
    )
    return total_checksum == 0xB1B0AFBA


def _decode_png_rgba(data: bytes) -> Tuple[int, int, Tuple[int, int, int, int]]:
    """Validate and decode the bounded RGBA PNG output contract."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("PNG output lacks the PNG signature")
    if len(data) > _MAX_RENDER_PNG_BYTES:
        raise ValueError("PNG output exceeds the encoded-size limit")
    position = 8
    saw_ihdr = False
    saw_idat = False
    idat_closed = False
    width = height = None
    compressed = bytearray()
    try:
        while position < len(data):
            if position + 12 > len(data):
                raise ValueError("PNG output has a truncated chunk header")
            length = struct.unpack(">I", data[position : position + 4])[0]
            chunk_end = position + 12 + length
            if chunk_end > len(data):
                raise ValueError("PNG output has a truncated chunk")
            chunk_type = data[position + 4 : position + 8]
            if len(chunk_type) != 4 or any(
                byte < 65 or (byte > 90 and byte < 97) or byte > 122
                for byte in chunk_type
            ):
                raise ValueError("PNG output has an invalid chunk type")
            if chunk_type not in _PNG_ALLOWED_CHUNKS:
                kind = "critical" if 65 <= chunk_type[0] <= 90 else "ancillary"
                raise ValueError(
                    "PNG output contains an unsupported %s chunk: %s"
                    % (kind, chunk_type.decode("ascii"))
                )
            payload = data[position + 8 : position + 8 + length]
            expected_crc = struct.unpack(">I", data[position + 8 + length : chunk_end])[
                0
            ]
            actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
            if actual_crc != expected_crc:
                raise ValueError("PNG output contains an invalid chunk checksum")
            if chunk_type == b"IHDR":
                if saw_ihdr or position != 8 or length != 13:
                    raise ValueError("PNG output has duplicate or misplaced IHDR")
                width, height, depth, color_type, compression, filtering, interlace = (
                    struct.unpack(">IIBBBBB", payload)
                )
                if (
                    not width
                    or not height
                    or width > _MAX_RENDER_DIMENSION
                    or height > _MAX_RENDER_DIMENSION
                    or width * height > _MAX_RENDER_PIXELS
                    or width * height * 4 > _MAX_RENDER_RGBA_BYTES
                    or depth != 8
                    or color_type != 6
                    or compression != 0
                    or filtering != 0
                    or interlace != 0
                ):
                    raise ValueError("PNG output violates the RGBA8 size contract")
                saw_ihdr = True
            elif not saw_ihdr:
                raise ValueError("PNG output has a non-IHDR first chunk")
            elif chunk_type == b"IDAT":
                if idat_closed:
                    raise ValueError("PNG output has non-contiguous IDAT chunks")
                compressed.extend(payload)
                saw_idat = True
            elif chunk_type == b"IEND":
                if length != 0 or not saw_idat:
                    raise ValueError("PNG output has an invalid IEND")
                position = chunk_end
                if position != len(data):
                    raise ValueError("PNG output has trailing bytes after IEND")
                break
            else:
                if saw_idat:
                    idat_closed = True
            position = chunk_end
        if not saw_ihdr or not saw_idat or position != len(data):
            raise ValueError("PNG output is missing IHDR, IDAT, or IEND")
        decoded = zlib.decompress(bytes(compressed))
    except (struct.error, ValueError, zlib.error, OverflowError) as err:
        # struct.error/ValueError: malformed chunk fields or scanlines;
        # zlib.error: IDAT is not a valid compressed stream; OverflowError:
        # checked dimension arithmetic cannot be represented by the decoder.
        if isinstance(err, ValueError):
            raise
        raise ValueError("PNG output has malformed compressed data") from err
    row_stride = width * 4 + 1
    if len(decoded) != row_stride * height:
        raise ValueError("PNG output has an invalid scanline length")
    previous = bytearray(width * 4)
    points = []
    offset = 0
    for y in range(height):
        filter_type = decoded[offset]
        encoded = decoded[offset + 1 : offset + row_stride]
        offset += row_stride
        row = bytearray(width * 4)
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
                predictor = min(
                    (left, above, upper_left),
                    key=lambda candidate: abs(estimate - candidate),
                )
            else:
                raise ValueError("PNG output uses an unsupported filter")
            row[index] = (value + predictor) & 0xFF
        for x in range(width):
            red, green, blue, alpha = row[x * 4 : x * 4 + 4]
            if alpha and (red < 245 or green < 245 or blue < 245):
                points.append((x, y))
        previous = row
    if not points:
        raise ValueError("PNG output contains no visible ink")
    xs, ys = zip(*points)
    return width, height, (min(xs), min(ys), max(xs), max(ys))


def _valid_png(data: bytes) -> bool:
    """Validate the opaque RGBA PNG payload emitted by the renderer."""
    try:
        _decode_png_rgba(data)
    except (TypeError, ValueError, struct.error, zlib.error, OverflowError):
        # TypeError/ValueError: non-bytes or malformed PNG; struct.error:
        # truncated binary fields; zlib.error/OverflowError: invalid stream or
        # checked decoder arithmetic.
        return False
    return True


class DiagramAssetEngine:
    """
    Drive the shared ES2017 renderer and resvg bridge in MiniRacer.

    :param timeout: Maximum seconds for one ELK/render polling operation,
        which must be finite and positive, defaults to ``30.0``.
    :type timeout: float, optional
    :param max_memory: Optional V8 heap limit in bytes applied to each
        JavaScript evaluation, defaults to ``None``.
    :type max_memory: int, optional

    Example::

        >>> engine = DiagramAssetEngine()
        >>> svg = engine.render_svg({"diagram": diagram_data})
        >>> svg.startswith("<svg")
        True
    """

    def __init__(self, timeout: float = 30.0, max_memory: Optional[int] = None) -> None:
        numeric_timeout = float(timeout)
        if not math.isfinite(numeric_timeout) or numeric_timeout <= 0:
            raise ValueError("timeout must be a finite positive number")
        if max_memory is not None:
            if isinstance(max_memory, bool) or not isinstance(max_memory, int):
                raise ValueError("max_memory must be a finite positive integer or None")
            if max_memory <= 0:
                raise ValueError("max_memory must be a finite positive integer or None")
        self.timeout = numeric_timeout
        self.max_memory = max_memory
        self._context = None
        self._active_context_count = 0
        self._context_token = None
        self._resvg_ready = False
        self._resvg_locale = None
        self._timeout_uses_seconds = False
        self._interrupt_errors = ()
        self._asset_eval_errors = ()
        self._ensure_context()

    @staticmethod
    def _distribution_version(name: str) -> Optional[str]:
        """Return one distribution version, or ``None`` when absent."""
        try:
            from importlib import metadata
        except ImportError:
            # Python 3.7 has no stdlib importlib.metadata; the backport is
            # optional, so fall back to setuptools when it is unavailable.
            try:
                import importlib_metadata as metadata
            except ImportError:
                try:
                    from pkg_resources import DistributionNotFound, get_distribution
                except ImportError as err:
                    # ImportError: Python 3.7 has no metadata provider and the
                    # optional backport/setuptools fallback is unavailable.
                    raise DiagramEngineMetadataError(
                        "cannot inspect installed MiniRacer distributions; "
                        "install importlib-metadata or setuptools"
                    ) from err
                try:
                    return str(get_distribution(name).version)
                except DistributionNotFound:
                    return None
        try:
            return str(metadata.version(name))
        except metadata.PackageNotFoundError:
            return None

    @staticmethod
    def _distribution_installed(name: str) -> bool:
        """Return whether a MiniRacer distribution is installed."""
        return DiagramAssetEngine._distribution_version(name) is not None

    def _create_context(self) -> Any:
        """Create the Python-version-appropriate MiniRacer context."""
        if self._distribution_installed("mini-racer") and self._distribution_installed(
            "py-mini-racer"
        ):
            modern_version = self._distribution_version("mini-racer") or "unknown"
            legacy_version = self._distribution_version("py-mini-racer") or "unknown"
            raise DiagramEngineConflictError(
                "mini-racer %s and py-mini-racer %s are installed together; "
                "install exactly one runtime for this Python version"
                % (modern_version, legacy_version)
            )
        try:
            from py_mini_racer import MiniRacer
        except ImportError as top_level_error:
            # Legacy py-mini-racer exports MiniRacer from this submodule.
            try:
                from py_mini_racer.py_mini_racer import MiniRacer
            except ImportError:
                # Preserve a modern package's native import/ABI failure when
                # neither supported export shape is available.
                raise top_level_error
        try:
            from py_mini_racer import (
                JSEvalException,
                JSOOMException,
                JSParseException,
                JSTimeoutException,
            )
        except ImportError:
            # py-mini-racer 0.6 keeps these exception classes in its legacy
            # module; modern mini-racer exports them at package top level.
            from py_mini_racer.py_mini_racer import (
                JSEvalException,
                JSOOMException,
                JSParseException,
                JSTimeoutException,
            )
        self._interrupt_errors = (JSTimeoutException, JSOOMException)
        self._asset_eval_errors = (JSEvalException, JSParseException)
        self._timeout_uses_seconds = (
            "timeout_sec" in inspect.signature(MiniRacer.eval).parameters
        )
        context = MiniRacer()
        self._active_context_count = 1
        self._context_token = "ctx-%d" % time.monotonic_ns()
        return context

    def _ensure_context(self) -> None:
        """Create and initialize a context after startup or interruption."""
        if self._context is None:
            self._context = self._create_context()
            self._load_bundle()

    def _discard_context(self) -> None:
        """Drop a context that was interrupted or exceeded its heap limit."""
        context = self._context
        self._context = None
        self._active_context_count = 0
        self._context_token = None
        self._resvg_ready = False
        self._resvg_locale = None
        if context is None:
            return
        close = getattr(context, "close", None)
        if callable(close):
            close()

    def _eval(self, source: str, timeout: Optional[float] = None) -> Any:
        """
        Evaluate JavaScript with the native MiniRacer resource limits.

        :param source: JavaScript source text to evaluate.
        :type source: str
        :param timeout: Evaluation limit in seconds, defaults to the engine
            timeout.
        :type timeout: float, optional
        :return: The converted MiniRacer result.
        :rtype: object
        :raises DiagramAssetError: If MiniRacer interrupts execution.
        """
        numeric_timeout = self.timeout if timeout is None else float(timeout)
        if not math.isfinite(numeric_timeout) or numeric_timeout <= 0:
            raise ValueError("timeout must be a finite positive number")
        self._ensure_context()
        try:
            if self._timeout_uses_seconds:
                return self._context.eval(
                    source,
                    timeout_sec=numeric_timeout,
                    max_memory=self.max_memory,
                )
            # py-mini-racer 0.6 accepts milliseconds and does not understand
            # the modern ``timeout_sec`` keyword.
            timeout_ms = max(1, int(math.ceil(numeric_timeout * 1000.0)))
            return self._context.eval(
                source,
                timeout=timeout_ms,
                max_memory=self.max_memory,
            )
        except Exception as err:
            # JSTimeoutException/JSOOMException are the only expected native
            # interruption failures; every other exception must propagate.
            if not isinstance(err, self._interrupt_errors):
                raise
            self._discard_context()
            raise DiagramAssetError(
                "embedded MiniRacer evaluation exceeded its time or memory limit"
            ) from err

    def _load_bundle(self) -> None:
        """Load the host shim and verified renderer bundle once."""
        try:
            host_shim = _asset_bytes("host-shim.js").decode("utf-8")
            renderer = _asset_bytes("renderer.js").decode("utf-8")
        except DiagramAssetError:
            self._discard_context()
            raise
        if "__pyfcstm_render_start" not in renderer:
            self._discard_context()
            raise _asset_failure(
                "renderer.js",
                "the bundle does not expose the required renderer entrypoint",
            )
        self._eval_asset("host-shim.js", host_shim)
        self._eval_asset(
            "host-shim.js",
            "globalThis.__pyfcstm_embedded_host = true;",
        )
        self._eval_asset("renderer.js", renderer)
        self._eval_asset(
            "resvg-bridge.js",
            "globalThis.__pyfcstm_bind_context_token(%s);"
            % json.dumps(self._context_token),
        )

    def _eval_asset(
        self,
        name: str,
        source: str,
        timeout: Optional[float] = None,
        request: bool = False,
    ) -> Any:
        """Evaluate an asset and attach the asset name to JavaScript failures."""
        try:
            return self._eval(source, timeout=timeout)
        except self._asset_eval_errors as err:
            self._discard_context()
            if request:
                raise _render_failure(
                    name,
                    "the renderer rejected the DiagramData request",
                    err,
                    request_error=True,
                ) from err
            raise _asset_failure(
                name, "the JavaScript resource could not be evaluated", err
            ) from err

    def _poll(
        self,
        request_id: str,
        timeout: Optional[float] = None,
        request: bool = False,
    ) -> Dict[str, Any]:
        """Read one renderer job status from the JS context."""
        value = self._eval_asset(
            "renderer.js",
            "__pyfcstm_render_poll(%s)" % json.dumps(request_id),
            timeout=timeout,
            request=request,
        )
        try:
            status = json.loads(str(value))
        except (TypeError, ValueError) as err:
            # TypeError/ValueError: a corrupted renderer returned non-JSON
            # polling data instead of its documented status envelope.
            raise _asset_failure(
                "renderer.js", "the renderer returned invalid job status data", err
            ) from err
        if not isinstance(status, dict):
            raise _asset_failure(
                "renderer.js", "the renderer returned a non-object job status"
            )
        return status

    def render_svg(self, request: Dict[str, Any]) -> str:
        """
        Render a canonical DiagramData request to SVG.

        :param request: JSON-compatible object containing ``diagram`` and
            optional renderer options.
        :type request: dict
        :return: UTF-8 SVG text.
        :rtype: str
        :raises ValueError: If ``request`` is not a JSON-compatible mapping.
        :raises DiagramAssetError: If the JS job reports an error or times out.

        Example::

            >>> engine = DiagramAssetEngine()
            >>> svg = engine.render_svg(diagram_data)
            >>> svg.startswith("<svg")
            True
        """
        request_id = "pyfcstm-%d" % time.monotonic_ns()
        deadline = time.monotonic() + self.timeout
        try:
            serialized_request = json.dumps(request, ensure_ascii=False)
        except (TypeError, ValueError) as err:
            # TypeError/ValueError: the caller supplied a non-JSON-compatible
            # DiagramData value such as a set, non-finite number, or cycle.
            raise ValueError("request must be JSON-compatible") from err
        self._eval_asset(
            "renderer.js",
            "__pyfcstm_render_start(%s, %s)"
            % (
                json.dumps(serialized_request),
                json.dumps(request_id),
            ),
            timeout=self.timeout,
            request=True,
        )
        while time.monotonic() < deadline:
            remaining = max(0.001, deadline - time.monotonic())
            status = self._poll(request_id, timeout=remaining, request=True)
            if status.get("status") == "done":
                self._eval_asset(
                    "renderer.js",
                    "__pyfcstm_render_drop(%s)" % json.dumps(request_id),
                    timeout=remaining,
                    request=True,
                )
                try:
                    svg = str(status["svg"])
                except KeyError as err:
                    self._discard_context()
                    raise _render_failure(
                        "renderer.js", "the completed job omitted its SVG output", err
                    ) from err
                if not svg.lstrip().startswith("<svg"):
                    self._discard_context()
                    raise _render_failure(
                        "renderer.js", "the renderer returned malformed SVG output"
                    )
                try:
                    return _validate_canonical_svg(svg)
                except DiagramAssetError as err:
                    self._discard_context()
                    raise _render_failure(
                        "renderer.js",
                        "the renderer returned SVG outside the closed SVG dialect",
                        err,
                    ) from err
            if status.get("status") == "error":
                self._eval_asset(
                    "renderer.js",
                    "__pyfcstm_render_drop(%s)" % json.dumps(request_id),
                    timeout=remaining,
                    request=True,
                )
                error = str(status.get("error", "unknown renderer error"))
                self._discard_context()
                raise _render_failure(
                    "renderer.js",
                    "the renderer job failed",
                    ValueError(error),
                    request_error=True,
                )
            time.sleep(0.001)
        # The renderer promise may still be pending in the old context.  A
        # Python-side deadline is therefore terminal too: discard the whole
        # context instead of allowing the next request to observe stale jobs.
        self._discard_context()
        raise DiagramAssetError("diagram renderer timed out after %.1fs" % self.timeout)

    def _ensure_resvg(self, cjk_locale: str = "sc") -> None:
        """Compile resvg and lazily register the selected locale's font pair."""
        locale = str(cjk_locale).lower()
        if locale not in _CJK_FONT_ASSET_PATHS:
            raise ValueError("unsupported CJK locale: %s" % cjk_locale)
        if self._resvg_ready and self._resvg_locale != locale:
            # resvg retains parsed font data inside the WASM heap. Recreate the
            # context when switching locales so a long-lived Python process
            # does not accumulate every CJK face it has rendered.
            self._discard_context()
        wasm_bytes = _asset_bytes("resvg.wasm")
        wasm = base64.b64encode(wasm_bytes).decode("ascii")
        deadline = time.monotonic() + self.timeout
        if not self._resvg_ready:
            self._eval_asset(
                "resvg.wasm",
                "__pyfcstm_resvg_init(%s)" % json.dumps(wasm),
            )
        while time.monotonic() < deadline:
            remaining = max(0.001, deadline - time.monotonic())
            status = (
                "ok"
                if self._resvg_ready
                else str(
                    self._eval_asset(
                        "resvg.wasm", "__pyfcstm_resvg_status", timeout=remaining
                    )
                )
            )
            if status == "ok" and self._resvg_locale != locale:
                font_paths = _LATIN_FONT_ASSET_PATHS + _CJK_FONT_ASSET_PATHS[locale]
                fonts = [
                    base64.b64encode(_asset_bytes(path)).decode("ascii")
                    for path in font_paths
                ]
                self._eval_asset(
                    "fonts/*",
                    "__pyfcstm_resvg_register_fonts(%s, %s)"
                    % (json.dumps(fonts), json.dumps(_CJK_FONT_FAMILIES[locale])),
                    timeout=remaining,
                )
                self._resvg_ready = True
                self._resvg_locale = locale
                return
            if status == "ok":
                return
            if status == "error":
                error = str(
                    self._eval_asset(
                        "resvg.wasm", "__pyfcstm_resvg_error", timeout=remaining
                    )
                )
                self._discard_context()
                raise _asset_failure(
                    "resvg.wasm", "WASM initialization failed", ValueError(error)
                )
            time.sleep(0.001)
        self._discard_context()
        raise _asset_failure("resvg.wasm", "resvg WASM initialization timed out")

    def _canonical_input(self, request: Any) -> _CanonicalSvg:
        """Resolve a DiagramData request or an internal canonical SVG."""
        if isinstance(request, _CanonicalSvg):
            return request
        if isinstance(request, dict):
            return self.render_svg(request)
        raise ValueError(
            "render_png/expand_svg require a DiagramData request; raw SVG input "
            "is not supported"
        )

    def render_png(self, request: Dict[str, Any], scale: float = 1.0) -> bytes:
        """
        Rasterize a DiagramData request with the pinned resvg WASM backend.

        :param request: JSON-compatible DiagramData request.
        :type request: dict
        :param scale: Finite positive raster scale, defaults to ``1.0``.
        :type scale: float, optional
        :return: PNG bytes.
        :rtype: bytes
        :raises ValueError: If ``scale`` is not finite and positive.
        :raises DiagramRenderLimitError: If scale or the checked output size
            exceeds the bounded PNG contract.
        :raises DiagramAssetError: If resvg reports a rendering failure.

        Example::

            >>> png = engine.render_png(diagram_data, scale=2.0)
            >>> png.startswith(b"\\x89PNG")
            True
        """
        if isinstance(scale, bool):
            raise ValueError("scale must be a finite positive number")
        if scale is None:
            raise ValueError("scale must be a finite positive number")
        numeric_scale = float(scale)
        if not math.isfinite(numeric_scale) or numeric_scale <= 0:
            raise ValueError("scale must be a finite positive number")
        svg = self._canonical_input(request)
        expected_width, expected_height = _checked_render_dimensions(svg, numeric_scale)
        self._ensure_resvg(self._locale_from_svg(svg))
        encoded = self._eval_asset(
            "resvg.wasm",
            "__pyfcstm_resvg_png(%s, %s)"
            % (json.dumps(svg), json.dumps(numeric_scale)),
            request=True,
        )
        try:
            result = base64.b64decode(str(encoded), validate=True)
        except (ValueError, binascii.Error) as err:
            # ValueError/binascii.Error: the WASM bridge returned malformed
            # base64 instead of a PNG payload.
            raise _render_failure(
                "resvg.wasm", "the renderer returned invalid PNG data", err
            ) from err
        try:
            width, height, _bbox = _decode_png_rgba(result)
        except (TypeError, ValueError, struct.error, zlib.error, OverflowError) as err:
            # TypeError/ValueError: the WASM bridge returned malformed or
            # blank PNG data; struct.error/zlib.error/OverflowError: the
            # binary decoder rejected its structure or checked arithmetic.
            raise _render_failure(
                "resvg.wasm", "the renderer returned invalid PNG data", err
            ) from err
        if (width, height) != (expected_width, expected_height):
            raise _render_failure(
                "resvg.wasm",
                "the renderer returned PNG dimensions %dx%d instead of %dx%d"
                % (width, height, expected_width, expected_height),
            )
        return result

    def expand_svg(self, request: Dict[str, Any]) -> str:
        """
        Expand a DiagramData request into resvg's normalized vector SVG.

        :param request: JSON-compatible DiagramData request.
        :type request: dict
        :return: Normalized vector SVG text.
        :rtype: str
        :raises DiagramAssetError: If resvg returns malformed or unsupported SVG.

        Example::

            >>> expanded = engine.expand_svg(diagram_data)
            >>> "<path" in expanded
            True
        """
        svg = self._canonical_input(request)
        self._ensure_resvg(self._locale_from_svg(svg))
        expanded = str(
            self._eval_asset(
                "resvg.wasm",
                "__pyfcstm_resvg_expand(%s)" % json.dumps(svg),
                timeout=self.timeout,
            )
        )
        stripped = expanded.strip()
        if not stripped.startswith("<svg") or not (
            stripped.endswith("</svg>") or stripped.endswith("/>")
        ):
            raise _render_failure(
                "resvg.wasm", "the renderer returned malformed expanded SVG output"
            )
        try:
            return _validate_expanded_svg(expanded)
        except DiagramAssetError as err:
            raise _render_failure(
                "resvg.wasm",
                "the renderer returned SVG outside the closed SVG dialect",
                err,
            ) from err

    @staticmethod
    def _locale_from_svg(svg: str) -> str:
        """Infer the embedded CJK face from an SVG font-family attribute."""
        match = _CJK_LOCALE_PATTERN.search(str(svg))
        return match.group(1).lower() if match else "sc"
