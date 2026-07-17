/**
 * Pure geometry helpers shared by the preview component and verification
 * harnesses.
 */

export interface PreviewViewportSize {
    width: number;
    height: number;
}

export interface PreviewSvgSize {
    width: number;
    height: number;
}

export interface PreviewViewTransform {
    tx: number;
    ty: number;
    scale: number;
}

/** Keep a small breathing room between the SVG and the stage border. */
export const PREVIEW_FIT_MARGIN_PX = 16;

/**
 * Compute the transform used by the preview's Fit-to-view action.
 *
 * The viewport is the actual ``.fcstm-stage__viewport`` rectangle, not the
 * containing webview or browser window.  Keeping this calculation pure lets
 * the production component and the right-pane verification harness assert
 * the same contract without duplicating arithmetic.
 */
export function computePreviewFit(
    viewport: PreviewViewportSize,
    svg: PreviewSvgSize,
    margin = PREVIEW_FIT_MARGIN_PX,
): PreviewViewTransform {
    const availableWidth = Math.max(40, viewport.width - margin * 2);
    const availableHeight = Math.max(40, viewport.height - margin * 2);
    const scale = Math.min(availableWidth / svg.width, availableHeight / svg.height, 1);
    return {
        tx: (viewport.width - svg.width * scale) / 2,
        ty: (viewport.height - svg.height * scale) / 2,
        scale,
    };
}
