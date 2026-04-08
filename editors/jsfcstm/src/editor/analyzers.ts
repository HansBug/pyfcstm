import {pathToFileURL} from 'node:url';

import type {FcstmAstExpression, FcstmAstImportMapping} from '../ast';
import type {FcstmSemanticDocument, FcstmSemanticImport, FcstmSemanticTransition} from '../semantics';
import {FcstmDiagnostic, TextDocumentLike} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {findIdentifierRange} from './ranges';

export const FCSTM_DIAGNOSTIC_CODES = {
    duplicateImportAlias: 'fcstm.duplicateImportAlias',
    missingImport: 'fcstm.missingImport',
    circularImport: 'fcstm.circularImport',
    unreachableState: 'fcstm.unreachableState',
    deadTransition: 'fcstm.deadTransition',
    unusedEvent: 'fcstm.unusedEvent',
    duplicateImportMapping: 'fcstm.duplicateImportMapping',
    unresolvedState: 'fcstm.unresolvedState',
    unresolvedActionRef: 'fcstm.unresolvedActionRef',
} as const;

function isFalseLiteral(expression: FcstmAstExpression): boolean {
    return expression.expressionKind === 'literal'
        && expression.literalType === 'boolean'
        && /^(false|False)$/i.test(expression.valueText);
}

function toFileUri(document: TextDocumentLike): string {
    const filePath = document.filePath || document.uri?.fsPath;
    return filePath ? pathToFileURL(filePath).toString() : 'untitled:fcstm';
}

function findImportAlias(
    semantic: FcstmSemanticDocument,
    ownerStatePath: string[],
    stateName?: string
): FcstmSemanticImport | undefined {
    if (!stateName) {
        return undefined;
    }

    for (let length = ownerStatePath.length; length >= 1; length--) {
        const prefix = ownerStatePath.slice(0, length);
        const found = semantic.imports.find(item => (
            item.alias === stateName
            && item.ownerStatePath.length === prefix.length
            && item.ownerStatePath.every((segment, index) => segment === prefix[index])
        ));
        if (found) {
            return found;
        }
    }

    return undefined;
}

function collectReachableStateIds(semantic: FcstmSemanticDocument): Set<string> {
    const reachable = new Set<string>();
    const worklist: string[] = [];

    if (semantic.machine.rootStateId) {
        reachable.add(semantic.machine.rootStateId);
        worklist.push(semantic.machine.rootStateId);
    }

    while (worklist.length > 0) {
        const stateId = worklist.pop() as string;
        const outgoing = semantic.transitions.filter(item => (
            (item.sourceKind === 'init' && item.ownerStateId === stateId)
            || item.sourceStateId === stateId
        ));

        for (const transition of outgoing) {
            if (transition.targetStateId && !reachable.has(transition.targetStateId)) {
                reachable.add(transition.targetStateId);
                worklist.push(transition.targetStateId);
            }
        }
    }

    return reachable;
}

function addImportMappingDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    for (const importItem of semantic.imports) {
        const seen = new Map<string, FcstmAstImportMapping>();
        for (const mapping of importItem.ast.mappings) {
            const key = mapping.kind === 'importDefMapping'
                ? `${mapping.kind}:${mapping.selector.text}->${mapping.targetTemplate}`
                : `${mapping.kind}:${mapping.sourceEvent.text}->${mapping.targetEvent.text}`;
            const firstMapping = seen.get(key);
            if (firstMapping) {
                diagnostics.push({
                    range: mapping.range,
                    message: `Duplicate import mapping ${JSON.stringify(mapping.text)} in alias ${JSON.stringify(importItem.alias)}.`,
                    severity: 'warning',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.duplicateImportMapping,
                    relatedInformation: [{
                        location: {
                            uri: toFileUri(document),
                            range: firstMapping.range,
                        },
                        message: `First mapping ${JSON.stringify(firstMapping.text)} is here.`,
                    }],
                });
            } else {
                seen.set(key, mapping);
            }
        }
    }
}

function addUnreachableStateDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const reachable = collectReachableStateIds(semantic);
    for (const state of semantic.states) {
        if (state.identity.id === semantic.machine.rootStateId || reachable.has(state.identity.id)) {
            continue;
        }

        diagnostics.push({
            range: findIdentifierRange(document, state.name, state.range),
            message: `State ${JSON.stringify(state.identity.qualifiedName)} is unreachable from the root machine entry path.`,
            severity: 'warning',
            source: 'fcstm',
            code: FCSTM_DIAGNOSTIC_CODES.unreachableState,
        });
    }
}

function addTransitionDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const reachable = collectReachableStateIds(semantic);

    for (const transition of semantic.transitions) {
        if (transition.sourceKind === 'state' && transition.sourceStateName && !transition.sourceStateId) {
            const imported = findImportAlias(semantic, transition.ownerStatePath, transition.sourceStateName);
            if (!imported) {
                diagnostics.push({
                    range: findIdentifierRange(document, transition.sourceStateName, transition.range),
                    message: `State ${JSON.stringify(transition.sourceStateName)} cannot be resolved in this scope.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.unresolvedState,
                });
            }
        }

        if (transition.targetKind === 'state' && transition.targetStateName && !transition.targetStateId) {
            const imported = findImportAlias(semantic, transition.ownerStatePath, transition.targetStateName);
            if (!imported) {
                diagnostics.push({
                    range: findIdentifierRange(document, transition.targetStateName, transition.range, {preferLast: true}),
                    message: `State ${JSON.stringify(transition.targetStateName)} cannot be resolved in this scope.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.unresolvedState,
                });
            }
        }

        const sourceUnreachable = Boolean(
            transition.sourceStateId
            && !reachable.has(transition.sourceStateId)
            && transition.sourceStateId !== semantic.machine.rootStateId
        );
        if (sourceUnreachable || (transition.guard && isFalseLiteral(transition.guard))) {
            const sourceState = semantic.states.find(item => item.identity.id === transition.sourceStateId);
            diagnostics.push({
                range: transition.range,
                message: sourceUnreachable
                    ? `Transition ${JSON.stringify(transition.ast.text)} is dead because its source state is unreachable.`
                    : `Transition ${JSON.stringify(transition.ast.text)} is dead because its guard is always false.`,
                severity: 'warning',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.deadTransition,
                relatedInformation: sourceState
                    ? [{
                        location: {
                            uri: toFileUri(document),
                            range: findIdentifierRange(document, sourceState.name, sourceState.range),
                        },
                        message: `The transition source state ${JSON.stringify(sourceState.identity.qualifiedName)} is defined here.`,
                    }]
                    : undefined,
            });
        }
    }
}

function addUnusedEventDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const usedEventIds = new Set(
        semantic.transitions
            .map(item => item.trigger?.eventId)
            .filter((item): item is string => Boolean(item))
    );

    for (const event of semantic.events) {
        if (!event.declared || usedEventIds.has(event.identity.id)) {
            continue;
        }

        diagnostics.push({
            range: findIdentifierRange(document, event.name, event.declarationAst?.range || event.range),
            message: `Event ${JSON.stringify(event.identity.qualifiedName)} is declared but never used by any transition.`,
            severity: 'warning',
            source: 'fcstm',
            code: FCSTM_DIAGNOSTIC_CODES.unusedEvent,
        });
    }
}

function addActionDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    for (const action of semantic.actions) {
        if (!action.ref || action.ref.resolved) {
            continue;
        }

        const refName = action.ref.rawPath.split('.').at(-1) || action.ref.rawPath;
        diagnostics.push({
            range: findIdentifierRange(document, refName, action.ref.range, {preferLast: true}),
            message: `Action reference ${JSON.stringify(action.ref.rawPath)} cannot be resolved.`,
            severity: 'error',
            source: 'fcstm',
            code: FCSTM_DIAGNOSTIC_CODES.unresolvedActionRef,
        });
    }
}

/**
 * Run static semantic analyzers that are strong enough to feed diagnostics and quick fixes.
 */
export async function collectSemanticAnalysisDiagnostics(
    document: TextDocumentLike
): Promise<FcstmDiagnostic[]> {
    const diagnostics: FcstmDiagnostic[] = [];
    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    if (!semantic) {
        return diagnostics;
    }

    addImportMappingDiagnostics(semantic, document, diagnostics);
    addUnreachableStateDiagnostics(semantic, document, diagnostics);
    addTransitionDiagnostics(semantic, document, diagnostics);
    addUnusedEventDiagnostics(semantic, document, diagnostics);
    addActionDiagnostics(semantic, document, diagnostics);
    return diagnostics;
}
