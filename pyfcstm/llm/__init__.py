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
from typing import Dict, Union

from pyfcstm.config.meta import __VERSION__

__all__ = [
    "GrammarGuidePromptPathUnavailableError",
    "get_grammar_guide_prompt_for_llm",
    "get_grammar_guide_prompt_path_for_llm",
    "get_grammar_guide_prompt_metadata_for_llm",
]

_GRAMMAR_GUIDE_RESOURCE_NAME = "fcstm_grammar_guide.md"


class GrammarGuidePromptPathUnavailableError(RuntimeError):
    """
    Error raised when the grammar guide has no direct filesystem path.

    The text API remains available for normal prompt construction even when the
    package is imported from a non-filesystem loader.
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


def get_grammar_guide_prompt_for_llm() -> str:
    """
    Return the packaged FCSTM grammar guide prompt.

    :return: UTF-8 decoded Markdown prompt text with LF newlines.
    :rtype: str
    :raises FileNotFoundError: If the packaged Markdown resource is missing.
    :raises UnicodeDecodeError: If the resource is not valid UTF-8.

    Example::

        >>> guide = get_grammar_guide_prompt_for_llm()
        >>> guide.startswith("# FCSTM")
        True
    """
    return _decode_grammar_guide_prompt(_get_grammar_guide_prompt_bytes())


def get_grammar_guide_prompt_path_for_llm() -> str:
    """
    Return the filesystem path to the packaged grammar guide prompt.

    This helper is intended for source-tree and normal wheel installs where the
    Markdown resource exists as a real file. It intentionally does not
    materialize temporary files for zip import or other non-filesystem import
    modes; callers that only need prompt text should use
    :func:`get_grammar_guide_prompt_for_llm`.

    :return: Filesystem path to ``fcstm_grammar_guide.md``.
    :rtype: str
    :raises GrammarGuidePromptPathUnavailableError: If the resource cannot be
        represented as a real filesystem path.

    Example::

        >>> import os
        >>> path = get_grammar_guide_prompt_path_for_llm()
        >>> os.path.basename(path)
        'fcstm_grammar_guide.md'
    """
    guide_path = os.path.join(os.path.dirname(__file__), _GRAMMAR_GUIDE_RESOURCE_NAME)
    if os.path.isfile(guide_path):
        return guide_path

    raise GrammarGuidePromptPathUnavailableError(
        "Packaged LLM grammar guide resource "
        f"{_GRAMMAR_GUIDE_RESOURCE_NAME!r} is not available as a filesystem "
        "path in the current installation mode. Use "
        "get_grammar_guide_prompt_for_llm() to read the prompt text instead."
    )


def get_grammar_guide_prompt_metadata_for_llm() -> Dict[str, Union[str, int]]:
    """
    Return deterministic metadata for the packaged grammar guide prompt.

    ``chapter_count`` is the number of Markdown level-two heading lines, i.e.
    lines starting with ``"## "``.

    :return: Resource metadata for experiment snapshots.
    :rtype: Dict[str, Union[str, int]]
    :raises FileNotFoundError: If the packaged Markdown resource is missing.
    :raises UnicodeDecodeError: If the resource is not valid UTF-8.

    Example::

        >>> metadata = get_grammar_guide_prompt_metadata_for_llm()
        >>> metadata["resource_name"]
        'fcstm_grammar_guide.md'
        >>> metadata["chapter_count"] > 0
        True
    """
    text = _decode_grammar_guide_prompt(_get_grammar_guide_prompt_bytes())
    data = text.encode("utf-8")
    lines = text.splitlines()
    return {
        "resource_name": _GRAMMAR_GUIDE_RESOURCE_NAME,
        "pyfcstm_version": __VERSION__,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
        "line_count": len(lines),
        "chapter_count": sum(1 for line in lines if line.startswith("## ")),
    }
