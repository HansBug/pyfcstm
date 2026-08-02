#!/usr/bin/env python3
"""Visually verify rendered BMC mathematics with a pinned Playwright."""

from __future__ import annotations

import argparse
import ast
import json
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from playwright.sync_api import sync_playwright

_REPO_ROOT = Path(__file__).resolve().parents[1]


_PLAYWRIGHT_VERSION = "1.55.0"
_PAGE_DIRECTORIES = (
    "explanations/bmc_semantics",
    "explanations/bmc_properties",
    "explanations/bmc_solving",
)
_VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}


class VisualCheckFailure(Exception):
    """Raised when rendered mathematical documentation fails visual checks."""


def _rendered_page_relative(language: str, directory: str) -> Path:
    if language == "en":
        filename = "index.html"
    elif language == "zh":
        filename = "index_zh.html"
    else:
        raise VisualCheckFailure("Unsupported documentation language: %s" % language)
    return Path(directory) / filename


def _rendered_pages(
    html_roots: Dict[str, Path],
) -> Iterator[Tuple[str, str, Path]]:
    for language, html_root in sorted(html_roots.items()):
        for directory in _PAGE_DIRECTORIES:
            yield (
                language,
                directory,
                html_root / _rendered_page_relative(language, directory),
            )


def _expected_anchor_count() -> int:
    """Return how many labelled equations the ledger currently declares.

    Read from ``tools/check_bmc_docs.py`` rather than hardcoded here.  The two
    checkers disagreed the first time an equation was added: one enforced the
    label list and the other still expected the previous count, so a correct
    addition failed the visual pass for a reason that had nothing to do with
    rendering.  Deriving the number keeps one place to update.

    :return: The number of frozen equation labels.
    :rtype: int
    :raises VisualCheckFailure: If the label list cannot be read.
    """
    source = _REPO_ROOT / "tools/check_bmc_docs.py"
    try:
        module = ast.parse(source.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as err:
        # OSError: the sibling checker is missing or unreadable.
        # SyntaxError: it is mid-edit; either way the count cannot be trusted.
        raise VisualCheckFailure(
            "cannot read the equation label list from %s: %s" % (source.name, err)
        )
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "_EQUATION_LABELS"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, ast.Tuple):
            return len(node.value.elts)
    raise VisualCheckFailure(
        "%s no longer defines _EQUATION_LABELS as a tuple literal." % source.name
    )


def _check_page_path_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="pyfcstm-bmc-visual-check-") as temp_dir:
        root = Path(temp_dir)
        html_roots = {"en": root / "en", "zh": root / "zh"}
        expected = set()
        for language, html_root in html_roots.items():
            for directory in _PAGE_DIRECTORIES:
                page = html_root / _rendered_page_relative(language, directory)
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text("<html></html>\n", encoding="utf-8")
                expected.add(page)
        selected = {page for _language, _directory, page in _rendered_pages(html_roots)}
        if selected != expected or not all(page.is_file() for page in selected):
            raise VisualCheckFailure(
                "English index.html and Chinese index_zh.html path selection diverged."
            )


def _require_playwright_version() -> None:
    try:
        installed = version("playwright")
    except PackageNotFoundError:
        # PackageNotFoundError: the tools-only visual dependency is absent.
        raise VisualCheckFailure("playwright==%s is required." % _PLAYWRIGHT_VERSION)
    if installed != _PLAYWRIGHT_VERSION:
        raise VisualCheckFailure(
            "playwright==%s is required, found %s." % (_PLAYWRIGHT_VERSION, installed)
        )


def _require_directory(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise VisualCheckFailure("%s is not a directory: %s" % (label, resolved))
    return resolved


def _check_page(page, url: str) -> Dict[str, object]:
    page.goto(url, wait_until="networkidle")
    page.wait_for_selector("mjx-container[display='true']", state="attached")
    page.wait_for_function(
        "document.querySelectorAll(\"mjx-container[display='true']\").length > 0"
    )
    return page.evaluate(
        """
        () => {
          const equations = [...document.querySelectorAll("mjx-container[display='true']")];
          const problems = [...document.querySelectorAll('.problematic')].map(
            (node) => node.textContent || node.outerHTML
          );
          const viewportWidth = document.documentElement.clientWidth;
          const invalid = [];
          equations.forEach((node, index) => {
            const rect = node.getBoundingClientRect();
            if (rect.width <= 1 || rect.height <= 1 || node.innerHTML.trim().length === 0) {
              invalid.push(`equation ${index + 1} is blank`);
            }
            if (rect.left < -1 || rect.right > viewportWidth + 1) {
              invalid.push(`equation ${index + 1} overflows the viewport`);
            }
          });
          const documentOverflow = document.documentElement.scrollWidth > viewportWidth + 1;
          const anchors = [...document.querySelectorAll('[id^="equation-bmc-"]')].map(
            (node) => node.id
          );
          return {
            equation_count: equations.length,
            equation_anchors: anchors,
            problematic: problems,
            invalid,
            document_overflow: documentOverflow,
          };
        }
        """
    )


def _require_text_rendering(page) -> None:
    """Refuse to report a pass when the browser cannot render text.

    A browser with no usable font lays every string out at zero width.  Nothing
    can then overflow, no formula container can be too wide, and every geometric
    check passes while the screenshots contain no glyphs at all -- which is how
    this checker once reported twelve passing pages whose images were blank.

    Point ``FONTCONFIG_FILE`` at a configuration naming a font the browser can
    load if this fires.

    :param page: The page to measure on.
    :type page: playwright.sync_api.Page
    :return: ``None``.
    :rtype: None
    :raises VisualCheckFailure: If a known string measures zero wide.
    """
    measured = page.evaluate(
        """() => {
          const c = document.createElement('canvas').getContext('2d');
          c.font = '32px sans-serif';
          return {latin: c.measureText('HELLO 12345').width,
                  cjk: c.measureText('\u6c42\u89e3\u4e0e\u56de\u653e').width,
                  cjkRef: c.measureText('MMMMM').width};
        }"""
    )
    if not measured["latin"]:
        raise VisualCheckFailure(
            "the browser measures text at zero width, so no visual check here "
            "means anything; set FONTCONFIG_FILE to a config with a loadable font"
        )
    # A missing CJK font does not give zero width -- Chromium draws tofu boxes,
    # which are narrower than real glyphs.  Measured at 95px against 160px here,
    # a 40% error, while the overflow this check exists to catch had 10px of
    # margin.  Five ideographs at 32px are about as wide as five 'M's; well under
    # that means the boxes, not the characters.
    if measured["cjk"] < 0.8 * measured["cjkRef"]:
        raise VisualCheckFailure(
            "the browser has no CJK font -- five ideographs measure %.0fpx "
            "against %.0fpx for five 'M's, so the Chinese pages would be laid "
            "out from tofu-box widths; add a CJK family to FONTCONFIG_FILE"
            % (measured["cjk"], measured["cjkRef"])
        )


def check(
    html_roots: Dict[str, Path],
    output_root: Path,
    browser_executable: Path,
) -> Dict[str, object]:
    """Check both languages at desktop/mobile sizes and write screenshots."""
    _require_playwright_version()
    executable = browser_executable.resolve()
    if not executable.is_file():
        raise VisualCheckFailure("Browser executable does not exist: %s" % executable)
    output_root.mkdir(parents=True, exist_ok=True)
    report: Dict[str, object] = {"playwright": _PLAYWRIGHT_VERSION, "pages": {}}
    errors: List[str] = []
    all_anchors = set()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(executable),
            headless=True,
        )
        for language, html_root in sorted(html_roots.items()):
            language_output = output_root / language
            language_output.mkdir(parents=True, exist_ok=True)
            for viewport_name, viewport in _VIEWPORTS.items():
                context = browser.new_context(viewport=viewport)
                page = context.new_page()
                _require_text_rendering(page)
                for _page_language, directory, html_path in _rendered_pages(
                    {language: html_root}
                ):
                    if not html_path.is_file():
                        errors.append("missing rendered page: %s" % html_path)
                        continue
                    key = "%s/%s/%s/%s" % (
                        language,
                        viewport_name,
                        directory,
                        html_path.name,
                    )
                    facts = _check_page(page, html_path.resolve().as_uri())
                    report["pages"][key] = facts
                    all_anchors.update(facts["equation_anchors"])
                    if facts["problematic"]:
                        errors.append("%s has problematic nodes" % key)
                    if facts["invalid"]:
                        errors.extend(
                            "%s: %s" % (key, item) for item in facts["invalid"]
                        )
                    if facts["document_overflow"]:
                        errors.append("%s has horizontal document overflow" % key)
                    screenshot_name = "%s-%s.png" % (
                        directory.replace("/", "-"),
                        viewport_name,
                    )
                    page.screenshot(
                        path=str(language_output / screenshot_name),
                        full_page=True,
                    )
                context.close()
        browser.close()
    expected_anchors = _expected_anchor_count()
    if len(all_anchors) != expected_anchors:
        errors.append(
            "expected %d distinct equation anchors across rendered pages, found %d"
            % (expected_anchors, len(all_anchors))
        )
    report["equation_anchor_count"] = len(all_anchors)
    report["errors"] = errors
    (output_root / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if errors:
        raise VisualCheckFailure("\n".join(errors))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the visual checker from built English and Chinese HTML roots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--html-root-en", type=Path)
    parser.add_argument("--html-root-zh", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    args = parser.parse_args(argv)
    visual_arguments = (
        args.html_root_en,
        args.html_root_zh,
        args.output_root,
        args.browser_executable,
    )
    if args.check:
        if any(value is not None for value in visual_arguments):
            parser.error("--check cannot be combined with visual-run arguments")
        try:
            _check_page_path_contract()
        except VisualCheckFailure as err:
            print("BMC MathJax visual self-check failed:\n%s" % err)
            return 1
        print("BMC MathJax visual page-path contract is up to date.")
        return 0
    if any(value is None for value in visual_arguments):
        parser.error(
            "--html-root-en, --html-root-zh, --output-root, and "
            "--browser-executable are required"
        )
    html_roots = {
        "en": _require_directory(args.html_root_en, "English HTML root"),
        "zh": _require_directory(args.html_root_zh, "Chinese HTML root"),
    }
    try:
        report = check(html_roots, args.output_root.resolve(), args.browser_executable)
    except VisualCheckFailure as err:
        # VisualCheckFailure: deterministic setup or rendered-page checks failed.
        print("BMC MathJax visual check failed:\n%s" % err)
        return 1
    print(
        "BMC MathJax visual check passed: %d equation anchors; artifacts: %s"
        % (report["equation_anchor_count"], args.output_root.resolve())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
