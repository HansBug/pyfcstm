import {
    BinaryOp,
    Expr,
    IfBlock,
    Integer,
    Float,
    OnAspect,
    OnStage,
    Operation,
    OperationStatement,
    StateMachine,
    Transition,
    UnaryOp,
    Variable,
} from '../../model/runtime';
import type {ModelDiagnosticJson, ModelSpanJson} from '../inspect';
import {foldConditionExpression} from './const-fold';
import {collectExprVariables} from './use-def';

interface ComboOriginRefLike {
    origin_id: string;
    term_index: number;
    role: string;
    consumes_term: boolean;
    term_text: string;
    transition_span?: ModelSpanJson | null;
    trigger_span?: ModelSpanJson | null;
    term_span?: ModelSpanJson | null;
    value_span?: ModelSpanJson | null;
    removal_span?: ModelSpanJson | null;
}

interface ComboTerm {
    ref: ComboOriginRefLike;
    transition: Transition;
}

interface Bound {
    value: number;
    inclusive: boolean;
}

interface SimpleConstraint {
    variable: string;
    lower?: Bound;
    upper?: Bound;
    equal?: number;
}

export function collectComboWarnings(machine: StateMachine | null | undefined): ModelDiagnosticJson[] {
    if (!machine) return [];
    const termsByOrigin = comboTermsByOrigin(machine);
    const diagnostics: ModelDiagnosticJson[] = [];
    for (const terms of termsByOrigin.values()) {
        diagnostics.push(...duplicateEventWarnings(terms));
        diagnostics.push(...guardConstWarnings(terms));
        diagnostics.push(...guardPrefixWarnings(terms));
    }
    return diagnostics;
}

function comboTermsByOrigin(machine: StateMachine): Map<string, ComboTerm[]> {
    const grouped = new Map<string, Map<number, ComboTerm>>();
    for (const transition of machine.allTransitions) {
        for (const rawRef of transition.combo_origin_refs ?? []) {
            const ref = comboOriginRef(rawRef);
            if (!ref || !ref.consumes_term) continue;
            let byIndex = grouped.get(ref.origin_id);
            if (!byIndex) {
                byIndex = new Map<number, ComboTerm>();
                grouped.set(ref.origin_id, byIndex);
            }
            if (!byIndex.has(ref.term_index)) {
                byIndex.set(ref.term_index, {ref, transition});
            }
        }
    }
    const out = new Map<string, ComboTerm[]>();
    for (const [originId, byIndex] of grouped.entries()) {
        out.set(originId, Array.from(byIndex.values()).sort((a, b) => a.ref.term_index - b.ref.term_index));
    }
    return out;
}

function comboOriginRef(value: unknown): ComboOriginRefLike | null {
    if (typeof value !== 'object' || value === null) return null;
    const item = value as Record<string, unknown>;
    if (
        typeof item.origin_id !== 'string' ||
        typeof item.term_index !== 'number' ||
        typeof item.role !== 'string' ||
        typeof item.consumes_term !== 'boolean' ||
        typeof item.term_text !== 'string'
    ) {
        return null;
    }
    return {
        origin_id: item.origin_id,
        term_index: item.term_index,
        role: item.role,
        consumes_term: item.consumes_term,
        term_text: item.term_text,
        transition_span: item.transition_span as ModelSpanJson | null | undefined,
        trigger_span: item.trigger_span as ModelSpanJson | null | undefined,
        term_span: item.term_span as ModelSpanJson | null | undefined,
        value_span: item.value_span as ModelSpanJson | null | undefined,
        removal_span: item.removal_span as ModelSpanJson | null | undefined,
    };
}

function duplicateEventWarnings(terms: ComboTerm[]): ModelDiagnosticJson[] {
    const diagnostics: ModelDiagnosticJson[] = [];
    const firstByEvent = new Map<string, ComboTerm>();
    for (const term of terms) {
        if (!term.transition.event) continue;
        const eventName = term.ref.term_text;
        const first = firstByEvent.get(eventName);
        if (!first) {
            firstByEvent.set(eventName, term);
            continue;
        }
        diagnostics.push({
            code: 'W_COMBO_DUPLICATE_EVENT',
            severity: 'warning',
            message: `Combo trigger repeats event ${JSON.stringify(eventName)}; this is legal but usually redundant.`,
            span: term.ref.term_span ?? null,
            refs: {
                origin_id: term.ref.origin_id,
                event_name: eventName,
                term_index: term.ref.term_index,
                first_term_index: first.ref.term_index,
                term_text: term.ref.term_text,
                first_term_text: first.ref.term_text,
                transition_span: term.ref.transition_span ?? null,
                trigger_span: term.ref.trigger_span ?? null,
                term_span: term.ref.term_span ?? null,
                first_term_span: first.ref.term_span ?? null,
            },
        });
    }
    return diagnostics;
}

function guardConstWarnings(terms: ComboTerm[]): ModelDiagnosticJson[] {
    const diagnostics: ModelDiagnosticJson[] = [];
    for (const term of terms) {
        const guard = term.transition.guard;
        if (!guard) continue;
        const folded = foldConditionExpression(guard);
        if (folded !== true && folded !== false) continue;
        diagnostics.push({
            code: folded ? 'W_COMBO_GUARD_CONST_TRUE' : 'W_COMBO_GUARD_CONST_FALSE',
            severity: 'warning',
            message: `Combo guard term ${JSON.stringify(term.ref.term_text)} is statically ${folded ? 'true' : 'false'}.`,
            span: term.ref.term_span ?? null,
            refs: {
                origin_id: term.ref.origin_id,
                term_index: term.ref.term_index,
                term_text: term.ref.term_text,
                folded_value: folded,
                transition_span: term.ref.transition_span ?? null,
                trigger_span: term.ref.trigger_span ?? null,
                term_span: term.ref.term_span ?? null,
                value_span: term.ref.value_span ?? null,
            },
        });
    }
    return diagnostics;
}

function guardPrefixWarnings(terms: ComboTerm[]): ModelDiagnosticJson[] {
    const diagnostics: ModelDiagnosticJson[] = [];
    const priorGuards: ComboTerm[] = [];
    for (const term of terms) {
        if (!term.transition.guard) continue;
        if (priorGuards.length > 0 && !sideEffectsMayChangeGuardPrefix(terms, term, priorGuards)) {
            const diagnostic = prefixGuardDiagnostic(term, priorGuards);
            if (diagnostic) diagnostics.push(diagnostic);
        }
        priorGuards.push(term);
    }
    return diagnostics;
}

function prefixGuardDiagnostic(current: ComboTerm, priorTerms: ComboTerm[]): ModelDiagnosticJson | null {
    const currentConstraint = current.transition.guard ? simpleConstraint(current.transition.guard) : null;
    if (!currentConstraint) return null;
    for (const prior of priorTerms) {
        const priorConstraint = prior.transition.guard ? simpleConstraint(prior.transition.guard) : null;
        if (!priorConstraint || priorConstraint.variable !== currentConstraint.variable) continue;
        if (constraintsContradict(priorConstraint, currentConstraint)) {
            return makePrefixGuardDiagnostic('W_COMBO_GUARD_PREFIX_CONTRADICTS', 'contradicts prior combo guard terms', current, prior);
        }
        if (constraintImplies(priorConstraint, currentConstraint)) {
            return makePrefixGuardDiagnostic('W_COMBO_GUARD_PREFIX_IMPLIED', 'is implied by prior combo guard terms', current, prior);
        }
    }
    return null;
}

function makePrefixGuardDiagnostic(
    code: 'W_COMBO_GUARD_PREFIX_IMPLIED' | 'W_COMBO_GUARD_PREFIX_CONTRADICTS',
    relation: string,
    current: ComboTerm,
    prior: ComboTerm,
): ModelDiagnosticJson {
    return {
        code,
        severity: 'warning',
        message: `Combo guard term ${JSON.stringify(current.ref.term_text)} ${relation}.`,
        span: current.ref.term_span ?? null,
        refs: {
            origin_id: current.ref.origin_id,
            term_index: current.ref.term_index,
            prior_term_index: prior.ref.term_index,
            term_text: current.ref.term_text,
            prior_term_text: prior.ref.term_text,
            transition_span: current.ref.transition_span ?? null,
            trigger_span: current.ref.trigger_span ?? null,
            term_span: current.ref.term_span ?? null,
            value_span: current.ref.value_span ?? null,
            prior_term_span: prior.ref.term_span ?? null,
            prior_value_span: prior.ref.value_span ?? null,
        },
    };
}

function simpleConstraint(expr: Expr): SimpleConstraint | null {
    if (!(expr instanceof BinaryOp)) return null;
    const leftVariable = expr.x instanceof Variable ? expr.x.name : null;
    const rightVariable = expr.y instanceof Variable ? expr.y.name : null;
    const leftNumber = numericLiteralValue(expr.x);
    const rightNumber = numericLiteralValue(expr.y);
    if (leftVariable && rightNumber !== null) {
        return constraintFromParts(leftVariable, expr.op, rightNumber);
    }
    if (rightVariable && leftNumber !== null) {
        return constraintFromParts(rightVariable, invertComparison(expr.op), leftNumber);
    }
    return null;
}

function numericLiteralValue(expr: Expr): number | null {
    if (expr instanceof Integer || expr instanceof Float) return expr.value;
    if (expr instanceof UnaryOp) {
        const value = numericLiteralValue(expr.x);
        if (value === null) return null;
        if (expr.op === '+') return value;
        if (expr.op === '-') return -value;
    }
    return null;
}

function invertComparison(op: string): string {
    if (op === '<') return '>';
    if (op === '<=') return '>=';
    if (op === '>') return '<';
    if (op === '>=') return '<=';
    return op;
}

function constraintFromParts(variable: string, op: string, value: number): SimpleConstraint | null {
    if (op === '>') return {variable, lower: {value, inclusive: false}};
    if (op === '>=') return {variable, lower: {value, inclusive: true}};
    if (op === '<') return {variable, upper: {value, inclusive: false}};
    if (op === '<=') return {variable, upper: {value, inclusive: true}};
    if (op === '==') return {variable, equal: value};
    return null;
}

function constraintImplies(prior: SimpleConstraint, current: SimpleConstraint): boolean {
    if (prior.equal !== undefined) return valueSatisfies(prior.equal, current);
    if (current.equal !== undefined) return prior.equal === current.equal;
    if (current.lower && prior.lower && lowerAtLeastAsStrong(prior.lower, current.lower)) return true;
    if (current.upper && prior.upper && upperAtLeastAsStrong(prior.upper, current.upper)) return true;
    return false;
}

function constraintsContradict(left: SimpleConstraint, right: SimpleConstraint): boolean {
    if (left.equal !== undefined) return !valueSatisfies(left.equal, right);
    if (right.equal !== undefined) return !valueSatisfies(right.equal, left);
    const lower = strongestLower(left.lower, right.lower);
    const upper = strongestUpper(left.upper, right.upper);
    if (!lower || !upper) return false;
    if (lower.value > upper.value) return true;
    return lower.value === upper.value && (!lower.inclusive || !upper.inclusive);
}

function valueSatisfies(value: number, constraint: SimpleConstraint): boolean {
    if (constraint.equal !== undefined && value !== constraint.equal) return false;
    if (constraint.lower) {
        if (value < constraint.lower.value) return false;
        if (value === constraint.lower.value && !constraint.lower.inclusive) return false;
    }
    if (constraint.upper) {
        if (value > constraint.upper.value) return false;
        if (value === constraint.upper.value && !constraint.upper.inclusive) return false;
    }
    return true;
}

function lowerAtLeastAsStrong(left: Bound, right: Bound): boolean {
    if (left.value > right.value) return true;
    return left.value === right.value && (left.inclusive === right.inclusive || !left.inclusive || right.inclusive);
}

function upperAtLeastAsStrong(left: Bound, right: Bound): boolean {
    if (left.value < right.value) return true;
    return left.value === right.value && (left.inclusive === right.inclusive || !left.inclusive || right.inclusive);
}

function strongestLower(left: Bound | undefined, right: Bound | undefined): Bound | undefined {
    if (!left) return right;
    if (!right) return left;
    return lowerAtLeastAsStrong(left, right) ? left : right;
}

function strongestUpper(left: Bound | undefined, right: Bound | undefined): Bound | undefined {
    if (!left) return right;
    if (!right) return left;
    return upperAtLeastAsStrong(left, right) ? left : right;
}

function sideEffectsMayChangeGuardPrefix(
    terms: ComboTerm[],
    current: ComboTerm,
    priorTerms: ComboTerm[],
): boolean {
    const relevant = guardVariables([...priorTerms, current]);
    if (relevant.length === 0) return false;
    const firstPriorIndex = Math.min(...priorTerms.map(term => term.ref.term_index));
    const sourceTransition = terms[0]?.transition ?? current.transition;
    if (firstHopActionsMayWrite(sourceTransition, relevant)) return true;
    for (const term of terms) {
        if (term.ref.term_index < firstPriorIndex || term.ref.term_index >= current.ref.term_index) continue;
        if (statementsMayWriteRelevant(term.transition.effects, relevant)) return true;
    }
    return false;
}

function guardVariables(terms: ComboTerm[]): string[] {
    const out: string[] = [];
    const seen = new Set<string>();
    for (const term of terms) {
        if (!term.transition.guard) continue;
        for (const name of collectExprVariables(term.transition.guard)) {
            if (seen.has(name)) continue;
            seen.add(name);
            out.push(name);
        }
    }
    return out;
}

function firstHopActionsMayWrite(transition: Transition, relevant: string[]): boolean {
    const parent = transition.parent;
    if (!parent) return false;
    if (transition.fromState === 'INIT_STATE') {
        return actionsMayWriteRelevant(
            parent.onDurings.filter(action => action.aspect === 'before'),
            relevant,
        );
    }
    const source = parent.substates[transition.fromState];
    return source ? actionsMayWriteRelevant(source.onExits, relevant) : false;
}

function actionsMayWriteRelevant(actions: Array<OnStage | OnAspect>, relevant: string[]): boolean {
    for (const action of actions) {
        if (action.isAbstract || action.isRef) return true;
        if (statementsMayWriteRelevant(action.operations, relevant)) return true;
    }
    return false;
}

function statementsMayWriteRelevant(statements: OperationStatement[], relevant: string[]): boolean {
    const relevantSet = new Set(relevant);
    for (const statement of statements) {
        if (statementWritesRelevantOrUnknown(statement, relevantSet)) return true;
    }
    return false;
}

function statementWritesRelevantOrUnknown(statement: OperationStatement, relevant: Set<string>): boolean {
    if (statement instanceof Operation) return relevant.has(statement.varName);
    if (statement instanceof IfBlock) {
        for (const branch of statement.branches) {
            for (const inner of branch.statements) {
                if (statementWritesRelevantOrUnknown(inner, relevant)) return true;
            }
        }
        return false;
    }
    return true;
}
