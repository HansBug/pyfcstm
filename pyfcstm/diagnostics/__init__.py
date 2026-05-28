"""
Structured diagnostic codes and design-health reporting for pyfcstm state
machines.

This package hosts the contract surface for the diagnostics that
:mod:`pyfcstm.model` (and, in later PRs, a static model inspector) emits.
It is *not* a formal-verification framework — Z3-based reachability and
guard-satisfiability live under :mod:`pyfcstm.solver`.

This package currently exposes:

* :mod:`pyfcstm.diagnostics.codes` — the single source of truth for
  diagnostic codes (``codes.yaml`` + the :data:`CODE_REGISTRY` loader).
* :class:`CodesSchemaError` — raised on import-time failure of the loader.

Future PRs in the Layer 1 / Layer 2 work add:

* the structured ``ModelDiagnostic`` emit pipeline in :mod:`pyfcstm.model`
* a static model inspector that produces design-health warnings
* a static simulation auditor that dry-runs speculative validation across
  the model

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
    EventInfo,
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
    'CodeFieldSpec',
    'CodeSpec',
    'CodesSchemaError',
    'DiagnosticSink',
    'EventInfo',
    'ForLlmSpec',
    'ModelInspect',
    'ModelMetrics',
    'StateInfo',
    'TransitionInfo',
    'VariableInfo',
    'inspect_model',
    'load_codes',
]
