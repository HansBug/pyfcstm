"""Exceptions raised by integrity-checked packaged LLM guide resources."""


class GrammarGuidePromptIntegrityError(RuntimeError):
    """
    Error raised when a packaged LLM guide integrity check fails.

    This means that a Markdown prompt and its SHA-256 digest do not agree, or
    that the digest resource is missing or malformed. Source-tree users should
    run ``make sha256`` after editing a guide and commit both files. Installed
    package users should reinstall :mod:`pyfcstm` from a clean distribution.

    Example::

        >>> issubclass(GrammarGuidePromptIntegrityError, RuntimeError)
        True
    """


class GrammarGuidePromptPathUnavailableError(RuntimeError):
    """
    Error raised when a packaged LLM guide has no direct filesystem path.

    This can happen when a zip importer, frozen bundle, or another installation
    mode does not expose package resources as real files. The text API remains
    available for prompt construction in those modes.

    Example::

        >>> issubclass(GrammarGuidePromptPathUnavailableError, RuntimeError)
        True
    """
