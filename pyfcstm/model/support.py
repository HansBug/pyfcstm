"""Explicit boundaries for consumers that still require a single active path."""

from .region import Region, walk_namespaces
from ..diagnostics.sink import DiagnosticSink
from ..utils.validate import ModelDiagnostic


def require_supported_model(model, operation: str) -> None:
    """Reject region and activity models before an unsupported consumer works.

    :param model: State machine or state subtree passed to a public consumer.
    :param operation: Name of the operation whose support is being checked.
    :raises ModelValidationError: If the operation cannot preserve the model.
    """
    root = getattr(model, 'root_state', model)
    if getattr(root, '_active_queries', ()):
        DiagnosticSink().emit(ModelDiagnostic(
            code='E_UNSUPPORTED_FEATURE', severity='error',
            message='%s does not support active queries yet.' % operation,
            span=root._span,
            refs={'feature': 'active', 'source_path': getattr(root, '_source_path', None)},
        ))
    for namespace in walk_namespaces(root):
        if isinstance(namespace, Region):
            DiagnosticSink().emit(ModelDiagnostic(
                code='E_UNSUPPORTED_FEATURE', severity='error',
                message='%s does not support region models yet.' % operation,
                span=namespace._span,
                refs={'feature': 'region',
                      'source_path': getattr(namespace, '_source_path', None)},
            ))
