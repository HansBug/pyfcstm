import {pathToFileURL} from 'node:url';

import type {
    FcstmAstAction,
    FcstmAstExpression,
    FcstmAstIfStatement,
    FcstmAstOperationStatement,
} from '../ast';
import type {
    FcstmSemanticAction,
    FcstmSemanticDocument,
    FcstmSemanticEvent,
    FcstmSemanticImport,
    FcstmSemanticState,
    FcstmSemanticTransition,
    FcstmSemanticVariable,
} from '../semantics';
import {
    createRange,
    getDocumentFilePath,
    rangeContains,
    TextDocumentLike,
    TextPositionLike,
    TextRange,
} from '../utils/text';
import {getWorkspaceGraph, type FcstmWorkspaceGraphNode, type FcstmWorkspaceGraphSnapshot} from '../workspace';
import {findIdentifierRange, rangeIntersects, rangeLength} from './ranges';
import type {FcstmDefinitionLocation} from './navigation';

export type FcstmReferenceSymbolKind = 'variable' | 'state' | 'event' | 'action' | 'import';
export type FcstmSymbolOccurrenceRole = 'definition' | 'reference' | 'write';
export type FcstmDocumentHighlightKind = 'text' | 'read' | 'write';

export interface FcstmReferenceLocation extends FcstmDefinitionLocation {
    role: FcstmSymbolOccurrenceRole;
}

export interface FcstmDocumentHighlight {
    range: TextRange;
    kind: FcstmDocumentHighlightKind;
}

export interface FcstmWorkspaceSymbol {
    name: string;
    kind: FcstmReferenceSymbolKind;
    containerName?: string;
    location: FcstmDefinitionLocation;
}

export interface FcstmTextEdit {
    range: TextRange;
    newText: string;
}

export interface FcstmWorkspaceEdit {
    changes: Record<string, FcstmTextEdit[]>;
}

export interface FcstmRenameRange {
    range: TextRange;
    placeholder: string;
}

interface FcstmSymbolOccurrence {
    key: string;
    kind: FcstmReferenceSymbolKind;
    name: string;
    qualifiedName: string;
    filePath: string;
    range: TextRange;
    role: FcstmSymbolOccurrenceRole;
    containerName?: string;
    renameable: boolean;
}

interface FcstmWorkspaceSymbolGraph {
    rootFile: string;
    occurrences: FcstmSymbolOccurrence[];
    rootDocument: TextDocumentLike;
}

const IDENTIFIER_NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

function toFileUri(filePath: string): string {
    return pathToFileURL(filePath).toString();
}

function makeLocation(filePath: string, range: TextRange): FcstmDefinitionLocation {
    return {
        uri: toFileUri(filePath),
        range,
    };
}

function dedupeOccurrences(occurrences: FcstmSymbolOccurrence[]): FcstmSymbolOccurrence[] {
    const seen = new Set<string>();
    const results: FcstmSymbolOccurrence[] = [];

    for (const occurrence of occurrences) {
        const key = [
            occurrence.key,
            occurrence.filePath,
            occurrence.range.start.line,
            occurrence.range.start.character,
            occurrence.range.end.line,
            occurrence.range.end.character,
            occurrence.role,
        ].join(':');
        if (seen.has(key)) {
            continue;
        }

        seen.add(key);
        results.push(occurrence);
    }

    return results;
}

function definitionOnly(occurrences: FcstmSymbolOccurrence[]): FcstmSymbolOccurrence[] {
    return occurrences.filter(item => item.role === 'definition');
}

function getContainerName(path: string[]): string | undefined {
    return path.length > 1 ? path.slice(0, -1).join('.') : undefined;
}

function findStateById(semantic: FcstmSemanticDocument, stateId?: string): FcstmSemanticState | undefined {
    if (!stateId) {
        return undefined;
    }
    return semantic.states.find(item => item.identity.id === stateId);
}

function findActionById(semantic: FcstmSemanticDocument, actionId?: string): FcstmSemanticAction | undefined {
    if (!actionId) {
        return undefined;
    }
    return semantic.actions.find(item => item.identity.id === actionId);
}

function findEventById(semantic: FcstmSemanticDocument, eventId?: string): FcstmSemanticEvent | undefined {
    if (!eventId) {
        return undefined;
    }
    return semantic.events.find(item => item.identity.id === eventId);
}

function stateAliasCountKey(ownerStatePath: string[], alias: string): string {
    return `${ownerStatePath.join('.')}::${alias}`;
}

function buildImportAliasCountMap(semantic: FcstmSemanticDocument): Map<string, number> {
    const counts = new Map<string, number>();
    for (const item of semantic.imports) {
        const key = stateAliasCountKey(item.ownerStatePath, item.alias);
        counts.set(key, (counts.get(key) || 0) + 1);
    }
    return counts;
}

function buildStateAliasKey(importItem: FcstmSemanticImport, duplicateAliasCounts: Map<string, number>): string {
    const duplicateKey = stateAliasCountKey(importItem.ownerStatePath, importItem.alias);
    if ((duplicateAliasCounts.get(duplicateKey) || 0) > 1) {
        return `import:${importItem.identity.id}`;
    }

    return `state:${importItem.identity.path.join('.')}`;
}

function findImportAlias(
    semantic: FcstmSemanticDocument,
    ownerStatePath: string[],
    stateName?: string
): FcstmSemanticImport | undefined {
    if (!stateName) {
        return undefined;
    }

    for (let length = ownerStatePath.length; length >= 1; length--) {
        const ownerPrefix = ownerStatePath.slice(0, length);
        const match = semantic.imports.find(item => (
            item.alias === stateName
            && item.ownerStatePath.length === ownerPrefix.length
            && item.ownerStatePath.every((segment, index) => segment === ownerPrefix[index])
        ));
        if (match) {
            return match;
        }
    }

    return undefined;
}

function variableOccurrenceKey(variable: FcstmSemanticVariable): string {
    return variable.identity.id;
}

function stateOccurrenceKey(state: FcstmSemanticState): string {
    return state.identity.id;
}

function eventOccurrenceKey(event: FcstmSemanticEvent): string {
    return event.identity.id;
}

function actionOccurrenceKey(action: FcstmSemanticAction): string {
    return action.identity.id;
}

function collectExpressionOccurrences(
    expression: FcstmAstExpression,
    document: TextDocumentLike,
    variablesByName: Map<string, FcstmSemanticVariable>,
    occurrences: FcstmSymbolOccurrence[]
): void {
    switch (expression.expressionKind) {
        case 'identifier': {
            const variable = variablesByName.get(expression.name);
            if (variable) {
                occurrences.push({
                    key: variableOccurrenceKey(variable),
                    kind: 'variable',
                    name: variable.name,
                    qualifiedName: variable.identity.qualifiedName,
                    filePath: getDocumentFilePath(document),
                    range: expression.range,
                    role: 'reference',
                    containerName: undefined,
                    renameable: true,
                });
            }
            break;
        }
        case 'unary':
            collectExpressionOccurrences(expression.operand, document, variablesByName, occurrences);
            break;
        case 'binary':
            collectExpressionOccurrences(expression.left, document, variablesByName, occurrences);
            collectExpressionOccurrences(expression.right, document, variablesByName, occurrences);
            break;
        case 'function':
            collectExpressionOccurrences(expression.argument, document, variablesByName, occurrences);
            break;
        case 'conditional':
            collectExpressionOccurrences(expression.condition, document, variablesByName, occurrences);
            collectExpressionOccurrences(expression.whenTrue, document, variablesByName, occurrences);
            collectExpressionOccurrences(expression.whenFalse, document, variablesByName, occurrences);
            break;
        case 'parenthesized':
            collectExpressionOccurrences(expression.expression, document, variablesByName, occurrences);
            break;
        default:
            break;
    }
}

function collectIfStatementOccurrences(
    statement: FcstmAstIfStatement,
    document: TextDocumentLike,
    variablesByName: Map<string, FcstmSemanticVariable>,
    occurrences: FcstmSymbolOccurrence[]
): void {
    for (const branch of statement.branches) {
        if (branch.condition) {
            collectExpressionOccurrences(branch.condition, document, variablesByName, occurrences);
        }
        for (const nested of branch.statements) {
            collectOperationOccurrences(nested, document, variablesByName, occurrences);
        }
    }
}

function collectOperationOccurrences(
    statement: FcstmAstOperationStatement,
    document: TextDocumentLike,
    variablesByName: Map<string, FcstmSemanticVariable>,
    occurrences: FcstmSymbolOccurrence[]
): void {
    if (statement.kind === 'assignmentStatement') {
        const variable = variablesByName.get(statement.targetName);
        if (variable) {
            occurrences.push({
                key: variableOccurrenceKey(variable),
                kind: 'variable',
                name: variable.name,
                qualifiedName: variable.identity.qualifiedName,
                filePath: getDocumentFilePath(document),
                range: findIdentifierRange(document, statement.targetName, statement.range),
                role: 'write',
                containerName: undefined,
                renameable: true,
            });
        }
        collectExpressionOccurrences(statement.expression, document, variablesByName, occurrences);
    } else if (statement.kind === 'ifStatement') {
        collectIfStatementOccurrences(statement, document, variablesByName, occurrences);
    }
}

function collectActionOperationOccurrences(
    action: FcstmAstAction,
    document: TextDocumentLike,
    variablesByName: Map<string, FcstmSemanticVariable>,
    occurrences: FcstmSymbolOccurrence[]
): void {
    for (const statement of action.operationsList || []) {
        collectOperationOccurrences(statement, document, variablesByName, occurrences);
    }
}

function collectNodeOccurrences(node: FcstmWorkspaceGraphNode): FcstmSymbolOccurrence[] {
    const semantic = node.semantic;
    if (!semantic) {
        return [];
    }

    const occurrences: FcstmSymbolOccurrence[] = [];
    const variablesByName = new Map(semantic.variables.map(item => [item.name, item]));
    const statesById = new Map(semantic.states.map(item => [item.identity.id, item]));
    const aliasCountMap = buildImportAliasCountMap(semantic);

    for (const variable of semantic.variables) {
        occurrences.push({
            key: variableOccurrenceKey(variable),
            kind: 'variable',
            name: variable.name,
            qualifiedName: variable.identity.qualifiedName,
            filePath: node.filePath,
            range: findIdentifierRange(node.document, variable.name, variable.range),
            role: 'definition',
            renameable: true,
        });
        collectExpressionOccurrences(variable.initializer, node.document, variablesByName, occurrences);
    }

    for (const state of semantic.states) {
        occurrences.push({
            key: stateOccurrenceKey(state),
            kind: 'state',
            name: state.name,
            qualifiedName: state.identity.qualifiedName,
            filePath: node.filePath,
            range: findIdentifierRange(node.document, state.name, state.range),
            role: 'definition',
            containerName: getContainerName(state.identity.path),
            renameable: true,
        });
    }

    for (const event of semantic.events) {
        if (!event.declared) {
            continue;
        }
        occurrences.push({
            key: eventOccurrenceKey(event),
            kind: 'event',
            name: event.name,
            qualifiedName: event.identity.qualifiedName,
            filePath: node.filePath,
            range: findIdentifierRange(
                node.document,
                event.name,
                event.declarationAst?.range || event.range,
                {preferLast: true}
            ),
            role: 'definition',
            containerName: getContainerName(event.identity.path),
            renameable: true,
        });
    }

    for (const action of semantic.actions) {
        if (action.name) {
            occurrences.push({
                key: actionOccurrenceKey(action),
                kind: 'action',
                name: action.name,
                qualifiedName: action.identity.qualifiedName,
                filePath: node.filePath,
                range: findIdentifierRange(node.document, action.name, action.range, {preferLast: true}),
                role: 'definition',
                containerName: getContainerName(action.identity.path),
                renameable: true,
            });
        }

        if (action.ref?.resolved) {
            const target = findActionById(semantic, action.ref.targetActionId);
            if (target) {
                const refName = target.name || action.ref.rawPath.split('.').at(-1) || action.ref.rawPath;
                occurrences.push({
                    key: actionOccurrenceKey(target),
                    kind: 'action',
                    name: refName,
                    qualifiedName: target.identity.qualifiedName,
                    filePath: node.filePath,
                    range: findIdentifierRange(node.document, refName, action.ref.range, {preferLast: true}),
                    role: 'reference',
                    containerName: getContainerName(target.identity.path),
                    renameable: true,
                });
            }
        }

        collectActionOperationOccurrences(action.ast, node.document, variablesByName, occurrences);
    }

    for (const importItem of semantic.imports) {
        occurrences.push({
            key: buildStateAliasKey(importItem, aliasCountMap),
            kind: 'import',
            name: importItem.alias,
            qualifiedName: importItem.mountedStatePath.join('.'),
            filePath: node.filePath,
            range: importItem.aliasRange,
            role: 'definition',
            containerName: importItem.ownerStatePath.join('.'),
            renameable: true,
        });
    }

    for (const transition of semantic.transitions) {
        const sourceState = findStateById(semantic, transition.sourceStateId);
        if (sourceState && transition.sourceStateName) {
            occurrences.push({
                key: stateOccurrenceKey(sourceState),
                kind: 'state',
                name: sourceState.name,
                qualifiedName: sourceState.identity.qualifiedName,
                filePath: node.filePath,
                range: findIdentifierRange(node.document, transition.sourceStateName, transition.range),
                role: 'reference',
                containerName: getContainerName(sourceState.identity.path),
                renameable: true,
            });
        } else if (transition.sourceStateName) {
            const aliasImport = findImportAlias(semantic, transition.ownerStatePath, transition.sourceStateName);
            if (aliasImport) {
                occurrences.push({
                    key: buildStateAliasKey(aliasImport, aliasCountMap),
                    kind: 'import',
                    name: aliasImport.alias,
                    qualifiedName: aliasImport.mountedStatePath.join('.'),
                    filePath: node.filePath,
                    range: findIdentifierRange(node.document, transition.sourceStateName, transition.range),
                    role: 'reference',
                    containerName: aliasImport.ownerStatePath.join('.'),
                    renameable: true,
                });
            }
        }

        const targetState = findStateById(semantic, transition.targetStateId);
        if (targetState && transition.targetStateName) {
            occurrences.push({
                key: stateOccurrenceKey(targetState),
                kind: 'state',
                name: targetState.name,
                qualifiedName: targetState.identity.qualifiedName,
                filePath: node.filePath,
                range: findIdentifierRange(node.document, transition.targetStateName, transition.range, {preferLast: true}),
                role: 'reference',
                containerName: getContainerName(targetState.identity.path),
                renameable: true,
            });
        } else if (transition.targetStateName) {
            const aliasImport = findImportAlias(semantic, transition.ownerStatePath, transition.targetStateName);
            if (aliasImport) {
                occurrences.push({
                    key: buildStateAliasKey(aliasImport, aliasCountMap),
                    kind: 'import',
                    name: aliasImport.alias,
                    qualifiedName: aliasImport.mountedStatePath.join('.'),
                    filePath: node.filePath,
                    range: findIdentifierRange(node.document, transition.targetStateName, transition.range, {preferLast: true}),
                    role: 'reference',
                    containerName: aliasImport.ownerStatePath.join('.'),
                    renameable: true,
                });
            }
        }

        if (transition.guard) {
            collectExpressionOccurrences(transition.guard, node.document, variablesByName, occurrences);
        }

        for (const statement of transition.ast.postOperations || []) {
            collectOperationOccurrences(statement, node.document, variablesByName, occurrences);
        }

        if (transition.trigger?.eventId) {
            const event = findEventById(semantic, transition.trigger.eventId);
            if (event) {
                const eventName = transition.trigger.normalizedPath.at(-1) || event.name;
                occurrences.push({
                    key: eventOccurrenceKey(event),
                    kind: 'event',
                    name: event.name,
                    qualifiedName: event.identity.qualifiedName,
                    filePath: node.filePath,
                    range: findIdentifierRange(node.document, eventName, transition.trigger.range, {preferLast: true}),
                    role: 'reference',
                    containerName: getContainerName(event.identity.path),
                    renameable: true,
                });
            }
        }
    }

    return dedupeOccurrences(occurrences);
}

async function buildSymbolGraph(document: TextDocumentLike): Promise<FcstmWorkspaceSymbolGraph> {
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const occurrences = dedupeOccurrences(
        Object.values(snapshot.nodes).flatMap(node => collectNodeOccurrences(node))
    );
    return {
        rootFile: snapshot.rootFile,
        occurrences,
        rootDocument: snapshot.nodes[snapshot.rootFile]?.document || document,
    };
}

function findOccurrenceAtPosition(
    graph: FcstmWorkspaceSymbolGraph,
    position: TextPositionLike
): FcstmSymbolOccurrence | undefined {
    const filePath = graph.rootFile;
    return graph.occurrences
        .filter(item => item.filePath === filePath && rangeContains(item.range, position))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function findDefinitionOccurrence(
    graph: FcstmWorkspaceSymbolGraph,
    occurrence: FcstmSymbolOccurrence
): FcstmSymbolOccurrence | undefined {
    return graph.occurrences.find(item => item.key === occurrence.key && item.role === 'definition');
}

function isRenameConflict(
    graph: FcstmWorkspaceSymbolGraph,
    target: FcstmSymbolOccurrence,
    nextName: string
): boolean {
    return graph.occurrences.some(item => (
        item.role === 'definition'
        && item.key !== target.key
        && item.kind === target.kind
        && item.filePath === target.filePath
        && item.containerName === target.containerName
        && item.name === nextName
    ));
}

function sortReferences(locations: FcstmReferenceLocation[]): FcstmReferenceLocation[] {
    return [...locations].sort((left, right) => (
        left.uri.localeCompare(right.uri)
        || left.range.start.line - right.range.start.line
        || left.range.start.character - right.range.start.character
    ));
}

/**
 * Resolve the most specific non-import symbol definition at a cursor position.
 */
export async function resolveSymbolDefinitionLocation(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmDefinitionLocation | null> {
    const graph = await buildSymbolGraph(document);
    const occurrence = findOccurrenceAtPosition(graph, position);
    if (!occurrence) {
        return null;
    }

    const definition = findDefinitionOccurrence(graph, occurrence);
    return definition ? makeLocation(definition.filePath, definition.range) : null;
}

/**
 * Collect all references for the symbol under the cursor.
 */
export async function collectReferences(
    document: TextDocumentLike,
    position: TextPositionLike,
    includeDeclaration = true
): Promise<FcstmReferenceLocation[]> {
    const graph = await buildSymbolGraph(document);
    const occurrence = findOccurrenceAtPosition(graph, position);
    if (!occurrence) {
        return [];
    }

    return sortReferences(graph.occurrences
        .filter(item => item.key === occurrence.key && (includeDeclaration || item.role !== 'definition'))
        .map(item => ({
            uri: toFileUri(item.filePath),
            range: item.range,
            role: item.role,
        })));
}

/**
 * Collect document highlights for all in-document references to the selected symbol.
 */
export async function collectDocumentHighlights(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmDocumentHighlight[]> {
    const graph = await buildSymbolGraph(document);
    const occurrence = findOccurrenceAtPosition(graph, position);
    if (!occurrence) {
        return [];
    }

    return graph.occurrences
        .filter(item => item.key === occurrence.key && item.filePath === graph.rootFile)
        .map(item => ({
            range: item.range,
            kind: item.role === 'write' ? 'write' : item.role === 'reference' ? 'read' : 'text',
        }));
}

/**
 * Collect workspace symbols from the currently tracked FCSTM documents.
 */
export async function collectWorkspaceSymbols(
    documents: TextDocumentLike[],
    query: string
): Promise<FcstmWorkspaceSymbol[]> {
    const normalizedQuery = query.trim().toLowerCase();
    const seen = new Set<string>();
    const results: FcstmWorkspaceSymbol[] = [];

    for (const document of documents) {
        const graph = await buildSymbolGraph(document);
        for (const occurrence of definitionOnly(graph.occurrences)) {
            const haystack = `${occurrence.name} ${occurrence.qualifiedName} ${occurrence.containerName || ''}`.toLowerCase();
            if (normalizedQuery && !haystack.includes(normalizedQuery)) {
                continue;
            }

            const key = `${occurrence.kind}:${occurrence.filePath}:${occurrence.range.start.line}:${occurrence.range.start.character}`;
            if (seen.has(key)) {
                continue;
            }
            seen.add(key);
            results.push({
                name: occurrence.name,
                kind: occurrence.kind,
                containerName: occurrence.containerName,
                location: makeLocation(occurrence.filePath, occurrence.range),
            });
        }
    }

    return results.sort((left, right) => (
        left.name.localeCompare(right.name)
        || left.location.uri.localeCompare(right.location.uri)
    ));
}

/**
 * Prepare a rename at the current cursor location if the selected symbol is safe to rename.
 */
export async function prepareRename(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmRenameRange | null> {
    const graph = await buildSymbolGraph(document);
    const occurrence = findOccurrenceAtPosition(graph, position);
    if (!occurrence || !occurrence.renameable) {
        return null;
    }

    return {
        range: occurrence.range,
        placeholder: occurrence.name,
    };
}

/**
 * Build a workspace edit that renames all known references of the selected symbol.
 */
export async function planRename(
    document: TextDocumentLike,
    position: TextPositionLike,
    newName: string
): Promise<FcstmWorkspaceEdit | null> {
    if (!IDENTIFIER_NAME_RE.test(newName)) {
        return null;
    }

    const graph = await buildSymbolGraph(document);
    const occurrence = findOccurrenceAtPosition(graph, position);
    if (!occurrence || !occurrence.renameable) {
        return null;
    }

    const definition = findDefinitionOccurrence(graph, occurrence) || occurrence;
    if (isRenameConflict(graph, definition, newName)) {
        return null;
    }

    const changes: Record<string, FcstmTextEdit[]> = {};
    for (const item of graph.occurrences.filter(candidate => candidate.key === occurrence.key)) {
        const uri = toFileUri(item.filePath);
        changes[uri] = changes[uri] || [];
        changes[uri].push({
            range: item.range,
            newText: newName,
        });
    }

    return {changes};
}

/**
 * Exposed for analyzer and code-action tests that need the occurrence graph directly.
 */
export async function collectSymbolOccurrences(
    document: TextDocumentLike
): Promise<Array<{
    key: string;
    kind: FcstmReferenceSymbolKind;
    name: string;
    qualifiedName: string;
    filePath: string;
    range: TextRange;
    role: FcstmSymbolOccurrenceRole;
    containerName?: string;
    renameable: boolean;
}>> {
    const graph = await buildSymbolGraph(document);
    return graph.occurrences;
}

/**
 * Test-oriented helper: return a definition range for a file-local occurrence set.
 */
export function findDefinitionForOccurrences(
    occurrences: Array<{
        key: string;
        range: TextRange;
        role: FcstmSymbolOccurrenceRole;
    }>,
    key: string
): TextRange | undefined {
    return occurrences.find(item => item.key === key && item.role === 'definition')?.range;
}
