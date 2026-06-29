import {pathToFileURL} from 'node:url';

import type {
    FcstmAstAction,
    FcstmAstAssignmentStatement,
    FcstmAstBinaryExpression,
    FcstmAstConditionalExpression,
    FcstmAstExpression,
    FcstmAstForcedTransition,
    FcstmAstFunctionExpression,
    FcstmAstIfStatement,
    FcstmAstImportMapping,
    FcstmAstLiteralExpression,
    FcstmAstOperationBlock,
    FcstmAstOperationStatement,
    FcstmAstTransition,
    FcstmAstUnaryExpression,
} from '../ast';
import type {FcstmSemanticDocument, FcstmSemanticImport, FcstmSemanticTransition} from '../semantics';
import {FcstmDiagnostic, rangeIsEmptyOrInvalid, TextDocumentLike} from '../utils/text';
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
    forcedTransitionExpansion: 'E_FORCED_TRANSITION_EXPANSION',
    eventRefInvalid: 'E_EVENT_REF_INVALID',
    eventNotFound: 'E_EVENT_NOT_FOUND',
    typeMismatch: 'E_TYPE_MISMATCH',
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
    guardConstTrue: 'W_GUARD_CONST_TRUE',
    deadlockLeaf: 'W_DEADLOCK_LEAF',
    initialUnconditionalMissing: 'W_INITIAL_UNCONDITIONAL_MISSING',
    unreferencedVar: 'W_UNREFERENCED_VAR',
    effectSelfAssign: 'W_EFFECT_SELF_ASSIGN',
    comboDuplicateEvent: 'W_COMBO_DUPLICATE_EVENT',
    comboGuardConstTrue: 'W_COMBO_GUARD_CONST_TRUE',
    comboGuardConstFalse: 'W_COMBO_GUARD_CONST_FALSE',
    comboGuardPrefixImplied: 'W_COMBO_GUARD_PREFIX_IMPLIED',
    comboGuardPrefixContradicts: 'W_COMBO_GUARD_PREFIX_CONTRADICTS',
} as const;


const EXPR_PRECEDENCE: Record<string, number> = {
    'function_call': 90,
    'unary+': 80,
    'unary-': 80,
    '!': 80,
    'not': 80,
    '**': 70,
    '*': 60,
    '/': 60,
    '%': 60,
    '+': 50,
    '-': 50,
    '<<': 40,
    '>>': 40,
    '&': 35,
    '^': 30,
    '|': 25,
    '<': 20,
    '>': 20,
    '<=': 20,
    '>=': 20,
    '==': 20,
    '!=': 20,
    'iff': 20,
    '&&': 15,
    'and': 15,
    'xor': 12,
    '||': 10,
    'or': 10,
    '=>': 7,
    '?:': 5,
};
const HEX_RADIX = 16;
const BINARY_RADIX = 2;

function canonicalBinaryOperator(op: string): string {
    if (op === 'and') return '&&';
    if (op === 'or') return '||';
    if (op === 'implies') return '=>';
    return op;
}

function canonicalUnaryOperator(op: string): string {
    return op === 'not' ? '!' : op;
}

function unaryPrecedenceKey(op: string): string {
    const canonical = canonicalUnaryOperator(op);
    return canonical === '+' || canonical === '-' ? `unary${canonical}` : canonical;
}

function normalizeDecimalDigits(raw: string): string {
    const normalized = raw.replace(/^0+/, '');
    return normalized.length > 0 ? normalized : '0';
}

function addSmallDecimal(raw: string, value: number): string {
    if (value === 0) return raw;
    let carry = value;
    const out: string[] = [];
    for (let index = raw.length - 1; index >= 0; index -= 1) {
        const total = Number(raw[index]) + carry;
        out.push(String(total % 10));
        carry = Math.floor(total / 10);
    }
    while (carry > 0) {
        out.push(String(carry % 10));
        carry = Math.floor(carry / 10);
    }
    return out.reverse().join('');
}

function multiplySmallDecimal(raw: string, factor: number): string {
    if (raw === '0' || factor === 0) return '0';
    let carry = 0;
    const out: string[] = [];
    for (let index = raw.length - 1; index >= 0; index -= 1) {
        const total = Number(raw[index]) * factor + carry;
        out.push(String(total % 10));
        carry = Math.floor(total / 10);
    }
    while (carry > 0) {
        out.push(String(carry % 10));
        carry = Math.floor(carry / 10);
    }
    return out.reverse().join('');
}

function convertRadixDigitsToDecimal(digits: string, radix: number): string {
    let value = '0';
    for (const char of digits.toLowerCase()) {
        const digit = parseInt(char, radix);
        value = addSmallDecimal(multiplySmallDecimal(value, radix), digit);
    }
    return value;
}

function numericAstText(expression: FcstmAstLiteralExpression): string {
    const raw = expression.valueText.trim();
    if (/^\d+$/.test(raw)) return normalizeDecimalDigits(raw);
    if (/^0[xX][0-9a-fA-F]+$/.test(raw)) {
        return convertRadixDigitsToDecimal(raw.slice(2), HEX_RADIX);
    }
    if (/^0[bB][01]+$/.test(raw)) {
        return convertRadixDigitsToDecimal(raw.slice(2), BINARY_RADIX);
    }
    const value = Number(raw);
    if (expression.pyNodeType === 'Float') {
        return Number.isInteger(value) ? `${value}.0` : String(value);
    }
    return String(Math.trunc(value));
}

function astExprPrecedence(expression: FcstmAstExpression): number | null {
    if (expression.expressionKind === 'binary') {
        return EXPR_PRECEDENCE[canonicalBinaryOperator(expression.op)] ?? null;
    }
    if (expression.expressionKind === 'conditional') return EXPR_PRECEDENCE['?:'];
    if (expression.expressionKind === 'unary') return EXPR_PRECEDENCE[unaryPrecedenceKey(expression.op)] ?? null;
    return null;
}

function astExprText(expression: FcstmAstExpression | undefined): string | null {
    if (!expression) return null;
    switch (expression.expressionKind) {
        case 'literal':
            return expression.literalType === 'boolean'
                ? expression.valueText.toLowerCase()
                : numericAstText(expression);
        case 'identifier':
            return expression.name;
        case 'mathConst':
            return expression.name;
        case 'parenthesized':
            return astExprText(expression.expression);
        case 'function': {
            const argument = astExprText(expression.argument);
            return argument === null ? null : `${expression.functionName}(${argument})`;
        }
        case 'unary': {
            const op = canonicalUnaryOperator(expression.op);
            const myPrecedence = EXPR_PRECEDENCE[unaryPrecedenceKey(expression.op)];
            let value = astExprText(expression.operand);
            if (value === null) return null;
            const valuePrecedence = astExprPrecedence(expression.operand);
            if (valuePrecedence !== null && valuePrecedence <= myPrecedence) {
                value = `(${value})`;
            }
            return `${op}${value}`;
        }
        case 'binary': {
            const op = canonicalBinaryOperator(expression.op);
            const myPrecedence = EXPR_PRECEDENCE[op];
            let left = astExprText(expression.left);
            let right = astExprText(expression.right);
            if (left === null || right === null) return null;
            const leftPrecedence = astExprPrecedence(expression.left);
            if (leftPrecedence !== null && leftPrecedence < myPrecedence) {
                left = `(${left})`;
            }
            const rightPrecedence = astExprPrecedence(expression.right);
            if (rightPrecedence !== null && rightPrecedence <= myPrecedence) {
                right = `(${right})`;
            }
            return `${left} ${op} ${right}`;
        }
        case 'conditional': {
            const myPrecedence = EXPR_PRECEDENCE['?:'];
            const condition = astExprText(expression.condition);
            let whenTrue = astExprText(expression.whenTrue);
            let whenFalse = astExprText(expression.whenFalse);
            if (condition === null || whenTrue === null || whenFalse === null) return null;
            const truePrecedence = astExprPrecedence(expression.whenTrue);
            if (truePrecedence !== null && truePrecedence <= myPrecedence) {
                whenTrue = `(${whenTrue})`;
            }
            const falsePrecedence = astExprPrecedence(expression.whenFalse);
            if (falsePrecedence !== null && falsePrecedence <= myPrecedence) {
                whenFalse = `(${whenFalse})`;
            }
            return `(${condition}) ? ${whenTrue} : ${whenFalse}`;
        }
    }
}

function isFalseLiteral(expression: FcstmAstExpression): boolean {
    return expression.expressionKind === 'literal'
        && expression.literalType === 'boolean'
        && /^(false|False)$/i.test(expression.valueText);
}

function dottedPath(path: readonly string[] | undefined): string | null {
    return path && path.length > 0 ? path.join('.') : null;
}

function transitionDiagnosticEndpointPaths(
    transition: FcstmSemanticTransition,
): {from_path?: string; to_path?: string} {
    if (transition.forced && transition.expandedTransitions.length === 1) {
        const [expanded] = transition.expandedTransitions;
        const fromPath = dottedPath(expanded.sourceStatePath);
        const toPath = expanded.targetKind === 'exit'
            ? '[*]'
            : dottedPath(expanded.targetStatePath);
        return {
            ...(fromPath ? {from_path: fromPath} : {}),
            ...(toPath ? {to_path: toPath} : {}),
        };
    }

    const fromPath = transition.sourceKind === 'init'
        ? '[*]'
        : dottedPath(transition.sourceStatePath) ?? transition.sourceStateName ?? null;
    const toPath = transition.targetKind === 'exit'
        ? '[*]'
        : dottedPath(transition.targetStatePath) ?? transition.targetStateName ?? null;
    return {
        ...(fromPath ? {from_path: fromPath} : {}),
        ...(toPath ? {to_path: toPath} : {}),
    };
}

function transitionModelOrderIndex(transition: FcstmSemanticTransition): number | null {
    const rawIndex = transition.ast.transitionIndex;
    if (typeof rawIndex === 'number' && Number.isInteger(rawIndex)) return rawIndex;

    if (!Array.isArray(transition.ast.transitionIndexRefs)) return null;
    if (transition.forced && transition.expandedTransitions.length === 1) {
        const [expanded] = transition.expandedTransitions;
        const match = transition.ast.transitionIndexRefs.find(ref => (
            typeof ref.index === 'number' &&
            (typeof ref.fromPath !== 'string' || ref.fromPath === dottedPath(expanded.sourceStatePath)) &&
            (typeof ref.toPath !== 'string' || ref.toPath === (
                expanded.targetKind === 'exit' ? '[*]' : dottedPath(expanded.targetStatePath)
            ))
        ));
        return typeof match?.index === 'number' ? match.index : null;
    }

    const endpoints = transitionDiagnosticEndpointPaths(transition);
    const match = transition.ast.transitionIndexRefs.find(ref => (
        typeof ref.index === 'number' &&
        (typeof ref.fromPath !== 'string' || ref.fromPath === endpoints.from_path) &&
        (typeof ref.toPath !== 'string' || ref.toPath === endpoints.to_path)
    ));
    return typeof match?.index === 'number' ? match.index : null;
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
    // Defensive: callers always pass a non-empty state name.
    /* c8 ignore start */
    if (!stateName) {
        return undefined;
    }
    /* c8 ignore stop */

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
            const isVariable = mapping.kind === 'importDefMapping';
            const mappingKind: 'variable' | 'event' = isVariable ? 'variable' : 'event';
            const sourceName = isVariable ? mapping.selector.text : mapping.sourceEvent.text;
            const targetName = isVariable ? mapping.targetTemplate : mapping.targetEvent.text;
            const key = `${mapping.kind}:${sourceName}->${targetName}`;
            const firstMapping = seen.get(key);
            if (firstMapping) {
                diagnostics.push({
                    range: mapping.range,
                    message: `Duplicate import mapping ${JSON.stringify(mapping.text)} in alias ${JSON.stringify(importItem.alias)}.`,
                    // pyfcstm imports.py treats duplicate mappings as a
                    // hard error; align the severity so the two ends
                    // emit the same blocking level for the same input.
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.importDuplicateMapping,
                    data: {
                        alias: importItem.alias,
                        mapping_kind: mappingKind,
                        // The dedupe key matches when both source AND target
                        // are identical, so either ``direction`` is technically
                        // correct. Pick ``source_duplicated`` as the canonical
                        // form to match pyfcstm's ordering of these checks.
                        duplicated_name: sourceName,
                        direction: 'source_duplicated',
                        host_state_path: importItem.ownerStatePath.join('.'),
                    },
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
            data: {
                state_path: state.identity.qualifiedName,
            },
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
                // pyfcstm distinguishes forced-transition expansion failures
                // (E_FORCED_TRANSITION_EXPANSION) from regular dangling
                // transitions. Replicate that here so downstream LLM
                // dispatch logic can tell whether the bad endpoint came
                // from a ``!`` forced declaration.
                const isForced = transition.forced;
                diagnostics.push({
                    range: findIdentifierRange(document, transition.sourceStateName, transition.range),
                    message: isForced
                        ? `Forced transition source state ${JSON.stringify(transition.sourceStateName)} cannot be resolved in this scope.`
                        : `State ${JSON.stringify(transition.sourceStateName)} cannot be resolved in this scope.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: isForced
                        ? FCSTM_DIAGNOSTIC_CODES.forcedTransitionExpansion
                        : FCSTM_DIAGNOSTIC_CODES.missingState,
                    data: isForced
                        ? {
                            original_raw: transition.ast.text,
                            reason: 'src_not_found',
                        }
                        : {
                            state_path: transition.sourceStateName,
                            referenced_from: 'transition_source',
                            reason: 'not_found',
                        },
                });
            }
        }

        if (transition.targetKind === 'state' && transition.targetStateName && !transition.targetStateId) {
            const imported = findImportAlias(semantic, transition.ownerStatePath, transition.targetStateName);
            if (!imported) {
                const isForced = transition.forced;
                diagnostics.push({
                    range: findIdentifierRange(document, transition.targetStateName, transition.range, {preferLast: true}),
                    message: isForced
                        ? `Forced transition target state ${JSON.stringify(transition.targetStateName)} cannot be resolved in this scope.`
                        : `Transition target state ${JSON.stringify(transition.targetStateName)} cannot be resolved in this scope.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: isForced
                        ? FCSTM_DIAGNOSTIC_CODES.forcedTransitionExpansion
                        : FCSTM_DIAGNOSTIC_CODES.danglingTransition,
                    data: isForced
                        ? {
                            original_raw: transition.ast.text,
                            reason: 'tgt_not_found',
                        }
                        : {
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
                // For forced expansions, ``transition.guard`` still points at
                // the original forced declaration guard, so this range anchors
                // literal-false warnings to the authored guard expression.
                range: !sourceUnreachable && transition.guard ? transition.guard.range : transition.range,
                message: sourceUnreachable
                    ? `Transition ${JSON.stringify(transition.ast.text)} is dead because its source state is unreachable.`
                    : `Transition ${JSON.stringify(transition.ast.text)} is dead because its guard is always false.`,
                severity: 'warning',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.guardConstFalse,
                data: {
                    transition_span: null,
                    folded_value: false,
                    guard_text: astExprText(transition.guard),
                    transition_index: transitionModelOrderIndex(transition),
                    ...transitionDiagnosticEndpointPaths(transition),
                },
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
            data: {
                event_qualified_name: event.identity.qualifiedName,
                // ``event Foo;`` declarations are always source-local
                // (they bind into the enclosing state's namespace).
                // Re-scoping happens at transition-trigger sites (``::``
                // / ``:`` / ``/``), not at declaration sites.
                scope: 'local',
            },
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
        // M2: fill schema-required ``ref_path`` + ``reason``. The
        // jsfcstm resolver does not yet distinguish state-not-found
        // vs named-function-not-found; emit the latter as a
        // conservative default, matching the common case where the
        // path resolves but the action name doesn't.
        diagnostics.push({
            range: findIdentifierRange(document, refName, action.ref.range, {preferLast: true}),
            message: `Action reference ${JSON.stringify(action.ref.rawPath)} cannot be resolved.`,
            severity: 'error',
            source: 'fcstm',
            code: FCSTM_DIAGNOSTIC_CODES.namedFunctionRefNotFound,
            data: {
                ref_path: action.ref.rawPath,
                reason: 'named_function_not_found',
            },
        });
    }
}

function collectIdentifierRefs(
    expression: FcstmAstExpression | null | undefined,
    out: Array<{name: string; range: import('../utils/text').TextRange}>
): void {
    // Defensive: callers gate on a non-null expression
    // before invoking this walker.
    /* c8 ignore start */
    if (!expression) {
        return;
    }
    /* c8 ignore stop */
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
    if (identifier.name.length === 0 || rangeIsEmptyOrInvalid(identifier.range)) {
        return;
    }
    // M2 (PR #115 final review): inject ``var_name`` from the
    // identifier itself so every E_UNDEFINED_VAR / E_DUPLICATE_VAR
    // emit carries the schema-required field without each caller
    // having to remember it. Callers can still override by passing
    // ``var_name`` in their ``data``.
    const mergedData: Record<string, unknown> = {var_name: identifier.name, ...(data ?? {})};
    diagnostics.push({
        range: identifier.range,
        message,
        severity,
        source: 'fcstm',
        code,
        data: mergedData,
    });
}

/**
 * Walk a block of operational statements while tracking which names are already
 * assigned inside the block. Names that are not in ``globals`` become
 * block-local temporary variables after their first assignment, matching the
 * pyfcstm runtime rule.
 */
/**
 * Schema enum for ``E_UNDEFINED_VAR.refs.referenced_in`` (see
 * ``pyfcstm/diagnostics/codes.yaml``). Threaded from each call site
 * to keep the emitted payload schema-conformant.
 */
export type ReferencedIn =
    | 'guard'
    | 'effect'
    | 'enter'
    | 'during'
    | 'exit'
    | 'during_aspect'
    | 'init';

function analyzeOperationStatements(
    statements: FcstmAstOperationStatement[] | undefined,
    globals: Set<string>,
    assignedBefore: Set<string>,
    diagnostics: FcstmDiagnostic[],
    referencedIn: ReferencedIn
): Set<string> {
    const assigned = new Set(assignedBefore);
    // Defensive: AST builder never emits operation-block nodes with
    // a null ``statements`` array; the empty-block case shows up as
    // an empty array, not null.
    /* c8 ignore start */
    if (!statements) {
        return assigned;
    }
    /* c8 ignore stop */

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
                    {is_temporary: true, referenced_in: referencedIn}
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
                            {is_temporary: true, referenced_in: referencedIn}
                        );
                    }
                }
                const branchResult = analyzeOperationStatements(
                    branch.statements,
                    globals,
                    assigned,
                    diagnostics,
                    referencedIn
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
    diagnostics: FcstmDiagnostic[],
    referencedIn: ReferencedIn
): void {
    // Defensive: callers guard ``block`` truthy before invoking.
    /* c8 ignore start */
    if (!block) {
        return;
    }
    /* c8 ignore stop */
    analyzeOperationStatements(block.statements, globals, new Set(), diagnostics, referencedIn);
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
            data: {
                var_name: variable.name,
            },
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
                'error',
                {referenced_in: 'guard'}
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
            analyzeOperationBlock(ast.effect, globals, diagnostics, 'effect');
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
        // Map AST stage + aspect onto the schema enum:
        //   ``>> during before/after`` → ``during_aspect``
        //   bare ``enter|during|exit`` → same name
        const referencedIn: ReferencedIn = ast.aspect ? 'during_aspect' : ast.stage;
        analyzeOperationBlock(block, globals, diagnostics, referencedIn);
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
 * ``>> during before/after`` aspect actions. Aspect actions fan out to
 * every descendant leaf, so a leaf state (no descendants) has nothing
 * to fan into and the aspect declaration is invalid.
 *
 * Uses the structural definition of "leaf": ``childStateIds.length ===
 * 0``. The grammar-level ``state.composite`` field already aligns to
 * this (see ``ast/builder.ts`` — composite is true iff there is at
 * least one substate or one import that gets merged in), so ``leaf =
 * !state.composite`` is the canonical check.
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
        const owner = stateById.get(action.ownerStateId);
        // Defensive: every action's ownerStateId is added to stateById
        // before the iteration starts.
        /* c8 ignore start */
        if (!owner) {
            continue;
        }
        /* c8 ignore stop */
        /* c8 ignore start -- defensive: the enclosing loop
           iterates ``semantic.actions``, all of which have
           ``stage`` populated by the AST builder; this guard is
           a belt-and-braces against future builder changes. */
        if (action.stage !== 'during') {
            continue;
        }
        /* c8 ignore stop */

        // Scenario (c): global ``>> during before/after`` aspect on a
        // leaf state — there is no descendant for the aspect to fan
        // into.
        if (action.isGlobalAspect && !owner.composite) {
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
            continue;
        }

        // I-f scenarios (a) and (b): non-global ``during`` action.
        if (action.isGlobalAspect) {
            continue;
        }

        // I3 lockdown (PR #116 re-review): ``aspect`` may be
        // ``undefined`` from the live AST or ``null`` after a JSON
        // round-trip / cross-worker serialization. Treat any value
        // that is not the literal string ``'before'`` / ``'after'``
        // as the bare-during case to keep both ends agreeing.
        const aspectIsBeforeAfter = action.aspect === 'before' || action.aspect === 'after';

        // Scenario (a): leaf state with a local ``during before`` /
        // ``during after`` — the aspect-qualified during only makes
        // sense on a composite (it gates on entry/exit of the
        // composite).
        if (!owner.composite && aspectIsBeforeAfter) {
            diagnostics.push({
                range: action.range,
                message: `For leaf state ${JSON.stringify(owner.name)}, during cannot assign aspect ${JSON.stringify(action.aspect)}.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.duringAspectInvalid,
                data: {
                    state_path: action.ownerStatePath.join('.'),
                    state_kind: 'leaf',
                    aspect: action.aspect,
                },
            });
            continue;
        }

        // Scenario (b): composite state with a bare ``during`` (no
        // aspect token) — composites must pick ``before`` or ``after``.
        if (owner.composite && !aspectIsBeforeAfter) {
            diagnostics.push({
                range: action.range,
                message: `For composite state ${JSON.stringify(owner.name)}, during must assign aspect to either 'before' or 'after'.`,
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.duringAspectInvalid,
                data: {
                    state_path: action.ownerStatePath.join('.'),
                    state_kind: 'composite',
                    aspect: null,
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
                    reason: 'missing_entry',
                },
            });
        }
    }
}

export function collectSemanticAnalysisDiagnosticsFromSemantic(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
): FcstmDiagnostic[] {
    const diagnostics: FcstmDiagnostic[] = [];
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
    addTypeMismatchDiagnostics(semantic, document, diagnostics);
    return diagnostics;
}

export async function collectSemanticAnalysisDiagnostics(
    document: TextDocumentLike
): Promise<FcstmDiagnostic[]> {
    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    // Defensive: callers always invoke against documents with a
    // semantic analysis available; this guard exists for hypothetical
    // future async paths.
    /* c8 ignore start */
    if (!semantic) {
        return [];
    }
    /* c8 ignore stop */

    return collectSemanticAnalysisDiagnosticsFromSemantic(semantic, document);
}

// -------------------------------------------------------------------------
// ``E_TYPE_MISMATCH`` — light-weight type checker.
//
// pyfcstm separates arithmetic (``num_expression``) and logical
// (``cond_expression``) expressions in its grammar; jsfcstm's AST keeps
// the same separation via ``expression.expressionType`` ('init' / 'num'
// / 'cond'). The grammar already prevents many obvious mixes, but a
// handful of cases slip through (e.g. ``if [x]`` where ``x`` is an
// integer, or ``def int y = a > 1;``). This analyzer walks every
// expression and confirms that operand categories match the operator's
// requirement, mirroring pyfcstm's planned ``E_TYPE_MISMATCH`` semantics:
//
//   * guard: must produce ``boolean``
//   * assignment RHS / def initializer / function arg / arithmetic
//     operand: must produce ``numeric``
//   * logical operand (``&&`` / ``||`` / ``!``): must produce ``boolean``
//   * comparison operand: must produce ``numeric``
//   * ternary condition: must produce ``boolean``; both branches share
//     the parent's expected category
// -------------------------------------------------------------------------

type TypeCategory = 'numeric' | 'boolean' | 'unknown';

const ARITH_BINARY_OPS = new Set(['+', '-', '*', '/', '%', '**']);
const BITWISE_BINARY_OPS = new Set(['&', '|', '^', '<<', '>>']);
const COMPARISON_OPS = new Set(['==', '!=', '<', '<=', '>', '>=', '<>']);
const LOGICAL_BINARY_OPS = new Set([
    '&&',
    '||',
    '=>',
    'xor',
    'iff',
    'and',
    'or',
    'implies',
    'AND',
    'OR',
    'IMPLIES',
]);

function isLogicalUnaryOp(op: string | undefined): boolean {
    if (!op) return false;
    return op === '!' || op === 'not' || op === 'NOT';
}

export function inferExpressionCategory(expr: FcstmAstExpression): TypeCategory {
    switch (expr.expressionKind) {
        case 'literal': {
            const lit = expr as FcstmAstLiteralExpression;
            return lit.literalType === 'boolean' ? 'boolean' : 'numeric';
        }
        case 'identifier':
            // pyfcstm only supports ``int`` and ``float`` def types,
            // both of which are numeric. Truly undefined identifiers
            // are caught by E_UNDEFINED_VAR; we keep ``numeric`` as
            // the optimistic guess to avoid double-firing.
            return 'numeric';
        case 'mathConst':
        case 'function':
            return 'numeric';
        case 'unary': {
            const un = expr as FcstmAstUnaryExpression;
            return isLogicalUnaryOp(un.operator) ? 'boolean' : 'numeric';
        }
        case 'binary': {
            const bin = expr as FcstmAstBinaryExpression;
            const op = bin.operator;
            if (LOGICAL_BINARY_OPS.has(op) || COMPARISON_OPS.has(op)) {
                return 'boolean';
            }
            // arithmetic + bitwise → numeric
            if (ARITH_BINARY_OPS.has(op) || BITWISE_BINARY_OPS.has(op)) {
                return 'numeric';
            }
            /* c8 ignore start */
            // Defensive: grammar covers all 3 BinaryOp categories
            // above; ``unknown`` is the fallback for any future
            // operator extension.
            return 'unknown';
        }
        /* c8 ignore stop */
        case 'conditional': {
            const cond = expr as FcstmAstConditionalExpression;
            // The ternary's result category is the branch category. We
            // walk the true branch first; if it is unknown we try the
            // false branch as a fallback.
            const t = inferExpressionCategory(cond.whenTrue || cond.valueTrue);
            if (t !== 'unknown') return t;
            return inferExpressionCategory(cond.whenFalse || cond.valueFalse);
        }
    }
    return 'unknown';
}

function emitTypeMismatch(
    diagnostics: FcstmDiagnostic[],
    expr: FcstmAstExpression,
    expected: TypeCategory,
    actual: TypeCategory,
): void {
    const exprText = (expr as {text?: string}).text ?? '';
    if (exprText.length === 0 || rangeIsEmptyOrInvalid(expr.range)) {
        return;
    }
    diagnostics.push({
        range: expr.range,
        message: `Type mismatch: expected ${expected} expression, got ${actual} (${JSON.stringify(exprText)}).`,
        severity: 'error',
        source: 'fcstm',
        code: FCSTM_DIAGNOSTIC_CODES.typeMismatch,
        data: {
            expected,
            actual,
            expr_text: exprText,
        },
    });
}

/**
 * Recursively type-check ``expr`` against the surrounding ``expected``
 * category. Reports a mismatch when the inferred category disagrees;
 * keeps recursing so that nested sub-expressions also get checked, but
 * stops descending past the offending node to avoid cascading reports.
 */
export function checkExpression(
    expr: FcstmAstExpression | null | undefined,
    expected: TypeCategory,
    diagnostics: FcstmDiagnostic[],
): void {
    if (!expr) return;

    const actual = inferExpressionCategory(expr);
    let categoryOk = actual === 'unknown' || actual === expected;
    if (!categoryOk) {
        emitTypeMismatch(diagnostics, expr, expected, actual);
    }

    switch (expr.expressionKind) {
        case 'unary': {
            const un = expr as FcstmAstUnaryExpression;
            const childExpected: TypeCategory = isLogicalUnaryOp(un.operator) ? 'boolean' : 'numeric';
            checkExpression(un.operand || un.expr, childExpected, diagnostics);
            break;
        }
        case 'binary': {
            const bin = expr as FcstmAstBinaryExpression;
            const op = bin.operator;
            let leftExpected: TypeCategory;
            let rightExpected: TypeCategory;
            if (LOGICAL_BINARY_OPS.has(op)) {
                leftExpected = 'boolean';
                rightExpected = 'boolean';
            } else {
                // arithmetic / bitwise / comparison all want numeric operands
                leftExpected = 'numeric';
                rightExpected = 'numeric';
            }
            checkExpression(bin.left || bin.expr1, leftExpected, diagnostics);
            checkExpression(bin.right || bin.expr2, rightExpected, diagnostics);
            break;
        }
        case 'conditional': {
            const cond = expr as FcstmAstConditionalExpression;
            checkExpression(cond.condition || cond.cond, 'boolean', diagnostics);
            checkExpression(cond.whenTrue || cond.valueTrue, expected, diagnostics);
            checkExpression(cond.whenFalse || cond.valueFalse, expected, diagnostics);
            break;
        }
        case 'function': {
            const fn = expr as FcstmAstFunctionExpression;
            checkExpression(fn.argument || fn.expr, 'numeric', diagnostics);
            break;
        }
        default:
            break;
    }
}

function checkOperationStatements(
    statements: FcstmAstOperationStatement[] | undefined,
    diagnostics: FcstmDiagnostic[],
): void {
    if (!statements) return;
    for (const stmt of statements) {
        if (stmt.kind === 'assignmentStatement') {
            const assign = stmt as FcstmAstAssignmentStatement;
            checkExpression(assign.expression || assign.expr, 'numeric', diagnostics);
        } else if (stmt.kind === 'ifStatement') {
            const ifStmt = stmt as FcstmAstIfStatement;
            for (const branch of ifStmt.branches) {
                if (branch.condition) {
                    checkExpression(branch.condition, 'boolean', diagnostics);
                }
                checkOperationStatements(branch.statements, diagnostics);
            }
            if (ifStmt.elseBlock) {
                checkOperationStatements(ifStmt.elseBlock.statements, diagnostics);
            }
        }
    }
}

function addTypeMismatchDiagnostics(
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike,
    diagnostics: FcstmDiagnostic[]
): void {
    // 1. Variable initializers — must be numeric.
    if (semantic.ast) {
        for (const def of semantic.ast.definitions) {
            const init = def.initializer || def.expr;
            if (init) {
                checkExpression(init, 'numeric', diagnostics);
            }
        }
    }

    // 2. Transition guards — must be boolean; effect-block RHSs — numeric.
    for (const transition of semantic.transitions) {
        const ast = transition.ast as (FcstmAstTransition | FcstmAstForcedTransition) & {
            guard?: FcstmAstExpression;
            effect?: FcstmAstOperationBlock;
        };
        if (ast.guard) {
            checkExpression(ast.guard, 'boolean', diagnostics);
        }
        if (ast.effect) {
            checkOperationStatements(ast.effect.statements, diagnostics);
        }
    }

    // 3. Lifecycle action bodies — RHSs must be numeric.
    for (const action of semantic.actions) {
        const ast = action.ast as FcstmAstAction & {operationBlock?: FcstmAstOperationBlock};
        const block = ast.operationBlock;
        if (block) {
            checkOperationStatements(block.statements, diagnostics);
        }
    }
}
