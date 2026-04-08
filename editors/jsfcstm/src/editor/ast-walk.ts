import type {TextRange} from '../utils/text';

export interface FcstmAstWalkNode {
    kind?: string;
    range?: TextRange;
    [key: string]: unknown;
}

export interface FcstmAstRangeNode extends FcstmAstWalkNode {
    kind: string;
    range: TextRange;
}

function isObject(value: unknown): value is FcstmAstWalkNode {
    return Boolean(value) && typeof value === 'object';
}

/**
 * Check whether a value looks like an AST node with a usable source range.
 */
export function isAstRangeNode(value: unknown): value is FcstmAstRangeNode {
    return isObject(value)
        && typeof value.kind === 'string'
        && Boolean(value.range)
        && isObject(value.range)
        && isObject(value.range.start)
        && isObject(value.range.end);
}

/**
 * Walk jsfcstm AST-shaped objects without depending on a concrete node family.
 */
export function walkAstNodes(
    value: unknown,
    visit: (node: FcstmAstRangeNode) => void,
    seen: Set<unknown> = new Set()
): void {
    if (!isObject(value) || seen.has(value)) {
        return;
    }

    seen.add(value);
    if (isAstRangeNode(value)) {
        visit(value);
    }

    for (const child of Object.values(value)) {
        if (Array.isArray(child)) {
            for (const item of child) {
                walkAstNodes(item, visit, seen);
            }
        } else if (isObject(child)) {
            walkAstNodes(child, visit, seen);
        }
    }
}
