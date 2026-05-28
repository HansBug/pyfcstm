"""
Loader for the structured diagnostic code registry.

This module loads ``codes.yaml`` (the single source of truth for diagnostic
codes emitted by :mod:`pyfcstm.model`) at import time and exposes the parsed
table as :data:`CODE_REGISTRY`. Downstream consumers — including the
``research_ideas`` LLM agent loop, IDE integrations, and the future
``jsfcstm`` visualization layer — can mirror this registry to drive their
own dispatch logic without depending on exception message text.

The loader performs structural validation on import so that schema drift
in ``codes.yaml`` fails fast.

The module contains:

* :class:`CodeFieldSpec` - Per-field schema describing a ``refs`` payload key.
* :class:`CodeSpec` - Full specification for one diagnostic code.
* :data:`CODE_REGISTRY` - Mapping ``code -> CodeSpec`` loaded at import time.
* :func:`load_codes` - Parse a YAML file path and return the registry.

.. note::
   The codes.yaml file is intentionally kept lightweight: it does not
   enforce ``refs`` runtime types on every emitted diagnostic. The schema
   serves as documentation and as the contract surface for downstream
   tools and tests.

Example::

    >>> from pyfcstm.verify.codes import CODE_REGISTRY
    >>> spec = CODE_REGISTRY['E_UNDEFINED_VAR']
    >>> spec.severity
    'error'
    >>> 'var_name' in spec.refs_schema
    True
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

import yaml

_ALLOWED_SEVERITIES = ('error', 'warning')
_ALLOWED_REF_TYPES = (
    'str',
    'str_or_null',
    'int',
    'int_or_null',
    'bool',
    'Span',
    'list[str]',
)


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
        the structured payload for diagnostics with this code.
    :type refs_schema: Dict[str, CodeFieldSpec]
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


def _validate_field(code: str, field_name: str, raw: Any) -> CodeFieldSpec:
    if not isinstance(raw, dict):
        raise ValueError(
            f"codes.yaml: code {code!r} field {field_name!r} must be a mapping, got {type(raw).__name__}."
        )
    if 'type' not in raw:
        raise ValueError(
            f"codes.yaml: code {code!r} field {field_name!r} is missing required key 'type'."
        )
    field_type = raw['type']
    if field_type not in _ALLOWED_REF_TYPES:
        raise ValueError(
            f"codes.yaml: code {code!r} field {field_name!r} has unsupported type {field_type!r}. "
            f"Allowed: {_ALLOWED_REF_TYPES}."
        )
    required = bool(raw.get('required', False))
    description = str(raw.get('description', ''))
    return CodeFieldSpec(
        name=field_name,
        type=field_type,
        required=required,
        description=description,
    )


def _validate_code(code: str, raw: Any) -> CodeSpec:
    if not isinstance(raw, dict):
        raise ValueError(
            f"codes.yaml: code {code!r} must be a mapping, got {type(raw).__name__}."
        )
    severity = raw.get('severity')
    if severity not in _ALLOWED_SEVERITIES:
        raise ValueError(
            f"codes.yaml: code {code!r} has invalid severity {severity!r}. "
            f"Allowed: {_ALLOWED_SEVERITIES}."
        )
    description = str(raw.get('description', '')).strip()
    if not description:
        raise ValueError(
            f"codes.yaml: code {code!r} must have a non-empty 'description'."
        )

    raw_refs = raw.get('refs') or {}
    if not isinstance(raw_refs, dict):
        raise ValueError(
            f"codes.yaml: code {code!r} 'refs' must be a mapping when present, "
            f"got {type(raw_refs).__name__}."
        )
    refs_schema: Dict[str, CodeFieldSpec] = {}
    for field_name, field_raw in raw_refs.items():
        refs_schema[field_name] = _validate_field(code, field_name, field_raw)

    example_dsl = raw.get('example_dsl')
    if example_dsl is not None and not isinstance(example_dsl, str):
        raise ValueError(
            f"codes.yaml: code {code!r} 'example_dsl' must be a string when present, "
            f"got {type(example_dsl).__name__}."
        )

    # Codes follow a 1-letter severity prefix convention: E_* for errors,
    # W_* for warnings. Enforce so that severity and code stay in sync.
    expected_prefix = 'E_' if severity == 'error' else 'W_'
    if not code.startswith(expected_prefix):
        raise ValueError(
            f"codes.yaml: code {code!r} has severity {severity!r} but does not start "
            f"with the expected prefix {expected_prefix!r}."
        )

    return CodeSpec(
        code=code,
        severity=severity,
        description=description,
        refs_schema=refs_schema,
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
    :raises ValueError: If the YAML structure does not match the expected
        schema, or if a code uses an unknown severity / type token.

    Example::

        >>> import os
        >>> from pyfcstm.verify.codes import load_codes
        >>> path = os.path.join(os.path.dirname(__file__), 'codes.yaml')

    """
    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ValueError(f"codes.yaml at {path!r} is empty.")
    if not isinstance(raw, dict):
        raise ValueError(
            f"codes.yaml at {path!r} must contain a top-level mapping, "
            f"got {type(raw).__name__}."
        )
    registry: Dict[str, CodeSpec] = {}
    for code, entry in raw.items():
        if not isinstance(code, str):
            raise ValueError(
                f"codes.yaml at {path!r}: top-level key {code!r} must be a string."
            )
        registry[code] = _validate_code(code, entry)
    if not registry:
        raise ValueError(f"codes.yaml at {path!r} contains no code definitions.")
    return registry


_CODES_YAML_PATH = os.path.join(os.path.dirname(__file__), 'codes.yaml')

#: Mapping ``code -> CodeSpec`` loaded from ``codes.yaml`` at import time.
CODE_REGISTRY: Dict[str, CodeSpec] = load_codes(_CODES_YAML_PATH)
