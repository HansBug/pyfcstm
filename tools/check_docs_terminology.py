#!/usr/bin/env python3
"""Check Chinese documentation for avoidable English prose terms.

The checker is intentionally conservative: it reports only a bounded list of
ordinary English prose terms that the repository documentation policy says
should normally be translated or introduced with a same-page Chinese/English
handoff. It ignores code blocks, inline literals, roles, directive lines, file
paths, option names, and known product or API names so that command examples and
exact identifiers can stay verbatim.

Example::

    $ python tools/check_docs_terminology.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

DOCS_SOURCE = Path("docs/source")
PRIMARY_ROOTS = (
    DOCS_SOURCE / "tutorials",
    DOCS_SOURCE / "how_to",
    DOCS_SOURCE / "explanations",
    DOCS_SOURCE / "reference",
)
SECONDARY_PAGES = (
    DOCS_SOURCE / "index_zh.rst",
    DOCS_SOURCE / "api_doc_zh.rst",
    DOCS_SOURCE / "release_notes_zh.rst",
)

REJECTED_TERMS = (
    "runtime",
    "renderer",
    "mapping",
    "native",
    "compiler",
    "wrapper",
    "callback",
    "metadata",
    "profile",
    "formatter",
    "smoke test",
    "simulator",
    "alignment",
    "reference",
    "how-to",
    "explanation",
    "workflow",
    "pipeline",
    "output",
    "input",
    "source",
    "target",
    "generated",
    "checked-in",
    "checked",
    "stage",
    "role",
    "roadmap",
    "card",
    "form",
    "fact",
    "prose",
    "landing page",
    "artifact",
    "highlighters",
    "forms",
    "Python-only",
    "module",
    "class",
    "function",
    "data object",
    "inspect report",
    "diagnostics code",
    "visualization option",
    "template config",
    "toctree",
    "speculative rollback",
    "hot-start initialization",
    "event normalization",
    "lifecycle action refs",
    "abstract handler contracts",
    "cycle boundary",
    "semantic fixture corpus",
)

CODE_DIRECTIVES = {
    "code-block",
    "code",
    "literalinclude",
    "parsed-literal",
    "raw",
}

DIRECTIVE_PREFIXES = (
    ".. ",
    ".._",
)

INLINE_LITERAL_RE = re.compile(r"``[^`]*``")
ROLE_RE = re.compile(r":[A-Za-z][A-Za-z0-9_-]*:`[^`]*`")
EXPLICIT_LINK_RE = re.compile(r"`[^`<]*<[^`>]+>`_")
SUBSTITUTION_RE = re.compile(r"\|[^|]+\|")
URL_RE = re.compile(r"https?://\S+")
HANDOFF_RE = re.compile(r"(?<=[\u4e00-\u9fffA-Za-z0-9_）])（[A-Za-z0-9][A-Za-z0-9_+./#\-\s]*）")
KNOWN_LITERAL_PHRASE_RE = re.compile(r"(?<![A-Za-z0-9_])(?:C\+\+ Poll Wrapper|C\+\+ Wrapper)(?![A-Za-z0-9_])")
PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:[./]?[-A-Za-z0-9_]+/)+[-A-Za-z0-9_.*]+")
OPTION_RE = re.compile(r"(?<![A-Za-z0-9_])--?[A-Za-z][A-Za-z0-9_-]*")
TARGET_RE = re.compile(r"(?<![A-Za-z0-9_])_[A-Za-z0-9_-]+:(?![A-Za-z0-9_])")


def _term_pattern(term: str) -> re.Pattern[str]:
    """Create a boundary-aware regular expression for a rejected term.

    :param term: Rejected English term to match.
    :type term: str
    :return: Compiled regular expression that treats non-ASCII text and
        punctuation as boundaries around ASCII words.
    :rtype: re.Pattern[str]

    Example::

        >>> bool(_term_pattern("runtime").search("运行时 runtime。"))
        True
    """

    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(r"(?<![A-Za-z0-9_])" + escaped + r"(?![A-Za-z0-9_])", re.IGNORECASE)


TERM_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = tuple(
    (term, _term_pattern(term)) for term in sorted(REJECTED_TERMS, key=len, reverse=True)
)


@dataclass(frozen=True)
class Finding:
    """Suspicious English prose term found in a Chinese documentation page.

    :param path: Documentation path relative to the repository root.
    :type path: str
    :param line: One-based source line number.
    :type line: int
    :param term: Rejected English term that matched.
    :type term: str
    :param classification: Initial machine classification for reviewers.
    :type classification: str
    :param context: Source line with surrounding whitespace collapsed.
    :type context: str

    Example::

        >>> Finding("docs/source/example_zh.rst", 1, "runtime", "suspicious", "运行时 runtime")
        Finding(path='docs/source/example_zh.rst', line=1, term='runtime', classification='suspicious', context='运行时 runtime')
    """

    path: str
    line: int
    term: str
    classification: str
    context: str

    def format_text(self) -> str:
        """Format the finding as a stable text line.

        :return: ``path:line:term:classification:context`` text.
        :rtype: str

        Example::

            >>> Finding("a.rst", 3, "runtime", "suspicious", "x runtime").format_text()
            'a.rst:3:runtime:suspicious:x runtime'
        """

        return f"{self.path}:{self.line}:{self.term}:{self.classification}:{self.context}"


def default_pages() -> List[Path]:
    """Return the default Chinese documentation pages checked by this tool.

    :return: Primary user-documentation pages plus selected secondary audit
        pages, sorted for deterministic output.
    :rtype: list[pathlib.Path]

    Example::

        >>> pages = default_pages()
        >>> any(str(path).endswith('index_zh.rst') for path in pages)
        True
    """

    pages = []
    for root in PRIMARY_ROOTS:
        pages.extend(root.rglob("*_zh.rst"))
    pages.extend(path for path in SECONDARY_PAGES if path.exists())
    return sorted(dict.fromkeys(pages))


def _directive_name(stripped: str) -> Optional[str]:
    """Extract a reST directive name from a stripped directive line.

    :param stripped: Source line with leading whitespace removed.
    :type stripped: str
    :return: Directive name or ``None`` if the line is not a directive.
    :rtype: str or None
    """

    if not stripped.startswith(".. "):
        return None
    body = stripped[3:].strip()
    if "::" not in body:
        return None
    return body.split("::", 1)[0].split()[0]


def _strip_inline_markup(text: str) -> str:
    """Remove inline markup that is expected to contain exact literals.

    :param text: Source line text.
    :type text: str
    :return: Text with inline literals, roles, links, substitutions, URLs,
        paths, command options, and explicit targets removed.
    :rtype: str
    """

    cleaned = INLINE_LITERAL_RE.sub(" ", text)
    cleaned = ROLE_RE.sub(" ", cleaned)
    cleaned = EXPLICIT_LINK_RE.sub(" ", cleaned)
    cleaned = SUBSTITUTION_RE.sub(" ", cleaned)
    cleaned = HANDOFF_RE.sub(" ", cleaned)
    cleaned = KNOWN_LITERAL_PHRASE_RE.sub(" ", cleaned)
    cleaned = URL_RE.sub(" ", cleaned)
    cleaned = PATH_RE.sub(" ", cleaned)
    cleaned = OPTION_RE.sub(" ", cleaned)
    cleaned = TARGET_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("\\ ", " ")
    return cleaned


def iter_prose_lines(path: Path) -> Iterator[Tuple[int, str, str]]:
    """Yield candidate prose lines from a reST file.

    Code-like directives and their indented bodies are skipped. Ordinary table
    cells, bullet items, and paragraphs remain visible because repository policy
    applies to prose in those locations too.

    :param path: reST page to inspect.
    :type path: pathlib.Path
    :return: Iterator of ``(line_number, original_line, cleaned_line)`` tuples.
    :rtype: collections.abc.Iterator[tuple[int, str, str]]
    """

    lines = path.read_text(encoding="utf-8").splitlines()
    skip_indent: Optional[int] = None
    literal_indent: Optional[int] = None

    for lineno, line in enumerate(lines, 1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if skip_indent is not None:
            if not stripped or indent > skip_indent:
                continue
            skip_indent = None

        if literal_indent is not None:
            if not stripped or indent > literal_indent:
                continue
            literal_indent = None

        if not stripped:
            continue

        directive = _directive_name(stripped)
        if directive is not None:
            if directive in CODE_DIRECTIVES:
                skip_indent = indent
            continue

        if stripped.startswith(DIRECTIVE_PREFIXES):
            continue

        if stripped.startswith(":") and stripped.count(":") >= 2:
            continue

        cleaned = _strip_inline_markup(line)
        if cleaned.rstrip().endswith("::"):
            literal_indent = indent
            cleaned = cleaned.rstrip()[:-2]

        if cleaned.strip():
            yield lineno, line, cleaned


def scan_page(path: Path) -> List[Finding]:
    """Scan a Chinese documentation page for rejected prose terms.

    :param path: Page to scan.
    :type path: pathlib.Path
    :return: Findings in source order.
    :rtype: list[Finding]
    """

    findings: List[Finding] = []
    for lineno, original, cleaned in iter_prose_lines(path):
        for term, pattern in TERM_PATTERNS:
            if pattern.search(cleaned):
                context = " ".join(original.strip().split())
                findings.append(
                    Finding(
                        path=path.as_posix(),
                        line=lineno,
                        term=term,
                        classification="suspicious",
                        context=context,
                    )
                )
    return findings


def scan_pages(paths: Iterable[Path]) -> List[Finding]:
    """Scan multiple pages for rejected prose terms.

    :param paths: Pages to scan.
    :type paths: collections.abc.Iterable[pathlib.Path]
    :return: Sorted findings.
    :rtype: list[Finding]
    """

    findings: List[Finding] = []
    for path in sorted(paths):
        findings.extend(scan_page(path))
    return findings


def _write_self_check_page(directory: Path, name: str, text: str) -> Path:
    """Write a temporary self-check page.

    :param directory: Directory for the temporary page.
    :type directory: pathlib.Path
    :param name: File name to create.
    :type name: str
    :param text: Page content.
    :type text: str
    :return: Path to the written page.
    :rtype: pathlib.Path
    """

    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def _finding_terms(findings: Iterable[Finding]) -> List[str]:
    """Return finding terms in source order.

    :param findings: Findings to summarize.
    :type findings: collections.abc.Iterable[Finding]
    :return: Finding terms.
    :rtype: list[str]
    """

    return [finding.term for finding in findings]


def run_self_check() -> int:
    """Run built-in regression checks for terminology scanning boundaries.

    :return: ``0`` when all regression checks pass, otherwise ``1``.
    :rtype: int

    Example::

        >>> run_self_check() in {0, 1}
        True
    """

    cases = []
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        cases.append(
            (
                "plain prose terms are reported",
                _write_self_check_page(root, "plain_zh.rst", "这是普通 runtime 和 renderer 说明。\n"),
                {"runtime", "renderer"},
            )
        )
        cases.append(
            (
                "simple terminology handoff is ignored",
                _write_self_check_page(root, "handoff_zh.rst", "运行时（runtime）后文只称运行时。\n"),
                set(),
            )
        )
        cases.append(
            (
                "ordinary parenthetical prose is still scanned",
                _write_self_check_page(
                    root,
                    "parenthetical_zh.rst",
                    "这个说明（详见 runtime 与 renderer 章节）没有做术语交接。\n",
                ),
                {"runtime", "renderer"},
            )
        )
        cases.append(
            (
                "csv table visible cells are scanned",
                _write_self_check_page(
                    root,
                    "csv_table_zh.rst",
                    ".. csv-table:: t\n\n   普通 runtime, 普通 renderer\n",
                ),
                {"runtime", "renderer"},
            )
        )
        cases.append(
            (
                "inline literals are ignored",
                _write_self_check_page(root, "literal_zh.rst", "这行包含 ``runtime`` 字面量。\n"),
                set(),
            )
        )
        cases.append(
            (
                "known template titles are ignored as exact names",
                _write_self_check_page(root, "template_title_zh.rst", "标题列保留 C++ Wrapper。\n"),
                set(),
            )
        )

        failed = False
        for label, path, expected_terms in cases:
            terms = set(_finding_terms(scan_page(path)))
            if terms != expected_terms:
                failed = True
                print(
                    f"self-check failed: {label}: expected {sorted(expected_terms)!r}, got {sorted(terms)!r}",
                    file=sys.stderr,
                )
        return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    :return: Configured parser.
    :rtype: argparse.ArgumentParser
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when suspicious prose English terms are found",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit findings as JSON instead of text",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run built-in regression checks and exit",
    )
    parser.add_argument(
        "--list-pages",
        action="store_true",
        help="print the default page inventory and exit",
    )
    parser.add_argument(
        "pages",
        nargs="*",
        type=Path,
        help="optional explicit pages or directories to scan",
    )
    return parser


def _expand_pages(inputs: Sequence[Path]) -> List[Path]:
    """Expand command-line page or directory arguments.

    :param inputs: Explicit paths from the command line.
    :type inputs: collections.abc.Sequence[pathlib.Path]
    :return: Unique sorted Chinese reST pages.
    :rtype: list[pathlib.Path]
    """

    if not inputs:
        return default_pages()

    pages: List[Path] = []
    for path in inputs:
        if path.is_dir():
            pages.extend(path.rglob("*_zh.rst"))
        else:
            pages.append(path)
    return sorted(dict.fromkeys(pages))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the terminology checker.

    :param argv: Optional argument list. ``None`` uses ``sys.argv``.
    :type argv: collections.abc.Sequence[str] or None
    :return: Process exit status.
    :rtype: int
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_check:
        return run_self_check()

    pages = _expand_pages(args.pages)

    if args.list_pages:
        for path in pages:
            print(path.as_posix())
        return 0

    missing = [path for path in pages if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing page: {path.as_posix()}", file=sys.stderr)
        return 2

    findings = scan_pages(pages)
    if args.json:
        print(json.dumps([asdict(finding) for finding in findings], ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(finding.format_text())

    if args.check and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
