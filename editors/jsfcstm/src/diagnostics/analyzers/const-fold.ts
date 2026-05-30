import {
    BinaryOp,
    BooleanExpr,
    ConditionalOp,
    Float,
    Integer,
    OnStage,
    Operation,
    OperationStatement,
    StateMachine,
    UnaryOp,
} from '../../model/runtime';
import type {ModelDiagnosticJson} from '../inspect';

interface ExactInteger {
    kind: 'exactInteger';
    sign: -1 | 1;
    digits: string;
}

interface FloatNumeric {
    kind: 'float';
    value: number;
}

type ConstNumeric = ExactInteger | FloatNumeric | number;
type ConstValue = boolean | ConstNumeric;
type RuntimeIntegerFactory = (value: string | number) => any;

declare const BigInt: RuntimeIntegerFactory | undefined;

const MAX_JSON_STABLE_INT = 9007199254740991;
const MAX_FOLD_SHIFT_BITS = 1024;
const EPSILON = 1e-9;
const RUNTIME_INTEGER = getRuntimeIntegerFactory();

export function foldNumericExpression(expr: unknown): ConstNumeric | null {
    return publicNumericValue(foldNumericExpressionInternal(expr));
}

function foldNumericExpressionInternal(expr: unknown): ConstNumeric | null {
    if (expr instanceof Integer) {
        return integerLiteralValue(expr);
    }
    if (expr instanceof Float) {
        return makeFloatNumeric(expr.value);
    }
    if (expr instanceof UnaryOp) {
        const value = foldNumericExpressionInternal(expr.x);
        if (value === null) return null;
        if (expr.op === '+') return value;
        if (expr.op === '-') return negateNumeric(value);
        return null;
    }
    if (expr instanceof BinaryOp) {
        const left = foldNumericExpressionInternal(expr.x);
        const right = foldNumericExpressionInternal(expr.y);
        if (left === null || right === null) return null;
        return foldNumericBinary(expr.op, left, right);
    }
    if (expr instanceof ConditionalOp) {
        const condition = foldConditionExpression(expr.cond);
        if (condition === null) return null;
        return foldNumericExpressionInternal(condition ? expr.ifTrue : expr.ifFalse);
    }
    return null;
}

export function foldConditionExpression(expr: unknown): boolean | null {
    if (expr instanceof BooleanExpr) {
        return expr.value;
    }
    if (expr instanceof UnaryOp) {
        if (expr.op !== '!') return null;
        const value = foldConditionExpression(expr.x);
        return value === null ? null : !value;
    }
    if (expr instanceof BinaryOp) {
        if (expr.op === '&&' || expr.op === '||') {
            const left = foldConditionExpression(expr.x);
            const right = foldConditionExpression(expr.y);
            if (left === null || right === null) return null;
            return expr.op === '&&' ? left && right : left || right;
        }
        if (['<', '<=', '>', '>=', '==', '!='].includes(expr.op)) {
            return foldComparison(expr);
        }
        return null;
    }
    if (expr instanceof ConditionalOp) {
        const condition = foldConditionExpression(expr.cond);
        if (condition === null) return null;
        return foldConditionExpression(condition ? expr.ifTrue : expr.ifFalse);
    }
    return null;
}

export function collectConstFoldWarnings(machine: StateMachine | null | undefined): ModelDiagnosticJson[] {
    if (!machine) return [];
    const out: ModelDiagnosticJson[] = [];
    for (const state of machine.allStates) {
        const statePath = state.path.join('.');
        for (const transition of state.transitions) {
            const foldedGuard = transition.guard ? foldConditionExpression(transition.guard) : null;
            if (foldedGuard === true || foldedGuard === false) {
                out.push(guardConstDiagnostic(
                    transition.fromState,
                    transition.toState,
                    transition.sourceKind,
                    transition.targetKind,
                    foldedGuard,
                ));
            }
        }
        out.push(...duringConstAssignDiagnostics(statePath, state.onDurings));
    }
    return out;
}

function foldNumericBinary(op: string, left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    if (['<<', '>>', '&', '^', '|'].includes(op)) {
        return foldBitwise(op, left, right);
    }
    if (op === '+') return foldAdd(left, right);
    if (op === '-') return foldSubtract(left, right);
    if (op === '*') return foldMultiply(left, right);
    if (op === '/') return foldDivide(left, right);
    if (op === '%') return foldModulo(left, right);
    if (op === '**') {
        return foldPower(left, right);
    }
    return null;
}

function foldComparison(expr: BinaryOp): boolean | null {
    const leftNumeric = foldNumericExpressionInternal(expr.x);
    const rightNumeric = foldNumericExpressionInternal(expr.y);
    if (leftNumeric !== null && rightNumeric !== null) {
        return compareValues(expr.op, leftNumeric, rightNumeric);
    }
    if (expr.op !== '==' && expr.op !== '!=') return null;
    const leftBool = foldConditionExpression(expr.x);
    const rightBool = foldConditionExpression(expr.y);
    if (leftBool === null || rightBool === null) return null;
    return expr.op === '==' ? leftBool === rightBool : leftBool !== rightBool;
}

function compareValues(op: string, left: ConstNumeric, right: ConstNumeric): boolean | null {
    if (op === '<') return numericCompare(left, right, (value) => value < 0);
    if (op === '<=') return numericCompare(left, right, (value) => value <= 0);
    if (op === '>') return numericCompare(left, right, (value) => value > 0);
    if (op === '>=') return numericCompare(left, right, (value) => value >= 0);
    if (op === '==') return numericEqual(left, right);
    if (op === '!=') {
        const equal = numericEqual(left, right);
        return equal === null ? null : !equal;
    }
    return null;
}

function nearlyEqual(left: number, right: number): boolean {
    if (left === right) return true;
    return Math.abs(left - right) <= EPSILON * Math.max(Math.abs(left), Math.abs(right));
}

function numericEqual(left: ConstNumeric, right: ConstNumeric): boolean | null {
    const leftNumber = constNumericToNumber(left);
    const rightNumber = constNumericToNumber(right);
    if (leftNumber !== null && rightNumber !== null) return nearlyEqual(leftNumber, rightNumber);
    if (isExactInteger(left) && isExactInteger(right)) return compareExactIntegers(left, right) === 0;
    const leftInt = toExactIntegerIfInteger(left);
    const rightInt = toExactIntegerIfInteger(right);
    return leftInt !== null && rightInt !== null ? compareExactIntegers(leftInt, rightInt) === 0 : null;
}

function duringConstAssignDiagnostics(statePath: string, actions: OnStage[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const action of actions) {
        if (action.isAbstract || action.isRef || action.aspect !== undefined) continue;
        for (const stmt of action.operations) {
            out.push(...duringStmtConstAssignDiagnostics(statePath, stmt));
        }
    }
    return out;
}

function duringStmtConstAssignDiagnostics(statePath: string, stmt: OperationStatement): ModelDiagnosticJson[] {
    if (!(stmt instanceof Operation)) return [];
    const value = jsonStableNumber(foldNumericExpressionInternal(stmt.expr));
    if (value === null) return [];
    return [{
        code: 'W_DURING_CONST_ASSIGN',
        severity: 'warning',
        message: `During action in ${JSON.stringify(statePath)} assigns ${JSON.stringify(stmt.varName)} to the same constant value every cycle.`,
        span: null,
        refs: {
            state_path: statePath,
            var_name: stmt.varName,
            value,
        },
    }];
}

function guardConstDiagnostic(
    fromState: string,
    toState: string,
    sourceKind: 'init' | 'state',
    targetKind: 'state' | 'exit',
    value: boolean,
): ModelDiagnosticJson {
    const label = value ? 'true' : 'false';
    const sourceLabel = transitionSourceLabel(fromState, sourceKind);
    const targetLabel = transitionTargetLabel(toState, targetKind);
    return {
        code: value ? 'W_GUARD_CONST_TRUE' : 'W_GUARD_CONST_FALSE',
        severity: 'warning',
        message: `Transition ${JSON.stringify(sourceLabel)} -> ${JSON.stringify(targetLabel)} has a guard that is statically ${label}.`,
        span: null,
        refs: {transition_span: null, folded_value: value},
    };
}

function transitionSourceLabel(value: string, sourceKind: 'init' | 'state'): string {
    return sourceKind === 'init' ? '[*]' : value;
}

function transitionTargetLabel(value: string, targetKind: 'state' | 'exit'): string {
    return targetKind === 'exit' ? '[*]' : value;
}

function jsonStableNumber(value: ConstValue | null): number | null {
    if (value === null || typeof value === 'boolean') return null;
    const numberValue = constNumericToNumber(value);
    if (numberValue === null) return null;
    value = numberValue;
    if (isExactInteger(value)) return null;
    if (!Number.isFinite(value)) return null;
    if (Math.trunc(value) === value && Math.abs(value) > MAX_JSON_STABLE_INT) return null;
    return value;
}

function stableNumericResult(value: number, keepFloat: boolean): ConstNumeric | null {
    if (!Number.isFinite(value)) return null;
    if (Math.trunc(value) === value && Math.abs(value) > MAX_JSON_STABLE_INT) return null;
    if (keepFloat && Math.trunc(value) === value) return makeFloatNumeric(value);
    return value;
}

function publicNumericValue(value: ConstNumeric | null): ConstNumeric | null {
    if (value === null) return null;
    if (isFloatNumeric(value)) return value.value;
    return value;
}

function integerLiteralValue(expr: Integer): ExactInteger | number | null {
    const raw = expr.text.trim();
    let digits: string | null = null;
    if (/^\d+$/.test(raw)) {
        digits = normalizeDecimalDigits(raw);
    } else if (/^0[xX][0-9a-fA-F]+$/.test(raw)) {
        digits = convertRadixDigitsToDecimal(raw.slice(2), 16);
    } else if (/^0[bB][01]+$/.test(raw)) {
        digits = convertRadixDigitsToDecimal(raw.slice(2), 2);
    }
    if (digits !== null) {
        const exact = makeExactInteger(1, digits);
        const safe = exactIntegerToSafeNumber(exact);
        return safe === null ? exact : safe;
    }
    if (Number.isSafeInteger(expr.value)) {
        return expr.value;
    }
    return null;
}

function negateNumeric(value: ConstNumeric): ConstNumeric {
    if (isExactInteger(value)) return makeExactInteger((value.sign * -1) as -1 | 1, value.digits);
    if (isFloatNumeric(value)) return makeFloatNumeric(-value.value);
    return -value;
}

function toSafeIntegerNumber(value: ConstNumeric): number | null {
    if (typeof value === 'number' && Number.isSafeInteger(value)) return value;
    if (isExactInteger(value)) return exactIntegerToSafeNumber(value);
    return null;
}

function toSafeNumber(value: ConstNumeric): number | null {
    if (isFloatNumeric(value)) {
        return Number.isFinite(value.value) ? value.value : null;
    }
    if (typeof value === 'number') {
        return Number.isFinite(value) ? value : null;
    }
    return exactIntegerToSafeNumber(value);
}

function getRuntimeIntegerFactory(): RuntimeIntegerFactory | null {
    return typeof BigInt === 'function' ? BigInt : null;
}

function foldAdd(left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const leftNumber = toSafeNumber(left);
    const rightNumber = toSafeNumber(right);
    if (leftNumber === null || rightNumber === null) return null;
    return stableNumericResult(leftNumber + rightNumber, hasFloatNumericOperand(left, right));
}

function foldSubtract(left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const leftNumber = toSafeNumber(left);
    const rightNumber = toSafeNumber(right);
    if (leftNumber === null || rightNumber === null) return null;
    return stableNumericResult(leftNumber - rightNumber, hasFloatNumericOperand(left, right));
}

function foldMultiply(left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const leftNumber = toSafeNumber(left);
    const rightNumber = toSafeNumber(right);
    if (leftNumber === null || rightNumber === null) return null;
    return stableNumericResult(leftNumber * rightNumber, hasFloatNumericOperand(left, right));
}

function foldDivide(left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const rightNumber = toSafeNumber(right);
    if (rightNumber === null || rightNumber === 0) return null;
    const leftNumber = toSafeNumber(left);
    if (leftNumber === null) return null;
    return stableNumericResult(leftNumber / rightNumber, true);
}

function foldModulo(left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const leftInt = toRuntimeInteger(left);
    const rightInt = toRuntimeInteger(right);
    if (leftInt !== null && rightInt !== null && RUNTIME_INTEGER !== null) {
        const zero = RUNTIME_INTEGER(0);
        if (rightInt === zero) return null;
        let remainder = leftInt % rightInt;
        if (remainder !== zero && (remainder > zero) !== (rightInt > zero)) {
            remainder += rightInt;
        }
        return runtimeIntegerToConst(remainder);
    }

    const rightNumber = toSafeNumber(right);
    if (rightNumber === null || rightNumber === 0) return null;
    const leftNumber = toSafeNumber(left);
    if (leftNumber === null) return null;
    const result = leftNumber - Math.floor(leftNumber / rightNumber) * rightNumber;
    return stableNumericResult(Object.is(result, -0) ? 0 : result, hasFloatNumericOperand(left, right));
}

function foldPower(left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const leftNumber = toSafeNumber(left);
    const rightNumber = toSafeNumber(right);
    if (leftNumber === null || rightNumber === null) return null;
    if (leftNumber === 0 && rightNumber < 0) return null;
    const result = leftNumber ** rightNumber;
    return stableNumericResult(result, hasFloatNumericOperand(left, right));
}

function foldBitwise(op: string, left: ConstNumeric, right: ConstNumeric): ConstNumeric | null {
    const leftInt = toRuntimeInteger(left);
    const rightInt = toRuntimeInteger(right);
    if (leftInt === null || rightInt === null || RUNTIME_INTEGER === null) return null;
    if ((op === '<<' || op === '>>') && rightInt < RUNTIME_INTEGER(0)) return null;
    if ((op === '<<' || op === '>>') && rightInt > RUNTIME_INTEGER(MAX_FOLD_SHIFT_BITS)) return null;
    if (op === '<<') return runtimeIntegerToConst(leftInt << rightInt);
    if (op === '>>') return runtimeIntegerToConst(leftInt >> rightInt);
    if (op === '&') return runtimeIntegerToConst(leftInt & rightInt);
    if (op === '^') return runtimeIntegerToConst(leftInt ^ rightInt);
    return runtimeIntegerToConst(leftInt | rightInt);
}

function isExactInteger(value: ConstNumeric): value is ExactInteger {
    return typeof value === 'object' && value !== null && value.kind === 'exactInteger';
}

function isFloatNumeric(value: ConstNumeric): value is FloatNumeric {
    return typeof value === 'object' && value !== null && value.kind === 'float';
}

function makeFloatNumeric(value: number): FloatNumeric {
    return {kind: 'float', value};
}

function hasFloatNumericOperand(left: ConstNumeric, right: ConstNumeric): boolean {
    return isFloatNumeric(left) || isFloatNumeric(right);
}

function makeExactInteger(sign: -1 | 1, digits: string): ExactInteger {
    const normalized = normalizeDecimalDigits(digits);
    return {
        kind: 'exactInteger',
        sign: normalized === '0' ? 1 : sign,
        digits: normalized,
    };
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

function exactIntegerToSafeNumber(value: ExactInteger): number | null {
    const signed = value.sign < 0 ? `-${value.digits}` : value.digits;
    const numberValue = Number(signed);
    return Number.isSafeInteger(numberValue) ? numberValue : null;
}

function exactIntegerToSignedDecimal(value: ExactInteger): string {
    return value.sign < 0 ? `-${value.digits}` : value.digits;
}

function signedDecimalToConstNumeric(raw: string): ConstNumeric | null {
    if (!/^-?\d+$/.test(raw)) return null;
    const sign = raw.startsWith('-') ? -1 : 1;
    const digits = sign < 0 ? raw.slice(1) : raw;
    const exact = makeExactInteger(sign, digits);
    const safe = exactIntegerToSafeNumber(exact);
    return safe === null ? exact : safe;
}

function toRuntimeInteger(value: ConstNumeric): any | null {
    if (RUNTIME_INTEGER === null) return null;
    if (isExactInteger(value)) return RUNTIME_INTEGER(exactIntegerToSignedDecimal(value));
    if (typeof value === 'number' && Number.isSafeInteger(value)) return RUNTIME_INTEGER(value);
    return null;
}

function runtimeIntegerToConst(value: any): ConstNumeric | null {
    return signedDecimalToConstNumeric(String(value));
}

function toExactIntegerIfInteger(value: ConstNumeric): ExactInteger | null {
    if (isExactInteger(value)) return value;
    if (isFloatNumeric(value)) return null;
    if (!Number.isSafeInteger(value)) return null;
    const sign = value < 0 ? -1 : 1;
    return makeExactInteger(sign, String(Math.abs(value)));
}

function constNumericToNumber(value: ConstNumeric): number | null {
    if (isFloatNumeric(value)) return value.value;
    if (typeof value === 'number') return value;
    return exactIntegerToSafeNumber(value);
}

function compareExactIntegers(left: ExactInteger, right: ExactInteger): number {
    if (left.sign !== right.sign) return left.sign < right.sign ? -1 : 1;
    if (left.digits === right.digits) return 0;
    if (left.digits.length !== right.digits.length) {
        const order = left.digits.length < right.digits.length ? -1 : 1;
        return left.sign > 0 ? order : -order;
    }
    const lexical = left.digits < right.digits ? -1 : 1;
    return left.sign > 0 ? lexical : -lexical;
}

function numericCompare(
    left: ConstNumeric,
    right: ConstNumeric,
    predicate: (order: number) => boolean
): boolean | null {
    if (typeof left === 'number' && typeof right === 'number') {
        if (!Number.isFinite(left) || !Number.isFinite(right)) return null;
        return predicate(left < right ? -1 : left > right ? 1 : 0);
    }
    const leftNumber = constNumericToNumber(left);
    const rightNumber = constNumericToNumber(right);
    if (leftNumber !== null && rightNumber !== null) {
        if (!Number.isFinite(leftNumber) || !Number.isFinite(rightNumber)) return null;
        return predicate(leftNumber < rightNumber ? -1 : leftNumber > rightNumber ? 1 : 0);
    }
    const leftInt = toExactIntegerIfInteger(left);
    const rightInt = toExactIntegerIfInteger(right);
    return leftInt !== null && rightInt !== null
        ? predicate(compareExactIntegers(leftInt, rightInt))
        : null;
}
