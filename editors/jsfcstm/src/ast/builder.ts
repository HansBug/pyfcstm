import {getParser} from '../dsl/parser';
import {
    fallbackRangeFromText,
    getDocumentFilePath,
    makeNodeRange,
    makeTokenRange,
    ParseTreeNode,
    TextDocumentLike,
    TextRange,
    tokenText,
} from '../utils/text';
import type {
    FcstmAstAction,
    FcstmAstAssignmentStatement,
    FcstmAstBinaryExpression,
    FcstmAstChainPath,
    FcstmAstChainTrigger,
    FcstmAstComboTrigger,
    FcstmAstComboTriggerTerm,
    FcstmAstConditionalExpression,
    FcstmAstDocument,
    FcstmAstEmptyStatement,
    FcstmAstEventDefinition,
    FcstmAstExpression,
    FcstmAstForcedTransition,
    FcstmAstFunctionExpression,
    FcstmAstIdentifierExpression,
    FcstmAstIfBranch,
    FcstmAstIfStatement,
    FcstmAstImportDefExactSelector,
    FcstmAstImportDefFallbackSelector,
    FcstmAstImportDefMapping,
    FcstmAstImportDefPatternSelector,
    FcstmAstImportDefSelector,
    FcstmAstImportDefSetSelector,
    FcstmAstImportDefTargetTemplate,
    FcstmAstImportEventMapping,
    FcstmAstImportMapping,
    FcstmAstImportStatement,
    FcstmAstLiteralExpression,
    FcstmAstLocalTrigger,
    FcstmAstMathConstExpression,
    FcstmAstOperationBlock,
    FcstmAstOperationStatement,
    FcstmAstParenthesizedExpression,
    FcstmAstStateDefinition,
    FcstmAstStateStatement,
    FcstmAstTransition,
    FcstmAstTrigger,
    FcstmAstUnaryExpression,
    FcstmAstVariableDefinition,
} from './model';

const UNARY_OPERATOR_ALIASES: Record<string, string> = {
    not: '!',
};

const BINARY_OPERATOR_ALIASES: Record<string, string> = {
    and: '&&',
    or: '||',
};

const COND_BINARY_OPERATOR_ALIASES: Record<string, string> = {
    implies: '=>',
};

const EXPR_PRECEDENCE: Record<string, number> = {
    function_call: 90,
    'unary+': 80,
    'unary-': 80,
    '!': 80,
    not: 80,
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
    iff: 20,
    '&&': 15,
    and: 15,
    xor: 12,
    '||': 10,
    or: 10,
    '=>': 7,
    '?:': 5,
};

interface ParseTreeContext extends ParseTreeNode {
    from_state?: { text?: string };
    to_state?: { text?: string };
    from_id?: { text?: string };
    func_name?: { text?: string };
    aspect?: { text?: string };
    raw_doc?: { text?: string };
    target_event?: { getText?: () => string };
    target_text?: { text?: string };
    selector_pattern?: { text?: string };
    selector_name?: { text?: string };
    selector_items?: Array<{ text?: string }>;
    op?: { text?: string };
    isabs?: { text?: string };
    num_expression?: () => ParseTreeContext;
    combo_transition_trigger?: () => ParseTreeContext | undefined;
    entry_combo_transition_trigger?: () => ParseTreeContext | undefined;
    entry_chain_combo_trigger?: () => ParseTreeContext | undefined;
    entry_chain_combo_leading_guard?: (index?: number | null) => ParseTreeContext[] | ParseTreeContext | undefined;
    entry_chain_combo_trigger_term?: (index?: number | null) => ParseTreeContext[] | ParseTreeContext | undefined;
    local_combo_trigger?: () => ParseTreeContext | undefined;
    chain_combo_trigger?: () => ParseTreeContext | undefined;
    local_combo_event_term?: () => ParseTreeContext | undefined;
    local_combo_leading_guard?: (index?: number | null) => ParseTreeContext[] | ParseTreeContext | undefined;
    local_combo_trigger_term?: (index?: number | null) => ParseTreeContext[] | ParseTreeContext | undefined;
    combo_event_term?: () => ParseTreeContext | undefined;
    combo_trigger_term?: (index?: number | null) => ParseTreeContext[] | ParseTreeContext | undefined;
    chain_combo_guard_alias?: () => ParseTreeContext | undefined;
    combo_guard_term?: () => ParseTreeContext | undefined;
    chain_id?: () => ParseTreeContext | undefined;
    cond_expression?: () => ParseTreeContext | undefined;
}

function nodeText(node: ParseTreeNode | undefined): string {
    return node?.getText?.() || '';
}

function decodeEscapedString(value: string): string {
    let result = '';

    for (let index = 0; index < value.length; index += 1) {
        const current = value[index];
        if (current !== '\\' || index === value.length - 1) {
            result += current;
            continue;
        }

        const next = value[index + 1];
        if (next === 'b') {
            result += '\b';
            index += 1;
        } else if (next === 't') {
            result += '\t';
            index += 1;
        } else if (next === 'n') {
            result += '\n';
            index += 1;
        } else if (next === 'f') {
            result += '\f';
            index += 1;
        } else if (next === 'r') {
            result += '\r';
            index += 1;
        } else if (next === '"' || next === '\'' || next === '\\') {
            result += next;
            index += 1;
        } else if (next === 'u' && /^[0-9a-fA-F]{4}$/.test(value.slice(index + 2, index + 6))) {
            result += String.fromCharCode(parseInt(value.slice(index + 2, index + 6), 16));
            index += 5;
        } else if (next === 'x' && /^[0-9a-fA-F]{2}$/.test(value.slice(index + 2, index + 4))) {
            result += String.fromCharCode(parseInt(value.slice(index + 2, index + 4), 16));
            index += 3;
        } else if (/[0-7]/.test(next)) {
            let octal = next;
            let octalIndex = index + 2;
            while (octal.length < 3 && octalIndex < value.length && /[0-7]/.test(value[octalIndex])) {
                octal += value[octalIndex];
                octalIndex += 1;
            }
            result += String.fromCharCode(parseInt(octal, 8));
            index += octal.length;
        } /* c8 ignore start -- defensive: the grammar rejects
             unknown escape characters at lex time, so the default
             "preserve literal" fallback is never reached via parsed
             DSL. Kept so future grammar relaxations don't crash. */ else {
            result += next;
            index += 1;
        }
        /* c8 ignore stop */
    }

    return result;
}

function unquoteText(value: string | undefined): string {
    // Defensive: callers pass tokenText(token) which returns '' for
    // missing tokens; an undefined value would indicate a future
    // caller-side regression.
    /* c8 ignore start */
    if (!value) {
        return '';
    }
    /* c8 ignore stop */
    if (
        (value.startsWith('"') && value.endsWith('"'))
        || (value.startsWith('\'') && value.endsWith('\''))
    ) {
        return decodeEscapedString(value.slice(1, -1));
    }
    return value;
}

function unquoteTokenValue(token: { text?: string } | undefined): string | undefined {
    return token ? unquoteText(tokenText(token)) : undefined;
}

function formatMultilineComment(rawDoc: string | undefined): string | undefined {
    // Defensive: callers gate on ``node.raw_doc`` being truthy before
    // calling; an undefined value would indicate a future caller-side
    // regression.
    /* c8 ignore start */
    if (!rawDoc) {
        return undefined;
    }
    /* c8 ignore stop */

    const trimmed = rawDoc.trim();
    if (/^\s*\/\*+\s*\*\/\s*$/.test(trimmed)) {
        return '';
    }

    let content = trimmed.replace(/^\s*\/\*+/, '');
    content = content.replace(/\*+\/\s*$/, '');

    let lines = content.split(/\r?\n/);

    while (lines.length > 0 && !lines[0].trim()) {
        lines = lines.slice(1);
    }
    while (lines.length > 1 && !lines[lines.length - 1].trim()) {
        lines = lines.slice(0, -1);
    }

    const trailingTrimmed = lines.map(line => line.replace(/\s+$/g, ''));
    const nonEmptyLines = trailingTrimmed.filter(line => line.trim());
    // Defensive: any all-whitespace comment is already short-circuited
    // above by the regex matching empty C-style comments. Reaching this
    // guard would require non-whitespace input that nonetheless has
    // zero non-empty lines after stripping, which the implementation
    // upstream guarantees is impossible.
    /* c8 ignore start */
    if (nonEmptyLines.length === 0) {
        return '';
    }
    /* c8 ignore stop */

    const indent = nonEmptyLines.reduce((minIndent, line) => {
        const currentIndent = line.match(/^\s*/)![0].length;
        return Math.min(minIndent, currentIndent);
    }, Number.POSITIVE_INFINITY);

    return trailingTrimmed
        .map(line => line.slice(Math.min(indent, line.length)))
        .join('\n');
}

function contextChildren(node: ParseTreeNode | undefined): ParseTreeContext[] {
    return (node?.children || []).filter(child => {
        const name = child?.constructor?.name;
        return Boolean(name) && name !== 'TerminalNodeImpl';
    }) as ParseTreeContext[];
}

function terminalChildren(node: ParseTreeNode | undefined): ParseTreeNode[] {
    return (node?.children || []).filter(child => child?.constructor?.name === 'TerminalNodeImpl');
}

function firstContextChild(node: ParseTreeNode | undefined): ParseTreeContext | undefined {
    return contextChildren(node)[0];
}

function arrayContextChildren(
    value: ParseTreeContext[] | ParseTreeContext | undefined
): ParseTreeContext[] {
    if (!value) {
        return [];
    }
    return Array.isArray(value) ? value : [value];
}

function getNodeByMethod(
    node: ParseTreeContext | undefined,
    methodName: keyof ParseTreeContext
): ParseTreeContext | undefined {
    const method = node?.[methodName] as unknown;
    if (typeof method !== 'function') {
        return undefined;
    }

    const getter = method as (this: ParseTreeContext) => ParseTreeContext[] | ParseTreeContext | undefined;
    return arrayContextChildren(getter.call(node as ParseTreeContext))[0];
}

function getNodesByMethod(
    node: ParseTreeContext | undefined,
    methodName: keyof ParseTreeContext
): ParseTreeContext[] {
    const method = node?.[methodName] as unknown;
    if (typeof method !== 'function') {
        return [];
    }

    const getter = method as (this: ParseTreeContext, index?: number | null) => ParseTreeContext[] | ParseTreeContext | undefined;
    return arrayContextChildren(getter.call(node as ParseTreeContext, null));
}

function getNodeRange(
    node: ParseTreeNode,
    document: TextDocumentLike,
    fallbackText?: string
): TextRange {
    return makeNodeRange(node, document)
        || fallbackRangeFromText(document, document.getText(), fallbackText || nodeText(node), 0);
}

function buildChainPath(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstChainPath {
    const text = nodeText(node);
    const raw = text.startsWith('/') ? text.slice(1) : text;
    const segments = raw ? raw.split('.') : [];
    return {
        kind: 'chainPath',
        pyNodeType: 'ChainID',
        range: getNodeRange(node, document, text),
        text,
        isAbsolute: Boolean(node.isabs) || text.startsWith('/'),
        is_absolute: Boolean(node.isabs) || text.startsWith('/'),
        segments,
        path: segments,
    };
}

function buildExpressionType(nodeName: string): 'init' | 'num' | 'cond' {
    if (nodeName.endsWith('InitContext')) {
        return 'init';
    }
    if (nodeName === 'Num_literalContext' || nodeName === 'Math_constContext') {
        return 'num';
    }
    if (nodeName === 'Bool_literalContext' || nodeName === 'ConditionalCStyleCondNumContext') {
        return 'cond';
    }
    if (nodeName.endsWith('CondContext')) {
        return 'cond';
    }
    return 'num';
}

function inferLiteralPyNodeType(text: string, expressionType: 'init' | 'num' | 'cond'):
    'Boolean' | 'Integer' | 'HexInt' | 'Float' {
    if (expressionType === 'cond') {
        return 'Boolean';
    }
    if (/^0x/i.test(text)) {
        return 'HexInt';
    }
    if (text.includes('.')) {
        return 'Float';
    }
    return 'Integer';
}

function canonicalizeUnaryOperator(operator: string): string {
    return UNARY_OPERATOR_ALIASES[operator] || operator;
}

function canonicalizeBinaryOperator(
    operator: string,
    expressionType: 'init' | 'num' | 'cond'
): string {
    if (expressionType === 'cond') {
        return COND_BINARY_OPERATOR_ALIASES[operator] || BINARY_OPERATOR_ALIASES[operator] || operator;
    }
    return BINARY_OPERATOR_ALIASES[operator] || operator;
}

function buildLocalEventPath(
    sourceKind: 'init' | 'state' | 'all',
    sourceStateName: string | undefined,
    eventName: string,
    range: TextRange
): FcstmAstChainPath {
    const path = sourceKind === 'state' && sourceStateName
        ? [sourceStateName, eventName]
        : [eventName];
    return {
        kind: 'chainPath',
        pyNodeType: 'ChainID',
        range,
        text: path.join('.'),
        isAbsolute: false,
        is_absolute: false,
        segments: path,
        path,
    };
}

function buildEntryEventPath(eventPath: FcstmAstChainPath): FcstmAstChainPath {
    return {
        ...eventPath,
        range: makeCopiedRange(eventPath.range),
        isAbsolute: eventPath.isAbsolute,
        is_absolute: eventPath.is_absolute,
        segments: [...eventPath.segments],
        path: [...eventPath.path],
    };
}

function expressionPrecedence(expression: FcstmAstExpression): number | null {
    if (expression.expressionKind === 'binary') {
        return EXPR_PRECEDENCE[canonicalizeBinaryOperator(expression.op, expression.expressionType)] ?? null;
    }
    if (expression.expressionKind === 'conditional') return EXPR_PRECEDENCE['?:'];
    if (expression.expressionKind === 'unary') return EXPR_PRECEDENCE[unaryPrecedenceKey(expression.op)] ?? null;
    return null;
}

function unaryPrecedenceKey(op: string): string {
    const canonical = canonicalizeUnaryOperator(op);
    return canonical === '+' || canonical === '-' ? `unary${canonical}` : canonical;
}

function canonicalExpressionText(expression: FcstmAstExpression | undefined): string | null {
    if (!expression) return null;
    switch (expression.expressionKind) {
        case 'literal':
            return expression.valueText.toLowerCase();
        case 'identifier':
            return expression.name;
        case 'mathConst':
            return expression.name;
        case 'parenthesized': {
            const inner = canonicalExpressionText(expression.expression);
            return inner === null ? null : `(${inner})`;
        }
        case 'function': {
            const argument = canonicalExpressionText(expression.argument);
            return argument === null ? null : `${expression.functionName}(${argument})`;
        }
        case 'unary': {
            const op = canonicalizeUnaryOperator(expression.op);
            const myPrecedence = EXPR_PRECEDENCE[unaryPrecedenceKey(expression.op)];
            let value = canonicalExpressionText(expression.operand);
            if (value === null) return null;
            const valuePrecedence = expressionPrecedence(expression.operand);
            if (valuePrecedence !== null && valuePrecedence <= myPrecedence) {
                value = `(${value})`;
            }
            return `${op}${value}`;
        }
        case 'binary': {
            const op = canonicalizeBinaryOperator(expression.op, expression.expressionType);
            const myPrecedence = EXPR_PRECEDENCE[op];
            let left = canonicalExpressionText(expression.left);
            let right = canonicalExpressionText(expression.right);
            if (left === null || right === null) return null;
            const leftPrecedence = expressionPrecedence(expression.left);
            if (leftPrecedence !== null && leftPrecedence < myPrecedence) {
                left = `(${left})`;
            }
            const rightPrecedence = expressionPrecedence(expression.right);
            if (rightPrecedence !== null && rightPrecedence <= myPrecedence) {
                right = `(${right})`;
            }
            return `${left} ${op} ${right}`;
        }
        case 'conditional': {
            const myPrecedence = EXPR_PRECEDENCE['?:'];
            const condition = canonicalExpressionText(expression.condition);
            let whenTrue = canonicalExpressionText(expression.whenTrue);
            let whenFalse = canonicalExpressionText(expression.whenFalse);
            if (condition === null || whenTrue === null || whenFalse === null) return null;
            const truePrecedence = expressionPrecedence(expression.whenTrue);
            if (truePrecedence !== null && truePrecedence <= myPrecedence) {
                whenTrue = `(${whenTrue})`;
            }
            const falsePrecedence = expressionPrecedence(expression.whenFalse);
            if (falsePrecedence !== null && falsePrecedence <= myPrecedence) {
                whenFalse = `(${whenFalse})`;
            }
            return `(${condition}) ? ${whenTrue} : ${whenFalse}`;
        }
    }
}

function buildActionPyNodeType(
    stage: 'enter' | 'during' | 'exit',
    mode: 'operations' | 'abstract' | 'ref',
    isGlobalAspect: boolean
): FcstmAstAction['pyNodeType'] {
    if (stage === 'enter') {
        if (mode === 'abstract') {
            return 'EnterAbstractFunction';
        } else if (mode === 'ref') {
            return 'EnterRefFunction';
        }
        return 'EnterOperations';
    }
    if (stage === 'exit') {
        if (mode === 'abstract') {
            return 'ExitAbstractFunction';
        } else if (mode === 'ref') {
            return 'ExitRefFunction';
        }
        return 'ExitOperations';
    }
    if (isGlobalAspect) {
        if (mode === 'abstract') {
            return 'DuringAspectAbstractFunction';
        } else if (mode === 'ref') {
            return 'DuringAspectRefFunction';
        }
        return 'DuringAspectOperations';
    }
    if (mode === 'abstract') {
        return 'DuringAbstractFunction';
    } else if (mode === 'ref') {
        return 'DuringRefFunction';
    }
    return 'DuringOperations';
}

function buildExpression(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstExpression {
    const nodeName = node.constructor?.name || '';
    const range = getNodeRange(node, document, nodeText(node));
    const text = nodeText(node);
    const expressionType = buildExpressionType(nodeName);
    const childContexts = contextChildren(node);

    if (/^Pass.*ExprCondContext$/.test(nodeName)) {
        return buildExpression(childContexts[0], document);
    }

    if (nodeName === 'Num_literalContext' || nodeName === 'Bool_literalContext') {
        return {
            kind: 'expression',
            pyNodeType: inferLiteralPyNodeType(text, expressionType),
            expressionKind: 'literal',
            expressionType,
            range,
            text,
            literalType: expressionType === 'cond' ? 'boolean' : 'number',
            valueText: text,
            raw: text,
        } as FcstmAstLiteralExpression;
    }

    if (nodeName === 'Math_constContext') {
        return {
            kind: 'expression',
            pyNodeType: 'Constant',
            expressionKind: 'mathConst',
            expressionType,
            range,
            text,
            name: text,
            raw: text,
        } as FcstmAstMathConstExpression;
    }

    if (/ParenExpr/.test(nodeName)) {
        const expression = buildExpression(childContexts[0], document);
        return {
            kind: 'expression',
            pyNodeType: 'Paren',
            expressionKind: 'parenthesized',
            expressionType,
            range,
            text,
            expression,
            expr: expression,
        } as FcstmAstParenthesizedExpression;
    }

    if (/LiteralExpr/.test(nodeName)) {
        const valueText = childContexts[0] ? nodeText(childContexts[0]) : text;
        return {
            kind: 'expression',
            pyNodeType: inferLiteralPyNodeType(valueText, expressionType),
            expressionKind: 'literal',
            expressionType,
            range,
            text,
            literalType: expressionType === 'cond' ? 'boolean' : 'number',
            valueText,
            raw: valueText,
        } as FcstmAstLiteralExpression;
    }

    if (/IdExprNumContext$/.test(nodeName)) {
        return {
            kind: 'expression',
            pyNodeType: 'Name',
            expressionKind: 'identifier',
            expressionType,
            range,
            text,
            name: text,
        } as FcstmAstIdentifierExpression;
    }

    if (/MathConstExpr/.test(nodeName)) {
        const raw = childContexts[0] ? nodeText(childContexts[0]) : text;
        return {
            kind: 'expression',
            pyNodeType: 'Constant',
            expressionKind: 'mathConst',
            expressionType,
            range,
            text,
            name: raw,
            raw,
        } as FcstmAstMathConstExpression;
    }

    if (/UnaryExpr/.test(nodeName)) {
        const operator = canonicalizeUnaryOperator(tokenText(node.op));
        const operand = buildExpression(childContexts[childContexts.length - 1], document);
        return {
            kind: 'expression',
            pyNodeType: 'UnaryOp',
            expressionKind: 'unary',
            expressionType,
            range,
            text,
            operator,
            op: operator,
            operand,
            expr: operand,
        } as FcstmAstUnaryExpression;
    }

    if (/BinaryExpr/.test(nodeName)) {
        const left = buildExpression(childContexts[0], document);
        const right = buildExpression(childContexts[1], document);
        const operator = canonicalizeBinaryOperator(tokenText(node.op), expressionType);
        return {
            kind: 'expression',
            pyNodeType: 'BinaryOp',
            expressionKind: 'binary',
            expressionType,
            range,
            text,
            operator,
            op: operator,
            left,
            expr1: left,
            right,
            expr2: right,
        } as FcstmAstBinaryExpression;
    }

    if (/FuncExpr/.test(nodeName)) {
        const argument = buildExpression(childContexts[0], document);
        const functionName = tokenText(node.func_name);
        return {
            kind: 'expression',
            pyNodeType: 'UFunc',
            expressionKind: 'function',
            expressionType,
            range,
            text,
            functionName,
            func: functionName,
            argument,
            expr: argument,
        } as FcstmAstFunctionExpression;
    }

    if (/ConditionalCStyle/.test(nodeName)) {
        let condition = buildExpression(childContexts[0], document);
        if (expressionType === 'cond' && condition.pyNodeType === 'Paren') {
            condition = condition.expr;
        }
        const whenTrue = buildExpression(childContexts[1], document);
        const whenFalse = buildExpression(childContexts[2], document);
        return {
            kind: 'expression',
            pyNodeType: 'ConditionalOp',
            expressionKind: 'conditional',
            expressionType,
            range,
            text,
            condition,
            cond: condition,
            whenTrue,
            valueTrue: whenTrue,
            value_true: whenTrue,
            whenFalse,
            valueFalse: whenFalse,
            value_false: whenFalse,
        } as FcstmAstConditionalExpression;
    }

    return {
        kind: 'expression',
        pyNodeType: 'Name',
        expressionKind: 'identifier',
        expressionType,
        range,
        text,
        name: text,
    } as FcstmAstIdentifierExpression;
}

function buildOperationBlockFromStatementSet(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstOperationBlock {
    const statements = contextChildren(node)
        .filter(child => child.constructor?.name === 'Operational_statementContext')
        .map(child => buildOperationalStatement(firstContextChild(child) || child, document))
        .filter(statement => statement.kind !== 'emptyStatement');

    return {
        kind: 'operationBlock',
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        statements,
    };
}

function buildOperationBlock(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstOperationBlock {
    const statementSet = contextChildren(node).find(child => child.constructor?.name === 'Operational_statement_setContext');
    if (statementSet) {
        return buildOperationBlockFromStatementSet(statementSet, document);
    }

    return {
        kind: 'operationBlock',
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        statements: [],
    };
}

function buildOperationalStatement(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstOperationStatement {
    const nodeName = node.constructor?.name || '';
    const range = getNodeRange(node, document, nodeText(node));
    const text = nodeText(node);

    if (nodeName === 'Operation_assignmentContext' || nodeName === 'Operational_assignmentContext') {
        const expressionNode = contextChildren(node).find(child => /Expr|Num_expression|Cond_expression/.test(child.constructor?.name || ''));
        const expression = buildExpression(expressionNode || (firstContextChild(node) as ParseTreeContext), document);
        const targetName = text.split('=')[0].trim().replace(/:$/, '');
        return {
            kind: 'assignmentStatement',
            pyNodeType: 'OperationAssignment',
            range,
            text,
            targetName,
            name: targetName,
            expression,
            expr: expression,
        } as FcstmAstAssignmentStatement;
    }

    if (nodeName === 'If_statementContext') {
        const childContexts = contextChildren(node);
        const branches: FcstmAstIfBranch[] = [];
        const conditionNodes = childContexts.filter(child => /Cond/.test(child.constructor?.name || ''));
        const blockNodes = childContexts.filter(child => child.constructor?.name === 'Operation_blockContext');

        for (let i = 0; i < conditionNodes.length; i++) {
            const block = buildOperationBlock(blockNodes[i], document);
            const condition = buildExpression(conditionNodes[i], document);
            branches.push({
                kind: 'ifBranch',
                pyNodeType: 'OperationIfBranch',
                range: getNodeRange(blockNodes[i] || conditionNodes[i], document, nodeText(conditionNodes[i])),
                text: nodeText(conditionNodes[i]),
                condition,
                statements: block.statements,
                block,
            });
        }

        const elseBlock = blockNodes.length > conditionNodes.length
            ? buildOperationBlock(blockNodes[blockNodes.length - 1], document)
            : undefined;
        if (elseBlock) {
            branches.push({
                kind: 'ifBranch',
                pyNodeType: 'OperationIfBranch',
                range: elseBlock.range,
                text: elseBlock.text,
                condition: null,
                statements: elseBlock.statements,
                block: elseBlock,
            });
        }

        return {
            kind: 'ifStatement',
            pyNodeType: 'OperationIf',
            range,
            text,
            branches,
            elseBlock,
        } as FcstmAstIfStatement;
    }

    return {
        kind: 'emptyStatement',
        range,
        text,
    } as FcstmAstEmptyStatement;
}

function makeCopiedRange(range: TextRange): TextRange {
    return {
        start: {line: range.start.line, character: range.start.character},
        end: {line: range.end.line, character: range.end.character},
    };
}

function rangeBetween(
    startRange: TextRange,
    endRange: TextRange
): TextRange {
    return {
        start: {line: startRange.start.line, character: startRange.start.character},
        end: {line: endRange.end.line, character: endRange.end.character},
    };
}

function buildGuardTermValueRange(
    guardTermNode: ParseTreeContext,
    conditionNode: ParseTreeContext | undefined,
    document: TextDocumentLike
): TextRange | undefined {
    if (conditionNode) {
        return getNodeRange(conditionNode, document, nodeText(conditionNode));
    }

    const range = getNodeRange(guardTermNode, document, nodeText(guardTermNode));
    if (range.start.line === range.end.line && range.end.character - range.start.character >= 2) {
        return {
            start: {line: range.start.line, character: range.start.character + 1},
            end: {line: range.end.line, character: range.end.character - 1},
        };
    }

    return undefined;
}

function guardTermCanonicalText(condition: FcstmAstExpression | undefined, guardTermNode: ParseTreeContext): string {
    const canonical = canonicalExpressionText(condition);
    return canonical !== null ? `[${canonical}]` : nodeText(guardTermNode);
}

function buildEventComboTerm(
    eventTermNode: ParseTreeContext,
    eventScope: 'local' | 'chain' | 'absolute',
    document: TextDocumentLike
): FcstmAstComboTriggerTerm {
    const localEventNode = getNodeByMethod(eventTermNode, 'local_combo_event_term') || eventTermNode;
    const chainEventNode = getNodeByMethod(eventTermNode, 'combo_event_term') || eventTermNode;
    const chainNode = getNodeByMethod(chainEventNode, 'chain_id') || chainEventNode;
    const isLocal = eventScope === 'local';
    const eventPath = isLocal
        ? {
            kind: 'chainPath',
            pyNodeType: 'ChainID',
            range: getNodeRange(localEventNode, document, nodeText(localEventNode)),
            text: nodeText(localEventNode),
            isAbsolute: false,
            is_absolute: false,
            segments: [nodeText(localEventNode)],
            path: [nodeText(localEventNode)],
        } as FcstmAstChainPath
        : buildChainPath(chainNode, document);
    const scope = eventPath.isAbsolute ? 'absolute' : eventScope;
    const canonicalText = scope === 'local' ? eventPath.path[eventPath.path.length - 1] : eventPath.text;

    const termRange = getNodeRange(eventTermNode, document, nodeText(eventTermNode));

    return {
        kind: 'comboTriggerTerm',
        range: termRange,
        text: nodeText(eventTermNode),
        termKind: 'event',
        canonicalText,
        canonical_text: canonicalText,
        removalRange: makeCopiedRange(termRange),
        removal_range: makeCopiedRange(termRange),
        eventScope: scope,
        event_scope: scope,
        eventPath,
        event_id: eventPath,
    };
}

function buildGuardComboTerm(
    guardTermNode: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstComboTriggerTerm {
    const conditionNode = getNodeByMethod(guardTermNode, 'cond_expression');
    const condition = conditionNode ? buildExpression(conditionNode, document) : undefined;
    const canonicalText = guardTermCanonicalText(condition, guardTermNode);
    const termRange = getNodeRange(guardTermNode, document, nodeText(guardTermNode));
    const valueRange = buildGuardTermValueRange(guardTermNode, conditionNode, document);

    return {
        kind: 'comboTriggerTerm',
        range: termRange,
        text: nodeText(guardTermNode),
        termKind: 'guard',
        canonicalText,
        canonical_text: canonicalText,
        removalRange: makeCopiedRange(termRange),
        removal_range: makeCopiedRange(termRange),
        valueRange: valueRange,
        value_range: valueRange,
        condition,
        condition_expr: condition,
    };
}

function applyComboRemovalRanges(terms: FcstmAstComboTriggerTerm[]): void {
    if (terms.length === 0) {
        return;
    }
    if (terms.length === 1) {
        terms[0].removalRange = makeCopiedRange(terms[0].range);
        terms[0].removal_range = makeCopiedRange(terms[0].range);
        return;
    }

    for (let index = 0; index < terms.length; index += 1) {
        const current = terms[index];
        const removalRange = index === 0
            ? rangeBetween(current.range, {start: terms[index + 1].range.start, end: terms[index + 1].range.start})
            : rangeBetween({start: terms[index - 1].range.end, end: terms[index - 1].range.end}, current.range);
        current.removalRange = removalRange;
        current.removal_range = removalRange;
    }
}

function buildComboTriggerFromSyntax(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstComboTrigger | undefined {
    const entryComboNode = getNodeByMethod(node, 'entry_combo_transition_trigger');
    const comboNode = getNodeByMethod(node, 'combo_transition_trigger') || entryComboNode;
    if (!comboNode) {
        return undefined;
    }

    const terms: FcstmAstComboTriggerTerm[] = [];
    let scopePrefix: ':' | '::' = ':';
    const legacyCondNode = getNodeByMethod(comboNode, 'cond_expression');
    if (legacyCondNode) {
        const condition = buildExpression(legacyCondNode, document);
        const range = getNodeRange(comboNode, document, nodeText(comboNode));
        const leftBracket = nodeText(comboNode).indexOf('[');
        const rightBracket = nodeText(comboNode).lastIndexOf(']');
        const termRange = leftBracket >= 0 && rightBracket >= leftBracket
            ? {
                start: {line: range.start.line, character: range.start.character + leftBracket},
                end: {line: range.start.line, character: range.start.character + rightBracket + 1},
            }
            : range;
        const valueRange = {
            start: {line: legacyCondNode.start?.line ? legacyCondNode.start.line - 1 : termRange.start.line, character: legacyCondNode.start?.column ?? termRange.start.character + 1},
            end: {line: legacyCondNode.stop?.line ? legacyCondNode.stop.line - 1 : termRange.end.line, character: (legacyCondNode.stop?.column ?? termRange.end.character - 1) + nodeText(legacyCondNode).length},
        };
        terms.push({
            kind: 'comboTriggerTerm',
            range: termRange,
            text: nodeText(comboNode).slice(Math.max(0, leftBracket), rightBracket >= leftBracket ? rightBracket + 1 : undefined),
            termKind: 'guard',
            canonicalText: guardTermCanonicalText(condition, comboNode),
            canonical_text: guardTermCanonicalText(condition, comboNode),
            removalRange: termRange,
            removal_range: termRange,
            valueRange,
            value_range: valueRange,
            condition,
            condition_expr: condition,
        });
    } else {
        const entryTriggerNode = getNodeByMethod(comboNode, 'entry_chain_combo_trigger');
        const localTriggerNode = getNodeByMethod(comboNode, 'local_combo_trigger');
        const chainTriggerNode = getNodeByMethod(comboNode, 'chain_combo_trigger');
        if (entryTriggerNode) {
            scopePrefix = '::';
            for (const leading of getNodesByMethod(entryTriggerNode, 'entry_chain_combo_leading_guard')) {
                const guardNode = getNodeByMethod(leading, 'combo_guard_term');
                if (guardNode) terms.push(buildGuardComboTerm(guardNode, document));
            }
            const eventNode = getNodeByMethod(entryTriggerNode, 'combo_event_term');
            if (eventNode) terms.push(buildEventComboTerm(eventNode, 'chain', document));
            for (const termNode of getNodesByMethod(entryTriggerNode, 'entry_chain_combo_trigger_term')) {
                const event = getNodeByMethod(termNode, 'combo_event_term');
                const guard = getNodeByMethod(termNode, 'combo_guard_term');
                if (event) terms.push(buildEventComboTerm(event, 'chain', document));
                if (guard) terms.push(buildGuardComboTerm(guard, document));
            }
        } else if (localTriggerNode) {
            scopePrefix = '::';
            for (const leading of getNodesByMethod(localTriggerNode, 'local_combo_leading_guard')) {
                const guardNode = getNodeByMethod(leading, 'combo_guard_term');
                if (guardNode) terms.push(buildGuardComboTerm(guardNode, document));
            }
            const eventNode = getNodeByMethod(localTriggerNode, 'local_combo_event_term');
            if (eventNode) terms.push(buildEventComboTerm(eventNode, 'local', document));
            for (const termNode of getNodesByMethod(localTriggerNode, 'local_combo_trigger_term')) {
                const event = getNodeByMethod(termNode, 'local_combo_event_term');
                const guard = getNodeByMethod(termNode, 'combo_guard_term');
                if (event) terms.push(buildEventComboTerm(event, 'local', document));
                if (guard) terms.push(buildGuardComboTerm(guard, document));
            }
        } else if (chainTriggerNode) {
            const aliasNode = getNodeByMethod(chainTriggerNode, 'chain_combo_guard_alias');
            const singleEventNode = getNodeByMethod(chainTriggerNode, 'combo_event_term');
            if (aliasNode) {
                const guardNode = getNodeByMethod(aliasNode, 'combo_guard_term');
                if (guardNode) terms.push(buildGuardComboTerm(guardNode, document));
            } else if (singleEventNode) {
                terms.push(buildEventComboTerm(singleEventNode, 'chain', document));
            } else {
                for (const termNode of getNodesByMethod(chainTriggerNode, 'combo_trigger_term')) {
                    const event = getNodeByMethod(termNode, 'combo_event_term');
                    const guard = getNodeByMethod(termNode, 'combo_guard_term');
                    if (event) terms.push(buildEventComboTerm(event, 'chain', document));
                    if (guard) terms.push(buildGuardComboTerm(guard, document));
                }
            }
        }
    }

    applyComboRemovalRanges(terms);
    const isCombo = terms.length > 1;
    const isPureGuardAlias = Boolean(
        getNodeByMethod(getNodeByMethod(comboNode, 'chain_combo_trigger'), 'chain_combo_guard_alias')
    );
    if (!isCombo && !isPureGuardAlias) {
        return undefined;
    }
    const canonicalText = `${scopePrefix} ${terms.map(term => term.canonicalText).join(' + ')}`;
    return {
        kind: 'comboTrigger',
        range: getNodeRange(comboNode, document, nodeText(comboNode)),
        text: nodeText(comboNode),
        scopePrefix,
        scope_prefix: scopePrefix,
        canonicalText,
        canonical_text: canonicalText,
        terms,
        isCombo,
        is_combo: isCombo,
    };
}

function buildLocalTriggerFromNode(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstLocalTrigger {
    const eventName = nodeText(node);
    return {
        kind: 'localTrigger',
        range: getNodeRange(node, document, eventName),
        text: eventName,
        eventName,
    } as FcstmAstLocalTrigger;
}

function buildChainTriggerFromNode(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstChainTrigger {
    const chainNode = getNodeByMethod(node, 'chain_id') || node;
    return {
        kind: 'chainTrigger',
        range: getNodeRange(chainNode, document, nodeText(chainNode)),
        text: nodeText(chainNode),
        eventPath: buildChainPath(chainNode, document),
    } as FcstmAstChainTrigger;
}

function buildTrigger(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstTrigger | undefined {
    if (node.from_id) {
        const eventName = tokenText(node.from_id);
        return {
            kind: 'localTrigger',
            range: makeTokenRange(node.from_id, document)
                || fallbackRangeFromText(document, document.getText(), eventName),
            text: eventName,
            eventName,
        } as FcstmAstLocalTrigger;
    }

    const directChainNode = contextChildren(node).find(child => child.constructor?.name === 'Chain_idContext');
    if (directChainNode) {
        return buildChainTriggerFromNode(directChainNode, document);
    }

    const entryComboNode = getNodeByMethod(node, 'entry_combo_transition_trigger');
    const comboNode = getNodeByMethod(node, 'combo_transition_trigger') || entryComboNode;
    if (!comboNode) {
        return undefined;
    }

    const entryTriggerNode = getNodeByMethod(comboNode, 'entry_chain_combo_trigger');
    if (entryTriggerNode) {
        const isSingleEntryEvent = getNodesByMethod(entryTriggerNode, 'entry_chain_combo_leading_guard').length === 0
            && getNodesByMethod(entryTriggerNode, 'entry_chain_combo_trigger_term').length === 0;
        const eventTermNode = isSingleEntryEvent
            ? getNodeByMethod(entryTriggerNode, 'combo_event_term')
            : undefined;
        return eventTermNode ? buildChainTriggerFromNode(eventTermNode, document) : undefined;
    }

    const localTriggerNode = getNodeByMethod(comboNode, 'local_combo_trigger');
    if (localTriggerNode) {
        const isSingleLocalEvent = getNodesByMethod(localTriggerNode, 'local_combo_leading_guard').length === 0
            && getNodesByMethod(localTriggerNode, 'local_combo_trigger_term').length === 0;
        const eventTermNode = isSingleLocalEvent
            ? getNodeByMethod(localTriggerNode, 'local_combo_event_term')
            : undefined;
        return eventTermNode ? buildLocalTriggerFromNode(eventTermNode, document) : undefined;
    }

    const chainTriggerNode = getNodeByMethod(comboNode, 'chain_combo_trigger');
    const isSingleChainEvent = getNodesByMethod(chainTriggerNode, 'combo_trigger_term').length === 0;
    const eventTermNode = isSingleChainEvent
        ? getNodeByMethod(chainTriggerNode, 'combo_event_term')
        : undefined;
    return eventTermNode ? buildChainTriggerFromNode(eventTermNode, document) : undefined;
}

function buildTransitionGuard(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstExpression | undefined {
    const directCondNode = contextChildren(node).find(child => /Cond/.test(child.constructor?.name || ''));
    if (directCondNode) {
        return buildExpression(directCondNode, document);
    }

    const comboNode = getNodeByMethod(node, 'combo_transition_trigger')
        || getNodeByMethod(node, 'entry_combo_transition_trigger');
    if (!comboNode) {
        return undefined;
    }

    const legacyCondNode = getNodeByMethod(comboNode, 'cond_expression');
    if (legacyCondNode) {
        return buildExpression(legacyCondNode, document);
    }

    const chainTriggerNode = getNodeByMethod(comboNode, 'chain_combo_trigger');
    const aliasNode = getNodeByMethod(chainTriggerNode, 'chain_combo_guard_alias');
    const guardTermNode = getNodeByMethod(aliasNode, 'combo_guard_term');
    const condNode = getNodeByMethod(guardTermNode, 'cond_expression');
    return condNode ? buildExpression(condNode, document) : undefined;
}

function buildTransitionLikeBase(
    node: ParseTreeContext,
    document: TextDocumentLike
): Omit<FcstmAstTransition, 'kind' | 'transitionKind' | 'pyNodeType'> {
    const nodeName = node.constructor?.name || '';
    const sourceKind = /AllForce/.test(nodeName)
        ? 'all'
        : /EntryTransition/.test(nodeName)
            ? 'init'
            : 'state';
    const targetKind = /Exit/.test(nodeName) ? 'exit' : 'state';
    const effectNode = contextChildren(node).find(child => child.constructor?.name === 'Operational_statement_setContext');
    const trigger = buildTrigger(node, document);
    const comboTrigger = buildComboTriggerFromSyntax(node, document);
    const guard = buildTransitionGuard(node, document);
    const effect = effectNode ? buildOperationBlockFromStatementSet(effectNode, document) : undefined;
    const eventId = trigger
        ? trigger.kind === 'localTrigger'
            ? buildLocalEventPath(sourceKind, tokenText(node.from_state), trigger.eventName, trigger.range)
            : sourceKind === 'init'
                ? buildEntryEventPath(trigger.eventPath)
                : trigger.eventPath
        : undefined;
    const fromState = sourceKind === 'init'
        ? 'INIT_STATE'
        : sourceKind === 'all'
            ? 'ALL'
            : tokenText(node.from_state);
    const toState = targetKind === 'exit'
        ? 'EXIT_STATE'
        : tokenText(node.to_state);

    return {
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        sourceStateName: tokenText(node.from_state),
        targetStateName: tokenText(node.to_state),
        sourceKind,
        targetKind,
        trigger,
        comboTrigger,
        combo_trigger: comboTrigger,
        guard,
        effect,
        fromState,
        from_state: fromState,
        toState,
        to_state: toState,
        eventId,
        event_id: eventId,
        conditionExpr: guard,
        condition_expr: guard,
        postOperations: effect?.statements || [],
        post_operations: effect?.statements || [],
    };
}

function buildTransition(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstTransition {
    const nodeName = node.constructor?.name || '';
    return {
        kind: 'transition',
        pyNodeType: 'TransitionDefinition',
        transitionKind: nodeName.startsWith('Entry')
            ? 'entry'
            : nodeName.startsWith('Exit')
                ? 'exit'
                : 'normal',
        ...buildTransitionLikeBase(node, document),
    };
}

function buildForcedTransition(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstForcedTransition {
    const nodeName = node.constructor?.name || '';
    return {
        kind: 'forcedTransition',
        pyNodeType: 'ForceTransitionDefinition',
        transitionKind: nodeName.startsWith('ExitAll')
            ? 'exitAll'
            : nodeName.startsWith('NormalAll')
                ? 'normalAll'
                : nodeName.startsWith('Exit')
                    ? 'exit'
                    : 'normal',
        ...buildTransitionLikeBase(node, document),
    };
}

function buildAction(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstAction {
    const nodeName = node.constructor?.name || '';
    const stage: FcstmAstAction['stage'] = nodeName.startsWith('Exit')
        ? 'exit'
        : nodeName.startsWith('During')
            ? 'during'
            : 'enter';
    const mode: FcstmAstAction['mode'] = nodeName.includes('Abstract')
        ? 'abstract'
        : nodeName.includes('Ref')
            ? 'ref'
            : 'operations';
    const isGlobalAspect = nodeName.startsWith('DuringAspect');
    const chainNode = contextChildren(node).find(child => child.constructor?.name === 'Chain_idContext');
    const statementSet = contextChildren(node).find(child => child.constructor?.name === 'Operational_statement_setContext');
    const refPath = chainNode ? buildChainPath(chainNode, document) : undefined;
    const operationBlock = statementSet ? buildOperationBlockFromStatementSet(statementSet, document) : undefined;
    const operations = mode === 'operations' ? operationBlock?.statements || [] : undefined;
    const doc = node.raw_doc ? formatMultilineComment(tokenText(node.raw_doc)) : undefined;
    const name = tokenText(node.func_name) || undefined;
    return {
        kind: 'action',
        pyNodeType: buildActionPyNodeType(stage, mode, isGlobalAspect),
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        stage,
        aspect: (tokenText(node.aspect) || undefined) as 'before' | 'after' | undefined,
        isGlobalAspect,
        mode,
        name,
        nameRange: name
            ? (makeTokenRange(node.func_name, document)
                || fallbackRangeFromText(document, document.getText(), name))
            : undefined,
        operationBlock,
        operation_block: operationBlock,
        operations,
        operationsList: operations || [],
        refPath,
        ref: mode === 'ref' ? refPath : undefined,
        doc,
    };
}

function buildImportDefSelector(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstImportDefSelector {
    const nodeName = node.constructor?.name || '';
    const range = getNodeRange(node, document, nodeText(node));
    const text = nodeText(node);

    if (nodeName === 'ImportDefFallbackSelectorContext') {
        return {
            kind: 'importDefFallbackSelector',
            pyNodeType: 'ImportDefFallbackSelector',
            range,
            text,
        } as FcstmAstImportDefFallbackSelector;
    }

    if (nodeName === 'ImportDefSetSelectorContext') {
        return {
            kind: 'importDefSetSelector',
            pyNodeType: 'ImportDefSetSelector',
            range,
            text,
            names: (node.selector_items || []).map(item => tokenText(item)),
        } as FcstmAstImportDefSetSelector;
    }

    if (nodeName === 'ImportDefPatternSelectorContext') {
        return {
            kind: 'importDefPatternSelector',
            pyNodeType: 'ImportDefPatternSelector',
            range,
            text,
            pattern: tokenText(node.selector_pattern),
        } as FcstmAstImportDefPatternSelector;
    }

    return {
        kind: 'importDefExactSelector',
        pyNodeType: 'ImportDefExactSelector',
        range,
        text,
        name: tokenText(node.selector_name),
    } as FcstmAstImportDefExactSelector;
}

function buildImportDefTargetTemplate(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstImportDefTargetTemplate {
    const template = tokenText(node.target_text) || nodeText(node);
    return {
        kind: 'importDefTargetTemplate',
        pyNodeType: 'ImportDefTargetTemplate',
        range: getNodeRange(node, document, template),
        text: template,
        template,
    };
}

function buildImportMapping(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstImportMapping | null {
    const inner = firstContextChild(node) || node;
    const nodeName = inner.constructor?.name || '';

    if (nodeName === 'Import_def_mappingContext') {
        const selectorNode = contextChildren(inner).find(child => /ImportDef.*SelectorContext$/.test(child.constructor?.name || ''));
        const templateNode = contextChildren(inner).find(child => child.constructor?.name === 'Import_def_target_templateContext');
        const targetTemplateNode = buildImportDefTargetTemplate(templateNode as ParseTreeContext, document);
        return {
            kind: 'importDefMapping',
            pyNodeType: 'ImportDefMapping',
            range: getNodeRange(inner, document, nodeText(inner)),
            text: nodeText(inner),
            selector: buildImportDefSelector(selectorNode as ParseTreeContext, document),
            targetTemplate: targetTemplateNode.template,
            targetTemplateNode,
            target_template: targetTemplateNode,
        } as FcstmAstImportDefMapping;
    }

    if (nodeName === 'Import_event_mappingContext') {
        const childContexts = contextChildren(inner).filter(child => child.constructor?.name === 'Chain_idContext');
        const sourceEvent = buildChainPath(childContexts[0], document);
        const targetEvent = buildChainPath(childContexts[1], document);
        const extraName = unquoteTokenValue(inner.extra_name);
        return {
            kind: 'importEventMapping',
            pyNodeType: 'ImportEventMapping',
            range: getNodeRange(inner, document, nodeText(inner)),
            text: nodeText(inner),
            sourceEvent,
            source_event: sourceEvent,
            targetEvent,
            target_event: targetEvent,
            displayName: extraName,
            extraName,
            extra_name: extraName,
        } as FcstmAstImportEventMapping;
    }

    return null;
}

function buildImport(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstImportStatement {
    const mappings = contextChildren(node)
        .filter(child => child.constructor?.name === 'Import_mapping_statementContext')
        .map(child => buildImportMapping(child, document))
        .filter(Boolean) as FcstmAstImportMapping[];

    const sourcePath = unquoteText(tokenText(node.import_path));
    const extraName = unquoteTokenValue(node.extra_name);
    return {
        kind: 'importStatement',
        pyNodeType: 'ImportStatement',
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        sourcePath,
        source_path: sourcePath,
        alias: tokenText(node.state_alias),
        displayName: extraName,
        extraName,
        extra_name: extraName,
        pathRange: makeTokenRange(node.import_path, document)
            || fallbackRangeFromText(document, document.getText(), tokenText(node.import_path)),
        aliasRange: makeTokenRange(node.state_alias, document)
            || fallbackRangeFromText(document, document.getText(), tokenText(node.state_alias)),
        mappings,
    };
}

function buildStateStatement(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstStateStatement | null {
    const inner = firstContextChild(node) || node;
    const nodeName = inner.constructor?.name || '';

    if (nodeName === 'LeafStateDefinitionContext' || nodeName === 'CompositeStateDefinitionContext') {
        return buildStateDefinition(inner, document);
    }
    if (/ForceTransitionDefinitionContext$/.test(nodeName)) {
        return buildForcedTransition(inner, document);
    }
    if (/TransitionDefinitionContext$/.test(nodeName)) {
        return buildTransition(inner, document);
    }
    if (/Enter|Exit|During/.test(nodeName)) {
        return buildAction(inner, document);
    }
    if (nodeName === 'Event_definitionContext') {
        return buildEventDefinition(inner, document);
    }
    if (nodeName === 'Import_statementContext') {
        return buildImport(inner, document);
    }

    return null;
}

function buildEventDefinition(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstEventDefinition {
    const extraName = unquoteTokenValue(node.extra_name);
    const name = tokenText(node.event_name);
    return {
        kind: 'eventDefinition',
        pyNodeType: 'EventDefinition',
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        name,
        nameRange: makeTokenRange(node.event_name, document)
            || fallbackRangeFromText(document, document.getText(), name),
        displayName: extraName,
        extraName,
        extra_name: extraName,
    };
}

function buildStateDefinition(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstStateDefinition {
    const hasBraceBody = node.constructor?.name === 'CompositeStateDefinitionContext';
    const statements = hasBraceBody
        ? contextChildren(node)
            .filter(child => child.constructor?.name === 'State_inner_statementContext')
            .map(child => buildStateStatement(child, document))
            .filter(Boolean) as FcstmAstStateStatement[]
        : [];

    const extraName = unquoteTokenValue(node.extra_name);
    const name = tokenText(node.state_id);
    const substates = statements.filter(item => item.kind === 'stateDefinition') as FcstmAstStateDefinition[];
    const transitions = statements.filter(item => item.kind === 'transition') as FcstmAstTransition[];
    const forceTransitions = statements.filter(item => item.kind === 'forcedTransition') as FcstmAstForcedTransition[];
    const events = statements.filter(item => item.kind === 'eventDefinition') as FcstmAstEventDefinition[];
    const imports = statements.filter(item => item.kind === 'importStatement') as FcstmAstImportStatement[];
    // ``composite`` follows the pyfcstm semantic rule: it is true iff the
    // state has at least one substate (a direct ``state X;`` child) or
    // at least one ``import ... as Alias`` that gets merged in as a
    // substate by the workspace-assembly phase. A ``state X { enter
    // { ... } }`` with neither is semantically a leaf even though the
    // grammar uses the ``{ ... }`` form.
    const composite = substates.length > 0 || imports.length > 0;
    const enters = statements.filter(item => item.kind === 'action' && item.stage === 'enter') as FcstmAstAction[];
    const durings = statements.filter(
        item => item.kind === 'action' && item.stage === 'during' && !item.isGlobalAspect
    ) as FcstmAstAction[];
    const exits = statements.filter(item => item.kind === 'action' && item.stage === 'exit') as FcstmAstAction[];
    const duringAspects = statements.filter(
        item => item.kind === 'action' && item.stage === 'during' && item.isGlobalAspect
    ) as FcstmAstAction[];
    return {
        kind: 'stateDefinition',
        pyNodeType: 'StateDefinition',
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        name,
        nameRange: makeTokenRange(node.state_id, document)
            || fallbackRangeFromText(document, document.getText(), name),
        displayName: extraName,
        extraName,
        extra_name: extraName,
        pseudo: Boolean((node as ParseTreeContext).pseudo),
        isPseudo: Boolean((node as ParseTreeContext).pseudo),
        is_pseudo: Boolean((node as ParseTreeContext).pseudo),
        composite,
        statements,
        events,
        imports,
        substates,
        transitions,
        enters,
        durings,
        exits,
        duringAspects,
        during_aspects: duringAspects,
        forceTransitions,
        force_transitions: forceTransitions,
    };
}

function buildVariableDefinition(
    node: ParseTreeContext,
    document: TextDocumentLike
): FcstmAstVariableDefinition {
    const expressionNode = contextChildren(node).find(child => /InitContext$/.test(child.constructor?.name || ''));
    const terminals = terminalChildren(node);
    const valueType = tokenText((node as ParseTreeContext).deftype) === 'float' ? 'float' : 'int';
    const initializer = buildExpression(expressionNode as ParseTreeContext, document);
    return {
        kind: 'variableDefinition',
        pyNodeType: 'DefAssignment',
        range: getNodeRange(node, document, nodeText(node)),
        text: nodeText(node),
        name: terminals[2]?.getText?.() || '',
        type: valueType,
        valueType,
        deftype: valueType,
        initializer,
        expr: initializer,
    };
}

/**
 * Build a jsfcstm AST document from a parser-generated FCSTM parse tree.
 *
 * The returned structure preserves pyfcstm-compatible field aliases such as
 * ``definitions`` and ``root_state`` while retaining editor-friendly metadata
 * such as ranges and source text.
 */
export function buildAstFromTree(
    tree: ParseTreeNode,
    document: TextDocumentLike
): FcstmAstDocument | null {
    if (!tree) {
        return null;
    }

    const childContexts = contextChildren(tree);
    const variables = childContexts
        .filter(child => child.constructor?.name === 'Def_assignmentContext')
        .map(child => buildVariableDefinition(child, document));
    const rootStateNode = childContexts.find(child => {
        const name = child.constructor?.name || '';
        return name === 'LeafStateDefinitionContext' || name === 'CompositeStateDefinitionContext';
    });
    const rootState = rootStateNode ? buildStateDefinition(rootStateNode, document) : undefined;

    return {
        kind: 'document',
        pyNodeType: 'StateMachineDSLProgram',
        range: getNodeRange(tree, document, document.getText()),
        text: document.getText(),
        filePath: getDocumentFilePath(document),
        variables,
        definitions: variables,
        rootState,
        root_state: rootState,
    };
}

/**
 * Parse a document and convert it into the jsfcstm AST model.
 */
export async function parseAstDocument(
    document: TextDocumentLike
): Promise<FcstmAstDocument | null> {
    try {
        const tree = await getParser().parseTree(document.getText());
        if (!tree) {
            return null;
        }

        return buildAstFromTree(tree as ParseTreeNode, document);
    } catch (err) {
        // Barrier around the antlr4 parser plus the AST builder. The
        // builder routinely receives PARTIAL parse trees while the user
        // types in the editor (e.g. ``def `` mid-edit). Partial trees
        // make ``buildAstFromTree`` reach undefined children and raise
        // ``TypeError`` on ``.constructor`` access -- this is the
        // documented degrade-to-null behavior the LSP relies on. We
        // therefore accept any ``Error`` subclass here, but still
        // re-raise non-Error throws (raw strings / numbers), which can
        // only happen via misuse and indicate a programmer bug.
        if (!(err instanceof Error)) {
            throw err;
        }
        return null;
    }
}
