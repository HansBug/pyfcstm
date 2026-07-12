"""Public API for the packaged FBMCQ language guide resource."""

import typing as _typing

from ._resources import (
    get_guide_prompt,
    get_guide_prompt_metadata,
    get_guide_prompt_path,
)

_RESOURCE_NAME = "fbmcq_language_guide.md"
_CHECKSUM_RESOURCE_NAME = _RESOURCE_NAME + ".sha256"
_RESOURCE_LABEL = "FBMCQ LLM language guide"


def get_fbmcq_language_guide_prompt_for_llm(
    raise_on_integrity_error: bool = True,
) -> str:
    """
    Return the packaged FBMCQ language guide prompt.

    :param raise_on_integrity_error: Whether a missing, malformed, or
        mismatched checksum should raise instead of returning text with a
        warning, defaults to ``True``.
    :type raise_on_integrity_error: bool, optional
    :return: UTF-8 decoded FBMCQ Markdown prompt with LF newlines.
    :rtype: str
    :raises FileNotFoundError: If the packaged Markdown resource is missing.
    :raises UnicodeDecodeError: If a resource is not valid UTF-8.
    :raises GrammarGuidePromptIntegrityError: If checksum verification fails.

    Example::

        >>> get_fbmcq_language_guide_prompt_for_llm().startswith("# FBMCQ")
        True
    """
    return get_guide_prompt(
        _RESOURCE_NAME,
        _CHECKSUM_RESOURCE_NAME,
        _RESOURCE_LABEL,
        raise_on_integrity_error,
    )


def get_fbmcq_language_guide_prompt_path_for_llm(
    raise_on_integrity_error: bool = True,
) -> str:
    """
    Return the filesystem path to the packaged FBMCQ language guide prompt.

    :param raise_on_integrity_error: Whether checksum failures raise, defaults
        to ``True``.
    :type raise_on_integrity_error: bool, optional
    :return: Filesystem path to ``fbmcq_language_guide.md``.
    :rtype: str
    :raises GrammarGuidePromptPathUnavailableError: If no real path exists.
    :raises GrammarGuidePromptIntegrityError: If checksum verification fails.

    Example::

        >>> get_fbmcq_language_guide_prompt_path_for_llm().endswith("fbmcq_language_guide.md")
        True
    """
    return get_guide_prompt_path(
        _RESOURCE_NAME,
        _CHECKSUM_RESOURCE_NAME,
        _RESOURCE_LABEL,
        "get_fbmcq_language_guide_prompt_for_llm",
        raise_on_integrity_error,
    )


def get_fbmcq_language_guide_prompt_metadata_for_llm(
    raise_on_integrity_error: bool = True,
) -> _typing.Dict[str, _typing.Union[str, int]]:
    """
    Return deterministic metadata for the packaged FBMCQ language guide.

    :param raise_on_integrity_error: Whether checksum failures raise, defaults
        to ``True``.
    :type raise_on_integrity_error: bool, optional
    :return: Resource metadata for experiment snapshots.
    :rtype: Dict[str, Union[str, int]]
    :raises GrammarGuidePromptIntegrityError: If checksum verification fails.

    Example::

        >>> get_fbmcq_language_guide_prompt_metadata_for_llm()["resource_name"]
        'fbmcq_language_guide.md'
    """
    return get_guide_prompt_metadata(
        _RESOURCE_NAME,
        _CHECKSUM_RESOURCE_NAME,
        _RESOURCE_LABEL,
        raise_on_integrity_error,
    )
