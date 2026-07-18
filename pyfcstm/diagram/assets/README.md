# Python Diagram Runtime Assets

This directory contains the offline resources used by the Python diagram
runtime. ``pyfcstm.diagram`` loads the JavaScript renderer, resvg WebAssembly
module, and embedded fonts inside MiniRacer to provide ELK layout, SVG output,
PNG rasterization, and expanded vector SVG output without Node.js, a browser,
or system-font dependencies.

## Maintenance Rules

- Rebuild generated resources only with ``make build_assets`` from the
  repository root. Do not edit generated files or copy them from another
  build directory.
- Source URLs, versions, SHA-256 values, byte budgets, font metadata, and
  license provenance are recorded in
  ``tools/diagram_assets/asset-lock.json``.
- After changing a source or build rule, run ``make build_assets`` and
  ``make diagram_assets_check`` followed by the relevant tests, package build,
  and archive checks.
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

### Generated resources shipped in Python packages

- ``renderer.js``: minified ES2017 IIFE containing ELK, SVG rendering, and the
  Python entrypoint.
- ``resvg-binding.js``: pinned resvg JavaScript binding.
- ``resvg-bridge.js``: restricted MiniRacer bridge and font-registration API.
- ``host-shim.js``: the minimal host-environment shim required by MiniRacer.
- ``resvg.wasm``: pinned resvg WebAssembly backend.
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
