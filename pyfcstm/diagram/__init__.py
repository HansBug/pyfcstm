"""
Internal MiniRacer bridge for the shared offline diagram assets.

The module contains:

* :class:`DiagramAssetEngine` - Loads the generated ES2017 renderer and
  exposes SVG, PNG, and normalized-vector feasibility operations.
* :class:`DiagramAssetError` - Reports missing assets and renderer failures.
* :class:`DiagramEngineMetadataError` - Reports unavailable distribution
  metadata needed to select one MiniRacer runtime.
* :class:`DiagramEngineConflictError` - Identifies incompatible dual engine
  installations before a JavaScript context is created.

The public ``StateMachine.diagram`` facade is intentionally deferred to the
follow-up Python API work; this package only owns the asset-runtime boundary.
"""

from .engine import (
    DiagramAssetError,
    DiagramAssetEngine,
    DiagramEngineConflictError,
    DiagramEngineMetadataError,
)

__all__ = [
    "DiagramAssetEngine",
    "DiagramAssetError",
    "DiagramEngineConflictError",
    "DiagramEngineMetadataError",
]
