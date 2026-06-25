import {
    BinaryOp,
    BooleanExpr,
    ConditionalOp,
    Float,
    IfBlock,
    Integer,
    Operation,
    OperationStatement,
    StateMachine,
    UFunc,
    UnaryOp,
    Variable,
    type Expr,
    type OnAspect,
    type OnStage,
} from '../../model/runtime';
import {exprText, type ModelDiagnosticJson} from '../inspect';
import {foldNumericExpression} from './const-fold';

const TARGET_FAMILY = 'c_family';
const TARGET_TEMPLATES = ['c', 'c_poll', 'cpp', 'cpp_poll'];
const TARGET_BITS = 64;
const MIN_SIGNED_INT64_TEXT = '-9223372036854775808';
const MAX_SIGNED_INT64_TEXT = '9223372036854775807';
const BITWISE_OPERATORS = new Set(['&', '^', '|', '<<', '>>']);
const ZERO_OPERATORS = new Set(['/', '%']);
const SHIFT_OPERATORS = new Set(['<<', '>>']);
const C_FAMILY_INTEGER_UFUNCS = new Set(['ceil', 'floor', 'int', 'round', 'sign', 'trunc']);
const C_FAMILY_CONDITION_OPERATORS = new Set([
    '&&',
    '||',
    '=>',
    'xor',
    'iff',
    '==',
    '!=',
    '<',
    '<=',
    '>',
    '>=',
]);

const RUNTIME_NOTES: Record<string, string> = {
    W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE:
        'C/C++ deployment profile risk: the default C-family templates use '
        + 'PYFCSTM_GENERATED_INT64, while Python generated runtimes may not have '
        + 'the same fixed-width integer carrying risk.',
    W_NUMERIC_CONSTANT_DIVISION_BY_ZERO:
        'C/C++ deployment profile risk: generated C/C++ code needs an explicit '
        + 'division-by-zero or modulo-by-zero policy, while Python generated '
        + 'runtimes use different exception semantics.',
    W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE:
        'C/C++ deployment profile risk: the default C-family integer width is '
        + '64 bits, while Python generated runtimes may not have the same '
        + 'fixed-width shift risk.',
    W_NUMERIC_FLOAT_BITWISE:
        'C/C++ integer-operation profile risk: bitwise and shift operators are '
        + 'integer operations in the generated C-family templates; Python '
        + 'generated runtimes may fail for a different reason.',
};

interface ExpressionContext {
    expr: Expr;
    context: 'var_initializer' | 'guard' | 'transition_effect' | 'lifecycle_action';
    statementKind?: 'operation_assignment';
    varName?: string;
}

interface SignedIntegerLiteral {
    text: string;
    decimalText: string;
}

type NumericType = 'int' | 'float' | 'unknown';
type NumericTypeSource = 'literal' | 'declared_var' | 'local_expression';

/**
 * Collect C/C++ deployment-profile numeric warnings for a model.
 */
export function collectNumericWarnings(machine: StateMachine | null | undefined): ModelDiagnosticJson[] {
    if (!machine) return [];
    const varTypes = variableTypes(machine);
    const diagnostics: ModelDiagnosticJson[] = [];
    for (const context of expressionContexts(machine)) {
        diagnostics.push(...diagnosticsForExpression(context, varTypes));
    }
    return diagnostics;
}

function variableTypes(machine: StateMachine): Record<string, 'int' | 'float'> {
    const out: Record<string, 'int' | 'float'> = {};
    for (const [name, definition] of Object.entries(machine.defines)) {
        out[name] = definition.type;
    }
    return out;
}

function diagnosticsForExpression(
    context: ExpressionContext,
    varTypes: Record<string, 'int' | 'float'>,
): ModelDiagnosticJson[] {
    const diagnostics: ModelDiagnosticJson[] = [];
    const signedLiteralChildren = signedLiteralChildIds(context.expr);
    for (const expr of walkExpressions(context.expr)) {
        if (!signedLiteralChildren.has(expr)) {
            diagnostics.push(...literalRangeDiagnostic(context, expr));
        }
        diagnostics.push(...constantZeroDivisionDiagnostic(context, expr));
        diagnostics.push(...shiftCountDiagnostic(context, expr));
        diagnostics.push(...floatBitwiseDiagnostic(context, expr, varTypes));
    }
    return diagnostics;
}

function* expressionContexts(machine: StateMachine): Generator<ExpressionContext, void, void> {
    for (const [varName, definition] of Object.entries(machine.defines)) {
        yield {
            expr: definition.init,
            context: 'var_initializer',
            varName,
        };
    }

    for (const state of machine.allStates) {
        for (const transition of state.transitions) {
            if (transition.guard) {
                yield {
                    expr: transition.guard,
                    context: 'guard',
                };
            }
            for (const statement of transition.effects) {
                yield* statementExpressionContexts(statement, 'transition_effect');
            }
        }
        for (const action of concreteActions([
            ...state.onEnters,
            ...state.onDurings,
            ...state.onExits,
            ...state.onDuringAspects,
        ])) {
            for (const statement of action.operations) {
                yield* statementExpressionContexts(statement, 'lifecycle_action');
            }
        }
    }
}

function* concreteActions(actions: Array<OnStage | OnAspect>): Generator<OnStage | OnAspect, void, void> {
    for (const action of actions) {
        if (action.isAbstract || action.isRef) continue;
        yield action;
    }
}

function* statementExpressionContexts(
    statement: OperationStatement,
    context: ExpressionContext['context'],
): Generator<ExpressionContext, void, void> {
    if (statement instanceof Operation) {
        yield {
            expr: statement.expr,
            context,
            statementKind: 'operation_assignment',
            varName: statement.varName,
        };
        return;
    }
    if (statement instanceof IfBlock) {
        for (const branch of statement.branches) {
            if (branch.condition) {
                yield {
                    expr: branch.condition,
                    context,
                };
            }
            for (const inner of branch.statements) {
                yield* statementExpressionContexts(inner, context);
            }
        }
    }
}

function* walkExpressions(expr: Expr): Generator<Expr, void, void> {
    yield expr;
    if (expr instanceof UnaryOp) {
        yield* walkExpressions(expr.x);
    } else if (expr instanceof BinaryOp) {
        yield* walkExpressions(expr.x);
        yield* walkExpressions(expr.y);
    } else if (expr instanceof ConditionalOp) {
        yield* walkExpressions(expr.cond);
        yield* walkExpressions(expr.ifTrue);
        yield* walkExpressions(expr.ifFalse);
    } else if (expr instanceof UFunc) {
        yield* walkExpressions(expr.x);
    }
}

function signedLiteralChildIds(expr: Expr): Set<Expr> {
    const out = new Set<Expr>();
    for (const item of walkExpressions(expr)) {
        if (item instanceof UnaryOp && (item.op === '+' || item.op === '-') && item.x instanceof Integer) {
            out.add(item.x);
        }
    }
    return out;
}

function literalRangeDiagnostic(context: ExpressionContext, expr: Expr): ModelDiagnosticJson[] {
    const literal = signedIntegerLiteral(expr);
    if (!literal || isSignedInt64Literal(literal.decimalText)) return [];
    const refs = baseRefs('W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE', context, exprText(expr));
    refs.literal_text = literal.text;
    refs.target_bits = TARGET_BITS;
    refs.signed = true;
    refs.min_value_text = MIN_SIGNED_INT64_TEXT;
    refs.max_value_text = MAX_SIGNED_INT64_TEXT;
    if (context.varName) {
        refs.var_name = context.varName;
    }
    return [diagnostic(
        'W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE',
        `C/C++ default deployment profile risk: integer literal ${literal.text} is outside the `
            + `PYFCSTM_GENERATED_INT64 range [${MIN_SIGNED_INT64_TEXT}, ${MAX_SIGNED_INT64_TEXT}]; `
            + 'Python generated runtimes may not have the same fixed-width risk.',
        refs,
    )];
}

function constantZeroDivisionDiagnostic(context: ExpressionContext, expr: Expr): ModelDiagnosticJson[] {
    if (!(expr instanceof BinaryOp) || !ZERO_OPERATORS.has(expr.op)) return [];
    const rhsValue = foldNumericExpression(expr.y);
    if (rhsValue !== 0) return [];
    const refs = baseRefs('W_NUMERIC_CONSTANT_DIVISION_BY_ZERO', context, exprText(expr));
    refs.operator = expr.op;
    refs.rhs_text = exprText(expr.y) ?? '';
    return [diagnostic(
        'W_NUMERIC_CONSTANT_DIVISION_BY_ZERO',
        `C/C++ default deployment profile risk: the RHS of operator ${JSON.stringify(expr.op)} `
            + 'folds to 0; generated C/C++ code needs an explicit failure policy, '
            + 'while Python runtime exception semantics differ.',
        refs,
    )];
}

function shiftCountDiagnostic(context: ExpressionContext, expr: Expr): ModelDiagnosticJson[] {
    if (!(expr instanceof BinaryOp) || !SHIFT_OPERATORS.has(expr.op)) return [];
    const rhsValue = foldNumericExpression(expr.y);
    if (
        typeof rhsValue !== 'number'
        || !Number.isFinite(rhsValue)
        || !(rhsValue < 0 || rhsValue >= TARGET_BITS)
    ) {
        return [];
    }
    const refs = baseRefs('W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE', context, exprText(expr));
    refs.operator = expr.op;
    refs.target_bits = TARGET_BITS;
    refs.shift_count_text = numberText(rhsValue);
    return [diagnostic(
        'W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE',
        `C/C++ default deployment profile risk: the shift count of operator ${JSON.stringify(expr.op)} `
            + `folds to ${numberText(rhsValue)}, outside 0 <= count < ${TARGET_BITS}; `
            + 'Python generated runtimes do not represent the same fixed-width shift contract.',
        refs,
    )];
}

function floatBitwiseDiagnostic(
    context: ExpressionContext,
    expr: Expr,
    varTypes: Record<string, 'int' | 'float'>,
): ModelDiagnosticJson[] {
    if (!(expr instanceof BinaryOp) || !BITWISE_OPERATORS.has(expr.op)) return [];
    const left = inferNumericType(expr.x, varTypes);
    const right = inferNumericType(expr.y, varTypes);
    if (left[0] !== 'float' && right[0] !== 'float') return [];
    const refs = baseRefs('W_NUMERIC_FLOAT_BITWISE', context, exprText(expr));
    refs.operator = expr.op;
    refs.operand_types = [left[0], right[0]];
    refs.operand_type_sources = [left[1], right[1]];
    return [diagnostic(
        'W_NUMERIC_FLOAT_BITWISE',
        `C/C++ default deployment profile risk: a float-shaped operand participates in integer `
            + `bitwise or shift operator ${JSON.stringify(expr.op)}; C-family templates generate `
            + 'integer operations, while Python runtime failures have different semantics.',
        refs,
    )];
}

function inferNumericType(
    expr: Expr,
    varTypes: Record<string, 'int' | 'float'>,
): [NumericType, NumericTypeSource] {
    if (expr instanceof BooleanExpr || expr instanceof Integer) {
        return ['int', 'literal'];
    }
    if (expr instanceof Float) {
        return ['float', 'literal'];
    }
    if (expr instanceof Variable) {
        const declared = varTypes[expr.name];
        if (declared === 'float') return ['float', 'declared_var'];
        if (declared === 'int') return ['int', 'declared_var'];
        return ['unknown', 'declared_var'];
    }
    if (expr instanceof UnaryOp) {
        const inner = inferNumericType(expr.x, varTypes);
        return inner[0] === 'int' || inner[0] === 'float' ? inner : ['unknown', 'local_expression'];
    }
    if (expr instanceof UFunc) {
        if (C_FAMILY_INTEGER_UFUNCS.has(expr.func)) {
            return ['int', 'local_expression'];
        }
        if (expr.func === 'abs') {
            const inner = inferNumericType(expr.x, varTypes);
            return inner[0] === 'int' || inner[0] === 'float'
                ? [inner[0], 'local_expression']
                : ['unknown', 'local_expression'];
        }
        return ['float', 'local_expression'];
    }
    if (expr instanceof BinaryOp) {
        if (BITWISE_OPERATORS.has(expr.op) || C_FAMILY_CONDITION_OPERATORS.has(expr.op)) {
            return ['int', 'local_expression'];
        }
        if (expr.op === '/') {
            return ['float', 'local_expression'];
        }
        const left = inferNumericType(expr.x, varTypes);
        const right = inferNumericType(expr.y, varTypes);
        return [mergeNumericTypes(left[0], right[0]), 'local_expression'];
    }
    if (expr instanceof ConditionalOp) {
        const ifTrue = inferNumericType(expr.ifTrue, varTypes);
        const ifFalse = inferNumericType(expr.ifFalse, varTypes);
        return [mergeNumericTypes(ifTrue[0], ifFalse[0]), 'local_expression'];
    }
    return ['unknown', 'local_expression'];
}

function mergeNumericTypes(typeA: NumericType, typeB: NumericType): NumericType {
    if (typeA === 'float' || typeB === 'float') return 'float';
    if (typeA === 'int' && typeB === 'int') return 'int';
    return 'unknown';
}

function signedIntegerLiteral(expr: Expr): SignedIntegerLiteral | null {
    if (expr instanceof Integer) {
        const digits = unsignedIntegerDecimalText(expr.text);
        return digits === null ? null : {text: expr.text.trim(), decimalText: digits};
    }
    if (expr instanceof UnaryOp && (expr.op === '+' || expr.op === '-') && expr.x instanceof Integer) {
        const digits = unsignedIntegerDecimalText(expr.x.text);
        if (digits === null) return null;
        const sign = expr.op === '-' ? '-' : '+';
        return {
            text: `${sign}${expr.x.text.trim()}`,
            decimalText: expr.op === '-' && digits !== '0' ? `-${digits}` : digits,
        };
    }
    return null;
}

function unsignedIntegerDecimalText(rawText: string): string | null {
    const raw = rawText.trim();
    if (/^\d+$/.test(raw)) {
        return normalizeDecimalDigits(raw);
    }
    if (/^0[xX][0-9a-fA-F]+$/.test(raw)) {
        return convertRadixDigitsToDecimal(raw.slice(2), 16);
    }
    if (/^0[bB][01]+$/.test(raw)) {
        return convertRadixDigitsToDecimal(raw.slice(2), 2);
    }
    return null;
}

function isSignedInt64Literal(signedDecimalText: string): boolean {
    const normalized = normalizeSignedDecimal(signedDecimalText);
    if (normalized.startsWith('-')) {
        return compareUnsignedDecimal(normalized.slice(1), MIN_SIGNED_INT64_TEXT.slice(1)) <= 0;
    }
    return compareUnsignedDecimal(normalized, MAX_SIGNED_INT64_TEXT) <= 0;
}

function normalizeSignedDecimal(raw: string): string {
    if (raw.startsWith('-')) {
        const digits = normalizeDecimalDigits(raw.slice(1));
        return digits === '0' ? '0' : `-${digits}`;
    }
    if (raw.startsWith('+')) {
        return normalizeDecimalDigits(raw.slice(1));
    }
    return normalizeDecimalDigits(raw);
}

function normalizeDecimalDigits(raw: string): string {
    const normalized = raw.replace(/^0+/, '');
    return normalized.length > 0 ? normalized : '0';
}

function compareUnsignedDecimal(left: string, right: string): number {
    const leftNormalized = normalizeDecimalDigits(left);
    const rightNormalized = normalizeDecimalDigits(right);
    if (leftNormalized.length !== rightNormalized.length) {
        return leftNormalized.length < rightNormalized.length ? -1 : 1;
    }
    if (leftNormalized === rightNormalized) return 0;
    return leftNormalized < rightNormalized ? -1 : 1;
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
    return normalizeDecimalDigits(value);
}

function baseRefs(
    code: keyof typeof RUNTIME_NOTES,
    context: ExpressionContext,
    renderedExpr: string | null,
): Record<string, unknown> {
    const refs: Record<string, unknown> = {
        target_family: TARGET_FAMILY,
        target_templates: [...TARGET_TEMPLATES],
        runtime_note: RUNTIME_NOTES[code],
        context: context.context,
        expr_text: renderedExpr ?? '',
    };
    if (context.statementKind) {
        refs.statement_kind = context.statementKind;
    }
    return refs;
}

function diagnostic(code: string, message: string, refs: Record<string, unknown>): ModelDiagnosticJson {
    return {
        code,
        severity: 'warning',
        message,
        span: null,
        refs,
    };
}

function numberText(value: number): string {
    return Number.isInteger(value) ? String(Math.trunc(value)) : String(value);
}
