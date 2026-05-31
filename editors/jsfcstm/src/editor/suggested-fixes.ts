import type {
    FcstmAstAssignmentStatement,
    FcstmAstIfStatement,
    FcstmAstOperationStatement,
} from '../ast';
import type {FcstmSemanticDocument} from '../semantics';
import {
    createRange,
    FcstmDiagnostic,
    TextDocumentLike,
    TextRange,
} from '../utils/text';
export interface SuggestedFixEditPlan {
    range: TextRange;
    newText: string;
}

interface SuggestedFixPayload {
    kind: 'insert' | 'delete' | 'replace';
    target: string;
    anchor: {
        type: 'ref';
        ref: string;
    };
    text: string;
    rationale: string;
}

function isSuggestedFixPayload(value: unknown): value is SuggestedFixPayload {
    if (typeof value !== 'object' || value === null) return false;
    const payload = value as Record<string, unknown>;
    const anchor = payload.anchor;
    return (
        (payload.kind === 'insert' || payload.kind === 'delete' || payload.kind === 'replace') &&
        typeof payload.target === 'string' &&
        typeof payload.text === 'string' &&
        typeof payload.rationale === 'string' &&
        typeof anchor === 'object' &&
        anchor !== null &&
        (anchor as Record<string, unknown>).type === 'ref' &&
        typeof (anchor as Record<string, unknown>).ref === 'string'
    );
}

export function suggestedFixFromDiagnostic(diagnostic: FcstmDiagnostic): SuggestedFixPayload | null {
    const data = diagnostic.data;
    if (!data) return null;
    const direct = data.suggested_fix;
    if (isSuggestedFixPayload(direct)) return direct;
    const refs = data.refs;
    if (typeof refs === 'object' && refs !== null) {
        const nested = (refs as Record<string, unknown>).suggested_fix;
        if (isSuggestedFixPayload(nested)) return nested;
    }
    return null;
}

function lineIndent(document: TextDocumentLike, line: number): string {
    const text = document.lineAt(Math.max(0, Math.min(line, document.lineCount - 1))).text;
    return text.match(/^\s*/)?.[0] ?? '';
}

function fullLineRange(document: TextDocumentLike, range: TextRange): TextRange {
    const startLine = range.start.line;
    if (startLine + 1 < document.lineCount) {
        return createRange(startLine, 0, startLine + 1, 0);
    }
    const lineText = document.lineAt(startLine).text;
    return createRange(startLine, 0, startLine, lineText.length);
}

function trimComparable(value: string): string {
    return value.trim().replace(/\s+/g, ' ');
}

function statementDeleteRange(document: TextDocumentLike, statement: FcstmAstAssignmentStatement): TextRange {
    const line = document.lineAt(statement.range.start.line).text;
    if (trimComparable(line) === trimComparable(statement.text)) {
        return fullLineRange(document, statement.range);
    }
    return statement.range;
}

function variableDefinitionRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    varName: string,
): TextRange | null {
    const variable = semantic.variables.find(item => item.name === varName);
    return variable ? fullLineRange(document, variable.range) : null;
}

function resolveStatePath(semantic: FcstmSemanticDocument, statePath: string) {
    return semantic.states.find(item => item.identity.qualifiedName === statePath);
}

function insertionAfterLine(line: number): TextRange {
    return createRange(line + 1, 0, line + 1, 0);
}

function indentedTextForInsertion(
    document: TextDocumentLike,
    range: TextRange,
    text: string,
): string {
    if (text.length === 0) return text;
    const indent = lineIndent(document, range.start.line);
    return text
        .split('\n')
        .map((line, index, lines) => {
            if (line === '' && index === lines.length - 1) return line;
            return line.startsWith(indent) ? line : `${indent}${line}`;
        })
        .join('\n');
}

function deadlockLeafInsertion(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    statePath: string,
    text: string,
): SuggestedFixEditPlan | null {
    const state = resolveStatePath(semantic, statePath);
    if (!state) return null;
    const range = insertionAfterLine(state.range.end.line);
    return {
        range,
        newText: indentedTextForInsertion(document, state.range, text),
    };
}

function initialTransitionInsertion(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    compositePath: string,
    text: string,
): SuggestedFixEditPlan | null {
    const composite = resolveStatePath(semantic, compositePath);
    if (!composite) return null;
    const firstChild = semantic.states.find(item => item.parentStateId === composite.identity.id);
    const anchorRange = firstChild?.range ?? composite.range;
    const range = insertionAfterLine(anchorRange.end.line);
    return {
        range,
        newText: indentedTextForInsertion(document, anchorRange, text),
    };
}

function isSelfAssignStatement(statement: FcstmAstAssignmentStatement, varName: string): boolean {
    return statement.targetName === varName &&
        statement.expression.expressionKind === 'identifier' &&
        statement.expression.name === varName;
}

function findSelfAssignStatement(
    statements: readonly FcstmAstOperationStatement[],
    varName: string,
): FcstmAstAssignmentStatement | null {
    for (const statement of statements) {
        if (statement.kind === 'assignmentStatement' && isSelfAssignStatement(statement, varName)) {
            return statement;
        }
        if (statement.kind === 'ifStatement') {
            const found = findSelfAssignInIf(statement, varName);
            if (found) return found;
        }
    }
    return null;
}

function findSelfAssignInIf(
    statement: FcstmAstIfStatement,
    varName: string,
): FcstmAstAssignmentStatement | null {
    for (const branch of statement.branches) {
        const found = findSelfAssignStatement(branch.statements, varName);
        if (found) return found;
    }
    return null;
}

function effectSelfAssignRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    statePath: string | undefined,
    varName: string,
): TextRange | null {
    for (const transition of semantic.transitions) {
        if (statePath && transition.sourceStatePath?.join('.') !== statePath) continue;
        const statement = findSelfAssignStatement(transition.ast.effect?.statements ?? [], varName);
        if (statement) return statementDeleteRange(document, statement);
    }
    return null;
}

function spanLikeToRange(value: unknown): TextRange | null {
    if (typeof value !== 'object' || value === null) return null;
    const obj = value as Record<string, unknown>;
    const start = obj.start as Record<string, unknown> | undefined;
    const end = obj.end as Record<string, unknown> | undefined;
    if (
        typeof start?.line === 'number' &&
        typeof start?.character === 'number' &&
        typeof end?.line === 'number' &&
        typeof end?.character === 'number'
    ) {
        return createRange(start.line, start.character, end.line, end.character);
    }
    if (typeof obj.line === 'number' && typeof obj.column === 'number') {
        const startLine = Math.max(0, obj.line - 1);
        const startColumn = Math.max(0, obj.column - 1);
        const endLine = typeof obj.end_line === 'number' ? Math.max(0, obj.end_line - 1) : startLine;
        const endColumn = typeof obj.end_column === 'number' ? Math.max(0, obj.end_column - 1) : startColumn;
        return createRange(startLine, startColumn, endLine, endColumn);
    }
    return null;
}

function referencedValue(
    diagnostic: FcstmDiagnostic,
    payload: SuggestedFixPayload,
): unknown {
    const ref = payload.anchor.ref;
    if (!ref.startsWith('refs.')) return undefined;
    const field = ref.slice('refs.'.length);
    const direct = diagnostic.data?.[field];
    if (direct !== undefined) return direct;
    const refs = diagnostic.data?.refs;
    if (typeof refs === 'object' && refs !== null) {
        return (refs as Record<string, unknown>)[field];
    }
    return undefined;
}

export function planSuggestedFixEdit(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    diagnostic: FcstmDiagnostic,
): SuggestedFixEditPlan | null {
    const payload = suggestedFixFromDiagnostic(diagnostic);
    if (!payload) return null;
    const anchorValue = referencedValue(diagnostic, payload);
    if (anchorValue === undefined || anchorValue === null) return null;

    if (payload.target === 'variable_definition' && typeof diagnostic.data?.var_name === 'string') {
        const range = variableDefinitionRange(document, semantic, diagnostic.data.var_name);
        return range ? {range, newText: ''} : null;
    }
    if (payload.target === 'effect_self_assign_statement' && typeof diagnostic.data?.var_name === 'string') {
        const range = effectSelfAssignRange(
            document,
            semantic,
            typeof diagnostic.data.state_path === 'string' ? diagnostic.data.state_path : undefined,
            diagnostic.data.var_name,
        );
        return range ? {range, newText: ''} : null;
    }
    if (payload.target === 'deadlock_leaf_exit_transition' && typeof diagnostic.data?.state_path === 'string') {
        return deadlockLeafInsertion(document, semantic, diagnostic.data.state_path, payload.text);
    }
    if (payload.target === 'unconditional_initial_transition' && typeof diagnostic.data?.composite_path === 'string') {
        return initialTransitionInsertion(document, semantic, diagnostic.data.composite_path, payload.text);
    }

    const spanRange = spanLikeToRange(anchorValue);
    if (!spanRange) return null;
    if (payload.kind === 'insert') {
        return {
            range: createRange(
                spanRange.end.line,
                spanRange.end.character,
                spanRange.end.line,
                spanRange.end.character,
            ),
            newText: payload.text,
        };
    }
    return {
        range: spanRange,
        newText: payload.kind === 'delete' ? '' : payload.text,
    };
}

export function suggestedFixDiagnosticRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    diagnostic: FcstmDiagnostic,
): TextRange {
    const plan = planSuggestedFixEdit(document, semantic, diagnostic);
    return plan?.range ?? diagnostic.range;
}
