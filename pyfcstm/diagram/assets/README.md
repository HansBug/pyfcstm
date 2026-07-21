# Python Diagram Runtime Assets

This directory contains the offline resources used by the Python diagram
runtime. ``pyfcstm.diagram`` packages the JavaScript renderer, resvg WebAssembly
module, and embedded fonts for the shared offline runtime. ``viewer.js`` and
``viewer.css`` additionally carry the standalone browser shell which reuses the
VSCode preview components for FCSTM-only, diagram-only, and compare modes.
The browser host embeds ``svg2pdf.js`` 2.7.0 in ``viewer.js`` for vector PDF
export; Python synchronous headless export remains a later delivery stage.

## Maintenance Rules

- Rebuild generated resources only with ``make build_assets`` from the
  repository root. Do not edit generated files or copy them from another
  build directory.
- The official ``@resvg/resvg-wasm`` 2.6.2 package is restored from the locked
  ``editors/jsfcstm/package-lock.json`` entry. Source URLs, commits, SHA-256
  values, byte budgets, font metadata, and license provenance are recorded in
  ``tools/diagram_assets/asset-lock.json``.
- After changing a source or build rule, run ``make build_assets`` and
  ``make diagram_assets_check``, then run
  ``make DIAGRAM_REFERENCE=/abs/path/reference.json diagram_assets_verify``
  with the frozen custom 0.37 reference bundle. The parity gate must not be
  skipped.
- Generated files are ignored by the source-tree ``.gitignore``. ``README.md``,
  ``__init__.py``, ``.gitignore``, ``NOTICE.txt``, and license files are
  controlled metadata and must not be removed by the builder.
- Do not add temporary files, caches, unregistered fonts, or extra runtime
  dependencies. The asset and archive checkers reject unregistered files.

## Expected File List

### Controlled metadata in the source tree

- ``README.md``
- ``__init__.py``
- ``.gitignore`` (source-tree boundary marker; not included in wheels or
  source distributions)
- ``NOTICE.txt``
- ``LICENSE-MPL-2.0.txt``
- ``LICENSE-EPL-2.0.txt``
- ``LICENSE-OFL-1.1.txt``
- ``LICENSE-MIT.txt``

### Generated resources shipped in Python packages

- ``renderer.js``: minified ES2017 IIFE containing ELK, SVG rendering, and the
  Python entrypoint.
- ``resvg-binding.js``: official ``@resvg/resvg-wasm`` 2.6.2 JavaScript
  binding.
- ``resvg-bridge.js``: restricted MiniRacer bridge and font-registration API.
- ``host-shim.js``: the minimal host-environment shim required by MiniRacer.
- ``viewer.js``: self-contained Vue browser viewer bundle built from the
  VSCode preview components and standalone host adapter.
- ``viewer.css``: extracted styles for the standalone viewer bundle.
- ``svg2pdf.js`` 2.7.0 and its MIT-licensed dependencies are bundled inside
  ``viewer.js``; they are not separate runtime files.
- ``resvg.wasm``: official ``@resvg/resvg-wasm`` 2.6.2 WebAssembly backend.
- ``manifest.json``: generated-file paths, byte sizes, hashes, and provenance.
- ``fonts/JetBrainsMono-Regular.ttf``: Latin regular face.
- ``fonts/JetBrainsMono-Medium.ttf``: Latin medium face.
- ``fonts/JetBrainsMono-Bold.ttf``: Latin bold face.
- ``fonts/NotoSansSC-Regular.otf`` and ``fonts/NotoSansSC-Bold.otf``:
  Simplified Chinese (SC) regular and bold faces.
- ``fonts/NotoSansTC-Regular.otf`` and ``fonts/NotoSansTC-Bold.otf``:
  Traditional Chinese (TC) regular and bold faces.
- ``fonts/NotoSansHK-Regular.otf`` and ``fonts/NotoSansHK-Bold.otf``:
  Hong Kong Chinese (HK) regular and bold faces.
- ``fonts/NotoSansJP-Regular.otf`` and ``fonts/NotoSansJP-Bold.otf``:
  Japanese (JP) regular and bold faces.
- ``fonts/NotoSansKR-Regular.otf`` and ``fonts/NotoSansKR-Bold.otf``:
  Korean (KR) regular and bold faces.

The CJK faces are locale-specific OTF files rather than one multi-face TTC.
The Python runtime registers only the locale selected by the SVG, which keeps
MiniRacer memory use bounded while preserving deterministic glyph coverage.
All listed fonts are distributed under the SIL Open Font License 1.1. Exact
URLs, versions, SHA-256 values, and size budgets are authoritative in
``tools/diagram_assets/asset-lock.json``.
