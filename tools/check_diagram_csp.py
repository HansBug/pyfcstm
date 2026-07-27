"""Check the ordinary standalone HTML CSP and embedded-resource contract."""

import argparse
import base64
import hashlib
from pathlib import Path
import re
import sys
from typing import List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_contract_support import sample_diagram  # noqa: E402


def _check_style_sources(html: str, policy: str, styles: List[str]) -> None:
    """
    Pin the exact contents of ``style-src``.

    The component library renders its stylesheets at runtime, so the policy
    carries a nonce in addition to the hash of the static stylesheet. A nonce
    matches ``<link rel=stylesheet>`` from any origin, which a hash-only list
    made structurally impossible, so the source list is worth pinning: only the
    hashes of the styles actually embedded here plus exactly one nonce, and that
    nonce must be the one the bootstrap publishes. Without this, widening the
    directive to ``'unsafe-inline'`` or a host source, or letting the policy and
    the bootstrap drift apart, leaves every other check passing.

    ``style-src-elem`` is checked too: when present it *overrides* ``style-src``
    for ``<style>`` and ``<link rel=stylesheet>``, so a widening moved there
    takes effect while ``style-src`` itself stays perfectly pinned.
    """
    matches = re.findall(r"(?:^|;)\s*style-src\s+([^;]*)", policy)
    if not matches:
        raise SystemExit("CSP has no style-src directive")
    if len(matches) != 1:
        # A duplicate directive is ignored by user agents, but it means the
        # policy no longer says one thing, and this check would only ever see
        # the first copy.
        raise SystemExit(
            "CSP declares style-src %d times; it must appear exactly once"
            % len(matches)
        )
    for directive in ("style-src-elem", "script-src-elem"):
        overriding = re.findall(r"(?:^|;)\s*%s\s+([^;]*)" % directive, policy)
        if overriding:
            raise SystemExit(
                "CSP declares %s, which overrides its base directive for the "
                "very elements these checks pin: %s"
                % (directive, "; ".join(overriding))
            )
    # The -attr directives are pinned to 'none' by the producer; anything else
    # re-enables inline style and event-handler attributes.
    for directive in ("style-src-attr", "script-src-attr"):
        values = re.findall(r"(?:^|;)\s*%s\s+([^;]*)" % directive, policy)
        if values != ["'none'"]:
            raise SystemExit(
                "CSP must declare %s exactly once as 'none', found %s"
                % (directive, values or "nothing")
            )
    sources = matches[0].split()
    expected_hashes = {
        "'sha256-%s'"
        % base64.b64encode(hashlib.sha256(style.encode("utf-8")).digest()).decode(
            "ascii"
        )
        for style in styles
    }
    nonces = [item for item in sources if item.startswith("'nonce-")]
    if len(nonces) != 1:
        raise SystemExit(
            "style-src must carry exactly one nonce, found %d" % len(nonces)
        )
    unexpected = [
        item for item in sources if item not in expected_hashes and item not in nonces
    ]
    if unexpected:
        raise SystemExit(
            "style-src carries sources beyond the embedded style hashes and its "
            "nonce: %s" % ", ".join(unexpected)
        )
    declared = nonces[0][len("'nonce-") : -1]
    # All occurrences, not the first: the last assignment is what the runtime
    # ends up with, so checking only the first would validate a value the
    # browser never sees.
    published = re.findall(r"window\.__FCSTM_STYLE_NONCE__ = \"([^\"]*)\";", html)
    if not published:
        raise SystemExit("standalone HTML does not publish a style nonce")
    if len(set(published)) != 1:
        raise SystemExit(
            "standalone HTML publishes %d different style nonces: %s"
            % (len(set(published)), ", ".join(sorted(set(published))))
        )
    if published[0] != declared:
        raise SystemExit(
            "style-src nonce %r does not match the published nonce %r"
            % (declared, published[0])
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-default-none", action="store_true")
    parser.add_argument("--require-connect-none", action="store_true")
    parser.add_argument("--require-worker-none", action="store_true")
    parser.add_argument("--require-script-hashes", action="store_true")
    parser.add_argument("--require-style-hashes", action="store_true")
    parser.add_argument("--require-style-nonce", action="store_true")
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
        r"(?:^|[\s;])'unsafe-eval'(?:$|[\s;])", policy
    ):
        raise SystemExit("CSP enables JavaScript unsafe-eval")
    if args.zero_network and re.search(
        r'(?:src|href)\s*=\s*["\']?(?:https?:)?//', html, re.IGNORECASE
    ):
        raise SystemExit("standalone HTML contains a remote resource")
    scripts = re.findall(
        r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE
    )
    if args.require_script_hashes:
        for script in scripts:
            digest = base64.b64encode(
                hashlib.sha256(script.encode("utf-8")).digest()
            ).decode("ascii")
            if "sha256-%s" % digest not in policy:
                raise SystemExit("CSP script hash does not match embedded script")
    # Match attributes too: a `<style nonce="...">` block is accepted by the
    # policy but was invisible to the hash check, which is the one shape the
    # nonce makes newly loadable. Script bodies are removed first because the
    # bundled component library's source contains a `<style cssr-id="...">`
    # template literal, and that string is not a stylesheet in this document.
    markup = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    styles = re.findall(r"<style[^>]*>(.*?)</style>", markup, re.DOTALL | re.IGNORECASE)
    if args.require_style_hashes:
        if not styles:
            raise SystemExit("standalone HTML has no inline style block")
        for style in styles:
            digest = base64.b64encode(
                hashlib.sha256(style.encode("utf-8")).digest()
            ).decode("ascii")
            if "sha256-%s" % digest not in policy:
                raise SystemExit("CSP style hash does not match embedded style")
    if args.require_style_nonce:
        _check_style_sources(html, policy, styles)
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
