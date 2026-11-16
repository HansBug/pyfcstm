"""Temporarily reject syntax whose model semantics are not implemented.

Remove the region rejection when model construction preserves and validates
regions, and the active-query rejection when model lowering implements queries.
Delete this module once neither rejection is needed. Backend support checks
belong to the respective execution or rendering entry points.
"""

from dataclasses import fields

from ..diagnostics.sink import DiagnosticSink
from ..dsl import node as dsl_nodes
from ..utils.validate import ModelDiagnostic


def _unsupported_nodes(node):
    """Yield unsupported syntax sites, stopping at an unsupported owner."""
    if isinstance(node, dsl_nodes.ActiveStateQuery):
        yield node, "active"
    elif isinstance(node, dsl_nodes.ASTNode):
        for item in fields(node):
            yield from _unsupported_nodes(getattr(node, item.name))
    elif isinstance(node, list):
        for item in node:
            yield from _unsupported_nodes(item)


def reject_unsupported_syntax(node, sink: DiagnosticSink) -> bool:
    """Emit capability errors and return whether construction must stop.

    A transition can retain the same guard in both its compatibility field and
    its combo trigger. Source coordinates identify that single authored site
    even when import assembly has cloned the two references separately.
    """
    seen = set()
    for unsupported, feature in _unsupported_nodes(node):
        span = unsupported._span
        source_path = getattr(unsupported, "_source_path", None)
        key = (feature, source_path, span if span is not None else id(unsupported))
        if key in seen:
            continue
        seen.add(key)
        sink.emit(ModelDiagnostic(
            code="E_UNSUPPORTED_FEATURE",
            severity="error",
            message="The %r feature is parsed but is not supported by model construction." % feature,
            span=span,
            refs={"feature": feature, "source_path": source_path},
        ))
    return bool(seen)
