"""
Schema-payload checker for diagnostics emitted by pyfcstm.

I-e from PR #115 review: parity tests historically only compared the
emitted code set across pyfcstm/jsfcstm, leaving room for schema↔emit
drift to land silently (C-A/B/C/D were exactly this). This helper is
the mechanical guard against future drift.

The check is single-source-of-truth driven: it pulls field declarations
from :data:`pyfcstm.diagnostics.CODE_REGISTRY`, which is loaded from
``pyfcstm/diagnostics/codes.yaml`` at import time. Every assertion that
fires here corresponds to a violation of that YAML.
"""

from typing import Iterable, Optional

from pyfcstm.diagnostics import CODE_REGISTRY
from pyfcstm.diagnostics.codes import CodeFieldSpec
from pyfcstm.utils import ModelDiagnostic


_TYPE_PREDICATES = {
    'str': lambda v: isinstance(v, str),
    'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'float': lambda v: isinstance(v, float),
    'number': lambda v: (
        isinstance(v, (int, float)) and not isinstance(v, bool)
    ),
    'bool': lambda v: isinstance(v, bool),
    'list[str]': lambda v: isinstance(v, list) and all(isinstance(item, str) for item in v),
    'Span': lambda v: v is None or hasattr(v, 'line'),
    'str_or_null': lambda v: v is None or isinstance(v, str),
    'int_or_null': lambda v: v is None or (isinstance(v, int) and not isinstance(v, bool)),
}


def _type_ok(value, type_token: str) -> bool:
    predicate = _TYPE_PREDICATES.get(type_token)
    if predicate is None:
        # Unknown type token — fall back to always-pass so the helper
        # stays forward-compatible. The yaml-schema test is the place
        # that catches new type tokens not in this table.
        return True
    return predicate(value)


def assert_refs_match_schema(diag: ModelDiagnostic, *, context: str = '') -> None:
    """Assert that ``diag.refs`` conforms to the schema declared for
    ``diag.code`` in ``codes.yaml``.

    Checks performed:

    1. Every key in ``refs`` is declared in the schema (no extras).
    2. Every required schema field is present and non-None in ``refs``.
    3. If the field declares an ``enum``, the actual value is a member.
    4. The actual value's runtime type matches the schema's ``type``
       token (``str`` / ``int`` / ``list[str]`` / ``str_or_null`` etc.).

    :param diag: Diagnostic to validate.
    :type diag: pyfcstm.utils.ModelDiagnostic
    :param context: Optional context string prefixed onto every failure
        message — typically the fixture or test name.
    :type context: str, optional
    :raises AssertionError: If any of the checks above fails.
    """
    prefix = f'{context}: ' if context else ''
    spec = CODE_REGISTRY.get(diag.code)
    assert spec is not None, f'{prefix}unknown code {diag.code!r}'

    declared = set(spec.refs_schema.keys())
    actual = set(diag.refs.keys())
    extra = actual - declared
    assert not extra, (
        f'{prefix}{diag.code} refs has undeclared keys {extra} '
        f'(declared={sorted(declared)})'
    )

    for field_name in spec.required_fields():
        assert field_name in diag.refs, (
            f'{prefix}{diag.code} refs missing required key {field_name!r}'
        )
        assert diag.refs[field_name] is not None, (
            f'{prefix}{diag.code} refs[{field_name!r}] is required '
            f'but value is None'
        )

    for field_name, field_spec in spec.refs_schema.items():
        if field_name not in diag.refs:
            continue
        value = diag.refs[field_name]

        if field_spec.enum:
            allowed = set(field_spec.enum)
            assert value in allowed, (
                f'{prefix}{diag.code} refs[{field_name!r}] = {value!r} '
                f'not in declared enum {sorted(allowed)}'
            )

        assert _type_ok(value, field_spec.type), (
            f'{prefix}{diag.code} refs[{field_name!r}] = {value!r} '
            f'has runtime type {type(value).__name__}, expected schema '
            f'type {field_spec.type!r}'
        )


def assert_all_diags_match_schema(
    diagnostics: Iterable[ModelDiagnostic], *, context: str = '',
) -> None:
    """Apply :func:`assert_refs_match_schema` to every diagnostic in
    ``diagnostics``."""
    for diag in diagnostics:
        assert_refs_match_schema(diag, context=context)
