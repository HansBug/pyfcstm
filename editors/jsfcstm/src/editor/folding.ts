import type {TextDocumentLike} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {walkAstNodes, type FcstmAstRangeNode} from './ast-walk';

export interface FcstmFoldingRange {
    startLine: number;
    endLine: number;
    startCharacter?: number;
    endCharacter?: number;
    kind?: 'comment' | 'imports' | 'region';
}

function pushUnique(
    ranges: FcstmFoldingRange[],
    range: FcstmFoldingRange,
    seen: Set<string>
): void {
    const key = [
        range.startLine,
        range.endLine,
        range.startCharacter ?? '',
        range.endCharacter ?? '',
        range.kind ?? '',
    ].join(':');
    if (seen.has(key)) {
        return;
    }

    seen.add(key);
    ranges.push(range);
}

function foldableNodeToRange(node: FcstmAstRangeNode): FcstmFoldingRange | null {
    if (node.range.start.line >= node.range.end.line) {
        return null;
    }

    switch (node.kind) {
        case 'stateDefinition':
        case 'operationBlock':
        case 'ifStatement':
        case 'ifBranch':
            return {
                startLine: node.range.start.line,
                endLine: node.range.end.line,
                kind: 'region',
            };
        case 'importStatement':
            return {
                startLine: node.range.start.line,
                endLine: node.range.end.line,
                kind: 'imports',
            };
        default:
            return null;
    }
}

function collectCommentRanges(document: TextDocumentLike): FcstmFoldingRange[] {
    const ranges: FcstmFoldingRange[] = [];
    const text = document.getText();
    const lines = text.split('\n');
    let startLine: number | null = null;

    for (let index = 0; index < lines.length; index++) {
        const line = lines[index];
        const blockStart = line.indexOf('/*');
        if (startLine === null && blockStart >= 0) {
            const blockEnd = line.indexOf('*/', blockStart + 2);
            if (blockEnd < 0) {
                startLine = index;
            }
        }
        if (startLine !== null && line.includes('*/') && index > startLine) {
            ranges.push({
                startLine,
                endLine: index,
                kind: 'comment',
            });
            startLine = null;
        }
    }

    return ranges;
}

/**
 * Collect foldable regions for FCSTM source.
 */
export async function collectFoldingRanges(
    document: TextDocumentLike
): Promise<FcstmFoldingRange[]> {
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const rootNode = snapshot.nodes[snapshot.rootFile];
    const ast = rootNode?.ast;
    if (!ast) {
        return collectCommentRanges(document);
    }

    const ranges: FcstmFoldingRange[] = [];
    const seen = new Set<string>();
    for (const commentRange of collectCommentRanges(document)) {
        pushUnique(ranges, commentRange, seen);
    }

    walkAstNodes(ast, node => {
        const range = foldableNodeToRange(node);
        if (range) {
            pushUnique(ranges, range, seen);
        }
    });

    return ranges.sort((left, right) => (
        left.startLine - right.startLine
        || left.endLine - right.endLine
    ));
}
