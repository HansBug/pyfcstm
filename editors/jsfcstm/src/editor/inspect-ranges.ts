import type {FcstmSemanticDocument, FcstmSemanticTransition} from '../semantics';
import {createRange, type TextDocumentLike, type TextRange} from '../utils/text';
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

function dottedPath(path: readonly string[] | undefined): string | null {
    return path && path.length > 0 ? path.join('.') : null;
}

function importAliasPathMatches(
    semantic: FcstmSemanticDocument,
    path: string | null,
    stateName: string | undefined,
): boolean {
    if (!path || !stateName) return false;
    const mountedImport = semantic.lookups.importsByMountedPath[path];
    return Boolean(mountedImport && mountedImport.alias === stateName);
}

function transitionEndpointPath(
    transition: FcstmSemanticTransition,
    endpoint: 'source' | 'target',
): string | null {
    if (endpoint === 'source') {
        if (transition.sourceKind === 'init') return '[*]';
        return dottedPath(transition.sourceStatePath) ?? transition.sourceStateName ?? null;
    }
    if (transition.targetKind === 'exit') return '[*]';
    return dottedPath(transition.targetStatePath) ?? transition.targetStateName ?? null;
}

function compactText(value: string | null | undefined): string | null {
    if (value === undefined || value === null) return null;
    return value.replace(/\s+/g, '');
}

interface TransitionEndpointPair {
    fromPath: string | null;
    toPath: string | null;
}

function transitionEndpointPairs(transition: FcstmSemanticTransition): TransitionEndpointPair[] {
    if (transition.forced && transition.expandedTransitions.length > 0) {
        return transition.expandedTransitions.map(expanded => ({
            fromPath: dottedPath(expanded.sourceStatePath),
            toPath: expanded.targetKind === 'exit'
                ? '[*]'
                : dottedPath(expanded.targetStatePath),
        }));
    }
    return [{
        fromPath: transitionEndpointPath(transition, 'source'),
        toPath: transitionEndpointPath(transition, 'target'),
    }];
}

function transitionPathRefsMatch(
    semantic: FcstmSemanticDocument,
    transition: FcstmSemanticTransition,
    refs: Record<string, unknown>,
): boolean {
    const fromPath = stringRef(refs, 'from_path');
    const toPath = stringRef(refs, 'to_path');
    const statePath = stringRef(refs, 'state_path');
    if (!fromPath && !toPath && !statePath) return true;

    return transitionEndpointPairs(transition).some(pair => (
        (!fromPath || pair.fromPath === fromPath || importAliasPathMatches(semantic, fromPath, transition.sourceStateName)) &&
        (!toPath || pair.toPath === toPath || importAliasPathMatches(semantic, toPath, transition.targetStateName)) &&
        (!statePath || pair.fromPath === statePath || importAliasPathMatches(semantic, statePath, transition.sourceStateName))
    ));
}

function guardExpressionRange(transition: FcstmSemanticTransition): TextRange | null {
    return transition.guard?.range ?? null;
}

function effectBlockRange(
    document: TextDocumentLike,
    transition: FcstmSemanticTransition,
): TextRange | null {
    const effectRange = transition.ast.effect?.range;
    if (!effectRange) return null;
    for (let lineIndex = transition.range.start.line; lineIndex <= effectRange.start.line; lineIndex += 1) {
        const line = document.lineAt(lineIndex).text;
        const startCharacter = lineIndex === transition.range.start.line ? transition.range.start.character : 0;
        const endCharacter = lineIndex === effectRange.start.line ? effectRange.start.character : line.length;
        const prefix = line.slice(startCharacter, endCharacter);
        const keywordOffset = prefix.lastIndexOf('effect');
        if (keywordOffset >= 0) {
            const keywordCharacter = startCharacter + keywordOffset;
            return createRange(
                lineIndex,
                keywordCharacter,
                transition.range.end.line,
                transition.range.end.character,
            );
        }
    }
    return effectRange;
}

function transitionHasEvent(transition: FcstmSemanticTransition, expectedEvent: string | null): boolean {
    if (expectedEvent === null) return true;
    if (!transition.trigger) return false;
    return transition.trigger.rawText === expectedEvent ||
        transition.trigger.qualifiedName === expectedEvent ||
        transition.trigger.normalizedPath.join('.') === expectedEvent;
}

function hasNumericTransitionIndex(refs: Record<string, unknown>): boolean {
    return typeof refs.transition_index === 'number' && Number.isInteger(refs.transition_index);
}

function transitionMatchesRefs(
    semantic: FcstmSemanticDocument,
    transition: FcstmSemanticTransition,
    refs: Record<string, unknown>,
): boolean {
    if (!transitionPathRefsMatch(semantic, transition, refs)) return false;

    const guardText = compactText(stringRef(refs, 'guard_text'));
    if (guardText !== null && !hasNumericTransitionIndex(refs) && compactText(transition.guard?.text) !== guardText) {
        return false;
    }

    const effectText = compactText(stringRef(refs, 'effect_text'));
    if (effectText !== null && compactText(transition.effectText) !== effectText) return false;

    const eventName = stringRef(refs, 'event_name') ?? stringRef(refs, 'event_chain') ?? stringRef(refs, 'event');
    if (!transitionHasEvent(transition, eventName)) return false;

    return true;
}


interface TransitionIndexRef {
    index: number;
    fromPath: string | null;
    toPath: string | null;
}

function transitionIndexRefMatchesRefs(
    semantic: FcstmSemanticDocument,
    transition: FcstmSemanticTransition,
    ref: TransitionIndexRef,
    index: number,
    refs: Record<string, unknown>,
): boolean {
    if (ref.index !== index) return false;
    const fromPath = stringRef(refs, 'from_path') ?? stringRef(refs, 'state_path');
    const toPath = stringRef(refs, 'to_path');
    return (!fromPath || ref.fromPath === fromPath || importAliasPathMatches(semantic, fromPath, transition.sourceStateName)) &&
        (!toPath || ref.toPath === toPath || importAliasPathMatches(semantic, toPath, transition.targetStateName));
}

function transitionRangeMatchesIndex(
    semantic: FcstmSemanticDocument,
    transition: FcstmSemanticTransition,
    index: number,
    refs: Record<string, unknown>,
): boolean {
    if (Array.isArray(transition.ast.transitionIndexRefs)) {
        return transition.ast.transitionIndexRefs
            .some(ref => transitionIndexRefMatchesRefs(semantic, transition, ref, index, refs));
    }

    const rawIndex = transition.ast.transitionIndex;
    return typeof rawIndex === 'number' && Number.isInteger(rawIndex) && rawIndex === index;
}

function transitionRangeResolution(
    semantic: FcstmSemanticDocument,
    refs: Record<string, unknown>,
): InspectRangeResolution {
    const transitions = semantic.transitions.filter(transition => transitionMatchesRefs(semantic, transition, refs));
    if (transitions.length === 0) return {range: null, fallback: 'transition_not_found'};

    const requestedIndex = refs.transition_index;
    if (typeof requestedIndex === 'number' && Number.isInteger(requestedIndex)) {
        const selected = transitions.find(transition => transitionRangeMatchesIndex(semantic, transition, requestedIndex, refs));
        return selected
            ? {range: selected.range, transition: selected}
            : {range: null, fallback: 'transition_not_found'};
    }

    const selected = transitions[0];
    const invalidIndexProvided = requestedIndex !== undefined;
    return {
        range: selected.range,
        fallback: transitions.length > 1 || invalidIndexProvided ? 'transition_ambiguous' : undefined,
        transition: selected,
    };
}

function guardRangeResolution(
    semantic: FcstmSemanticDocument,
    refs: Record<string, unknown>,
): InspectRangeResolution {
    const transitionResolution = transitionRangeResolution(semantic, refs);
    if (!transitionResolution.range) return transitionResolution;
    const guardRange = transitionResolution.transition
        ? guardExpressionRange(transitionResolution.transition)
        : null;
    return {
        range: guardRange ?? transitionResolution.range,
        fallback: transitionResolution.fallback,
    };
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

export type InspectRangeFallback =
    | 'full_document'
    | 'first_of_ambiguous'
    | 'transition_ambiguous'
    | 'transition_not_found'
    | 'effect_fallback'
    | 'transition_fallback';

export interface InspectRangeResolution {
    range: TextRange | null;
    fallback?: InspectRangeFallback;
    transition?: FcstmSemanticTransition;
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
    const transitionIndex = refMap.transition_index;
    return typeof transitionIndex === 'number' && Number.isInteger(transitionIndex)
        ? JSON.stringify([statePath, variableName, transitionIndex])
        : JSON.stringify([statePath, variableName]);
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
        const transitionResolution = transitionRangeResolution(semantic, refMap);
        const occurrenceIndex = peekEffectSelfAssignOccurrenceIndex(seenEffectSelfAssigns, refMap);
        const range = transitionResolution.transition
            ? effectSelfAssignRange(
                document,
                semantic,
                statePath,
                variableName,
                occurrenceIndex,
                transitionResolution.transition,
            )
            : effectSelfAssignRange(
                document,
                semantic,
                statePath,
                variableName,
                occurrenceIndex,
            );
        consumeEffectSelfAssignOccurrenceIndex(seenEffectSelfAssigns, refMap, Boolean(range));
        if (range) {
            return {
                range,
                fallback: transitionResolution.fallback,
            };
        }
        if (transitionResolution.range) {
            const effectRange = transitionResolution.transition
                ? effectBlockRange(document, transitionResolution.transition)
                : null;
            return {
                range: effectRange ?? transitionResolution.range,
                fallback: transitionResolution.fallback ?? (effectRange ? 'effect_fallback' : 'transition_fallback'),
            };
        }
        return {range: null};
    }

    for (const key of ['guard_span', 'transition_span', 'forced_declaration_span', 'forced_span']) {
        const range = spanLikeToRange(refMap[key]);
        if (range) return {range};
    }

    const duplicateRange = arrayFirstRange(refMap.duplicate_spans);
    if (duplicateRange) return {range: duplicateRange};

    if (refMap.transition_span === null || refMap.guard_span === null || refMap.duplicate_spans !== undefined) {
        if (refMap.folded_value === true || refMap.folded_value === false || stringRef(refMap, 'guard_text')) {
            const guardResolution = guardRangeResolution(semantic, refMap);
            if (guardResolution.range) return guardResolution;
        }
        const transitionResolution = transitionRangeResolution(semantic, refMap);
        if (transitionResolution.range) return transitionResolution;
        if (transitionResolution.fallback) return transitionResolution;
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

    return {range: null};
}

export function resolveRangeFromRefs(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    refs: unknown,
): TextRange | null {
    return resolveRangeFromRefsDetailed(document, semantic, refs).range;
}
