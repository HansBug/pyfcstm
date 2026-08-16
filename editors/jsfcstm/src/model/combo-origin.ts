import type {
    FcstmAstExpression,
    FcstmAstIfStatement,
    FcstmAstOperationStatement,
    FcstmAstLiteralExpression,
} from '../ast';

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
    if (/^0[xX][0-9a-fA-F]+$/.test(raw)) return convertRadixDigitsToDecimal(raw.slice(2), 16);
    if (/^0[bB][01]+$/.test(raw)) return convertRadixDigitsToDecimal(raw.slice(2), 2);
    const value = Number(raw);
    if (expression.pyNodeType === 'Float') {
        return Number.isInteger(value) ? `${value}.0` : String(value);
    }
    return String(Math.trunc(value));
}

function expressionPrecedence(expression: FcstmAstExpression): number | null {
    if (expression.expressionKind === 'binary') {
        return EXPR_PRECEDENCE[canonicalBinaryOperator(expression.op)] ?? null;
    }
    if (expression.expressionKind === 'conditional') return EXPR_PRECEDENCE['?:'];
    if (expression.expressionKind === 'unary') {
        return EXPR_PRECEDENCE[unaryPrecedenceKey(expression.op)] ?? null;
    }
    return null;
}

function canonicalExpressionText(expression: FcstmAstExpression | null | undefined): string | null {
    if (!expression) return null;
    switch (expression.expressionKind) {
        case 'literal':
            return expression.literalType === 'boolean'
                ? expression.valueText.toLowerCase()
                : numericAstText(expression);
        case 'identifier':
        case 'mathConst':
            return expression.name;
        case 'parenthesized':
            return canonicalExpressionText(expression.expression);
        case 'function': {
            const argument = canonicalExpressionText(expression.argument);
            return argument === null ? null : `${expression.functionName}(${argument})`;
        }
        case 'unary': {
            const op = canonicalUnaryOperator(expression.op);
            const myPrecedence = EXPR_PRECEDENCE[unaryPrecedenceKey(expression.op)];
            let value = canonicalExpressionText(expression.operand);
            if (value === null) return null;
            const valuePrecedence = expressionPrecedence(expression.operand);
            if (valuePrecedence !== null && valuePrecedence <= myPrecedence) value = `(${value})`;
            return `${op}${value}`;
        }
        case 'binary': {
            const op = canonicalBinaryOperator(expression.op);
            const myPrecedence = EXPR_PRECEDENCE[op];
            let left = canonicalExpressionText(expression.left);
            let right = canonicalExpressionText(expression.right);
            if (left === null || right === null) return null;
            const leftPrecedence = expressionPrecedence(expression.left);
            if (leftPrecedence !== null && leftPrecedence < myPrecedence) left = `(${left})`;
            const rightPrecedence = expressionPrecedence(expression.right);
            if (rightPrecedence !== null && rightPrecedence <= myPrecedence) right = `(${right})`;
            return `${left} ${op} ${right}`;
        }
        case 'conditional': {
            const condition = canonicalExpressionText(expression.condition);
            let whenTrue = canonicalExpressionText(expression.whenTrue);
            let whenFalse = canonicalExpressionText(expression.whenFalse);
            if (condition === null || whenTrue === null || whenFalse === null) return null;
            if ((expressionPrecedence(expression.whenTrue) ?? 99) <= EXPR_PRECEDENCE['?:']) whenTrue = `(${whenTrue})`;
            if ((expressionPrecedence(expression.whenFalse) ?? 99) <= EXPR_PRECEDENCE['?:']) whenFalse = `(${whenFalse})`;
            return `(${condition}) ? ${whenTrue} : ${whenFalse}`;
        }
    }
}

function indentLines(value: string): string {
    return value.split('\n').map(line => `    ${line}`).join('\n');
}

function canonicalOperationStatement(statement: FcstmAstOperationStatement): string {
    if (statement.kind === 'assignmentStatement') {
        const expression = canonicalExpressionText(statement.expression);
        return `${statement.targetName} = ${expression ?? statement.expression.text};`;
    }
    if (statement.kind !== 'ifStatement') return statement.text.replace(/\s+/g, ' ').trim();

    const ifStatement = statement as FcstmAstIfStatement;
    if (ifStatement.branches.length === 0) return statement.text.replace(/\s+/g, ' ').trim();
    const lines: string[] = [];
    ifStatement.branches.forEach((branch, index) => {
        if (index === 0) {
            const condition = canonicalExpressionText(branch.condition) ?? branch.text;
            lines.push(`if [${condition}] {`);
        } else if (branch.condition === null) {
            lines.push('} else {');
        } else {
            const condition = canonicalExpressionText(branch.condition) ?? branch.text;
            lines.push(`} else if [${condition}] {`);
        }
        for (const child of branch.statements) lines.push(...indentLines(canonicalOperationStatement(child)).split('\n'));
    });
    lines.push('}');
    return lines.join('\n');
}

/**
 * Keep combo provenance stable across the AST and runtime model layers.
 * pyfcstm renders assignment nodes with spaces around the assignment operator;
 * parser source text does not promise that formatting.
 */
export function canonicalComboEffectSignature(
    statements: FcstmAstOperationStatement[],
): string[] {
    return statements.map(canonicalOperationStatement);
}
