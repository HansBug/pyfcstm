"""
Validate generated Sphinx PDF artifacts and their build evidence.

This repository-local maintenance command rejects partial PDFs that happen to
exist after a failed LaTeX run. It checks PDF structure, extracted content,
embedded CJK fonts, generated TeX line shape, and LaTeX/index logs. The command
stays outside :mod:`pyfcstm` and pytest so documentation builds remain
independent from the Python unit-test boundary.

The module contains:

* :class:`PdfValidationError` - Invalid PDF artifacts or failed self-checks.
* :func:`validate_docs_pdf` - Validate one language-specific Sphinx build root.
* :func:`validate_isolated_build_roots` - Reject shared bilingual build roots.
* :func:`run_self_check` - Exercise positive and adversarial temporary fixtures.
* :func:`main` - Command-line entry point.

Example::

    $ python tools/check_docs_pdf.py --check
    $ python tools/check_docs_pdf.py --language en --build-root docs/build/pdf/en
"""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple


_MAX_TEX_LINE_LENGTH = 65_536
_TAIL_PAGE_COUNT = 8
_REQUIRED_COMMANDS = (
    "xelatex",
    "latexmk",
    "pdfinfo",
    "pdftotext",
    "pdffonts",
    "mutool",
)
_CJK_CHARACTER = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
_FATAL_LOG_PATTERNS = (
    re.compile(r"TeX capacity exceeded", re.IGNORECASE),
    re.compile(r"Unable to read an entire line", re.IGNORECASE),
    re.compile(r"Emergency stop", re.IGNORECASE),
    re.compile(r"Fatal error", re.IGNORECASE),
    re.compile(r"LaTeX Error:", re.IGNORECASE),
    re.compile(r"File [`'].+[`'] not found", re.IGNORECASE),
    re.compile(r"Missing character: There is no", re.IGNORECASE),
    re.compile(r"fontspec Error", re.IGNORECASE),
    re.compile(r"Latexmk: Errors", re.IGNORECASE),
)
_REFERENCE_WARNING_PATTERNS = (
    re.compile(r"WARNING:.*undefined label", re.IGNORECASE),
    re.compile(r"WARNING:.*unknown document", re.IGNORECASE),
    re.compile(r"WARNING:.*reference target not found", re.IGNORECASE),
    re.compile(
        r"WARNING:.*toctree contains reference to nonexisting document",
        re.IGNORECASE,
    ),
)
_FORCE_MODE_PATTERN = re.compile(r"\blatexmk\b[^\n]*(?:^|\s)-f(?:\s|$)", re.IGNORECASE)
_MAKEINDEX_RESULT_PATTERN = re.compile(
    r"(?P<accepted>\d+) entries accepted,\s*(?P<rejected>\d+) rejected",
    re.IGNORECASE,
)
_PAGES_PATTERN = re.compile(r"^Pages:\s*(?P<pages>\d+)\s*$", re.MULTILINE)
_LANGUAGE_SPECS = {
    "en": {
        "contents_title": "Contents",
        "contents_entries": (
            "Tutorials",
            "How-to Guides",
            "Explanations",
            "Reference",
        ),
        "document_sentinel": "hard-coded parsing targets",
        "tail_sentinel": "windows_chinese_encodings",
        "cjk_sentinel": "你好",
        "minimum_pages": 20,
        "minimum_text_chars": 0,
        "required_text": (),
        "required_bookmarks": (
            "Tutorials",
            "How-to Guides",
            "Explanations",
            "Reference",
        ),
        "forbidden_text": (),
    },
    "zh": {
        "contents_title": "目录",
        "contents_entries": (
            "项目验收要求",
            "教程",
            "任务指南",
            "解释",
            "参考",
            "API 文档",
        ),
        "document_sentinel": "项目验收可复现验收完成哨兵",
        "tail_sentinel": "windows_chinese_encodings",
        "cjk_sentinel": "动态验证不是形式化验证",
        "minimum_pages": 500,
        "minimum_text_chars": 250_000,
        "required_text": (
            "交付范围",
            "功能映射",
            "动态验证",
            "编辑器与 GUI 交接",
            "五套内置模板",
            "cmake-native-evidence",
            "pygments-entry-point",
            "java-jar-prerequisite",
            "expected_actual",
            "mutation_counterexample",
            "design_validation_failure_multilevel_transition",
            "design_evented_pseudo_chain_invalid_then_valid",
            "expression_failure_transition_guard_raises_expression_error",
            "pseudo_self_loop_step_limit_raises_dfs_error",
            "TextMate 高亮",
            "Problems 诊断",
            "completion",
            "hover",
            "definition",
            "outline",
            "format",
            "code action",
            "preview",
            "export",
            "公式编辑交接",
            "Windows 7 可执行文件交付基线",
            "windows-2022",
            "python37.dll",
            "acceptance_pdf_tail_sentinel",
            "教程路线图",
            "任务指南路线图",
            "解释地图",
            "参考地图",
            "API 文档",
            "windows_chinese_encodings",
        ),
        "required_bookmarks": (
            "项目验收要求",
            "功能映射",
            "后端真实证据",
            "最小自定义模板",
            "动态验证",
            "编辑器与 GUI 交接",
            "Java/JAR 前置",
            "PDF 门禁",
            "教程路线图",
            "任务指南路线图",
            "解释地图",
            "参考地图",
            "API 文档",
        ),
        "forbidden_text": (
            r"dev/s714",
            r"S714",
            r"/home/zhangshaoang/",
        ),
    },
}


class PdfValidationError(RuntimeError):
    """
    Report an invalid generated PDF artifact or failed validator self-check.

    :param message: Human-readable validation failure.
    :type message: str

    Example::

        >>> PdfValidationError("missing tail sentinel").args[0]
        'missing tail sentinel'
    """


def _read_text(path: Path) -> str:
    """
    Read one UTF-8 text artifact with replacement for tool-emitted bytes.

    :param path: Text artifact to read.
    :type path: pathlib.Path
    :return: Decoded text.
    :rtype: str
    :raises PdfValidationError: If the artifact cannot be read.

    Example::

        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as directory:
        ...     path = Path(directory) / 'sample.log'
        ...     _ = path.write_text('ok', encoding='utf-8')
        ...     _read_text(path)
        'ok'
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        # Path.read_text raises OSError when a generated artifact is unreadable.
        raise PdfValidationError("cannot read {0}: {1}".format(path, error)) from error


def _write_text(path: Path, text: str) -> None:
    """
    Write one UTF-8 temporary self-check artifact.

    :param path: Destination path.
    :type path: pathlib.Path
    :param text: Text to write.
    :type text: str
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If the temporary artifact cannot be written.

    Example::

        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as directory:
        ...     path = Path(directory) / 'sample.txt'
        ...     _write_text(path, 'sample')
        ...     path.read_text(encoding='utf-8')
        'sample'
    """
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        # Path.write_text raises OSError when a self-check directory is unusable.
        raise PdfValidationError("cannot write {0}: {1}".format(path, error)) from error


def _language_spec(language: str) -> Mapping[str, object]:
    """
    Return the validation specification for one documentation language.

    :param language: Documentation language code.
    :type language: str
    :return: Language-specific titles, entries, and sentinels.
    :rtype: collections.abc.Mapping[str, object]
    :raises PdfValidationError: If the language is unsupported.

    Example::

        >>> _language_spec('zh')['contents_title']
        '目录'
        >>> _language_spec('zh')['tail_sentinel']
        'acceptance_pdf_tail_sentinel'
    """
    if language not in _LANGUAGE_SPECS:
        raise PdfValidationError(
            "unsupported documentation language: {0}".format(language)
        )
    return _LANGUAGE_SPECS[language]


def _require_command(command: str) -> str:
    """
    Resolve one required external PDF or TeX command.

    :param command: Executable name.
    :type command: str
    :return: Absolute executable path.
    :rtype: str
    :raises PdfValidationError: If the executable is unavailable.

    Example::

        >>> Path(_require_command('python')).name.startswith('python')
        True
    """
    resolved = shutil.which(command)
    if resolved is None:
        raise PdfValidationError(
            "required command {0!r} is unavailable; install the documented PDF toolchain".format(
                command
            )
        )
    return resolved


def _run_command(
    arguments: Sequence[str],
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run one external validator command with combined text output.

    :param arguments: Executable and arguments.
    :type arguments: collections.abc.Sequence[str]
    :param cwd: Optional working directory.
    :type cwd: pathlib.Path, optional
    :param check: Whether a non-zero status is a validation failure.
    :type check: bool, optional
    :return: Completed process with combined stdout/stderr in ``stdout``.
    :rtype: subprocess.CompletedProcess
    :raises PdfValidationError: If the command is unavailable or fails while
        ``check`` is true.

    Example::

        >>> _run_command(['python', '-c', 'print(3)']).stdout.strip()
        '3'
    """
    if not arguments:
        raise PdfValidationError("cannot run an empty command")
    executable = _require_command(arguments[0])
    completed = subprocess.run(
        [executable] + list(arguments[1:]),
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if check and completed.returncode != 0:
        raise PdfValidationError(
            "command failed with status {0}: {1}\n{2}".format(
                completed.returncode,
                " ".join(arguments),
                completed.stdout.strip(),
            )
        )
    return completed


def _normalize_extracted_text(text: str) -> str:
    """
    Normalize PDF text for stable cross-line and CJK sentinel matching.

    The normalization applies Unicode NFC, joins explicit hyphenated line
    breaks, removes layout whitespace between adjacent CJK characters, and
    collapses all remaining whitespace to one ASCII space.

    :param text: Raw ``pdftotext`` output.
    :type text: str
    :return: Normalized text.
    :rtype: str

    Example::

        >>> _normalize_extracted_text('hard-\\n coded 解析 方 式')
        'hard-coded 解析方式'
    """
    normalized = unicodedata.normalize("NFC", text).replace("\u00ad", "")
    normalized = re.sub(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)", "-", normalized)
    previous = None
    while previous != normalized:
        previous = normalized
        normalized = re.sub(
            "({0})\\s+({0})".format(_CJK_CHARACTER),
            r"\1\2",
            normalized,
        )
    return " ".join(normalized.split())


def _validate_extracted_text(
    full_text: str,
    front_text: str,
    tail_text: str,
    language: str,
    enforce_required_text: bool = False,
) -> None:
    """
    Validate directory, document-end, index-tail, and CJK PDF text.

    :param full_text: Text extracted from the full PDF.
    :type full_text: str
    :param front_text: Text extracted from the first PDF pages.
    :type front_text: str
    :param tail_text: Text extracted from the final PDF pages containing the
        generated index tail.
    :type tail_text: str
    :param language: Documentation language code.
    :type language: str
    :param enforce_required_text: Whether to enforce language-specific full-content sentinels.
    :type enforce_required_text: bool, optional
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If a required title, entry, document sentinel,
        index-tail sentinel, or CJK sample is missing.

    Example::

        >>> spec = _language_spec('en')
        >>> front = 'Contents\\n' + '\\n'.join(spec['contents_entries'])
        >>> full = '你好 hard-coded parsing targets'
        >>> _validate_extracted_text(full, front, 'windows_chinese_encodings', 'en')
    """
    spec = _language_spec(language)
    title = str(spec["contents_title"])
    normalized_lines = {
        _normalize_extracted_text(line)
        for line in front_text.splitlines()
        if line.strip()
    }
    if title not in normalized_lines:
        raise PdfValidationError(
            "PDF front matter has no independent {0!r} contents-title line".format(
                title
            )
        )

    normalized_front = _normalize_extracted_text(front_text)
    for entry in spec["contents_entries"]:
        if _normalize_extracted_text(str(entry)) not in normalized_front:
            raise PdfValidationError(
                "PDF contents pages are missing the major entry {0!r}".format(entry)
            )

    normalized_full = _normalize_extracted_text(full_text)
    document_sentinel = _normalize_extracted_text(str(spec["document_sentinel"]))
    if document_sentinel not in normalized_full:
        raise PdfValidationError(
            "PDF text is missing document-end sentinel {0!r}".format(
                spec["document_sentinel"]
            )
        )

    normalized_tail = _normalize_extracted_text(tail_text)
    tail_sentinel = _normalize_extracted_text(str(spec["tail_sentinel"]))
    if tail_sentinel not in normalized_tail:
        raise PdfValidationError(
            "PDF final {0} pages are missing index-tail sentinel {1!r}".format(
                _TAIL_PAGE_COUNT, spec["tail_sentinel"]
            )
        )

    cjk_sentinel = _normalize_extracted_text(str(spec["cjk_sentinel"]))
    if cjk_sentinel not in normalized_full:
        raise PdfValidationError(
            "PDF text is missing the CJK extraction sentinel {0!r}".format(
                spec["cjk_sentinel"]
            )
        )

    if enforce_required_text:
        for required_text in spec.get("required_text", ()):
            normalized_required = _normalize_extracted_text(str(required_text))
            if normalized_required not in normalized_full:
                raise PdfValidationError(
                    "PDF text is missing required content {0!r}".format(required_text)
                )

        for forbidden_pattern in spec.get("forbidden_text", ()):
            if re.search(str(forbidden_pattern), normalized_full, re.IGNORECASE):
                raise PdfValidationError(
                    "PDF text contains forbidden internal marker matching {0!r}".format(
                        forbidden_pattern
                    )
                )


def _validate_tex_file(tex_path: Path) -> int:
    """
    Validate generated TeX line length and registry-value suppression.

    :param tex_path: Generated primary TeX file.
    :type tex_path: pathlib.Path
    :return: Maximum physical line length.
    :rtype: int
    :raises PdfValidationError: If a line exceeds the safety threshold or the
        diagnostic registry value is expanded.

    Example::

        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as directory:
        ...     path = Path(directory) / 'sample.tex'
        ...     _ = path.write_text('short\\n', encoding='utf-8')
        ...     _validate_tex_file(path)
        5
    """
    text = _read_text(tex_path)
    lines = text.splitlines()
    maximum = max((len(line) for line in lines), default=0)
    if maximum > _MAX_TEX_LINE_LENGTH:
        raise PdfValidationError(
            "generated TeX maximum line length {0} exceeds {1}".format(
                maximum, _MAX_TEX_LINE_LENGTH
            )
        )
    for line_number, line in enumerate(lines, start=1):
        lowered = line.lower()
        registry_name = "code\\_registry" in lowered or "code_registry" in lowered
        registry_value = "mappingproxy(" in lowered or "codespec(code=" in lowered
        if registry_name and registry_value:
            raise PdfValidationError(
                "generated TeX expands CODE_REGISTRY on line {0}".format(line_number)
            )
    return maximum


def _validate_log_text(log_text: str) -> Tuple[int, int]:
    """
    Validate combined Sphinx, LaTeX, and makeindex log text.

    :param log_text: Combined build, LaTeX, and index logs.
    :type log_text: str
    :return: Last observed makeindex accepted and rejected counts.
    :rtype: tuple[int, int]
    :raises PdfValidationError: If a fatal pattern, latexmk force mode, missing
        makeindex result, or rejected index entry is found.

    Example::

        >>> _validate_log_text('latexmk -pdf doc.tex\\n1 entries accepted, 0 rejected')
        (1, 0)
    """
    for pattern in _FATAL_LOG_PATTERNS:
        match = pattern.search(log_text)
        if match is not None:
            raise PdfValidationError(
                "build log contains fatal pattern {0!r}".format(match.group(0))
            )
    for pattern in _REFERENCE_WARNING_PATTERNS:
        match = pattern.search(log_text)
        if match is not None:
            raise PdfValidationError(
                "build log contains broken-reference warning {0!r}".format(
                    match.group(0)
                )
            )
    if _FORCE_MODE_PATTERN.search(log_text) is not None:
        raise PdfValidationError("build log shows forbidden latexmk -f force mode")
    results = list(_MAKEINDEX_RESULT_PATTERN.finditer(log_text))
    if not results:
        raise PdfValidationError("build logs contain no makeindex acceptance summary")
    for result in results:
        rejected = int(result.group("rejected"))
        if rejected != 0:
            raise PdfValidationError("makeindex rejected {0} entries".format(rejected))
    last = results[-1]
    return int(last.group("accepted")), int(last.group("rejected"))


def _collect_log_text(build_root: Path, tex_stem: str) -> str:
    """
    Collect required build, LaTeX, and index logs for one Sphinx build.

    :param build_root: Sphinx make-mode output root.
    :type build_root: pathlib.Path
    :param tex_stem: Primary TeX document stem.
    :type tex_stem: str
    :return: Combined log text with file labels.
    :rtype: str
    :raises PdfValidationError: If required logs are missing or unreadable.

    Example::

        >>> isinstance(_collect_log_text, Callable)
        True
    """
    latex_dir = build_root / "latex"
    required = [build_root / "build.log", latex_dir / "{0}.log".format(tex_stem)]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise PdfValidationError(
            "required PDF build logs are missing: {0}".format(missing)
        )
    log_paths = required + sorted(latex_dir.glob("*.ilg"))
    if len(log_paths) == len(required):
        raise PdfValidationError("Sphinx PDF build produced no makeindex .ilg log")
    return "\n".join(
        "===== {0} =====\n{1}".format(path, _read_text(path)) for path in log_paths
    )


def _primary_artifacts(build_root: Path) -> Tuple[Path, Path]:
    """
    Resolve the primary TeX and matching PDF from one Sphinx build root.

    :param build_root: Sphinx make-mode output root.
    :type build_root: pathlib.Path
    :return: Primary TeX and PDF paths.
    :rtype: tuple[pathlib.Path, pathlib.Path]
    :raises PdfValidationError: If the LaTeX directory or primary artifacts are
        missing or ambiguous.

    Example::

        >>> isinstance(_primary_artifacts, Callable)
        True
    """
    latex_dir = build_root / "latex"
    if not latex_dir.is_dir():
        raise PdfValidationError(
            "Sphinx LaTeX directory is missing: {0}".format(latex_dir)
        )
    tex_files = sorted(latex_dir.glob("*.tex"))
    if len(tex_files) != 1:
        raise PdfValidationError(
            "expected exactly one primary TeX file in {0}, found {1}".format(
                latex_dir, len(tex_files)
            )
        )
    tex_path = tex_files[0]
    pdf_path = tex_path.with_suffix(".pdf")
    if not pdf_path.is_file():
        raise PdfValidationError("matching PDF is missing: {0}".format(pdf_path))
    return tex_path, pdf_path


def _pdf_page_count(pdf_path: Path) -> int:
    """
    Return a positive page count from ``pdfinfo``.

    :param pdf_path: PDF to inspect.
    :type pdf_path: pathlib.Path
    :return: Positive page count.
    :rtype: int
    :raises PdfValidationError: If ``pdfinfo`` fails or reports no pages.

    Example::

        >>> isinstance(_pdf_page_count, Callable)
        True
    """
    output = _run_command(["pdfinfo", str(pdf_path)]).stdout
    match = _PAGES_PATTERN.search(output)
    if match is None:
        raise PdfValidationError(
            "pdfinfo output has no Pages field for {0}".format(pdf_path)
        )
    pages = int(match.group("pages"))
    if pages <= 0:
        raise PdfValidationError("PDF has no readable pages: {0}".format(pdf_path))
    return pages


def _extract_pdf_text(pdf_path: Path, first_page: int, last_page: int) -> str:
    """
    Extract one inclusive PDF page range as UTF-8 text.

    :param pdf_path: PDF to extract.
    :type pdf_path: pathlib.Path
    :param first_page: First one-based page number.
    :type first_page: int
    :param last_page: Last one-based page number.
    :type last_page: int
    :return: Extracted text.
    :rtype: str
    :raises PdfValidationError: If ``pdftotext`` fails.

    Example::

        >>> isinstance(_extract_pdf_text, Callable)
        True
    """
    return _run_command(
        [
            "pdftotext",
            "-f",
            str(first_page),
            "-l",
            str(last_page),
            str(pdf_path),
            "-",
        ]
    ).stdout


def _validate_pdf_outline(pdf_path: Path, language: str) -> str:
    """
    Validate PDF bookmarks with ``mutool show outline``.

    :param pdf_path: Generated PDF.
    :type pdf_path: pathlib.Path
    :param language: Documentation language code.
    :type language: str
    :return: Raw outline text.
    :rtype: str
    :raises PdfValidationError: If the outline is unreadable or missing a
        required major bookmark.

    Example::

        >>> isinstance(_validate_pdf_outline, Callable)
        True
    """
    spec = _language_spec(language)
    outline = _run_command(["mutool", "show", str(pdf_path), "outline"]).stdout
    normalized_outline = _normalize_extracted_text(outline)
    if not normalized_outline:
        raise PdfValidationError("PDF has no readable bookmark outline")
    for bookmark in spec.get("required_bookmarks", ()):  # type: ignore[attr-defined]
        if _normalize_extracted_text(str(bookmark)) not in normalized_outline:
            raise PdfValidationError(
                "PDF outline is missing required bookmark {0!r}".format(bookmark)
            )
    return outline


def _validate_pdf_file(
    pdf_path: Path,
    language: str,
    enforce_minimum_pages: bool = True,
    enforce_required_text: bool = True,
) -> Tuple[int, str, int, str]:
    """
    Validate PDF structure, extracted content, bookmarks, and embedded CJK fonts.

    :param pdf_path: Generated PDF.
    :type pdf_path: pathlib.Path
    :param language: Documentation language code.
    :type language: str
    :param enforce_minimum_pages: Whether to enforce the language-specific page-count and text-size floors.
    :type enforce_minimum_pages: bool, optional
    :param enforce_required_text: Whether to enforce language-specific full-content sentinels.
    :type enforce_required_text: bool, optional
    :return: Page count, raw ``pdffonts`` output, normalized text length, and
        raw bookmark outline.
    :rtype: tuple[int, str, int, str]
    :raises PdfValidationError: If PDF structure, text, or fonts are invalid.

    Example::

        >>> isinstance(_validate_pdf_file, Callable)
        True
    """
    if shutil.which("qpdf") is not None:
        _run_command(["qpdf", "--check", str(pdf_path)])
    pages = _pdf_page_count(pdf_path)
    minimum_pages = int(_language_spec(language).get("minimum_pages", 1))
    if enforce_minimum_pages and pages < minimum_pages:
        raise PdfValidationError(
            "PDF page count {0} is below required minimum {1}".format(
                pages, minimum_pages
            )
        )
    outline = ""
    if enforce_required_text:
        outline = _validate_pdf_outline(pdf_path, language)
    full_text = _extract_pdf_text(pdf_path, 1, pages)
    text_chars = len(_normalize_extracted_text(full_text))
    minimum_text_chars = int(_language_spec(language).get("minimum_text_chars", 0))
    if enforce_minimum_pages and text_chars < minimum_text_chars:
        raise PdfValidationError(
            "PDF normalized text length {0} is below required minimum {1}".format(
                text_chars, minimum_text_chars
            )
        )
    front_text = _extract_pdf_text(pdf_path, 1, min(pages, 20))
    tail_text = _extract_pdf_text(pdf_path, max(1, pages - _TAIL_PAGE_COUNT + 1), pages)
    _validate_extracted_text(
        full_text,
        front_text,
        tail_text,
        language,
        enforce_required_text=enforce_required_text,
    )
    fonts = _run_command(["pdffonts", str(pdf_path)]).stdout
    if "Fandol" not in fonts:
        raise PdfValidationError("PDF embeds no Fandol CJK font: {0}".format(pdf_path))
    if "CID" not in fonts:
        raise PdfValidationError(
            "PDF fonts output has no CID font entries: {0}".format(pdf_path)
        )
    return pages, fonts, text_chars, outline


def validate_docs_pdf(
    build_root: Path,
    language: str,
    enforce_minimum_pages: bool = True,
    enforce_required_text: bool = True,
) -> Dict[str, object]:
    """
    Validate one language-specific Sphinx PDF build root.

    :param build_root: Sphinx make-mode output root containing ``latex/`` and
        ``build.log``.
    :type build_root: pathlib.Path
    :param language: Documentation language.
    :type language: str
    :param enforce_minimum_pages: Whether to enforce the language-specific page-count and text-size floors.
    :type enforce_minimum_pages: bool, optional
    :param enforce_required_text: Whether to enforce language-specific full-content sentinels.
    :type enforce_required_text: bool, optional
    :return: Validation evidence including artifact paths, page count, maximum
        TeX line length, and makeindex counts.
    :rtype: dict[str, object]
    :raises PdfValidationError: If any structure, content, font, TeX, or log
        contract fails.

    Example::

        >>> isinstance(validate_docs_pdf, Callable)
        True
    """
    _language_spec(language)
    build_root = build_root.resolve()
    tex_path, pdf_path = _primary_artifacts(build_root)
    maximum_line = _validate_tex_file(tex_path)
    log_text = _collect_log_text(build_root, tex_path.stem)
    accepted, rejected = _validate_log_text(log_text)
    pages, fonts, text_chars, outline = _validate_pdf_file(
        pdf_path,
        language,
        enforce_minimum_pages=enforce_minimum_pages,
        enforce_required_text=enforce_required_text,
    )
    return {
        "language": language,
        "build_root": str(build_root),
        "tex_path": str(tex_path),
        "pdf_path": str(pdf_path),
        "pages": pages,
        "text_chars": text_chars,
        "outline_entries": len([line for line in outline.splitlines() if line.strip()]),
        "required_contents_entries": tuple(
            str(item) for item in _language_spec(language)["contents_entries"]
        ),
        "maximum_tex_line_length": maximum_line,
        "makeindex_accepted": accepted,
        "makeindex_rejected": rejected,
        "fandol_embedded": "Fandol" in fonts,
    }


def validate_isolated_build_roots(first: Path, second: Path) -> None:
    """
    Require two language build roots to be distinct and non-nested.

    :param first: First language build root.
    :type first: pathlib.Path
    :param second: Second language build root.
    :type second: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If roots resolve to the same path or one root is
        nested inside the other.

    Example::

        >>> validate_isolated_build_roots(Path('/tmp/pdf-en'), Path('/tmp/pdf-zh'))
    """
    first_resolved = first.resolve()
    second_resolved = second.resolve()
    if first_resolved == second_resolved:
        raise PdfValidationError("bilingual PDF build roots resolve to the same path")
    common = Path(os.path.commonpath([str(first_resolved), str(second_resolved)]))
    if common == first_resolved or common == second_resolved:
        raise PdfValidationError(
            "bilingual PDF build roots must not be nested: {0}, {1}".format(
                first_resolved, second_resolved
            )
        )


def _validate_acceptance_source_contract(index_text: str, conf_text: str) -> None:
    """
    Validate the source-level full-manual acceptance profile contract.

    The delivery PDF must reuse the normal Chinese manual root, place the
    acceptance page before every technical section, and keep all five
    technical navigation roots. This fast check catches an accidental return
    to an acceptance-only document before XeLaTeX work starts.

    :param index_text: Chinese root document source.
    :type index_text: str
    :param conf_text: Sphinx configuration source.
    :type conf_text: str
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If the root, ordering, profile tag, or technical
        source inclusion contract is missing.

    Example::

        >>> isinstance(_validate_acceptance_source_contract, Callable)
        True
    """
    ordered_index_markers = (
        "教程路线图 <tutorials/index_zh>",
        "任务指南路线图 <how_to/index_zh>",
        "解释地图 <explanations/index_zh>",
        "参考地图 <reference/index_zh>",
        "应用程序接口文档 <api_doc_zh>",
    )
    cursor = -1
    for marker in ordered_index_markers:
        position = index_text.find(marker, cursor + 1)
        if position < 0:
            raise PdfValidationError(
                "Chinese manual root is missing ordered entry {0!r}".format(marker)
            )
        cursor = position

    hidden_entry = index_text.find(".. only:: not acceptance_pdf")
    release_entry = index_text.find("release_notes_zh")
    if hidden_entry < 0 or release_entry < hidden_entry:
        raise PdfValidationError(
            "release/community entries are not hidden from the acceptance PDF"
        )

    required_conf_markers = (
        'master_doc = "index"',
        'app.tags.add("acceptance_pdf")',
        "项目验收要求 <acceptance/index_zh>",
        "_copy_language_index(_source_index, _target_index, _ACCEPTANCE_PDF)",
        '"index",\n            "pyfcstm-acceptance-zh.tex"',
    )
    for marker in required_conf_markers:
        if marker not in conf_text:
            raise PdfValidationError(
                "Sphinx acceptance profile is missing {0!r}".format(marker)
            )
    forbidden_excludes = (
        '"api_doc/**"',
        '"tutorials/**"',
        '"how_to/**"',
        '"explanations/**"',
        '"reference/**"',
    )
    for marker in forbidden_excludes:
        if marker in conf_text:
            raise PdfValidationError(
                "Sphinx acceptance profile excludes technical content {0}".format(
                    marker
                )
            )


def _expect_failure(label: str, callback: Callable[[], object]) -> None:
    """
    Require one adversarial self-check callback to fail validation.

    :param label: Human-readable adversarial case label.
    :type label: str
    :param callback: Zero-argument validation callback.
    :type callback: collections.abc.Callable[[], object]
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If the invalid fixture is accepted.

    Example::

        >>> _expect_failure('sample', lambda: (_ for _ in ()).throw(PdfValidationError('x')))
    """
    try:
        callback()
    except PdfValidationError:
        # PdfValidationError is the expected result for an adversarial fixture.
        return
    raise PdfValidationError("self-check accepted invalid fixture: {0}".format(label))


def _check_sphinx_metadata_contract() -> None:
    """
    Check Sphinx metadata parsing with and without the required blank line.

    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If the installed Sphinx version does not honor
        the expected ``hide-value`` metadata contract.

    Example::

        >>> _check_sphinx_metadata_contract()
    """
    try:
        from sphinx.ext.autodoc import separate_metadata
    except ImportError as error:
        # Sphinx is required by the documented PDF build and metadata self-check.
        raise PdfValidationError(
            "Sphinx autodoc is unavailable: {0}".format(error)
        ) from error
    _, valid_metadata = separate_metadata(
        "Mapping from codes to specifications.\n\n:meta hide-value:"
    )
    _, invalid_metadata = separate_metadata(
        "Mapping from codes to specifications.\n:meta hide-value:"
    )
    if "hide-value" not in valid_metadata:
        raise PdfValidationError("Sphinx did not parse valid hide-value metadata")
    if "hide-value" in invalid_metadata:
        raise PdfValidationError(
            "Sphinx unexpectedly accepted metadata without a blank line"
        )


def _smoke_source(language: str) -> str:
    """
    Return a standalone XeLaTeX smoke document for one language.

    :param language: Documentation language code.
    :type language: str
    :return: Complete XeLaTeX source with ToC, index, CJK, and tail sentinel.
    :rtype: str
    :raises PdfValidationError: If the language is unsupported.

    Example::

        >>> r'\\usepackage{xeCJK}' in _smoke_source('en')
        True
    """
    spec = _language_spec(language)
    title = str(spec["contents_title"])
    sections = tuple(str(entry) for entry in spec["contents_entries"])
    section_text = "\n".join(
        "\\section{{{0}}}\nSmoke text for {0}.".format(section) for section in sections
    )
    cjk_sentinel_text = str(spec["cjk_sentinel"])
    tail_sentinel_tex = str(spec["tail_sentinel"]).replace("_", r"\_")
    return r"""\documentclass{article}
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{makeidx}
\setCJKmainfont{FandolSong-Regular.otf}[
  BoldFont=FandolHei-Regular.otf,
  ItalicFont=FandolKai-Regular.otf
]
\setCJKmonofont{FandolFang-Regular.otf}
\renewcommand{\contentsname}{%s}
\makeindex
\begin{document}
\tableofcontents
\newpage
%s
\index{smoke}
\textbf{你好} \texttt{你好} %s
\newpage
%s
\texttt{%s}
\printindex
\end{document}
""" % (
        title,
        section_text,
        cjk_sentinel_text,
        spec["document_sentinel"],
        tail_sentinel_tex,
    )


def _create_smoke_build(build_root: Path, language: str) -> Path:
    """
    Compile one standalone XeLaTeX smoke build in a temporary root.

    :param build_root: Temporary build root.
    :type build_root: pathlib.Path
    :param language: Documentation language code.
    :type language: str
    :return: Generated PDF path.
    :rtype: pathlib.Path
    :raises PdfValidationError: If the smoke document cannot be compiled.

    Example::

        >>> isinstance(_create_smoke_build, Callable)
        True
    """
    latex_dir = build_root / "latex"
    try:
        latex_dir.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        # Path.mkdir raises OSError when the temporary build root is unusable.
        raise PdfValidationError(
            "cannot create smoke build root: {0}".format(error)
        ) from error
    tex_path = latex_dir / "smoke.tex"
    _write_text(tex_path, _smoke_source(language))
    result = _run_command(
        [
            "latexmk",
            "-xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            tex_path.name,
        ],
        cwd=latex_dir,
        check=False,
    )
    _write_text(build_root / "build.log", result.stdout)
    if result.returncode != 0:
        raise PdfValidationError(
            "standalone XeLaTeX smoke build failed with status {0}\n{1}".format(
                result.returncode, result.stdout
            )
        )
    validate_docs_pdf(
        build_root, language, enforce_minimum_pages=False, enforce_required_text=False
    )
    return tex_path.with_suffix(".pdf")


def _run_pure_self_checks(root: Path) -> None:
    """
    Run validator checks that do not require external PDF commands.

    :param root: Temporary root for text fixtures.
    :type root: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If a positive case fails or a negative case is
        accepted.

    Example::

        >>> isinstance(_run_pure_self_checks, Callable)
        True
    """
    try:
        root.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        # Path.mkdir raises OSError when the pure self-check root is unusable.
        raise PdfValidationError(
            "cannot create pure self-check root: {0}".format(error)
        ) from error
    repository = Path(__file__).resolve().parents[1]
    index_text = _read_text(repository / "docs" / "source" / "index_zh.rst")
    conf_text = _read_text(repository / "docs" / "source" / "conf.py")
    _validate_acceptance_source_contract(index_text, conf_text)
    _expect_failure(
        "missing technical manual root",
        lambda: _validate_acceptance_source_contract(
            index_text.replace(
                "教程路线图 <tutorials/index_zh>",
                "教程路线图 <tutorials/missing>",
            ),
            conf_text,
        ),
    )
    _expect_failure(
        "acceptance profile excludes technical docs",
        lambda: _validate_acceptance_source_contract(
            index_text,
            conf_text + '\nexclude_patterns.append("tutorials/**")\n',
        ),
    )
    _check_sphinx_metadata_contract()
    en_spec = _language_spec("en")
    en_front = "Contents\n" + "\n".join(en_spec["contents_entries"])
    _validate_extracted_text(
        "你好 hard-coded parsing targets",
        en_front,
        "windows_chinese_encodings",
        "en",
    )
    _expect_failure(
        "wrong contents title",
        lambda: _validate_extracted_text(
            "你好 hard-coded parsing targets",
            en_front.replace("Contents", "Tutorials", 1),
            en_spec["tail_sentinel"],
            "en",
        ),
    )
    _expect_failure(
        "uppercased contents title",
        lambda: _validate_extracted_text(
            "你好 hard-coded parsing targets",
            en_front.replace("Contents", "CONTENTS", 1),
            en_spec["tail_sentinel"],
            "en",
        ),
    )
    _expect_failure(
        "missing major contents entry",
        lambda: _validate_extracted_text(
            "你好 hard-coded parsing targets",
            en_front.replace("How-to Guides\n", "", 1),
            en_spec["tail_sentinel"],
            "en",
        ),
    )
    _expect_failure(
        "missing document sentinel",
        lambda: _validate_extracted_text(
            "你好", en_front, en_spec["tail_sentinel"], "en"
        ),
    )
    _expect_failure(
        "missing index-tail sentinel",
        lambda: _validate_extracted_text(
            "你好 hard-coded parsing targets", en_front, "truncated", "en"
        ),
    )
    _expect_failure(
        "missing CJK sentinel",
        lambda: _validate_extracted_text(
            "ASCII only hard-coded parsing targets",
            en_front,
            en_spec["tail_sentinel"],
            "en",
        ),
    )

    tex_path = root / "sample.tex"
    _write_text(tex_path, "short\n")
    _validate_tex_file(tex_path)
    _write_text(tex_path, "x" * (_MAX_TEX_LINE_LENGTH + 1))
    _expect_failure("oversized TeX line", lambda: _validate_tex_file(tex_path))
    _write_text(tex_path, "CODE\\_REGISTRY = mappingproxy({})\n")
    _expect_failure("expanded registry", lambda: _validate_tex_file(tex_path))

    good_log = "latexmk -pdf smoke.tex\n1 entries accepted, 0 rejected"
    _validate_log_text(good_log)
    _expect_failure(
        "TeX fatal with PDF output",
        lambda: _validate_log_text(
            good_log + "\nTeX capacity exceeded\nOutput written on smoke.pdf"
        ),
    )
    _expect_failure(
        "latexmk force mode",
        lambda: _validate_log_text(
            "latexmk -pdf -f smoke.tex\n1 entries accepted, 0 rejected"
        ),
    )
    _expect_failure(
        "rejected index entries",
        lambda: _validate_log_text(
            "latexmk -pdf smoke.tex\n1 entries accepted, 1 rejected"
        ),
    )
    _expect_failure(
        "broken Sphinx document reference",
        lambda: _validate_log_text(
            good_log
            + "\nWARNING: toctree contains reference to nonexisting document "
            + "'tutorials/missing'"
        ),
    )
    _expect_failure(
        "shared bilingual roots",
        lambda: validate_isolated_build_roots(root / "same", root / "same"),
    )
    _expect_failure(
        "nested bilingual roots",
        lambda: validate_isolated_build_roots(
            root / "parent", root / "parent" / "child"
        ),
    )
    validate_isolated_build_roots(root / "en", root / "zh")

    zh_spec = _language_spec("zh")
    zh_front = "目录\n" + "\n".join(zh_spec["contents_entries"])
    _validate_extracted_text(
        "动态验证不是形式化验证 项目验收可复现验收完成哨兵",
        zh_front,
        zh_spec["tail_sentinel"],
        "zh",
    )
    _expect_failure(
        "zh acceptance rejects abbreviated contents",
        lambda: _validate_extracted_text(
            "动态验证不是形式化验证 项目验收可复现验收完成哨兵",
            "目录\n交付范围\n功能映射\n动态验证\n编辑器与 GUI 交接",
            zh_spec["tail_sentinel"],
            "zh",
        ),
    )
    _expect_failure(
        "zh missing acceptance required text",
        lambda: _validate_extracted_text(
            "动态验证不是形式化验证 项目验收可复现验收完成哨兵",
            zh_front,
            zh_spec["tail_sentinel"],
            "zh",
            enforce_required_text=True,
        ),
    )


def _run_external_self_checks(root: Path) -> None:
    """
    Run standalone XeLaTeX and damaged-PDF integration checks.

    :param root: Temporary root for real PDF fixtures.
    :type root: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If the toolchain is unavailable, a positive
        build fails, or a damaged PDF is accepted.

    Example::

        >>> isinstance(_run_external_self_checks, Callable)
        True
    """
    for command in _REQUIRED_COMMANDS:
        _require_command(command)
    en_root = root / "pdf-en"
    zh_root = root / "pdf-zh"
    validate_isolated_build_roots(en_root, zh_root)
    en_pdf = _create_smoke_build(en_root, "en")
    _create_smoke_build(zh_root, "zh")

    broken_pdf = root / "truncated.pdf"
    try:
        data = en_pdf.read_bytes()
        broken_pdf.write_bytes(data[:-256])
    except OSError as error:
        # Path byte I/O can fail when the temporary self-check root is unusable.
        raise PdfValidationError(
            "cannot create truncated PDF fixture: {0}".format(error)
        ) from error
    if shutil.which("qpdf") is not None:
        result = _run_command(["qpdf", "--check", str(broken_pdf)], check=False)
        if result.returncode == 0:
            raise PdfValidationError("qpdf accepted the truncated self-check PDF")
    else:
        result = _run_command(["pdftotext", str(broken_pdf), "-"], check=False)
        if result.returncode == 0:
            raise PdfValidationError("pdftotext accepted the truncated self-check PDF")


def run_self_check() -> None:
    """
    Run validator positive and adversarial checks in temporary directories.

    :return: ``None``.
    :rtype: None
    :raises PdfValidationError: If a positive fixture fails or an invalid
        fixture is accepted.

    Example::

        >>> isinstance(run_self_check, Callable)
        True
    """
    try:
        with tempfile.TemporaryDirectory(prefix="pyfcstm-pdf-check-") as directory:
            root = Path(directory)
            _run_pure_self_checks(root / "pure")
            _run_external_self_checks(root / "external")
    except OSError as error:
        # TemporaryDirectory raises OSError when no writable temporary root exists.
        raise PdfValidationError(
            "cannot create PDF self-check directory: {0}".format(error)
        ) from error


def _build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser

    Example::

        >>> isinstance(_build_parser(), argparse.ArgumentParser)
        True
    """
    parser = argparse.ArgumentParser(
        description="Validate generated Sphinx PDF artifacts and build logs."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="run built-in positive and adversarial self-checks",
    )
    parser.add_argument("--language", choices=("en", "zh"))
    parser.add_argument("--build-root", type=Path)
    parser.add_argument(
        "--check-isolation",
        nargs=2,
        type=Path,
        metavar=("FIRST_ROOT", "SECOND_ROOT"),
        help="verify two language build roots are distinct and non-nested",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the PDF validator command-line interface.

    :param argv: Optional argument sequence without the executable name.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status. ``0`` means every requested check passed.
    :rtype: int

    Example::

        >>> isinstance(main, Callable)
        True
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    selected_modes = sum(
        (
            bool(args.check),
            args.check_isolation is not None,
            args.language is not None or args.build_root is not None,
        )
    )
    if selected_modes != 1:
        parser.error(
            "choose exactly one mode: --check, --check-isolation, or --language with --build-root"
        )
    if args.check:
        run_self_check()
        print("PDF validator self-check passed.")
        return 0
    if args.check_isolation is not None:
        validate_isolated_build_roots(*args.check_isolation)
        print("PDF build roots are isolated.")
        return 0
    if args.language is None or args.build_root is None:
        parser.error("--language and --build-root must be used together")
    evidence = validate_docs_pdf(args.build_root, args.language)
    print("PDF validation passed: {0}".format(evidence["pdf_path"]))
    print("Pages: {0}".format(evidence["pages"]))
    print("Normalized text characters: {0}".format(evidence["text_chars"]))
    print("Outline entries: {0}".format(evidence["outline_entries"]))
    print("Maximum TeX line: {0}".format(evidence["maximum_tex_line_length"]))
    print("Makeindex rejected: {0}".format(evidence["makeindex_rejected"]))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PdfValidationError as error:
        # PdfValidationError is the command's documented validation failure.
        raise SystemExit("PDF validation failed: {0}".format(error))
