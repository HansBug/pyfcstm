"""
Explicit boundaries for consumers that still require a single active path.

Region models are understood by the model layer, but some consumers (analysis,
rendering, export, code generation, bounded model checking) still assume one
active state at a time. Instead of silently producing a wrong result for such
a model, those consumers call :func:`require_supported_model` first and fail
with a structured ``E_UNSUPPORTED_FEATURE`` diagnostic that names the
operation and the feature. ``active()`` queries are not a boundary: they are
lowered into ordinary hidden variables, so every consumer takes them like any
other model.

The module contains:

* :func:`require_supported_model` - Reject models a consumer cannot preserve

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> from pyfcstm.model.support import require_supported_model
    >>> ordinary = load_state_machine_from_text('state Root { [*] -> Idle; state Idle; }')
    >>> require_supported_model(ordinary, 'demo export') is None
    True
    >>> parallel = load_state_machine_from_text('''
    ... state Root {
    ...     [*] -> Run;
    ...     state Run { region A { [*] -> X; state X; } region B { [*] -> Y; state Y; } }
    ... }
    ... ''')
    >>> from pyfcstm.utils.validate import ModelValidationError
    >>> try:
    ...     require_supported_model(parallel, 'demo export')
    ... except ModelValidationError as error:
    ...     print([(item.code, item.message) for item in error.diagnostics])
    [('E_UNSUPPORTED_FEATURE', 'demo export does not support region models yet.')]
"""

from .region import Region, walk_namespaces
from ..diagnostics.sink import DiagnosticSink
from ..utils.validate import ModelDiagnostic


def require_supported_model(model, operation: str) -> None:
    """
    Reject region models before an unsupported consumer works.

    Every region in the subtree is reported with ``feature='region'``, one
    diagnostic per region. Problems are emitted through a strict
    :class:`~pyfcstm.diagnostics.sink.DiagnosticSink`, which raises at the
    first one, so ``error.diagnostics`` holds exactly one entry. Models without
    regions pass silently. ``active()`` queries never matter here: the model
    lowers them into ordinary variables, so the operations that call this
    function work on a model that uses them.

    :param model: State machine or state subtree passed to a public consumer.
    :type model: Union[pyfcstm.model.model.StateMachine, pyfcstm.model.model.State]
    :param operation: Name of the operation whose support is being checked; it
        starts the diagnostic message, for example ``'inspect'``.
    :type operation: str
    :return: ``None`` when the model is supported.
    :rtype: None
    :raises pyfcstm.utils.validate.ModelValidationError: If the operation cannot
        preserve the model; each diagnostic has code ``E_UNSUPPORTED_FEATURE``
        and ``refs['feature']`` set to ``'region'``.

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> from pyfcstm.model.support import require_supported_model
        >>> from pyfcstm.utils.validate import ModelValidationError
        >>> queried = load_state_machine_from_text('''
        ... def int x = 0;
        ... state Root { [*] -> I; state I; I -> J : if [active("Root.J")]; state J; }
        ... ''')
        >>> require_supported_model(queried, 'demo export') is None
        True
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
