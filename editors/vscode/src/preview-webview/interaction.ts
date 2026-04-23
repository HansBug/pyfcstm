/**
 * Pure decision helper re-exported from ``src/preview-interaction.ts``
 * so the Vue webview and the Node-side verify scripts share a single
 * implementation. Interaction contract:
 *
 *   - drag past the threshold cancels any click (pan, not click).
 *   - plain click on chevron → toggle collapse.
 *   - plain click on a state / transition / label → select it.
 *   - plain click on empty space → clear the current selection.
 *   - Ctrl/Cmd + click on an element with a range → reveal source.
 */
export {
    decidePreviewPointerAction,
    PREVIEW_DRAG_THRESHOLD_PX,
    type PointerAction,
    type PointerActionInput,
    type PointerKind,
} from '../preview-interaction';
