"""Private loading and integrity helpers for packaged LLM guides."""

import hashlib
import os
import pkgutil
import typing as _typing
import warnings

from pyfcstm.config.meta import __VERSION__

from .error import (
    GrammarGuidePromptIntegrityError,
    GrammarGuidePromptPathUnavailableError,
)

_HEX_DIGITS = set("0123456789abcdefABCDEF")


def _resource_bytes(resource_name: str, resource_label: str, kind: str) -> bytes:
    """Load one package resource and report a missing resource clearly."""
    data = pkgutil.get_data(__package__, resource_name)
    if data is None:
        raise FileNotFoundError(
            "Packaged %s %s resource %r was not found."
            % (resource_label, kind, resource_name)
        )
    return data


def _normalize_prompt(data: bytes) -> str:
    """Decode UTF-8 prompt data and normalize its line endings to LF."""
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _failure_message(
    reason: str,
    resource_name: str,
    checksum_name: str,
    resource_label: str,
) -> str:
    """Format one actionable integrity diagnostic."""
    return (
        "%s integrity verification failed: %s This means pyfcstm cannot prove "
        "that the packaged %r prompt matches the released %r digest. If you "
        "are developing from source, run `make sha256`, then rebuild or rerun "
        "your tests and commit the Markdown guide and checksum together. If you "
        "are using an installed package, reinstall pyfcstm from a clean wheel "
        "or source distribution. To inspect or use the prompt despite this "
        "problem, call the LLM prompt API with "
        "`raise_on_integrity_error=False`; pyfcstm will still emit this warning."
        % (resource_label, reason, resource_name, checksum_name)
    )


def _raise_or_warn(message: str, raise_on_integrity_error: bool) -> None:
    """Apply the public strict-or-warning integrity policy."""
    if raise_on_integrity_error:
        raise GrammarGuidePromptIntegrityError(message)
    warnings.warn(message, RuntimeWarning, stacklevel=4)


def _expected_digest(
    resource_name: str,
    checksum_name: str,
    resource_label: str,
    raise_on_integrity_error: bool,
) -> str:
    """Read one validated checksum or apply the warning fallback."""
    try:
        checksum = _resource_bytes(checksum_name, resource_label, "checksum")
        first_line = checksum.decode("utf-8").strip().splitlines()
        digest = first_line[0].split()[0] if first_line else ""
        if len(digest) != 64 or any(char not in _HEX_DIGITS for char in digest):
            raise GrammarGuidePromptIntegrityError(
                "Packaged %s checksum resource %r is malformed. It should start "
                "with a 64-character SHA-256 hex digest for %r."
                % (resource_label, checksum_name, resource_name)
            )
    except FileNotFoundError as err:
        _raise_or_warn(
            _failure_message(str(err), resource_name, checksum_name, resource_label),
            raise_on_integrity_error,
        )
        return ""
    except UnicodeDecodeError as err:
        _raise_or_warn(
            _failure_message(
                "checksum resource %r is not valid UTF-8 (%s)." % (checksum_name, err),
                resource_name,
                checksum_name,
                resource_label,
            ),
            raise_on_integrity_error,
        )
        return ""
    except GrammarGuidePromptIntegrityError as err:
        # This catches only the malformed-digest branch raised directly above.
        _raise_or_warn(
            _failure_message(str(err), resource_name, checksum_name, resource_label),
            raise_on_integrity_error,
        )
        return ""
    return digest.lower()


def _verify(
    text: str,
    resource_name: str,
    checksum_name: str,
    resource_label: str,
    raise_on_integrity_error: bool,
) -> str:
    """Verify prompt text and return its declared digest."""
    expected = _expected_digest(
        resource_name,
        checksum_name,
        resource_label,
        raise_on_integrity_error,
    )
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if expected and actual != expected:
        _raise_or_warn(
            _failure_message(
                "expected SHA-256 %s, but computed %s from the LF-normalized "
                "packaged prompt." % (expected, actual),
                resource_name,
                checksum_name,
                resource_label,
            ),
            raise_on_integrity_error,
        )
    return expected


def get_guide_prompt(
    resource_name: str,
    checksum_name: str,
    resource_label: str,
    raise_on_integrity_error: bool,
) -> str:
    """Load, normalize, and verify a packaged guide."""
    text = _normalize_prompt(_resource_bytes(resource_name, resource_label, "prompt"))
    _verify(
        text,
        resource_name,
        checksum_name,
        resource_label,
        raise_on_integrity_error,
    )
    return text


def get_guide_prompt_path(
    resource_name: str,
    checksum_name: str,
    resource_label: str,
    text_api_name: str,
    raise_on_integrity_error: bool,
) -> str:
    """Return a verified filesystem path when the installation exposes one."""
    get_guide_prompt(
        resource_name,
        checksum_name,
        resource_label,
        raise_on_integrity_error,
    )
    guide_path = os.path.join(os.path.dirname(__file__), resource_name)
    if os.path.isfile(guide_path):
        return guide_path
    raise GrammarGuidePromptPathUnavailableError(
        "Packaged %s resource %r is not available as a filesystem path in the "
        "current installation mode. Use %s() to read the prompt text instead."
        % (resource_label, resource_name, text_api_name)
    )


def get_guide_prompt_metadata(
    resource_name: str,
    checksum_name: str,
    resource_label: str,
    raise_on_integrity_error: bool,
) -> _typing.Dict[str, _typing.Union[str, int]]:
    """Return deterministic metadata for a packaged guide."""
    text = _normalize_prompt(_resource_bytes(resource_name, resource_label, "prompt"))
    data = text.encode("utf-8")
    expected = _verify(
        text,
        resource_name,
        checksum_name,
        resource_label,
        raise_on_integrity_error,
    )
    lines = text.splitlines()
    return {
        "resource_name": resource_name,
        "checksum_resource_name": checksum_name,
        "pyfcstm_version": __VERSION__,
        "sha256": hashlib.sha256(data).hexdigest(),
        "expected_sha256": expected,
        "byte_size": len(data),
        "line_count": len(lines),
        "chapter_count": sum(1 for line in lines if line.startswith("## ")),
    }
