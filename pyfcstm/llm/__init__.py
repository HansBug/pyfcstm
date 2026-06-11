"""
LLM prompt resources for FCSTM model generation.

This module exposes the official FCSTM grammar guide prompt as a small Python
API. The guide is packaged with :mod:`pyfcstm` so downstream prompt builders can
use the same grammar reference that the project tests and releases validate.

Example::

    >>> from pyfcstm.llm import get_grammar_guide_prompt_for_llm
    >>> guide = get_grammar_guide_prompt_for_llm()
    >>> "FCSTM" in guide
    True
"""

import hashlib
import os
import pkgutil
import warnings
import typing as _typing

from pyfcstm.config.meta import __VERSION__

__all__ = [
    "GrammarGuidePromptIntegrityError",
    "GrammarGuidePromptPathUnavailableError",
    "get_grammar_guide_prompt_for_llm",
    "get_grammar_guide_prompt_path_for_llm",
    "get_grammar_guide_prompt_metadata_for_llm",
]

_GRAMMAR_GUIDE_RESOURCE_NAME = "fcstm_grammar_guide.md"
_GRAMMAR_GUIDE_SHA256_RESOURCE_NAME = _GRAMMAR_GUIDE_RESOURCE_NAME + ".sha256"
_HEX_DIGITS = set("0123456789abcdefABCDEF")


class GrammarGuidePromptIntegrityError(RuntimeError):
    """
    Error raised when the packaged grammar guide integrity check fails.

    This indicates that the Markdown prompt and the packaged SHA-256 digest do
    not agree, or that the digest resource is missing or malformed. Source-tree
    users should run ``make sha256`` after editing the guide and commit the
    guide and digest together. Installed-package users should reinstall
    :mod:`pyfcstm` from a clean wheel or source distribution.
    """


class GrammarGuidePromptPathUnavailableError(RuntimeError):
    """
    Error raised when the grammar guide has no direct filesystem path.

    This can occur when the package is loaded from zip import, frozen bundles,
    or another importer that does not expose packaged Markdown resources as real
    files. The text API remains available for normal prompt construction in
    those installation modes.
    """


def _get_grammar_guide_prompt_bytes() -> bytes:
    """
    Load the packaged grammar guide prompt as bytes.

    :return: Raw UTF-8 encoded guide bytes.
    :rtype: bytes
    :raises FileNotFoundError: If the packaged Markdown resource is missing.
    """
    data = pkgutil.get_data(__name__, _GRAMMAR_GUIDE_RESOURCE_NAME)
    if data is None:
        raise FileNotFoundError(
            "Packaged LLM grammar guide resource "
            f"{_GRAMMAR_GUIDE_RESOURCE_NAME!r} was not found."
        )
    return data


def _get_grammar_guide_sha256_bytes() -> bytes:
    """
    Load the packaged grammar guide SHA-256 resource as bytes.

    :return: Raw checksum resource bytes.
    :rtype: bytes
    :raises FileNotFoundError: If the packaged checksum resource is missing.
    """
    data = pkgutil.get_data(__name__, _GRAMMAR_GUIDE_SHA256_RESOURCE_NAME)
    if data is None:
        raise FileNotFoundError(
            "Packaged LLM grammar guide checksum resource "
            f"{_GRAMMAR_GUIDE_SHA256_RESOURCE_NAME!r} was not found."
        )
    return data


def _decode_grammar_guide_prompt(data: bytes) -> str:
    """
    Decode raw grammar guide bytes into canonical prompt text.

    Markdown resources checked out on Windows may contain CRLF newlines. The
    public prompt API normalizes newlines to LF so downstream prompt snapshots,
    Markdown fence parsing, and metadata stay deterministic across platforms.

    :param data: Raw UTF-8 encoded guide bytes.
    :type data: bytes
    :return: UTF-8 decoded prompt text with LF newlines.
    :rtype: str
    :raises UnicodeDecodeError: If the resource is not valid UTF-8.
    """
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _decode_grammar_guide_sha256(data: bytes) -> str:
    """
    Decode and validate the packaged grammar guide SHA-256 digest.

    The checksum file may contain either a bare 64-character digest or the
    common ``sha256sum`` style ``"<digest>  <filename>"`` format. Only the
    first whitespace-delimited token is treated as the digest.

    :param data: Raw checksum resource bytes.
    :type data: bytes
    :return: Lowercase expected SHA-256 digest.
    :rtype: str
    :raises UnicodeDecodeError: If the checksum resource is not valid UTF-8.
    :raises GrammarGuidePromptIntegrityError: If the digest is malformed.
    """
    stripped = data.decode("utf-8").strip()
    first_line = stripped.splitlines()[0].strip() if stripped else ""
    digest = first_line.split()[0] if first_line else ""
    if len(digest) != 64 or any(char not in _HEX_DIGITS for char in digest):
        raise GrammarGuidePromptIntegrityError(
            "Packaged LLM grammar guide checksum resource "
            f"{_GRAMMAR_GUIDE_SHA256_RESOURCE_NAME!r} is malformed. It should "
            "start with a 64-character SHA-256 hex digest for "
            f"{_GRAMMAR_GUIDE_RESOURCE_NAME!r}. If you are developing from "
            "source, run `make sha256` and commit the updated checksum. If you "
            "are using an installed package, reinstall pyfcstm from a clean "
            "wheel or source distribution."
        )
    return digest.lower()


def _format_grammar_guide_integrity_message(reason: str) -> str:
    """
    Format an actionable grammar guide integrity failure message.

    :param reason: Specific integrity failure reason.
    :type reason: str
    :return: Full user-facing diagnostic.
    :rtype: str
    """
    return (
        "FCSTM LLM grammar guide integrity verification failed: "
        f"{reason} This means pyfcstm cannot prove that the packaged "
        f"{_GRAMMAR_GUIDE_RESOURCE_NAME!r} prompt matches the released "
        f"{_GRAMMAR_GUIDE_SHA256_RESOURCE_NAME!r} digest. If you are "
        "developing from source, run `make sha256`, then rebuild or rerun your "
        "tests and commit the Markdown guide and checksum together. If you are "
        "using an installed package, reinstall pyfcstm from a clean wheel or "
        "source distribution. To inspect or use the prompt despite this "
        "problem, call the LLM prompt API with "
        "`raise_on_integrity_error=False`; pyfcstm will still emit this warning."
    )


def _handle_grammar_guide_integrity_error(
    message: str, raise_on_integrity_error: bool
) -> None:
    """
    Raise or warn for a grammar guide integrity failure.

    :param message: Full diagnostic message.
    :type message: str
    :param raise_on_integrity_error: Whether to raise instead of warning.
    :type raise_on_integrity_error: bool
    :return: ``None``.
    :rtype: None
    :raises GrammarGuidePromptIntegrityError: If ``raise_on_integrity_error``
        is true.
    """
    if raise_on_integrity_error:
        raise GrammarGuidePromptIntegrityError(message)

    warnings.warn(message, RuntimeWarning, stacklevel=4)


def _verify_grammar_guide_prompt_integrity(
    text: str, raise_on_integrity_error: bool
) -> str:
    """
    Verify the normalized grammar guide prompt against its packaged digest.

    :param text: LF-normalized prompt text.
    :type text: str
    :param raise_on_integrity_error: Whether to raise instead of warning.
    :type raise_on_integrity_error: bool
    :return: Expected SHA-256 digest from the packaged checksum resource.
    :rtype: str
    :raises GrammarGuidePromptIntegrityError: If verification fails and
        ``raise_on_integrity_error`` is true.
    """
    try:
        expected = _decode_grammar_guide_sha256(_get_grammar_guide_sha256_bytes())
    except FileNotFoundError as err:
        message = _format_grammar_guide_integrity_message(str(err))
        _handle_grammar_guide_integrity_error(message, raise_on_integrity_error)
        return ""
    except UnicodeDecodeError as err:
        message = _format_grammar_guide_integrity_message(
            "checksum resource "
            f"{_GRAMMAR_GUIDE_SHA256_RESOURCE_NAME!r} is not valid UTF-8 "
            f"({err})."
        )
        _handle_grammar_guide_integrity_error(message, raise_on_integrity_error)
        return ""
    except GrammarGuidePromptIntegrityError as err:
        message = _format_grammar_guide_integrity_message(str(err))
        _handle_grammar_guide_integrity_error(message, raise_on_integrity_error)
        return ""

    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if actual != expected:
        message = _format_grammar_guide_integrity_message(
            f"expected SHA-256 {expected}, but computed {actual} from the "
            "LF-normalized packaged prompt."
        )
        _handle_grammar_guide_integrity_error(message, raise_on_integrity_error)

    return expected


def get_grammar_guide_prompt_for_llm(
    raise_on_integrity_error: bool = True,
) -> str:
    """
    Return the packaged FCSTM grammar guide prompt.

    :param raise_on_integrity_error: Whether a missing, malformed, or
        mismatched ``fcstm_grammar_guide.md.sha256`` resource should raise
        instead of returning the prompt with a warning, defaults to ``True``.
    :type raise_on_integrity_error: bool, optional
    :return: UTF-8 decoded Markdown prompt text with LF newlines.
    :rtype: str
    :raises FileNotFoundError: If the packaged Markdown resource is missing.
    :raises UnicodeDecodeError: If the resource is not valid UTF-8.
    :raises GrammarGuidePromptIntegrityError: If the checksum resource is
        missing, malformed, or does not match the normalized prompt text.

    Example::

        >>> guide = get_grammar_guide_prompt_for_llm()
        >>> guide.startswith("# FCSTM")
        True
    """
    text = _decode_grammar_guide_prompt(_get_grammar_guide_prompt_bytes())
    _verify_grammar_guide_prompt_integrity(text, raise_on_integrity_error)
    return text


def get_grammar_guide_prompt_path_for_llm(
    raise_on_integrity_error: bool = True,
) -> str:
    """
    Return the filesystem path to the packaged grammar guide prompt.

    This helper is intended for source-tree and normal wheel installs where the
    Markdown resource exists as a real file. It intentionally does not
    materialize temporary files for zip import or other non-filesystem import
    modes; callers that only need prompt text should use
    :func:`get_grammar_guide_prompt_for_llm`.

    :param raise_on_integrity_error: Whether a missing, malformed, or
        mismatched ``fcstm_grammar_guide.md.sha256`` resource should raise
        instead of returning the path with a warning, defaults to ``True``.
    :type raise_on_integrity_error: bool, optional
    :return: Filesystem path to ``fcstm_grammar_guide.md``.
    :rtype: str
    :raises GrammarGuidePromptPathUnavailableError: If the resource cannot be
        represented as a real filesystem path.
    :raises GrammarGuidePromptIntegrityError: If the checksum resource is
        missing, malformed, or does not match the normalized prompt text.

    Example::

        >>> import os
        >>> path = get_grammar_guide_prompt_path_for_llm()
        >>> os.path.basename(path)
        'fcstm_grammar_guide.md'
    """
    get_grammar_guide_prompt_for_llm(raise_on_integrity_error=raise_on_integrity_error)
    guide_path = os.path.join(os.path.dirname(__file__), _GRAMMAR_GUIDE_RESOURCE_NAME)
    if os.path.isfile(guide_path):
        return guide_path

    raise GrammarGuidePromptPathUnavailableError(
        "Packaged LLM grammar guide resource "
        f"{_GRAMMAR_GUIDE_RESOURCE_NAME!r} is not available as a filesystem "
        "path in the current installation mode. Use "
        "get_grammar_guide_prompt_for_llm() to read the prompt text instead."
    )


def get_grammar_guide_prompt_metadata_for_llm(
    raise_on_integrity_error: bool = True,
) -> _typing.Dict[str, _typing.Union[str, int]]:
    """
    Return deterministic metadata for the packaged grammar guide prompt.

    ``sha256``, ``byte_size``, and ``line_count`` are computed from the same
    LF-normalized prompt text returned by
    :func:`get_grammar_guide_prompt_for_llm`. ``chapter_count`` is the number of
    Markdown level-two heading lines, i.e. lines starting with ``"## "``.

    :param raise_on_integrity_error: Whether a missing, malformed, or
        mismatched ``fcstm_grammar_guide.md.sha256`` resource should raise
        instead of returning metadata with a warning, defaults to ``True``.
    :type raise_on_integrity_error: bool, optional
    :return: Resource metadata for experiment snapshots.
    :rtype: Dict[str, Union[str, int]]
    :raises FileNotFoundError: If the packaged Markdown resource is missing.
    :raises UnicodeDecodeError: If the resource is not valid UTF-8.
    :raises GrammarGuidePromptIntegrityError: If the checksum resource is
        missing, malformed, or does not match the normalized prompt text.

    Example::

        >>> metadata = get_grammar_guide_prompt_metadata_for_llm()
        >>> metadata["resource_name"]
        'fcstm_grammar_guide.md'
        >>> metadata["chapter_count"] > 0
        True
    """
    text = _decode_grammar_guide_prompt(_get_grammar_guide_prompt_bytes())
    data = text.encode("utf-8")
    expected_sha256 = _verify_grammar_guide_prompt_integrity(
        text, raise_on_integrity_error=raise_on_integrity_error
    )
    lines = text.splitlines()
    return {
        "resource_name": _GRAMMAR_GUIDE_RESOURCE_NAME,
        "checksum_resource_name": _GRAMMAR_GUIDE_SHA256_RESOURCE_NAME,
        "pyfcstm_version": __VERSION__,
        "sha256": hashlib.sha256(data).hexdigest(),
        "expected_sha256": expected_sha256,
        "byte_size": len(data),
        "line_count": len(lines),
        "chapter_count": sum(1 for line in lines if line.startswith("## ")),
    }
