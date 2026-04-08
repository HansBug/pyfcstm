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
        } else {
            result += next;
            index += 1;
        }
    }

    return result;
}

function unquoteText(value: string | undefined): string {
    if (!value) {
        return '';
    }
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
    if (!rawDoc) {
        return undefined;
    }

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
    if (nonEmptyLines.length === 0) {
        return '';
    }

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

function canonicalizeBinaryOperator(operator: string): string {
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
        const operand = buildExpression(childContexts[0], document);
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
        const operator = canonicalizeBinaryOperator(tokenText(node.op));
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
        const condition = buildExpression(childContexts[0], document);
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

    const chainNode = contextChildren(node).find(child => child.constructor?.name === 'Chain_idContext');
    if (chainNode) {
        return {
            kind: 'chainTrigger',
            range: getNodeRange(chainNode, document, nodeText(chainNode)),
            text: nodeText(chainNode),
            eventPath: buildChainPath(chainNode, document),
        } as FcstmAstChainTrigger;
    }

    return undefined;
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
    const condNode = contextChildren(node).find(child => /Cond/.test(child.constructor?.name || ''));
    const effectNode = contextChildren(node).find(child => child.constructor?.name === 'Operational_statement_setContext');
    const trigger = buildTrigger(node, document);
    const guard = condNode ? buildExpression(condNode, document) : undefined;
    const effect = effectNode ? buildOperationBlockFromStatementSet(effectNode, document) : undefined;
    const eventId = trigger
        ? trigger.kind === 'localTrigger'
            ? buildLocalEventPath(sourceKind, tokenText(node.from_state), trigger.eventName, trigger.range)
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
    const composite = node.constructor?.name === 'CompositeStateDefinitionContext';
    const statements = composite
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
    } catch {
        return null;
    }
}
