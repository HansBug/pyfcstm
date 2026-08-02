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

/**
 * Every mark in the drawing that the pointer contract treats as a target.
 *
 * The values come first and the type is read off them. Writing the union by
 * hand and the set beside it left the two free to drift: a set that named one
 * too many was a type error, one that named one too few was silence, which is
 * the direction that matters -- a kind missing from the set is read as no kind
 * at all and its element quietly stops responding.
 */
export const POINTER_KINDS = [
    'state',
    'composite-state',
    'transition',
    'transition-label',
    'chevron',
    'pseudo-init',
    'pseudo-exit',
] as const;

export type PointerKind = (typeof POINTER_KINDS)[number] | null;

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

/**
 * Read a DOM mark as a pointer kind, or ``null`` when it names none.
 *
 * The drawing carries marks this contract has no opinion about -- the event and
 * action rows inside a state body are labels, not targets -- and the click
 * handler used to force whatever it read into the union with a cast, so the
 * compiler had nothing to say when an eighth mark appeared and the handler
 * treated it as a target that does nothing.
 *
 * :param value: The ``data-fcstm-kind`` attribute, if the element carried one.
 * :returns: The kind, or ``null`` for a mark outside this contract.
 */
export function asPointerKind(value: string | null | undefined): PointerKind {
    return (POINTER_KINDS as readonly string[]).includes(value || '')
        ? (value as PointerKind)
        : null;
}

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
