import {pathToFileURL} from 'node:url';

import type {
    FcstmAstAction,
    FcstmAstAssignmentStatement,
    FcstmAstExpression,
    FcstmAstIfStatement,
    FcstmAstImportMapping,
    FcstmAstOperationBlock,
    FcstmAstOperationStatement,
    FcstmAstTransition,
    FcstmAstForcedTransition,
} from '../ast';
import type {FcstmSemanticDocument, FcstmSemanticImport, FcstmSemanticTransition} from '../semantics';
import {FcstmDiagnostic, TextDocumentLike} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {findIdentifierRange} from './ranges';

/**
 * Diagnostic code constants — single source of truth for jsfcstm
 * analyzer emitters. The values match the codes registered in
 * ``pyfcstm/diagnostics/codes.yaml`` so that downstream consumers
 * (LLM agent loops, evaluation tooling, the bundled VSCode extension)
 * see byte-identical ``code`` strings regardless of which end produced
 * the diagnostic. PR-A unifies the historical ``fcstm.*`` namespace
 * into the shared ``E_*`` / ``W_*`` / ``I_*`` set.
 */
export const FCSTM_DIAGNOSTIC_CODES = {
    // -------- Layer 1 errors (E_*) --------
    undefinedVar: 'E_UNDEFINED_VAR',
    duplicateVar: 'E_DUPLICATE_VAR',
    missingState: 'E_MISSING_STATE',
    danglingTransition: 'E_DANGLING_TRANSITION',
    namedFunctionRefNotFound: 'E_NAMED_FUNCTION_REF_NOT_FOUND',
    duplicateState: 'E_DUPLICATE_STATE',
    duplicateFunctionName: 'E_DUPLICATE_FUNCTION_NAME',
    duringAspectInvalid: 'E_DURING_ASPECT_INVALID',
    pseudoNotLeaf: 'E_PSEUDO_NOT_LEAF',
    initialTransitionInvalid: 'E_INITIAL_TRANSITION_INVALID',
    // -------- Import errors (E_IMPORT_*) --------
    importAliasConflict: 'E_IMPORT_ALIAS_CONFLICT',
    importNotFound: 'E_IMPORT_NOT_FOUND',
    importCircular: 'E_IMPORT_CIRCULAR',
    importDuplicateMapping: 'E_IMPORT_DUPLICATE_MAPPING',
    importMappingInvalid: 'E_IMPORT_MAPPING_INVALID',
    // -------- Layer 2 warnings (W_*) - emit logic kept in place,
    // codes.yaml schema placeholders introduced in PR-A --------
    unreachableState: 'W_UNREACHABLE_STATE',
    guardConstFalse: 'W_GUARD_CONST_FALSE',
    unusedEvent: 'W_UNUSED_EVENT',
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

    // Index forced-transition expansions by their concrete per-descendant source.
    // A forced transition such as `!* -> X :: E` is expanded in the semantics layer
    // into one synthetic edge per affected descendant: any state in that index
    // contributes an outgoing edge to the expanded target (issue #99).
    const forcedExpandedBySource = new Map<string, Set<string>>();
    for (const transition of semantic.transitions) {
        if (!transition.forced) {
            continue;
        }
        for (const expanded of transition.expandedTransitions) {
            if (!expanded.targetStateId) {
                continue;
            }
            let targets = forcedExpandedBySource.get(expanded.sourceStateId);
            if (!targets) {
                targets = new Set<string>();
                forcedExpandedBySource.set(expanded.sourceStateId, targets);
            }
            targets.add(expanded.targetStateId);
        }
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

        const forcedTargets = forcedExpandedBySource.get(stateId);
        if (forcedTargets) {
            for (const targetId of forcedTargets) {
                if (!reachable.has(targetId)) {
                    reachable.add(targetId);
                    worklist.push(targetId);
                }
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
                    code: FCSTM_DIAGNOSTIC_CODES.importDuplicateMapping,
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
        // pyfcstm Layer 1 distinction: the source side of a transition
        // failing to resolve emits E_MISSING_STATE (a "state reference"
        // not found in scope), while the target side emits
        // E_DANGLING_TRANSITION (the transition has a known source but
        // points at a non-existent target). When both endpoints are
        // explicitly known and missing, the source-side firing wins —
        // matches pyfcstm/model/model.py emit order.
        if (transition.sourceKind === 'state' && transition.sourceStateName && !transition.sourceStateId) {
            const imported = findImportAlias(semantic, transition.ownerStatePath, transition.sourceStateName);
            if (!imported) {
                diagnostics.push({
                    range: findIdentifierRange(document, transition.sourceStateName, transition.range),
                    message: `State ${JSON.stringify(transition.sourceStateName)} cannot be resolved in this scope.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.missingState,
                    data: {
                        state_path: transition.sourceStateName,
                        referenced_from: 'transition_source',
                        reason: 'state_not_found',
                    },
                });
            }
        }

        if (transition.targetKind === 'state' && transition.targetStateName && !transition.targetStateId) {
            const imported = findImportAlias(semantic, transition.ownerStatePath, transition.targetStateName);
            if (!imported) {
                diagnostics.push({
                    range: findIdentifierRange(document, transition.targetStateName, transition.range, {preferLast: true}),
                    message: `Transition target state ${JSON.stringify(transition.targetStateName)} cannot be resolved in this scope.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.danglingTransition,
                    data: {
                        src: transition.sourceStateName ?? null,
                        tgt: transition.targetStateName,
                        reason: 'tgt_not_found',
                    },
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
                code: FCSTM_DIAGNOSTIC_CODES.guardConstFalse,
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
            code: FCSTM_DIAGNOSTIC_CODES.namedFunctionRefNotFound,
        });
    }
}

function collectIdentifierRefs(
    expression: FcstmAstExpression | null | undefined,
    out: Array<{name: string; range: import('../utils/text').TextRange}>
): void {
    if (!expression) {
        return;
    }
    switch (expression.expressionKind) {
        case 'identifier':
            out.push({name: expression.name, range: expression.range});
            return;
        case 'unary':
            collectIdentifierRefs(expression.operand, out);
            return;
        case 'binary':
            collectIdentifierRefs(expression.left, out);
            collectIdentifierRefs(expression.right, out);
            return;
        case 'function':
            collectIdentifierRefs(expression.argument, out);
            return;
        case 'conditional':
            collectIdentifierRefs(expression.condition, out);
            collectIdentifierRefs(expression.whenTrue, out);
            collectIdentifierRefs(expression.whenFalse, out);
            return;
        case 'parenthesized':
            collectIdentifierRefs(expression.expression, out);
            return;
        default:
            return;
    }
}

function pushIdentifierDiagnostic(
    diagnostics: FcstmDiagnostic[],
    identifier: {name: string; range: import('../utils/text').TextRange},
    message: string,
    code: string,
    severity: 'error' | 'warning' | 'info' = 'error',
    data?: Record<string, unknown>
): void {
    diagnostics.push({
        range: identifier.range,
        message,
        severity,
        source: 'fcstm',
        code,
        ...(data ? {data} : {}),
    });
}

/**
 * Walk a block of operational statements while tracking which names are already
 * assigned inside the block. Names that are not in ``globals`` become
 * block-local temporary variables after their first assignment, matching the
 * pyfcstm runtime rule.
 */
function analyzeOperationStatements(
    statements: FcstmAstOperationStatement[] | undefined,
    globals: Set<string>,
    assignedBefore: Set<string>,
    diagnostics: FcstmDiagnostic[]
): Set<string> {
    const assigned = new Set(assignedBefore);
    if (!statements) {
        return assigned;
    }

    for (const statement of statements) {
        if (statement.kind === 'assignmentStatement') {
            const assignment = statement as FcstmAstAssignmentStatement;
            const identifiers: Array<{name: string; range: import('../utils/text').TextRange}> = [];
            collectIdentifierRefs(assignment.expression, identifiers);
            for (const identifier of identifiers) {
                if (globals.has(identifier.name) || assigned.has(identifier.name)) {
                    continue;
                }
                // pyfcstm Layer 2: read-before-assign in a block-local
                // temporary collapses into E_UNDEFINED_VAR with
                // ``is_temporary: true`` so the LLM and the VSCode
                // surface both see a single code family.
                pushIdentifierDiagnostic(
                    diagnostics,
                    identifier,
                    `Variable ${JSON.stringify(identifier.name)} is read before it is assigned in this block.`,
                    FCSTM_DIAGNOSTIC_CODES.undefinedVar,
                    'error',
                    {is_temporary: true, referenced_in: 'operation_block'}
                );
            }
            if (assignment.targetName) {
                assigned.add(assignment.targetName);
            }
        } else if (statement.kind === 'ifStatement') {
            const ifStatement = statement as FcstmAstIfStatement;
            const branchAssigned: Set<string>[] = [];
            for (const branch of ifStatement.branches) {
                if (branch.condition) {
                    const identifiers: Array<{name: string; range: import('../utils/text').TextRange}> = [];
                    collectIdentifierRefs(branch.condition, identifiers);
                    for (const identifier of identifiers) {
                        if (globals.has(identifier.name) || assigned.has(identifier.name)) {
                            continue;
                        }
                        pushIdentifierDiagnostic(
                            diagnostics,
                            identifier,
                            `Variable ${JSON.stringify(identifier.name)} is read before it is assigned in this block.`,
                            FCSTM_DIAGNOSTIC_CODES.undefinedVar,
                            'error',
                            {is_temporary: true, referenced_in: 'operation_block'}
                        );
                    }
                }
                const branchResult = analyzeOperationStatements(
                    branch.statements,
                    globals,
                    assigned,
                    diagnostics
                );
                branchAssigned.push(branchResult);
            }
            // Only names assigned on EVERY branch (including else) survive after the if.
            const hasElse = ifStatement.elseBlock !== undefined
                || ifStatement.branches.some(branch => branch.condition === null);
            if (hasElse && branchAssigned.length > 0) {
                const firstBranch = branchAssigned[0];
                for (const name of firstBranch) {
                    if (assigned.has(name)) {
                        continue;
                    }
                    if (branchAssigned.every(set => set.has(name))) {
                        assigned.add(name);
                    }
                }
            }
        }
    }

    return assigned;
}

function analyzeOperationBlock(
    block: FcstmAstOperationBlock | undefined,
    globals: Set<string>,
    diagnostics: FcstmDiagnostic[]
): void {
    if (!block) {
        return;
    }
    analyzeOperationStatements(block.statements, globals, new Set(), diagnostics);
}

function collectTopLevelGlobals(semantic: FcstmSemanticDocument): Set<string> {
    return new Set(semantic.variables.map(variable => variable.name));
}

function addVariableDefinitionDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const seen = new Map<string, typeof semantic.variables[number]>();
    for (const variable of semantic.variables) {
        const firstDefinition = seen.get(variable.name);
        if (!firstDefinition) {
            seen.set(variable.name, variable);
            continue;
        }
        diagnostics.push({
            range: findIdentifierRange(document, variable.name, variable.range),
            message: `Variable ${JSON.stringify(variable.name)} is already defined.`,
            severity: 'error',
            source: 'fcstm',
            code: FCSTM_DIAGNOSTIC_CODES.duplicateVar,
            relatedInformation: [{
                location: {
                    uri: toFileUri(document),
                    range: findIdentifierRange(document, firstDefinition.name, firstDefinition.range),
                },
                message: `First definition of ${JSON.stringify(variable.name)} is here.`,
            }],
        });
    }
}

function addGuardDiagnostics(
    transitions: FcstmSemanticTransition[],
    globals: Set<string>,
    diagnostics: FcstmDiagnostic[]
): void {
    for (const transition of transitions) {
        if (!transition.guard) {
            continue;
        }
        const identifiers: Array<{name: string; range: import('../utils/text').TextRange}> = [];
        collectIdentifierRefs(transition.guard, identifiers);
        for (const identifier of identifiers) {
            if (globals.has(identifier.name)) {
                continue;
            }
            pushIdentifierDiagnostic(
                diagnostics,
                identifier,
                `Variable ${JSON.stringify(identifier.name)} is not defined. Add a \`def\` declaration or fix the name.`,
                FCSTM_DIAGNOSTIC_CODES.undefinedVar,
                'error'
            );
        }
    }
}

function addEffectBlockDiagnostics(
    transitions: FcstmSemanticTransition[],
    globals: Set<string>,
    diagnostics: FcstmDiagnostic[]
): void {
    for (const transition of transitions) {
        const ast = transition.ast as (FcstmAstTransition | FcstmAstForcedTransition) & {
            effect?: FcstmAstOperationBlock;
        };
        if (ast.effect) {
            analyzeOperationBlock(ast.effect, globals, diagnostics);
        }
    }
}

function addActionBlockDiagnostics(
    actions: FcstmSemanticDocument['actions'],
    globals: Set<string>,
    diagnostics: FcstmDiagnostic[]
): void {
    for (const semanticAction of actions) {
        if (semanticAction.mode !== 'operations') {
            continue;
        }
        const ast = semanticAction.ast as FcstmAstAction;
        const block = ast.operationBlock || ast.operation_block;
        analyzeOperationBlock(block, globals, diagnostics);
    }
}

function addExpressionAndVariableDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    addVariableDefinitionDiagnostics(semantic, document, diagnostics);

    const globals = collectTopLevelGlobals(semantic);

    addGuardDiagnostics(semantic.transitions, globals, diagnostics);
    addEffectBlockDiagnostics(semantic.transitions, globals, diagnostics);
    addActionBlockDiagnostics(semantic.actions, globals, diagnostics);
}

/**
 * Run static semantic analyzers that are strong enough to feed diagnostics and quick fixes.
 */
/**
 * ``E_DUPLICATE_STATE`` — two child states share the same name under the
 * same composite scope. Mirrors ``pyfcstm.model.model._recursive_finish_states``
 * duplicate-substate detection.
 */
function addDuplicateStateDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const byParent = new Map<string | undefined, Map<string, typeof semantic.states[number]>>();
    for (const state of semantic.states) {
        const parentKey = state.parentStateId;
        let group = byParent.get(parentKey);
        if (!group) {
            group = new Map();
            byParent.set(parentKey, group);
        }
        const first = group.get(state.name);
        if (first) {
            const parentPath = (first.identity.qualifiedName || '').split('.').slice(0, -1).join('.');
            diagnostics.push({
                range: findIdentifierRange(document, state.name, state.range),
                message: `State ${JSON.stringify(state.name)} is already defined in scope ${JSON.stringify(parentPath || '<root>')}.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.duplicateState,
                data: {
                    state_name: state.name,
                    parent_path: parentPath,
                },
                relatedInformation: [{
                    location: {
                        uri: toFileUri(document),
                        range: findIdentifierRange(document, first.name, first.range),
                    },
                    message: `First definition of ${JSON.stringify(state.name)} is here.`,
                }],
            });
            continue;
        }
        group.set(state.name, state);
    }
}

/**
 * ``E_DUPLICATE_FUNCTION_NAME`` — two named lifecycle actions on the
 * same state share the same name within the same stage.
 */
function addDuplicateFunctionNameDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const seen = new Map<string, typeof semantic.actions[number]>();
    for (const action of semantic.actions) {
        if (!action.name) {
            continue;
        }
        const stageKey = action.aspect ? `${action.stage}:${action.aspect}` : action.stage;
        const key = `${action.ownerStateId}::${stageKey}::${action.name}`;
        const first = seen.get(key);
        if (first) {
            const statePath = action.ownerStatePath.join('.');
            diagnostics.push({
                range: action.range,
                message: `Named action ${JSON.stringify(action.name)} is already defined in stage ${JSON.stringify(stageKey)} of state ${JSON.stringify(statePath)}.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.duplicateFunctionName,
                data: {
                    function_name: action.name,
                    state_path: statePath,
                    stage: stageKey,
                },
                relatedInformation: [{
                    location: {
                        uri: toFileUri(document),
                        range: first.range,
                    },
                    message: `First definition is here.`,
                }],
            });
            continue;
        }
        seen.set(key, action);
    }
}

/**
 * ``E_DURING_ASPECT_INVALID`` — a leaf state cannot host
 * ``>> during before/after`` aspect actions; only composite states can.
 * Mirrors ``pyfcstm.model.model`` rule: aspect actions are descendant-fanning
 * and a leaf has no descendant by definition.
 */
function addDuringAspectInvalidDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const stateById = new Map<string, typeof semantic.states[number]>();
    for (const state of semantic.states) {
        stateById.set(state.identity.id, state);
    }
    for (const action of semantic.actions) {
        if (!action.isGlobalAspect) {
            continue;
        }
        const owner = stateById.get(action.ownerStateId);
        if (!owner) {
            continue;
        }
        if (!owner.composite) {
            diagnostics.push({
                range: action.range,
                message: `Aspect '>> during ${action.aspect ?? 'before'}' cannot appear in leaf state ${JSON.stringify(owner.name)}; aspect actions need at least one descendant leaf.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.duringAspectInvalid,
                data: {
                    state_path: action.ownerStatePath.join('.'),
                    state_kind: 'leaf',
                    aspect: action.aspect ?? 'before',
                },
            });
        }
    }
}

/**
 * ``E_PSEUDO_NOT_LEAF`` — ``pseudo state`` was declared but the body
 * still contains substates. pyfcstm rule: pseudo states must be leaves.
 */
function addPseudoNotLeafDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    for (const state of semantic.states) {
        if (state.pseudo && state.childStateIds.length > 0) {
            diagnostics.push({
                range: findIdentifierRange(document, state.name, state.range),
                message: `Pseudo state ${JSON.stringify(state.name)} cannot contain substates; declare it as a regular composite or remove the children.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.pseudoNotLeaf,
                data: {
                    state_path: state.identity.qualifiedName,
                },
            });
        }
    }
}

/**
 * ``E_INITIAL_TRANSITION_INVALID`` — a composite state lacks any
 * ``[*] -> child`` initial transition. The runtime cannot pick an
 * entry child on entry.
 */
function addInitialTransitionInvalidDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    const initialByOwner = new Map<string, number>();
    for (const transition of semantic.transitions) {
        if (transition.sourceKind !== 'init') {
            continue;
        }
        initialByOwner.set(transition.ownerStateId, (initialByOwner.get(transition.ownerStateId) ?? 0) + 1);
    }
    for (const state of semantic.states) {
        if (!state.composite || state.pseudo) {
            continue;
        }
        if ((initialByOwner.get(state.identity.id) ?? 0) === 0) {
            diagnostics.push({
                range: findIdentifierRange(document, state.name, state.range),
                message: `Composite state ${JSON.stringify(state.name)} has no '[*] -> child' initial transition; the runtime cannot decide which child to enter.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.initialTransitionInvalid,
                data: {
                    composite_path: state.identity.qualifiedName,
                    reason: 'no_initial_transition',
                },
            });
        }
    }
}

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
    addExpressionAndVariableDiagnostics(semantic, document, diagnostics);
    addDuplicateStateDiagnostics(semantic, document, diagnostics);
    addDuplicateFunctionNameDiagnostics(semantic, document, diagnostics);
    addDuringAspectInvalidDiagnostics(semantic, document, diagnostics);
    addPseudoNotLeafDiagnostics(semantic, document, diagnostics);
    addInitialTransitionInvalidDiagnostics(semantic, document, diagnostics);
    return diagnostics;
}
