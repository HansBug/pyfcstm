"""Naming and scope design-health diagnostics."""

from typing import TYPE_CHECKING, Dict, Iterable, List

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import ActionInfo


def collect_naming_warnings(actions: Iterable['ActionInfo']) -> List[ModelDiagnostic]:
    """Collect diagnostics for confusing named-action scopes."""
    return _named_action_shadows_ancestor_warnings(list(actions))


def _named_action_shadows_ancestor_warnings(actions) -> List[ModelDiagnostic]:
    by_name: Dict[str, List[object]] = {}
    for action in actions:
        if not action.name or action.is_ref:
            continue
        by_name.setdefault(action.name, []).append(action)

    diagnostics: List[ModelDiagnostic] = []
    for function_name, items in by_name.items():
        sorted_items = sorted(items, key=lambda item: item.state_path)
        for inner in sorted_items:
            ancestors = [
                outer for outer in sorted_items
                if _is_strict_ancestor(outer.state_path, inner.state_path)
            ]
            if not ancestors:
                continue
            outer = max(ancestors, key=lambda item: len(item.state_path))
            diagnostics.append(ModelDiagnostic(
                code='W_NAMED_ACTION_SHADOWS_ANCESTOR',
                span=inner.span,
                severity='warning',
                message=(
                    f'Named action {function_name!r} in {inner.state_path!r} '
                    f'shadows ancestor action in {outer.state_path!r}.'
                ),
                refs={
                    'function_name': function_name,
                    'inner_state_path': inner.state_path,
                    'outer_state_path': outer.state_path,
                },
            ))
    return diagnostics


def _is_strict_ancestor(outer_path: str, inner_path: str) -> bool:
    return bool(outer_path) and inner_path.startswith(f'{outer_path}.')
