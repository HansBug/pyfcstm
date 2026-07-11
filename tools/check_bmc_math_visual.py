#!/usr/bin/env python3
"""Visually verify rendered BMC mathematics with a pinned Playwright."""

from __future__ import annotations

import argparse
import json
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from playwright.sync_api import sync_playwright


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
    if len(all_anchors) != 40:
        errors.append(
            "expected 40 distinct equation anchors across rendered pages, found %d"
            % len(all_anchors)
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
