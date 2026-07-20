"""Verify the MiniRacer runtime floor for the packaged diagram engine.

The command is a maintenance gate.  It runs in the interpreter selected by a
CI matrix and proves that the same ES2017 renderer, official resvg binding,
WASM module, PNG path, and expanded-SVG path work with the distribution family
selected by the Python version marker.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.diagram import (  # noqa: E402
    DiagramAssetEngine,
    DiagramAssetError,
    DiagramEngineConflictError,
    DiagramEngineMetadataError,
)


DEFAULT_CORPUS = ROOT / "tools" / "diagram_assets" / "corpus" / "canonical-arrows.json"
VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")


def _version(name: str) -> Optional[str]:
    """Return one installed distribution version, or ``None``."""
    try:
        from importlib import metadata
    except ImportError:
        try:
            import importlib_metadata as metadata
        except ImportError:
            return None
    try:
        return str(metadata.version(name))
    except metadata.PackageNotFoundError:
        return None


def _version_tuple(value: str) -> Tuple[int, int, int]:
    """Parse the numeric prefix used by the runtime floor comparison."""
    match = VERSION_RE.match(value)
    if not match:
        raise ValueError("runtime version is not numeric: %s" % value)
    return tuple(int(part or 0) for part in match.groups())


def _load_request(path: Path) -> Dict[str, Any]:
    """Load the first serialized DiagramData request from a corpus."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        # OSError/UnicodeDecodeError/ValueError: the checked-in corpus cannot
        # be read as UTF-8 JSON by this interpreter.
        raise ValueError("cannot read runtime-floor corpus: %s" % path) from err
    try:
        request = payload["cases"][0]["request"]
    except (KeyError, IndexError, TypeError) as err:
        # KeyError/IndexError/TypeError: the corpus lacks a first DiagramData
        # request with the stable maintenance shape.
        raise ValueError("runtime-floor corpus has no DiagramData request") from err
    if not isinstance(request, dict):
        raise ValueError("runtime-floor corpus request is not an object")
    return request


def _runtime_family() -> Tuple[str, str, str]:
    """Return expected family, distribution name, and installed version."""
    legacy = _version("py-mini-racer")
    modern = _version("mini-racer")
    if legacy is not None and modern is not None:
        raise DiagramEngineConflictError(
            "mini-racer %s and py-mini-racer %s are installed together"
            % (modern, legacy)
        )
    if sys.version_info < (3, 8):
        if legacy is None:
            raise DiagramEngineMetadataError(
                "Python 3.7 requires the py-mini-racer distribution"
            )
        return "legacy", "py-mini-racer", legacy
    if modern is None:
        raise DiagramEngineMetadataError(
            "Python 3.8+ requires the mini-racer distribution"
        )
    return "modern", "mini-racer", modern


def _requirement_ok(requirement: str) -> None:
    """Require one installed MiniRacer distribution to satisfy a pin."""
    match = re.fullmatch(
        r"(mini-racer|py-mini-racer)\s*(==|>=)\s*([0-9.]+)", requirement.strip()
    )
    if not match:
        raise ValueError("unsupported runtime requirement: %s" % requirement)
    name, operator, expected_text = match.groups()
    actual = _version(name)
    if actual is None:
        raise DiagramEngineMetadataError("required runtime is not installed: %s" % name)
    expected = _version_tuple(expected_text)
    current = _version_tuple(actual)
    if (operator == "==" and current != expected) or (
        operator == ">=" and current < expected
    ):
        raise ValueError(
            "%s %s does not satisfy %s" % (name, actual, requirement.strip())
        )


def _resolve_python(spec: str) -> str:
    """Resolve a Python executable or a major.minor selector."""
    candidate = spec
    if re.fullmatch(r"\d+\.\d+", spec):
        candidate = "python%s" % spec
    executable = shutil.which(candidate)
    if executable is None:
        raise FileNotFoundError(
            "cannot resolve requested Python interpreter: %s" % spec
        )
    return executable


def _reexec_for_python(argv, spec: str) -> int:
    """Run this checker in the requested interpreter and return its status."""
    executable = _resolve_python(spec)
    if os.path.realpath(executable) == os.path.realpath(sys.executable):
        return -1
    child = [executable, __file__]
    child.extend(argv)
    child.remove("--python")
    child.remove(spec)
    return subprocess.run(child, check=False).returncode


def run(
    requests: list,
    minimum: Tuple[int, int, int],
    formats: Tuple[str, ...],
    check_timeout_reset: bool = False,
) -> Dict[str, Any]:
    """Run runtime export and bridge smoke checks."""
    family, distribution, version = _runtime_family()
    if _version_tuple(version) < minimum:
        raise ValueError(
            "%s %s is below the required floor %s.%s.%s"
            % (distribution, version, minimum[0], minimum[1], minimum[2])
        )
    engine = DiagramAssetEngine()
    exports = str(engine._eval("typeof resvg.Resvg + ':' + typeof resvg.initWasm"))
    encoders = str(engine._eval("typeof TextEncoder + ':' + typeof TextDecoder"))
    if exports != "function:function":
        raise ValueError("official resvg binding exports are unavailable: %s" % exports)
    if encoders != "function:function":
        raise ValueError(
            "TextEncoder/TextDecoder host shim is unavailable: %s" % encoders
        )
    counts = {"svg": 0, "png": 0, "expanded-svg": 0}
    for request in requests:
        if "svg" in formats:
            svg = engine.render_svg(request)
            if not str(svg).startswith("<svg"):
                raise ValueError("runtime floor returned an invalid SVG")
            counts["svg"] += 1
        if "png" in formats:
            png = engine.render_png(request)
            if not png.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("runtime floor returned an invalid PNG")
            counts["png"] += 1
        if "expanded-svg" in formats:
            expanded = engine.expand_svg(request)
            if not expanded.lstrip().startswith("<svg") or "<path" not in expanded:
                raise ValueError("runtime floor returned an invalid expanded SVG")
            counts["expanded-svg"] += 1
    if check_timeout_reset:
        timeout_engine = DiagramAssetEngine()
        timeout_engine.timeout = 0.05
        try:
            timeout_engine._eval("while (true) {}", timeout=0.05)
        except DiagramAssetError:
            # DiagramAssetError: the deliberate infinite loop must interrupt
            # and discard the context before a fresh render is attempted.
            print(
                "diagram engine floor: expected timeout interrupted the context",
                file=sys.stderr,
            )
        else:
            raise ValueError("runtime timeout smoke did not interrupt")
        timeout_engine.timeout = 30.0
        timeout_engine.render_svg(requests[0])
    if engine._eval("6 * 7") != 42:
        raise ValueError("MiniRacer arithmetic smoke failed")
    return {
        "python": "%d.%d.%d" % sys.version_info[:3],
        "family": family,
        "distribution": distribution,
        "version": version,
        "resvgExports": exports,
        "textEncoding": encoders,
        "formats": list(formats),
        "cases": len(requests),
        "counts": counts,
    }


def main(argv=None) -> int:
    """Run the runtime-floor maintenance command."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--python", dest="python_spec")
    parser.add_argument("--requirement")
    parser.add_argument(
        "--formats",
        default="svg,png,expanded-svg",
        help="comma-separated subset of svg,png,expanded-svg",
    )
    parser.add_argument("--all-cases", action="store_true")
    parser.add_argument("--check-timeout-reset", action="store_true")
    parser.add_argument(
        "--minimum", default=None, help="override the required x.y.z floor"
    )
    args = parser.parse_args(argv)
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if args.python_spec:
        status = _reexec_for_python(raw_argv, args.python_spec)
        if status >= 0:
            return status
    if args.requirement:
        _requirement_ok(args.requirement)
    formats = tuple(item.strip() for item in args.formats.split(",") if item.strip())
    if not formats or any(
        item not in {"svg", "png", "expanded-svg"} for item in formats
    ):
        raise ValueError("--formats must contain only svg,png,expanded-svg")
    minimum = (0, 6, 0) if sys.version_info < (3, 8) else (0, 7, 0)
    if args.minimum:
        minimum = _version_tuple(args.minimum)
    payload = json.loads(args.corpus.resolve().read_text(encoding="utf-8"))
    requests = (
        [item["request"] for item in payload.get("cases", [])]
        if args.all_cases
        else [_load_request(args.corpus.resolve())]
    )
    if not requests or any(not isinstance(item, dict) for item in requests):
        raise ValueError("runtime-floor corpus contains no valid requests")
    result = run(requests, minimum, formats, args.check_timeout_reset)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
