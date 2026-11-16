"""Explicit boundaries for consumers that still require a single active path."""

from .region import Region, walk_namespaces
from ..diagnostics.sink import DiagnosticSink
from ..utils.validate import ModelDiagnostic


def require_supported_model(model, operation: str) -> None:
    """Reject region models before an unsupported consumer performs work.

    :param model: State machine or state subtree passed to a public consumer.
    :param operation: Name of the operation whose support is being checked.
    :raises ModelValidationError: If the operation cannot preserve the model.
    """
    root = getattr(model, 'root_state', model)
    for namespace in walk_namespaces(root):
        if isinstance(namespace, Region):
            DiagnosticSink().emit(ModelDiagnostic(
                code='E_UNSUPPORTED_FEATURE', severity='error',
                message='%s does not support region models yet.' % operation,
                span=namespace._span,
                refs={'feature': 'region',
                      'source_path': getattr(namespace, '_source_path', None)},
            ))
