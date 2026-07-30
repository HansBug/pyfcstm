"""
Run the shared offline diagram renderer inside a constrained MiniRacer host.

The module owns the diagram asset boundary:

* :class:`DiagramAssetEngine` loads the generated ES2017 renderer and official
  resvg WebAssembly package, then exposes internal SVG/PNG operations.
* Basic SVG and PNG envelope checks reject malformed renderer output.  Strict
  visual dialect and pixel checks live in the repository maintenance gates.
* Runtime selection, resource recovery guidance, CJK font registration, and
  timeout/context lifecycle handling are kept in one Python boundary.

This is the internal asset boundary, not the API users reach for. That is
:class:`pyfcstm.diagram.api.Diagram`, via :meth:`pyfcstm.model.model.StateMachine.diagram`
and the ``pyfcstm diagram`` command; both are delivered and layered on top of
this module. Depend on the engine directly only from maintenance tooling, and
note that it needs the optional MiniRacer runtime that
``pip install pyfcstm[viz]`` provides.

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
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


class DiagramError(RuntimeError):
    """
    Base class for public diagram capability and rendering failures.

    Example::

        >>> raise DiagramError("diagram operation failed")
        Traceback (most recent call last):
        ...
        DiagramError: diagram operation failed
    """


class DiagramUnavailableError(DiagramError):
    """
    Report an optional diagram capability that is not installed.

    Example::

        >>> raise DiagramUnavailableError("headless renderer is not installed")
        Traceback (most recent call last):
        ...
        DiagramUnavailableError: headless renderer is not installed
    """


class DiagramAssetError(DiagramError):
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

        >>> raise DiagramRenderError("SVG output envelope rejected")
        Traceback (most recent call last):
        ...
        DiagramRenderError: SVG output envelope rejected
    """


class DiagramRenderLimitError(DiagramError):
    """
    Report an export whose size exceeds a documented output limit.

    This is deliberately a sibling of :class:`DiagramRenderError` rather than a
    subclass of it.  The two describe different situations and have different
    remedies: a render failure means the renderer was asked to do something and
    could not, while a limit failure means it was never asked, because the
    requested size was refused by a checked multiplication first.  A caller
    writing ``except DiagramRenderError`` is handling the former, and should not
    silently absorb the latter -- lowering ``scale`` fixes a limit failure and
    fixes nothing else.

    :ivar limit_name: Identifier of the limit that fired.
    :vartype limit_name: str

    Example::

        >>> raise DiagramRenderLimitError("scaled width 32768px exceeds 16384px")
        Traceback (most recent call last):
        ...
        DiagramRenderLimitError: scaled width 32768px exceeds 16384px
    """

    def __init__(self, message, limit_name=None):
        """
        Record the message and, when known, which limit fired.

        :param message: Human-readable explanation naming the sizes involved.
        :type message: str
        :param limit_name: Identifier of the limit that fired, defaults to
            ``None``.
        :type limit_name: str, optional
        """
        super().__init__(message)
        self.limit_name = limit_name


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


class DiagramEngineLoadError(DiagramAssetError):
    """
    Report an installed MiniRacer distribution that cannot be imported.

    Example::

        >>> raise DiagramEngineLoadError("mini-racer ABI failed")
        Traceback (most recent call last):
        ...
        DiagramEngineLoadError: mini-racer ABI failed
    """


class _DiagramEvaluationInterruptedError(DiagramAssetError):
    """Identify a native MiniRacer timeout or memory interruption."""


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
_ASSET_LOADER_BOOTSTRAP = """
(function () {
  const evaluate = globalThis.eval;
  globalThis.__pyfcstm_load_asset = function (source) {
    try {
      evaluate(String(source));
      return "ok";
    } catch (error) {
      return String((error && (error.stack || error.message)) || error);
    }
  };
})();
"""


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    """Reject real document type declarations while parsing SVG XML."""

    def doctype(
        self, _name: str, _pubid: Optional[str], _system: Optional[str]
    ) -> None:
        """Reject DTDs, including the only valid context for entity declarations."""
        raise DiagramAssetError("SVG output contains a DTD or entity declaration")


def _svg_parse(svg: str) -> ET.Element:
    """Parse SVG XML and require the SVG root element."""
    if not isinstance(svg, str):
        raise DiagramAssetError("SVG output requires UTF-8 text")
    try:
        parser = ET.XMLParser(target=_NoDoctypeTreeBuilder())
        root = ET.fromstring(svg, parser=parser)
    except ET.ParseError as err:
        # ParseError: malformed XML returned by the renderer or supplied as a
        # compatibility SVG input.
        raise DiagramAssetError("SVG output is not well-formed: %s" % err) from err
    if root.tag != "{%s}svg" % _SVG_NS:
        raise DiagramAssetError("SVG output requires an SVG root element")
    return root


def _summarize_exception(error: BaseException, limit: int = 512) -> str:
    """Return a bounded exception summary without embedding evaluated source."""
    lines = [line.strip() for line in str(error).splitlines() if line.strip()]
    if not lines:
        return "unspecified error"
    error_pattern = re.compile(
        r"(?:TypeError|ReferenceError|RangeError|SyntaxError|URIError|"
        r"EvalError|Error):\s*.*"
    )
    # MiniRacer places evaluated source and carets on later lines. Keep the
    # first native error headline and discard those source lines and stacks.
    match = next(
        (error_pattern.search(line) for line in lines if error_pattern.search(line)),
        None,
    )
    text = match.group(0).strip() if match else lines[0]
    text = re.split(r"\s+at\s+|`", text, maxsplit=1)[0].strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _check_canonical_svg(svg: str) -> str:
    """Check the basic canonical SVG envelope."""
    _svg_parse(svg)
    return svg


def _check_expanded_svg(svg: str) -> str:
    """Check the basic SVG envelope returned by resvg."""
    _svg_parse(svg)
    return svg


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
    action: Optional[str] = None,
) -> DiagramRenderError:
    """Build an actionable error for a renderer request after startup."""
    detail = str(cause).strip() or "the renderer request failed"
    if error is not None:
        detail = "%s: %s" % (detail, _summarize_exception(error))
    if action is not None:
        recovery = action
    elif request_error:
        recovery = "check the DiagramData shape and renderer options, then retry"
    elif _is_development_checkout():
        recovery = (
            "inspect the renderer output; if generated assets are stale, run "
            "`make build_assets` and retry"
        )
    else:
        recovery = "report this full error at %s" % _ASSET_ISSUE_URL
    return DiagramRenderError(
        "pyfcstm diagram render failure for %s: %s. %s" % (name, detail, recovery)
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
    elif name == "resvg.wasm" and not _valid_wasm_envelope(data):
        raise _asset_failure(
            name, "the resource is not a valid WebAssembly binary envelope"
        )
    elif name.startswith("fonts/") and not _valid_opentype(data):
        raise _asset_failure(
            name,
            "the resource failed OpenType table, bounds, or checksum validation",
        )
    return data


def _read_wasm_uleb(data: bytes, offset: int) -> Optional[Tuple[int, int]]:
    """Read one bounded unsigned LEB128 value from a WASM section stream."""
    value = 0
    shift = 0
    while offset < len(data) and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    return None


# Known non-custom section ids in the order the WebAssembly binary format
# requires them to appear. DataCount (12) is placed between Element (9) and
# Code (10), so the stream position is not the same as the numeric id.
_WASM_SECTION_POSITIONS = {
    section_id: position
    for position, section_id in enumerate(
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 10, 11), start=1
    )
}


def _valid_wasm_envelope(data: bytes) -> bool:
    """Check the ordered section envelope before a browser compiles WASM."""
    if len(data) < 8 or data[:4] != b"\x00asm" or data[4:8] != b"\x01\x00\x00\x00":
        return False
    offset = 8
    last_position = 0
    seen = set()
    required = {1, 3, 7, 10}
    while offset < len(data):
        section_id = data[offset]
        offset += 1
        parsed = _read_wasm_uleb(data, offset)
        if parsed is None:
            return False
        section_size, offset = parsed
        end = offset + section_size
        if end > len(data):
            return False
        if section_id == 0:
            offset = end
            continue
        position = _WASM_SECTION_POSITIONS.get(section_id)
        if position is None or position <= last_position:
            return False
        seen.add(section_id)
        last_position = position
        if section_id == 10 and section_size == 0:
            return False
        offset = end
    return offset == len(data) and required.issubset(seen)


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
    total_checksum = (
        sum(word[0] for word in struct.iter_unpack(">I", data)) & 0xFFFFFFFF
    )
    return total_checksum == 0xB1B0AFBA


#: Largest accepted raster scale.  Above this the caller has almost certainly
#: mistaken a scale for a pixel width, so it is an argument error rather than a
#: size outcome.
MAX_EXPORT_SCALE = 4
#: Largest accepted scaled edge, matching the widest dimension mainstream image
#: decoders and PDF viewers handle without special configuration.
MAX_EXPORT_EDGE_PX = 16384
#: Largest accepted scaled pixel count, which bounds the rasteriser's working
#: set independently of how the pixels are distributed between the two edges.
MAX_EXPORT_PIXELS = 16777216
#: Largest accepted uncompressed RGBA buffer, four bytes per pixel.
MAX_EXPORT_RAW_RGBA_BYTES = 67108864
#: Largest accepted encoded PNG.
MAX_EXPORT_PNG_BYTES = 33554432
#: Largest accepted encoded text or PDF export.
MAX_EXPORT_TEXT_BYTES = 67108864


def check_export_scale(scale: Any) -> float:
    """
    Validate a raster scale against the documented accepted range.

    :param scale: Requested output scale.
    :type scale: float
    :return: The scale as a float.
    :rtype: float
    :raises ValueError: If ``scale`` is not finite and positive, or exceeds
        :data:`MAX_EXPORT_SCALE`.

    Example::

        >>> check_export_scale(2)
        2.0
        >>> check_export_scale(5)
        Traceback (most recent call last):
        ...
        ValueError: scale must be at most 4; got 5
    """
    if isinstance(scale, bool):
        # ``float(True)`` is 1.0, so a bool would otherwise be accepted as a
        # scale of one. A caller passing a flag here has made a mistake that
        # silently producing unscaled output would hide.
        raise ValueError("scale must be a finite positive number; got %r" % (scale,))
    try:
        numeric = float(scale)
    except (TypeError, ValueError) as err:
        # TypeError: a non-numeric object such as a string or None.
        # ValueError: a string that does not parse as a number.
        raise ValueError("scale must be a finite positive number") from err
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise ValueError("scale must be a finite positive number; got %r" % (scale,))
    if numeric <= 0:
        raise ValueError("scale must be positive; got %r" % (scale,))
    if numeric > MAX_EXPORT_SCALE:
        raise ValueError("scale must be at most %d; got %s" % (MAX_EXPORT_SCALE, scale))
    return numeric


def check_export_size(width: float, height: float, scale: float) -> Tuple[int, int]:
    """
    Refuse an oversized export before any pixels are allocated.

    The multiplications happen here, in Python, so an impossible request is
    named and rejected rather than being handed to the rasteriser to fail on --
    running out of memory is not input validation, and it cannot tell the caller
    which scale would have fitted.

    :param width: Unscaled canvas width in user units.
    :type width: float
    :param height: Unscaled canvas height in user units.
    :type height: float
    :param scale: Validated output scale.
    :type scale: float
    :return: The scaled integer width and height.
    :rtype: tuple[int, int]
    :raises ValueError: If either unscaled dimension is not finite and positive.
    :raises DiagramRenderLimitError: If the scaled edges, pixel count, or raw
        RGBA buffer would exceed their documented limits.

    Example::

        >>> check_export_size(100, 50, 2)
        (200, 100)
        >>> check_export_size(10000, 10000, 4)
        Traceback (most recent call last):
        ...
        pyfcstm.diagram.engine.DiagramRenderLimitError: ...
    """
    for name, value in (("width", width), ("height", height)):
        numeric = float(value)
        if numeric != numeric or numeric in (float("inf"), float("-inf")):
            raise ValueError("canvas %s must be finite; got %r" % (name, value))
        if numeric <= 0:
            raise ValueError("canvas %s must be positive; got %r" % (name, value))
    scaled_width = int(math.ceil(float(width) * scale))
    scaled_height = int(math.ceil(float(height) * scale))
    origin = "%gx%g at scale %g gives %dx%d" % (
        width,
        height,
        scale,
        scaled_width,
        scaled_height,
    )
    advice = "lower scale and retry"
    for name, value in (("width", scaled_width), ("height", scaled_height)):
        if value > MAX_EXPORT_EDGE_PX:
            raise DiagramRenderLimitError(
                "%s, whose %s exceeds the %dpx limit; %s"
                % (origin, name, MAX_EXPORT_EDGE_PX, advice),
                limit_name="edge",
            )
    pixels = scaled_width * scaled_height
    if pixels > MAX_EXPORT_PIXELS:
        raise DiagramRenderLimitError(
            "%s, which is %d pixels and exceeds the %d limit; %s"
            % (origin, pixels, MAX_EXPORT_PIXELS, advice),
            limit_name="pixels",
        )
    raw_bytes = pixels * 4
    if raw_bytes > MAX_EXPORT_RAW_RGBA_BYTES:
        raise DiagramRenderLimitError(
            "%s, whose raw RGBA buffer is %d bytes and exceeds the %d limit; %s"
            % (origin, raw_bytes, MAX_EXPORT_RAW_RGBA_BYTES, advice),
            limit_name="raw_rgba",
        )
    return scaled_width, scaled_height


def check_export_bytes(data: bytes, kind: str, limit: int) -> bytes:
    """
    Refuse an encoded export that exceeds its documented size limit.

    The check happens before the bytes reach a cache, a decoder, or a file, so an
    oversized export cannot be written out and then rejected.

    :param data: Encoded export payload.
    :type data: bytes
    :param kind: Short name of the payload, used in the message.
    :type kind: str
    :param limit: Maximum accepted length in bytes.
    :type limit: int
    :return: The payload unchanged.
    :rtype: bytes
    :raises DiagramRenderLimitError: If ``data`` is longer than ``limit``.

    Example::

        >>> check_export_bytes(b"ab", "PNG", 4)
        b'ab'
    """
    if len(data) > limit:
        raise DiagramRenderLimitError(
            "encoded %s output is %d bytes and exceeds the %d limit; "
            "lower scale or reduce the diagram and retry" % (kind, len(data), limit),
            limit_name=kind.lower(),
        )
    return data


def _png_dimensions(data: bytes) -> Tuple[int, int]:
    """Check the PNG envelope and return its declared RGBA dimensions."""
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        raise ValueError("PNG output lacks the PNG signature")
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError("PNG output has no IHDR header")
    header_length = struct.unpack(">I", data[8:12])[0]
    if header_length != 13:
        raise ValueError("PNG output has an invalid IHDR length")
    try:
        width, height, depth, color_type, compression, filtering, interlace = (
            struct.unpack(">IIBBBBB", data[16:29])
        )
    except struct.error as err:
        # struct.error: the fixed IHDR payload is truncated.
        raise ValueError("PNG output has a truncated IHDR header") from err
    if not width or not height:
        raise ValueError("PNG output has non-positive dimensions")
    if (
        depth != 8
        or color_type != 6
        or compression != 0
        or filtering != 0
        or interlace != 0
    ):
        raise ValueError("PNG output violates the RGBA8 size contract")
    # Require IEND to be the final zero-length PNG chunk.  A substring check
    # could accept a truncated stream whose compressed IDAT bytes contain the
    # four-byte text ``IEND`` by coincidence.
    if len(data) < 45 or data[-12:-8] != b"\x00\x00\x00\x00" or data[-8:-4] != b"IEND":
        raise ValueError("PNG output is missing IEND")
    return width, height


class DiagramAssetEngine:
    """
    Drive the shared ES2017 renderer and resvg bridge in MiniRacer.

    :param timeout: Optional maximum seconds for one ELK/render polling
        operation. ``None`` leaves the operation uncapped, defaults to
        ``None``.
    :type timeout: float, optional
    :param max_memory: Optional V8 heap limit in bytes applied to each
        JavaScript evaluation, defaults to ``None``.
    :type max_memory: int, optional

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { state A; [*] -> A; }')
        >>> engine = DiagramAssetEngine()
        >>> svg = engine.render_svg({"diagram": model.diagram().to_dict()})
        >>> svg.startswith("<svg")
        True
    """

    def __init__(
        self, timeout: Optional[float] = None, max_memory: Optional[int] = None
    ) -> None:
        numeric_timeout = None if timeout is None else float(timeout)
        if numeric_timeout is not None and (
            not math.isfinite(numeric_timeout) or numeric_timeout <= 0
        ):
            raise ValueError("timeout must be None or a finite positive number")
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
        modern_installed = self._distribution_installed("mini-racer")
        legacy_installed = self._distribution_installed("py-mini-racer")
        if modern_installed and legacy_installed:
            modern_version = self._distribution_version("mini-racer") or "unknown"
            legacy_version = self._distribution_version("py-mini-racer") or "unknown"
            raise DiagramEngineConflictError(
                "mini-racer %s and py-mini-racer %s are installed together; "
                "install exactly one runtime for this Python version"
                % (modern_version, legacy_version)
            )
        if not modern_installed and not legacy_installed:
            raise DiagramUnavailableError(
                "no supported MiniRacer distribution is installed; run "
                "`pip install pyfcstm[viz]` to add the headless rendering runtime"
            )
        selected = "mini-racer" if modern_installed else "py-mini-racer"
        selected_version = self._distribution_version(selected) or "unknown"
        try:
            from py_mini_racer import MiniRacer
        except ImportError:
            # Legacy py-mini-racer exports MiniRacer from this submodule.
            try:
                from py_mini_racer.py_mini_racer import MiniRacer
            except (ImportError, OSError) as legacy_error:
                # ImportError/OSError: the selected distribution is installed
                # but its Python export or native ABI cannot be loaded.
                raise DiagramEngineLoadError(
                    "%s %s is installed but could not be loaded: %s"
                    % (selected, selected_version, legacy_error)
                ) from legacy_error
        except OSError as top_level_error:
            # OSError: the selected native MiniRacer extension failed to load.
            raise DiagramEngineLoadError(
                "%s %s is installed but could not be loaded: %s"
                % (selected, selected_version, top_level_error)
            ) from top_level_error
        try:
            from py_mini_racer import (
                JSEvalException,
                JSOOMException,
                JSParseException,
                JSTimeoutException,
            )
        except (ImportError, OSError):
            # ImportError/OSError: py-mini-racer 0.6 keeps these exception
            # classes in its legacy module; modern mini-racer exports them at
            # package top level, but a native import can still fail.
            try:
                from py_mini_racer.py_mini_racer import (
                    JSEvalException,
                    JSOOMException,
                    JSParseException,
                    JSTimeoutException,
                )
            except (ImportError, OSError) as legacy_error:
                # ImportError/OSError: the selected distribution lacks the
                # expected exception exports or native module dependency.
                raise DiagramEngineLoadError(
                    "%s %s exception exports could not be loaded: %s"
                    % (selected, selected_version, legacy_error)
                ) from legacy_error
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
        if numeric_timeout is not None and (
            not math.isfinite(numeric_timeout) or numeric_timeout <= 0
        ):
            raise ValueError("timeout must be None or a finite positive number")
        self._ensure_context()
        try:
            kwargs = {}
            if self.max_memory is not None:
                kwargs["max_memory"] = self.max_memory
            if numeric_timeout is not None:
                if self._timeout_uses_seconds:
                    kwargs["timeout_sec"] = numeric_timeout
                else:
                    # py-mini-racer 0.6 accepts milliseconds and does not
                    # understand the modern ``timeout_sec`` keyword.
                    kwargs["timeout"] = max(1, int(math.ceil(numeric_timeout * 1000.0)))
            return self._context.eval(source, **kwargs)
        except Exception as err:
            # JSTimeoutException/JSOOMException are the only expected native
            # interruption failures; every other exception must propagate.
            if not isinstance(err, self._interrupt_errors):
                raise
            self._discard_context()
            raise _DiagramEvaluationInterruptedError(
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
        self._eval_asset("asset-loader", _ASSET_LOADER_BOOTSTRAP)
        self._load_javascript_asset("host-shim.js", host_shim)
        self._eval_asset(
            "host-shim.js",
            "globalThis.__pyfcstm_embedded_host = true;",
        )
        self._load_javascript_asset("renderer.js", renderer)
        self._eval_asset(
            "asset-loader",
            "delete globalThis.__pyfcstm_load_asset;",
        )
        self._eval_asset(
            "resvg-bridge.js",
            "globalThis.__pyfcstm_bind_context_token(%s);"
            % json.dumps(self._context_token),
        )

    def _load_javascript_asset(self, name: str, source: str) -> None:
        """Evaluate packaged JavaScript without crossing native parse errors."""
        result = str(
            self._eval_asset(
                name,
                "globalThis.__pyfcstm_load_asset(%s)" % json.dumps(source),
            )
        )
        if result == "ok":
            return
        self._discard_context()
        raise _asset_failure(
            name,
            "the JavaScript resource could not be evaluated",
            ValueError(result),
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
        except _DiagramEvaluationInterruptedError as err:
            # Native interruption: request failures use the render taxonomy;
            # startup and asset failures retain the asset taxonomy.
            if request:
                raise _render_failure(
                    name,
                    "the renderer request exceeded its time or memory limit",
                    err,
                    request_error=True,
                ) from err
            raise
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
            if request:
                self._discard_context()
                raise _render_failure(
                    "renderer.js",
                    "the renderer returned invalid job status data",
                    err,
                    request_error=True,
                ) from err
            self._discard_context()
            raise _asset_failure(
                "renderer.js", "the renderer returned invalid job status data", err
            ) from err
        if not isinstance(status, dict):
            if request:
                self._discard_context()
                raise _render_failure(
                    "renderer.js",
                    "the renderer returned a non-object job status",
                    request_error=True,
                )
            self._discard_context()
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

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { state A; [*] -> A; }')
            >>> request = {"diagram": model.diagram().to_dict()}
            >>> engine = DiagramAssetEngine()
            >>> svg = engine.render_svg(request)
            >>> svg.startswith("<svg")
            True
        """
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON-compatible mapping")
        request_id = "pyfcstm-%d" % time.monotonic_ns()
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        try:
            serialized_request = json.dumps(
                request, ensure_ascii=False, allow_nan=False
            )
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
        while deadline is None or time.monotonic() < deadline:
            remaining = (
                None if deadline is None else max(0.001, deadline - time.monotonic())
            )
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
                    return _check_canonical_svg(svg)
                except DiagramAssetError as err:
                    self._discard_context()
                    raise _render_failure(
                        "renderer.js",
                        "the renderer returned malformed SVG output",
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
        raise _render_failure(
            "renderer.js",
            "diagram renderer timed out after %.1fs" % self.timeout,
            action="retry the DiagramData request; the interrupted renderer context was discarded",
        )

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
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        if not self._resvg_ready:
            self._eval_asset(
                "resvg.wasm",
                "__pyfcstm_resvg_init(%s)" % json.dumps(wasm),
            )
        while deadline is None or time.monotonic() < deadline:
            remaining = (
                None if deadline is None else max(0.001, deadline - time.monotonic())
            )
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

    def _canonical_input(self, request: Any) -> str:
        """Resolve DiagramData or compatibility SVG text for the bridge."""
        if isinstance(request, str):
            return _check_canonical_svg(request)
        if isinstance(request, dict):
            return self.render_svg(request)
        raise ValueError("render_png/expand_svg require DiagramData or SVG text")

    def render_png(
        self, request: Union[str, Dict[str, Any]], scale: float = 1.0
    ) -> bytes:
        """
        Rasterize a DiagramData request with the pinned resvg WASM backend.

        :param request: DiagramData request or canonical SVG text emitted by
            :meth:`render_svg`.  String input is a compatibility bridge, not a
            general-purpose SVG sanitizer.
        :type request: str or dict
        :param scale: Finite positive raster scale, defaults to ``1.0``.
        :type scale: float, optional
        :return: PNG bytes.
        :rtype: bytes
        :raises ValueError: If ``scale`` is not finite and positive.
        :raises DiagramAssetError: If resvg reports a rendering failure.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { state A; [*] -> A; }')
            >>> request = {"diagram": model.diagram().to_dict()}
            >>> engine = DiagramAssetEngine()
            >>> png = engine.render_png(request, scale=2.0)
            >>> png.startswith(b"\\x89PNG")
            True
        """
        if isinstance(scale, bool):
            raise ValueError("scale must be a finite positive number")
        if scale is None:
            raise ValueError("scale must be a finite positive number")
        try:
            numeric_scale = float(scale)
        except (TypeError, ValueError) as err:
            # TypeError/ValueError: the caller supplied a non-numeric scale.
            raise ValueError("scale must be a finite positive number") from err
        if not math.isfinite(numeric_scale) or numeric_scale <= 0:
            raise ValueError("scale must be a finite positive number")
        svg = self._canonical_input(request)
        self._ensure_resvg(self._locale_from_svg(svg))
        encoded = self._eval_asset(
            "resvg.wasm",
            "__pyfcstm_resvg_png(%s, %s)"
            % (json.dumps(svg), json.dumps(numeric_scale)),
            request=True,
        )
        encoded_text = str(encoded)
        try:
            result = base64.b64decode(encoded_text, validate=True)
        except (ValueError, binascii.Error) as err:
            # ValueError/binascii.Error: the WASM bridge returned malformed
            # base64 instead of a PNG payload.
            raise _render_failure(
                "resvg.wasm", "the renderer returned invalid PNG data", err
            ) from err
        try:
            _png_dimensions(result)
        except (TypeError, ValueError, struct.error, OverflowError) as err:
            # TypeError/ValueError: the WASM bridge returned malformed PNG
            # data; struct.error/OverflowError: the fixed IHDR is truncated
            # or its checked arithmetic is invalid.
            raise _render_failure(
                "resvg.wasm", "the renderer returned invalid PNG data", err
            ) from err
        return result

    def expand_svg(self, request: Union[str, Dict[str, Any]]) -> str:
        """
        Expand a DiagramData request into resvg's normalized vector SVG.

        :param request: DiagramData request or canonical SVG text emitted by
            :meth:`render_svg`.  String input is a compatibility bridge, not a
            general-purpose SVG sanitizer.
        :type request: str or dict
        :return: Normalized vector SVG text.
        :rtype: str
        :raises DiagramAssetError: If resvg returns malformed SVG output.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { state A; [*] -> A; }')
            >>> request = {"diagram": model.diagram().to_dict()}
            >>> engine = DiagramAssetEngine()
            >>> expanded = engine.expand_svg(request)
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
                request=True,
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
            return _check_expanded_svg(expanded)
        except DiagramAssetError as err:
            raise _render_failure(
                "resvg.wasm",
                "the renderer returned malformed SVG output",
                err,
            ) from err

    @staticmethod
    def _locale_from_svg(svg: str) -> str:
        """Infer the embedded CJK face from an SVG font-family attribute."""
        match = _CJK_LOCALE_PATTERN.search(str(svg))
        return match.group(1).lower() if match else "sc"
