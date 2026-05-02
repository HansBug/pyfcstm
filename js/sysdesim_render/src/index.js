// pyfcstm sysdesim sequence-diagram renderer.
//
// Entry point that exposes the IIFE global ``PyfcstmSysdesim``. The Python
// side (mini-racer) loads this bundle once, then calls ``PyfcstmSysdesim.render``
// per diagram. The renderer is self-contained: it does not require ELK.js or
// any DOM API and produces an SVG string directly.

import { renderSequenceSvg, RENDERER_VERSION } from "./sequence_svg.js";

export function render(timelineJson, options) {
  return renderSequenceSvg(timelineJson, options || {});
}

export function version() {
  return RENDERER_VERSION;
}
