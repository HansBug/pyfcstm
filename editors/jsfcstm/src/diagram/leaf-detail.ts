/**
 * The rows a leaf state shows beneath its title, and the metrics used to
 * measure and draw them.
 *
 * Layout and drawing live apart -- ELK is told how big a node is in
 * ``elk-graph.ts`` and the node is drawn in ``render/svg.ts`` -- so the numbers
 * they agree on belong in one place. A node sized for three rows and drawn
 * with four spills over its own border, and a rendered SVG says nothing about
 * which of the two was wrong.
 *
 * Only the row advance and the inset are shared. Where the rows begin is
 * measured back from the height ELK actually assigned, so a disagreement moves
 * the separator rather than pushing text outside the box.
 */

/** Font size of a detail row, one step down from the 14px state title. */
export const LEAF_DETAIL_FONT_SIZE = 11;

/** Vertical advance from one detail row to the next. */
export const LEAF_DETAIL_LINE_HEIGHT = 15;

/** Space between the separator under the title and the first row. */
export const LEAF_DETAIL_TOP_GAP = 7;

/** Space beneath the last row. */
export const LEAF_DETAIL_BOTTOM_PAD = 9;

/** Distance from the node's left edge to the start of a row. */
export const LEAF_DETAIL_INSET_X = 12;

/**
 * Height of the band holding ``count`` rows, or zero when there are none.
 *
 * A leaf with no rows keeps the single centred title it has always had, so the
 * band must contribute nothing rather than a small constant -- otherwise every
 * diagram at every detail level grows by the padding.
 *
 * @param count Number of rows the node will draw.
 * @returns Height in user units.
 */
export function leafDetailBandHeight(count: number): number {
    if (count <= 0) {
        return 0;
    }
    return LEAF_DETAIL_TOP_GAP + count * LEAF_DETAIL_LINE_HEIGHT + LEAF_DETAIL_BOTTOM_PAD;
}
