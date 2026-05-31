import {getParser, ParseError} from '../dsl/parser';
import {inspectModel} from '../diagnostics';
import type {FcstmSemanticDocument} from '../semantics';
import {collectSemanticAnalysisDiagnosticsFromSemantic} from './analyzers';
import {
    createRange,
    FcstmDiagnostic,
    TextDocumentLike,
    TextRange,
} from '../utils/text';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {getWorkspaceGraph} from '../workspace';
import {resolveRangeFromRefs} from './inspect-ranges';
import {suggestedFixDiagnosticRange, suggestedFixIssueRange} from './suggested-fixes';

// Only suppress inspect codes that the semantic analyzer already reports with
// equivalent coverage. Const-folded false guards stay inspect-backed because
// the semantic analyzer only recognizes literal `false`.
export const SUPPRESSED_FROM_INSPECT_SURFACE = new Set([
    'W_UNREACHABLE_STATE',
    'W_UNUSED_EVENT',
]);

function canonicalDiagnosticData(value: unknown): unknown {
    if (Array.isArray(value)) {
        return value.map(item => canonicalDiagnosticData(item));
    }
    if (typeof value !== 'object' || value === null) {
        return value;
    }

    const out: Record<string, unknown> = {};
    const item = value as Record<string, unknown>;
    for (const key of Object.keys(item).sort()) {
        if (key === 'suggested_fix') continue;
        out[key] = canonicalDiagnosticData(item[key]);
    }
    return out;
}

export function diagnosticKey(diagnostic: FcstmDiagnostic): string {
    return JSON.stringify([
        diagnostic.code ?? null,
        canonicalDiagnosticData(diagnostic.data ?? null),
    ]);
}

function consumeDiagnosticCount(counts: Map<string, number>, key: string): boolean {
    const count = counts.get(key) ?? 0;
    if (count <= 0) return false;
    if (count === 1) {
        counts.delete(key);
    } else {
        counts.set(key, count - 1);
    }
    return true;
}

export function fullDocumentRange(document: TextDocumentLike): TextRange {
    const lastLine = Math.max(0, document.lineCount - 1);
    return createRange(0, 0, lastLine, document.lineAt(lastLine).text.length);
}

function rangeEquals(left: TextRange, right: TextRange): boolean {
    return left.start.line === right.start.line &&
        left.start.character === right.start.character &&
        left.end.line === right.end.line &&
        left.end.character === right.end.character;
}

export interface CollectInspectModelDiagnosticsOptions {
    rangeMode?: 'diagnostic' | 'issue';
}

export function collectInspectModelDiagnostics(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    model: Parameters<typeof inspectModel>[0],
    existingDiagnostics: FcstmDiagnostic[] = [],
    options: CollectInspectModelDiagnosticsOptions = {},
): FcstmDiagnostic[] {
    const existingCounts = new Map<string, number>();
    for (const diagnostic of existingDiagnostics) {
        const key = diagnosticKey(diagnostic);
        existingCounts.set(key, (existingCounts.get(key) ?? 0) + 1);
    }
    const fullRange = fullDocumentRange(document);
    const diagnostics: FcstmDiagnostic[] = [];

    for (const item of inspectModel(model).diagnostics) {
        if (SUPPRESSED_FROM_INSPECT_SURFACE.has(item.code)) continue;
        const diagnostic: FcstmDiagnostic = {
            range: fullRange,
            message: item.message,
            severity: item.severity,
            source: 'fcstm',
            code: item.code,
            data: item.refs,
        };
        const suggestedRange = options.rangeMode === 'issue'
            ? suggestedFixIssueRange(document, semantic, diagnostic)
            : suggestedFixDiagnosticRange(document, semantic, diagnostic);
        diagnostic.range = rangeEquals(suggestedRange, fullRange)
            ? resolveRangeFromRefs(document, semantic, item.refs) ?? fullRange
            : suggestedRange;
        if (consumeDiagnosticCount(existingCounts, diagnosticKey(diagnostic))) continue;
        diagnostics.push(diagnostic);
    }

    return diagnostics;
}

export function convertParseErrorToDiagnostic(
    error: ParseError,
    document: TextDocumentLike
): FcstmDiagnostic {
    const safeLineCount = Math.max(1, document.lineCount);
    const line = Math.max(0, Math.min(error.line, safeLineCount - 1));
    const lineText = document.lineAt(line).text;
    const column = Math.max(0, Math.min(error.column, lineText.length));

    let endColumn = column + 1;
    if (column < lineText.length && /\w/.test(lineText[column])) {
        while (endColumn < lineText.length && /\w/.test(lineText[endColumn])) {
            endColumn++;
        }
    } else if (column < lineText.length) {
        endColumn = column + 1;
    }

    return {
        range: createRange(line, column, line, endColumn),
        message: error.message,
        severity: error.severity,
        source: 'fcstm',
    };
}

export async function collectDocumentDiagnostics(
    document: TextDocumentLike
): Promise<FcstmDiagnostic[]> {
    const parseResult = await getParser().parse(document.getText());
    const diagnostics = parseResult.errors.map(error => convertParseErrorToDiagnostic(error, document));
    diagnostics.push(...await getImportWorkspaceIndex().collectImportDiagnostics(document));
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const node = snapshot.nodes[snapshot.rootFile];
    if (node?.semantic) {
        diagnostics.push(...collectSemanticAnalysisDiagnosticsFromSemantic(node.semantic, document));
        if (node.model) {
            diagnostics.push(...collectInspectModelDiagnostics(document, node.semantic, node.model, diagnostics));
        }
    }
    return diagnostics;
}
