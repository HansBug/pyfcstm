import type {FcstmSemanticDocument} from '../semantics';
import type {TextDocumentLike, TextRange} from '../utils/text';
import {findIdentifierRange} from './ranges';
import {resolveStatePath, spanLikeToRange, variableDefinitionRange} from './suggested-fixes';

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

function arrayFirstRange(value: unknown): TextRange | null {
    if (!Array.isArray(value)) return null;
    for (const item of value) {
        const range = spanLikeToRange(item);
        if (range) return range;
    }
    return null;
}

/**
 * Resolve inspect diagnostic refs into the best source range available in the
 * editor semantic document. Returning null lets callers fall back to a full
 * document range, which keeps anchor-less inspect diagnostics visible.
 */
export function resolveRangeFromRefs(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    refs: unknown,
): TextRange | null {
    if (typeof refs !== 'object' || refs === null) return null;
    const refMap = refs as Record<string, unknown>;

    for (const key of ['state_path', 'composite_path', 'parent_path']) {
        const range = statePathRange(document, semantic, stringRef(refMap, key));
        if (range) return range;
    }

    const variableName = stringRef(refMap, 'var_name');
    if (variableName) {
        const range = variableDefinitionRange(document, semantic, variableName);
        if (range) return range;
    }

    const resolvedEventRange = eventRange(document, semantic, stringRef(refMap, 'event_qualified_name'));
    if (resolvedEventRange) return resolvedEventRange;

    for (const key of ['transition_span', 'guard_span']) {
        const range = spanLikeToRange(refMap[key]);
        if (range) return range;
    }

    return arrayFirstRange(refMap.duplicate_spans);
}
