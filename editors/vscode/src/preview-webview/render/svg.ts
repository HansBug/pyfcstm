/**
 * VSCode compatibility surface for the shared jsfcstm renderer.
 *
 * The webview must not carry a second SVG emitter. Keeping this import
 * relative to the source package makes local geometry scripts and the
 * packaged extension consume the same implementation before npm packing.
 */
export {
    renderSvg,
} from '../../../../jsfcstm/src/diagram/render/svg';
export type {
    RenderOptions,
    RenderedSvg,
} from '../../../../jsfcstm/src/diagram/render/svg';
