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

#: Locale and direction combinations compared on top of the corpus.  A locale
#: reaching one path and not the other is the divergence this command was written
#: for, and the corpus fixtures do not vary the locale.
LOCALE_CASES = (
    ("locale-sc", "sc", "TB"),
    ("locale-jp", "jp", "LR"),
    ("locale-kr", "kr", "TB"),
)

#: The canonical corpus, which is what the frozen acceptance names.  The two files
#: carry 35 layouts and 306 arrows between them, derived from the visual fixtures
#: the geometry work was built on.
CORPUS_FILES = (
    ROOT / "tools" / "diagram_assets" / "corpus" / "shared-layouts.json",
    ROOT / "tools" / "diagram_assets" / "corpus" / "canonical-arrows.json",
)

#: Where each corpus case's source lives.  The corpus records the directory in its
#: own ``provenance.source``; this constant follows it rather than guessing.
FIXTURE_DIR = ROOT / "editors" / "jsfcstm" / "test" / "fixtures" / "visual"


def load_corpus() -> List[Dict[str, Any]]:
    """
    Read every corpus case together with the source it was built from.

    Both export paths are driven from the same public entry point --
    ``load_state_machine_from_file(...).diagram(...)`` -- rather than from two
    fixtures meant to be alike, so a divergence cannot be an artefact of the
    inputs differing.

    :return: One record per case, carrying its id, arrow count, source path and
        the renderer options the corpus recorded.
    :rtype: list[dict]
    :raises SystemExit: If a corpus file or a case's source cannot be found.
    """
    records = []
    for path in CORPUS_FILES:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cases = payload["cases"]
        except (KeyError, OSError, TypeError, ValueError) as err:
            # KeyError/TypeError: no ``cases`` array. OSError/ValueError: the file
            # cannot be read or is not JSON.
            raise SystemExit("cannot read the canonical corpus: %s" % path) from err
        for case in cases:
            fixture = FIXTURE_DIR / ("%s.fcstm" % case["sourceFixture"])
            if not fixture.is_file():
                raise SystemExit(
                    "corpus case %s names a source that is not there: %s"
                    % (case.get("id"), fixture)
                )
            request = case.get("request") or {}
            records.append(
                {
                    "id": case["id"],
                    "arrows": int(case.get("arrows") or 0),
                    "fixture": fixture,
                    "direction": (request.get("options") or {}).get("direction", "TB"),
                    "palette": request.get("palette", "default"),
                    "mode": request.get("mode", "light"),
                    "cjkLocale": request.get("cjkLocale", "sc"),
                }
            )
    return records


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
    # The interaction and panel assertions in that check describe its own fixture,
    # and an arbitrary corpus layout fails them for reasons unrelated to the
    # export: a leaf-only machine has no transition to hover. Those assertions are
    # covered by `make diagram_browser_check`; what matters here is the export.
    environment["VIEWER_EXPORT_ONLY"] = "1"
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


def headless_facts(view, formats: Tuple[str, ...]) -> Dict[str, Any]:
    """
    Export one diagram synchronously and describe the result.

    :param view: The same snapshot the browser side is given.
    :type view: pyfcstm.diagram.api.Diagram
    :param formats: Formats to export.
    :type formats: tuple[str, ...]
    :return: The same facts the browser report carries, measured here.
    :rtype: dict
    """
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
        # A missing number is a failure rather than a skip: silently passing when
        # the report shape changes is how the whole comparison went dead once.
        width, height = browser.get("pdfWidth"), browser.get("pdfHeight")
        if not width or not height:
            problems.append(
                "%s: the browser report gives no PDF page size, so that comparison "
                "did not run" % label
            )
        else:
            theirs = (round(float(width)), round(float(height)))
            if theirs != tuple(headless["pdfPage"]):
                note("the PDF page size", theirs, headless["pdfPage"])
    if "pngWidth" in headless:
        for key in ("pngWidth", "pngHeight"):
            theirs = browser.get(key)
            if not theirs:
                problems.append(
                    "%s: the browser report has no %s, so that comparison did not "
                    "run" % (label, key)
                )
                continue
            if int(theirs) != int(headless[key]):
                note(key, theirs, headless[key])
    if "pdfPages" in headless:
        if browser.get("pages") is None:
            problems.append(
                "%s: the browser report has no PDF page count, so that comparison "
                "did not run" % label
            )
        elif int(browser["pages"]) != int(headless["pdfPages"]):
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
    parser.add_argument(
        "--max-cases",
        type=int,
        default=2,
        help="corpus cases to compare when --all-cases is absent",
    )
    parser.add_argument("--formats", default="svg,png,pdf")
    arguments = parser.parse_args(argv)
    formats = tuple(
        item.strip() for item in arguments.formats.split(",") if item.strip()
    )
    if not formats or any(item not in {"svg", "png", "pdf"} for item in formats):
        raise SystemExit("--formats must contain only svg,png,pdf")

    from pyfcstm.dsl.error import GrammarParseError
    from pyfcstm.model import load_state_machine_from_file
    from pyfcstm.utils.validate import ModelValidationError

    corpus = load_corpus()
    # Seven of the corpus fixtures are deliberately invalid machines -- three do
    # not parse and four carry dangling transitions -- because they exist to
    # exercise the renderer and the diagnostics. A user cannot reach them through
    # ``StateMachine.diagram()`` at all, so they are not part of the export surface
    # this command compares. They are reported rather than dropped quietly, and a
    # fixture that stops loading for any other reason is a failure.
    usable, unusable = [], []
    for record in corpus:
        try:
            record["model"] = load_state_machine_from_file(str(record["fixture"]))
        except (GrammarParseError, ModelValidationError) as err:
            unusable.append((record["id"], type(err).__name__))
            continue
        usable.append(record)
    corpus = usable
    if not arguments.all_cases:
        corpus = corpus[: arguments.max_cases]
    problems: List[str] = []
    arrows = 0
    compared = 0
    with tempfile.TemporaryDirectory(prefix="pyfcstm-parity-") as directory:
        for record in corpus:
            model = record["model"]
            view = model.diagram(
                direction=record["direction"],
                palette=record["palette"],
                mode=record["mode"],
                cjk_locale=record["cjkLocale"],
            )
            html = Path(directory) / ("%s.html" % record["id"])
            html.write_text(view.to_html(), encoding="utf-8")
            browser = run_browser(html, formats)
            problems.extend(
                compare(browser, headless_facts(view, formats), record["id"])
            )
            arrows += record["arrows"]
            compared += 1
        if arguments.all_cases:
            # The corpus fixtures never vary the locale, and a locale reaching one
            # path and not the other is exactly what this command exists to catch.
            for label, locale, direction in LOCALE_CASES:
                html = Path(directory) / (label + ".html")
                write_sample_html(html, cjk_locale=locale, direction=direction)
                view = sample_diagram(cjk_locale=locale, direction=direction)
                browser = run_browser(html, formats)
                problems.extend(compare(browser, headless_facts(view, formats), label))
                compared += 1
    if problems:
        raise SystemExit(
            "the two export paths disagree:\n  " + "\n  ".join(problems)
        )
    print(
        json.dumps(
            {
                "cases": compared,
                "layouts": len(corpus),
                "arrows": arrows,
                "notAMachine": sorted(item[0] for item in unusable),
                "formats": list(formats),
                "agree": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
