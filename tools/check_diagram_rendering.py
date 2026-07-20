"""Run the offline diagram arrow, parity, CJK, and reference gates.

This maintenance command deliberately lives outside pytest.  The checked-in
corpus contains serialized DiagramData, so this command can exercise the
production Python engine without importing Node, jsfcstm tests, or repository
fixtures from the other unit-test tree.
"""

import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.diagram import DiagramAssetEngine  # noqa: E402
from pyfcstm.diagram.engine import (  # noqa: E402
    _MAX_RENDER_DIMENSION,
    _MAX_RENDER_PIXELS,
    _MAX_RENDER_PNG_BYTES,
    _MAX_RENDER_RGBA_BYTES,
)


DEFAULT_CORPORA = (
    ROOT / "tools" / "diagram_assets" / "corpus" / "canonical-arrows.json",
    ROOT / "tools" / "diagram_assets" / "corpus" / "shared-layouts.json",
)

# These hashes identify the PR-A custom 0.37 baseline used for an official
# parity comparison.  A reference captured from the official package must
# never be accepted as a custom baseline, even if its pixels happen to match.
_CUSTOM_REFERENCE_FILES = {
    "tools/diagram_assets/asset-lock.json": "9147139082850957bd24b7845dfe9ea460722eeff20a7e1af84c971156dbf1bc",
    "tools/diagram_assets/resvg-bridge.js": "7620bd2ee02d63baa665946c8d5b8c741f49cfdf54c60fad0afdf0689784ef1d",
    "pyfcstm/diagram/assets/renderer.js": "9e934e0cdf63390c0738fb544014e1eaf01747a24011568f92fc6cdf92dd6d46",
    "pyfcstm/diagram/assets/resvg-binding.js": "435b67b9e703c1b33600e4696ee19817c402d5055136b782558ba719a3b227ae",
    "pyfcstm/diagram/assets/resvg.wasm": "65a71d371905968c3747f9c57a86fd803e27b9dc081e7145350b9529bc803248",
}
SVG_NS = "http://www.w3.org/2000/svg"
PATH_RE = re.compile(r"([ML])\s*(-?[0-9]+(?:\.[0-9]+)?)\s*,\s*(-?[0-9]+(?:\.[0-9]+)?)")
CLIP_ID_RE = re.compile(r'id="((?:clip-path|clipPath)[^"]+)"')

# The strict SVG contract is intentionally maintenance-only.  Production
# rendering performs bounded XML/canvas checks; this oracle catches renderer
# drift, unsafe references, and accidental text/marker retention in CI.
_STRICT_SVG_INPUT_ELEMENTS = {
    "svg", "defs", "marker", "filter", "feGaussianBlur", "feOffset",
    "feComponentTransfer", "feFuncA", "feFuncR", "feFuncG", "feFuncB",
    "feMerge", "feMergeNode", "g", "rect", "path", "line", "circle", "text",
}
_STRICT_SVG_OUTPUT_ELEMENTS = {
    "svg", "defs", "filter", "feGaussianBlur", "feOffset",
    "feComponentTransfer", "feFuncA", "feFuncR", "feFuncG", "feFuncB",
    "feMerge", "feMergeNode", "clipPath", "g", "path",
}
_STRICT_SVG_INPUT_ATTRIBUTES = {
    "svg": {"viewBox", "width", "height", "font-family", "font-size",
            "data-fcstm-canvas", "data-fcstm-direction", "data-fcstm-palette", "data-fcstm-mode"},
    "defs": set(),
    "marker": {"id", "viewBox", "refX", "refY", "markerWidth", "markerHeight", "orient", "markerUnits"},
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
    "g": {"data-fcstm-kind", "data-fcstm-id", "data-fcstm-variant", "data-fcstm-pseudo",
          "data-fcstm-composite", "data-fcstm-collapsed", "data-fcstm-range-start-line",
          "data-fcstm-range-start-character", "data-fcstm-range-end-line", "data-fcstm-range-end-character"},
    "rect": {"class", "x", "y", "width", "height", "rx", "ry", "fill", "stroke",
             "stroke-width", "stroke-dasharray", "filter", "pointer-events"},
    "path": {"d", "fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-linecap",
             "stroke-linejoin", "stroke-opacity", "marker-end", "data-fcstm-kind", "data-fcstm-id",
             "data-fcstm-range-start-line", "data-fcstm-range-start-character", "data-fcstm-range-end-line",
             "data-fcstm-range-end-character"},
    "line": {"x1", "y1", "x2", "y2", "stroke", "stroke-opacity", "stroke-width"},
    "circle": {"cx", "cy", "r", "fill", "stroke", "stroke-width", "data-fcstm-kind", "data-fcstm-id"},
    "text": {"x", "y", "fill", "font-family", "font-size", "font-weight", "text-anchor",
             "letter-spacing", "paint-order", "stroke", "stroke-width", "stroke-linejoin"},
}
_STRICT_SVG_OUTPUT_ATTRIBUTES = {
    "svg": {"width", "height", "viewBox"},
    "defs": set(),
    "filter": {"id", "x", "y", "width", "height"},
    "feGaussianBlur": {"color-interpolation-filters", "in", "stdDeviation", "result"},
    "feOffset": {"color-interpolation-filters", "in", "dx", "dy", "result"},
    "feComponentTransfer": {"color-interpolation-filters", "in", "result"},
    "feFuncA": {"type", "slope", "intercept"}, "feFuncR": {"type"},
    "feFuncG": {"type"}, "feFuncB": {"type"},
    "feMerge": {"color-interpolation-filters", "result"}, "feMergeNode": {"in"},
    "clipPath": {"id"}, "g": {"clip-path", "filter", "transform"},
    "path": {"d", "fill", "fill-opacity", "paint-order", "stroke", "stroke-dasharray",
             "stroke-linecap", "stroke-linejoin", "stroke-opacity", "stroke-width", "visibility"},
}
_STRICT_URI_RE = re.compile(
    r"(?:javascript|vbscript|data|blob|about|file|https?|ftp|ws|wss|"
    r"chrome|chrome-extension):",
    re.I,
)
_STRICT_URL_RE = re.compile(r"url\(([^)]*)\)", re.I)


def _strict_svg_validate(svg: str, output: bool = False) -> str:
    """Validate the closed renderer SVG dialect for maintenance gates."""
    if not isinstance(svg, str) or len(svg.encode("utf-8")) > 16 * 1024 * 1024:
        raise ValueError("closed SVG dialect rejected non-text or oversized SVG")
    if any(token in svg for token in ("<!DOCTYPE", "<!ENTITY", "<?", "<!--", "<![")):
        raise ValueError("closed SVG dialect rejected XML declarations or entities")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as err:
        raise ValueError("closed SVG dialect rejected malformed XML") from err
    prefix = "{%s}" % SVG_NS
    allowed_elements = _STRICT_SVG_OUTPUT_ELEMENTS if output else _STRICT_SVG_INPUT_ELEMENTS
    allowed_attrs = _STRICT_SVG_OUTPUT_ATTRIBUTES if output else _STRICT_SVG_INPUT_ATTRIBUTES
    if root.tag != prefix + "svg":
        raise ValueError("closed SVG dialect requires an SVG root element")
    ids = set()
    references = []
    pending = [(root, 1)]
    count = 0
    while pending:
        element, depth = pending.pop()
        count += 1
        if depth > 256 or count > 100000:
            raise ValueError("closed SVG dialect exceeded bounded tree limits")
        if not isinstance(element.tag, str) or not element.tag.startswith(prefix):
            raise ValueError("closed SVG dialect rejected a non-SVG namespace")
        tag = element.tag[len(prefix):]
        if tag not in allowed_elements:
            raise ValueError("closed SVG dialect rejected element: %s" % tag)
        for name, value in element.attrib.items():
            if name.startswith("{") or name not in allowed_attrs.get(tag, set()):
                raise ValueError("closed SVG dialect rejected attribute %s" % name)
            if name.lower().startswith("on") or name in {"href", "xlink:href", "style"}:
                raise ValueError("closed SVG dialect rejected executable attribute")
            if _STRICT_URI_RE.search(value):
                raise ValueError("closed SVG dialect rejected an external URL")
            for reference in _STRICT_URL_RE.findall(value):
                reference = reference.strip().strip("\"'")
                if not reference.startswith("#") or len(reference) == 1:
                    raise ValueError("closed SVG dialect rejected a non-local URL reference")
                references.append(reference[1:])
            if name == "id":
                if not value or value in ids:
                    raise ValueError("closed SVG dialect rejected duplicate or empty id")
                ids.add(value)
        if element.text and ((output and element.text.strip()) or not output and False):
            raise ValueError("closed SVG dialect rejected residual text nodes")
        if element.tail and element.tail.strip():
            raise ValueError("closed SVG dialect rejected residual tail text")
        pending.extend((child, depth + 1) for child in reversed(list(element)))
    if any(reference not in ids for reference in references):
        raise ValueError("closed SVG dialect rejected a broken local reference")
    if output and any((element.tag[len(prefix):] if isinstance(element.tag, str) and element.tag.startswith(prefix) else "") in {"text", "marker"} for element in root.iter()):
        raise ValueError("closed SVG dialect rejected residual text or marker elements")
    if not output:
        markers = [element for element in root.iter() if isinstance(element.tag, str) and element.tag == prefix + "marker"]
        if markers:
            if len(markers) != 1 or markers[0].attrib.get("orient") != "auto" or markers[0].attrib.get("refX") != "10":
                raise ValueError("closed SVG dialect rejected marker endpoint contract")
    return svg


def _sha256(data: bytes) -> str:
    """Return the SHA-256 digest for one evidence file."""
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    """Read one JSON maintenance input."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        # OSError: the corpus cannot be read; UnicodeDecodeError/ValueError:
        # the checked-in maintenance oracle is not valid UTF-8 JSON.
        raise ValueError("cannot read diagram corpus: %s" % path) from err
    if not isinstance(value, dict):
        raise ValueError("diagram corpus root must be an object: %s" % path)
    return value


def request_for_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Return the serialized DiagramData request for one corpus case."""
    request = case.get("request")
    if not isinstance(request, dict):
        raise ValueError("corpus case %s lacks serialized DiagramData" % case.get("id"))
    diagram = request.get("diagram")
    if not isinstance(diagram, dict):
        raise ValueError("corpus case %s lacks a DiagramData object" % case.get("id"))
    summary = diagram.get("summary")
    if not isinstance(summary, dict) or int(summary.get("transitions", -1)) != int(
        case.get("arrows", -2)
    ):
        raise ValueError(
            "corpus case %s has inconsistent transition count" % case.get("id")
        )
    options = request.get("options")
    if not isinstance(options, dict) or options.get("direction") not in {"LR", "TB"}:
        raise ValueError("corpus case %s has invalid layout direction" % case.get("id"))
    return request


def _walk_states(state: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield a DiagramData state and every descendant."""
    yield state
    for child in state.get("children", ()):
        if isinstance(child, dict):
            for nested in _walk_states(child):
                yield nested


def _walk_transitions(state: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield transitions owned by a state and every descendant."""
    for transition in state.get("transitions", ()):
        if isinstance(transition, dict):
            yield transition
    for child in state.get("children", ()):
        if isinstance(child, dict):
            for nested in _walk_transitions(child):
                yield nested


def load_cases(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    """Load and validate corpus identities, provenance, and counts."""
    cases: List[Dict[str, Any]] = []
    seen = set()
    for path in paths:
        payload = _read_json(path)
        if not isinstance(payload.get("cases"), list):
            raise ValueError("diagram corpus lacks a cases list: %s" % path)
        for case in payload["cases"]:
            if not isinstance(case, dict) or not case.get("id"):
                raise ValueError("diagram corpus contains an invalid case: %s" % path)
            case_id = str(case["id"])
            if case_id in seen:
                raise ValueError("diagram corpus contains duplicate case: %s" % case_id)
            seen.add(case_id)
            source_hash = str(case.get("sourceSha256", ""))
            if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                raise ValueError("corpus case %s has no source SHA-256" % case_id)
            request = request_for_case(case)
            state = request["diagram"].get("rootState")
            if not isinstance(state, dict):
                raise ValueError("corpus case %s lacks rootState" % case_id)
            transition_count = sum(1 for _ in _walk_transitions(state))
            if transition_count != int(case["arrows"]):
                raise ValueError(
                    "corpus case %s declares %d arrows but stores %d transitions"
                    % (case_id, int(case["arrows"]), transition_count)
                )
            item = dict(case)
            item["corpus"] = path.name
            item["corpusSha256"] = _sha256(path.read_bytes())
            cases.append(item)
    if not cases:
        raise ValueError("diagram corpus is empty")
    return cases


def _points(path_data: str) -> List[Tuple[float, float]]:
    """Extract line/move points used by a transition path."""
    return [(float(x), float(y)) for _command, x, y in PATH_RE.findall(path_data)]


def _direction(points: List[Tuple[float, float]]) -> str:
    """Classify the final terminal tangent direction."""
    if len(points) < 2:
        raise ValueError("transition path has no terminal segment")
    start_x, start_y = points[-2]
    end_x, end_y = points[-1]
    dx = end_x - start_x
    dy = end_y - start_y
    if abs(dx) >= abs(dy):
        return "right" if dx >= 0 else "left"
    return "down" if dy >= 0 else "up"


def _border_distance(
    point: Tuple[float, float], rect: Tuple[float, float, float, float]
) -> float:
    """Return distance from a point to a rectangle perimeter."""
    x, y = point
    rx, ry, width, height = rect
    inside_x = rx <= x <= rx + width
    inside_y = ry <= y <= ry + height
    if inside_x and inside_y:
        return min(
            abs(x - rx), abs(x - (rx + width)), abs(y - ry), abs(y - (ry + height))
        )
    closest_x = min(max(x, rx), rx + width)
    closest_y = min(max(y, ry), ry + height)
    return math.hypot(x - closest_x, y - closest_y)


def _shape_distance(
    point: Tuple[float, float], shape: Tuple[str, Tuple[float, ...]]
) -> float:
    """Return distance from a point to a rectangular or circular target."""
    kind, values = shape
    if kind == "rect":
        return _border_distance(point, values)  # type: ignore[arg-type]
    cx, cy, radius = values
    return abs(math.hypot(point[0] - cx, point[1] - cy) - radius)


def _normal_cosine(
    previous: Tuple[float, float],
    endpoint: Tuple[float, float],
    shape: Tuple[str, Tuple[float, ...]],
) -> float:
    """Return the terminal tangent dot product with the target normal."""
    if shape[0] == "circle":
        cx, cy, _radius = shape[1]
        normal_x = cx - endpoint[0]
        normal_y = cy - endpoint[1]
        normal_length = math.hypot(normal_x, normal_y)
        if normal_length == 0:
            return -1.0
        normal = (normal_x / normal_length, normal_y / normal_length)
    else:
        rx, ry, width, height = shape[1]
        x, y = endpoint
        distances = (
            (abs(x - rx), (1.0, 0.0)),
            (abs(x - (rx + width)), (-1.0, 0.0)),
            (abs(y - ry), (0.0, 1.0)),
            (abs(y - (ry + height)), (0.0, -1.0)),
        )
        _distance, normal = min(distances, key=lambda item: item[0])
    dx = endpoint[0] - previous[0]
    dy = endpoint[1] - previous[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return -1.0
    return (dx * normal[0] + dy * normal[1]) / length


def _transition_targets(request: Dict[str, Any]) -> Dict[str, str]:
    """Map renderer transition IDs to target state qualified names."""
    root = request["diagram"]["rootState"]
    targets: Dict[str, str] = {}
    for transition in _walk_transitions(root):
        target_path = transition.get("targetStatePath")
        transition_id = transition.get("id")
        if transition.get("targetKind") == "exit":
            source_path = transition.get("sourceStatePath")
            if isinstance(source_path, list) and len(source_path) > 1 and transition_id:
                targets[str(transition_id)] = "__exit__::%s" % ".".join(
                    str(part) for part in source_path[:-1]
                )
        elif isinstance(target_path, list) and target_path and transition_id:
            targets[str(transition_id)] = ".".join(str(part) for part in target_path)
    return targets


def inspect_arrows(
    svg: str, request: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Inspect every transition for direction, border contact, and normality."""
    root = ET.fromstring(svg)
    target_shapes: Dict[str, Tuple[str, Tuple[float, ...]]] = {}
    for group in root.iter("{%s}g" % SVG_NS):
        if group.attrib.get("data-fcstm-kind") not in {"state", "composite-state"}:
            continue
        state_id = group.attrib.get("data-fcstm-id")
        for child in group:
            if child.tag == "{%s}rect" % SVG_NS and "x" in child.attrib and state_id:
                target_shapes[state_id] = (
                    "rect",
                    tuple(
                        round(float(child.attrib[key]), 2)
                        for key in ("x", "y", "width", "height")
                    ),
                )
                break
    for group in root.iter("{%s}g" % SVG_NS):
        if group.attrib.get("data-fcstm-kind") != "pseudo-exit":
            continue
        target_id = group.attrib.get("data-fcstm-id")
        circle = next(
            (child for child in group if child.tag == "{%s}circle" % SVG_NS),
            None,
        )
        if target_id and circle is not None:
            target_shapes[target_id] = (
                "circle",
                (
                    float(circle.attrib["cx"]),
                    float(circle.attrib["cy"]),
                    float(circle.attrib["r"]),
                ),
            )
    target_by_id = _transition_targets(request) if request else {}
    arrows = []
    for path in root.iter("{%s}path" % SVG_NS):
        if path.attrib.get("data-fcstm-kind") != "transition":
            continue
        points = _points(path.attrib.get("d", ""))
        if len(points) < 2:
            raise ValueError("transition path has no usable line points")
        end = points[-1]
        previous = points[-2]
        transition_id = path.attrib.get("data-fcstm-id", "")
        target_id = target_by_id.get(transition_id)
        target_shape = target_shapes.get(target_id or "")
        if target_shape is None and request is None:
            candidates = list(target_shapes.values())
            target_rect = (
                min(candidates, key=lambda shape: _shape_distance(end, shape))
                if candidates
                else None
            )
            target_shape = target_rect
        tip_error = _shape_distance(end, target_shape) if target_shape else float("inf")
        terminal_length = math.hypot(end[0] - previous[0], end[1] - previous[1])
        arrows.append(
            {
                "id": path.attrib.get("data-fcstm-id", ""),
                "target": target_id,
                "targetShape": target_shape[0] if target_shape else None,
                "direction": _direction(points),
                "tipError": tip_error,
                "terminalLength": terminal_length,
                "normalCosine": (
                    _normal_cosine(previous, end, target_shape)
                    if target_shape
                    else None
                ),
            }
        )
    return arrows


def _png_ink_bbox(data: bytes) -> Tuple[int, int, Tuple[int, int, int, int]]:
    """Decode a strict RGBA PNG and return its canvas and ink bounds.

    This parser is intentionally independent from the production envelope
    checker: the maintenance parity gate validates the complete PNG grammar,
    scanlines, and visible ink without importing a production decoder.
    """
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("PNG output lacks the PNG signature")
    if len(data) > _MAX_RENDER_PNG_BYTES:
        raise ValueError("PNG output exceeds the bounded byte limit")
    position = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    saw_ihdr = False
    saw_idat = False
    idat_closed = False
    saw_iend = False
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError("PNG output has a truncated chunk header")
        chunk_start = position
        length = struct.unpack(">I", data[position : position + 4])[0]
        end = position + 12 + length
        if end > len(data):
            raise ValueError("PNG output has a truncated chunk")
        kind = data[position + 4 : position + 8]
        if len(kind) != 4 or kind not in {b"IHDR", b"IDAT", b"IEND"}:
            raise ValueError("PNG output contains an unsupported chunk")
        payload = data[position + 8 : position + 8 + length]
        checksum = struct.unpack(">I", data[position + 8 + length : end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != checksum:
            raise ValueError("PNG output contains an invalid chunk checksum")
        position = end
        if kind == b"IHDR":
            if saw_ihdr or chunk_start != 8:
                raise ValueError("PNG output has duplicate or misplaced IHDR")
            if len(payload) != 13:
                raise ValueError("PNG output has an invalid IHDR")
            width, height, bit_depth, color_type, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", payload)
            )
            if (bit_depth, color_type, compression, filtering, interlace) != (
                8,
                6,
                0,
                0,
                0,
            ):
                raise ValueError("PNG output is not non-interlaced RGBA8")
            if not width or not height:
                raise ValueError("PNG output has non-positive dimensions")
            if (
                width > _MAX_RENDER_DIMENSION
                or height > _MAX_RENDER_DIMENSION
                or width * height > _MAX_RENDER_PIXELS
                or width * height * 4 > _MAX_RENDER_RGBA_BYTES
            ):
                raise ValueError("PNG output exceeds the bounded dimension limit")
            saw_ihdr = True
        elif kind == b"IDAT":
            if not saw_ihdr:
                raise ValueError("PNG output has a non-IHDR first chunk")
            if idat_closed:
                raise ValueError("PNG output has non-contiguous IDAT chunks")
            compressed.extend(payload)
            saw_idat = True
        elif kind == b"IEND":
            if not saw_ihdr or not saw_idat or length != 0:
                raise ValueError("PNG output has an invalid IEND")
            saw_iend = True
            if position != len(data):
                raise ValueError("PNG output has trailing bytes after IEND")
            break
        if kind != b"IDAT" and saw_idat:
            idat_closed = True
    if not saw_iend or not saw_ihdr or not saw_idat or width is None or height is None:
        raise ValueError("PNG output is missing IHDR or IEND")
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as err:
        # zlib.error: IDAT payload is not a valid compressed scanline stream.
        raise ValueError("PNG output has invalid compressed scanlines") from err
    if len(raw) > _MAX_RENDER_RGBA_BYTES:
        raise ValueError("PNG output has oversized decoded scanlines")
    stride = width * 4
    if len(raw) != (stride + 1) * height:
        raise ValueError("PNG output has an invalid scanline length")
    previous = bytearray(stride)
    points = []
    offset = 0
    for y in range(height):
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


def _self_check_png_parser() -> None:
    """Exercise the independent strict PNG oracle with valid and invalid data."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", checksum)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    signature = b"\x89PNG\r\n\x1a\n"
    image = chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff"))
    valid = signature + chunk(b"IHDR", header) + image + chunk(b"IEND", b"")
    if _png_ink_bbox(valid)[:2] != (1, 1):
        raise AssertionError("strict parity PNG parser rejected a valid RGBA image")
    invalid_cases = (
        signature + chunk(b"IDAT", b"") + chunk(b"IHDR", header) + chunk(b"IEND", b""),
        signature
        + chunk(b"IHDR", header)
        + chunk(b"IHDR", header)
        + image
        + chunk(b"IEND", b""),
        signature + chunk(b"IHDR", header) + image + chunk(b"IEND", b"x"),
        valid + image,
        signature
        + chunk(b"IHDR", header)
        + image
        + chunk(b"tEXt", b"x")
        + image
        + chunk(b"IEND", b""),
        signature
        + chunk(b"IHDR", header)
        + image[:-4]
        + struct.pack(">I", (struct.unpack(">I", image[-4:])[0] ^ 1))
        + chunk(b"IEND", b""),
        valid + b"trailing-bytes",
        signature
        + chunk(b"IHDR", header)
        + chunk(b"tEXt", b"x")
        + image
        + chunk(b"IEND", b""),
    )
    for payload in invalid_cases:
        try:
            _png_ink_bbox(payload)
        except ValueError:
            continue
        raise AssertionError("strict parity PNG parser accepted malformed output")


def _self_check_svg_validator() -> None:
    """Exercise hostile SVG cases without coupling production runtime code."""
    valid = (
        '<svg xmlns="%s" width="20" height="20">'
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" '
        'refY="5" markerWidth="10" markerHeight="10" orient="auto">'
        '<path d="M0 0 L10 5 L0 10 z"/></marker></defs>'
        '<path d="M1 10 L10 10" marker-end="url(#arrow)"/></svg>' % SVG_NS
    )
    _strict_svg_validate(valid)
    expanded = '<svg xmlns="%s"><path d="M0 0 L1 1"/></svg>' % SVG_NS
    _strict_svg_validate(expanded, output=True)
    invalid = (
        '<svg xmlns="%s"><script>alert(1)</script></svg>' % SVG_NS,
        '<svg xmlns="%s"><image href="https://evil"/></svg>' % SVG_NS,
        '<svg xmlns="%s"><path fill="url(#missing)"/></svg>' % SVG_NS,
        '<svg xmlns="%s"><path d="M0 0" onload="evil()"/></svg>' % SVG_NS,
        '<svg xmlns="urn:not-svg"><path/></svg>',
        '<svg xmlns="%s"><path d="M0 0"/>tail</svg>' % SVG_NS,
        '<svg xmlns="%s"><defs><path id="x"/><path id="x"/></defs></svg>' % SVG_NS,
    )
    for payload in invalid:
        try:
            _strict_svg_validate(payload)
        except ValueError:
            continue
        raise AssertionError("strict SVG validator accepted malformed output")
    try:
        _strict_svg_validate('<svg xmlns="%s"><text>x</text></svg>' % SVG_NS, output=True)
    except ValueError:
        pass
    else:
        raise AssertionError("strict SVG validator accepted residual text")
    nested = '<svg xmlns="%s">%s<path d="M0 0"/>%s</svg>' % (
        SVG_NS,
        "<g>" * 257,
        "</g>" * 257,
    )
    try:
        _strict_svg_validate(nested)
    except ValueError:
        pass
    else:
        raise AssertionError("strict SVG validator accepted excessive nesting")


def _normalise_clip_ids(text: str) -> str:
    """Canonicalize generated clip IDs without touching geometry or paint."""
    mapping: Dict[str, str] = {}

    def replace_id(match: re.Match) -> str:
        value = match.group(1)
        mapping.setdefault(value, "clip-path-N%d" % (len(mapping) + 1))
        return 'id="%s"' % mapping[value]

    text = CLIP_ID_RE.sub(replace_id, text)
    for old, new in mapping.items():
        text = text.replace("url(#%s)" % old, "url(#%s)" % new)
    return text


def _write_output(
    report_dir: Path, case_id: str, suffix: str, data: bytes
) -> Dict[str, Any]:
    """Write one evidence output and return its digest record."""
    path = report_dir / "cases" / case_id
    path.mkdir(parents=True, exist_ok=True)
    output = path / suffix
    output.write_bytes(data)
    return {
        "path": output.relative_to(report_dir).as_posix(),
        "bytes": len(data),
        "sha256": _sha256(data),
    }


def run_cases(
    engine: DiagramAssetEngine,
    cases: List[Dict[str, Any]],
    report_dir: Path,
    legacy_svg_input: bool = False,
) -> Dict[str, Any]:
    """Render corpus cases and return deterministic arrow/output evidence."""
    report: Dict[str, Any] = {
        "cases": [],
        "layouts": 0,
        "arrows": 0,
        "directions": {"right": 0, "down": 0, "left": 0, "up": 0},
    }
    for case in cases:
        request = request_for_case(case)
        svg = engine.render_svg(request)
        _strict_svg_validate(svg)
        if legacy_svg_input:
            # Keep the historical SVG-text path available for immutable
            # reference capture.  The production engine still supports this
            # compatibility input, while the current corpus exercises the
            # DiagramData path below.
            png = engine.render_png(svg)
            expanded = engine.expand_svg(svg)
        else:
            # The canonical maintenance path exercises DiagramData requests
            # so the corpus covers the public renderer-to-resvg handoff.
            png = engine.render_png(request)
            expanded = engine.expand_svg(request)
        png_width, png_height, png_bbox = _png_ink_bbox(png)
        if (
            png_bbox[0] < 0
            or png_bbox[1] < 0
            or png_bbox[2] >= png_width
            or png_bbox[3] >= png_height
        ):
            raise ValueError(
                "case %s produced an out-of-canvas PNG ink bound: %s"
                % (case["id"], png_bbox)
            )
        expanded_root = ET.fromstring(expanded)
        _strict_svg_validate(expanded, output=True)
        expanded_paths = list(expanded_root.iter("{%s}path" % SVG_NS))
        if not expanded_paths:
            raise ValueError("case %s produced an empty expanded SVG" % case["id"])
        if list(expanded_root.iter("{%s}text" % SVG_NS)) or list(
            expanded_root.iter("{%s}marker" % SVG_NS)
        ):
            raise ValueError(
                "case %s expanded SVG retained text or marker elements" % case["id"]
            )
        arrows = inspect_arrows(svg, request)
        if len(arrows) != int(case["arrows"]):
            raise ValueError(
                "case %s produced %d arrows, expected %d"
                % (case["id"], len(arrows), int(case["arrows"]))
            )
        for arrow in arrows:
            # State blocks use the strict target-border contract.  ELK routes
            # pseudo-exit circles through the owning composite boundary, so
            # their dedicated tolerance is looser but still bounded and
            # catches a broken route instead of skipping the endpoint.
            tip_limit = 0.001 if arrow["targetShape"] == "rect" else 3.0
            cosine_limit = 0.999 if arrow["targetShape"] == "rect" else 0.8
            if (arrow["target"] is not None and arrow["tipError"] > tip_limit) or arrow[
                "terminalLength"
            ] < 18.0:
                raise ValueError(
                    "case %s failed endpoint gate: %s" % (case["id"], arrow)
                )
            if (
                arrow["target"] is not None
                and arrow["normalCosine"] is not None
                and arrow["normalCosine"] <= cosine_limit
            ):
                raise ValueError(
                    "case %s failed normality gate: %s" % (case["id"], arrow)
                )
            report["directions"][arrow["direction"]] += 1
        report["cases"].append(
            {
                "id": case["id"],
                "corpus": case["corpus"],
                "corpusSha256": case["corpusSha256"],
                "sourceFixture": case.get("sourceFixture"),
                "sourceSha256": case.get("sourceSha256"),
                "direction": request["options"]["direction"],
                "group": case.get("group"),
                "arrows": arrows,
                "outputs": {
                    "svg": _write_output(
                        report_dir,
                        str(case["id"]),
                        "canonical.svg",
                        svg.encode("utf-8"),
                    ),
                    "png": _write_output(
                        report_dir, str(case["id"]), "render.png", png
                    ),
                    "expanded": _write_output(
                        report_dir,
                        str(case["id"]),
                        "expanded.svg",
                        expanded.encode("utf-8"),
                    ),
                },
            }
        )
        report["layouts"] += 1
        report["arrows"] += len(arrows)
    return report


def _assert_expected(report: Dict[str, Any], args: argparse.Namespace) -> None:
    """Apply optional count, group, and direction expectations."""
    if args.expected_layouts is not None and report["layouts"] != args.expected_layouts:
        raise ValueError(
            "expected %d layouts, got %d" % (args.expected_layouts, report["layouts"])
        )
    if args.expected_arrows is not None and report["arrows"] != args.expected_arrows:
        raise ValueError(
            "expected %d arrows, got %d" % (args.expected_arrows, report["arrows"])
        )
    if args.expected_directions:
        expected = {
            key: int(value)
            for key, value in (
                item.split("=", 1) for item in args.expected_directions.split(",")
            )
        }
        if report["directions"] != expected:
            raise ValueError(
                "direction distribution differs: expected %s, got %s"
                % (expected, report["directions"])
            )
    if args.expected_groups:
        groups: Dict[str, int] = {}
        for item in report["cases"]:
            group = str(item.get("group"))
            groups[group] = groups.get(group, 0) + 1
        expected_groups = {
            key: int(value)
            for key, value in (
                item.split("=", 1) for item in args.expected_groups.split(",")
            )
        }
        if groups != expected_groups:
            raise ValueError(
                "layout groups differ: expected %s, got %s" % (expected_groups, groups)
            )


def _asset_provenance(
    corpus_paths: Iterable[Path], backend: str = "official-resvg-2.6.2"
) -> Dict[str, Any]:
    """Capture hashes needed to identify one renderer reference bundle."""
    files = [
        ROOT / "tools" / "diagram_assets" / "asset-lock.json",
        ROOT / "tools" / "diagram_assets" / "resvg-bridge.js",
    ]
    for relative in ("renderer.js", "resvg-binding.js", "resvg.wasm"):
        candidate = ROOT / "pyfcstm" / "diagram" / "assets" / relative
        if candidate.is_file():
            files.append(candidate)
    return {
        "backend": backend,
        "python": "%d.%d" % sys.version_info[:2],
        "files": {
            path.relative_to(ROOT).as_posix(): _sha256(path.read_bytes())
            for path in files
            if path.is_file()
        },
        "corpora": {
            path.relative_to(ROOT).as_posix(): _sha256(path.read_bytes())
            for path in corpus_paths
        },
    }


def _reference_payload(
    report: Dict[str, Any], corpus_paths: Iterable[Path], backend: str
) -> Dict[str, Any]:
    """Build a portable reference manifest with renderer provenance."""
    return {
        "schema": "pyfcstm-diagram-reference",
        "provenance": _asset_provenance(corpus_paths, backend=backend),
        "report": report,
    }


def _write_sha_ledger(root: Path, excluded: Iterable[str] = ()) -> None:
    """Write a deterministic root SHA ledger for a reference bundle."""
    excluded_set = set(excluded) | {"SHA256SUMS"}
    entries = []
    for output in root.rglob("*"):
        if output.is_file() and output.relative_to(root).as_posix() not in excluded_set:
            entries.append(
                "%s  %s"
                % (_sha256(output.read_bytes()), output.relative_to(root).as_posix())
            )
    (root / "SHA256SUMS").write_text(
        "\n".join(sorted(entries)) + "\n", encoding="ascii"
    )


def capture_reference(
    report: Dict[str, Any], path: Path, corpus_paths: Iterable[Path], backend: str
) -> None:
    """Write reference JSON, sidecar hash, and root SHA ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            _reference_payload(report, corpus_paths, backend),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(payload)
    path.with_name(path.name + ".sha256").write_text(
        _sha256(payload) + "\n", encoding="ascii"
    )
    _write_sha_ledger(path.parent, {path.name, path.name + ".sha256"})


def _validate_reference_files(path: Path, reference: Dict[str, Any]) -> None:
    """Validate reference sidecar, output paths, sizes, and hashes."""

    def reject_unknown(value: Dict[str, Any], allowed: set, label: str) -> None:
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "reference contains unknown %s fields: %s" % (label, ", ".join(unknown))
            )

    reject_unknown(reference, {"schema", "provenance", "report"}, "top-level")
    provenance = reference.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("reference provenance is malformed")
    reject_unknown(provenance, {"backend", "python", "files", "corpora"}, "provenance")
    report = reference.get("report")
    if not isinstance(report, dict):
        raise ValueError("reference report is malformed")
    reject_unknown(
        report,
        {
            "cases",
            "layouts",
            "arrows",
            "directions",
            "provenance",
            "memory",
            "cjk",
        },
        "report",
    )
    payload = path.read_bytes()
    sidecar_path = path.with_name(path.name + ".sha256")
    try:
        sidecar = sidecar_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as err:
        # OSError/UnicodeDecodeError: a reference sidecar is missing or not
        # the ASCII digest emitted by capture_reference.
        raise ValueError("reference JSON sidecar is unavailable") from err
    if _sha256(payload) != sidecar:
        raise ValueError("reference JSON sidecar hash mismatch")
    if reference.get("schema") != "pyfcstm-diagram-reference":
        raise ValueError("unsupported diagram reference schema")
    if not isinstance(report, dict) or not isinstance(report.get("cases"), list):
        raise ValueError("reference report is malformed")
    root = path.parent.resolve()
    ledger_path = root / "SHA256SUMS"
    try:
        ledger_lines = ledger_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as err:
        # OSError/UnicodeDecodeError: a reference bundle has no readable
        # root ledger, so its output set cannot be independently verified.
        raise ValueError("reference SHA256SUMS ledger is unavailable") from err
    ledger: Dict[str, str] = {}
    for line in ledger_lines:
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError as err:
            # ValueError: a ledger entry is not the canonical ``hash  path``
            # format emitted by capture_reference.
            raise ValueError("reference SHA256SUMS ledger is malformed") from err
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not relative:
            raise ValueError("reference SHA256SUMS ledger contains an invalid entry")
        ledger[relative] = digest
    expected_ledger = set()
    for case in report["cases"]:
        if not isinstance(case, dict):
            raise ValueError("reference contains a non-object case")
        reject_unknown(
            case,
            {
                "id",
                "corpus",
                "corpusSha256",
                "sourceFixture",
                "sourceSha256",
                "direction",
                "group",
                "arrows",
                "outputs",
            },
            "case",
        )
        outputs = case.get("outputs")
        if not isinstance(outputs, dict):
            raise ValueError("reference case outputs are malformed")
        reject_unknown(outputs, {"svg", "png", "expanded"}, "case output")
        for output in outputs.values():
            if not isinstance(output, dict):
                raise ValueError("reference case output is malformed")
            reject_unknown(output, {"path", "bytes", "sha256"}, "output")
            relative = Path(str(output.get("path", "")))
            candidate = (root / relative).resolve()
            if root not in candidate.parents:
                raise ValueError("reference output escapes its bundle: %s" % relative)
            if not candidate.is_file():
                raise ValueError("reference output is missing: %s" % relative)
            data = candidate.read_bytes()
            if len(data) != int(output.get("bytes", -1)) or _sha256(data) != output.get(
                "sha256"
            ):
                raise ValueError("reference output hash/size mismatch: %s" % relative)
            relative_name = relative.as_posix()
            expected_ledger.add(relative_name)
            if ledger.get(relative_name) != _sha256(data):
                raise ValueError("reference root ledger mismatch: %s" % relative)
    cjk = report.get("cjk", {})
    if not isinstance(cjk, dict):
        raise ValueError("reference CJK output manifest is malformed")
    for locale, output in cjk.items():
        if locale not in {"sc", "tc", "hk", "jp", "kr"}:
            raise ValueError("reference contains an unknown CJK locale: %s" % locale)
        if not isinstance(output, dict):
            raise ValueError("reference CJK output is malformed: %s" % locale)
        reject_unknown(output, {"path", "bytes", "sha256"}, "CJK output")
        relative = Path(str(output.get("path", "")))
        candidate = (root / relative).resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise ValueError("reference CJK output is missing: %s" % relative)
        data = candidate.read_bytes()
        if len(data) != int(output.get("bytes", -1)) or _sha256(data) != output.get(
            "sha256"
        ):
            raise ValueError("reference CJK output hash/size mismatch: %s" % relative)
        relative_name = relative.as_posix()
        expected_ledger.add(relative_name)
        if ledger.get(relative_name) != _sha256(data):
            raise ValueError("reference root ledger mismatch: %s" % relative)
    if set(ledger) != expected_ledger:
        raise ValueError("reference root ledger contains unexpected files")


def _assert_custom_reference_provenance(provenance: Dict[str, Any]) -> None:
    """Reject a reference whose declared custom asset set is incomplete."""
    if provenance.get("backend") != "custom-resvg-0.37":
        raise ValueError(
            "reference backend is not the locked custom resvg 0.37 baseline"
        )
    files = provenance.get("files")
    if not isinstance(files, dict):
        raise ValueError("reference custom backend file provenance is missing")
    for relative, expected in _CUSTOM_REFERENCE_FILES.items():
        if files.get(relative) != expected:
            raise ValueError(
                "reference does not contain the locked custom backend file: %s"
                % relative
            )


def _self_check_reference_provenance() -> None:
    """Exercise the custom-reference provenance gate and its negative path."""
    valid = {
        "backend": "custom-resvg-0.37",
        "files": dict(_CUSTOM_REFERENCE_FILES),
    }
    _assert_custom_reference_provenance(valid)
    for relative in _CUSTOM_REFERENCE_FILES:
        corrupted = {
            "backend": valid["backend"],
            "files": dict(valid["files"]),
        }
        corrupted["files"][relative] = "0" * 64
        try:
            _assert_custom_reference_provenance(corrupted)
        except ValueError as err:
            if relative not in str(err):
                raise AssertionError(
                    "provenance corruption failed for the wrong file: %s" % relative
                ) from err
        else:
            raise AssertionError("provenance corruption was accepted: %s" % relative)


def _self_check_reference_comparison() -> None:
    """Exercise strict and clip-ID-only reference comparison semantics."""
    with tempfile.TemporaryDirectory(prefix="pyfcstm-diagram-reference-check-") as raw:
        root = Path(raw)
        reference_root = root / "reference"
        current_root = root / "current"
        reference_root.mkdir()
        current_root.mkdir()
        relative_root = Path("cases") / "one"
        outputs = {
            "svg": b'<svg xmlns="http://www.w3.org/2000/svg"/>',
            "png": b"png-output",
            "expanded": (
                b'<svg><defs><clipPath id="clipPath-old"><path d="M0,0"/>'
                b'</clipPath></defs><g clip-path="url(#clipPath-old)"/></svg>'
            ),
        }
        current_outputs = dict(outputs)
        current_outputs["expanded"] = (
            b'<svg><defs><clipPath id="clipPath-new"><path d="M0,0"/>'
            b'</clipPath></defs><g clip-path="url(#clipPath-new)"/></svg>'
        )

        def write_outputs(directory: Path, values: Dict[str, bytes]) -> Dict[str, Any]:
            result = {}
            target = directory / relative_root
            target.mkdir(parents=True)
            for kind, data in values.items():
                path = target / kind
                path.write_bytes(data)
                result[kind] = {
                    "path": path.relative_to(directory).as_posix(),
                    "bytes": len(data),
                    "sha256": _sha256(data),
                }
            return result

        old_case = {
            "id": "one",
            "corpus": "fixture.json",
            "corpusSha256": "0" * 64,
            "sourceFixture": "fixture.json#one",
            "sourceSha256": "1" * 64,
            "direction": "right",
            "group": "LR",
            "arrows": 0,
            "outputs": write_outputs(reference_root, outputs),
        }
        new_case = dict(old_case)
        new_case["outputs"] = write_outputs(current_root, current_outputs)
        old_report = {
            "cases": [old_case],
            "layouts": 1,
            "arrows": 0,
            "directions": {"right": 1},
            "cjk": {},
        }
        new_report = {
            "cases": [new_case],
            "layouts": 1,
            "arrows": 0,
            "directions": {"right": 1},
            "cjk": {},
        }
        custom_provenance = {
            "backend": "custom-resvg-0.37",
            "python": "%d.%d" % sys.version_info[:2],
            "files": dict(_CUSTOM_REFERENCE_FILES),
            "corpora": {},
        }
        official_provenance = {
            "backend": "official-resvg-2.6.2",
            "python": "%d.%d" % sys.version_info[:2],
            "files": {},
            "corpora": {},
        }
        payload = (
            json.dumps(
                {
                    "schema": "pyfcstm-diagram-reference",
                    "provenance": custom_provenance,
                    "report": old_report,
                },
                ensure_ascii=True,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")
        reference_path = reference_root / "reference.json"
        reference_path.write_bytes(payload)
        reference_path.with_name("reference.json.sha256").write_text(
            _sha256(payload) + "\n", encoding="ascii"
        )
        _write_sha_ledger(reference_root, {"reference.json", "reference.json.sha256"})
        current = dict(new_report)
        current["provenance"] = official_provenance
        try:
            compare_reference(current, reference_path, current_root)
        except ValueError:
            pass
        else:
            raise AssertionError(
                "strict expanded SVG comparison accepted a generated clip-ID change"
            )
        compare_reference(
            current,
            reference_path,
            current_root,
            check_expanded_id_only=True,
        )


def compare_reference(
    report: Dict[str, Any],
    path: Path,
    report_dir: Path,
    check_expanded_id_only: bool = False,
) -> None:
    """Compare current outputs against a captured reference bundle.

    ``check_expanded_id_only`` permits only generated clip-ID renaming in the
    expanded SVG; all other output bytes remain exact.  Without the flag the
    expanded SVG is compared byte-for-byte, which is useful for diagnosing an
    unexpected structural difference.
    """
    try:
        reference = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        # OSError/UnicodeDecodeError/ValueError: the reference is absent or
        # cannot be parsed as the required UTF-8 JSON manifest.
        raise ValueError("reference JSON is unavailable or malformed") from err
    if not isinstance(reference, dict):
        raise ValueError("reference JSON root is not an object")
    _validate_reference_files(path, reference)
    old_report = reference["report"]
    old_provenance = reference.get("provenance")
    new_provenance = report.get("provenance")
    if not isinstance(old_provenance, dict) or not isinstance(new_provenance, dict):
        raise ValueError("reference or current renderer provenance is missing")
    _assert_custom_reference_provenance(old_provenance)
    if new_provenance.get("backend") != "official-resvg-2.6.2":
        raise ValueError("current renderer is not the official resvg 2.6.2 backend")
    if old_provenance.get("python") != new_provenance.get("python"):
        raise ValueError("reference and current runtime versions differ")
    # Backend hashes intentionally differ; both reports must identify exactly
    # the same corpus bytes after the baseline identity has been verified.
    if old_provenance.get("corpora") != new_provenance.get("corpora"):
        raise ValueError("reference corpus provenance differs")
    if (
        old_report.get("layouts") != report.get("layouts")
        or old_report.get("arrows") != report.get("arrows")
        or old_report.get("directions") != report.get("directions")
    ):
        raise ValueError("reference corpus counts or direction distribution differ")
    old_cases = {item["id"]: item for item in old_report["cases"]}
    new_cases = {item["id"]: item for item in report["cases"]}
    if list(old_cases) != list(new_cases):
        raise ValueError("reference fixture identities or order differ")
    if "memory" in report:
        old_memory = old_report.get("memory")
        if not isinstance(old_memory, dict):
            raise ValueError("reference lacks the required custom memory baseline")
        _assert_memory_limits(report["memory"])
        old_p95 = int(old_memory.get("steadyRssP95Bytes", 0))
        new_p95 = int(report["memory"].get("steadyRssP95Bytes", 0))
        if old_p95 <= 0 or new_p95 <= 0:
            raise ValueError("reference memory baseline lacks RSS samples")
        allowed_delta = max(32 * 1024 * 1024, int(old_p95 * 0.10))
        if new_p95 - old_p95 > allowed_delta:
            raise ValueError(
                "official steady-state RSS exceeds custom baseline: %d > %d"
                % (new_p95, old_p95 + allowed_delta)
            )
    for case_id, current in new_cases.items():
        old = old_cases[case_id]
        for field in (
            "corpus",
            "corpusSha256",
            "sourceFixture",
            "sourceSha256",
            "direction",
            "group",
            "arrows",
        ):
            if old.get(field) != current.get(field):
                raise ValueError(
                    "reference fixture metadata differs: %s/%s" % (case_id, field)
                )
        for kind in ("png", "svg", "expanded"):
            old_path = path.parent / old["outputs"][kind]["path"]
            new_path = report_dir / current["outputs"][kind]["path"]
            old_bytes = old_path.read_bytes()
            new_bytes = new_path.read_bytes()
            if kind == "expanded" and check_expanded_id_only:
                old_bytes = _normalise_clip_ids(old_bytes.decode("utf-8")).encode(
                    "utf-8"
                )
                new_bytes = _normalise_clip_ids(new_bytes.decode("utf-8")).encode(
                    "utf-8"
                )
            if old_bytes != new_bytes:
                raise ValueError(
                    "reference parity mismatch for %s/%s" % (case_id, kind)
                )
    old_cjk = old_report.get("cjk", {})
    new_cjk = report.get("cjk", {})
    if set(old_cjk) != set(new_cjk):
        raise ValueError("reference CJK locale set differs")
    for locale, current in new_cjk.items():
        old = old_cjk[locale]
        old_path = path.parent / old["path"]
        new_path = report_dir / current["path"]
        if old_path.read_bytes() != new_path.read_bytes():
            raise ValueError("reference parity mismatch for CJK locale %s" % locale)


def _clone(value: Any) -> Any:
    """Clone a JSON-compatible maintenance request."""
    return json.loads(json.dumps(value, ensure_ascii=False))


def check_cjk(
    engine: DiagramAssetEngine,
    report_dir: Path,
    base_request: Dict[str, Any],
    legacy_svg_input: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Render five locale samples and require valid non-empty PNG output."""
    samples = {"sc": "中文", "tc": "繁體", "hk": "香港", "jp": "日本語", "kr": "한국어"}
    outputs: Dict[str, Dict[str, Any]] = {}
    for locale, text in samples.items():
        request = _clone(base_request)
        request["cjkLocale"] = locale
        request["diagram"]["rootState"]["children"][0]["displayName"] = text
        payload = engine.render_svg(request) if legacy_svg_input else request
        png = engine.render_png(payload)
        _png_ink_bbox(png)
        expanded = engine.expand_svg(payload)
        if "<path" not in expanded or "<text" in expanded or "<marker" in expanded:
            raise ValueError("CJK expanded SVG is invalid for locale %s" % locale)
        outputs[locale] = _write_output(
            report_dir, "cjk-%s" % locale, "render.png", png
        )
    return outputs


def _rss_bytes() -> int:
    """Return current process RSS without adding a runtime dependency."""
    statm = Path("/proc/self/statm")
    if statm.is_file():
        try:
            pages = int(statm.read_text(encoding="ascii").split()[1])
            return pages * int(os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, IndexError):
            # OSError/ValueError/IndexError: procfs may be unavailable or
            # expose an incomplete statm record on a constrained host.
            pass
    try:
        import resource
    except ImportError:
        # ImportError: Windows does not provide the resource module.
        resource = None
    if resource is not None:
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if sys.platform == "darwin" else value * 1024
    return 0


def _heap_stats(engine: DiagramAssetEngine) -> Dict[str, int]:
    """Read V8 heap counters exposed by both MiniRacer distributions."""
    context = getattr(engine, "_context", None)
    method = getattr(context, "heap_stats", None)
    if not callable(method):
        return {}
    try:
        value = method()
    except (AttributeError, TypeError, ValueError):
        # AttributeError/TypeError/ValueError: a runtime distribution may not
        # expose heap statistics or may reject the call after context reset.
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        key: int(value[key])
        for key in ("used_heap_size", "total_heap_size", "heap_size_limit")
        if key in value
    }


def _bridge_metrics(engine: DiagramAssetEngine) -> Dict[str, Any]:
    """Read token-bound context ownership and registered-font metrics."""
    try:
        value = engine._eval("__pyfcstm_resvg_metrics()")
        metrics = json.loads(str(value))
    except (TypeError, ValueError):
        # TypeError/ValueError: an older or corrupted bridge did not return
        # the documented JSON metrics envelope.
        raise ValueError("resvg bridge did not return memory metrics")
    if not isinstance(metrics, dict):
        raise ValueError("resvg bridge memory metrics are not an object")
    try:
        active_context = int(metrics["activeContext"])
        python_context = getattr(engine, "_active_context_count", None)
        if python_context is not None and active_context != int(python_context):
            raise ValueError("bridge/Python active-context lifecycle counts differ")
        expected_token = getattr(engine, "_context_token", None)
        if not expected_token or str(metrics["contextToken"]) != str(expected_token):
            raise ValueError("bridge/Python context lifecycle tokens differ")
        return {
            "activeContext": active_context,
            "contextToken": str(metrics["contextToken"]),
            "registeredFonts": int(metrics["registeredFonts"]),
        }
    except (KeyError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: the bridge omitted or corrupted a
        # required context/font counter.
        raise ValueError("resvg bridge memory metrics are incomplete") from err


def _memory_sample(
    engine: DiagramAssetEngine, phase: str, index: int, locale: str
) -> Dict[str, Any]:
    """Capture one RSS, V8 heap, and bridge ownership sample."""
    notify = getattr(getattr(engine, "_context", None), "low_memory_notification", None)
    if callable(notify):
        notify()
    sample: Dict[str, Any] = {
        "phase": phase,
        "index": index,
        "locale": locale,
        "rssBytes": _rss_bytes(),
    }
    sample.update(_heap_stats(engine))
    sample.update(_bridge_metrics(engine))
    if sample["activeContext"] != 1 or sample["registeredFonts"] != 5:
        raise ValueError("resvg context/font ownership invariant failed: %s" % sample)
    return sample


def _p95(values: List[int]) -> int:
    """Return the nearest-rank 95th percentile for non-empty values."""
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, int(math.ceil(len(ordered) * 0.95)) - 1)
    return ordered[index]


def _linear_slope(values: List[int]) -> float:
    """Return least-squares bytes-per-switch slope for a sample sequence."""
    if len(values) < 2:
        return 0.0
    mean_x = (len(values) - 1) / 2.0
    mean_y = sum(values) / float(len(values))
    denominator = sum((index - mean_x) ** 2 for index in range(len(values)))
    if denominator == 0:
        return 0.0
    return (
        sum((index - mean_x) * (value - mean_y) for index, value in enumerate(values))
        / denominator
    )


def _memory_summary(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize warm-up, steady-state, and locale-switch memory samples."""
    rss = [int(item["rssBytes"]) for item in samples if int(item["rssBytes"]) > 0]
    switch_rss = [
        int(item["rssBytes"])
        for item in samples
        if item["phase"] == "switch" and int(item["rssBytes"]) > 0
    ]
    warmup_rss = [
        int(item["rssBytes"])
        for item in samples
        if item["phase"] == "warmup" and int(item["rssBytes"]) > 0
    ]
    steady_rss = [
        int(item["rssBytes"])
        for item in samples
        if item["phase"] == "steady" and int(item["rssBytes"]) > 0
    ]
    if not rss:
        raise ValueError("memory gate could not measure process RSS")
    slope_window = switch_rss[-25:] or switch_rss
    last_five = switch_rss[-5:] or rss[-5:]
    first_five = warmup_rss[:5] or rss[:5]
    return {
        "renders": len(samples),
        "sampleCount": len(samples),
        "rssP95Bytes": _p95(rss),
        "steadyRssP95Bytes": _p95(steady_rss or rss),
        "switchSlopeBytesPerSwitch": _linear_slope(slope_window),
        "switchSlopeWindow": len(slope_window),
        "warmupFirst5MeanBytes": sum(first_five) / float(len(first_five)),
        "switchLast5MeanBytes": sum(last_five) / float(len(last_five)),
        "heapUsedP95Bytes": _p95(
            [
                int(item["used_heap_size"])
                for item in samples
                if "used_heap_size" in item
            ]
        ),
        "samples": samples,
    }


def _assert_memory_limits(summary: Dict[str, Any]) -> None:
    """Enforce absolute memory ownership and leak-slope limits."""
    if float(summary["switchSlopeBytesPerSwitch"]) > 1024 * 1024:
        raise ValueError("memory switch RSS slope exceeds 1 MiB/switch")
    if (
        float(summary["switchLast5MeanBytes"]) - float(summary["warmupFirst5MeanBytes"])
        > 32 * 1024 * 1024
    ):
        raise ValueError("memory switch RSS grew by more than 32 MiB")


def check_memory(
    engine: DiagramAssetEngine,
    request: Dict[str, Any],
    legacy_svg_input: bool = False,
) -> Dict[str, Any]:
    """Run 10 warm-ups, 100 steady renders, and 50 locale switches."""

    def render(sample_request: Dict[str, Any]) -> None:
        if legacy_svg_input:
            engine.render_png(engine.render_svg(sample_request))
        else:
            engine.render_png(sample_request)

    samples: List[Dict[str, Any]] = []
    for index in range(10):
        render(request)
        samples.append(_memory_sample(engine, "warmup", index, "sc"))
    for index in range(100):
        render(request)
        samples.append(_memory_sample(engine, "steady", index, "sc"))
    for index, locale in enumerate(("sc", "tc", "hk", "jp", "kr") * 10):
        sample = _clone(request)
        sample["cjkLocale"] = locale
        render(sample)
        samples.append(_memory_sample(engine, "switch", index, locale))
    summary = _memory_summary(samples)
    _assert_memory_limits(summary)
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    """Run the rendering maintenance gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", action="append", type=Path, default=None)
    parser.add_argument("--expected-layouts", type=int)
    parser.add_argument("--expected-arrows", type=int)
    parser.add_argument("--expected-directions")
    parser.add_argument("--expected-groups")
    parser.add_argument("--capture-reference", type=Path)
    parser.add_argument("--compare-reference", type=Path)
    parser.add_argument(
        "--check-expanded-id-only",
        action="store_true",
        help="allow only generated clip-ID renaming in expanded SVG parity",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the reference provenance self-check without rendering",
    )
    parser.add_argument("--check-cjk", action="store_true")
    parser.add_argument("--check-memory", action="store_true")
    parser.add_argument(
        "--legacy-svg-input",
        action="store_true",
        help="capture references through the compatibility SVG-text input path",
    )
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args(argv)
    if args.check:
        _self_check_reference_provenance()
        _self_check_reference_comparison()
        _self_check_png_parser()
        _self_check_svg_validator()
        print(
            "diagram rendering checker: provenance, parity, SVG, and PNG self-check passed"
        )
        return 0
    corpus_paths = tuple(path.resolve() for path in (args.corpus or DEFAULT_CORPORA))
    cases = load_cases(corpus_paths)
    memory_report = None
    if args.check_memory:
        # Keep the memory probe independent from the arrow corpus renderings;
        # otherwise the corpus itself becomes an unbounded warm-up allocation.
        memory_engine = DiagramAssetEngine()
        memory_report = check_memory(
            memory_engine,
            request_for_case(cases[0]),
            legacy_svg_input=args.legacy_svg_input,
        )
        memory_engine._discard_context()
    report_dir = args.report_dir or Path(
        tempfile.mkdtemp(prefix="pyfcstm-diagram-report-")
    )
    engine = DiagramAssetEngine()
    report = run_cases(
        engine, cases, report_dir, legacy_svg_input=args.legacy_svg_input
    )
    backend = "custom-resvg-0.37" if args.legacy_svg_input else "official-resvg-2.6.2"
    report["provenance"] = _asset_provenance(corpus_paths, backend=backend)
    if memory_report is not None:
        report["memory"] = memory_report
    _assert_expected(report, args)
    if args.check_cjk:
        report["cjk"] = check_cjk(
            engine,
            report_dir,
            request_for_case(cases[0]),
            legacy_svg_input=args.legacy_svg_input,
        )
    if args.capture_reference:
        capture_reference(report, args.capture_reference, corpus_paths, backend)
    if args.compare_reference:
        compare_reference(
            report,
            args.compare_reference,
            report_dir,
            check_expanded_id_only=args.check_expanded_id_only,
        )
    (report_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "layouts": report["layouts"],
                "arrows": report["arrows"],
                "directions": report["directions"],
                "reportDir": str(report_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
