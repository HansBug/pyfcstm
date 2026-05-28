"""
Loader for the structured diagnostic code registry.

This module loads ``codes.yaml`` (the single source of truth for diagnostic
codes emitted by :mod:`pyfcstm.model`) at import time and exposes the parsed
table as :data:`CODE_REGISTRY`. Downstream consumers — including the
``research_ideas`` LLM agent loop, IDE integrations, and the future
``jsfcstm`` visualization layer — can mirror this registry to drive their
own dispatch logic without depending on exception message text.

The loader performs structural validation on import so that schema drift
in ``codes.yaml`` fails fast. Validation failures raise
:class:`CodesSchemaError` (subclass of :class:`ValueError`), so callers can
distinguish "the diagnostics package is structurally broken" from a generic
business-level ``ValueError`` further up the stack.

The module contains:

* :class:`CodeFieldSpec` - Per-field schema describing a ``refs`` payload key.
* :class:`CodeSpec` - Full specification for one diagnostic code.
* :class:`CodesSchemaError` - Raised when ``codes.yaml`` is structurally invalid.
* :data:`CODE_REGISTRY` - Mapping ``code -> CodeSpec`` loaded at import time.
* :func:`load_codes` - Parse a YAML file path and return the registry.

.. note::
   ``_ALLOWED_REF_TYPES`` and ``_ALLOWED_SEVERITIES`` are documentation-level
   enumerations used to validate the YAML schema. They do **not** enforce
   runtime ``isinstance`` checks on emitted ``ModelDiagnostic.refs`` values
   — type-checking refs payloads at emit time is the emitter's responsibility
   (see PR-2 of issue #103). The schema's job is to give downstream tooling
   a contract to mirror, not to act as a runtime type system.

Example::

    >>> from pyfcstm.diagnostics import CODE_REGISTRY
    >>> spec = CODE_REGISTRY['E_UNDEFINED_VAR']
    >>> spec.severity
    'error'
    >>> 'var_name' in spec.refs_schema
    True
"""

import os
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional

import yaml

#: Allowed values for ``severity`` in ``codes.yaml`` entries. Must stay in
#: sync with the type-token comment block at the top of ``codes.yaml``.
_ALLOWED_SEVERITIES = ('error', 'warning')

#: Allowed values for the ``refs.<field>.type`` token in ``codes.yaml``. This
#: tuple is the **single source of truth** for the type-token vocabulary; the
#: comment block at the top of ``codes.yaml`` is documentation that must
#: mirror this tuple (test/diagnostics/test_codes_yaml.py asserts both lists
#: stay aligned).
#:
#: NOTE: these tokens are documentation-only. PR-1 does not enforce that
#: ``refs[field]`` actually carries the declared Python type at emit time;
#: the YAML schema serves as the contract surface for downstream tools and
#: as the input for human-readable spec rendering.
_ALLOWED_REF_TYPES = (
    'str',
    'str_or_null',
    'int',
    'int_or_null',
    'bool',
    'Span',
    'list[str]',
)


class CodesSchemaError(ValueError):
    """
    Raised when ``codes.yaml`` is structurally invalid.

    Subclasses :class:`ValueError` so generic ``except ValueError`` handlers
    still catch it, but downstream tooling that wants to distinguish
    "diagnostics package broken" from a domain-level ``ValueError`` can use
    a tighter handler.
    """


@dataclass(frozen=True)
class CodeFieldSpec:
    """
    Schema for a single field inside :attr:`CodeSpec.refs_schema`.

    :param name: Field name as it will appear in :attr:`ModelDiagnostic.refs`.
    :type name: str
    :param type: Field type token. Must be one of the allowed type tokens
        documented at the top of ``codes.yaml``.
    :type type: str
    :param required: Whether this field must be present when the diagnostic
        is emitted.
    :type required: bool
    :param description: Human-readable explanation of the field.
    :type description: str
    """

    name: str
    type: str
    required: bool
    description: str


@dataclass(frozen=True)
class CodeSpec:
    """
    Full specification for a single diagnostic code.

    :param code: Stable code identifier (e.g. ``'E_UNDEFINED_VAR'``).
    :type code: str
    :param severity: ``'error'`` or ``'warning'``.
    :type severity: str
    :param description: Human-readable description of when the code fires.
    :type description: str
    :param refs_schema: Mapping ``field_name -> CodeFieldSpec`` describing
        the structured payload for diagnostics with this code. The mapping
        itself is a :class:`types.MappingProxyType` so downstream callers
        cannot mutate the registry by accident.
    :type refs_schema: Mapping[str, CodeFieldSpec]
    :param example_dsl: Minimal DSL snippet that triggers the code,
        defaults to ``None``.
    :type example_dsl: str, optional
    """

    code: str
    severity: str
    description: str
    refs_schema: Mapping[str, CodeFieldSpec]
    example_dsl: Optional[str] = None

    def required_fields(self) -> List[str]:
        """
        Return the names of fields that must be present in ``refs``.

        :return: List of required field names in declaration order.
        :rtype: List[str]
        """
        return [name for name, spec in self.refs_schema.items() if spec.required]


def _ctx(path: str, *bits: str) -> str:
    return f"codes.yaml at {path!r}: " + " ".join(bits)


def _validate_field(path: str, code: str, field_name: str, raw: Any) -> CodeFieldSpec:
    if not isinstance(raw, dict):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} field {field_name!r} must be a mapping, got",
            type(raw).__name__,
        ))
    if 'type' not in raw:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} field {field_name!r} is missing required key 'type'.",
        ))
    field_type = raw['type']
    if field_type not in _ALLOWED_REF_TYPES:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} field {field_name!r} has unsupported type {field_type!r}.",
            f"Allowed: {_ALLOWED_REF_TYPES}.",
        ))
    raw_required = raw.get('required', False)
    if not isinstance(raw_required, bool):
        # Catch the YAML footgun where `required: "false"` is loaded as a
        # truthy string instead of a bool. `bool("false")` is True, which
        # would silently invert required/optional semantics.
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} field {field_name!r} 'required' must be a YAML bool,",
            f"got {type(raw_required).__name__}: {raw_required!r}",
        ))
    description = str(raw.get('description', ''))
    return CodeFieldSpec(
        name=field_name,
        type=field_type,
        required=raw_required,
        description=description,
    )


def _validate_code(path: str, code: str, raw: Any) -> CodeSpec:
    if not isinstance(raw, dict):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} must be a mapping, got {type(raw).__name__}.",
        ))
    severity = raw.get('severity')
    if severity not in _ALLOWED_SEVERITIES:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} has invalid severity {severity!r}.",
            f"Allowed: {_ALLOWED_SEVERITIES}.",
        ))
    if 'description' not in raw:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} is missing required key 'description'.",
        ))
    description = str(raw.get('description', '')).strip()
    if not description:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} must have a non-empty 'description'.",
        ))

    raw_refs = raw.get('refs') or {}
    if not isinstance(raw_refs, dict):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'refs' must be a mapping when present,",
            f"got {type(raw_refs).__name__}.",
        ))
    refs_schema: Dict[str, CodeFieldSpec] = {}
    for field_name, field_raw in raw_refs.items():
        refs_schema[field_name] = _validate_field(path, code, field_name, field_raw)

    example_dsl = raw.get('example_dsl')
    if example_dsl is not None and not isinstance(example_dsl, str):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'example_dsl' must be a string when present,",
            f"got {type(example_dsl).__name__}.",
        ))

    # Codes follow a 1-letter severity prefix convention: E_* for errors,
    # W_* for warnings. Enforce so that severity and code stay in sync.
    expected_prefix = 'E_' if severity == 'error' else 'W_'
    if not code.startswith(expected_prefix):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} has severity {severity!r} but does not start",
            f"with the expected prefix {expected_prefix!r}.",
        ))

    return CodeSpec(
        code=code,
        severity=severity,
        description=description,
        refs_schema=MappingProxyType(refs_schema),
        example_dsl=example_dsl,
    )


def load_codes(path: str) -> Dict[str, CodeSpec]:
    """
    Load and validate a ``codes.yaml`` file from disk.

    :param path: Filesystem path to the YAML file.
    :type path: str
    :return: Mapping ``code -> CodeSpec`` parsed from the file.
    :rtype: Dict[str, CodeSpec]
    :raises FileNotFoundError: If ``path`` does not exist.
    :raises CodesSchemaError: If the YAML structure does not match the
        expected schema, or if a code uses an unknown severity / type token.
        Subclasses :class:`ValueError` for backwards compatibility with
        generic ``except ValueError`` handlers.

    Example::

        >>> import os
        >>> from pyfcstm.diagnostics.codes import load_codes
        >>> path = os.path.join(os.path.dirname(__file__), 'codes.yaml')

    """
    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise CodesSchemaError(_ctx(path, "file is empty."))
    if not isinstance(raw, dict):
        raise CodesSchemaError(_ctx(
            path,
            f"must contain a top-level mapping, got {type(raw).__name__}.",
        ))
    registry: Dict[str, CodeSpec] = {}
    for code, entry in raw.items():
        if not isinstance(code, str):
            raise CodesSchemaError(_ctx(
                path, f"top-level key {code!r} must be a string."
            ))
        registry[code] = _validate_code(path, code, entry)
    if not registry:
        raise CodesSchemaError(_ctx(path, "contains no code definitions."))
    return registry


def _resolve_codes_yaml_path() -> str:
    """
    Resolve the on-disk path of ``codes.yaml`` in both source and PyInstaller
    one-file bundle layouts.

    In a normal install / editable install, :data:`__file__` lives next to
    ``codes.yaml``. In a PyInstaller one-file bundle, data files are
    extracted to ``sys._MEIPASS`` at startup; the package directory under
    ``__file__`` may not contain ``codes.yaml`` directly.

    :return: Absolute path to a readable ``codes.yaml``.
    :rtype: str
    """
    here = os.path.dirname(__file__)
    candidate = os.path.join(here, 'codes.yaml')
    if os.path.isfile(candidate):
        return candidate

    meipass = getattr(sys, '_MEIPASS', None)
    if meipass is not None:
        bundled = os.path.join(meipass, 'pyfcstm', 'diagnostics', 'codes.yaml')
        if os.path.isfile(bundled):
            return bundled

    # Last-ditch: return the original candidate so the resulting
    # FileNotFoundError points at the expected location rather than a
    # synthetic path.
    return candidate


_CODES_YAML_PATH = _resolve_codes_yaml_path()

#: Mapping ``code -> CodeSpec`` loaded from ``codes.yaml`` at import time.
#: Wrapped in :class:`types.MappingProxyType` so downstream callers cannot
#: mutate the registry by accident.
CODE_REGISTRY: Mapping[str, CodeSpec] = MappingProxyType(load_codes(_CODES_YAML_PATH))
