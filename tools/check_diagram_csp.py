"""Check the ordinary standalone HTML CSP and embedded-resource contract."""

import argparse
import base64
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_contract_support import sample_diagram  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-default-none", action="store_true")
    parser.add_argument("--require-connect-none", action="store_true")
    parser.add_argument("--require-worker-none", action="store_true")
    parser.add_argument("--require-script-hashes", action="store_true")
    parser.add_argument("--require-style-hashes", action="store_true")
    parser.add_argument("--require-wasm-unsafe-eval", action="store_true")
    parser.add_argument("--forbid-unsafe-eval", action="store_true")
    parser.add_argument("--require-font-data", action="store_true")
    parser.add_argument("--require-img-data-blob", action="store_true")
    parser.add_argument("--forbid-eval", action="store_true")
    parser.add_argument("--forbid-new-function", action="store_true")
    parser.add_argument("--zero-network", action="store_true")
    parser.add_argument("--require-embedded-fonts", type=int, default=None)
    parser.add_argument("--require-fonts-ready", action="store_true")
    args = parser.parse_args()
    html = sample_diagram(cjk_locale="jp").to_html()
    match = re.search(
        r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', html
    )
    if match is None:
        raise SystemExit("standalone HTML has no CSP meta tag")
    policy = match.group(1)
    required_directives = []
    if args.require_default_none:
        required_directives.append("default-src 'none'")
    if args.require_connect_none:
        required_directives.append("connect-src 'none'")
    if args.require_worker_none:
        required_directives.append("worker-src 'none'")
    if args.require_font_data:
        required_directives.append("font-src data:")
    if args.require_img_data_blob:
        required_directives.append("img-src data: blob:")
    if args.require_wasm_unsafe_eval:
        required_directives.append("wasm-unsafe-eval")
    for directive in required_directives:
        if directive not in policy:
            raise SystemExit("CSP is missing %s" % directive)
    if args.forbid_unsafe_eval and re.search(
        r"(?:^|[ ;])'unsafe-eval'(?:$|[ ;])", policy
    ):
        raise SystemExit("CSP enables JavaScript unsafe-eval")
    if args.zero_network and re.search(
        r'(?:src|href)=["\']https?://', html, re.IGNORECASE
    ):
        raise SystemExit("standalone HTML contains a remote resource")
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    if args.require_script_hashes:
        for script in scripts:
            digest = base64.b64encode(
                hashlib.sha256(script.encode("utf-8")).digest()
            ).decode("ascii")
            if "sha256-%s" % digest not in policy:
                raise SystemExit("CSP script hash does not match embedded script")
    styles = re.findall(r"<style>(.*?)</style>", html, re.DOTALL)
    if args.require_style_hashes:
        if not styles:
            raise SystemExit("standalone HTML has no inline style block")
        for style in styles:
            digest = base64.b64encode(
                hashlib.sha256(style.encode("utf-8")).digest()
            ).decode("ascii")
            if "sha256-%s" % digest not in policy:
                raise SystemExit("CSP style hash does not match embedded style")
    if args.require_embedded_fonts is not None:
        faces = re.findall(r"@font-face\{", html)
        if len(faces) != args.require_embedded_fonts:
            raise SystemExit(
                "expected %d embedded font faces, found %d"
                % (args.require_embedded_fonts, len(faces))
            )
    if args.forbid_eval or args.forbid_new_function:
        scripts_text = "\n".join(scripts)
        if args.forbid_eval and re.search(r"(?:^|[^.])\beval\s*\(", scripts_text):
            raise SystemExit("standalone HTML contains eval()")
        if args.forbid_new_function and re.search(
            r"\bnew\s+Function\s*\(", scripts_text
        ):
            raise SystemExit("standalone HTML contains new Function()")
    if args.require_fonts_ready:
        scripts_text = "\n".join(scripts)
        # ``document.fonts.ready`` alone settles before any face is requested,
        # so the gate anchors on the explicit per-face load plus the readback
        # that decides whether the viewer degrades.
        for marker, message in (
            ("document.fonts.load", "viewer does not request the embedded font faces"),
            ("document.fonts.check", "viewer does not check embedded font faces"),
        ):
            if marker not in scripts_text:
                raise SystemExit(message)
    print("diagram CSP: embedded scripts, fonts, and zero-network policy passed")


if __name__ == "__main__":
    main()
