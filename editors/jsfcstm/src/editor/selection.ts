import {createRange, rangeContains, TextDocumentLike, TextPositionLike, TextRange} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {walkAstNodes} from './ast-walk';
import {rangeLength} from './ranges';

export interface FcstmSelectionRange {
    range: TextRange;
    parent?: FcstmSelectionRange;
}

function buildWordRange(document: TextDocumentLike, position: TextPositionLike): TextRange | null {
    const line = document.lineAt(position.line).text;
    if (!line) {
        return null;
    }

    let start = position.character;
    let end = position.character;
    while (start > 0 && /[A-Za-z0-9_./]/.test(line[start - 1])) {
        start--;
    }
    while (end < line.length && /[A-Za-z0-9_./]/.test(line[end])) {
        end++;
    }

    if (start === end) {
        return null;
    }

    return createRange(position.line, start, position.line, end);
}

function uniqueRanges(ranges: TextRange[]): TextRange[] {
    const seen = new Set<string>();
    const results: TextRange[] = [];

    for (const range of ranges) {
        const key = [
            range.start.line,
            range.start.character,
            range.end.line,
            range.end.character,
        ].join(':');
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        results.push(range);
    }

    return results;
}

function toSelectionChain(ranges: TextRange[]): FcstmSelectionRange | null {
    let parent: FcstmSelectionRange | undefined;
    for (let index = ranges.length - 1; index >= 0; index--) {
        parent = {
            range: ranges[index],
            parent,
        };
    }

    return parent || null;
}

/**
 * Collect nested selection ranges for one or more cursor positions.
 */
export async function collectSelectionRanges(
    document: TextDocumentLike,
    positions: TextPositionLike[]
): Promise<FcstmSelectionRange[]> {
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const ast = snapshot.nodes[snapshot.rootFile]?.ast;

    return positions.map(position => {
        const ranges: TextRange[] = [];
        const wordRange = buildWordRange(document, position);
        if (wordRange) {
            ranges.push(wordRange);
        }

        if (ast) {
            walkAstNodes(ast, node => {
                if (rangeContains(node.range, position)) {
                    ranges.push(node.range);
                }
            });
        }

        const unique = uniqueRanges(ranges)
            .sort((left, right) => rangeLength(left) - rangeLength(right));
        return toSelectionChain(unique) || {
            range: createRange(position.line, position.character, position.line, position.character),
        };
    });
}
