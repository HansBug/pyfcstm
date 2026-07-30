"""
Render an FCSTM state machine as portable data or a self-contained viewer.

This package turns a :class:`pyfcstm.model.model.StateMachine` into two things: a
JSON-compatible description of the diagram that carries no local paths, and a
single HTML file that displays it offline with the source, the diagram, and a
linked comparison of the two. The geometry and SVG rendering are shared with
jsfcstm and the VSCode preview rather than reimplemented here.

.. list-table:: Public surfaces
   :header-rows: 1

   * - Surface
     - Responsibility
   * - :class:`~pyfcstm.diagram.api.Diagram`
     - Immutable snapshot: portable data, and a three-mode browser viewer.
   * - :class:`~pyfcstm.diagram.api.DiagramData`
     - Frozen, hashable portable diagram description.
   * - :class:`~pyfcstm.diagram.api.DiagramOptions`
     - Renderer choices: detail preset, direction, palette, mode, CJK locale.
   * - :class:`~pyfcstm.diagram.api.DiagramViewState`
     - Initial browser state: view mode, collapse set, zoom and pan.

.. list-table:: Failure surfaces
   :header-rows: 1

   * - Surface
     - Raised when
   * - :class:`~pyfcstm.diagram.engine.DiagramError`
     - Base class for every failure below.
   * - :class:`~pyfcstm.diagram.engine.DiagramUnavailableError`
     - An optional capability is absent: no browser, or no headless runtime.
   * - :class:`~pyfcstm.diagram.engine.DiagramAssetError`
     - A packaged viewer, font or WASM asset is missing or unreadable.
   * - :class:`~pyfcstm.diagram.engine.DiagramRenderError`
     - The renderer rejected the supplied data or returned nothing usable.
   * - :class:`~pyfcstm.diagram.engine.DiagramEngineMetadataError`
     - The installed MiniRacer distribution reports no usable metadata.
   * - :class:`~pyfcstm.diagram.engine.DiagramEngineConflictError`
     - Both the legacy and the modern MiniRacer distribution are installed.
   * - :class:`~pyfcstm.diagram.engine.DiagramEngineLoadError`
     - An installed MiniRacer distribution cannot be imported.

.. list-table:: Maintenance surface
   :header-rows: 1

   * - Surface
     - Responsibility
   * - :class:`~pyfcstm.diagram.engine.DiagramAssetEngine`
     - Load the bundled renderer and drive headless SVG/PNG rendering.

.. note::
   The public surfaces and the error classes are stable entry points.
   :class:`~pyfcstm.diagram.engine.DiagramAssetEngine` is the internal asset-runtime bridge; its shape
   is settled together with the synchronous headless capability, so depend on
   it only from maintenance tooling. Headless rendering additionally needs the
   optional MiniRacer runtime, which ``pip install pyfcstm[viz]`` provides.

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root { state A; [*] -> A; }')
    >>> view = model.diagram(direction="LR")
    >>> sorted(view.to_dict())
    ['eventLegend', 'kind', 'machineName', 'rootState', 'summary', 'variables']
    >>> view.options.direction
    'LR'
"""

from .engine import (
    DiagramAssetError,
    DiagramAssetEngine,
    DiagramError,
    DiagramEngineConflictError,
    DiagramEngineLoadError,
    DiagramEngineMetadataError,
    DiagramRenderError,
    DiagramUnavailableError,
)
from .api import Diagram, DiagramData, DiagramOptions, DiagramViewState

__all__ = [
    "DiagramAssetEngine",
    "DiagramError",
    "DiagramAssetError",
    "DiagramUnavailableError",
    "DiagramEngineConflictError",
    "DiagramEngineLoadError",
    "DiagramEngineMetadataError",
    "DiagramRenderError",
    "Diagram",
    "DiagramData",
    "DiagramOptions",
    "DiagramViewState",
]
