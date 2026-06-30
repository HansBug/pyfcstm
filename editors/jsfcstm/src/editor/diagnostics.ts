import {pathToFileURL} from 'node:url';

import {getParser, ParseError} from '../dsl/parser';
import {inspectModel, type ModelDiagnosticJson} from '../diagnostics';
import {buildStateMachineModel} from '../model';
import type {FcstmSemanticDocument} from '../semantics';
import {collectSemanticAnalysisDiagnosticsFromSemantic} from './analyzers';
import {
    createRange,
    FcstmDiagnostic,
    rangeIsEmptyOrInvalid,
    TextDocumentLike,
    TextRange,
} from '../utils/text';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {getWorkspaceGraph} from '../workspace';
import {resolveRangeFromRefsDetailed, spanToRange} from './inspect-ranges';
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
        if (key === 'suggested_fix' || key === '__rangeFallback') continue;
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

function isDslIdentifier(value: string): boolean {
    return /^[A-Za-z_][A-Za-z0-9_]*$/.test(value);
}

function documentUri(document: TextDocumentLike): string {
    const filePath = document.filePath || document.uri?.fsPath;
    return filePath ? pathToFileURL(filePath).toString() : 'untitled:fcstm';
}

function actionShadowRelatedInformation(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    refs: Record<string, unknown>,
): FcstmDiagnostic['relatedInformation'] {
    const range = resolveRangeFromRefsDetailed(document, semantic, {
        function_name: refs.function_name,
        defined_in: refs.outer_state_path,
    }).range;
    if (!range) return undefined;
    return [{
        location: {
            uri: documentUri(document),
            range,
        },
        message: 'Ancestor named action shadowed by this declaration.',
    }];
}

function shadowedEventRelatedInformation(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    refs: Record<string, unknown>,
): FcstmDiagnostic['relatedInformation'] {
    const range = resolveRangeFromRefsDetailed(document, semantic, {
        event_qualified_name: refs.chain_path,
    }).range;
    if (!range) return undefined;
    return [{
        location: {
            uri: documentUri(document),
            range,
        },
        message: 'Broader event shadowed by this local event.',
    }];
}


function relatedInformationFromSpan(
    document: TextDocumentLike,
    span: unknown,
    message: string,
): NonNullable<FcstmDiagnostic['relatedInformation']>[number] | null {
    const range = spanToRange(span);
    if (!range) return null;
    return {
        location: {
            uri: documentUri(document),
            range,
        },
        message,
    };
}

function comboRelatedInformation(
    document: TextDocumentLike,
    item: ModelDiagnosticJson,
): FcstmDiagnostic['relatedInformation'] {
    const related: NonNullable<FcstmDiagnostic['relatedInformation']> = [];
    if (item.code === 'W_COMBO_DUPLICATE_EVENT') {
        const first = relatedInformationFromSpan(
            document,
            item.refs.first_term_span,
            'First occurrence of the repeated combo event term.',
        );
        if (first) related.push(first);
    } else if (
        item.code === 'W_COMBO_GUARD_PREFIX_IMPLIED' ||
        item.code === 'W_COMBO_GUARD_PREFIX_CONTRADICTS'
    ) {
        const prior = relatedInformationFromSpan(
            document,
            item.refs.prior_term_span,
            'Prior combo guard term used for this prefix relation.',
        );
        if (prior) related.push(prior);
    }
    const origin = relatedInformationFromSpan(
        document,
        item.refs.transition_span,
        'Original combo transition.',
    );
    if (origin) related.push(origin);
    return related.length > 0 ? related : undefined;
}

function relatedInformationFromRefs(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    item: ModelDiagnosticJson,
): FcstmDiagnostic['relatedInformation'] {
    if (item.code.startsWith('W_COMBO_')) {
        return comboRelatedInformation(document, item);
    }
    if (item.code === 'W_FORCED_OVERRIDES_NORMAL') {
        const normalRange = spanToRange(item.refs.normal_transition_span);
        if (!normalRange) return undefined;
        return [{
            location: {
                uri: documentUri(document),
                range: normalRange,
            },
            message: 'Normal transition duplicated by this forced transition.',
        }];
    }
    if (item.code === 'W_NAMED_ACTION_SHADOWS_ANCESTOR') {
        return actionShadowRelatedInformation(document, semantic, item.refs);
    }
    if (item.code === 'W_SHADOWED_EVENT') {
        return shadowedEventRelatedInformation(document, semantic, item.refs);
    }
    return undefined;
}

export interface CollectInspectModelDiagnosticsOptions {
    rangeMode?: 'problem' | 'fix-edit';
}

function shouldSuppressInspectDiagnostic(
    semantic: FcstmSemanticDocument,
    item: ModelDiagnosticJson,
): boolean {
    if (item.code !== 'W_DEADLOCK_LEAF') return false;
    const statePath = typeof item.refs.state_path === 'string' ? item.refs.state_path : null;
    if (!statePath) return false;
    const semanticState = semantic.lookups.statesByPath[statePath];
    return Boolean(semanticState && semanticState.ast.imports.length > 0);
}

export function collectInspectDiagnosticsFromItems(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    items: readonly ModelDiagnosticJson[],
    existingDiagnostics: FcstmDiagnostic[] = [],
    options: CollectInspectModelDiagnosticsOptions = {},
): FcstmDiagnostic[] {
    const existingCounts = new Map<string, number>();
    for (const diagnostic of existingDiagnostics) {
        if (!diagnostic.code) continue;
        const key = diagnosticKey(diagnostic);
        existingCounts.set(key, (existingCounts.get(key) ?? 0) + 1);
    }
    const fullRange = fullDocumentRange(document);
    const diagnostics: FcstmDiagnostic[] = [];
    const seenEffectSelfAssigns = new Map<string, number>();

    for (const item of items) {
        if (SUPPRESSED_FROM_INSPECT_SURFACE.has(item.code)) continue;
        if (shouldSuppressInspectDiagnostic(semantic, item)) continue;
        const diagnostic: FcstmDiagnostic = {
            range: fullRange,
            message: item.message,
            severity: item.severity,
            source: 'fcstm',
            code: item.code,
            data: item.refs,
        };
        const primarySpanRange = spanToRange(item.span);
        const refResolution = resolveRangeFromRefsDetailed(document, semantic, item.refs, seenEffectSelfAssigns);
        const problemRange = primarySpanRange
            ?? refResolution.range
            ?? suggestedFixIssueRange(document, semantic, diagnostic);
        if (options.rangeMode === 'fix-edit') {
            const suggestedRange = suggestedFixDiagnosticRange(document, semantic, diagnostic);
            diagnostic.range = rangeEquals(suggestedRange, fullRange)
                ? problemRange
                : suggestedRange;
        } else {
            diagnostic.range = problemRange;
            if (rangeEquals(diagnostic.range, fullRange)) {
                diagnostic.data = {...(diagnostic.data ?? {}), __rangeFallback: 'full_document'};
            }
        }
        if (refResolution.fallback) {
            diagnostic.data = {...(diagnostic.data ?? {}), __rangeFallback: refResolution.fallback};
        }
        diagnostic.relatedInformation = relatedInformationFromRefs(document, semantic, item);
        if (consumeDiagnosticCount(existingCounts, diagnosticKey(diagnostic))) continue;
        diagnostics.push(diagnostic);
    }

    return diagnostics;
}

export function collectInspectModelDiagnostics(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    model: Parameters<typeof inspectModel>[0],
    existingDiagnostics: FcstmDiagnostic[] = [],
    options: CollectInspectModelDiagnosticsOptions = {},
): FcstmDiagnostic[] {
    return collectInspectDiagnosticsFromItems(
        document,
        semantic,
        inspectModel(model).diagnostics,
        existingDiagnostics,
        options,
    );
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

/**
 * Return whether a semantic diagnostic should be hidden after parser recovery.
 *
 * The collector only calls this when parse diagnostics already exist, keeping
 * normal semantic diagnostics untouched for syntactically valid documents.
 */
export function shouldSuppressParseRecoveryDiagnostic(
    diagnostic: FcstmDiagnostic,
    parseDiagnostics: readonly FcstmDiagnostic[],
): boolean {
    if (!diagnostic.code || parseDiagnostics.length === 0) return false;
    if (diagnostic.code === 'E_UNDEFINED_VAR') {
        const varName = typeof diagnostic.data?.var_name === 'string' ? diagnostic.data.var_name : '';
        if (varName.length === 0 || !isDslIdentifier(varName)) return true;
    }
    if (diagnostic.code === 'E_TYPE_MISMATCH') {
        const exprText = typeof diagnostic.data?.expr_text === 'string' ? diagnostic.data.expr_text : '';
        if (exprText.length === 0) return true;
    }
    if (diagnostic.code === 'W_UNREFERENCED_VAR') {
        const varName = typeof diagnostic.data?.var_name === 'string' ? diagnostic.data.var_name : '';
        if (varName.length === 0 || !isDslIdentifier(varName)) return true;
    }
    return rangeIsEmptyOrInvalid(diagnostic.range);
}

export async function collectDocumentDiagnostics(
    document: TextDocumentLike
): Promise<FcstmDiagnostic[]> {
    const parseResult = await getParser().parse(document.getText());
    const parseDiagnostics = parseResult.errors.map(error => convertParseErrorToDiagnostic(error, document));
    const diagnostics = [...parseDiagnostics];
    diagnostics.push(...await getImportWorkspaceIndex().collectImportDiagnostics(document));
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const node = snapshot.nodes[snapshot.rootFile];
    if (node?.semantic) {
        diagnostics.push(...collectSemanticAnalysisDiagnosticsFromSemantic(node.semantic, document));
        const localModel = buildStateMachineModel(node.semantic);
        if (localModel) {
            diagnostics.push(...collectInspectModelDiagnostics(document, node.semantic, localModel, diagnostics));
        }
    }
    return diagnostics.filter(diagnostic => !shouldSuppressParseRecoveryDiagnostic(diagnostic, parseDiagnostics));
}
