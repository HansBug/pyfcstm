"""Helpers for rendering structured diagnostic suggested fixes."""

from string import Formatter
from typing import Any, Dict, Mapping, Optional, Set

from .codes import CODE_REGISTRY


def _template_field_names(template: str) -> Set[str]:
    out: Set[str] = set()
    for _, field_name, _, _ in Formatter().parse(template):
        if field_name:
            out.add(field_name)
    return out


def render_suggested_fix(
        code: str,
        refs: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    """Render the ``codes.yaml`` suggested-fix template for one emit.

    :param code: Diagnostic code.
    :type code: str
    :param refs: Already-rendered diagnostic refs payload.
    :type refs: Mapping[str, Any]
    :return: JSON-friendly suggested-fix payload, or ``None`` if the code
        has no suggested-fix metadata.
    :rtype: Optional[Dict[str, Any]]
    """
    spec = CODE_REGISTRY.get(code)
    if spec is None or spec.suggested_fix is None:
        return None

    values = dict(refs)
    state_path = values.get('state_path')
    if isinstance(state_path, str):
        values.setdefault('state_name', state_path.rsplit('.', 1)[-1])
    composite_path = values.get('composite_path')
    if isinstance(composite_path, str):
        values.setdefault('composite_name', composite_path.rsplit('.', 1)[-1])

    suggested = spec.suggested_fix
    if not suggested.anchor_ref.startswith('refs.'):
        return None
    anchor_field = suggested.anchor_ref[5:]
    if values.get(anchor_field) is None:
        return None
    for field_name in _template_field_names(suggested.text_template):
        if values.get(field_name) is None:
            return None

    text = suggested.text_template.format(**values)
    return {
        'kind': suggested.kind,
        'target': suggested.target,
        'anchor': {
            'type': 'ref',
            'ref': suggested.anchor_ref,
        },
        'text': text,
        'rationale': suggested.rationale,
    }


def refs_with_suggested_fix(
        code: str,
        refs: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return ``refs`` copied with ``suggested_fix`` attached when declared."""
    out = dict(refs)
    fix = render_suggested_fix(code, out)
    if fix is not None:
        out['suggested_fix'] = fix
    return out
