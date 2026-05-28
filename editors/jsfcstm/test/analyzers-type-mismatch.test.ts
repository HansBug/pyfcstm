/**
 * Direct unit tests for ``inferExpressionCategory`` and ``checkExpression``
 * (the building blocks behind ``E_TYPE_MISMATCH``).
 *
 * Why bypass the grammar?
 * -----------------------
 * pyfcstm's grammar already separates ``num_expression`` from
 * ``cond_expression``, so most type-mismatch DSL snippets become grammar
 * parse errors before reaching the semantic layer. That makes
 * ``E_TYPE_MISMATCH`` effectively a safety net for cases where the
 * grammar relaxes in the future (or where a third-party AST builder
 * skips the grammar). To prove the safety net works we drive the type
 * checker with synthetic AST nodes constructed in TypeScript — every
 * field shape mirrors what ``buildExpression`` would produce, only the
 * source-text-derived ranges and ``.text`` strings are stubbed.
 */
import assert from 'node:assert/strict';

import {editorModule} from './support';

const {inferExpressionCategory, checkExpression} = editorModule;

type Expr = Parameters<typeof inferExpressionCategory>[0];

const STUB_RANGE = {
    start: {line: 0, character: 0},
    end: {line: 0, character: 1},
};

function mkLiteral(literalType: 'number' | 'boolean', valueText: string): Expr {
    return {
        kind: 'expression',
        pyNodeType: literalType === 'boolean' ? 'Boolean' : 'Integer',
        expressionKind: 'literal',
        expressionType: literalType === 'boolean' ? 'cond' : 'num',
        literalType,
        valueText,
        raw: valueText,
        range: STUB_RANGE,
        text: valueText,
    } as unknown as Expr;
}

function mkIdent(name: string): Expr {
    return {
        kind: 'expression',
        pyNodeType: 'Name',
        expressionKind: 'identifier',
        expressionType: 'num',
        name,
        range: STUB_RANGE,
        text: name,
    } as unknown as Expr;
}

function mkMathConst(name: string): Expr {
    return {
        kind: 'expression',
        pyNodeType: 'Constant',
        expressionKind: 'mathConst',
        expressionType: 'num',
        name,
        raw: name,
        range: STUB_RANGE,
        text: name,
    } as unknown as Expr;
}

function mkUnary(operator: string, operand: Expr): Expr {
    return {
        kind: 'expression',
        pyNodeType: 'UnaryOp',
        expressionKind: 'unary',
        expressionType: operator === '!' || operator === 'not' ? 'cond' : 'num',
        operator,
        op: operator,
        operand,
        expr: operand,
        range: STUB_RANGE,
        text: `${operator}${(operand as {text?: string}).text ?? ''}`,
    } as unknown as Expr;
}

function mkBinary(operator: string, left: Expr, right: Expr): Expr {
    return {
        kind: 'expression',
        pyNodeType: 'BinaryOp',
        expressionKind: 'binary',
        expressionType: 'num',
        operator,
        op: operator,
        left,
        expr1: left,
        right,
        expr2: right,
        range: STUB_RANGE,
        text: `${(left as {text?: string}).text ?? ''}${operator}${(right as {text?: string}).text ?? ''}`,
    } as unknown as Expr;
}

function mkConditional(condition: Expr, whenTrue: Expr, whenFalse: Expr): Expr {
    return {
        kind: 'expression',
        pyNodeType: 'ConditionalOp',
        expressionKind: 'conditional',
        expressionType: 'num',
        condition,
        cond: condition,
        whenTrue,
        valueTrue: whenTrue,
        whenFalse,
        valueFalse: whenFalse,
        range: STUB_RANGE,
        text: `${(condition as {text?: string}).text}?${(whenTrue as {text?: string}).text}:${(whenFalse as {text?: string}).text}`,
    } as unknown as Expr;
}

function mkFunction(functionName: string, argument: Expr): Expr {
    return {
        kind: 'expression',
        pyNodeType: 'UFunc',
        expressionKind: 'function',
        expressionType: 'num',
        functionName,
        func: functionName,
        argument,
        expr: argument,
        range: STUB_RANGE,
        text: `${functionName}(${(argument as {text?: string}).text ?? ''})`,
    } as unknown as Expr;
}

describe('analyzers / inferExpressionCategory', () => {
    it('classifies literal categories by literalType', () => {
        assert.equal(inferExpressionCategory(mkLiteral('boolean', 'true')), 'boolean');
        assert.equal(inferExpressionCategory(mkLiteral('number', '42')), 'numeric');
    });

    it('identifies identifiers and math constants as numeric', () => {
        assert.equal(inferExpressionCategory(mkIdent('counter')), 'numeric');
        assert.equal(inferExpressionCategory(mkMathConst('pi')), 'numeric');
    });

    it('classifies arithmetic, bitwise, comparison, and logical binary ops', () => {
        const arith = mkBinary('+', mkLiteral('number', '1'), mkLiteral('number', '2'));
        assert.equal(inferExpressionCategory(arith), 'numeric');
        const bit = mkBinary('&', mkLiteral('number', '5'), mkLiteral('number', '3'));
        assert.equal(inferExpressionCategory(bit), 'numeric');
        const cmp = mkBinary('>', mkIdent('a'), mkLiteral('number', '0'));
        assert.equal(inferExpressionCategory(cmp), 'boolean');
        const logical = mkBinary('&&', mkLiteral('boolean', 'true'), mkLiteral('boolean', 'false'));
        assert.equal(inferExpressionCategory(logical), 'boolean');
    });

    it('classifies unary ops by operator', () => {
        const neg = mkUnary('-', mkLiteral('number', '5'));
        assert.equal(inferExpressionCategory(neg), 'numeric');
        const not = mkUnary('!', mkLiteral('boolean', 'true'));
        assert.equal(inferExpressionCategory(not), 'boolean');
        const bnot = mkUnary('~', mkLiteral('number', '5'));
        assert.equal(inferExpressionCategory(bnot), 'numeric');
    });

    it('treats function calls as numeric and ternaries as their branch type', () => {
        const fn = mkFunction('sin', mkIdent('x'));
        assert.equal(inferExpressionCategory(fn), 'numeric');
        const tern = mkConditional(
            mkBinary('>', mkIdent('x'), mkLiteral('number', '0')),
            mkLiteral('number', '1'),
            mkLiteral('number', '0'),
        );
        assert.equal(inferExpressionCategory(tern), 'numeric');
    });
});

describe('analyzers / checkExpression', () => {
    it('does not emit when the top-level category matches expected', () => {
        const diagnostics: Array<{code?: string}> = [];
        // Boolean guard.
        checkExpression(
            mkBinary('>', mkIdent('counter'), mkLiteral('number', '0')),
            'boolean',
            diagnostics,
        );
        assert.equal(diagnostics.length, 0);
    });

    it('emits E_TYPE_MISMATCH when a numeric expression is used as a guard', () => {
        const diagnostics: Array<{code?: string; data?: Record<string, unknown>}> = [];
        checkExpression(mkIdent('counter'), 'boolean', diagnostics);
        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].code, 'E_TYPE_MISMATCH');
        assert.equal(diagnostics[0].data?.expected, 'boolean');
        assert.equal(diagnostics[0].data?.actual, 'numeric');
    });

    it('emits E_TYPE_MISMATCH when a boolean expression is assigned to an int', () => {
        const diagnostics: Array<{code?: string; data?: Record<string, unknown>}> = [];
        checkExpression(
            mkBinary('>', mkIdent('counter'), mkLiteral('number', '0')),
            'numeric',
            diagnostics,
        );
        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].code, 'E_TYPE_MISMATCH');
        assert.equal(diagnostics[0].data?.expected, 'numeric');
        assert.equal(diagnostics[0].data?.actual, 'boolean');
    });

    it('catches mismatched operands inside binary ops', () => {
        const diagnostics: Array<{code?: string; data?: Record<string, unknown>}> = [];
        // `5 && true` — left operand of && should be boolean, but 5 is numeric.
        checkExpression(
            mkBinary('&&', mkLiteral('number', '5'), mkLiteral('boolean', 'true')),
            'boolean',
            diagnostics,
        );
        assert.ok(diagnostics.some(d => d.code === 'E_TYPE_MISMATCH' && d.data?.expected === 'boolean' && d.data?.actual === 'numeric'));
    });

    it('catches mismatched ternary condition', () => {
        const diagnostics: Array<{code?: string; data?: Record<string, unknown>}> = [];
        // (1 ? 2 : 3) — condition `1` is numeric, ternary cond must be boolean.
        const expr = mkConditional(
            mkLiteral('number', '1'),
            mkLiteral('number', '2'),
            mkLiteral('number', '3'),
        );
        checkExpression(expr, 'numeric', diagnostics);
        assert.ok(diagnostics.some(d =>
            d.code === 'E_TYPE_MISMATCH' &&
            d.data?.expected === 'boolean' &&
            d.data?.actual === 'numeric',
        ));
    });

    it('catches mismatched function argument category', () => {
        const diagnostics: Array<{code?: string; data?: Record<string, unknown>}> = [];
        // sin(true) — argument should be numeric, but true is boolean.
        checkExpression(
            mkFunction('sin', mkLiteral('boolean', 'true')),
            'numeric',
            diagnostics,
        );
        assert.ok(diagnostics.some(d =>
            d.code === 'E_TYPE_MISMATCH' &&
            d.data?.expected === 'numeric' &&
            d.data?.actual === 'boolean',
        ));
    });

    it('catches mismatched unary `!` operand', () => {
        const diagnostics: Array<{code?: string; data?: Record<string, unknown>}> = [];
        // !5 — operand should be boolean, but 5 is numeric.
        checkExpression(
            mkUnary('!', mkLiteral('number', '5')),
            'boolean',
            diagnostics,
        );
        assert.ok(diagnostics.some(d =>
            d.code === 'E_TYPE_MISMATCH' &&
            d.data?.expected === 'boolean' &&
            d.data?.actual === 'numeric',
        ));
    });
});
