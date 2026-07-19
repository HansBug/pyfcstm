"""
Internal MiniRacer bridge for the shared offline diagram assets.

The package roadmap is intentionally small and explicit:

.. list-table:: Exported asset-runtime surfaces
   :header-rows: 1

   * - Surface
     - Responsibility
   * - :class:`DiagramAssetEngine`
     - Load the bundled renderer and expose validated SVG/PNG feasibility operations.
   * - :class:`DiagramAssetError`
     - Report missing or unusable packaged resources with recovery guidance.
   * - :class:`DiagramRenderError`
     - Report invalid DiagramData or renderer output after startup.
   * - :class:`DiagramRenderLimitError`
     - Report a scale or bounded-output limit violation before rendering.
   * - :class:`DiagramEngineMetadataError`
     - Report unavailable MiniRacer distribution metadata.
   * - :class:`DiagramEngineConflictError`
     - Reject simultaneous legacy and modern MiniRacer installations.

The public ``StateMachine.diagram`` facade, CLI commands, and final export
API are follow-up work. This package owns only the asset-runtime boundary and
does not promise a stable user-facing diagram API yet.

Example::

    >>> from pyfcstm.diagram import DiagramAssetEngine
    >>> engine = DiagramAssetEngine(timeout=30.0)
    >>> isinstance(engine, DiagramAssetEngine)
    True
"""

from .engine import (
    DiagramAssetError,
    DiagramAssetEngine,
    DiagramEngineConflictError,
    DiagramEngineMetadataError,
    DiagramRenderError,
    DiagramRenderLimitError,
)

__all__ = [
    "DiagramAssetEngine",
    "DiagramAssetError",
    "DiagramEngineConflictError",
    "DiagramEngineMetadataError",
    "DiagramRenderError",
    "DiagramRenderLimitError",
]
