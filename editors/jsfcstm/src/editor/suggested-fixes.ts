import type {
    FcstmAstAssignmentStatement,
    FcstmAstIfStatement,
    FcstmAstOperationStatement,
} from '../ast';
import type {FcstmSemanticDocument, FcstmSemanticTransition} from '../semantics';
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

function variableDeclarationRange(
    document: TextDocumentLike,
    range: TextRange,
    text: string,
): TextRange {
    const line = document.lineAt(range.start.line).text;
    if (trimComparable(line) === trimComparable(text)) {
        return fullLineRange(document, range);
    }
    return range;
}

export function variableDefinitionRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    varName: string,
): TextRange | null {
    const variables = semantic.variables.filter(item => item.name === varName);
    if (variables.length !== 1) return null;
    const variable = variables[0];
    return variableDeclarationRange(document, variable.range, variable.ast.text);
}

export function firstVariableDefinitionRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    varName: string,
): TextRange | null {
    const variables = semantic.variables.filter(item => item.name === varName);
    if (variables.length === 0) return null;
    const variable = variables
        .slice()
        .sort((left, right) => (
            left.range.start.line - right.range.start.line ||
            left.range.start.character - right.range.start.character
        ))[0];
    return variableDeclarationRange(document, variable.range, variable.ast.text);
}

export function resolveStatePath(semantic: FcstmSemanticDocument, statePath: string) {
    return semantic.states.find(item => item.identity.qualifiedName === statePath);
}

function resolveStateId(semantic: FcstmSemanticDocument, stateId: string | undefined) {
    if (!stateId) return undefined;
    return semantic.states.find(item => item.identity.id === stateId);
}

function textAtIndent(text: string, indent: string): string {
    const trimmed = text.trimEnd();
    if (trimmed.length === 0) return '';
    return trimmed
        .split('\n')
        .map(line => line.length > 0 ? `${indent}${line}` : line)
        .join('\n');
}

function insertionAfterLinePlan(
    document: TextDocumentLike,
    line: number,
    newText: string,
): SuggestedFixEditPlan {
    if (line + 1 < document.lineCount) {
        return {
            range: createRange(line + 1, 0, line + 1, 0),
            newText,
        };
    }
    const lineText = document.lineAt(line).text;
    return {
        range: createRange(line, lineText.length, line, lineText.length),
        newText: `\n${newText}`,
    };
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

function insertionBeforeStateClose(
    document: TextDocumentLike,
    stateRange: TextRange,
    text: string,
): SuggestedFixEditPlan | null {
    const closeLine = stateRange.end.line;
    const lineText = document.lineAt(closeLine).text;
    const searchEnd = Math.min(stateRange.end.character, lineText.length);
    const closeColumn = lineText.lastIndexOf('}', Math.max(0, searchEnd - 1));
    if (closeColumn < 0) return null;
    const parentIndent = lineIndent(document, stateRange.start.line);
    const inserted = textAtIndent(text, `${parentIndent}    `);
    if (inserted.length === 0) return null;
    return {
        range: createRange(closeLine, closeColumn, closeLine, closeColumn),
        newText: `\n${inserted}\n${parentIndent}`,
    };
}

function deadlockLeafInsertion(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    statePath: string,
    text: string,
): SuggestedFixEditPlan | null {
    const state = resolveStatePath(semantic, statePath);
    if (!state) return null;
    const parent = resolveStateId(semantic, state.parentStateId);
    if (!parent) return null;
    const newText = indentedTextForInsertion(document, state.range, text);
    if (state.range.end.line < parent.range.end.line) {
        return insertionAfterLinePlan(document, state.range.end.line, newText);
    }
    return insertionBeforeStateClose(document, parent.range, text);
}

function initialTransitionInsertion(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    compositePath: string,
    text: string,
): SuggestedFixEditPlan | null {
    const composite = resolveStatePath(semantic, compositePath);
    if (!composite) return null;
    const initialTransitions = semantic.transitions
        .filter(item => item.ownerStateId === composite.identity.id && item.sourceKind === 'init')
        .sort((a, b) => (
            a.range.end.line - b.range.end.line ||
            a.range.end.character - b.range.end.character
        ));
    const lastInitial = initialTransitions[initialTransitions.length - 1];
    if (lastInitial) {
        const newText = indentedTextForInsertion(document, lastInitial.range, text);
        if (lastInitial.range.end.line < composite.range.end.line) {
            return insertionAfterLinePlan(document, lastInitial.range.end.line, newText);
        }
        return insertionBeforeStateClose(document, composite.range, text);
    }
    const firstChild = semantic.states.find(item => item.parentStateId === composite.identity.id);
    if (!firstChild) return null;
    const newText = indentedTextForInsertion(document, firstChild.range, text);
    if (firstChild.range.end.line < composite.range.end.line) {
        return insertionAfterLinePlan(document, firstChild.range.end.line, newText);
    }
    return insertionBeforeStateClose(document, composite.range, text);
}

function isSelfAssignStatement(statement: FcstmAstAssignmentStatement, varName: string): boolean {
    return statement.targetName === varName &&
        statement.expression.expressionKind === 'identifier' &&
        statement.expression.name === varName;
}

function collectSelfAssignStatements(
    statements: readonly FcstmAstOperationStatement[],
    varName: string,
    out: FcstmAstAssignmentStatement[],
): void {
    for (const statement of statements) {
        if (statement.kind === 'assignmentStatement' && isSelfAssignStatement(statement, varName)) {
            out.push(statement);
        }
        if (statement.kind === 'ifStatement') {
            collectSelfAssignsInIf(statement, varName, out);
        }
    }
}

function collectSelfAssignsInIf(
    statement: FcstmAstIfStatement,
    varName: string,
    out: FcstmAstAssignmentStatement[],
): void {
    for (const branch of statement.branches) {
        collectSelfAssignStatements(branch.statements, varName, out);
    }
}

export function effectSelfAssignRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    statePath: string | undefined,
    varName: string,
    occurrenceIndex?: number,
    selectedTransition?: FcstmSemanticTransition,
): TextRange | null {
    const matches: TextRange[] = [];
    const transitions = selectedTransition ? [selectedTransition] : semantic.transitions;
    for (const transition of transitions) {
        if (statePath === '[*]') {
            if (transition.sourceKind !== 'init') continue;
        } else if (statePath && transition.sourceStatePath?.join('.') !== statePath) {
            continue;
        }
        const statements: FcstmAstAssignmentStatement[] = [];
        collectSelfAssignStatements(transition.ast.effect?.statements ?? [], varName, statements);
        for (const statement of statements) {
            matches.push(statementDeleteRange(document, statement));
        }
    }
    if (occurrenceIndex !== undefined) {
        return matches[occurrenceIndex] ?? null;
    }
    return matches.length === 1 ? matches[0] : null;
}

export function spanLikeToRange(value: unknown): TextRange | null {
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
        const statePath = typeof diagnostic.data.state_path === 'string' ? diagnostic.data.state_path : undefined;
        if (!statePath || statePath === '[*]') return null;
        const range = effectSelfAssignRange(
            document,
            semantic,
            statePath,
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

export function suggestedFixIssueRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    diagnostic: FcstmDiagnostic,
): TextRange {
    const payload = suggestedFixFromDiagnostic(diagnostic);
    if (!payload) return diagnostic.range;

    if (payload.target === 'variable_definition' && typeof diagnostic.data?.var_name === 'string') {
        return variableDefinitionRange(document, semantic, diagnostic.data.var_name) ?? diagnostic.range;
    }
    if (payload.target === 'effect_self_assign_statement' && typeof diagnostic.data?.var_name === 'string') {
        const statePath = typeof diagnostic.data.state_path === 'string' ? diagnostic.data.state_path : undefined;
        if (!statePath || statePath === '[*]') return diagnostic.range;
        return effectSelfAssignRange(
            document,
            semantic,
            statePath,
            diagnostic.data.var_name,
        ) ?? diagnostic.range;
    }
    if (payload.target === 'deadlock_leaf_exit_transition' && typeof diagnostic.data?.state_path === 'string') {
        return resolveStatePath(semantic, diagnostic.data.state_path)?.range ?? diagnostic.range;
    }
    if (payload.target === 'unconditional_initial_transition' && typeof diagnostic.data?.composite_path === 'string') {
        return resolveStatePath(semantic, diagnostic.data.composite_path)?.range ?? diagnostic.range;
    }
    return diagnostic.range;
}

export function suggestedFixDiagnosticRange(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    diagnostic: FcstmDiagnostic,
): TextRange {
    const plan = planSuggestedFixEdit(document, semantic, diagnostic);
    return plan?.range ?? diagnostic.range;
}
