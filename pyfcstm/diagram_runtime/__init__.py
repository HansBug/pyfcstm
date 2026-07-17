"""
Internal MiniRacer bridge for the shared offline diagram assets.

The module contains:

* :class:`DiagramAssetEngine` - Loads the generated ES2017 renderer and
  exposes SVG, PNG, and normalized-vector feasibility operations.
* :class:`DiagramAssetError` - Reports missing assets and renderer failures.

The public ``StateMachine.diagram`` facade is intentionally deferred to the
follow-up Python API work; this package only owns the asset-runtime boundary.
"""

from .engine import DiagramAssetError, DiagramAssetEngine

__all__ = ["DiagramAssetEngine", "DiagramAssetError"]
