"""
Loader for the structured diagnostic code registry.

This module loads ``codes.yaml`` (the single source of truth for diagnostic
codes emitted by pyfcstm diagnostic pipelines) at import time and exposes the
parsed table as :data:`CODE_REGISTRY`. Downstream consumers — including the
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
   — type-checking refs payloads at emit time is the emitter's responsibility.
   The schema's job is to give downstream tooling a contract to mirror, not
   to act as a runtime type system.

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
from typing import Any, Dict, List, Mapping, Optional, Tuple

import yaml

#: Allowed values for ``severity`` in ``codes.yaml`` entries. Must stay in
#: sync with the type-token comment block at the top of ``codes.yaml``.
#:
#: ``info`` hosts ``I_*`` codes for observations that are likely-legitimate
#: rather than likely-defects.
_ALLOWED_SEVERITIES = ('error', 'warning', 'info')

#: Mapping from severity name to the required identifier prefix for codes
#: at that severity. Used by :func:`_validate_code` to enforce that the
#: code identifier and its severity stay in sync.
_SEVERITY_PREFIX = {
    'error': 'E_',
    'warning': 'W_',
    'info': 'I_',
}

#: Allowed values for the ``capability`` field on a code. Declared by
#: Layer 2 to gate downstream consumers that may not implement every
#: analysis flavor (e.g. jsfcstm without SMT WASM).
#:
#: * ``pure_static`` — judged from AST/model only, no expression folding,
#:   no external solver, no simulation
#: * ``const_fold`` — needs the expression constant folder
#: * ``requires_solver`` — needs an SMT backend (reserved for Layer 3)
#: * ``requires_simulation`` — needs the SimulationRuntime (reserved)
_ALLOWED_CAPABILITIES = (
    'pure_static',
    'const_fold',
    'requires_solver',
    'requires_simulation',
)

#: Allowed values for the ``emit_tier`` field on a code. This schema
#: explicitly declares which emit pipeline produces a code so downstream
#: dispatchers can register handlers correctly:
#:
#: * ``static_pipeline`` — fires during the regular static analysis
#:   pass (``parse_dsl_node_to_state_machine`` /
#:   ``collectDocumentDiagnostics``). This is the default for legacy
#:   codes that omit the field.
#: * ``lookup_api`` — fires only when a runtime resolver method
#:   (e.g. ``State.resolve_event``) is invoked explicitly; never seen
#:   by the static pipeline or the parity tests.
#: * ``partial_static_pipeline`` — implemented in the static pipeline
#:   on only one end (typically jsfcstm); the other end intentionally
#:   does not emit. Downstream LLM consumers should not block waiting
#:   for the missing end to surface this code.
#: * ``verify_pipeline`` — emitted only by the optional Python verify /
#:   inspect adapter path. These codes are not part of the default static
#:   inspect output and are not expected from jsfcstm.
_ALLOWED_EMIT_TIERS = (
    'static_pipeline',
    'lookup_api',
    'partial_static_pipeline',
    'verify_pipeline',
)

_ALLOWED_SUGGESTED_FIX_KINDS = ('insert', 'delete', 'replace')

#: Allowed values for the optional ``span_object`` field on a code entry.
#: The field documents which semantic source object the primary
#: ``ModelDiagnostic.span`` identifies. The vocabulary covers the common
#: problem objects plus current import, variable, and expression diagnostics
#: that already carry source spans.
_ALLOWED_SPAN_OBJECTS = (
    'state_identifier',
    'transition',
    'guard_expression',
    'effect_statement',
    'composite_block',
    'named_action_declaration',
    'event_declaration',
    'variable_declaration',
    'expression',
    'lifecycle_action',
    'import_statement',
)

#: Required keys for the ``for_llm`` payload when present on a code.
#: ``summary`` is a one-line description aimed at downstream LLM consumers;
#: ``recommended_actions`` is a list of dicts describing concrete fixes;
#: ``do_not`` is a list of strings describing anti-patterns to avoid.
_FOR_LLM_REQUIRED_KEYS = ('summary', 'recommended_actions', 'do_not')

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
    'float',
    'number',
    'bool',
    'dict',
    'Span',
    'list[str]',
    'list[Span]',
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
    :param enum: Optional tuple of allowed string values for the field.
        When present, downstream emit-test infrastructure (and any future
        runtime validator) checks that ``refs[field]`` is a member of the
        tuple. ``None`` means the field has no enumeration constraint.
    :type enum: Optional[Tuple[str, ...]]
    """

    name: str
    type: str
    required: bool
    description: str
    enum: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class ForLlmSpec:
    """
    Structured guidance attached to a diagnostic code for downstream LLM
    consumers.

    Emitted ``E_*``, ``W_*``, and ``I_*`` codes carry this payload so that
    LLM agent loops can read structured fix recommendations instead of
    regex-ing the human-readable ``message``. All catalogued codes are
    expected to provide this field unless the loader is explicitly handling
    a forward-compatibility case.

    :param summary: One-line description aimed at LLM consumers.
    :type summary: str
    :param recommended_actions: Ordered list of concrete fix suggestions.
        Each entry is a free-form dict; downstream tooling is expected to
        treat the list as a hint rather than a closed schema.
    :type recommended_actions: Tuple[Mapping[str, Any], ...]
    :param do_not: List of anti-pattern strings the LLM should avoid.
    :type do_not: Tuple[str, ...]
    """

    summary: str
    recommended_actions: Tuple[Mapping[str, Any], ...]
    do_not: Tuple[str, ...]


@dataclass(frozen=True)
class SuggestedFixSpec:
    """Structured auto-fix metadata declared by ``codes.yaml``.

    :param kind: Edit operation kind: ``insert``, ``delete``, or ``replace``.
    :type kind: str
    :param target: Semantic target kind, such as ``variable_definition``.
    :type target: str
    :param anchor_ref: Reference to a field in the emitted refs payload,
        written as ``refs.<field>``.
    :type anchor_ref: str
    :param text_template: Optional edit text template. ``insert`` and
        ``replace`` use it; ``delete`` normally leaves it empty.
    :type text_template: str
    :param rationale: Short reason suitable for LLM/UI display.
    :type rationale: str
    """

    kind: str
    target: str
    anchor_ref: str
    text_template: str
    rationale: str


@dataclass(frozen=True)
class CodeSpec:
    """
    Full specification for a single diagnostic code.

    :param code: Stable code identifier (e.g. ``'E_UNDEFINED_VAR'``).
    :type code: str
    :param severity: ``'error'``, ``'warning'``, or ``'info'``.
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
    :param capability: Which analysis tier this code belongs to. Layer 2
        declares this required when present; unset means
        ``'pure_static'`` for grandfathered Layer 1 codes.
    :type capability: str, optional
    :param for_llm: Structured guidance for downstream LLM consumers.
        Expected on catalogued codes so downstream tooling can consume
        structured remediation guidance. Still typed as ``Optional`` so
        the loader can tolerate forward-compatibility cases.
    :type for_llm: ForLlmSpec, optional
    :param emit_tier: Which emit pipeline actually fires this code.
        ``'static_pipeline'`` (default) means the code fires during
        ``parse_dsl_node_to_state_machine`` / the equivalent jsfcstm
        ``collectDocumentDiagnostics`` static analysis pass.
        ``'lookup_api'`` means the code only fires through explicit
        runtime resolver APIs (e.g. ``State.resolve_event``) and is
        never produced by the static pipeline. ``'partial_static_pipeline'``
        marks codes whose static-pipeline emit is implemented on one
        end only (typically jsfcstm) — downstream LLM consumers should
        not block waiting for the missing end. ``'verify_pipeline'`` marks
        diagnostics emitted only by optional Python verify integration.
        The field lets dispatchers register handlers based on the actual
        emit channel.
    :type emit_tier: str, optional
    :param span_object: Semantic source object identified by the primary
        diagnostic span. Repository entries declare this to make source-slice
        assertions and downstream UI behavior explicit.
    :type span_object: str, optional
    """

    code: str
    severity: str
    description: str
    refs_schema: Mapping[str, CodeFieldSpec]
    example_dsl: Optional[str] = None
    capability: str = 'pure_static'
    for_llm: Optional[ForLlmSpec] = None
    emit_tier: str = 'static_pipeline'
    suggested_fix: Optional[SuggestedFixSpec] = None
    span_object: Optional[str] = None

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

    raw_enum = raw.get('enum')
    field_enum: Optional[Tuple[str, ...]] = None
    if raw_enum is not None:
        if not isinstance(raw_enum, list):
            raise CodesSchemaError(_ctx(
                path,
                f"code {code!r} field {field_name!r} 'enum' must be a list "
                f"when present,",
                f"got {type(raw_enum).__name__}",
            ))
        if not raw_enum:
            raise CodesSchemaError(_ctx(
                path,
                f"code {code!r} field {field_name!r} 'enum' must be non-empty "
                f"when present.",
            ))
        for value in raw_enum:
            if not isinstance(value, str):
                raise CodesSchemaError(_ctx(
                    path,
                    f"code {code!r} field {field_name!r} 'enum' members must "
                    f"be strings, got {type(value).__name__}: {value!r}",
                ))
        field_enum = tuple(raw_enum)

    return CodeFieldSpec(
        name=field_name,
        type=field_type,
        required=raw_required,
        description=description,
        enum=field_enum,
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

    # Codes follow a 1-letter severity prefix convention: E_* errors,
    # W_* warnings, I_* infos. Enforce so that severity and code stay in sync.
    expected_prefix = _SEVERITY_PREFIX[severity]
    if not code.startswith(expected_prefix):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} has severity {severity!r} but does not start",
            f"with the expected prefix {expected_prefix!r}.",
        ))

    capability = raw.get('capability', 'pure_static')
    if capability not in _ALLOWED_CAPABILITIES:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} has invalid capability {capability!r}.",
            f"Allowed: {_ALLOWED_CAPABILITIES}.",
        ))

    emit_tier = raw.get('emit_tier', 'static_pipeline')
    if emit_tier not in _ALLOWED_EMIT_TIERS:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} has invalid emit_tier {emit_tier!r}.",
            f"Allowed: {_ALLOWED_EMIT_TIERS}.",
        ))

    for_llm = _validate_for_llm(path, code, raw.get('for_llm'))
    suggested_fix = _validate_suggested_fix(path, code, raw.get('suggested_fix'))
    span_object = _validate_span_object(path, code, raw.get('span_object'))

    return CodeSpec(
        code=code,
        severity=severity,
        description=description,
        refs_schema=MappingProxyType(refs_schema),
        example_dsl=example_dsl,
        capability=capability,
        for_llm=for_llm,
        emit_tier=emit_tier,
        suggested_fix=suggested_fix,
        span_object=span_object,
    )


def _validate_span_object(path: str, code: str, raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if raw not in _ALLOWED_SPAN_OBJECTS:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} has invalid span_object {raw!r}.",
            f"Allowed: {_ALLOWED_SPAN_OBJECTS}.",
        ))
    return raw


def _validate_suggested_fix(path: str, code: str, raw: Any) -> Optional[SuggestedFixSpec]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'suggested_fix' must be a mapping when present,",
            f"got {type(raw).__name__}.",
        ))

    kind = raw.get('kind')
    if kind not in _ALLOWED_SUGGESTED_FIX_KINDS:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'suggested_fix.kind' must be one of",
            f"{_ALLOWED_SUGGESTED_FIX_KINDS!r}, got {kind!r}.",
        ))

    target = raw.get('target')
    if not isinstance(target, str) or not target.strip():
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'suggested_fix.target' must be a non-empty string.",
        ))

    anchor_ref = raw.get('anchor_ref')
    if not isinstance(anchor_ref, str) or not anchor_ref.startswith('refs.'):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'suggested_fix.anchor_ref' must be a refs.<field> string.",
        ))

    text_template = raw.get('text_template', '')
    if not isinstance(text_template, str):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'suggested_fix.text_template' must be a string.",
        ))

    rationale = raw.get('rationale')
    if not isinstance(rationale, str) or not rationale.strip():
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'suggested_fix.rationale' must be a non-empty string.",
        ))

    return SuggestedFixSpec(
        kind=kind,
        target=target.strip(),
        anchor_ref=anchor_ref,
        text_template=text_template,
        rationale=rationale.strip(),
    )


def _validate_for_llm(path: str, code: str, raw: Any) -> Optional[ForLlmSpec]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'for_llm' must be a mapping when present,",
            f"got {type(raw).__name__}.",
        ))
    missing = [k for k in _FOR_LLM_REQUIRED_KEYS if k not in raw]
    if missing:
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'for_llm' is missing required keys {missing}.",
            f"Required: {_FOR_LLM_REQUIRED_KEYS}.",
        ))
    summary = raw['summary']
    if not isinstance(summary, str) or not summary.strip():
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'for_llm.summary' must be a non-empty string.",
        ))
    actions_raw = raw['recommended_actions']
    if not isinstance(actions_raw, list):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'for_llm.recommended_actions' must be a list,",
            f"got {type(actions_raw).__name__}.",
        ))
    for i, action in enumerate(actions_raw):
        if not isinstance(action, dict):
            raise CodesSchemaError(_ctx(
                path,
                f"code {code!r} 'for_llm.recommended_actions[{i}]' must be a",
                f"mapping, got {type(action).__name__}.",
            ))
    do_not_raw = raw['do_not']
    if not isinstance(do_not_raw, list):
        raise CodesSchemaError(_ctx(
            path,
            f"code {code!r} 'for_llm.do_not' must be a list,",
            f"got {type(do_not_raw).__name__}.",
        ))
    for i, item in enumerate(do_not_raw):
        if not isinstance(item, str):
            raise CodesSchemaError(_ctx(
                path,
                f"code {code!r} 'for_llm.do_not[{i}]' must be a string,",
                f"got {type(item).__name__}.",
            ))
    return ForLlmSpec(
        summary=summary.strip(),
        recommended_actions=tuple(MappingProxyType(dict(a)) for a in actions_raw),
        do_not=tuple(do_not_raw),
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
