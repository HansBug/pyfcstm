"""
Internal MiniRacer bridge for the shared offline diagram assets.

The package roadmap is intentionally small and explicit:

.. list-table:: Exported asset-runtime surfaces
   :header-rows: 1

   * - Surface
     - Responsibility
   * - :class:`DiagramAssetEngine`
     - Load the bundled renderer and expose SVG/PNG rendering operations.
   * - :class:`DiagramAssetError`
     - Report missing or unusable packaged resources with recovery guidance.
   * - :class:`DiagramRenderError`
     - Report invalid DiagramData or renderer output after startup.
   * - :class:`DiagramEngineMetadataError`
     - Report unavailable MiniRacer distribution metadata.
   * - :class:`DiagramEngineConflictError`
     - Reject simultaneous legacy and modern MiniRacer installations.
   * - :class:`Diagram`
     - Build portable data and a self-contained three-mode browser viewer.

The public :class:`Diagram` facade is layered on top of this asset boundary;
the renderer remains shared with jsfcstm and the VSCode preview.

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
)
from .api import Diagram, DiagramData, DiagramOptions, DiagramViewState

__all__ = [
    "DiagramAssetEngine",
    "DiagramAssetError",
    "DiagramEngineConflictError",
    "DiagramEngineMetadataError",
    "DiagramRenderError",
    "Diagram",
    "DiagramData",
    "DiagramOptions",
    "DiagramViewState",
]
