import {
    BinaryOp,
    BooleanExpr,
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

type VariableDomain = 'int' | 'float';

interface SimpleConstraint {
    variable: string;
    domain: VariableDomain;
    lower?: Bound;
    upper?: Bound;
    equal?: number;
    notEqual?: number[];
}

interface ConstraintSet {
    constraints: Map<string, SimpleConstraint>;
    unsat: boolean;
}

interface ConstraintFormula {
    alternatives: ConstraintSet[];
}

// Conservative DNF explosion guard: if a formula grows beyond this limit, the
// analyzer skips that prefix-sensitive warning instead of risking a false
// positive or slowing editor diagnostics.
const MAX_CONSTRAINT_FORMULA_ALTERNATIVES = 64;

export function collectComboWarnings(machine: StateMachine | null | undefined): ModelDiagnosticJson[] {
    if (!machine) return [];
    const termsByOrigin = comboTermsByOrigin(machine);
    const domains = variableDomains(machine);
    const diagnostics: ModelDiagnosticJson[] = [];
    for (const terms of termsByOrigin.values()) {
        diagnostics.push(...duplicateEventWarnings(terms));
        diagnostics.push(...guardConstWarnings(terms));
        diagnostics.push(...guardPrefixWarnings(terms, domains));
    }
    return diagnostics;
}

function variableDomains(machine: StateMachine): Map<string, VariableDomain> {
    const domains = new Map<string, VariableDomain>();
    for (const define of Object.values(machine.defines)) {
        if (define.type === 'int' || define.type === 'float') {
            domains.set(define.name, define.type);
        }
    }
    return domains;
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

function guardPrefixWarnings(terms: ComboTerm[], domains: Map<string, VariableDomain>): ModelDiagnosticJson[] {
    const diagnostics: ModelDiagnosticJson[] = [];
    const priorGuards: ComboTerm[] = [];
    for (const term of terms) {
        if (!term.transition.guard) continue;
        if (priorGuards.length > 0 && !sideEffectsMayChangeGuardPrefix(terms, term, priorGuards)) {
            const diagnostic = prefixGuardDiagnostic(term, priorGuards, domains);
            if (diagnostic) diagnostics.push(diagnostic);
        }
        priorGuards.push(term);
    }
    return diagnostics;
}

function prefixGuardDiagnostic(
    current: ComboTerm,
    priorTerms: ComboTerm[],
    domains: Map<string, VariableDomain>,
): ModelDiagnosticJson | null {
    const currentFormula = current.transition.guard ? constraintFormulaFromExpression(current.transition.guard, domains) : null;
    if (!currentFormula) return null;

    const priorFormulas: Array<{term: ComboTerm; formula: ConstraintFormula}> = [];
    for (const prior of priorTerms) {
        const formula = prior.transition.guard ? constraintFormulaFromExpression(prior.transition.guard, domains) : null;
        if (!formula) return null;
        priorFormulas.push({term: prior, formula});
    }

    const fullPrefix = andConstraintFormulas(priorFormulas.map(item => item.formula));
    if (!fullPrefix) return null;
    if (constraintFormulasContradict(fullPrefix, currentFormula)) {
        return makePrefixGuardDiagnostic(
            'W_COMBO_GUARD_PREFIX_CONTRADICTS',
            'contradicts prior combo guard terms',
            current,
            firstDecisivePriorTerm(priorFormulas, currentFormula, 'contradicts'),
        );
    }
    if (constraintFormulaImplies(fullPrefix, currentFormula)) {
        return makePrefixGuardDiagnostic(
            'W_COMBO_GUARD_PREFIX_IMPLIED',
            'is implied by prior combo guard terms',
            current,
            firstDecisivePriorTerm(priorFormulas, currentFormula, 'implies'),
        );
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

function simpleConstraint(expr: Expr, domains: Map<string, VariableDomain>): SimpleConstraint | null {
    if (!(expr instanceof BinaryOp)) return null;
    const leftVariable = expr.x instanceof Variable ? expr.x.name : null;
    const rightVariable = expr.y instanceof Variable ? expr.y.name : null;
    const leftNumber = numericLiteralValue(expr.x);
    const rightNumber = numericLiteralValue(expr.y);
    if (leftVariable && rightNumber !== null) {
        return constraintFromParts(leftVariable, domains.get(leftVariable), expr.op, rightNumber);
    }
    if (rightVariable && leftNumber !== null) {
        return constraintFromParts(rightVariable, domains.get(rightVariable), invertComparison(expr.op), leftNumber);
    }
    return null;
}

function constraintFormulaFromExpression(expr: Expr, domains: Map<string, VariableDomain>): ConstraintFormula | null {
    if (expr instanceof BooleanExpr) {
        return expr.value ? trueConstraintFormula() : falseConstraintFormula();
    }
    if (expr instanceof UnaryOp && (expr.op === '!' || expr.op === 'not')) {
        const formula = constraintFormulaFromExpression(expr.x, domains);
        return formula ? negateConstraintFormula(formula) : null;
    }
    if (expr instanceof BinaryOp && (expr.op === '&&' || expr.op === 'and')) {
        const left = constraintFormulaFromExpression(expr.x, domains);
        const right = constraintFormulaFromExpression(expr.y, domains);
        if (!left || !right) return null;
        return andConstraintFormulas([left, right]);
    }
    if (expr instanceof BinaryOp && (expr.op === '||' || expr.op === 'or')) {
        const left = constraintFormulaFromExpression(expr.x, domains);
        const right = constraintFormulaFromExpression(expr.y, domains);
        if (!left || !right) return null;
        return orConstraintFormulas([left, right]);
    }
    const constraint = simpleConstraint(expr, domains);
    if (!constraint) return null;
    return constraintFormulaFromConstraints([constraint]);
}

function trueConstraintFormula(): ConstraintFormula {
    return {alternatives: [{constraints: new Map(), unsat: false}]};
}

function falseConstraintFormula(): ConstraintFormula {
    return {alternatives: []};
}

function constraintFormulaFromConstraints(constraints: SimpleConstraint[]): ConstraintFormula {
    const merged = mergeConstraintSets(constraints.map(constraint => ({
        constraints: new Map([[constraint.variable, cloneConstraint(constraint)]]),
        unsat: false,
    })));
    return constraintFormulaFromSet(merged);
}

function constraintFormulaFromSet(set: ConstraintSet): ConstraintFormula {
    return isConstraintSetSatisfiable(set) ? {alternatives: [set]} : falseConstraintFormula();
}

function andConstraintFormulas(formulas: ConstraintFormula[]): ConstraintFormula | null {
    let result = trueConstraintFormula();
    for (const formula of formulas) {
        const alternatives: ConstraintSet[] = [];
        for (const left of result.alternatives) {
            for (const right of formula.alternatives) {
                const merged = mergeConstraintSets([left, right]);
                if (isConstraintSetSatisfiable(merged)) alternatives.push(merged);
                if (alternatives.length > MAX_CONSTRAINT_FORMULA_ALTERNATIVES) return null;
            }
        }
        result = {alternatives};
    }
    return result;
}

function orConstraintFormulas(formulas: ConstraintFormula[]): ConstraintFormula | null {
    const alternatives: ConstraintSet[] = [];
    for (const formula of formulas) {
        for (const alternative of formula.alternatives) {
            if (!isConstraintSetSatisfiable(alternative)) continue;
            alternatives.push(cloneConstraintSet(alternative));
            if (alternatives.length > MAX_CONSTRAINT_FORMULA_ALTERNATIVES) return null;
        }
    }
    return {alternatives};
}

function negateConstraintFormula(formula: ConstraintFormula): ConstraintFormula | null {
    if (formula.alternatives.length === 0) return trueConstraintFormula();
    const negatedAlternatives = formula.alternatives.map(negateConstraintSet);
    if (negatedAlternatives.some(item => item === null)) return null;
    return andConstraintFormulas(negatedAlternatives as ConstraintFormula[]);
}

function negateConstraintSet(set: ConstraintSet): ConstraintFormula | null {
    if (!isConstraintSetSatisfiable(set)) return trueConstraintFormula();
    const alternatives: ConstraintFormula[] = [];
    for (const constraint of set.constraints.values()) {
        const negated = negateSimpleConstraint(constraint);
        if (!negated) return null;
        alternatives.push(negated);
    }
    return orConstraintFormulas(alternatives);
}

function negateSimpleConstraint(constraint: SimpleConstraint): ConstraintFormula | null {
    const alternatives: ConstraintSet[] = [];
    if (constraint.equal !== undefined) {
        alternatives.push(simpleConstraintSet({
            variable: constraint.variable,
            domain: constraint.domain,
            notEqual: [constraint.equal],
        }));
    } else {
        if (constraint.lower) {
            alternatives.push(simpleConstraintSet({
                variable: constraint.variable,
                domain: constraint.domain,
                upper: {value: constraint.lower.value, inclusive: !constraint.lower.inclusive},
            }));
        }
        if (constraint.upper) {
            alternatives.push(simpleConstraintSet({
                variable: constraint.variable,
                domain: constraint.domain,
                lower: {value: constraint.upper.value, inclusive: !constraint.upper.inclusive},
            }));
        }
        for (const value of constraint.notEqual ?? []) {
            alternatives.push(simpleConstraintSet({
                variable: constraint.variable,
                domain: constraint.domain,
                equal: value,
            }));
        }
    }
    return {alternatives: alternatives.filter(isConstraintSetSatisfiable)};
}

function simpleConstraintSet(constraint: SimpleConstraint): ConstraintSet {
    return mergeConstraintSets([{constraints: new Map([[constraint.variable, cloneConstraint(constraint)]]), unsat: false}]);
}

function mergeConstraintSets(sets: ConstraintSet[]): ConstraintSet {
    const constraints = new Map<string, SimpleConstraint>();
    let unsat = false;
    for (const item of sets) {
        if (item.unsat) unsat = true;
        for (const constraint of item.constraints.values()) {
            const current = constraints.get(constraint.variable);
            if (!current) {
                constraints.set(constraint.variable, normalizeConstraint(cloneConstraint(constraint)));
                continue;
            }
            if (constraintsContradict(current, constraint)) {
                unsat = true;
            }
            const merged = normalizeConstraint(mergeCompatibleConstraints(current, constraint));
            if (constraintImpossible(merged)) unsat = true;
            constraints.set(constraint.variable, merged);
        }
    }
    return {constraints, unsat};
}

function mergeCompatibleConstraints(left: SimpleConstraint, right: SimpleConstraint): SimpleConstraint {
    const domain = left.domain;
    const equal = left.equal !== undefined ? left.equal : right.equal;
    if (equal !== undefined) {
        return normalizeConstraint({
            variable: left.variable,
            domain,
            equal,
            notEqual: mergeNotEqual(left.notEqual, right.notEqual),
        });
    }
    return normalizeConstraint({
        variable: left.variable,
        domain,
        lower: strongestLower(left.lower, right.lower),
        upper: strongestUpper(left.upper, right.upper),
        notEqual: mergeNotEqual(left.notEqual, right.notEqual),
    });
}

function cloneConstraintSet(set: ConstraintSet): ConstraintSet {
    return {
        constraints: new Map(Array.from(set.constraints.entries()).map(([name, constraint]) => [name, cloneConstraint(constraint)])),
        unsat: set.unsat,
    };
}

function cloneConstraint(constraint: SimpleConstraint): SimpleConstraint {
    return {
        variable: constraint.variable,
        domain: constraint.domain,
        lower: constraint.lower ? {...constraint.lower} : undefined,
        upper: constraint.upper ? {...constraint.upper} : undefined,
        equal: constraint.equal,
        notEqual: constraint.notEqual ? [...constraint.notEqual] : undefined,
    };
}

function normalizeConstraint(constraint: SimpleConstraint): SimpleConstraint {
    const normalized = constraint.domain === 'int' ? normalizeIntegerConstraint(constraint) : constraint;
    const singleton = singletonValue(normalized);
    if (singleton !== null) {
        return {
            variable: normalized.variable,
            domain: normalized.domain,
            equal: singleton,
            notEqual: normalized.notEqual ? [...normalized.notEqual] : undefined,
        };
    }
    return normalized;
}

function normalizeIntegerConstraint(constraint: SimpleConstraint): SimpleConstraint {
    return {
        variable: constraint.variable,
        domain: constraint.domain,
        lower: constraint.lower ? integerLowerBound(constraint.lower) : undefined,
        upper: constraint.upper ? integerUpperBound(constraint.upper) : undefined,
        equal: constraint.equal,
        notEqual: constraint.notEqual?.filter(Number.isInteger),
    };
}

function integerLowerBound(bound: Bound): Bound {
    return {
        value: bound.inclusive ? Math.ceil(bound.value) : Math.floor(bound.value) + 1,
        inclusive: true,
    };
}

function integerUpperBound(bound: Bound): Bound {
    return {
        value: bound.inclusive ? Math.floor(bound.value) : Math.ceil(bound.value) - 1,
        inclusive: true,
    };
}

function singletonValue(constraint: SimpleConstraint): number | null {
    if (constraint.equal !== undefined) return constraint.equal;
    if (
        constraint.lower &&
        constraint.upper &&
        constraint.lower.inclusive &&
        constraint.upper.inclusive &&
        constraint.lower.value === constraint.upper.value
    ) {
        return constraint.lower.value;
    }
    return null;
}

function isConstraintSetSatisfiable(set: ConstraintSet): boolean {
    if (set.unsat) return false;
    for (const constraint of set.constraints.values()) {
        if (constraintImpossible(constraint)) return false;
    }
    return true;
}

function constraintImpossible(constraint: SimpleConstraint): boolean {
    if (constraint.domain === 'int' && constraint.equal !== undefined && !Number.isInteger(constraint.equal)) {
        return true;
    }
    const singleton = singletonValue(constraint);
    if (singleton !== null) return constraint.notEqual?.includes(singleton) ?? false;
    if (constraint.lower && constraint.upper) {
        if (constraint.lower.value > constraint.upper.value) return true;
        if (constraint.lower.value === constraint.upper.value && (!constraint.lower.inclusive || !constraint.upper.inclusive)) {
            return true;
        }
    }
    return false;
}

function constraintFormulaImplies(prior: ConstraintFormula, current: ConstraintFormula): boolean {
    const negatedCurrent = negateConstraintFormula(current);
    return negatedCurrent !== null && constraintFormulasContradict(prior, negatedCurrent);
}

function constraintFormulasContradict(left: ConstraintFormula, right: ConstraintFormula): boolean {
    return andConstraintFormulas([left, right])?.alternatives.length === 0;
}

function firstDecisivePriorTerm(
    priorFormulas: Array<{term: ComboTerm; formula: ConstraintFormula}>,
    currentFormula: ConstraintFormula,
    relation: 'implies' | 'contradicts',
): ComboTerm {
    let prefix = trueConstraintFormula();
    for (const item of priorFormulas) {
        const merged = andConstraintFormulas([prefix, item.formula]);
        if (!merged) return item.term;
        prefix = merged;
        if (relation === 'contradicts' && constraintFormulasContradict(prefix, currentFormula)) {
            return item.term;
        }
        if (relation === 'implies' && constraintFormulaImplies(prefix, currentFormula)) {
            return item.term;
        }
    }
    // Unreachable once the caller has already established the prefix relation;
    // keep the nearest prior guard as a defensive fallback.
    return priorFormulas[priorFormulas.length - 1].term;
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

function constraintFromParts(
    variable: string,
    domain: VariableDomain | undefined,
    op: string,
    value: number,
): SimpleConstraint | null {
    if (!domain) return null;
    if (op === '>') return normalizeConstraint({variable, domain, lower: {value, inclusive: false}});
    if (op === '>=') return normalizeConstraint({variable, domain, lower: {value, inclusive: true}});
    if (op === '<') return normalizeConstraint({variable, domain, upper: {value, inclusive: false}});
    if (op === '<=') return normalizeConstraint({variable, domain, upper: {value, inclusive: true}});
    if (op === '==') return normalizeConstraint({variable, domain, equal: value});
    if (op === '!=') return normalizeConstraint({variable, domain, notEqual: [value]});
    return null;
}

function constraintsContradict(left: SimpleConstraint, right: SimpleConstraint): boolean {
    if (left.domain !== right.domain) return false;
    if (left.equal !== undefined) return !valueSatisfies(left.equal, right);
    if (right.equal !== undefined) return !valueSatisfies(right.equal, left);
    return constraintImpossible(mergeCompatibleConstraints(left, right));
}

function valueSatisfies(value: number, constraint: SimpleConstraint): boolean {
    if (constraint.domain === 'int' && !Number.isInteger(value)) return false;
    if (constraint.equal !== undefined && value !== constraint.equal) return false;
    if (constraint.notEqual?.includes(value)) return false;
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

function mergeNotEqual(left: number[] | undefined, right: number[] | undefined): number[] | undefined {
    const values = Array.from(new Set([...(left ?? []), ...(right ?? [])])).sort((a, b) => a - b);
    return values.length > 0 ? values : undefined;
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
