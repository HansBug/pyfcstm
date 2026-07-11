"""
Validate acceptance delivery artifacts from repository-local evidence.

This maintenance command checks acceptance delivery artifacts without trusting the
source checkout as proof of artifact contents. It reads package archives,
recursive PyInstaller inventories, PDF text and bookmarks, VSIX archives, and
packaged template assets directly. Package installation and editor installation
checks are explicit options. Executable validation performs its recursive
inventory and end-to-end command checks whenever an executable path is given.
The built-in self-check uses temporary fixtures and does not require network
access or heavyweight external tools.

The module contains:

* :class:`ArtifactValidationError` - Invalid artifact or self-check evidence.
* :func:`validate_packages` - Validate one wheel and one sdist in a directory.
* :func:`validate_executable_inventory` - Validate a PyInstaller inventory.
* :func:`validate_pdf_artifact` - Validate acceptance PDF metadata and text evidence.
* :func:`validate_vsix` - Validate one VS Code extension package.
* :func:`validate_delivery_bundle` - Validate the consolidated six-file bundle.
* :func:`validate_template_assets` - Compare template ZIP entry names and
  payload bytes while ignoring ZIP container metadata.
* :func:`run_self_check` - Exercise positive and adversarial fixtures.
* :func:`main` - Command-line entry point.

Example::

    $ python tools/check_acceptance_artifacts.py --check
    $ python tools/check_acceptance_artifacts.py packages --artifact-dir dist/packages
    $ python tools/check_acceptance_artifacts.py executable --path dist/pyfcstm-0.5.0-windows-x86_64.exe --source acceptance.fcstm --plantuml-jar plantuml.jar
"""

from __future__ import annotations

import argparse
import ast
import csv
import fnmatch
import hashlib
import io
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import zipfile
import zlib
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from xml.etree import ElementTree


TEMPLATE_NAMES = ("c", "c_poll", "cpp", "cpp_poll", "python")
CLI_COMMANDS = ("generate", "inspect", "plantuml", "simulate", "visualize")
VSIX_ENTRY_COUNT = 13
VSIX_EXTENSION_ID = "hansbug.fcstm-language-support@0.1.0"
FORBIDDEN_DELIVERY_TERMS = ("github", "s714")

WHEEL_REQUIRED = (
    "pyfcstm/__init__.py",
    "pyfcstm/config/meta.py",
    "pyfcstm/dsl/parse.py",
    "pyfcstm/model/model.py",
    "pyfcstm/diagnostics/codes.yaml",
    "pyfcstm/diagnostics/schema.json",
    "pyfcstm/entry/cli.py",
    "pyfcstm/highlight/pygments_lexer.py",
    "pyfcstm/render/render.py",
    "pyfcstm/simulate/runtime.py",
    "pyfcstm/solver/solve.py",
    "pyfcstm/verify/__init__.py",
    "pyfcstm/template/index.json",
    "pyfcstm/template/c.zip",
    "pyfcstm/template/c_poll.zip",
    "pyfcstm/template/cpp.zip",
    "pyfcstm/template/cpp_poll.zip",
    "pyfcstm/template/python.zip",
)
WHEEL_DIST_INFO_REQUIRED = ("METADATA", "WHEEL", "RECORD", "entry_points.txt")
WHEEL_DIST_INFO_LICENSE_PATHS = ("LICENSE", "licenses/LICENSE")
WHEEL_DENYLIST = (
    "pyfcstm/llm/*",
    "pyfcstm/diagnostics/README*",
    "pyfcstm/diagnostics/inspect_llm_report_schema.json",
    "pyfcstm/dsl/grammar/*.g4",
    "pyfcstm/dsl/grammar/*.interp",
    "pyfcstm/dsl/grammar/*.tokens",
    "test/*",
    "docs/*",
    "editors/*",
    "llm_eval/*",
    ".github/*",
    ".omx/*",
    ".agents/*",
    "templates/*",
    "requirements-dev.txt",
    "requirements-doc.txt",
    "requirements-test.txt",
    "requirements-build.txt",
    "README.md",
)

SDIST_REQUIRED = (
    "setup.py",
    "setup.cfg",
    "MANIFEST.in",
    "requirements.txt",
    "README_ACCEPTANCE.md",
    "LICENSE",
    "PKG-INFO",
    "pyfcstm/__init__.py",
    "pyfcstm/dsl/parse.py",
    "pyfcstm/dsl/grammar/GrammarParser.g4",
    "pyfcstm/dsl/grammar/GrammarLexer.g4",
    "pyfcstm/dsl/grammar/GrammarParser.interp",
    "pyfcstm/dsl/grammar/GrammarLexer.tokens",
    "pyfcstm/diagnostics/codes.yaml",
    "pyfcstm/diagnostics/schema.json",
    "pyfcstm/template/index.json",
    "pyfcstm/template/c.zip",
    "pyfcstm/template/c_poll.zip",
    "pyfcstm/template/cpp.zip",
    "pyfcstm/template/cpp_poll.zip",
    "pyfcstm/template/python.zip",
)
SDIST_DENYLIST = (
    "pyfcstm/llm/*",
    "pyfcstm/diagnostics/README*",
    "pyfcstm/diagnostics/inspect_llm_report_schema.json",
    "test/*",
    "docs/*",
    "editors/*",
    "llm_eval/*",
    ".github/*",
    ".omx/*",
    ".agents/*",
    "templates/*",
    "requirements-dev.txt",
    "requirements-doc.txt",
    "requirements-test.txt",
    "requirements-build.txt",
    "README.md",
)

EXECUTABLE_REQUIRED = (
    "icons/pyfcstm.png",
    "jinja2",
    "plantumlcli",
    "prompt_toolkit",
    "rich",
    "z3",
    "pyfcstm.render.c_runtime",
    "pyfcstm/diagnostics/codes.yaml",
    "pyfcstm/diagnostics/schema.json",
    "pyfcstm/template/index.json",
    "pyfcstm/template/c.zip",
    "pyfcstm/template/c_poll.zip",
    "pyfcstm/template/cpp.zip",
    "pyfcstm/template/cpp_poll.zip",
    "pyfcstm/template/python.zip",
)
EXECUTABLE_REQUIRED_PATTERN_GROUPS = (
    (
        "z3/lib/libz3.so*",
        "z3/lib/libz3.dylib",
        "z3/lib/libz3.dll",
        "libz3.so*",
        "libz3.dylib",
        "libz3.dll",
    ),
)
WINDOWS_EXECUTABLE_REQUIRED_PATTERN_GROUPS = (("python37.dll",),)
LINUX_EXECUTABLE_REQUIRED_PATTERN_GROUPS = (
    ("libpython3.7*.so*", "python3.7/lib-dynload/*"),
)
EXECUTABLE_DENYLIST = (
    "pyfcstm/llm/*",
    "pyfcstm.llm*",
    "pyfcstm/diagnostics/README*",
    "pyfcstm/diagnostics/inspect_llm_report_schema.json",
    "pyfcstm/dsl/grammar/*.g4",
    "pyfcstm/dsl/grammar/*.interp",
    "pyfcstm/dsl/grammar/*.tokens",
    "z3/include/*",
    "z3*.h",
    "test/*",
    "docs/*",
    "editors/*",
    "templates/*",
)

PDF_REQUIRED_TEXT = (
    "项目验收",
    "fcstm状态机建模与解析",
    "Windows 7 可执行文件交付基线",
    "windows-2022",
    "python37.dll",
    "Linux 可执行文件交付基线",
    "ubuntu-22.04",
    "模型动态验证",
    "动态验证不是形式化验证",
    "design_validation_failure_multilevel_transition",
    "design_evented_pseudo_chain_invalid_then_valid",
    "expression_failure_transition_guard_raises_expression_error",
    "pseudo_self_loop_step_limit_raises_dfs_error",
    "五套内置模板",
    "cmake-native-evidence",
    "pygments-entry-point",
    "java-jar-prerequisite",
    "mutation_counterexample",
    "TextMate 高亮",
    "Problems 诊断",
    "公式编辑交接",
    "GUI",
    "教程路线图",
    "任务指南路线图",
    "解释地图",
    "参考地图",
    "API 文档",
    "windows_chinese_encodings",
)
PDF_DENY_TEXT = (
    "/home/zhangshaoang/",
    "dev/s714",
    "S714",
    "github",
)
PDF_REQUIRED_OUTLINE = (
    "项目验收要求",
    "交付范围",
    "功能映射",
    "验收样例",
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
)
PDF_DENY_OUTLINE = (
    "Release Notes",
    "Community",
    "发布说明",
    "社区",
)

VSIX_REQUIRED_ENTRIES = (
    "[Content_Types].xml",
    "extension.vsixmanifest",
    "extension/package.json",
    "extension/dist/extension.js",
    "extension/dist/server.js",
    "extension/dist/preview-webview.js",
    "extension/dist/preview-webview.css",
    "extension/language-configuration.json",
    "extension/LICENSE.txt",
    "extension/README.md",
    "extension/resources/icon.png",
    "extension/snippets/fcstm.code-snippets",
    "extension/syntaxes/fcstm.tmLanguage.json",
)
VSIX_DENYLIST = (
    "extension/src/*",
    "extension/test/*",
    "extension/scripts/*",
    "extension/out/*",
    "extension/node_modules/*",
    "extension/**/*.map",
    "extension/syntaxes/fcstm-bmc-query.tmLanguage.json",
    "extension/dist/preview-worker.js",
    "extension/.vscodeignore*",
    "extension/README_*.md",
    "extension/README-dev.md",
    "extension/dist/*.ts",
    "*.whl",
    "*.tar.gz",
    "*.pdf",
    "*.vsix",
)
VSIX_DENY_TEXT = (
    "BMC",
    "SMT",
    "LLM",
    "/home/",
    "node_modules",
    "需要 Python",
    "需要 Java",
)
VSIX_BUNDLE_SENTINELS = {
    "extension/dist/extension.js": (
        "fcstm.preview.open",
        "LanguageClient",
        "registerCommand",
    ),
    "extension/dist/server.js": (
        "createConnection",
        "TextDocuments",
        "publishDiagnostics",
    ),
    "extension/dist/preview-webview.js": (
        "acquireVsCodeApi",
        "postMessage",
    ),
}


class ArtifactValidationError(RuntimeError):
    """
    Report invalid acceptance artifact evidence or a failed checker self-test.

    :param message: Human-readable validation failure.
    :type message: str

    Example::

        >>> ArtifactValidationError('missing wheel').args[0]
        'missing wheel'
    """


def repository_root() -> Path:
    """
    Return the repository root for this maintenance command.

    :return: Repository root path.
    :rtype: pathlib.Path

    Example::

        >>> repository_root().name  # doctest: +SKIP
        'pyfcstm'
    """
    return Path(__file__).resolve().parents[1]


def validate_packages(
    artifact_dir: Path,
    install_smoke: bool = False,
    python: Optional[str] = None,
    assert_isolated: bool = False,
    source: Optional[Path] = None,
) -> Mapping[str, object]:
    """
    Validate one acceptance wheel and one acceptance sdist in ``artifact_dir``.

    The archive checks are always local and deterministic. Installation smoke
    is opt-in because it creates virtual environments and invokes pip. The
    checker never builds artifacts itself; callers must provide already-built
    files.

    :param artifact_dir: Directory containing exactly one ``.whl`` and one
        ``.tar.gz`` source distribution.
    :type artifact_dir: pathlib.Path
    :param install_smoke: Whether to install both artifacts in clean virtual
        environments.
    :type install_smoke: bool, optional
    :param python: Interpreter used to create smoke-test virtual environments.
    :type python: str, optional
    :param assert_isolated: Whether smoke tests assert imports originate from
        the target environment and not from the repository checkout.
    :type assert_isolated: bool, optional
    :param source: Optional FCSTM source used by smoke tests.
    :type source: pathlib.Path, optional
    :return: Summary of validated package artifacts.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If archives or optional smoke tests fail.

    Example::

        >>> try:
        ...     validate_packages(Path('/missing'))
        ... except ArtifactValidationError as error:
        ...     str(error).startswith('package artifact directory does not exist')
        True
    """
    if not artifact_dir.is_dir():
        raise ArtifactValidationError(
            "package artifact directory does not exist: {0}".format(artifact_dir)
        )
    wheels = sorted(artifact_dir.glob("*.whl"))
    sdists = sorted(artifact_dir.glob("*.tar.gz"))
    if len(wheels) != 1:
        raise ArtifactValidationError(
            "expected exactly one wheel in {0}, found {1}: {2}".format(
                artifact_dir, len(wheels), [p.name for p in wheels]
            )
        )
    if len(sdists) != 1:
        raise ArtifactValidationError(
            "expected exactly one sdist in {0}, found {1}: {2}".format(
                artifact_dir, len(sdists), [p.name for p in sdists]
            )
        )
    _assert_package_filenames(wheels[0], sdists[0])

    wheel_entries, wheel_payloads = _read_zip_entries(wheels[0])
    _assert_required("wheel", wheel_entries, WHEEL_REQUIRED)
    _assert_wheel_allowlist(wheel_entries)
    _assert_denylist("wheel", wheel_entries, WHEEL_DENYLIST)
    _assert_wheel_dist_info(wheel_entries, wheel_payloads)
    _assert_acceptance_metadata(wheel_payloads)
    wheel_sensitive_scan = _assert_delivery_content_clean(
        "wheel",
        (wheels[0].name,) + wheel_entries,
        {wheels[0].name: wheels[0].read_bytes(), **wheel_payloads},
    )

    sdist_entries, sdist_payloads = _read_tar_entries(sdists[0])
    sdist_normalized = _strip_single_root(sdist_entries)
    _assert_required("sdist", sdist_normalized, SDIST_REQUIRED)
    _assert_sdist_allowlist(sdist_normalized)
    _assert_denylist("sdist", sdist_normalized, SDIST_DENYLIST)
    _assert_sdist_readme(sdist_payloads)
    sdist_sensitive_scan = _assert_delivery_content_clean(
        "sdist",
        (sdists[0].name,) + sdist_entries,
        {sdists[0].name: sdists[0].read_bytes(), **sdist_payloads},
    )

    smoke = None
    if install_smoke:
        smoke = _run_package_install_smoke(
            wheels[0], sdists[0], python or sys.executable, assert_isolated, source
        )
    return {
        "wheel": str(wheels[0]),
        "sdist": str(sdists[0]),
        "wheel_entries": len(wheel_entries),
        "sdist_entries": len(sdist_entries),
        "sensitive_scan": {
            "wheel": wheel_sensitive_scan,
            "sdist": sdist_sensitive_scan,
        },
        "install_smoke": smoke,
    }


def validate_executable_inventory(
    executable: Path,
    source: Path,
    plantuml_jar: Path,
    archive_viewer: str = "pyi-archive_viewer",
) -> Mapping[str, object]:
    """
    Validate a recursive PyInstaller inventory and executable behavior.

    Validation requires the accepted Windows 7 delivery build baseline
    (GitHub Actions ``windows-2022``, 64-bit CPython 3.7), derives a recursive
    inventory from the supplied binary, and then runs the complete end-to-end
    command suite. A caller-provided inventory is deliberately not accepted as
    artifact evidence because it can be detached from the executable under
    test.

    :param executable: Executable file to inventory and execute.
    :type executable: pathlib.Path
    :param source: FCSTM source file used by executable end-to-end checks.
    :type source: pathlib.Path
    :param plantuml_jar: PlantUML JAR used for real local PNG and SVG rendering.
    :type plantuml_jar: pathlib.Path
    :param archive_viewer: PyInstaller archive viewer command.
    :type archive_viewer: str, optional
    :return: Summary of build provenance, inventory, and executable evidence.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If inventory generation, inventory rules,
        source validation, or executable behavior fails.

    Example::

        >>> try:
        ...     validate_executable_inventory(
        ...         Path('/missing'), Path('/missing.fcstm'), Path('/missing.jar')
        ...     )
        ... except ArtifactValidationError as error:
        ...     str(error).startswith('executable does not exist')
        True
    """
    if not executable.is_file():
        raise ArtifactValidationError(
            "executable does not exist: {0}".format(executable)
        )
    if not source.is_file():
        raise ArtifactValidationError(
            "executable end-to-end source does not exist: {0}".format(source)
        )
    if not plantuml_jar.is_file():
        raise ArtifactValidationError(
            "PlantUML JAR does not exist: {0}".format(plantuml_jar)
        )

    build_baseline = _assert_executable_delivery_build_baseline()
    inventory_text = _run_command(
        [archive_viewer, "-r", "-l", str(executable.resolve())]
    ).stdout
    entries = _parse_inventory_entries(inventory_text)
    inventory_origin = "{0} -r -l {1}".format(archive_viewer, executable.resolve())
    _assert_executable_inventory_entries(entries, build_baseline["platform"])
    extracted_payloads = _read_pyinstaller_payloads(executable)
    executable_bytes = executable.read_bytes()
    sensitive_scan = _assert_delivery_content_clean(
        "executable",
        (executable.name,) + entries + tuple(extracted_payloads),
        {
            executable.name: executable_bytes,
            "printable-strings": _extract_printable_strings(executable_bytes),
            **extracted_payloads,
        },
    )
    smoke = _run_executable_smoke(executable, source, plantuml_jar)
    return {
        "inventory": inventory_origin,
        "entries": len(entries),
        "executable": str(executable),
        "build_baseline": build_baseline,
        "sensitive_scan": sensitive_scan,
        "e2e": smoke,
    }


def validate_pdf_artifact(
    pdf: Optional[Path] = None,
    text_file: Optional[Path] = None,
    metadata_file: Optional[Path] = None,
    outline_file: Optional[Path] = None,
    build_root: Optional[Path] = None,
    min_pages: int = 500,
    max_pages: int = 1000,
    min_text_chars: int = 250_000,
) -> Mapping[str, object]:
    """
    Validate acceptance PDF metadata, extracted text, and outline evidence.

    Explicit sidecar files exist only for lightweight unit tests and self-check
    fixtures. A formal ``build_root`` validation rejects sidecars, discovers
    exactly one correctly named PDF under ``build_root/latex``, invokes the
    normal Chinese documentation checker, and extracts evidence from the real
    PDF with Poppler and MuPDF tools.

    :param pdf: Optional PDF artifact path. When omitted, discover the fixed
        acceptance PDF under ``build_root/latex``.
    :type pdf: pathlib.Path, optional
    :param text_file: Optional extracted UTF-8 text file.
    :type text_file: pathlib.Path, optional
    :param metadata_file: Optional ``pdfinfo``-style metadata file.
    :type metadata_file: pathlib.Path, optional
    :param outline_file: Optional outline/bookmark text file.
    :type outline_file: pathlib.Path, optional
    :param build_root: Optional Sphinx PDF build root for common checks.
    :type build_root: pathlib.Path, optional
    :param min_pages: Minimum acceptable PDF page count.
    :type min_pages: int, optional
    :param max_pages: Maximum acceptable PDF page count.
    :type max_pages: int, optional
    :param min_text_chars: Minimum normalized extracted-text length.
    :type min_text_chars: int, optional
    :return: Summary of validated PDF evidence.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If required metadata, text, or outline
        evidence is missing or invalid.

    Example::

        >>> try:
        ...     validate_pdf_artifact(Path('/missing.pdf'))
        ... except ArtifactValidationError as error:
        ...     str(error).startswith('acceptance PDF does not exist')
        True
    """
    sidecars = (text_file, metadata_file, outline_file)
    if build_root is not None:
        if any(item is not None for item in sidecars):
            raise ArtifactValidationError(
                "formal --build-root PDF validation cannot use extraction sidecars"
            )
        pdf = _discover_pdf_artifact(build_root, pdf)
        _run_common_pdf_checker(build_root)
    elif pdf is None:
        raise ArtifactValidationError("PDF validation requires --build-root or --pdf")

    if pdf is None:  # pragma: no cover - guarded above
        raise ArtifactValidationError("acceptance PDF path could not be resolved")
    if not pdf.is_file():
        raise ArtifactValidationError("acceptance PDF does not exist: {0}".format(pdf))
    if pdf.suffix.lower() != ".pdf":
        raise ArtifactValidationError(
            "acceptance PDF path must end with .pdf: {0}".format(pdf)
        )
    if pdf.name != "pyfcstm-acceptance-zh.pdf":
        raise ArtifactValidationError(
            "acceptance PDF filename must be pyfcstm-acceptance-zh.pdf: {0}".format(
                pdf.name
            )
        )
    _assert_pdf_magic(pdf)

    text = (
        _read_text_evidence(text_file)
        if text_file is not None
        else _extract_pdf_text(pdf)
    )
    metadata = (
        _read_text_evidence(metadata_file)
        if metadata_file is not None
        else _extract_pdf_metadata(pdf)
    )
    outline = (
        _read_text_evidence(outline_file)
        if outline_file is not None
        else _extract_pdf_outline(pdf)
    )
    pages = _parse_page_count(metadata)
    if pages < min_pages or pages > max_pages:
        raise ArtifactValidationError(
            "acceptance PDF page count out of range for {0}: actual {1}, expected {2}..{3}".format(
                pdf, pages, min_pages, max_pages
            )
        )
    text_chars = len(_normalize_search_text(text))
    if text_chars < min_text_chars:
        raise ArtifactValidationError(
            "acceptance PDF normalized text length {0} is below required "
            "minimum {1}".format(text_chars, min_text_chars)
        )
    _assert_text_contains("acceptance PDF text", text, PDF_REQUIRED_TEXT)
    _assert_text_excludes("acceptance PDF text", text, PDF_DENY_TEXT)
    outline_entries, required_outline = _validate_pdf_outline(outline)
    sensitive_scan = _assert_delivery_content_clean(
        "acceptance PDF",
        (pdf.name,),
        {
            pdf.name: pdf.read_bytes(),
            "extracted-text": text.encode("utf-8"),
            "metadata": metadata.encode("utf-8"),
            "outline": outline.encode("utf-8"),
        },
    )
    return {
        "pdf": str(pdf),
        "pages": pages,
        "text_chars": text_chars,
        "outline_entries": outline_entries,
        "required_outline": required_outline,
        "sensitive_scan": sensitive_scan,
    }


def validate_vsix(
    vsix: Path,
    install_smoke: bool = False,
    code: Optional[str] = None,
    source: Optional[Path] = None,
    javascript_syntax: bool = True,
) -> Mapping[str, object]:
    """
    Validate one acceptance VS Code extension archive.

    :param vsix: VSIX file path.
    :type vsix: pathlib.Path
    :param install_smoke: Whether to install the VSIX into an isolated VS Code
        extension directory.
    :type install_smoke: bool, optional
    :param code: VS Code executable used for installation smoke.
    :type code: str, optional
    :param source: Optional FCSTM source associated with the acceptance run.
    :type source: pathlib.Path, optional
    :param javascript_syntax: Whether to run ``node --check`` for the three
        JavaScript bundle entries, defaults to ``True``.
    :type javascript_syntax: bool, optional
    :return: Summary of validated VSIX archive evidence.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If the archive, manifest, package metadata,
        allowlist, denylist, or optional installation smoke fails.

    Example::

        >>> try:
        ...     validate_vsix(Path('/missing.vsix'))
        ... except ArtifactValidationError as error:
        ...     str(error).startswith('VSIX does not exist')
        True
    """
    if not vsix.is_file():
        raise ArtifactValidationError("VSIX does not exist: {0}".format(vsix))
    vsix = vsix.resolve()
    if vsix.suffix.lower() != ".vsix":
        raise ArtifactValidationError("VSIX path must end with .vsix: {0}".format(vsix))
    _assert_single_vsix(vsix)
    _assert_vsix_filename(vsix)
    if install_smoke and source is None:
        raise ArtifactValidationError("VSIX install smoke requires --source")
    if source is not None and not source.is_file():
        raise ArtifactValidationError("VSIX source does not exist: {0}".format(source))
    entries, payloads = _read_zip_entries(vsix)
    _assert_denylist("VSIX", entries, VSIX_DENYLIST)
    _assert_exact_entries("VSIX", entries, VSIX_REQUIRED_ENTRIES)
    if len(entries) != VSIX_ENTRY_COUNT:
        raise ArtifactValidationError(
            "VSIX entry count mismatch for {0}: actual {1}, expected {2}".format(
                vsix, len(entries), VSIX_ENTRY_COUNT
            )
        )
    package = _load_json_payload(payloads, "extension/package.json", "VSIX package")
    _assert_vsix_package(package, entries)
    installation_id = _assert_vsix_manifest(payloads, package)
    _assert_vsix_payload_quality(payloads)
    readme = _decode_payload(payloads, "extension/README.md", "VSIX README")
    manifest = _decode_payload(payloads, "extension.vsixmanifest", "VSIX manifest")
    _assert_text_excludes("VSIX visible text", readme + "\n" + manifest, VSIX_DENY_TEXT)
    sensitive_scan = _assert_delivery_content_clean(
        "VSIX",
        (vsix.name,) + entries,
        {vsix.name: vsix.read_bytes(), **payloads},
    )
    if javascript_syntax:
        _run_vsix_javascript_syntax_checks(payloads)
    smoke = None
    if install_smoke:
        smoke = _run_vsix_install_smoke(vsix, code or "code", source)
    return {
        "vsix": str(vsix),
        "entries": len(entries),
        "extension": installation_id,
        "version": package.get("version"),
        "source": str(source) if source is not None else None,
        "sensitive_scan": sensitive_scan,
        "install_smoke": smoke,
    }


def validate_delivery_bundle(delivery_dir: Path) -> Mapping[str, object]:
    """
    Validate the consolidated six-file acceptance delivery bundle.

    This final gate repeats filename, signature, archive-member, PDF evidence,
    raw executable, printable-string, and extractable PyInstaller payload scans
    after staging artifacts have been downloaded and merged.

    :param delivery_dir: Directory containing the six final delivery files.
    :type delivery_dir: pathlib.Path
    :return: Frozen file metadata and zero-count sensitive-term reports.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If the bundle contract or content scan
        fails.

    Example::

        >>> try:
        ...     validate_delivery_bundle(Path('/missing'))
        ... except ArtifactValidationError as error:
        ...     str(error).startswith('delivery directory does not exist')
        True
    """
    files = _classify_delivery_files(delivery_dir)
    _assert_delivery_signatures(files)
    scans: Dict[str, Mapping[str, object]] = {}

    wheel = files["wheel"]
    wheel_entries, wheel_payloads = _read_zip_entries(wheel)
    scans["wheel"] = _assert_delivery_content_clean(
        "delivery wheel",
        (wheel.name,) + wheel_entries,
        {wheel.name: wheel.read_bytes(), **wheel_payloads},
    )

    sdist = files["sdist"]
    sdist_entries, sdist_payloads = _read_tar_entries(sdist)
    scans["sdist"] = _assert_delivery_content_clean(
        "delivery sdist",
        (sdist.name,) + sdist_entries,
        {sdist.name: sdist.read_bytes(), **sdist_payloads},
    )

    pdf = files["pdf"]
    scans["pdf"] = _assert_delivery_content_clean(
        "delivery PDF",
        (pdf.name,),
        {
            pdf.name: pdf.read_bytes(),
            "extracted-text": _extract_pdf_text(pdf).encode("utf-8"),
            "metadata": _extract_pdf_metadata(pdf).encode("utf-8"),
            "outline": _extract_pdf_outline(pdf).encode("utf-8"),
        },
    )

    vsix = files["vsix"]
    vsix_entries, vsix_payloads = _read_zip_entries(vsix)
    scans["vsix"] = _assert_delivery_content_clean(
        "delivery VSIX",
        (vsix.name,) + vsix_entries,
        {vsix.name: vsix.read_bytes(), **vsix_payloads},
    )

    for key in ("windows_executable", "linux_executable"):
        executable = files[key]
        executable_bytes = executable.read_bytes()
        extracted_payloads = _read_pyinstaller_payloads(executable)
        scans[key] = _assert_delivery_content_clean(
            "delivery {0}".format(key.replace("_", " ")),
            (executable.name,) + tuple(extracted_payloads),
            {
                executable.name: executable_bytes,
                "printable-strings": _extract_printable_strings(executable_bytes),
                **extracted_payloads,
            },
        )

    frozen_files = []
    for key, path in sorted(files.items()):
        frozen_files.append(
            {
                "kind": key,
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {"files": frozen_files, "sensitive_scan": scans}


def validate_template_assets(
    actual_dir: Path,
    expected_dir: Optional[Path] = None,
    source_dir: Optional[Path] = None,
) -> Mapping[str, object]:
    """
    Compare packaged built-in template assets by index, entry names, and bytes.

    ZIP timestamps, compression methods, comments, and other container metadata
    are intentionally ignored. Only the tracked ``index.json`` content, member
    path set, and each member's decompressed payload bytes are compared.

    :param actual_dir: Directory containing packaged template ``index.json`` and
        ``*.zip`` assets under test.
    :type actual_dir: pathlib.Path
    :param expected_dir: Optional independently rebuilt template asset directory.
        When omitted, templates are repackaged from the repository source into a
        temporary directory using :mod:`tools.package_templates`.
    :type expected_dir: pathlib.Path, optional
    :param source_dir: Optional repository-source template directory to package.
        Defaults to the repository ``templates`` directory when neither an
        expected directory nor an explicit source is supplied.
    :type source_dir: pathlib.Path, optional
    :return: Summary of compared template assets.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If indexes, ZIP entry names, or payload
        bytes differ.

    Example::

        >>> try:
        ...     validate_template_assets(Path('/missing'))
        ... except ArtifactValidationError as error:
        ...     str(error).startswith('template asset directory does not exist')
        True
    """
    if not actual_dir.is_dir():
        raise ArtifactValidationError(
            "template asset directory does not exist: {0}".format(actual_dir)
        )
    if expected_dir is not None and source_dir is not None:
        raise ArtifactValidationError(
            "template validation accepts either expected_dir or source_dir, not both"
        )
    temp_manager = None
    try:
        if expected_dir is None:
            source = source_dir or (repository_root() / "templates")
            if not source.is_dir():
                raise ArtifactValidationError(
                    "template source directory does not exist: {0}".format(source)
                )
            temp_manager, expected_dir = _package_templates_to_tempdir(source)
        if expected_dir is None or not expected_dir.is_dir():
            raise ArtifactValidationError(
                "expected template asset directory does not exist: {0}".format(
                    expected_dir
                )
            )
        _assert_template_asset_file_set(
            "packaged template assets", actual_dir, package_directory=True
        )
        _assert_template_asset_file_set("expected template assets", expected_dir)
        _assert_json_equal(expected_dir / "index.json", actual_dir / "index.json")
        compared = []
        for name in TEMPLATE_NAMES:
            _assert_zip_payloads_equal(
                expected_dir / "{0}.zip".format(name),
                actual_dir / "{0}.zip".format(name),
                "template {0}".format(name),
            )
            compared.append(name)
        return {
            "packaged": str(actual_dir),
            "source": str(source_dir) if source_dir is not None else None,
            "templates": compared,
        }
    finally:
        if temp_manager is not None:
            temp_manager.cleanup()


def _assert_template_asset_file_set(
    label: str, directory: Path, package_directory: bool = False
) -> None:
    expected = {"index.json"}
    expected.update("{0}.zip".format(name) for name in TEMPLATE_NAMES)
    if package_directory:
        expected.add("__init__.py")
    actual = {item.name for item in directory.iterdir() if item.name != "__pycache__"}
    if actual != expected:
        raise ArtifactValidationError(
            "{0} file set mismatch: missing={1}; extra={2}".format(
                label, sorted(expected - actual), sorted(actual - expected)
            )
        )


def run_self_check() -> Mapping[str, object]:
    """
    Run positive and adversarial checks using only temporary fixtures.

    The self-check proves that required-file, denylist, installed package file
    parity, executable help policy, template member and payload tamper, ZIP
    metadata-only drift, exact VSIX 13-entry identity, PDF text/metadata/
    outline, and recursive PyInstaller inventory checks are not constant-true
    predicates.

    :return: Summary of self-check scenarios.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If any positive fixture fails or any
        adversarial fixture unexpectedly passes.

    Example::

        >>> run_self_check()['status']  # doctest: +SKIP
        'ok'
    """
    checks: List[str] = []
    with tempfile.TemporaryDirectory(prefix="acceptance-artifacts-check-") as directory:
        root = Path(directory)
        package_dir = root / "packages"
        _create_package_fixture(package_dir)
        validate_packages(package_dir)
        checks.append("packages-positive")
        _expect_failure(
            lambda: validate_packages(
                _copy_and_tamper_package_fixture(
                    package_dir, root / "bad-packages-deny", "wheel-llm"
                )
            ),
            "wheel denylist",
        )
        checks.append("packages-wheel-deny")
        _expect_failure(
            lambda: validate_packages(
                _copy_and_tamper_package_fixture(
                    package_dir,
                    root / "bad-packages-license",
                    "wheel-missing-license",
                )
            ),
            "wheel license required",
        )
        checks.append("packages-wheel-license-required")
        for mode in (
            "wheel-diagnostics-readme",
            "sdist-diagnostics-readme",
            "wheel-sensitive-payload",
            "sdist-sensitive-payload",
        ):
            _expect_failure(
                lambda mode=mode: validate_packages(
                    _copy_and_tamper_package_fixture(
                        package_dir, root / ("bad-packages-" + mode), mode
                    )
                ),
                mode,
            )
            checks.append("packages-{0}".format(mode))
        _expect_failure(
            lambda: validate_packages(
                _copy_and_tamper_package_fixture(
                    package_dir, root / "bad-packages-missing", "sdist-missing-required"
                )
            ),
            "sdist required",
        )
        checks.append("packages-sdist-required")
        _expect_failure(
            lambda: validate_packages(
                _copy_and_tamper_package_fixture(
                    package_dir,
                    root / "bad-packages-filename",
                    "wheel-filename",
                )
            ),
            "normal package filenames",
        )
        checks.append("packages-filename-negative")
        wheel = next(package_dir.glob("*.whl"))
        wheel_entries, _ = _read_zip_entries(wheel)
        install_files = _wheel_install_files(wheel_entries)
        _assert_package_install_files(
            install_files, install_files, "package file parity"
        )
        checks.append("packages-runtime-files-positive")
        dist_info = "pyfcstm-0.0.0.dist-info"
        _assert_package_install_files(
            ("{0}/LICENSE".format(dist_info),),
            ("{0}/licenses/LICENSE".format(dist_info),),
            "equivalent wheel license layouts",
        )
        checks.append("packages-license-layout-equivalence")
        _expect_failure(
            lambda: _assert_package_install_files(
                install_files,
                tuple(install_files) + ("pyfcstm/llm/forbidden.py",),
                "package file parity",
            ),
            "installed package file set extra entry",
        )
        checks.append("packages-runtime-files-negative")

        inventory = root / "pyinstaller-inventory.txt"
        _write_inventory_fixture(inventory, good=True)
        _assert_executable_inventory_entries(_read_inventory_entries(inventory))
        checks.append("executable-positive")
        windows_inventory = root / "pyinstaller-inventory-windows.txt"
        windows_inventory.write_text(
            " 1, 2, 3, 1, 'x', 'icons\\\\pyfcstm.png'\n",
            encoding="utf-8",
        )
        windows_entries = _read_inventory_entries(windows_inventory)
        if windows_entries != ("icons/pyfcstm.png",):
            raise ArtifactValidationError(
                "Windows PyInstaller inventory path was not decoded: {0!r}".format(
                    windows_entries
                )
            )
        checks.append("executable-windows-inventory-path")
        delivery_facts = {
            "os_name": "nt",
            "system_name": "Windows",
            "python_version": (3, 7),
            "pointer_bits": 64,
            "github_actions": "true",
            "runner_os": "Windows",
            "baseline": "windows-2022-cpython-3.7-x86_64",
            "image_os": "win22",
        }
        _assert_windows7_delivery_build_facts(**delivery_facts)
        checks.append("executable-windows7-baseline-positive")
        invalid_delivery_facts = (
            ("os_name", "posix"),
            ("system_name", "Linux"),
            ("python_version", (3, 8)),
            ("pointer_bits", 32),
            ("github_actions", ""),
            ("runner_os", "Linux"),
            ("baseline", ""),
            ("image_os", ""),
        )
        for key, invalid_value in invalid_delivery_facts:
            facts = dict(delivery_facts)
            facts[key] = invalid_value
            _expect_failure(
                lambda facts=facts: _assert_windows7_delivery_build_facts(**facts),
                "Windows 7 delivery {0}".format(key),
            )
        checks.append("executable-windows7-baseline-negative")
        linux_delivery_facts = {
            "os_name": "posix",
            "system_name": "Linux",
            "python_version": (3, 7),
            "pointer_bits": 64,
            "github_actions": "true",
            "runner_os": "Linux",
            "baseline": "ubuntu-22.04-cpython-3.7-x86_64",
            "image_os": "ubuntu22",
        }
        _assert_linux_delivery_build_facts(**linux_delivery_facts)
        linux_inventory = root / "pyinstaller-inventory-linux.txt"
        _write_inventory_fixture(linux_inventory, good=True, delivery_platform="linux")
        _assert_executable_inventory_entries(
            _read_inventory_entries(linux_inventory), "linux"
        )
        checks.append("executable-linux-baseline-positive")
        invalid_linux_facts = dict(linux_delivery_facts)
        invalid_linux_facts["image_os"] = "ubuntu24"
        _expect_failure(
            lambda: _assert_linux_delivery_build_facts(**invalid_linux_facts),
            "Linux delivery image",
        )
        checks.append("executable-linux-baseline-negative")
        bad_inventory = root / "pyinstaller-inventory-bad.txt"
        _write_inventory_fixture(bad_inventory, good=False)
        _expect_failure(
            lambda: _assert_executable_inventory_entries(
                _read_inventory_entries(bad_inventory)
            ),
            "inventory denylist",
        )
        checks.append("executable-deny")
        sensitive_inventory = root / "pyinstaller-inventory-sensitive.txt"
        _write_inventory_fixture(sensitive_inventory, good=True)
        sensitive_inventory.write_text(
            sensitive_inventory.read_text(encoding="utf-8")
            + " 0, 1, 1, 1, 'x', 'payload/GitHub.txt'\n",
            encoding="utf-8",
        )
        _expect_failure(
            lambda: _assert_executable_inventory_entries(
                _read_inventory_entries(sensitive_inventory)
            ),
            "executable sensitive inventory",
        )
        checks.append("executable-sensitive-inventory-negative")
        missing_inventory = root / "pyinstaller-inventory-missing.txt"
        _write_inventory_fixture(missing_inventory, good=True, missing_required=True)
        _expect_failure(
            lambda: _assert_executable_inventory_entries(
                _read_inventory_entries(missing_inventory)
            ),
            "inventory required resource",
        )
        checks.append("executable-required")
        parser = _build_parser()
        subparsers_action = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        executable_parser = subparsers_action.choices["executable"]
        executable_options = {
            option
            for action in executable_parser._actions
            for option in action.option_strings
        }
        if "--inventory" in executable_options or "--run-e2e" in executable_options:
            raise ArtifactValidationError(
                "inventory-only executable validation unexpectedly remained available"
            )
        required_destinations = {
            action.dest for action in executable_parser._actions if action.required
        }
        if required_destinations != {"path", "source", "plantuml_jar"}:
            raise ArtifactValidationError(
                "executable parser required fields drifted: {0}".format(
                    sorted(required_destinations)
                )
            )
        checks.append("executable-inventory-only-negative")
        top_help, inspect_help = _cli_help_fixture()
        _assert_cli_help_contract(top_help, inspect_help)
        checks.append("executable-help-positive")
        bad_top_help, _ = _cli_help_fixture(mutation="missing-command")
        _expect_failure(
            lambda: _assert_cli_help_contract(bad_top_help, inspect_help),
            "executable command table",
        )
        checks.append("executable-command-table-negative")
        _, bad_inspect_help = _cli_help_fixture(mutation="inspect-policy")
        _expect_failure(
            lambda: _assert_cli_help_contract(top_help, bad_inspect_help),
            "inspect help policy",
        )
        checks.append("executable-inspect-help-negative")

        pdf = root / "pyfcstm-acceptance-zh.pdf"
        pdf.write_bytes(b"%PDF-1.4\n% fixture\n")
        text_file = root / "pdf.txt"
        metadata_file = root / "pdfinfo.txt"
        outline_file = root / "outline.txt"
        _write_pdf_sidecars(text_file, metadata_file, outline_file, good=True)
        validate_pdf_artifact(pdf, text_file, metadata_file, outline_file)
        checks.append("pdf-positive")
        sparse_text = root / "pdf-sparse.txt"
        sparse_text.write_text("\n".join(PDF_REQUIRED_TEXT), encoding="utf-8")
        _expect_failure(
            lambda: validate_pdf_artifact(
                pdf, sparse_text, metadata_file, outline_file
            ),
            "PDF text-size floor",
        )
        checks.append("pdf-text-size-negative")
        bad_text = root / "pdf-bad.txt"
        _write_pdf_sidecars(bad_text, metadata_file, outline_file, good=False)
        _expect_failure(
            lambda: validate_pdf_artifact(pdf, bad_text, metadata_file, outline_file),
            "pdf deny text",
        )
        checks.append("pdf-deny")
        for mutation in ("sensitive-text", "sensitive-metadata", "sensitive-outline"):
            sensitive_text = root / ("pdf-" + mutation + ".txt")
            sensitive_metadata = root / ("pdfinfo-" + mutation + ".txt")
            sensitive_outline = root / ("outline-" + mutation + ".txt")
            _write_pdf_sidecars(
                sensitive_text,
                sensitive_metadata,
                sensitive_outline,
                good=True,
                mutation=mutation,
            )
            _expect_failure(
                lambda sensitive_text=sensitive_text, sensitive_metadata=sensitive_metadata, sensitive_outline=sensitive_outline: (
                    validate_pdf_artifact(
                        pdf,
                        sensitive_text,
                        sensitive_metadata,
                        sensitive_outline,
                    )
                ),
                "PDF {0}".format(mutation),
            )
            checks.append("pdf-{0}-negative".format(mutation))
        bad_metadata = root / "pdfinfo-bad.txt"
        _write_pdf_sidecars(
            text_file, bad_metadata, outline_file, good=True, mutation="metadata"
        )
        _expect_failure(
            lambda: validate_pdf_artifact(pdf, text_file, bad_metadata, outline_file),
            "PDF metadata",
        )
        checks.append("pdf-metadata-negative")
        bad_outline = root / "outline-bad.txt"
        _write_pdf_sidecars(
            text_file, metadata_file, bad_outline, good=True, mutation="outline"
        )
        _expect_failure(
            lambda: validate_pdf_artifact(pdf, text_file, metadata_file, bad_outline),
            "PDF outline",
        )
        checks.append("pdf-outline-negative")
        pdf_build_root = root / "pdf-build"
        pdf_build_latex = pdf_build_root / "latex"
        pdf_build_latex.mkdir(parents=True)
        discovered_pdf = pdf_build_latex / "pyfcstm-acceptance-zh.pdf"
        discovered_pdf.write_bytes(pdf.read_bytes())
        if _discover_pdf_artifact(pdf_build_root, None) != discovered_pdf:
            raise ArtifactValidationError(
                "self-check did not discover the normal acceptance PDF name"
            )
        extra_pdf = pdf_build_latex / "pyfcstm-stale.pdf"
        extra_pdf.write_bytes(pdf.read_bytes())
        _expect_failure(
            lambda: _discover_pdf_artifact(pdf_build_root, None),
            "acceptance PDF unique file",
        )
        checks.append("pdf-multiple-negative")
        discovered_pdf.unlink()
        _expect_failure(
            lambda: _discover_pdf_artifact(pdf_build_root, None),
            "acceptance PDF normal filename",
        )
        checks.append("pdf-filename-negative")
        vsix_dir = root / "vsix-good"
        vsix = vsix_dir / "fcstm-language-support-0.1.0.vsix"
        _create_vsix_fixture(vsix)
        validate_vsix(vsix, javascript_syntax=False)
        checks.append("vsix-positive")
        for mutation in (
            "missing-server",
            "missing-preview",
            "bmc-grammar",
            "wrong-id",
            "wrong-version",
            "extra-entry",
            "placeholder-bundle",
            "empty-grammar",
            "missing-manifest-asset",
            "sensitive-bundle",
        ):
            bad_dir = root / "vsix-{0}".format(mutation)
            bad_vsix = bad_dir / "fcstm-language-support-0.1.0.vsix"
            _create_vsix_fixture(bad_vsix, mutation=mutation)
            _expect_failure(
                lambda bad_vsix=bad_vsix: validate_vsix(
                    bad_vsix, javascript_syntax=False
                ),
                "VSIX {0}".format(mutation),
            )
            checks.append("vsix-{0}".format(mutation))
        wrong_filename_dir = root / "vsix-wrong-filename"
        wrong_filename = (
            wrong_filename_dir / "fcstm-language-support-0.1.0-acceptance.vsix"
        )
        _create_vsix_fixture(wrong_filename)
        _expect_failure(
            lambda: validate_vsix(wrong_filename, javascript_syntax=False),
            "VSIX normal filename",
        )
        checks.append("vsix-filename-negative")
        _assert_vsix_installation_listing(VSIX_EXTENSION_ID + "\n")
        _expect_failure(
            lambda: _assert_vsix_installation_listing(
                "other.fcstm-language-support@0.1.0\n"
            ),
            "VSIX installed extension id",
        )
        checks.append("vsix-install-id-negative")
        archive_entries, _ = _read_zip_entries(vsix)
        installed_layout = _expected_installed_vsix_files(archive_entries)
        if ".vsixmanifest" not in installed_layout:
            raise ArtifactValidationError(
                "VSIX installed-layout mapping omitted .vsixmanifest"
            )
        if "extension.vsixmanifest" in installed_layout:
            raise ArtifactValidationError(
                "VSIX installed-layout mapping retained archive manifest path"
            )
        _assert_package_install_files(
            installed_layout,
            installed_layout,
            "VSIX installed-layout self-check",
        )
        _expect_failure(
            lambda: _assert_package_install_files(
                installed_layout,
                installed_layout + ("forbidden.txt",),
                "VSIX installed-layout extra file",
            ),
            "VSIX installed-layout extra file",
        )
        checks.append("vsix-install-layout")

        delivery_dir = root / "delivery"
        delivery_dir.mkdir()
        shutil.copy2(str(next(package_dir.glob("*.whl"))), str(delivery_dir))
        shutil.copy2(str(next(package_dir.glob("*.tar.gz"))), str(delivery_dir))
        shutil.copy2(str(pdf), str(delivery_dir))
        shutil.copy2(str(vsix), str(delivery_dir))
        (delivery_dir / "pyfcstm-0.0.0-windows-x86_64.exe").write_bytes(
            b"MZ" + b"safe" * 16
        )
        (delivery_dir / "pyfcstm-0.0.0-linux-x86_64").write_bytes(
            b"\x7fELF" + b"safe" * 16
        )
        delivery_files = _classify_delivery_files(delivery_dir)
        _assert_delivery_signatures(delivery_files)
        _assert_delivery_content_clean(
            "delivery fixture",
            (path.name for path in delivery_files.values()),
            {path.name: path.read_bytes() for path in delivery_files.values()},
        )
        checks.append("delivery-six-file-positive")
        extra_delivery = root / "delivery-extra"
        shutil.copytree(str(delivery_dir), str(extra_delivery))
        (extra_delivery / "report.json").write_text("{}\n", encoding="utf-8")
        _expect_failure(
            lambda: _classify_delivery_files(extra_delivery),
            "delivery exact file count",
        )
        checks.append("delivery-file-count-negative")

        expected_templates = root / "templates-expected"
        actual_templates = root / "templates-actual"
        _create_template_asset_fixture(expected_templates, metadata_variant=False)
        _create_template_asset_fixture(actual_templates, metadata_variant=True)
        validate_template_assets(actual_templates, expected_templates)
        checks.append("template-metadata-only-positive")
        tampered_entry = root / "templates-bad-entry"
        _create_template_asset_fixture(
            tampered_entry, metadata_variant=True, tamper="entry"
        )
        _expect_failure(
            lambda: validate_template_assets(tampered_entry, expected_templates),
            "template entry tamper",
        )
        checks.append("template-entry-tamper")
        tampered_payload = root / "templates-bad-payload"
        _create_template_asset_fixture(
            tampered_payload, metadata_variant=True, tamper="payload"
        )
        _expect_failure(
            lambda: validate_template_assets(tampered_payload, expected_templates),
            "template payload tamper",
        )
        checks.append("template-payload-tamper")
        extra_archive = root / "templates-extra-archive"
        _create_template_asset_fixture(
            extra_archive, metadata_variant=True, tamper="extra-archive"
        )
        _expect_failure(
            lambda: validate_template_assets(extra_archive, expected_templates),
            "template extra archive",
        )
        checks.append("template-extra-archive")
        parsed_pdf = _build_parser().parse_args(
            ["pdf", "--build-root", str(pdf_build_root)]
        )
        if parsed_pdf.build_root != pdf_build_root:
            raise ArtifactValidationError(
                "self-check PDF parser did not preserve --build-root"
            )
        if any(
            hasattr(parsed_pdf, name)
            for name in ("pdf", "text_file", "metadata_file", "outline_file")
        ):
            raise ArtifactValidationError(
                "formal PDF CLI unexpectedly exposes sidecar evidence options"
            )
        checks.append("pdf-cli-build-root-only")
        parsed = _build_parser().parse_args(
            [
                "vsix",
                "--path",
                str(vsix),
                "--source",
                str(pdf),
                "--report",
                str(root / "report.json"),
            ]
        )
        if parsed.path != vsix or parsed.report != root / "report.json":
            raise ArtifactValidationError(
                "self-check CLI parser did not preserve --path/--source/--report"
            )
        checks.append("cli-final-options")
    return {"status": "ok", "checks": checks}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the acceptance artifact checker command-line interface.

    :param argv: Optional command-line arguments excluding the program name.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int

    Example::

        >>> main(['--check'])  # doctest: +SKIP
        0
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = getattr(args, "report", None)
    try:
        if args.check:
            summary = run_self_check()
        elif args.command == "packages":
            summary = validate_packages(
                args.artifact_dir,
                install_smoke=args.install_smoke,
                python=args.python,
                assert_isolated=args.assert_isolated,
                source=args.source,
            )
        elif args.command == "executable":
            summary = validate_executable_inventory(
                executable=args.path,
                source=args.source,
                plantuml_jar=args.plantuml_jar,
                archive_viewer=args.archive_viewer,
            )
        elif args.command == "pdf":
            summary = validate_pdf_artifact(
                build_root=args.build_root,
                min_pages=args.min_pages,
                max_pages=args.max_pages,
                min_text_chars=args.min_text_chars,
            )
        elif args.command == "vsix":
            summary = validate_vsix(
                args.path,
                install_smoke=args.install_smoke,
                code=args.code_bin,
                source=args.source,
            )
        elif args.command == "delivery":
            summary = validate_delivery_bundle(args.delivery_dir)
        elif args.command == "template-assets":
            summary = validate_template_assets(
                args.packaged,
                expected_dir=args.expected_dir,
                source_dir=args.source,
            )
        else:
            parser.error("choose a subcommand or --check")
            return 2
    except ArtifactValidationError as error:
        # ArtifactValidationError is the expected validation failure contract.
        if report is not None:
            try:
                _write_json_report(
                    report,
                    {
                        "status": "failed",
                        "command": args.command or "self-check",
                        "error": str(error),
                    },
                )
            except ArtifactValidationError as report_error:
                # Report writes can fail independently after artifact validation.
                print(
                    "acceptance artifact report failed: {0}".format(report_error),
                    file=sys.stderr,
                )
        print("acceptance artifact check failed: {0}".format(error), file=sys.stderr)
        return 1
    if report is not None:
        try:
            _write_json_report(
                report,
                {
                    "status": "passed",
                    "command": args.command or "self-check",
                    "result": summary,
                },
            )
        except ArtifactValidationError as error:
            # ArtifactValidationError reports an unusable requested report path.
            print(
                "acceptance artifact check failed: {0}".format(error), file=sys.stderr
            )
            return 1
    if getattr(args, "json", False):
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("acceptance artifact check passed: {0}".format(_format_summary(summary)))
    return 0


# Private helpers intentionally stay below the public CLI surface.


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate acceptance delivery artifacts."
    )
    parser.add_argument(
        "--check", action="store_true", help="run temporary self-check fixtures"
    )
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    parser.add_argument("--report", type=Path, help="write a JSON validation report")
    subparsers = parser.add_subparsers(dest="command")

    packages = subparsers.add_parser(
        "packages", help="validate wheel and sdist archives"
    )
    packages.add_argument("--artifact-dir", type=Path, required=True)
    packages.add_argument("--source", type=Path)
    packages.add_argument("--install-smoke", action="store_true")
    packages.add_argument("--python", default=sys.executable)
    packages.add_argument("--assert-isolated", action="store_true")
    _add_subcommand_report(packages)

    executable = subparsers.add_parser(
        "executable", help="validate PyInstaller inventory"
    )
    executable.add_argument(
        "--path", "--executable", dest="path", type=Path, required=True
    )
    executable.add_argument("--source", type=Path, required=True)
    executable.add_argument("--plantuml-jar", type=Path, required=True)
    executable.add_argument("--archive-viewer", default="pyi-archive_viewer")
    _add_subcommand_report(executable)

    pdf = subparsers.add_parser("pdf", help="validate a real acceptance PDF build")
    pdf.add_argument("--build-root", type=Path, required=True)
    pdf.add_argument("--min-pages", type=int, default=500)
    pdf.add_argument("--max-pages", type=int, default=1000)
    pdf.add_argument("--min-text-chars", type=int, default=250_000)
    _add_subcommand_report(pdf)

    vsix = subparsers.add_parser("vsix", help="validate acceptance VSIX archive")
    vsix.add_argument("--path", "--vsix", dest="path", type=Path, required=True)
    vsix.add_argument("--source", type=Path)
    vsix.add_argument("--install-smoke", action="store_true")
    vsix.add_argument("--code-bin", "--code", dest="code_bin", default="code")
    _add_subcommand_report(vsix)

    delivery = subparsers.add_parser(
        "delivery", help="validate the consolidated six-file delivery"
    )
    delivery.add_argument("--delivery-dir", type=Path, required=True)
    _add_subcommand_report(delivery)

    templates = subparsers.add_parser("template-assets", help="compare template assets")
    templates.add_argument(
        "--packaged", "--actual-dir", dest="packaged", type=Path, required=True
    )
    templates.add_argument("--source", type=Path)
    templates.add_argument("--expected-dir", type=Path)
    _add_subcommand_report(templates)
    return parser


def _add_subcommand_report(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--report",
        type=Path,
        default=argparse.SUPPRESS,
        help="write a JSON validation report",
    )


def _format_summary(summary: Mapping[str, object]) -> str:
    parts = []
    for key in sorted(summary):
        value = summary[key]
        if isinstance(value, (list, tuple)):
            value_text = ",".join(str(item) for item in value)
        else:
            value_text = str(value)
        parts.append("{0}={1}".format(key, value_text))
    return "; ".join(parts)


def _normalize_entry(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _classify_delivery_files(delivery_dir: Path) -> Mapping[str, Path]:
    if not delivery_dir.is_dir():
        raise ArtifactValidationError(
            "delivery directory does not exist: {0}".format(delivery_dir)
        )
    paths = sorted(path for path in delivery_dir.iterdir() if path.is_file())
    if len(paths) != 6:
        raise ArtifactValidationError(
            "expected exactly six delivery files, got {0}: {1}".format(
                len(paths), [path.name for path in paths]
            )
        )

    def unique(pattern: str, label: str) -> Path:
        matches = [path for path in paths if re.fullmatch(pattern, path.name)]
        if len(matches) != 1:
            raise ArtifactValidationError(
                "expected one {0} matching {1!r}, got {2}".format(
                    label, pattern, [path.name for path in matches]
                )
            )
        return matches[0]

    wheel = unique(r"pyfcstm-([0-9][^-]*)-py3-none-any\.whl", "wheel")
    version_match = re.fullmatch(r"pyfcstm-([0-9][^-]*)-py3-none-any\.whl", wheel.name)
    if version_match is None:  # pragma: no cover - unique matched above
        raise ArtifactValidationError("cannot parse wheel version: {0}".format(wheel))
    version = re.escape(version_match.group(1))
    return {
        "wheel": wheel,
        "sdist": unique(r"pyfcstm-{0}\.tar\.gz".format(version), "sdist"),
        "pdf": unique(r"pyfcstm-acceptance-zh\.pdf", "PDF"),
        "vsix": unique(r"fcstm-language-support-([0-9][^-]*)\.vsix", "VSIX"),
        "windows_executable": unique(
            r"pyfcstm-{0}-windows-x86_64\.exe".format(version),
            "Windows executable",
        ),
        "linux_executable": unique(
            r"pyfcstm-{0}-linux-x86_64".format(version), "Linux executable"
        ),
    }


def _assert_delivery_signatures(files: Mapping[str, Path]) -> None:
    signatures = {
        "wheel": b"PK",
        "sdist": b"\x1f\x8b",
        "pdf": b"%PDF",
        "vsix": b"PK",
        "windows_executable": b"MZ",
        "linux_executable": b"\x7fELF",
    }
    for key, signature in signatures.items():
        path = files[key]
        try:
            actual = path.read_bytes()[: len(signature)]
        except OSError as error:
            # Path.read_bytes raises OSError for unreadable delivery files.
            raise ArtifactValidationError(
                "cannot read delivery file {0}: {1}".format(path, error)
            ) from error
        if actual != signature:
            raise ArtifactValidationError(
                "invalid delivery signature for {0}: expected {1!r}, got {2!r}".format(
                    path.name, signature, actual
                )
            )


def _assert_delivery_content_clean(
    label: str,
    names: Iterable[str],
    payloads: Mapping[str, bytes],
) -> Mapping[str, object]:
    """
    Reject forbidden acceptance-delivery terms in names or payload bytes.

    The scan is ASCII case-insensitive and recursively opens ZIP payloads, so
    compressed template archives and VSIX members cannot hide a forbidden
    term. The returned zero-count report is suitable for CI evidence but is
    never added to the delivery bundle itself.

    :param label: Human-readable artifact label.
    :type label: str
    :param names: Artifact and member names to scan.
    :type names: collections.abc.Iterable[str]
    :param payloads: Named raw payloads to scan.
    :type payloads: collections.abc.Mapping[str, bytes]
    :return: Zero-count scan summary.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If a forbidden term is present.

    Example::

        >>> _assert_delivery_content_clean('fixture', ('safe.txt',), {'safe.txt': b'ok'})['terms']
        {'github': 0, 's714': 0}
    """
    counts = {term: 0 for term in FORBIDDEN_DELIVERY_TERMS}
    matches: Dict[str, List[str]] = {term: [] for term in FORBIDDEN_DELIVERY_TERMS}
    scanned_items = 0
    scanned_bytes = 0

    def scan_bytes(origin: str, data: bytes, depth: int = 0) -> None:
        nonlocal scanned_items, scanned_bytes
        scanned_items += 1
        scanned_bytes += len(data)
        lowered = data.lower()
        for term in FORBIDDEN_DELIVERY_TERMS:
            count = lowered.count(term.encode("ascii"))
            counts[term] += count
            if count:
                matches[term].append("{0} ({1})".format(origin, count))
        if depth >= 4 or not data.startswith(b"PK"):
            return
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
                for info in archive.infolist():
                    scan_name("{0}!{1}".format(origin, info.filename))
                    scan_bytes(
                        "{0}!{1}".format(origin, info.filename),
                        archive.read(info.filename),
                        depth + 1,
                    )
        except zipfile.BadZipFile as error:
            # A PK-prefixed non-ZIP binary is still covered by its raw-byte scan.
            if origin.lower().endswith((".zip", ".whl", ".vsix")):
                raise ArtifactValidationError(
                    "{0} contains an invalid ZIP payload {1}: {2}".format(
                        label, origin, error
                    )
                ) from error

    def scan_name(name: str) -> None:
        lowered = name.lower()
        for term in FORBIDDEN_DELIVERY_TERMS:
            count = lowered.count(term)
            counts[term] += count
            if count:
                matches[term].append("name:{0} ({1})".format(name, count))

    for name in names:
        scan_name(str(name))
    for origin, payload in payloads.items():
        scan_bytes(str(origin), payload)

    if any(counts.values()):
        details = {
            term: matches[term] for term in FORBIDDEN_DELIVERY_TERMS if matches[term]
        }
        raise ArtifactValidationError(
            "{0} contains forbidden delivery terms: {1}".format(
                label, json.dumps(details, ensure_ascii=False, sort_keys=True)
            )
        )
    return {
        "terms": counts,
        "scanned_items": scanned_items,
        "scanned_bytes": scanned_bytes,
    }


def _extract_printable_strings(data: bytes) -> bytes:
    """
    Extract printable ASCII runs for explicit executable string scanning.

    :param data: Raw executable bytes.
    :type data: bytes
    :return: Newline-separated printable strings of at least four bytes.
    :rtype: bytes

    Example::

        >>> _extract_printable_strings(b'\\x00hello\\x00x')
        b'hello'
    """
    return b"\n".join(re.findall(rb"[\x20-\x7e]{4,}", data))


def _read_pyinstaller_payloads(executable: Path) -> Mapping[str, bytes]:
    """
    Read root and embedded PYZ payloads from a PyInstaller executable.

    :param executable: PyInstaller executable to inspect.
    :type executable: pathlib.Path
    :return: Payload names mapped to uncompressed bytes.
    :rtype: collections.abc.Mapping[str, bytes]
    :raises ArtifactValidationError: If the executable archive cannot be read.

    Example::

        >>> _read_pyinstaller_payloads(Path('/missing'))  # doctest: +SKIP
        {}
    """
    try:
        from PyInstaller.archive.readers import (
            ArchiveReadError,
            CArchiveReader,
            PKG_ITEM_PYZ,
        )
    except ImportError as error:
        # PyInstaller is the executable builder and supplies its archive reader.
        raise ArtifactValidationError(
            "PyInstaller archive reader is required for executable payload scanning"
        ) from error

    try:
        archive = CArchiveReader(str(executable))
        payloads: Dict[str, bytes] = {}
        for name, entry in archive.toc.items():
            payload = archive.extract(name)
            if payload is not None:
                payloads["PKG/{0}".format(name)] = payload
            if entry[-1] != PKG_ITEM_PYZ:
                continue
            embedded = archive.open_embedded_archive(name)
            for embedded_name in embedded.toc:
                embedded_payload = embedded.extract(embedded_name, raw=True)
                if embedded_payload is not None:
                    payloads["PKG/{0}!{1}".format(name, embedded_name)] = (
                        embedded_payload
                    )
        return payloads
    except (ArchiveReadError, OSError, ValueError, zlib.error) as error:
        # Reader construction/extraction raises these for malformed PKG/PYZ data.
        raise ArtifactValidationError(
            "cannot extract PyInstaller payloads from {0}: {1}".format(
                executable, error
            )
        ) from error


def _read_zip_entries(path: Path) -> Tuple[Tuple[str, ...], Dict[str, bytes]]:
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            entries = tuple(
                sorted(
                    _normalize_entry(info.filename)
                    for info in zf.infolist()
                    if not info.is_dir()
                )
            )
            payloads = {
                _normalize_entry(info.filename): zf.read(info)
                for info in zf.infolist()
                if not info.is_dir()
            }
    except zipfile.BadZipFile as error:
        # ZipFile raises BadZipFile when an artifact has invalid ZIP structure.
        raise ArtifactValidationError(
            "invalid ZIP archive {0}: {1}".format(path, error)
        ) from error
    except OSError as error:
        # ZipFile and ZipExtFile raise OSError for unreadable archive storage.
        raise ArtifactValidationError(
            "cannot read ZIP archive {0}: {1}".format(path, error)
        ) from error
    return entries, payloads


def _read_tar_entries(path: Path) -> Tuple[Tuple[str, ...], Dict[str, bytes]]:
    try:
        with tarfile.open(str(path), "r:gz") as tf:
            members = [member for member in tf.getmembers() if member.isfile()]
            entries = tuple(sorted(_normalize_entry(member.name) for member in members))
            payloads: Dict[str, bytes] = {}
            for member in members:
                extracted = tf.extractfile(member)
                if extracted is None:
                    raise ArtifactValidationError(
                        "cannot extract tar member {0}".format(member.name)
                    )
                payloads[_normalize_entry(member.name)] = extracted.read()
    except tarfile.TarError as error:
        # tarfile raises TarError when an sdist has invalid archive structure.
        raise ArtifactValidationError(
            "invalid tar archive {0}: {1}".format(path, error)
        ) from error
    except OSError as error:
        # tarfile raises OSError for unreadable sdist storage.
        raise ArtifactValidationError(
            "cannot read tar archive {0}: {1}".format(path, error)
        ) from error
    return entries, payloads


def _strip_single_root(entries: Iterable[str]) -> Tuple[str, ...]:
    stripped = []
    roots = set()
    for entry in entries:
        parts = entry.split("/", 1)
        if len(parts) == 2:
            roots.add(parts[0])
            stripped.append(parts[1])
        else:
            stripped.append(entry)
    if len(roots) > 1:
        raise ArtifactValidationError(
            "sdist has multiple archive roots: {0}".format(sorted(roots))
        )
    return tuple(sorted(stripped))


def _strip_single_root_payloads(payloads: Mapping[str, bytes]) -> Dict[str, bytes]:
    stripped: Dict[str, bytes] = {}
    for entry, payload in payloads.items():
        parts = entry.split("/", 1)
        stripped[parts[1] if len(parts) == 2 else entry] = payload
    return stripped


def _assert_required(
    label: str, entries: Iterable[str], required: Iterable[str]
) -> None:
    entry_set = set(entries)
    missing = [item for item in required if item not in entry_set]
    if missing:
        raise ArtifactValidationError(
            "{0} missing required entries: {1}".format(label, ", ".join(missing))
        )


def _assert_package_filenames(wheel: Path, sdist: Path) -> None:
    wheel_parts = wheel.name[: -len(".whl")].split("-")
    if (
        len(wheel_parts) not in (5, 6)
        or wheel_parts[0] != "pyfcstm"
        or not wheel_parts[1]
    ):
        raise ArtifactValidationError(
            "wheel filename must use the normal pyfcstm wheel form: {0}".format(
                wheel.name
            )
        )
    sdist_prefix = "pyfcstm-"
    sdist_suffix = ".tar.gz"
    if not sdist.name.startswith(sdist_prefix) or not sdist.name.endswith(sdist_suffix):
        raise ArtifactValidationError(
            "sdist filename must use the normal pyfcstm source form: {0}".format(
                sdist.name
            )
        )
    wheel_version = wheel_parts[1]
    sdist_version = sdist.name[len(sdist_prefix) : -len(sdist_suffix)]
    if not sdist_version or wheel_version != sdist_version:
        raise ArtifactValidationError(
            "wheel/sdist filename versions differ: wheel={0!r}, sdist={1!r}".format(
                wheel_version, sdist_version
            )
        )


def _assert_exact_entries(
    label: str, entries: Iterable[str], required: Iterable[str]
) -> None:
    actual_set = set(entries)
    required_set = set(required)
    missing = sorted(required_set - actual_set)
    extra = sorted(actual_set - required_set)
    if missing or extra:
        raise ArtifactValidationError(
            "{0} entry set mismatch: missing={1}; extra={2}".format(
                label, missing, extra
            )
        )


def _assert_required_pattern_groups(
    label: str,
    entries: Iterable[str],
    pattern_groups: Iterable[Iterable[str]],
) -> None:
    entry_list = tuple(entries)
    missing_groups = []
    for patterns in pattern_groups:
        pattern_tuple = tuple(patterns)
        if not any(
            fnmatch.fnmatch(entry, pattern)
            for entry in entry_list
            for pattern in pattern_tuple
        ):
            missing_groups.append(" or ".join(pattern_tuple))
    if missing_groups:
        raise ArtifactValidationError(
            "{0} missing entries matching: {1}".format(label, "; ".join(missing_groups))
        )


def _assert_denylist(
    label: str, entries: Iterable[str], patterns: Iterable[str]
) -> None:
    violations = []
    for entry in entries:
        for pattern in patterns:
            if fnmatch.fnmatch(entry, pattern):
                violations.append("{0} matches {1}".format(entry, pattern))
    if violations:
        raise ArtifactValidationError(
            "{0} contains forbidden entries: {1}".format(label, "; ".join(violations))
        )


def _assert_wheel_allowlist(entries: Iterable[str]) -> None:
    allowed_data = set(WHEEL_REQUIRED)
    invalid = []
    for entry in entries:
        if entry.startswith("pyfcstm/"):
            if entry.endswith(".py") or entry in allowed_data:
                continue
            invalid.append(entry)
            continue
        if ".dist-info/" in entry:
            relative = entry.split(".dist-info/", 1)[1]
            if relative in WHEEL_DIST_INFO_REQUIRED or relative == "top_level.txt":
                continue
            if relative in WHEEL_DIST_INFO_LICENSE_PATHS:
                continue
        invalid.append(entry)
    if invalid:
        raise ArtifactValidationError(
            "wheel contains entries outside the runtime allowlist: {0}".format(
                ", ".join(sorted(invalid))
            )
        )


def _assert_sdist_allowlist(entries: Iterable[str]) -> None:
    allowed_root = {
        "setup.py",
        "setup.cfg",
        "MANIFEST.in",
        "requirements.txt",
        "README_ACCEPTANCE.md",
        "LICENSE",
        "PKG-INFO",
    }
    allowed_data = set(SDIST_REQUIRED)
    invalid = []
    for entry in entries:
        if entry in allowed_root:
            continue
        if entry.startswith("pyfcstm.egg-info/"):
            continue
        if entry.startswith("pyfcstm/"):
            if entry.endswith(".py") or entry in allowed_data:
                continue
            if entry.startswith("pyfcstm/dsl/grammar/") and entry.endswith(
                (".g4", ".interp", ".tokens")
            ):
                continue
        invalid.append(entry)
    if invalid:
        raise ArtifactValidationError(
            "sdist contains entries outside the source allowlist: {0}".format(
                ", ".join(sorted(invalid))
            )
        )


def _assert_wheel_dist_info(
    entries: Iterable[str], payloads: Mapping[str, bytes]
) -> None:
    entry_tuple = tuple(sorted(entries))
    dist_info_dirs = sorted(
        {
            entry.split("/", 1)[0]
            for entry in entries
            if entry.endswith(".dist-info/METADATA")
        }
    )
    if len(dist_info_dirs) != 1:
        raise ArtifactValidationError(
            "wheel must contain exactly one dist-info METADATA, found {0}".format(
                dist_info_dirs
            )
        )
    dist_info = dist_info_dirs[0]
    required = ["{0}/{1}".format(dist_info, name) for name in WHEEL_DIST_INFO_REQUIRED]
    _assert_required("wheel dist-info", entries, required)
    license_entries = [
        "{0}/{1}".format(dist_info, name)
        for name in WHEEL_DIST_INFO_LICENSE_PATHS
        if "{0}/{1}".format(dist_info, name) in entry_tuple
    ]
    if len(license_entries) != 1:
        raise ArtifactValidationError(
            "wheel dist-info must contain exactly one LICENSE file, found {0}".format(
                license_entries
            )
        )
    entry_points = _decode_payload(
        payloads, "{0}/entry_points.txt".format(dist_info), "wheel entry points"
    )
    if "pyfcstm" not in entry_points or "pygments.lexers" not in entry_points:
        raise ArtifactValidationError(
            "wheel entry_points.txt must declare console script and Pygments lexer"
        )
    record_path = "{0}/RECORD".format(dist_info)
    record_text = _decode_payload(payloads, record_path, "wheel RECORD")
    record_entries = tuple(
        sorted(
            _normalize_entry(row[0])
            for row in csv.reader(record_text.splitlines())
            if row and row[0]
        )
    )
    if record_entries != entry_tuple:
        missing = sorted(set(entry_tuple) - set(record_entries))
        extra = sorted(set(record_entries) - set(entry_tuple))
        raise ArtifactValidationError(
            "wheel RECORD entry set mismatch: missing={0}; extra={1}".format(
                missing, extra
            )
        )


def _assert_acceptance_metadata(payloads: Mapping[str, bytes]) -> None:
    metadata_paths = [
        entry for entry in payloads if entry.endswith(".dist-info/METADATA")
    ]
    metadata = _decode_payload(payloads, metadata_paths[0], "wheel metadata")
    _assert_text_contains(
        "wheel METADATA",
        metadata,
        ("Name: pyfcstm", "Requires-Python", "Requires-Dist", "项目验收"),
    )
    _assert_text_excludes(
        "wheel METADATA",
        metadata,
        (
            "Provides-Extra: dev",
            "Provides-Extra: doc",
            "Provides-Extra: test",
            "LLM 评估",
        ),
    )


def _assert_sdist_readme(payloads: Mapping[str, bytes]) -> None:
    normalized = _strip_single_root_payloads(payloads)
    readme = _decode_payload(
        normalized, "README_ACCEPTANCE.md", "sdist README_ACCEPTANCE.md"
    )
    first_line = readme.splitlines()[0] if readme.splitlines() else ""
    if "pyfcstm" not in first_line.lower():
        raise ArtifactValidationError(
            "sdist README_ACCEPTANCE.md first line must identify pyfcstm"
        )
    _assert_text_contains("sdist README_ACCEPTANCE.md", readme, ("项目验收",))


def _decode_payload(payloads: Mapping[str, bytes], path: str, label: str) -> str:
    if path not in payloads:
        raise ArtifactValidationError("{0} payload missing: {1}".format(label, path))
    try:
        return payloads[path].decode("utf-8")
    except UnicodeDecodeError as error:
        # bytes.decode raises UnicodeDecodeError for non-UTF-8 metadata payloads.
        raise ArtifactValidationError(
            "{0} is not UTF-8: {1}".format(label, error)
        ) from error


def _load_json_payload(
    payloads: Mapping[str, bytes], path: str, label: str
) -> Mapping[str, object]:
    text = _decode_payload(payloads, path, label)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as error:
        # json.loads raises JSONDecodeError for malformed archive metadata.
        raise ArtifactValidationError(
            "{0} is invalid JSON: {1}".format(label, error)
        ) from error
    if not isinstance(obj, dict):
        raise ArtifactValidationError("{0} must be a JSON object".format(label))
    return obj


def _run_package_install_smoke(
    wheel: Path, sdist: Path, python: str, assert_isolated: bool, source: Optional[Path]
) -> Mapping[str, object]:
    if source is not None and not source.is_file():
        raise ArtifactValidationError(
            "package smoke source does not exist: {0}".format(source)
        )
    wheel_entries, _ = _read_zip_entries(wheel)
    wheel_install_files = _wheel_install_files(wheel_entries)
    results: List[Mapping[str, object]] = []
    clean_environment = _clean_subprocess_environment()
    with tempfile.TemporaryDirectory(prefix="acceptance-package-smoke-") as directory:
        root = Path(directory)
        empty_cwd = root / "empty-cwd"
        empty_cwd.mkdir()
        environments = []
        for artifact in (wheel, sdist):
            venv = root / artifact.name.replace(".", "-")
            _run_command(
                [python, "-m", "venv", str(venv)],
                cwd=empty_cwd,
                env=clean_environment,
            )
            venv_python = venv / (
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            install_command = [str(venv_python), "-m", "pip", "install"]
            if artifact.name.endswith(".tar.gz"):
                install_command.append("--use-pep517")
            install_command.append(str(artifact.resolve()))
            _run_command(
                install_command,
                cwd=empty_cwd,
                env=clean_environment,
            )
            environments.append((artifact, venv, venv_python))

        for artifact, venv, venv_python in environments:
            forbidden_roots = [repository_root()]
            forbidden_roots.extend(
                other_venv for _, other_venv, _ in environments if other_venv != venv
            )
            smoke = _package_smoke_script(
                assert_isolated,
                source.resolve() if source is not None else None,
                forbidden_roots,
            )
            cli_path = venv / (
                "Scripts/pyfcstm.exe" if os.name == "nt" else "bin/pyfcstm"
            )
            _run_command(
                [str(cli_path), "--help"], cwd=empty_cwd, env=clean_environment
            )
            completed = _run_command(
                [str(venv_python), "-I", "-c", smoke],
                cwd=empty_cwd,
                env=clean_environment,
            )
            payload = _parse_json_command_output(
                completed.stdout, "package smoke for {0}".format(artifact.name)
            )
            package_files = payload.get("package_files")
            if not isinstance(package_files, list) or not all(
                isinstance(item, str) for item in package_files
            ):
                raise ArtifactValidationError(
                    "package smoke did not report a string package_files list: {0}".format(
                        artifact.name
                    )
                )
            distribution_files = payload.get("distribution_files")
            if not isinstance(distribution_files, list) or not all(
                isinstance(item, str) for item in distribution_files
            ):
                raise ArtifactValidationError(
                    "package smoke did not report a string distribution_files list: {0}".format(
                        artifact.name
                    )
                )
            _assert_package_install_files(
                wheel_install_files,
                distribution_files,
                "installed distribution files for {0}".format(artifact.name),
            )
            results.append(
                {
                    "artifact": artifact.name,
                    "python": payload.get("executable"),
                    "import_path": payload.get("import_path"),
                    "sys_path": payload.get("sys_path"),
                    "package_files": len(package_files),
                    "distribution_files": len(distribution_files),
                    "templates": payload.get("templates"),
                    "generated_files": payload.get("generated_files"),
                    "lexer": payload.get("lexer"),
                }
            )
    return {
        "wheel_install_files": len(wheel_install_files),
        "artifacts": results,
    }


def _package_smoke_script(
    assert_isolated: bool,
    source: Optional[Path],
    forbidden_roots: Sequence[Path],
) -> str:
    source_text = str(source) if source is not None else ""
    forbidden_text = [str(path.resolve()) for path in forbidden_roots]
    return "\n".join(
        [
            "import csv, importlib.util, json, os, pathlib, site, sys, sysconfig, tempfile",
            "import pyfcstm",
            "from pygments.lexers import get_lexer_by_name",
            "from pyfcstm.diagnostics import inspect_model",
            "from pyfcstm.dsl import parse_state_machine_dsl",
            "from pyfcstm.model import load_state_machine_from_text",
            "from pyfcstm.render import StateMachineCodeRenderer",
            "from pyfcstm.simulate import SimulationRuntime",
            "from pyfcstm.template import extract_template, list_templates",
            "assert importlib.util.find_spec('pyfcstm.llm') is None",
            "templates = list_templates()",
            "assert templates == ['c', 'c_poll', 'cpp', 'cpp_poll', 'python'], templates",
            "paths = [pathlib.Path(sysconfig.get_paths()[k]).resolve() for k in ('purelib','platlib')]",
            "module = pathlib.Path(pyfcstm.__file__).resolve()",
            "package_root = module.parent",
            "def _under(path, root):",
            "    try:",
            "        return os.path.commonpath([str(path), str(root)]) == str(root)",
            "    except ValueError:",
            "        # os.path.commonpath raises ValueError for paths on different drives.",
            "        return False",
            (
                "assert any(_under(module, path) for path in paths), "
                "{'import_path': str(module), 'site_paths': [str(p) for p in paths], "
                "'sys_path': sys.path}"
                if assert_isolated
                else "assert pyfcstm.__file__"
            ),
            "forbidden = [pathlib.Path(item).resolve() for item in {0!r}]".format(
                forbidden_text
            ),
            "user_site = pathlib.Path(site.getusersitepackages()).resolve()",
            "forbidden.append(user_site)",
            (
                "assert not any(_under(module, path) for path in forbidden), "
                "{'import_path': str(module), 'forbidden': [str(p) for p in forbidden], "
                "'sys_path': sys.path}"
                if assert_isolated
                else "assert module.is_file()"
            ),
            "source_path = pathlib.Path({0!r}).resolve() if {0!r} else None".format(
                source_text
            ),
            "source_code = source_path.read_text(encoding='utf-8') if source_path else 'state Root { state Idle; [*] -> Idle; }'",
            "ast = parse_state_machine_dsl(source_code)",
            "assert ast is not None",
            "model = load_state_machine_from_text(source_code, path=str(source_path or pathlib.Path.cwd()))",
            "inspect_text = json.dumps(inspect_model(model).to_json(), ensure_ascii=False)",
            "assert isinstance(json.loads(inspect_text), dict)",
            "runtime = SimulationRuntime(model)",
            "runtime.cycle()",
            "assert runtime.current_state is not None",
            "with tempfile.TemporaryDirectory(prefix='pyfcstm-installed-template-') as directory:",
            "    temp_root = pathlib.Path(directory)",
            "    template_dir = extract_template('python', str(temp_root / 'template'))",
            "    output_dir = temp_root / 'generated'",
            "    StateMachineCodeRenderer(template_dir).render(model, str(output_dir), clear_previous_directory=True)",
            "    generated = sorted(str(path.relative_to(output_dir)) for path in output_dir.rglob('*') if path.is_file() and path.stat().st_size > 0)",
            "    assert generated",
            "lexer = get_lexer_by_name('fcstm')",
            "assert lexer.__class__.__module__ == 'pyfcstm.highlight.pygments_lexer'",
            "package_files = sorted('pyfcstm/' + path.relative_to(package_root).as_posix() for path in package_root.rglob('*') if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')",
            "assert not any(path.startswith('pyfcstm/llm/') for path in package_files)",
            "assert 'pyfcstm/diagnostics/inspect_llm_report_schema.json' not in package_files",
            "record_paths = sorted(package_root.parent.glob('pyfcstm-*.dist-info/RECORD'))",
            "assert len(record_paths) == 1, [str(path) for path in record_paths]",
            "dist_info = record_paths[0].parent.name",
            "with record_paths[0].open(newline='', encoding='utf-8') as record_file:",
            "    recorded = [row[0].replace('\\\\', '/') for row in csv.reader(record_file) if row and row[0]]",
            "generated_metadata = {dist_info + '/INSTALLER', dist_info + '/REQUESTED', dist_info + '/direct_url.json'}",
            "distribution_files = sorted(path for path in recorded if not path.startswith('../../../bin/') and '/__pycache__/' not in path and not path.endswith('.pyc') and path != dist_info + '/RECORD' and path not in generated_metadata)",
            "print(json.dumps({'executable': sys.executable, 'import_path': str(module), 'sys_path': sys.path, 'package_files': package_files, 'distribution_files': distribution_files, 'templates': templates, 'generated_files': generated, 'lexer': lexer.__class__.__module__ + ':' + lexer.__class__.__name__}, ensure_ascii=False, sort_keys=True))",
        ]
    )


def _read_inventory_entries(inventory: Path) -> Tuple[str, ...]:
    text = _read_text_evidence(inventory)
    return _parse_inventory_entries(text)


def _assert_executable_inventory_entries(
    entries: Iterable[str], delivery_platform: str = "windows"
) -> None:
    normalized = tuple(entries)
    _assert_required("executable inventory", normalized, EXECUTABLE_REQUIRED)
    _assert_required_pattern_groups(
        "executable inventory", normalized, EXECUTABLE_REQUIRED_PATTERN_GROUPS
    )
    if delivery_platform == "windows":
        platform_groups = WINDOWS_EXECUTABLE_REQUIRED_PATTERN_GROUPS
    elif delivery_platform == "linux":
        platform_groups = LINUX_EXECUTABLE_REQUIRED_PATTERN_GROUPS
    else:
        raise ArtifactValidationError(
            "unsupported executable delivery platform: {0}".format(delivery_platform)
        )
    _assert_required_pattern_groups(
        "{0} executable inventory".format(delivery_platform),
        normalized,
        platform_groups,
    )
    _assert_denylist("executable inventory", normalized, EXECUTABLE_DENYLIST)
    _assert_delivery_content_clean("executable inventory", normalized, {})


def _parse_inventory_entries(text: str) -> Tuple[str, ...]:
    stripped = text.lstrip()
    if stripped.startswith("["):
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as error:
            # json.loads raises JSONDecodeError for malformed fixture reports.
            raise ArtifactValidationError(
                "invalid inventory JSON: {0}".format(error)
            ) from error
        if not isinstance(raw, list):
            raise ArtifactValidationError("inventory JSON must be a list")
        entries = [_normalize_entry(str(item)) for item in raw]
    else:
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            is_quoted_entry = line.endswith(("'", '"')) and (
                "," in line or line.startswith(("'", '"'))
            )
            if is_quoted_entry:
                try:
                    literal = ast.literal_eval("({0})".format(line))
                except (SyntaxError, ValueError) as error:
                    # ast.literal_eval raises SyntaxError/ValueError when an
                    # archive-viewer entry ends like a literal but is malformed.
                    raise ArtifactValidationError(
                        "invalid quoted PyInstaller inventory entry: {0!r}".format(line)
                    ) from error
                value = literal[-1] if isinstance(literal, tuple) else literal
                if not isinstance(value, str):
                    raise ArtifactValidationError(
                        "PyInstaller inventory entry path is not text: {0!r}".format(
                            value
                        )
                    )
                entries.append(_normalize_entry(value))
                continue
            if " " not in line and "\t" not in line:
                entries.append(_normalize_entry(line.strip(",\"'")))
    return tuple(sorted(set(entries)))


def _run_executable_smoke(
    executable: Path, source: Path, plantuml_jar: Path
) -> Mapping[str, object]:
    if not executable.is_file():
        raise ArtifactValidationError(
            "executable does not exist: {0}".format(executable)
        )
    if not source.is_file():
        raise ArtifactValidationError(
            "executable end-to-end source does not exist: {0}".format(source)
        )
    executable = executable.resolve()
    plantuml_jar = plantuml_jar.resolve()
    _assert_executable_platform_shape(executable)
    environment = _clean_subprocess_environment()
    environment["PLANTUML_JAR"] = str(plantuml_jar)
    java = _require_external_command(
        "java", "install a Java runtime compatible with the supplied PlantUML JAR"
    )
    plantuml_version = _run_command(
        [java, "-jar", str(plantuml_jar), "-version"], env=environment
    ).stdout.strip()
    if "PlantUML version" not in plantuml_version:
        raise ArtifactValidationError(
            "PlantUML JAR version probe produced unexpected output: {0}".format(
                plantuml_version
            )
        )
    with tempfile.TemporaryDirectory(
        prefix="acceptance-executable-smoke-"
    ) as directory:
        root = Path(directory)
        copied_source = root / "acceptance.fcstm"
        try:
            shutil.copy2(str(source.resolve()), str(copied_source))
        except OSError as error:
            # shutil.copy2 raises OSError when the acceptance source is unreadable.
            raise ArtifactValidationError(
                "cannot copy executable source {0}: {1}".format(source, error)
            ) from error

        help_text = _run_command(
            [str(executable), "--help"], cwd=root, env=environment
        ).stdout
        version_text = _run_command(
            [str(executable), "--version"], cwd=root, env=environment
        ).stdout
        version = _parse_executable_version(version_text)
        _assert_executable_filename(executable, version)
        command_help: Dict[str, str] = {}
        for command in CLI_COMMANDS:
            command_help[command] = _run_command(
                [str(executable), command, "--help"],
                cwd=root,
                env=environment,
            ).stdout
        commands = _assert_cli_help_contract(help_text, command_help["inspect"])

        inspect_human = root / "inspect.txt"
        _run_command(
            [
                str(executable),
                "inspect",
                "-i",
                str(copied_source),
                "--format",
                "human",
                "-o",
                str(inspect_human),
            ],
            cwd=root,
            env=environment,
        )
        _assert_nonempty_file(inspect_human, "inspect human output")

        inspect_json = root / "inspect.json"
        _run_command(
            [
                str(executable),
                "inspect",
                "-i",
                str(copied_source),
                "--format",
                "json",
                "-o",
                str(inspect_json),
            ],
            cwd=root,
            env=environment,
        )
        inspect_payload = _read_json_file(inspect_json)
        if not isinstance(inspect_payload, dict):
            raise ArtifactValidationError("inspect JSON output must be an object")

        plantuml_output = root / "machine.puml"
        _run_command(
            [
                str(executable),
                "plantuml",
                "-i",
                str(copied_source),
                "-o",
                str(plantuml_output),
            ],
            cwd=root,
            env=environment,
        )
        plantuml_text = _read_text_evidence(plantuml_output)
        _assert_text_contains(
            "PlantUML output", plantuml_text, ("@startuml", "@enduml")
        )

        diagrams = {}
        for render_type in ("png", "svg"):
            output = root / "machine.{0}".format(render_type)
            _run_command(
                [
                    str(executable),
                    "visualize",
                    "-i",
                    str(copied_source),
                    "-o",
                    str(output),
                    "--type",
                    render_type,
                    "--renderer",
                    "local",
                    "--no-open",
                ],
                cwd=root,
                env=environment,
            )
            _assert_diagram_file(output, render_type)
            diagrams[render_type] = output.stat().st_size

        simulation = _run_command(
            [
                str(executable),
                "simulate",
                "-i",
                str(copied_source),
                "-e",
                "cycle; current",
                "--no-color",
            ],
            cwd=root,
            env=environment,
        )
        if not simulation.stdout.strip():
            raise ArtifactValidationError("simulate batch output is empty")

        generated = {}
        for template_name in TEMPLATE_NAMES:
            output_dir = root / "generated" / template_name
            _run_command(
                [
                    str(executable),
                    "generate",
                    "-i",
                    str(copied_source),
                    "--template",
                    template_name,
                    "-o",
                    str(output_dir),
                    "--clear",
                ],
                cwd=root,
                env=environment,
            )
            generated[template_name] = _assert_nonempty_directory(
                output_dir, "generated {0} template output".format(template_name)
            )

        return {
            "commands": commands,
            "version": version,
            "source": str(source),
            "plantuml_jar": str(plantuml_jar),
            "plantuml_version": plantuml_version.splitlines()[0],
            "inspect_human_bytes": inspect_human.stat().st_size,
            "inspect_json_keys": len(inspect_payload),
            "plantuml_bytes": plantuml_output.stat().st_size,
            "diagrams": diagrams,
            "simulate_output_chars": len(simulation.stdout),
            "generated_files": generated,
        }


def _assert_cli_help_contract(top_help: str, inspect_help: str) -> Tuple[str, ...]:
    commands = _parse_click_commands(top_help)
    if commands != CLI_COMMANDS:
        raise ArtifactValidationError(
            "CLI command set mismatch: actual {0}, expected {1}".format(
                commands, CLI_COMMANDS
            )
        )
    choice_match = re.search(r"--format\s+\[([^\]]+)\]", inspect_help)
    if choice_match is None:
        raise ArtifactValidationError(
            "inspect help does not expose a parseable --format choice"
        )
    formats = tuple(sorted(item.strip() for item in choice_match.group(1).split("|")))
    if formats != ("human", "json"):
        raise ArtifactValidationError(
            "inspect format choices mismatch: actual {0}, expected ('human', 'json')".format(
                formats
            )
        )
    forbidden_patterns = (
        r"llm-json",
        r"llm-md",
        r"--enable-verify",
        r"bmc[_-]search",
        r"--max-complexity-tier",
        r"--max-call-count-scaling",
        r"--smt-timeout-ms",
        r"\bsmt\b",
    )
    found = [
        pattern
        for pattern in forbidden_patterns
        if re.search(pattern, inspect_help, re.IGNORECASE)
    ]
    if found:
        raise ArtifactValidationError(
            "inspect help exposes forbidden policy or format entries: {0}".format(
                ", ".join(found)
            )
        )
    return commands


def _parse_click_commands(help_text: str) -> Tuple[str, ...]:
    commands = []
    in_commands = False
    for line in help_text.splitlines():
        if line.strip() == "Commands:":
            in_commands = True
            continue
        if in_commands:
            match = re.match(r"^\s{2,}([a-zA-Z0-9_-]+)\s", line)
            if match:
                commands.append(match.group(1))
            elif line and not line.startswith(" "):
                break
    return tuple(sorted(commands))


def _assert_executable_platform_shape(executable: Path) -> None:
    if os.name == "nt":
        if executable.suffix.lower() != ".exe":
            raise ArtifactValidationError(
                "Windows executable path must end with .exe: {0}".format(executable)
            )
        try:
            magic = executable.read_bytes()[:2]
        except OSError as error:
            # Path.read_bytes raises OSError when the executable is unreadable.
            raise ArtifactValidationError(
                "cannot read executable {0}: {1}".format(executable, error)
            ) from error
        if magic != b"MZ":
            raise ArtifactValidationError(
                "Windows executable does not have PE MZ magic: {0}".format(executable)
            )
    else:
        if not os.access(str(executable), os.X_OK):
            raise ArtifactValidationError(
                "executable is not marked executable: {0}".format(executable)
            )
        try:
            magic = executable.read_bytes()[:4]
        except OSError as error:
            # Path.read_bytes raises OSError when the executable is unreadable.
            raise ArtifactValidationError(
                "cannot read executable {0}: {1}".format(executable, error)
            ) from error
        if magic != b"\x7fELF":
            raise ArtifactValidationError(
                "Linux executable does not have ELF magic: {0}".format(executable)
            )


def _assert_windows7_delivery_build_facts(
    os_name: str,
    system_name: str,
    python_version: Tuple[int, int],
    pointer_bits: int,
    github_actions: str,
    runner_os: str,
    baseline: str,
    image_os: str,
) -> Mapping[str, object]:
    """
    Validate the accepted Windows 7 delivery build provenance.

    :param os_name: Python operating-system family name.
    :type os_name: str
    :param system_name: Platform system name.
    :type system_name: str
    :param python_version: Python major and minor version pair.
    :type python_version: typing.Tuple[int, int]
    :param pointer_bits: Interpreter pointer width in bits.
    :type pointer_bits: int
    :param github_actions: GitHub Actions environment marker.
    :type github_actions: str
    :param runner_os: GitHub Actions runner operating-system name.
    :type runner_os: str
    :param baseline: Explicit acceptance delivery baseline marker.
    :type baseline: str
    :param image_os: GitHub hosted-runner image identifier.
    :type image_os: str
    :return: Validated build provenance facts.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If any fact differs from the accepted
        ``windows-2022`` CPython 3.7 x86-64 baseline.

    Example::

        >>> facts = _assert_windows7_delivery_build_facts(
        ...     os_name="nt",
        ...     system_name="Windows",
        ...     python_version=(3, 7),
        ...     pointer_bits=64,
        ...     github_actions="true",
        ...     runner_os="Windows",
        ...     baseline="windows-2022-cpython-3.7-x86_64",
        ...     image_os="win22",
        ... )
        >>> facts["python"]
        '3.7'
    """
    facts = {
        "platform": "windows",
        "os_name": os_name,
        "system": system_name,
        "python": "{0}.{1}".format(*python_version),
        "pointer_bits": pointer_bits,
        "github_actions": github_actions,
        "runner_os": runner_os,
        "baseline": baseline,
        "image_os": image_os,
    }
    expected = {
        "platform": "windows",
        "os_name": "nt",
        "system": "Windows",
        "python": "3.7",
        "pointer_bits": 64,
        "github_actions": "true",
        "runner_os": "Windows",
        "baseline": "windows-2022-cpython-3.7-x86_64",
        "image_os": "win22",
    }
    mismatches = {
        key: {"actual": facts[key], "expected": value}
        for key, value in expected.items()
        if facts[key] != value
    }
    if mismatches:
        raise ArtifactValidationError(
            "Windows 7 delivery build baseline mismatch: {0}".format(
                json.dumps(mismatches, sort_keys=True)
            )
        )
    return facts


def _assert_windows7_delivery_build_baseline() -> Mapping[str, object]:
    """
    Validate the current process against the accepted delivery baseline.

    :return: Validated build provenance facts for the current process.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If the current process is not the accepted
        GitHub Actions ``windows-2022`` CPython 3.7 x86-64 build.

    Example::

        >>> facts = _assert_windows7_delivery_build_baseline()  # doctest: +SKIP
        >>> facts["image_os"]  # doctest: +SKIP
        'win22'
    """
    return _assert_windows7_delivery_build_facts(
        os_name=os.name,
        system_name=platform.system(),
        python_version=(sys.version_info[0], sys.version_info[1]),
        pointer_bits=struct.calcsize("P") * 8,
        github_actions=os.environ.get("GITHUB_ACTIONS", ""),
        runner_os=os.environ.get("RUNNER_OS", ""),
        baseline=os.environ.get("PYFCSTM_WINDOWS7_DELIVERY_BASELINE", ""),
        image_os=os.environ.get("ImageOS", ""),
    )


def _assert_linux_delivery_build_facts(
    os_name: str,
    system_name: str,
    python_version: Tuple[int, int],
    pointer_bits: int,
    github_actions: str,
    runner_os: str,
    baseline: str,
    image_os: str,
) -> Mapping[str, object]:
    """
    Validate the Ubuntu 22.04 CPython 3.7 x86-64 delivery provenance.

    :param os_name: Python operating-system family name.
    :type os_name: str
    :param system_name: Platform system name.
    :type system_name: str
    :param python_version: Python major and minor version pair.
    :type python_version: typing.Tuple[int, int]
    :param pointer_bits: Interpreter pointer width in bits.
    :type pointer_bits: int
    :param github_actions: Hosted automation environment marker.
    :type github_actions: str
    :param runner_os: Hosted runner operating-system name.
    :type runner_os: str
    :param baseline: Explicit Linux delivery baseline marker.
    :type baseline: str
    :param image_os: Hosted-runner image identifier.
    :type image_os: str
    :return: Validated Linux build provenance facts.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If any fact differs from the accepted
        Ubuntu 22.04 CPython 3.7 x86-64 baseline.

    Example::

        >>> facts = _assert_linux_delivery_build_facts(
        ...     os_name="posix",
        ...     system_name="Linux",
        ...     python_version=(3, 7),
        ...     pointer_bits=64,
        ...     github_actions="true",
        ...     runner_os="Linux",
        ...     baseline="ubuntu-22.04-cpython-3.7-x86_64",
        ...     image_os="ubuntu22",
        ... )
        >>> facts["platform"]
        'linux'
    """
    facts = {
        "platform": "linux",
        "os_name": os_name,
        "system": system_name,
        "python": "{0}.{1}".format(*python_version),
        "pointer_bits": pointer_bits,
        "github_actions": github_actions,
        "runner_os": runner_os,
        "baseline": baseline,
        "image_os": image_os,
    }
    expected = {
        "platform": "linux",
        "os_name": "posix",
        "system": "Linux",
        "python": "3.7",
        "pointer_bits": 64,
        "github_actions": "true",
        "runner_os": "Linux",
        "baseline": "ubuntu-22.04-cpython-3.7-x86_64",
        "image_os": "ubuntu22",
    }
    mismatches = {
        key: {"actual": facts[key], "expected": value}
        for key, value in expected.items()
        if facts[key] != value
    }
    if mismatches:
        raise ArtifactValidationError(
            "Linux delivery build baseline mismatch: {0}".format(
                json.dumps(mismatches, sort_keys=True)
            )
        )
    return facts


def _assert_linux_delivery_build_baseline() -> Mapping[str, object]:
    """
    Validate the current process against the Linux delivery baseline.

    :return: Validated build provenance facts for the current process.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If the current process is not Ubuntu
        22.04 with 64-bit CPython 3.7 under hosted automation.

    Example::

        >>> _assert_linux_delivery_build_baseline()  # doctest: +SKIP
    """
    return _assert_linux_delivery_build_facts(
        os_name=os.name,
        system_name=platform.system(),
        python_version=(sys.version_info[0], sys.version_info[1]),
        pointer_bits=struct.calcsize("P") * 8,
        github_actions=os.environ.get("GITHUB_ACTIONS", ""),
        runner_os=os.environ.get("RUNNER_OS", ""),
        baseline=os.environ.get("PYFCSTM_LINUX_DELIVERY_BASELINE", ""),
        image_os=os.environ.get("ImageOS", ""),
    )


def _assert_executable_delivery_build_baseline() -> Mapping[str, object]:
    """
    Validate the current Windows or Linux executable delivery provenance.

    :return: Platform-specific validated build provenance.
    :rtype: collections.abc.Mapping[str, object]
    :raises ArtifactValidationError: If the platform is unsupported or the
        corresponding delivery baseline is not satisfied.

    Example::

        >>> _assert_executable_delivery_build_baseline()  # doctest: +SKIP
    """
    if os.name == "nt":
        return _assert_windows7_delivery_build_baseline()
    if os.name == "posix" and platform.system() == "Linux":
        return _assert_linux_delivery_build_baseline()
    raise ArtifactValidationError(
        "unsupported executable delivery host: os.name={0!r}, system={1!r}".format(
            os.name, platform.system()
        )
    )


def _parse_executable_version(version_text: str) -> str:
    match = re.search(
        r"\bversion\s+([0-9][0-9A-Za-z.+-]*)", version_text, re.IGNORECASE
    )
    if match is None:
        raise ArtifactValidationError(
            "executable --version output does not contain a version: {0!r}".format(
                version_text.strip()
            )
        )
    return match.group(1).rstrip(".")


def _assert_executable_filename(executable: Path, version: str) -> None:
    platform_name = {"win32": "windows", "darwin": "macos"}.get(
        sys.platform, sys.platform
    )
    architecture = platform.machine().lower()
    architecture = {"amd64": "x86_64"}.get(architecture, architecture)
    suffix = ".exe" if os.name == "nt" else ""
    expected = "pyfcstm-{0}-{1}-{2}{3}".format(
        version, platform_name, architecture, suffix
    )
    if executable.name != expected:
        raise ArtifactValidationError(
            "executable filename mismatch: actual {0}, expected {1}".format(
                executable.name, expected
            )
        )


def _assert_nonempty_file(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ArtifactValidationError(
            "{0} is missing or empty: {1}".format(label, path)
        )


def _assert_nonempty_directory(path: Path, label: str) -> int:
    if not path.is_dir():
        raise ArtifactValidationError("{0} is missing: {1}".format(label, path))
    files = [item for item in path.rglob("*") if item.is_file() and item.stat().st_size]
    if not files:
        raise ArtifactValidationError(
            "{0} has no non-empty files: {1}".format(label, path)
        )
    return len(files)


def _assert_diagram_file(path: Path, render_type: str) -> None:
    _assert_nonempty_file(path, "{0} diagram".format(render_type.upper()))
    try:
        payload = path.read_bytes()
    except OSError as error:
        # Path.read_bytes raises OSError when a rendered diagram is unreadable.
        raise ArtifactValidationError(
            "cannot read rendered diagram {0}: {1}".format(path, error)
        ) from error
    if render_type == "png" and not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ArtifactValidationError("PNG diagram has invalid magic: {0}".format(path))
    if render_type == "svg" and b"<svg" not in payload[:4096].lower():
        raise ArtifactValidationError(
            "SVG diagram has no svg root element: {0}".format(path)
        )


def _read_text_evidence(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        # Path.read_text raises OSError when evidence is absent or unreadable.
        raise ArtifactValidationError(
            "cannot read text evidence {0}: {1}".format(path, error)
        ) from error


def _extract_pdf_text(pdf: Path) -> str:
    command = _require_external_command(
        "pdftotext", "install Poppler to extract PDF text"
    )
    return _run_command([command, str(pdf), "-"]).stdout


def _extract_pdf_metadata(pdf: Path) -> str:
    command = _require_external_command(
        "pdfinfo", "install Poppler to inspect PDF metadata"
    )
    return _run_command([command, str(pdf)]).stdout


def _extract_pdf_outline(pdf: Path) -> str:
    command = _require_external_command(
        "mutool", "install MuPDF tools to read the real PDF outline"
    )
    return _run_command([command, "show", str(pdf), "outline"]).stdout


def _require_external_command(command: str, install_hint: str) -> str:
    resolved = shutil.which(command)
    if resolved is None:
        raise ArtifactValidationError(
            "required command {0!r} is unavailable; {1}".format(command, install_hint)
        )
    return resolved


def _discover_pdf_artifact(build_root: Path, supplied_pdf: Optional[Path]) -> Path:
    if not build_root.is_dir():
        raise ArtifactValidationError(
            "acceptance PDF build root does not exist: {0}".format(build_root)
        )
    latex_root = build_root / "latex"
    expected = latex_root / "pyfcstm-acceptance-zh.pdf"
    pdfs = sorted(latex_root.glob("pyfcstm*.pdf")) if latex_root.is_dir() else []
    if pdfs != [expected]:
        raise ArtifactValidationError(
            "acceptance PDF discovery expected exactly {0}, found {1}".format(
                expected, [str(item) for item in pdfs]
            )
        )
    if supplied_pdf is not None and supplied_pdf.resolve() != expected.resolve():
        raise ArtifactValidationError(
            "--pdf does not match build-root artifact: actual {0}, expected {1}".format(
                supplied_pdf, expected
            )
        )
    return expected


def _assert_pdf_magic(pdf: Path) -> None:
    try:
        magic = pdf.read_bytes()[:5]
    except OSError as error:
        # Path.read_bytes raises OSError when the PDF artifact is unreadable.
        raise ArtifactValidationError(
            "cannot read acceptance PDF {0}: {1}".format(pdf, error)
        ) from error
    if magic != b"%PDF-":
        raise ArtifactValidationError(
            "acceptance PDF has invalid magic {0!r}: {1}".format(magic, pdf)
        )


def _parse_page_count(metadata: str) -> int:
    match = re.search(r"^Pages:\s*(\d+)\s*$", metadata, re.MULTILINE)
    if not match:
        raise ArtifactValidationError("PDF metadata does not contain a Pages line")
    return int(match.group(1))


def _assert_text_contains(label: str, text: str, required: Iterable[str]) -> None:
    normalized = _normalize_search_text(text)
    missing = [
        item for item in required if _normalize_search_text(item) not in normalized
    ]
    if missing:
        raise ArtifactValidationError(
            "{0} missing required text: {1}".format(label, ", ".join(missing))
        )


def _assert_text_excludes(label: str, text: str, denied: Iterable[str]) -> None:
    normalized = _normalize_search_text(text)
    found = [item for item in denied if _normalize_search_text(item) in normalized]
    if found:
        raise ArtifactValidationError(
            "{0} contains forbidden text: {1}".format(label, ", ".join(found))
        )


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).replace("\u00ad", "")
    normalized = re.sub(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)", "-", normalized)
    return "".join(normalized.split())


def _validate_pdf_outline(outline: str) -> Tuple[int, Tuple[str, ...]]:
    _assert_text_contains("acceptance PDF outline", outline, PDF_REQUIRED_OUTLINE)
    _assert_text_excludes("acceptance PDF outline", outline, PDF_DENY_OUTLINE)
    mutool_rows = []
    plain_titles = []
    for line in outline.splitlines():
        match = re.match(r"^[+|](?P<indent>\s+)\"(?P<title>[^\"]+)\"", line)
        if match:
            mutool_rows.append((len(match.group("indent")), match.group("title")))
        elif line.strip():
            plain_titles.append(line.strip())
    titles = (
        tuple(title for _, title in mutool_rows) if mutool_rows else tuple(plain_titles)
    )
    normalized_titles = tuple(_normalize_search_text(title) for title in titles)
    cursor = -1
    for required in PDF_REQUIRED_OUTLINE:
        normalized_required = _normalize_search_text(required)
        try:
            cursor = next(
                index
                for index in range(cursor + 1, len(normalized_titles))
                if normalized_required in normalized_titles[index]
            )
        except StopIteration as error:
            # This ordered subset proves that the acceptance chapter precedes
            # the retained technical manual instead of replacing it.
            raise ArtifactValidationError(
                "acceptance PDF outline is missing ordered title {0!r} "
                "after index {1}".format(required, cursor)
            ) from error
    return len(titles), PDF_REQUIRED_OUTLINE


def _run_common_pdf_checker(build_root: Path) -> None:
    checker = repository_root() / "tools" / "check_docs_pdf.py"
    if not checker.is_file():
        raise ArtifactValidationError(
            "common PDF checker not found: {0}".format(checker)
        )
    _run_command(
        [
            sys.executable,
            str(checker),
            "--language",
            "zh",
            "--profile",
            "acceptance",
            "--build-root",
            str(build_root),
        ]
    )


def _assert_single_vsix(vsix: Path) -> None:
    siblings = sorted(vsix.parent.glob("*.vsix"))
    if siblings != [vsix]:
        raise ArtifactValidationError(
            "VSIX directory must contain exactly the requested archive: requested {0}, found {1}".format(
                vsix, [str(item) for item in siblings]
            )
        )


def _assert_vsix_filename(vsix: Path) -> None:
    if re.fullmatch(r"fcstm-language-support-0\.1\.0\.vsix", vsix.name) is None:
        raise ArtifactValidationError(
            "VSIX filename must be fcstm-language-support-0.1.0.vsix: {0}".format(
                vsix.name
            )
        )


def _assert_vsix_package(package: Mapping[str, object], entries: Iterable[str]) -> None:
    if package.get("name") != "fcstm-language-support":
        raise ArtifactValidationError(
            "VSIX package name must be fcstm-language-support"
        )
    if package.get("publisher") != "hansbug":
        raise ArtifactValidationError("VSIX package publisher must be hansbug")
    if package.get("version") != "0.1.0":
        raise ArtifactValidationError("VSIX package version must be 0.1.0")
    if package.get("main") != "./dist/extension.js":
        raise ArtifactValidationError("VSIX package main must be ./dist/extension.js")
    engines = package.get("engines")
    if not isinstance(engines, dict) or engines.get("vscode") != "^1.60.0":
        raise ArtifactValidationError("VSIX package engines.vscode must be ^1.60.0")
    contributes = package.get("contributes")
    if not isinstance(contributes, dict):
        raise ArtifactValidationError("VSIX contributes must be an object")

    languages = contributes.get("languages")
    if not isinstance(languages, list) or len(languages) != 1:
        raise ArtifactValidationError("VSIX must declare exactly one language")
    language = languages[0]
    if not isinstance(language, dict):
        raise ArtifactValidationError("VSIX language contribution must be an object")
    extensions = language.get("extensions")
    if (
        language.get("id") != "fcstm"
        or not isinstance(extensions, list)
        or ".fcstm" not in extensions
        or language.get("configuration") != "./language-configuration.json"
    ):
        raise ArtifactValidationError(
            "VSIX language contribution must register fcstm, .fcstm, and its configuration"
        )

    grammars = contributes.get("grammars")
    if not isinstance(grammars, list) or len(grammars) != 1:
        raise ArtifactValidationError("VSIX must declare exactly one grammar")
    grammar = grammars[0]
    if not isinstance(grammar, dict) or (
        grammar.get("language") != "fcstm"
        or grammar.get("path") != "./syntaxes/fcstm.tmLanguage.json"
    ):
        raise ArtifactValidationError("VSIX grammar contribution is invalid")

    snippets = contributes.get("snippets")
    if not isinstance(snippets, list) or len(snippets) != 1:
        raise ArtifactValidationError(
            "VSIX must declare exactly one snippet contribution"
        )
    snippet = snippets[0]
    if not isinstance(snippet, dict) or (
        snippet.get("language") != "fcstm"
        or snippet.get("path") != "./snippets/fcstm.code-snippets"
    ):
        raise ArtifactValidationError("VSIX snippet contribution is invalid")

    commands = contributes.get("commands")
    if not isinstance(commands, list):
        raise ArtifactValidationError("VSIX commands contribution must be a list")
    command_ids = {item.get("command") for item in commands if isinstance(item, dict)}
    expected_commands = {
        "fcstm.preview.export",
        "fcstm.preview.open",
        "fcstm.preview.openAlone",
        "fcstm.preview.toggle",
    }
    if command_ids != expected_commands:
        raise ArtifactValidationError(
            "VSIX preview commands mismatch: actual {0}, expected {1}".format(
                sorted(command_ids, key=str), sorted(expected_commands)
            )
        )

    entry_set = set(entries)
    references = (
        package.get("main"),
        language.get("configuration"),
        grammar.get("path"),
        snippet.get("path"),
    )
    missing_references = []
    for reference in references:
        if not isinstance(reference, str):
            missing_references.append(str(reference))
            continue
        relative = reference[2:] if reference.startswith("./") else reference
        normalized = "extension/" + relative
        if normalized not in entry_set:
            missing_references.append(normalized)
    if missing_references:
        raise ArtifactValidationError(
            "VSIX package references missing archive entries: {0}".format(
                ", ".join(missing_references)
            )
        )

    text = json.dumps(package, ensure_ascii=False, sort_keys=True)
    if "fcstm-bmc-query" in text:
        raise ArtifactValidationError("VSIX package must not register BMC grammar")


def _assert_vsix_manifest(
    payloads: Mapping[str, bytes], package: Mapping[str, object]
) -> str:
    text = _decode_payload(payloads, "extension.vsixmanifest", "VSIX manifest")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        # ElementTree raises ParseError for malformed VSIX manifest XML.
        raise ArtifactValidationError(
            "VSIX manifest XML is invalid: {0}".format(error)
        ) from error
    identities = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "Identity"
    ]
    if len(identities) != 1:
        raise ArtifactValidationError(
            "VSIX manifest must contain exactly one Identity element"
        )
    identity = identities[0]
    expected = {
        "Id": package.get("name"),
        "Publisher": package.get("publisher"),
        "Version": package.get("version"),
    }
    actual = {key: identity.attrib.get(key) for key in expected}
    if actual != expected:
        raise ArtifactValidationError(
            "VSIX manifest Identity mismatch: actual {0}, expected {1}".format(
                actual, expected
            )
        )
    installation_id = "{0}.{1}@{2}".format(
        actual["Publisher"], actual["Id"], actual["Version"]
    )
    if installation_id != VSIX_EXTENSION_ID:
        raise ArtifactValidationError(
            "VSIX installation id mismatch: actual {0}, expected {1}".format(
                installation_id, VSIX_EXTENSION_ID
            )
        )
    assets = [
        element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "Asset"
    ]
    required_asset_types = {
        "Microsoft.VisualStudio.Code.Manifest",
        "Microsoft.VisualStudio.Services.Content.Details",
        "Microsoft.VisualStudio.Services.Content.License",
        "Microsoft.VisualStudio.Services.Icons.Default",
    }
    asset_types = {element.attrib.get("Type") for element in assets}
    if not required_asset_types.issubset(asset_types):
        raise ArtifactValidationError(
            "VSIX manifest is missing required Asset declarations: {0}".format(
                sorted(required_asset_types - asset_types)
            )
        )
    missing_assets = sorted(
        {
            element.attrib.get("Path")
            for element in assets
            if not element.attrib.get("Path")
            or element.attrib.get("Path") not in payloads
        },
        key=str,
    )
    if missing_assets:
        raise ArtifactValidationError(
            "VSIX manifest Asset paths are absent from the archive: {0}".format(
                missing_assets
            )
        )
    return installation_id


def _assert_vsix_payload_quality(payloads: Mapping[str, bytes]) -> None:
    for entry, sentinels in VSIX_BUNDLE_SENTINELS.items():
        text = _decode_payload(payloads, entry, "VSIX runtime bundle")
        missing = [sentinel for sentinel in sentinels if sentinel not in text]
        if missing:
            raise ArtifactValidationError(
                "VSIX runtime bundle {0} is missing behavior sentinels: {1}".format(
                    entry, ", ".join(missing)
                )
            )

    grammar = _load_json_payload(
        payloads, "extension/syntaxes/fcstm.tmLanguage.json", "VSIX TextMate grammar"
    )
    patterns = grammar.get("patterns")
    repository = grammar.get("repository")
    if (
        grammar.get("scopeName") != "source.fcstm"
        or not isinstance(patterns, list)
        or not patterns
        or not isinstance(repository, dict)
        or not repository
    ):
        raise ArtifactValidationError(
            "VSIX TextMate grammar must define source.fcstm with non-empty patterns and repository"
        )

    language = _load_json_payload(
        payloads,
        "extension/language-configuration.json",
        "VSIX language configuration",
    )
    if not isinstance(language.get("brackets"), list) or not language.get("brackets"):
        raise ArtifactValidationError(
            "VSIX language configuration must define non-empty brackets"
        )
    snippets = _load_json_payload(
        payloads, "extension/snippets/fcstm.code-snippets", "VSIX snippets"
    )
    if not snippets:
        raise ArtifactValidationError("VSIX snippets must not be empty")

    icon = payloads.get("extension/resources/icon.png", b"")
    if len(icon) < 1024 or not icon.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ArtifactValidationError("VSIX icon must be a non-placeholder PNG")
    style = _decode_payload(
        payloads, "extension/dist/preview-webview.css", "VSIX preview stylesheet"
    )
    if "{" not in style or "}" not in style:
        raise ArtifactValidationError("VSIX preview stylesheet is a placeholder")


def _run_vsix_javascript_syntax_checks(payloads: Mapping[str, bytes]) -> None:
    node = _require_external_command(
        "node", "install Node.js to validate VSIX JavaScript bundles"
    )
    bundle_entries = (
        "extension/dist/extension.js",
        "extension/dist/server.js",
        "extension/dist/preview-webview.js",
    )
    with tempfile.TemporaryDirectory(prefix="acceptance-vsix-javascript-") as directory:
        root = Path(directory)
        for entry in bundle_entries:
            target = root / Path(entry).name
            try:
                target.write_bytes(payloads[entry])
            except OSError as error:
                # Path.write_bytes raises OSError for unusable temporary storage.
                raise ArtifactValidationError(
                    "cannot write VSIX JavaScript fixture {0}: {1}".format(
                        target, error
                    )
                ) from error
            _run_command([node, "--check", str(target)], cwd=root)


def _run_vsix_install_smoke(
    vsix: Path, code: str, source: Optional[Path]
) -> Mapping[str, object]:
    with tempfile.TemporaryDirectory(prefix="acceptance-vsix-smoke-") as directory:
        root = Path(directory)
        extensions = root / "extensions"
        user_data = root / "user-data"
        completed = _run_command(
            [
                code,
                "--extensions-dir",
                str(extensions),
                "--user-data-dir",
                str(user_data),
                "--install-extension",
                str(vsix),
                "--force",
            ],
            cwd=root,
        )
        listing = _run_command(
            [
                code,
                "--extensions-dir",
                str(extensions),
                "--user-data-dir",
                str(user_data),
                "--list-extensions",
                "--show-versions",
            ],
            cwd=root,
        )
        extension_id = _assert_vsix_installation_listing(listing.stdout)
        installed_roots = sorted(
            item
            for item in extensions.iterdir()
            if item.is_dir()
            and item.name.lower() == "hansbug.fcstm-language-support-0.1.0"
        )
        if len(installed_roots) != 1:
            raise ArtifactValidationError(
                "isolated VS Code install did not create exactly one extension root: {0}".format(
                    [str(item) for item in installed_roots]
                )
            )
        installed_root = installed_roots[0]
        archive_entries, _ = _read_zip_entries(vsix)
        expected_files = _expected_installed_vsix_files(archive_entries)
        installed_files = tuple(
            sorted(
                item.relative_to(installed_root).as_posix()
                for item in installed_root.rglob("*")
                if item.is_file()
            )
        )
        _assert_package_install_files(
            expected_files, installed_files, "isolated VS Code extension files"
        )
        node = _require_external_command(
            "node", "install Node.js to validate installed VSIX runtime bundles"
        )
        for relative in (
            "dist/extension.js",
            "dist/server.js",
            "dist/preview-webview.js",
        ):
            _run_command([node, "--check", str(installed_root / relative)], cwd=root)
        return {
            "install_stdout": completed.stdout.strip(),
            "list_stdout": listing.stdout.strip(),
            "extension": extension_id,
            "installed_root": str(installed_root),
            "installed_files": len(installed_files),
            "source": str(source) if source is not None else None,
        }


def _expected_installed_vsix_files(
    archive_entries: Sequence[str],
) -> Tuple[str, ...]:
    installed = [
        entry[len("extension/") :]
        for entry in archive_entries
        if entry.startswith("extension/")
    ]
    if "extension.vsixmanifest" not in archive_entries:
        raise ArtifactValidationError("VSIX archive is missing extension.vsixmanifest")
    installed.append(".vsixmanifest")
    return tuple(sorted(installed))


def _assert_vsix_installation_listing(output: str) -> str:
    extension_rows = tuple(
        line.strip()
        for line in output.splitlines()
        if re.fullmatch(r"[A-Za-z0-9._-]+@[A-Za-z0-9.+_-]+", line.strip())
    )
    if extension_rows != (VSIX_EXTENSION_ID,):
        raise ArtifactValidationError(
            "isolated VS Code extension list mismatch: actual {0}, expected ({1!r},)".format(
                extension_rows, VSIX_EXTENSION_ID
            )
        )
    return VSIX_EXTENSION_ID


def _package_templates_to_tempdir(
    source_dir: Path,
) -> Tuple[tempfile.TemporaryDirectory, Path]:
    root_text = str(repository_root())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        from tools.package_templates import package_templates
    except ImportError as error:
        # ImportError reports an unavailable repository-local production packager.
        raise ArtifactValidationError(
            "cannot import tools.package_templates: {0}".format(error)
        ) from error
    manager = tempfile.TemporaryDirectory(prefix="acceptance-template-assets-")
    output = Path(manager.name)
    package_templates(str(source_dir), str(output), verbose=False)
    return manager, output


def _assert_json_equal(expected: Path, actual: Path) -> None:
    expected_obj = _read_json_file(expected)
    actual_obj = _read_json_file(actual)
    if expected_obj != actual_obj:
        raise ArtifactValidationError(
            "JSON mismatch: expected {0}, actual {1}".format(expected, actual)
        )


def _read_json_file(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        # json.loads raises JSONDecodeError for malformed JSON artifact files.
        raise ArtifactValidationError(
            "invalid JSON file {0}: {1}".format(path, error)
        ) from error
    except OSError as error:
        # Path.read_text raises OSError for missing or unreadable JSON artifacts.
        raise ArtifactValidationError(
            "cannot read JSON file {0}: {1}".format(path, error)
        ) from error


def _assert_zip_payloads_equal(expected: Path, actual: Path, label: str) -> None:
    expected_entries, expected_payloads = _read_zip_entries(expected)
    actual_entries, actual_payloads = _read_zip_entries(actual)
    if expected_entries != actual_entries:
        raise ArtifactValidationError(
            "{0} ZIP entry names differ: expected {1}, actual {2}".format(
                label, list(expected_entries), list(actual_entries)
            )
        )
    changed = []
    for entry in expected_entries:
        if expected_payloads[entry] != actual_payloads[entry]:
            changed.append(entry)
    if changed:
        raise ArtifactValidationError(
            "{0} ZIP payload bytes differ for entries: {1}".format(
                label, ", ".join(changed)
            )
        )


def _run_command(
    arguments: Sequence[str],
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> subprocess.CompletedProcess:
    if not arguments:
        raise ArtifactValidationError("cannot run an empty command")
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        # subprocess.run raises OSError when the executable cannot be launched.
        raise ArtifactValidationError(
            "cannot run command {0}: {1}".format(arguments[0], error)
        ) from error
    if completed.returncode != 0:
        raise ArtifactValidationError(
            "command failed with status {0}: {1}\n{2}".format(
                completed.returncode, " ".join(arguments), completed.stdout.strip()
            )
        )
    return completed


def _clean_subprocess_environment() -> Dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    return environment


def _wheel_install_files(entries: Iterable[str]) -> Tuple[str, ...]:
    return tuple(
        sorted(
            entry
            for entry in entries
            if "/__pycache__/" not in entry
            and not entry.endswith(".pyc")
            and not entry.endswith(".dist-info/RECORD")
        )
    )


def _assert_package_install_files(
    expected: Iterable[str], actual: Iterable[str], label: str
) -> None:
    expected_set = {_normalize_distribution_file(entry) for entry in expected}
    actual_set = {_normalize_distribution_file(entry) for entry in actual}
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if missing or extra:
        raise ArtifactValidationError(
            "{0} differ from the normalized wheel archive: missing={1}; extra={2}".format(
                label, missing, extra
            )
        )


def _normalize_distribution_file(entry: str) -> str:
    """
    Normalize equivalent wheel license installation paths.

    Different supported setuptools versions install the same license as either
    ``dist-info/LICENSE`` or ``dist-info/licenses/LICENSE``. The acceptance
    checker requires the license while treating those two metadata layouts as
    equivalent.

    :param entry: Distribution-relative installed file path.
    :type entry: str
    :return: Normalized installed file path.
    :rtype: str

    Example::

        >>> _normalize_distribution_file('pkg.dist-info/licenses/LICENSE')
        'pkg.dist-info/LICENSE'
    """
    suffix = ".dist-info/licenses/LICENSE"
    if entry.endswith(suffix):
        return entry[: -len(suffix)] + ".dist-info/LICENSE"
    return entry


def _parse_json_command_output(text: str, label: str) -> Mapping[str, object]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ArtifactValidationError("{0} produced no JSON output".format(label))
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as error:
        # json.loads raises JSONDecodeError when the smoke subprocess is malformed.
        raise ArtifactValidationError(
            "{0} produced invalid JSON: {1}\n{2}".format(label, error, text)
        ) from error
    if not isinstance(payload, dict):
        raise ArtifactValidationError("{0} JSON output must be an object".format(label))
    return payload


def _write_json_report(path: Path, payload: Mapping[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        # mkdir and write_text raise OSError for unusable report destinations.
        raise ArtifactValidationError(
            "cannot write JSON report {0}: {1}".format(path, error)
        ) from error
    except TypeError as error:
        # json.dumps raises TypeError if a result unexpectedly is not serializable.
        raise ArtifactValidationError(
            "cannot serialize JSON report {0}: {1}".format(path, error)
        ) from error


def _expect_failure(callable_obj, label: str) -> None:
    try:
        callable_obj()
    except ArtifactValidationError:
        # ArtifactValidationError is the expected adversarial-fixture result.
        return
    raise ArtifactValidationError(
        "self-check adversarial fixture unexpectedly passed: {0}".format(label)
    )


def _create_package_fixture(package_dir: Path) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    wheel = package_dir / "pyfcstm-0.0.0-py3-none-any.whl"
    dist_info = "pyfcstm-0.0.0.dist-info"
    wheel_payloads: Dict[str, bytes] = {
        entry: b"# fixture\n" for entry in WHEEL_REQUIRED
    }
    wheel_payloads.update(
        {
            "{0}/METADATA".format(
                dist_info
            ): "Name: pyfcstm\nVersion: 0.0.0\nRequires-Python: >=3.7\nRequires-Dist: click\nSummary: pyfcstm 项目验收发行包\n".encode(
                "utf-8"
            ),
            "{0}/WHEEL".format(dist_info): b"Wheel-Version: 1.0\n",
            "{0}/LICENSE".format(dist_info): b"Apache License 2.0 fixture\n",
            "{0}/RECORD".format(dist_info): b"",
            "{0}/entry_points.txt".format(
                dist_info
            ): b"[console_scripts]\npyfcstm=pyfcstm.entry.cli:pyfcstmcli\n[pygments.lexers]\nfcstm=pyfcstm.highlight.pygments_lexer:FcstmLexer\n",
        }
    )
    _refresh_wheel_record(wheel_payloads)
    _write_zip(wheel, wheel_payloads)

    sdist = package_dir / "pyfcstm-0.0.0.tar.gz"
    root = "pyfcstm-0.0.0"
    sdist_payloads: Dict[str, bytes] = {
        "{0}/{1}".format(root, entry): b"# fixture\n" for entry in SDIST_REQUIRED
    }
    sdist_payloads["{0}/README_ACCEPTANCE.md".format(root)] = (
        "# pyfcstm 项目验收发行包\n".encode("utf-8")
    )
    _write_tar(sdist, sdist_payloads)


def _copy_and_tamper_package_fixture(source: Path, target: Path, mode: str) -> Path:
    shutil.copytree(str(source), str(target))
    wheel = next(target.glob("*.whl"))
    sdist = next(target.glob("*.tar.gz"))
    if mode == "wheel-llm":
        entries, payloads = _read_zip_entries(wheel)
        payloads["pyfcstm/llm/__init__.py"] = b"# forbidden\n"
        _refresh_wheel_record(payloads)
        _write_zip(wheel, payloads)
    elif mode == "wheel-diagnostics-readme":
        entries, payloads = _read_zip_entries(wheel)
        payloads["pyfcstm/diagnostics/README.md"] = b"# internal\n"
        _refresh_wheel_record(payloads)
        _write_zip(wheel, payloads)
    elif mode == "wheel-missing-license":
        entries, payloads = _read_zip_entries(wheel)
        payloads = {
            entry: payload
            for entry, payload in payloads.items()
            if not entry.endswith(".dist-info/LICENSE")
        }
        _refresh_wheel_record(payloads)
        _write_zip(wheel, payloads)
    elif mode == "sdist-diagnostics-readme":
        entries, payloads = _read_tar_entries(sdist)
        root = next(iter(payloads)).split("/", 1)[0]
        payloads["{0}/pyfcstm/diagnostics/README.md".format(root)] = b"# internal\n"
        _write_tar(sdist, payloads)
    elif mode == "sdist-missing-required":
        entries, payloads = _read_tar_entries(sdist)
        payloads = {
            entry: payload
            for entry, payload in payloads.items()
            if not entry.endswith("pyfcstm/template/python.zip")
        }
        _write_tar(sdist, payloads)
    elif mode == "wheel-filename":
        wheel.rename(wheel.with_name("acceptance-" + wheel.name))
    elif mode == "wheel-sensitive-payload":
        entries, payloads = _read_zip_entries(wheel)
        payloads["pyfcstm/diagnostics/schema.json"] += b"\nGITHUB\n"
        _refresh_wheel_record(payloads)
        _write_zip(wheel, payloads)
    elif mode == "sdist-sensitive-payload":
        entries, payloads = _read_tar_entries(sdist)
        setup_entry = next(entry for entry in entries if entry.endswith("/setup.py"))
        payloads[setup_entry] += b"\ns714\n"
        _write_tar(sdist, payloads)
    else:
        raise ArtifactValidationError("unknown package tamper mode: {0}".format(mode))
    return target


def _refresh_wheel_record(payloads: Dict[str, bytes]) -> None:
    record_paths = [entry for entry in payloads if entry.endswith(".dist-info/RECORD")]
    if len(record_paths) != 1:
        raise ArtifactValidationError(
            "wheel fixture requires exactly one RECORD path: {0}".format(record_paths)
        )
    payloads[record_paths[0]] = "".join(
        "{0},,\n".format(entry) for entry in sorted(payloads)
    ).encode("utf-8")


def _write_inventory_fixture(
    path: Path,
    good: bool,
    missing_required: bool = False,
    delivery_platform: str = "windows",
) -> None:
    entries = list(EXECUTABLE_REQUIRED)
    entries.append("z3/lib/libz3.so")
    if delivery_platform == "windows":
        entries.append("python37.dll")
    elif delivery_platform == "linux":
        entries.append("libpython3.7m.so.1.0")
    else:
        raise ArtifactValidationError(
            "unknown inventory fixture platform: {0}".format(delivery_platform)
        )
    if missing_required:
        entries.remove("pyfcstm/template/python.zip")
    if not good:
        entries.append("pyfcstm/llm/fcstm_grammar_guide.md")
        entries.append("z3/include/z3++.h")
    lines = [
        "Contents of 'pyfcstm' (PKG/CArchive):",
        " position, length, uncompressed_length, is_compressed, typecode, name",
    ]
    lines.extend(" 0, 1, 1, 1, 'x', {0!r}".format(entry) for entry in entries)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cli_help_fixture(mutation: Optional[str] = None) -> Tuple[str, str]:
    commands = list(CLI_COMMANDS)
    if mutation == "missing-command":
        commands.remove("visualize")
    top_help = "Usage: pyfcstm [OPTIONS] COMMAND [ARGS]...\n\nCommands:\n" + "\n".join(
        "  {0}  fixture command".format(command) for command in commands
    )
    inspect_help = "Usage: pyfcstm inspect [OPTIONS]\n  --format [human|json]\n"
    if mutation == "inspect-policy":
        inspect_help = (
            "Usage: pyfcstm inspect [OPTIONS]\n"
            "  --format [human|json|llm-json]\n"
            "  --enable-verify\n"
            "  --max-complexity-tier [structural|bmc_search]\n"
            "  --smt-timeout-ms INTEGER\n"
        )
    elif mutation not in (None, "missing-command"):
        raise ArtifactValidationError(
            "unknown CLI help fixture mutation: {0}".format(mutation)
        )
    return top_help, inspect_help


def _write_pdf_sidecars(
    text_file: Path,
    metadata_file: Path,
    outline_file: Path,
    good: bool,
    mutation: Optional[str] = None,
) -> None:
    text = "\n".join(PDF_REQUIRED_TEXT) + "\n" + ("技术正文" * 70_000)
    if not good:
        text += "\nS714\n"
    metadata = "Title: pyfcstm 项目验收\nPages: 620\n"
    outline = "\n".join(
        '+\t"{0}"\t#nameddest=chapter.{1}'.format(title, index)
        for index, title in enumerate(PDF_REQUIRED_OUTLINE, start=1)
    )
    if mutation == "metadata":
        metadata = "Title: pyfcstm 项目验收\nPages: 1200\n"
    elif mutation == "outline":
        outline = "\n".join(
            '+\t"{0}"\t#nameddest=chapter.{1}'.format(title, index)
            for index, title in enumerate(PDF_REQUIRED_OUTLINE[:-1], start=1)
        )
    elif mutation == "sensitive-text":
        text += "\nGitHub\n"
    elif mutation == "sensitive-metadata":
        metadata += "Subject: S714\n"
    elif mutation == "sensitive-outline":
        outline += '\n+\t"GitHub"\t#nameddest=chapter.999\n'
    elif mutation is not None:
        raise ArtifactValidationError(
            "unknown PDF sidecar mutation: {0}".format(mutation)
        )
    text_file.write_text(text, encoding="utf-8")
    metadata_file.write_text(metadata, encoding="utf-8")
    outline_file.write_text(outline, encoding="utf-8")


def _create_vsix_fixture(path: Path, mutation: Optional[str] = None) -> None:
    package_name = (
        "wrong-language-support" if mutation == "wrong-id" else "fcstm-language-support"
    )
    version = "0.2.0" if mutation == "wrong-version" else "0.1.0"
    package = {
        "name": package_name,
        "displayName": "FCSTM Language Support",
        "version": version,
        "publisher": "hansbug",
        "main": "./dist/extension.js",
        "engines": {"vscode": "^1.60.0"},
        "contributes": {
            "languages": [
                {
                    "id": "fcstm",
                    "extensions": [".fcstm"],
                    "configuration": "./language-configuration.json",
                }
            ],
            "grammars": [
                {"language": "fcstm", "path": "./syntaxes/fcstm.tmLanguage.json"}
            ],
            "snippets": [
                {"language": "fcstm", "path": "./snippets/fcstm.code-snippets"}
            ],
            "commands": [
                {"command": "fcstm.preview.open", "title": "Open Preview"},
                {"command": "fcstm.preview.openAlone", "title": "Open Preview Alone"},
                {"command": "fcstm.preview.toggle", "title": "Toggle Preview"},
                {"command": "fcstm.preview.export", "title": "Export Preview"},
            ],
        },
    }
    manifest = """<?xml version='1.0' encoding='utf-8'?>
<PackageManifest Version='2.0.0' xmlns='http://schemas.microsoft.com/developer/vsx-schema/2011'>
  <Metadata><Identity Id='{name}' Version='{version}' Publisher='hansbug'/><DisplayName>FCSTM Language Support</DisplayName></Metadata>
  <Assets>
    <Asset Type='Microsoft.VisualStudio.Code.Manifest' Path='extension/package.json'/>
    <Asset Type='Microsoft.VisualStudio.Services.Content.Details' Path='extension/README.md'/>
    <Asset Type='Microsoft.VisualStudio.Services.Content.License' Path='extension/LICENSE.txt'/>
    <Asset Type='Microsoft.VisualStudio.Services.Icons.Default' Path='extension/resources/icon.png'/>
  </Assets>
</PackageManifest>
""".format(name=package_name, version=version)
    payloads: Dict[str, bytes] = {
        "[Content_Types].xml": b"<?xml version='1.0'?><Types></Types>\n",
        "extension.vsixmanifest": manifest.encode("utf-8"),
        "extension/package.json": json.dumps(package, ensure_ascii=False).encode(
            "utf-8"
        ),
        "extension/README.md": "FCSTM offline acceptance extension\n".encode("utf-8"),
        "extension/LICENSE.txt": b"fixture license\n",
        "extension/language-configuration.json": b'{"brackets": [["{", "}"]]}\n',
        "extension/dist/extension.js": b"/* LanguageClient registerCommand fcstm.preview.open */\n",
        "extension/dist/server.js": b"/* createConnection TextDocuments publishDiagnostics */\n",
        "extension/dist/preview-webview.js": b"/* acquireVsCodeApi postMessage */\n",
        "extension/dist/preview-webview.css": b"body { color: black; }\n",
        "extension/resources/icon.png": b"\x89PNG\r\n\x1a\n" + b"x" * 1024,
        "extension/snippets/fcstm.code-snippets": b'{"state": {"prefix": "state", "body": ["state Name;"]}}\n',
        "extension/syntaxes/fcstm.tmLanguage.json": b'{"scopeName": "source.fcstm", "patterns": [{"include": "#state"}], "repository": {"state": {"match": "state", "name": "keyword.control.fcstm"}}}\n',
    }
    if mutation == "missing-server":
        del payloads["extension/dist/server.js"]
    elif mutation == "missing-preview":
        del payloads["extension/dist/preview-webview.js"]
    elif mutation == "bmc-grammar":
        payloads["extension/syntaxes/fcstm-bmc-query.tmLanguage.json"] = b"{}\n"
    elif mutation == "extra-entry":
        payloads["extension/extra.txt"] = b"forbidden\n"
    elif mutation == "placeholder-bundle":
        payloads["extension/dist/server.js"] = b"console.log('server');\n"
    elif mutation == "empty-grammar":
        payloads["extension/syntaxes/fcstm.tmLanguage.json"] = b"{}\n"
    elif mutation == "missing-manifest-asset":
        del payloads["extension/README.md"]
    elif mutation == "sensitive-bundle":
        payloads["extension/dist/extension.js"] += b"/* GiThUb */\n"
    elif mutation not in (None, "wrong-id", "wrong-version"):
        raise ArtifactValidationError(
            "unknown VSIX fixture mutation: {0}".format(mutation)
        )
    _write_zip(path, payloads)


def _create_template_asset_fixture(
    directory: Path, metadata_variant: bool, tamper: Optional[str] = None
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    index = {
        "templates": [
            {"name": name, "archive": "{0}.zip".format(name)} for name in TEMPLATE_NAMES
        ]
    }
    (directory / "index.json").write_text(
        json.dumps(index, sort_keys=True), encoding="utf-8"
    )
    if metadata_variant:
        (directory / "__init__.py").write_text("# package fixture\n", encoding="utf-8")
    for name in TEMPLATE_NAMES:
        payloads = {
            "{0}/template.json".format(name): json.dumps(
                {"name": name}, sort_keys=True
            ).encode("utf-8"),
            "{0}/config.yaml".format(name): "name: {0}\n".format(name).encode("utf-8"),
        }
        if tamper == "entry" and name == "python":
            payloads["python/config-renamed.yaml"] = payloads.pop("python/config.yaml")
        if tamper == "payload" and name == "python":
            payloads["python/config.yaml"] = b"name: changed\n"
        _write_zip(
            directory / "{0}.zip".format(name),
            payloads,
            metadata_variant=metadata_variant,
        )
    if tamper == "extra-archive":
        _write_zip(directory / "llm.zip", {"llm/internal.txt": b"forbidden\n"})


def _write_zip(
    path: Path, payloads: Mapping[str, bytes], metadata_variant: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in sorted(payloads):
                info = zipfile.ZipInfo(entry)
                info.date_time = (
                    (2026, 7, 10, 0, 0, 0)
                    if metadata_variant
                    else (2020, 1, 1, 0, 0, 0)
                )
                info.compress_type = (
                    zipfile.ZIP_STORED if metadata_variant else zipfile.ZIP_DEFLATED
                )
                zf.writestr(info, payloads[entry])
    except OSError as error:
        # ZipFile writes raise OSError for unusable fixture destinations.
        raise ArtifactValidationError(
            "cannot write ZIP fixture {0}: {1}".format(path, error)
        ) from error


def _write_tar(path: Path, payloads: Mapping[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(str(path), "w:gz") as tf:
            for entry in sorted(payloads):
                data = payloads[entry]
                info = tarfile.TarInfo(entry)
                info.size = len(data)
                info.mtime = 0
                import io

                tf.addfile(info, io.BytesIO(data))
    except OSError as error:
        # tarfile writes raise OSError for unusable fixture destinations.
        raise ArtifactValidationError(
            "cannot write tar fixture {0}: {1}".format(path, error)
        ) from error


if __name__ == "__main__":
    sys.exit(main())
