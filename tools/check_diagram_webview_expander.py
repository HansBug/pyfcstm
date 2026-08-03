"""
Check that the editor preview can outline its own drawing.

The preview webview has the diagram on screen but no fonts and no rasteriser, so
its SVG download used to hand over a document whose text depended on fonts the
reader might not have.  Shipping the outliner would add 17.7 MB to the extension
for one CJK locale, or 59.4 MB for all of them, so the extension asks an
installed ``pyfcstm[viz]`` instead.

Two properties make that safe, and neither is visible from either side alone:

* the extension expands *the document the webview produced*, not a re-render
  from the ``.fcstm`` source.  Re-rendering returns a perfectly valid file in the
  default palette, silently discarding the palette and colour mode the user
  chose -- a wrong-colour export that every structural assertion waves through;
* with nothing usable installed, the export says so.  A fallback to the
  unexpanded document would be the original defect wearing a success message.

The Python tests may not read the editor tree and the jsfcstm tests may not read
the Python one, so this comparison lives outside both.

Run it directly, or through ``make diagram_webview_expander_check``::

    $ python tools/check_diagram_webview_expander.py
    diagram webview expander: expanded 3422 -> 9457 bytes, 7 colours preserved
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
from typing import Dict, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
VSCODE_DIR = ROOT / "editors" / "vscode"
EXPANDER_JS = VSCODE_DIR / "out" / "pyfcstm-expander.js"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: A palette that is not the default, so a re-render would produce visibly
#: different colours from the document handed in.
PALETTE = "nord"
MODE = "dark"

MACHINE = "state Root { state A; state B; [*] -> A; A -> B :: Go; }"

VSCODE_STUB = """
module.exports = {
  workspace: {
    getConfiguration: () => ({get: () => process.env.PYFCSTM_EXPANDER_PATH || ''}),
    onDidChangeConfiguration: () => ({dispose() {}}),
  },
};
"""

PROBE_JS = """
const Module = require('module');
const original = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (request === 'vscode') return require.resolve(process.env.PYFCSTM_VSCODE_STUB);
  return original.call(this, request, ...rest);
};
const fs = require('fs');
const {resolveExpander, expandSvg} = require(process.env.PYFCSTM_EXPANDER_JS);
(async () => {
  const resolution = await resolveExpander(true);
  const canonical = fs.readFileSync(process.env.PYFCSTM_CANONICAL_SVG, 'utf8');
  if (!resolution.command) {
    // Asking anyway is the point: a fallback that returns the document it was
    // handed lives inside `expandSvg`, where a check that only reads the
    // resolution would never see it.
    let refused = false;
    let detail = resolution.detail;
    try {
      await expandSvg(canonical);
    } catch (error) {
      refused = true;
      detail = String(error && error.message || error);
    }
    console.log(JSON.stringify({resolved: false, refused, detail}));
    return;
  }
  try {
    const expanded = await expandSvg(canonical);
    console.log(JSON.stringify({resolved: true, command: resolution.command, expanded}));
  } catch (error) {
    console.log(JSON.stringify({resolved: true, command: resolution.command, error: String(error && error.message || error)}));
  }
})().catch(error => {
  console.log(JSON.stringify({fatal: String(error && error.message || error)}));
});
"""


def fills(svg: str) -> Set[str]:
    """
    Collect every fill colour a document paints with.

    :param svg: SVG text.
    :type svg: str
    :return: The distinct ``fill`` values.
    :rtype: set[str]

    Example::

        >>> sorted(fills('<path fill="#abc"/><path fill="#abc"/><rect fill="red"/>'))
        ['#abc', 'red']
    """
    return set(re.findall(r'fill="([^"]+)"', svg))


def palette_colours(svg: str) -> Set[str]:
    """
    Collect the hex fills, which are the ones a palette decides.

    Only hex values: ``none`` and ``transparent`` are not colours, and resvg
    normalises ``rgba(...)`` away during expansion, so including either turns
    "the palette survived" into a comparison two unrelated documents can pass.

    :param svg: SVG text.
    :type svg: str
    :return: The distinct hex ``fill`` values, lowercased.
    :rtype: set[str]

    Example::

        >>> sorted(palette_colours('<path fill="#2E3440"/><path fill="none"/>'))
        ['#2e3440']
    """
    return {
        value.lower() for value in fills(svg) if re.match(r"^#[0-9a-fA-F]{3,8}$", value)
    }


def canonical_svg(palette: str = PALETTE, mode: str = MODE) -> str:
    """
    Render the canonical SVG the webview would be holding.

    :param palette: Palette identifier.
    :type palette: str
    :param mode: Colour mode.
    :type mode: str
    :return: Canonical SVG text, with ``<text>`` still present.
    :rtype: str
    :raises SystemExit: If the optional rendering runtime is unavailable.
    """
    from pyfcstm.diagram import DiagramUnavailableError
    from pyfcstm.diagram.engine import DiagramAssetEngine
    from pyfcstm.model import load_state_machine_from_text

    view = load_state_machine_from_text(MACHINE).diagram()
    try:
        engine = DiagramAssetEngine()
    except DiagramUnavailableError as err:
        raise SystemExit("the optional rendering runtime is required here: %s" % err)
    return engine.render_svg(
        {
            "diagram": view.to_dict(),
            "options": view.options.to_dict(),
            "palette": palette,
            "mode": mode,
            "cjkLocale": None,
        }
    )


def run_probe(canonical: str, path_override: Optional[str] = None) -> Dict:
    """
    Drive the extension's expander in a real subprocess.

    ``path_override`` sets the ``pyfcstmPath`` setting.  Naming something that
    does not exist is how the absent-runtime half is exercised: an explicit
    setting is used or reported rather than replaced by a guess, so the
    candidate list is not consulted and ``PATH`` can stay intact -- emptying it
    would hide ``node`` as well and test nothing.

    :param canonical: Canonical SVG to expand.
    :type canonical: str
    :param path_override: Value for the ``pyfcstmPath`` setting, or ``None`` to
        let the extension search its candidates.
    :type path_override: str, optional
    :return: The probe's decoded report.
    :rtype: dict
    :raises SystemExit: If the probe could not be run or did not report.
    """
    if not EXPANDER_JS.is_file():
        raise SystemExit(
            "%s is missing; run `npm run compile:tsc` in editors/vscode first"
            % EXPANDER_JS
        )
    with tempfile.TemporaryDirectory(prefix="pyfcstm-expander-check-") as directory:
        root = Path(directory)
        stub = root / "vscode-stub.js"
        stub.write_text(VSCODE_STUB, encoding="utf-8")
        probe = root / "probe.js"
        probe.write_text(PROBE_JS, encoding="utf-8")
        source = root / "canonical.svg"
        source.write_text(canonical, encoding="utf-8")
        environment = dict(os.environ)
        environment.update(
            {
                "PYFCSTM_VSCODE_STUB": str(stub),
                "PYFCSTM_EXPANDER_JS": str(EXPANDER_JS),
                "PYFCSTM_CANONICAL_SVG": str(source),
            }
        )
        environment["PYFCSTM_EXPANDER_PATH"] = path_override or ""
        completed = subprocess.run(
            ["node", str(probe)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=environment,
        )
    line = (completed.stdout or "").strip().splitlines()
    if not line:
        raise SystemExit(
            "the expander probe reported nothing (exit %d)\n%s"
            % (completed.returncode, (completed.stderr or "")[-2000:])
        )
    return json.loads(line[-1])


def check() -> None:
    """
    Expand a real document and require the two properties that make it safe.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If expansion fails, loses the caller's colours, or if a
        host with nothing installed does not say so.
    """
    canonical = canonical_svg()
    if not re.findall(r"<text\b", canonical):
        raise SystemExit(
            "the canonical document has no text, so expanding it would prove nothing"
        )

    report = run_probe(canonical)
    if report.get("fatal"):
        raise SystemExit("the expander probe failed: %s" % report["fatal"])
    if not report.get("resolved"):
        raise SystemExit(
            "no installed pyfcstm with expand-svg was reachable from this "
            "environment, so the editor preview could not outline its text here: %s"
            % report.get("detail")
        )
    if report.get("error"):
        raise SystemExit("the expander returned an error: %s" % report["error"])

    expanded = report["expanded"]
    problems = []
    if re.findall(r"<text\b", expanded):
        problems.append("the expanded document still carries <text>")
    if re.findall(r"font-family[=:]", expanded):
        problems.append("the expanded document still names a font family")
    if not re.findall(r"<path\b", expanded):
        problems.append("the expanded document has no paths")
    wanted = palette_colours(canonical)
    got = palette_colours(expanded)
    if not wanted:
        raise SystemExit(
            "the canonical document paints no palette colour, so this check "
            "cannot tell an expansion from a re-render"
        )
    # Every one of them, not merely one: a re-render in another palette still
    # shares the odd colour, so "some overlap survived" passes for a document
    # that is correctly expanded and entirely the wrong colour. Expansion adds
    # black for the glyph outlines and drops nothing, so this is exact.
    lost = sorted(wanted - got)
    if lost:
        problems.append(
            "the drawing was re-rendered rather than expanded: %d of the %d "
            "palette colours are gone (%s)" % (len(lost), len(wanted), ", ".join(lost))
        )
    preserved = wanted & got
    if problems:
        raise SystemExit(
            "the editor preview's expander is wrong:\n  " + "\n  ".join(problems)
        )

    # And the other half: a host with nothing usable has to say so rather than
    # return the document it was handed.
    empty = run_probe(canonical, str(ROOT / "no-such-pyfcstm"))
    if empty.get("resolved"):
        raise SystemExit(
            "a host with no installed pyfcstm still resolved a command: %r"
            % (empty.get("command"),)
        )
    if not empty.get("refused"):
        # The failure this half exists for: expanding "succeeds" by returning the
        # canonical document, and the user downloads a file whose text depends on
        # fonts the reader may not have -- with no error anywhere.
        raise SystemExit(
            "a host with no installed pyfcstm did not refuse to expand; it "
            "returned something instead of reporting that it cannot"
        )
    if not empty.get("detail"):
        raise SystemExit("a host with no installed pyfcstm reported no reason")

    print(
        "diagram webview expander: expanded %d -> %d bytes, %d colours preserved, "
        "absence reported" % (len(canonical), len(expanded), len(preserved))
    )


def _self_check() -> None:
    """
    Prove this command's own assertions can fail.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If a wrong document is accepted as a right one.
    """
    canonical = (
        '<svg><text x="1">A</text><rect fill="#2e3440"/><rect fill="#81a1c1"/></svg>'
    )
    cases = (
        (
            "a document that kept its text",
            '<svg><text>A</text><path fill="#2e3440"/></svg>',
        ),
        (
            "a document that kept its fonts",
            '<svg><path font-family="X" fill="#2e3440"/></svg>',
        ),
        ("a document with no paths", '<svg><rect fill="#2e3440"/></svg>'),
        # The wrong-colour export: correctly expanded, entirely re-rendered.
        ("a re-render in another palette", '<svg><path fill="#183b61"/></svg>'),
        # And the shape that a "some overlap survived" test lets through: a
        # re-render that happens to share one colour with the original.
        (
            "a re-render sharing one colour",
            '<svg><path fill="#2e3440"/><path fill="#183b61"/></svg>',
        ),
    )
    for label, expanded in cases:
        problems = []
        if re.findall(r"<text\b", expanded):
            problems.append("text")
        if re.findall(r"font-family[=:]", expanded):
            problems.append("font")
        if not re.findall(r"<path\b", expanded):
            problems.append("paths")
        if palette_colours(canonical) - palette_colours(expanded):
            problems.append("colours")
        if not problems:
            raise SystemExit("the expansion check accepted %s" % label)
    # Every palette colour, plus the black expansion adds for glyph outlines.
    good = (
        '<svg><path fill="#2e3440"/><path fill="#81a1c1"/><path fill="#000000"/></svg>'
    )
    if re.findall(r"<text\b", good) or (
        palette_colours(canonical) - palette_colours(good)
    ):
        raise SystemExit("the expansion check rejected a correct document")
    if shutil.which("node") is None:
        raise SystemExit("node is required to run this check")
    print("diagram webview expander: self-check passed")


def main(argv=None) -> int:
    """
    Run the expander check, or this command's own self-check.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int

    Example::

        $ python tools/check_diagram_webview_expander.py --check
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="run this command's own self-check"
    )
    arguments = parser.parse_args(argv)
    if arguments.check:
        _self_check()
        return 0
    check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
