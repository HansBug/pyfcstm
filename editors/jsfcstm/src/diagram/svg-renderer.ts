/**
 * Compatibility entry point for the canonical diagram SVG renderer.
 *
 * The implementation lives in ``./render/svg`` so the VSCode webview and
 * Python bundle consume exactly the same emitter. This small adapter keeps
 * the existing jsfcstm public function returning a string for callers that
 * do not need canvas dimensions.
 */
import type {FcstmElkNode, ResolvedFcstmDiagramPreviewOptions} from './model';
import {
    renderSvg,
    type RenderOptions,
    type RenderedSvg,
} from './render/svg';

export type {RenderOptions, RenderedSvg};

export function renderFcstmDiagramSvg(
    canvas: FcstmElkNode,
    options: ResolvedFcstmDiagramPreviewOptions,
    renderOptions: RenderOptions = {},
): string {
    return renderSvg(canvas, options, renderOptions).svg;
}

export {renderSvg};
