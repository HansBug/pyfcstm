/**
 * Pure decision helper for the FCSTM preview webview pointer interactions.
 *
 * The webview side (inlined script) and the verify test both consume this
 * helper so the interaction contract stays in one place:
 *
 *   - drag past the threshold cancels any click (the mouse was panning).
 *   - plain click on chevron → toggle collapse.
 *   - plain click on a state / transition / label → select it; the Details
 *     side panel displays its full information (events / actions / event,
 *     guard, effect, source range, etc.).
 *   - plain click on empty space → clear the current selection.
 *   - Ctrl/Cmd + click on an element with a source range → reveal the
 *     range in the editor (JetBrains-style code tracking).
 */

export type PointerKind =
    | 'state'
    | 'composite-state'
    | 'transition'
    | 'transition-label'
    | 'chevron'
    | 'pseudo-init'
    | 'pseudo-exit'
    | null;

export interface PointerActionInput {
    kind: PointerKind;
    modifier: boolean;
    dragMovedPx: number;
    hasRange: boolean;
}

export type PointerAction =
    | {type: 'none'}
    | {type: 'toggleCollapse'}
    | {type: 'revealSource'}
    | {type: 'select'}
    | {type: 'clearSelection'};

export const PREVIEW_DRAG_THRESHOLD_PX = 4;

/** Set of kinds that the Details side panel knows how to display. */
const SELECTABLE_KINDS: ReadonlySet<Exclude<PointerKind, null>> = new Set([
    'state',
    'composite-state',
    'transition',
    'transition-label',
    'pseudo-init',
    'pseudo-exit',
]);

export function decidePreviewPointerAction(input: PointerActionInput): PointerAction {
    if (input.dragMovedPx > PREVIEW_DRAG_THRESHOLD_PX) {
        return {type: 'none'};
    }
    // Modifier held: only ever reveal source; never fall back to select or
    // collapse. If the element has no range there's nothing to jump to.
    if (input.modifier) {
        if (input.kind && input.hasRange) {
            return {type: 'revealSource'};
        }
        return {type: 'none'};
    }
    if (!input.kind) {
        // Click on blank canvas with no modifier clears the current selection.
        return {type: 'clearSelection'};
    }
    if (input.kind === 'chevron') {
        return {type: 'toggleCollapse'};
    }
    if (SELECTABLE_KINDS.has(input.kind)) {
        return {type: 'select'};
    }
    return {type: 'none'};
}
