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
import {resolveRangeFromRefsDetailed, spanToRange, statePathIsLocalToDocument} from './inspect-ranges';
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

function isSuppressedFromInspectSurface(item: ModelDiagnosticJson): boolean {
    if (!SUPPRESSED_FROM_INSPECT_SURFACE.has(item.code)) return false;
    // The semantic model does not carry the runtime's canonical forced-origin
    // text, so generated forced edges remain inspect-backed.
    if (item.code === 'W_UNREACHABLE_TRANSITION' && typeof item.refs.forced_origin === 'string') {
        return false;
    }
    return true;
}

function inspectItemSourcePath(item: ModelDiagnosticJson): string | null {
    const refs = item.refs;
    for (const key of ['source_state_path', 'selection_owner_path', 'from_path']) {
        const value = refs[key];
        if (typeof value === 'string' && value !== '[*]') return value;
    }
    return null;
}

function inspectItemAuthoredByDocument(
    document: TextDocumentLike,
    item: ModelDiagnosticJson,
): boolean {
    const authoredPath = item.refs.source_path;
    const documentPath = document.filePath || document.uri?.fsPath;
    return typeof authoredPath === 'string'
        && typeof documentPath === 'string'
        && authoredPath === documentPath;
}

function localizeImportedStatePath(
    model: Parameters<typeof inspectModel>[0],
    statePath: string | null,
    sourceFile: string,
    authoredRootName: string,
): string | null {
    if (!statePath || statePath === '[*]') return statePath;
    const segments = statePath.split('.');
    for (let length = segments.length; length >= 1; length -= 1) {
        const candidate = segments.slice(0, length).join('.');
        const state = model.lookups.statesByPath[candidate];
        const importedFromFile = state?.importedFromFile ?? state?.imported_from_file;
        if (importedFromFile !== sourceFile) continue;
        return [authoredRootName, ...segments.slice(length)].join('.');
    }
    return statePath;
}

function localizeImportedDiagnostic(
    item: ModelDiagnosticJson,
    model: Parameters<typeof inspectModel>[0],
    sourceFile: string,
    authoredRootName: string,
): ModelDiagnosticJson {
    const refs = {...item.refs};
    const replacements = new Map<string, string>();
    for (const key of ['from_path', 'to_path', 'source_state_path', 'selection_owner_path']) {
        const value = refs[key];
        if (typeof value !== 'string' || value === '[*]') continue;
        const localized = localizeImportedStatePath(
            model,
            value,
            sourceFile,
            authoredRootName,
        );
        if (localized === null || localized === value) continue;
        refs[key] = localized;
        replacements.set(value, localized);
    }
    let message = item.message;
    for (const [source, target] of [...replacements.entries()].sort((left, right) => right[0].length - left[0].length)) {
        message = message.split(source).join(target);
    }
    const comboOriginIds = refs.combo_origin_ids;
    if (Array.isArray(comboOriginIds)) {
        refs.combo_origin_ids = comboOriginIds.map(originId => {
            if (typeof originId !== 'string') return originId;
            const separator = originId.indexOf(':');
            if (separator <= 0) return originId;
            const ownerPath = originId.slice(0, separator);
            const localizedOwner = localizeImportedStatePath(
                model,
                ownerPath,
                sourceFile,
                authoredRootName,
            );
            return localizedOwner && localizedOwner !== ownerPath
                ? `${localizedOwner}${originId.slice(separator)}`
                : originId;
        });
    }
    return {...item, message, refs};
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
        if (isSuppressedFromInspectSurface(item)) continue;
        if (shouldSuppressInspectDiagnostic(semantic, item)) continue;
        const diagnostic: FcstmDiagnostic = {
            range: fullRange,
            message: item.message,
            severity: item.severity,
            source: 'fcstm',
            code: item.code,
            data: item.refs,
        };
        // Hydrated workspace models retain source spans from imported files.
        // A span without its owning URI must not be applied to the host file;
        // the refs/range resolver can still anchor the import boundary or fall
        // back to the full document while the imported document owns its span.
        const sourcePath = inspectItemSourcePath(item);
        const primarySpanRange = inspectItemAuthoredByDocument(document, item)
            || sourcePath === null || statePathIsLocalToDocument(
                document,
                semantic,
                sourcePath,
            )
            ? spanToRange(item.span)
            : null;
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

export async function collectDocumentDiagnosticsByUri(
    document: TextDocumentLike,
    rootUri = documentUri(document),
): Promise<Map<string, FcstmDiagnostic[]>> {
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

    const publications = new Map<string, FcstmDiagnostic[]>();
    publications.set(
        rootUri,
        diagnostics.filter(diagnostic => !shouldSuppressParseRecoveryDiagnostic(diagnostic, parseDiagnostics)),
    );

    // A hydrated root model carries imported paths in the host namespace, so
    // topology must be checked against that assembled model. Use the model's
    // imported-root provenance only to partition the resulting diagnostics by
    // authored URI; running a child model as a new root would incorrectly make
    // a subtree mounted under an unreachable host state appear reachable.
    if (node?.model) {
        const assembledModel = node.model;
        const assembledDiagnostics = inspectModel(assembledModel).diagnostics;
        for (const filePath of snapshot.order) {
            const authoredNode = snapshot.nodes[filePath];
            if (!authoredNode?.semantic) continue;
            const authoredRootName = authoredNode.semantic.summary.rootStateName
                || authoredNode.ast?.rootState?.name;
            if (!authoredRootName) continue;
            const items = assembledDiagnostics.filter(item => {
                if (item.code !== 'W_UNREACHABLE_TRANSITION') return false;
                return item.refs.source_path === filePath;
            }).map(item => localizeImportedDiagnostic(
                item,
                assembledModel,
                filePath,
                authoredRootName,
            ));
            if (items.length === 0) continue;
            const isRootFile = filePath === snapshot.rootFile || filePath === document.filePath;
            const authoredDiagnostics = collectInspectDiagnosticsFromItems(
                authoredNode.document,
                authoredNode.semantic,
                items,
                isRootFile ? diagnostics : [],
            );
            if (authoredDiagnostics.length === 0) continue;
            const authoredUri = isRootFile
                ? rootUri
                : documentUri(authoredNode.document);
            if (isRootFile) {
                publications.set(authoredUri, [
                    ...(publications.get(authoredUri) || []),
                    ...authoredDiagnostics,
                ]);
            } else {
                publications.set(authoredUri, authoredDiagnostics);
            }
        }
    }
    return publications;
}

export async function collectDocumentDiagnostics(
    document: TextDocumentLike
): Promise<FcstmDiagnostic[]> {
    const publications = await collectDocumentDiagnosticsByUri(document);
    return publications.get(documentUri(document)) || [];
}
