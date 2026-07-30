"""
Require the browser download and the synchronous export to agree.

The same diagram is exported twice by different machinery: the browser download
runs the shared export core inside a real browser, and the synchronous export runs
it in the embedded host through a DOM adapter.  They are meant to produce the same
drawing.  Nothing else checks that, and the ways they can diverge are all quiet:

* A presentation option that reaches one path and not the other returns a valid
  file of the wrong colour.  This is not hypothetical -- the synchronous path
  ignored ``palette``, ``mode`` and ``cjkLocale`` entirely until they were moved
  to the request root, and every structural assertion passed throughout.
* A path that exports the renderer's canonical SVG instead of the expanded form
  returns a document that renders differently wherever the fonts differ.
* A path that rasterises the drawing and embeds one bitmap produces a PDF that
  opens, prints, and looks right until it is zoomed.

The comparison is on invariants rather than bytes.  Two renderers reached through
different hosts will not produce byte-identical output -- a PDF alone carries a
creation timestamp -- so what has to match is the geometry, the structure, and the
per-format invariants.

Both sides start from :func:`tools.diagram_contract_support.sample_diagram`, so
the input is the same object rather than two fixtures that are meant to be alike.

Run it directly, or through ``make diagram_browser_headless_check``::

    $ python tools/check_diagram_browser_headless.py --all-cases \\
          --formats svg,png,pdf
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.diagram_contract_support import (  # noqa: E402
    sample_diagram,
    write_sample_html,
)

VIEWER_CHECK = ROOT / "tools" / "diagram_assets" / "check_viewer_browser.js"

#: Scale the viewer's PNG download uses.  It is fixed in the browser component
#: rather than configurable, so the synchronous side has to match it explicitly to
#: compare like with like.
BROWSER_PNG_SCALE = 2

#: Locale and direction combinations to compare.  The first is the default; the
#: rest exist because a locale reaching one path and not the other is exactly the
#: divergence this command was written for.
ALL_CASES = (
    ("default", "sc", "TB"),
    ("cjk-jp", "jp", "LR"),
    ("cjk-kr", "kr", "TB"),
)


def run_browser(html: Path, formats: Tuple[str, ...]) -> Dict[str, Any]:
    """
    Drive the browser export and return its structured report.

    :param html: Standalone viewer document to open.
    :type html: pathlib.Path
    :param formats: Formats the browser should export.
    :type formats: tuple[str, ...]
    :return: The report the browser check prints.
    :rtype: dict
    :raises SystemExit: If Node is unavailable, or the browser check fails or
        prints something that is not a report.
    """
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node.js is required to drive the browser export")
    environment = dict(os.environ)
    environment["VIEWER_FORMATS"] = ",".join(sorted(formats))
    environment["VIEWER_REQUIRE_PDF_ZERO_IMAGES"] = "1"
    environment["VIEWER_REQUIRE_PDF_PAGE_SIZE"] = "1"
    completed = subprocess.run(
        [node, str(VIEWER_CHECK), str(html)],
        capture_output=True,
        text=True,
        env=environment,
    )
    # The report is one pretty-printed object spanning the whole of stdout, so it
    # is parsed as a whole rather than looked for line by line.
    report = None
    text = completed.stdout.strip()
    start = text.find("{")
    if start >= 0:
        try:
            report = json.loads(text[start:])
        except ValueError:
            report = None
    if completed.returncode != 0 or report is None:
        raise SystemExit(
            "the browser export check failed (exit %d); last stderr:\n%s"
            % (completed.returncode, completed.stderr[-2000:])
        )
    return report


def headless_facts(
    cjk_locale: str, direction: str, formats: Tuple[str, ...]
) -> Dict[str, Any]:
    """
    Export the same diagram synchronously and describe the result.

    :param cjk_locale: CJK locale for the shared fixture.
    :type cjk_locale: str
    :param direction: Layout direction for the shared fixture.
    :type direction: str
    :param formats: Formats to export.
    :type formats: tuple[str, ...]
    :return: The same facts the browser report carries, measured here.
    :rtype: dict
    """
    view = sample_diagram(cjk_locale=cjk_locale, direction=direction)
    facts: Dict[str, Any] = {}
    if "svg" in formats:
        svg = view.to_svg()
        facts["svgText"] = len(re.findall(r"<text\b", svg))
        facts["svgMarker"] = len(re.findall(r"<marker\b", svg))
        facts["svgFontFamily"] = len(re.findall(r"font-family[=:]", svg))
        box = re.search(r'\bviewBox="\s*0\s+0\s+([\d.]+)\s+([\d.]+)', svg)
        if box is not None:
            facts["viewBox"] = (round(float(box.group(1))), round(float(box.group(2))))
        facts["fills"] = sorted(set(re.findall(r'fill="(#[0-9a-fA-F]{3,6})"', svg)))
    if "png" in formats:
        # The viewer's download button rasterises at a fixed 2x, while
        # ``to_png()`` defaults to 1x. Comparing the two defaults would report a
        # factor-of-two "disagreement" that is really two different requests, so
        # the comparison is made at the scale the browser actually uses.
        png = view.to_png(scale=BROWSER_PNG_SCALE)
        facts["pngWidth"], facts["pngHeight"] = _png_size(png)
    if "pdf" in formats:
        pdf = view.to_pdf()
        facts["pdfPages"] = len(re.findall(rb"/Type\s*/Page\b", pdf))
        facts["pdfImages"] = len(re.findall(rb"/Subtype\s*/Image\b|/ImageMask\b", pdf))
        box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
        if box is not None:
            facts["pdfPage"] = (
                round(float(box.group(1))),
                round(float(box.group(2))),
            )
    return facts


def _png_size(data: bytes) -> Tuple[int, int]:
    """
    Read a PNG's declared dimensions.

    :param data: PNG bytes.
    :type data: bytes
    :return: Width and height in pixels.
    :rtype: tuple[int, int]
    :raises SystemExit: If the payload is not a PNG.
    """
    import struct

    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        raise SystemExit("the synchronous export produced something that is not a PNG")
    return struct.unpack(">II", data[16:24])


def compare(browser: Dict[str, Any], headless: Dict[str, Any], label: str) -> List[str]:
    """
    List every invariant the two paths disagree on.

    :param browser: Report from the browser export.
    :type browser: dict
    :param headless: Facts measured from the synchronous export.
    :type headless: dict
    :param label: Case name, used in the messages.
    :type label: str
    :return: Human-readable disagreements, empty when the two agree.
    :rtype: list[str]
    """
    problems = []
    # The browser check reports its export facts under ``pdf``, not at the root of
    # the report. Reading them from the root made every cross-path comparison
    # below compare ``None`` against a real number and skip -- the gate passed on
    # the strength of the per-side assertions alone, which is the failure mode
    # this file's own docstring warns about.
    facts = browser.get("pdf")
    if not isinstance(facts, dict):
        return [
            "%s: the browser report carries no export facts, so nothing was "
            "compared" % label
        ]
    browser = facts

    def note(what, left, right):
        problems.append(
            "%s: %s is %r in the browser export but %r in the synchronous one"
            % (label, what, left, right)
        )

    for key in ("svgText", "svgMarker", "svgFontFamily"):
        if key not in headless:
            continue
        if key not in browser:
            problems.append(
                "%s: the browser report has no %s, so that comparison did not run"
                % (label, key)
            )
            continue
        if browser[key] != headless[key]:
            note(key, browser[key], headless[key])
    # Both exports must be the expanded form. Equal-but-wrong would pass the
    # comparison above, so the absolute requirement is stated too.
    for side, facts in (("browser", browser), ("synchronous", headless)):
        for key in ("svgText", "svgMarker", "svgFontFamily"):
            if facts.get(key):
                problems.append(
                    "%s: the %s export carries %d %s, so it is not the expanded form"
                    % (label, side, facts[key], key)
                )
    if "pdfPage" in headless:
        # The browser reports the page it produced as two numbers; the page has to
        # be the same size on both paths or the drawings are not the same drawing.
        width, height = browser.get("pdfWidth"), browser.get("pdfHeight")
        if width and height:
            theirs = (round(float(width)), round(float(height)))
            if theirs != tuple(headless["pdfPage"]):
                note("the PDF page size", theirs, headless["pdfPage"])
    if "pngWidth" in headless:
        for key, mine in (("pngWidth", "pngWidth"), ("pngHeight", "pngHeight")):
            theirs = browser.get(key)
            if theirs and int(theirs) != int(headless[mine]):
                note(key, theirs, headless[mine])
    if "pdfPages" in headless:
        if browser.get("pages") and int(browser["pages"]) != int(headless["pdfPages"]):
            note("the PDF page count", browser["pages"], headless["pdfPages"])
        if headless["pdfImages"]:
            problems.append(
                "%s: the synchronous PDF carries %d image object(s), so the drawing "
                "was rasterised" % (label, headless["pdfImages"])
            )
        if browser.get("images"):
            problems.append(
                "%s: the browser PDF carries %s image object(s)"
                % (label, browser["images"])
            )
    return problems


def main(argv=None) -> int:
    """
    Compare the two export paths over the selected cases.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int
    :raises SystemExit: If the two paths disagree on any invariant.
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--all-cases", action="store_true")
    parser.add_argument("--formats", default="svg,png,pdf")
    arguments = parser.parse_args(argv)
    formats = tuple(
        item.strip() for item in arguments.formats.split(",") if item.strip()
    )
    if not formats or any(item not in {"svg", "png", "pdf"} for item in formats):
        raise SystemExit("--formats must contain only svg,png,pdf")

    cases = ALL_CASES if arguments.all_cases else ALL_CASES[:1]
    problems: List[str] = []
    compared = 0
    with tempfile.TemporaryDirectory(prefix="pyfcstm-parity-") as directory:
        for label, locale, direction in cases:
            html = Path(directory) / (label + ".html")
            write_sample_html(html, cjk_locale=locale, direction=direction)
            browser = run_browser(html, formats)
            headless = headless_facts(locale, direction, formats)
            problems.extend(compare(browser, headless, label))
            compared += 1
    if problems:
        raise SystemExit(
            "the two export paths disagree:\n  " + "\n  ".join(problems)
        )
    print(
        json.dumps(
            {"cases": compared, "formats": list(formats), "agree": True},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
