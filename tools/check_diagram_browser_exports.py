"""Run the normal standalone browser export smoke for representative cases."""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_contract_support import write_sample_html  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-cases", action="store_true")
    parser.add_argument("--formats", default="svg,png,pdf")
    parser.add_argument("--zero-network", action="store_true")
    parser.add_argument("--pdf-require-zero-images", action="store_true")
    parser.add_argument("--pdf-page-size-match", action="store_true")
    parser.add_argument("--pdf-rerender", action="store_true")
    args = parser.parse_args()
    formats = {item.strip() for item in args.formats.split(",") if item.strip()}
    if not formats.issubset({"svg", "png", "pdf"}) or not formats:
        raise SystemExit("--formats must contain only svg,png,pdf")
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node.js is required for the browser export gate")

    cases = [("default", "sc", "TB")]
    if args.all_cases:
        cases.extend(
            [
                ("cjk-tc", "tc", "TB"),
                ("cjk-hk", "hk", "LR"),
                ("cjk-jp", "jp", "LR"),
                ("cjk-kr", "kr", "TB"),
            ]
        )
    viewports = ["800x600"]
    if args.all_cases:
        viewports = ["800x600", "320x480", "750x900", "1365x768"]
    with tempfile.TemporaryDirectory(prefix="pyfcstm-diagram-browser-") as directory:
        for name, locale, direction in cases:
            html_path = Path(directory) / (name + ".html")
            write_sample_html(html_path, cjk_locale=locale, direction=direction)
            for viewport in viewports:
                env = dict(os.environ)
                env["VIEWER_REQUIRE_EXPANDED_SVG"] = "1"
                env["VIEWER_VIEWPORT"] = viewport
                env["VIEWER_FORMATS"] = ",".join(sorted(formats))
                env["VIEWER_REQUIRE_ZERO_NETWORK"] = "1" if args.zero_network else "0"
                env["VIEWER_REQUIRE_PDF_ZERO_IMAGES"] = (
                    "1" if args.pdf_require_zero_images else "0"
                )
                env["VIEWER_REQUIRE_PDF_PAGE_SIZE"] = (
                    "1" if args.pdf_page_size_match else "0"
                )
                env["VIEWER_REQUIRE_PDF_RERENDER"] = "1" if args.pdf_rerender else "0"
                subprocess.run(
                    [
                        node,
                        str(
                            ROOT
                            / "tools"
                            / "diagram_assets"
                            / "check_viewer_browser.js"
                        ),
                        str(html_path),
                    ],
                    check=True,
                    cwd=str(ROOT),
                    env=env,
                )
    print(
        "diagram browser exports: %d cases x %d viewports passed"
        % (len(cases), len(viewports))
    )


if __name__ == "__main__":
    main()
