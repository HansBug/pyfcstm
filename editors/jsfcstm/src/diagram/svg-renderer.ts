/**
 * Compatibility entry point for the canonical diagram SVG renderer.
 *
 * The implementation lives in ``./render/svg`` so the VSCode webview and
 * Python bundle consume exactly the same emitter. This small adapter keeps
 * the existing jsfcstm public function returning a string for callers that
 * do not need canvas dimensions.
 *
 * Lay a graph that has regions out with ``layoutFcstmGraph`` before drawing it;
 * see :func:`renderSvg` for what the drawing relies on.
 */
import type {FcstmElkNode, ResolvedFcstmDiagramPreviewOptions} from './model';
import {
    renderSvg,
    type RenderOptions,
    type RenderedSvg,
} from './render/svg';

export type {RenderOptions, RenderedSvg};

/**
 * Draw a laid-out graph as an SVG string.
 *
 * Same as ``renderSvg`` without the canvas size. A graph with regions must come
 * from ``layoutFcstmGraph``: it tiles the regions over their owner and sets the
 * dividers, which this function draws. A graph laid out by ``elk.layout`` alone
 * shows its regions without borders and without dividers.
 */
export function renderFcstmDiagramSvg(
    canvas: FcstmElkNode,
    options: ResolvedFcstmDiagramPreviewOptions,
    renderOptions: RenderOptions = {},
): string {
    return renderSvg(canvas, options, renderOptions).svg;
}

export {renderSvg};
