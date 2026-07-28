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

    Matching is case-insensitive and accepts any whitespace, because directive
    names and keyword sources are ASCII case-insensitive per the CSP grammar and
    browsers honour ``STYLE-SRC-ELEM 'UNSAFE-INLINE'`` exactly as they honour
    the lowercase spelling.
    """
    matches = re.findall(r"(?:^|;)\s*style-src\s+([^;]*)", policy, re.IGNORECASE)
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
        overriding = re.findall(
            r"(?:^|;)\s*%s\s+([^;]*)" % directive, policy, re.IGNORECASE
        )
        if overriding:
            raise SystemExit(
                "CSP declares %s, which overrides its base directive for the "
                "very elements these checks pin: %s"
                % (directive, "; ".join(overriding))
            )
    # The -attr directives are pinned to 'none' by the producer; anything else
    # re-enables inline style and event-handler attributes.
    for directive in ("style-src-attr", "script-src-attr"):
        values = re.findall(
            r"(?:^|;)\s*%s\s+([^;]*)" % directive, policy, re.IGNORECASE
        )
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
    parser.add_argument("--require-no-fallback-directives", action="store_true")
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
    # Every requirement is expressed as an exact source list and checked by
    # parsing the directive out of the policy, not by searching for its text.
    # A substring test passes on `connect-src https://evil; connect-src 'none'`,
    # where a user agent honours the first declaration and ignores the second,
    # and on `connect-src 'none' https://evil`, where the extra source is what
    # takes effect. Both were measured against this gate while only `base-uri`
    # and `form-action` were parsed -- and `connect-src 'none'` is what the
    # zero-network promise rests on, so it mattered more than either.
    required_directives = []
    if args.require_default_none:
        required_directives.append(("default-src", ["'none'"]))
    if args.require_connect_none:
        required_directives.append(("connect-src", ["'none'"]))
    if args.require_worker_none:
        required_directives.append(("worker-src", ["'none'"]))
    if args.require_font_data:
        required_directives.append(("font-src", ["data:"]))
    if args.require_img_data_blob:
        required_directives.append(("img-src", ["data:", "blob:"]))
    if args.require_no_fallback_directives:
        # `base-uri` and `form-action` are the two directives in this policy
        # that do not fall back to `default-src`, so dropping either leaves it
        # entirely unrestricted no matter how strict the rest of the policy is.
        # Without `base-uri 'none'` an injected `<base href>` re-points every
        # relative URL in the document; without `form-action 'none'` a form can
        # post the embedded model source to a remote host. The other `'none'`
        # directives here -- object-src, frame-src, media-src, manifest-src --
        # do fall back, so they are deliberately not required.
        required_directives.append(("base-uri", ["'none'"]))
        required_directives.append(("form-action", ["'none'"]))
    for directive, expected in required_directives:
        declared = re.findall(
            r"(?:^|;)\s*%s\s+([^;]*)" % re.escape(directive), policy, re.IGNORECASE
        )
        if len(declared) != 1:
            raise SystemExit(
                "CSP declares %s %d times; it must appear exactly once"
                % (directive, len(declared))
            )
        if declared[0].split() != expected:
            raise SystemExit(
                "CSP must declare %s as exactly %s, found %r"
                % (directive, " ".join(expected), declared[0].strip())
            )
    if args.require_wasm_unsafe_eval and "wasm-unsafe-eval" not in policy:
        # A source keyword rather than a directive, so it is looked for inside
        # `script-src`, whose full contents are pinned by the hash check.
        raise SystemExit("CSP is missing wasm-unsafe-eval")
    if args.forbid_unsafe_eval and re.search(
        r"(?:^|[\s;])'unsafe-eval'(?:$|[\s;])", policy, re.IGNORECASE
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
    # Name the checks that actually ran. Every assertion here is behind a flag
    # that defaults to off, so a bare `python tools/check_diagram_csp.py` used to
    # print a blanket "zero-network policy passed" while verifying nothing —
    # widening `connect-src` to `*` still exited 0. Reporting the enabled set
    # makes an under-armed invocation visible instead of reassuring.
    performed = [
        name
        for name, enabled in (
            ("default-src 'none'", args.require_default_none),
            ("connect-src 'none'", args.require_connect_none),
            ("worker-src 'none'", args.require_worker_none),
            ("script hashes", args.require_script_hashes),
            ("style hashes", args.require_style_hashes),
            ("style nonce", args.require_style_nonce),
            ("wasm-unsafe-eval", args.require_wasm_unsafe_eval),
            ("base-uri/form-action 'none'", args.require_no_fallback_directives),
            ("no unsafe-eval", args.forbid_unsafe_eval),
            ("font-src data:", args.require_font_data),
            ("img-src data:/blob:", args.require_img_data_blob),
            ("no eval()", args.forbid_eval),
            ("no new Function()", args.forbid_new_function),
            ("zero network", args.zero_network),
            ("embedded fonts", args.require_embedded_fonts is not None),
            ("fonts ready", args.require_fonts_ready),
        )
        if enabled
    ]
    if not performed:
        raise SystemExit(
            "no CSP checks were requested, so nothing was verified; pass the flags "
            "`make diagram_csp_check` uses, or --help to choose them"
        )
    print("diagram CSP: %d checks passed (%s)" % (len(performed), ", ".join(performed)))


if __name__ == "__main__":
    main()
