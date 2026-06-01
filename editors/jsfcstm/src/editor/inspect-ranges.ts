import type {FcstmSemanticDocument} from '../semantics';
import type {TextDocumentLike, TextRange} from '../utils/text';
import {findIdentifierRange} from './ranges';
import {
    effectSelfAssignRange,
    firstVariableDefinitionRange,
    resolveStatePath,
    spanLikeToRange,
    variableDefinitionRange,
} from './suggested-fixes';

function stringRef(refs: Record<string, unknown>, key: string): string | null {
    const value = refs[key];
    return typeof value === 'string' && value.length > 0 ? value : null;
}

function statePathRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    path: string | null,
): TextRange | null {
    if (!path || path === '[*]') return null;
    const state = resolveStatePath(semantic, path);
    return state ? findIdentifierRange(document, state.name, state.range) : null;
}

function eventRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    qualifiedName: string | null,
): TextRange | null {
    if (!qualifiedName) return null;
    const event = semantic.events.find(item => item.identity.qualifiedName === qualifiedName);
    if (!event) return null;
    return findIdentifierRange(document, event.name, event.declarationAst?.range ?? event.range);
}

export type InspectRangeFallback = 'full_document' | 'first_of_ambiguous';

export interface InspectRangeResolution {
    range: TextRange | null;
    fallback?: InspectRangeFallback;
}

function arrayFirstRange(value: unknown): TextRange | null {
    if (!Array.isArray(value)) return null;
    for (const item of value) {
        const range = spanLikeToRange(item);
        if (range) return range;
    }
    return null;
}

function effectSelfAssignGroupKey(refMap: Record<string, unknown>): string | null {
    const variableName = stringRef(refMap, 'var_name');
    const statePath = stringRef(refMap, 'state_path');
    if (!variableName || !statePath) return null;
    if (
        typeof refMap.effect_self_assign_anchor !== 'string' &&
        !Object.prototype.hasOwnProperty.call(refMap, 'transition_span')
    ) {
        return null;
    }
    return JSON.stringify([statePath, variableName]);
}

function consumeEffectSelfAssignOccurrenceIndex(
    seen: Map<string, number> | undefined,
    refMap: Record<string, unknown>,
    matched: boolean,
): void {
    if (!matched) return;
    const key = effectSelfAssignGroupKey(refMap);
    if (!key || !seen) return;
    seen.set(key, (seen.get(key) ?? 0) + 1);
}

function peekEffectSelfAssignOccurrenceIndex(
    seen: Map<string, number> | undefined,
    refMap: Record<string, unknown>,
): number | undefined {
    const key = effectSelfAssignGroupKey(refMap);
    if (!key || !seen) return undefined;
    return seen.get(key) ?? 0;
}

/**
 * Resolve inspect diagnostic refs into the best source range available in the
 * editor semantic document. Returning null lets callers fall back to a full
 * document range, which keeps anchor-less inspect diagnostics visible.
 */
export function resolveRangeFromRefsDetailed(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    refs: unknown,
    seenEffectSelfAssigns?: Map<string, number>,
): InspectRangeResolution {
    if (typeof refs !== 'object' || refs === null) return {range: null};
    const refMap = refs as Record<string, unknown>;

    const variableName = stringRef(refMap, 'var_name');
    const statePath = stringRef(refMap, 'state_path');
    const looksLikeEffectSelfAssign = variableName && statePath && (
        typeof refMap.effect_self_assign_anchor === 'string' ||
        Object.prototype.hasOwnProperty.call(refMap, 'transition_span')
    );
    if (looksLikeEffectSelfAssign) {
        const range = effectSelfAssignRange(
            document,
            semantic,
            statePath,
            variableName,
            peekEffectSelfAssignOccurrenceIndex(seenEffectSelfAssigns, refMap),
        );
        consumeEffectSelfAssignOccurrenceIndex(seenEffectSelfAssigns, refMap, Boolean(range));
        if (range) return {range};
        return {range: null};
    }

    for (const key of ['guard_span', 'transition_span', 'forced_span', 'normal_span']) {
        const range = spanLikeToRange(refMap[key]);
        if (range) return {range};
    }

    for (const key of ['state_path', 'composite_path', 'parent_path', 'from_path', 'to_path', 'deepest_path']) {
        const range = statePathRange(document, semantic, stringRef(refMap, key));
        if (range) return {range};
    }

    if (variableName) {
        const range = variableDefinitionRange(document, semantic, variableName);
        if (range) return {range};
        const firstRange = firstVariableDefinitionRange(document, semantic, variableName);
        if (firstRange) return {range: firstRange, fallback: 'first_of_ambiguous'};
    }

    const resolvedEventRange = eventRange(document, semantic, stringRef(refMap, 'event_qualified_name'));
    if (resolvedEventRange) return {range: resolvedEventRange};

    const duplicateRange = arrayFirstRange(refMap.duplicate_spans);
    return {range: duplicateRange};
}

export function resolveRangeFromRefs(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    refs: unknown,
): TextRange | null {
    return resolveRangeFromRefsDetailed(document, semantic, refs).range;
}
