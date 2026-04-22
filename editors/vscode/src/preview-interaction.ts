/**
 * Pure decision helper for the FCSTM preview webview pointer interactions.
 *
 * The webview side (inlined script) and the verify test both consume this
 * helper so the "plain click vs Ctrl/Cmd-click vs drag-pan" contract stays in
 * one place. Keep this module free of DOM/vscode imports so it can be required
 * directly from Node-based verify scripts.
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
    | {type: 'revealSource'};

export const PREVIEW_DRAG_THRESHOLD_PX = 4;

export function decidePreviewPointerAction(input: PointerActionInput): PointerAction {
    if (input.dragMovedPx > PREVIEW_DRAG_THRESHOLD_PX) {
        return {type: 'none'};
    }
    if (!input.kind) {
        return {type: 'none'};
    }
    if (input.kind === 'chevron' && !input.modifier) {
        return {type: 'toggleCollapse'};
    }
    if (input.modifier && input.hasRange) {
        return {type: 'revealSource'};
    }
    return {type: 'none'};
}
