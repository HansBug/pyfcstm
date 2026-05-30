"""
Structured diagnostic codes and design-health reporting for pyfcstm state
machines.

This package hosts the contract surface for diagnostics emitted by
:mod:`pyfcstm.model` and by inspect-based design-health analyzers.
It is *not* a formal-verification framework — Z3-based reachability and
guard-satisfiability live under :mod:`pyfcstm.solver`.

This package currently exposes:

* :mod:`pyfcstm.diagnostics.codes` — the single source of truth for
  diagnostic codes (``codes.yaml`` + the :data:`CODE_REGISTRY` loader).
* :class:`CodesSchemaError` — raised on import-time failure of the loader.
* :func:`inspect_model` and the related inspect dataclasses used by
  pyfcstm / jsfcstm parity checks and design-health diagnostics.
* :class:`DiagnosticSink` for strict-mode and collect-mode diagnostic
  emission.

See ``HansBug/pyfcstm`` issue #103 for the migration plan and ``codes.yaml``
for the authoritative code catalog.
"""

from .codes import (
    CODE_REGISTRY,
    CodeFieldSpec,
    CodeSpec,
    CodesSchemaError,
    ForLlmSpec,
    load_codes,
)
from .inspect import (
    ActionInfo,
    EventInfo,
    ForcedTransitionInfo,
    ModelInspect,
    ModelMetrics,
    StateInfo,
    TransitionInfo,
    VariableInfo,
    inspect_model,
)
from .sink import DiagnosticSink

__all__ = [
    'CODE_REGISTRY',
    'ActionInfo',
    'CodeFieldSpec',
    'CodeSpec',
    'CodesSchemaError',
    'DiagnosticSink',
    'EventInfo',
    'ForcedTransitionInfo',
    'ForLlmSpec',
    'ModelInspect',
    'ModelMetrics',
    'StateInfo',
    'TransitionInfo',
    'VariableInfo',
    'inspect_model',
    'load_codes',
]
