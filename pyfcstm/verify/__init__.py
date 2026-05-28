"""
Structural verification and design-health diagnostics for pyfcstm state machines.

This package hosts:

* :mod:`pyfcstm.verify.codes` — the single source of truth for structured
  diagnostic codes (``codes.yaml`` + the :data:`CODE_REGISTRY` loader).

Future PRs in the Layer 1 / Layer 2 work add:

* a static model inspector that produces design-health warnings,
* a static simulation auditor that dry-runs speculative validation across
  the model.

See ``HansBug/pyfcstm`` issue #103 for the migration plan and ``codes.yaml``
for the authoritative code catalog.
"""

from .codes import CODE_REGISTRY, CodeFieldSpec, CodeSpec, load_codes

__all__ = [
    'CODE_REGISTRY',
    'CodeFieldSpec',
    'CodeSpec',
    'load_codes',
]
