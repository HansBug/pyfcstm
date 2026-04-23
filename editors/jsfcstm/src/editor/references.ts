import {pathToFileURL} from 'node:url';

import type {
    FcstmAstAction,
    FcstmAstChainPath,
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

export type FcstmReferenceSymbolKind = 'variable' | 'state' | 'event' | 'action' | 'import' | 'tempVariable';
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
    targetFilePath?: string;
    targetRange?: TextRange;
}

interface FcstmWorkspaceSymbolGraph {
    rootFile: string;
    occurrences: FcstmSymbolOccurrence[];
    rootDocument: TextDocumentLike;
    snapshot: FcstmWorkspaceGraphSnapshot;
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

function rangeContainsRange(outer: TextRange, inner: TextRange): boolean {
    return rangeContains(outer, inner.start) && rangeContains(outer, inner.end);
}

function isShadowedDefinitionOccurrence(
    candidate: FcstmSymbolOccurrence,
    occurrences: FcstmSymbolOccurrence[]
): boolean {
    if (candidate.role !== 'definition') {
        return false;
    }

    return occurrences.some(other => (
        other !== candidate
        && other.key === candidate.key
        && other.filePath === candidate.filePath
        && other.role === 'definition'
        && rangeLength(other.range) < rangeLength(candidate.range)
        && rangeContainsRange(candidate.range, other.range)
    ));
}

function visibleOccurrences(occurrences: FcstmSymbolOccurrence[]): FcstmSymbolOccurrence[] {
    return occurrences.filter(item => !isShadowedDefinitionOccurrence(item, occurrences));
}

function definitionOnly(occurrences: FcstmSymbolOccurrence[]): FcstmSymbolOccurrence[] {
    return visibleOccurrences(occurrences).filter(item => item.role === 'definition');
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

function findRootState(semantic: FcstmSemanticDocument): FcstmSemanticState | undefined {
    return semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : semantic.states.find(item => !item.parentStateId);
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

function semanticPathKey(path: string[]): string {
    return path.join('.');
}

function findStateByPath(
    semantic: FcstmSemanticDocument,
    statePath: string[]
): FcstmSemanticState | undefined {
    const key = semanticPathKey(statePath);
    return semantic.lookups.statesByPath[key]
        || semantic.states.find(item => item.identity.path.join('.') === key);
}

function findEventByPath(
    semantic: FcstmSemanticDocument,
    eventPath: string[]
): FcstmSemanticEvent | undefined {
    const key = semanticPathKey(eventPath);
    return semantic.lookups.eventsByQualifiedName[key]
        || semantic.events.find(item => item.identity.path.join('.') === key);
}

function eventPathSegmentRange(
    document: TextDocumentLike,
    eventPath: FcstmAstChainPath,
    segmentIndex: number
): TextRange {
    const fallbackName = eventPath.segments[segmentIndex];
    if (!fallbackName) {
        return eventPath.range;
    }

    if (eventPath.range.start.line !== eventPath.range.end.line) {
        return findIdentifierRange(document, fallbackName, eventPath.range, {
            preferLast: segmentIndex === eventPath.segments.length - 1,
        });
    }

    let offset = eventPath.isAbsolute ? 1 : 0;
    for (let index = 0; index < eventPath.segments.length; index += 1) {
        const segment = eventPath.segments[index];
        const startOffset = offset;
        const endOffset = startOffset + segment.length;
        if (index === segmentIndex) {
            return createRange(
                eventPath.range.start.line,
                eventPath.range.start.character + startOffset,
                eventPath.range.end.line,
                eventPath.range.start.character + endOffset
            );
        }
        offset = endOffset + 1;
    }

    return findIdentifierRange(document, fallbackName, eventPath.range, {
        preferLast: segmentIndex === eventPath.segments.length - 1,
    });
}

/**
 * Push state-reference occurrences for every intermediate segment of a
 * chain / absolute identifier path. Used by transition triggers and action
 * refs so clicking on `Parent` in `/Parent.Inner.Evt` navigates to the
 * Parent state definition rather than silently doing nothing.
 */
function collectStateSegmentOccurrences(
    semantic: FcstmSemanticDocument,
    ownerStatePath: string[],
    path: FcstmAstChainPath,
    document: TextDocumentLike,
    filePath: string,
    occurrences: FcstmSymbolOccurrence[],
    options: { includeFinal?: boolean } = {}
): void {
    const {includeFinal = false} = options;
    if (path.segments.length === 0) {
        return;
    }

    const rootState = findRootState(semantic);
    const baseStatePath = path.isAbsolute
        ? rootState?.identity.path
        : ownerStatePath;
    if (!baseStatePath || baseStatePath.length === 0) {
        return;
    }

    const lastIndex = includeFinal ? path.segments.length : path.segments.length - 1;
    let currentStatePath = [...baseStatePath];
    for (let index = 0; index < lastIndex; index += 1) {
        currentStatePath = [...currentStatePath, path.segments[index]];
        const state = findStateByPath(semantic, currentStatePath);
        if (!state) {
            return;
        }

        occurrences.push({
            key: stateOccurrenceKey(state),
            kind: 'state',
            name: state.name,
            qualifiedName: state.identity.qualifiedName,
            filePath,
            range: eventPathSegmentRange(document, path, index),
            role: 'reference',
            containerName: getContainerName(state.identity.path),
            renameable: true,
        });
    }
}

function collectEventPathOccurrences(
    semantic: FcstmSemanticDocument,
    ownerStatePath: string[],
    eventPath: FcstmAstChainPath,
    document: TextDocumentLike,
    filePath: string,
    occurrences: FcstmSymbolOccurrence[],
    renameable: boolean
): void {
    if (eventPath.segments.length === 0) {
        return;
    }

    const rootState = findRootState(semantic);
    const baseStatePath = eventPath.isAbsolute
        ? rootState?.identity.path
        : ownerStatePath;
    if (!baseStatePath || baseStatePath.length === 0) {
        return;
    }

    let currentStatePath = [...baseStatePath];
    for (let index = 0; index < eventPath.segments.length - 1; index += 1) {
        currentStatePath = [...currentStatePath, eventPath.segments[index]];
        const state = findStateByPath(semantic, currentStatePath);
        if (!state) {
            return;
        }

        occurrences.push({
            key: stateOccurrenceKey(state),
            kind: 'state',
            name: state.name,
            qualifiedName: state.identity.qualifiedName,
            filePath,
            range: eventPathSegmentRange(document, eventPath, index),
            role: 'reference',
            containerName: getContainerName(state.identity.path),
            renameable,
        });
    }

    const event = findEventByPath(semantic, [...baseStatePath, ...eventPath.segments]);
    if (!event) {
        return;
    }

    occurrences.push({
        key: eventOccurrenceKey(event),
        kind: 'event',
        name: event.name,
        qualifiedName: event.identity.qualifiedName,
        filePath,
        range: eventPathSegmentRange(document, eventPath, eventPath.segments.length - 1),
        role: 'reference',
        containerName: getContainerName(event.identity.path),
        renameable,
    });
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

/**
 * Collect block-local temporary variable occurrences from a sequence of
 * operation statements.
 *
 * FCSTM allows assigning to an undeclared name inside an
 * `enter / during / exit / effect` block; that creates a temp variable
 * whose scope is the entire block (including nested if / else branches)
 * and whose lifetime ends when the block finishes. So:
 *
 *  - Occurrences of the same name inside the same block are grouped.
 *  - Occurrences in different blocks (even of the same name) are unrelated.
 *  - The earliest-seen assignment in document order is tagged as the
 *    `definition`; later assignments become `write`, and any read on the
 *    RHS or in a guard becomes a `reference`.
 */
function collectTempVariableOccurrences(
    statements: FcstmAstOperationStatement[] | undefined,
    document: TextDocumentLike,
    filePath: string,
    variablesByName: Map<string, FcstmSemanticVariable>,
    blockKey: string,
    occurrences: FcstmSymbolOccurrence[]
): void {
    if (!statements || statements.length === 0) {
        return;
    }

    interface TempOccurrence {
        name: string;
        range: TextRange;
        role: FcstmSymbolOccurrenceRole;
    }
    const collected: TempOccurrence[] = [];

    const walkExpression = (expr: FcstmAstExpression | null | undefined): void => {
        if (!expr) {
            return;
        }
        switch (expr.expressionKind) {
            case 'identifier': {
                if (!variablesByName.has(expr.name)) {
                    collected.push({name: expr.name, range: expr.range, role: 'reference'});
                }
                break;
            }
            case 'unary':
                walkExpression(expr.operand);
                break;
            case 'binary':
                walkExpression(expr.left);
                walkExpression(expr.right);
                break;
            case 'function':
                walkExpression(expr.argument);
                break;
            case 'conditional':
                walkExpression(expr.condition);
                walkExpression(expr.whenTrue);
                walkExpression(expr.whenFalse);
                break;
            case 'parenthesized':
                walkExpression(expr.expression);
                break;
            default:
                break;
        }
    };

    const walkStatement = (statement: FcstmAstOperationStatement): void => {
        if (statement.kind === 'assignmentStatement') {
            if (!variablesByName.has(statement.targetName)) {
                collected.push({
                    name: statement.targetName,
                    range: findIdentifierRange(document, statement.targetName, statement.range),
                    role: 'write',
                });
            }
            walkExpression(statement.expression);
        } else if (statement.kind === 'ifStatement') {
            for (const branch of statement.branches) {
                walkExpression(branch.condition);
                for (const nested of branch.statements) {
                    walkStatement(nested);
                }
            }
        }
    };

    for (const statement of statements) {
        walkStatement(statement);
    }

    if (collected.length === 0) {
        return;
    }

    // Promote the earliest write of each name (by document position) to
    // `definition` so go-to-definition / find-references have a definitive
    // anchor inside the block.
    const earliestWriteKey = new Map<string, TempOccurrence>();
    for (const item of collected) {
        if (item.role !== 'write') {
            continue;
        }
        const prev = earliestWriteKey.get(item.name);
        const itemStart = item.range.start;
        const prevStart = prev?.range.start;
        const earlier = !prev || (
            itemStart.line < prevStart!.line
            || (itemStart.line === prevStart!.line && itemStart.character < prevStart!.character)
        );
        if (earlier) {
            earliestWriteKey.set(item.name, item);
        }
    }

    for (const item of collected) {
        const isDefinition = earliestWriteKey.get(item.name) === item;
        occurrences.push({
            key: `temp:${filePath}:${blockKey}:${item.name}`,
            kind: 'tempVariable',
            name: item.name,
            qualifiedName: `${blockKey}.${item.name}`,
            filePath,
            range: item.range,
            role: isDefinition ? 'definition' : item.role,
            containerName: blockKey,
            renameable: true,
        });
    }
}

function importTargetRange(
    snapshot: FcstmWorkspaceGraphSnapshot,
    importItem: FcstmSemanticImport
): {filePath?: string; range?: TextRange} {
    const targetFile = importItem.entryFile;
    if (!targetFile) {
        return {};
    }

    const targetSemantic = snapshot.nodes[targetFile]?.semantic;
    const rootState = targetSemantic?.states.find(item => !item.parentStateId);
    return {
        filePath: targetFile,
        range: rootState?.range || createRange(0, 0, 0, 0),
    };
}

function collectNodeOccurrences(
    node: FcstmWorkspaceGraphNode,
    snapshot: FcstmWorkspaceGraphSnapshot
): FcstmSymbolOccurrence[] {
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
            range: state.ast.nameRange || findIdentifierRange(node.document, state.name, state.range),
            role: 'definition',
            containerName: getContainerName(state.identity.path),
            renameable: true,
        });
    }

    for (const event of semantic.events) {
        if (!event.declared) {
            continue;
        }
        if (!event.name) {
            // Parser failure (e.g. event name collides with a reserved token
            // like `E` or `pi`) can leave us with an empty-named semantic
            // event. Skip it instead of emitting a bogus zero-width
            // occurrence at the top of the document.
            continue;
        }
        const identifierRange = findIdentifierRange(
            node.document,
            event.name,
            event.declarationAst?.nameRange || event.declarationAst?.range || event.range,
            {preferLast: true}
        );
        occurrences.push({
            key: eventOccurrenceKey(event),
            kind: 'event',
            name: event.name,
            qualifiedName: event.identity.qualifiedName,
            filePath: node.filePath,
            range: identifierRange,
            role: 'definition',
            containerName: getContainerName(event.identity.path),
            renameable: true,
        });
        const declarationRange = event.declarationAst?.range || event.range;
        if (declarationRange.start.line !== identifierRange.start.line
            || declarationRange.start.character !== identifierRange.start.character
            || declarationRange.end.line !== identifierRange.end.line
            || declarationRange.end.character !== identifierRange.end.character) {
            occurrences.push({
                key: eventOccurrenceKey(event),
                kind: 'event',
                name: event.name,
                qualifiedName: event.identity.qualifiedName,
                filePath: node.filePath,
                range: declarationRange,
                role: 'definition',
                containerName: getContainerName(event.identity.path),
                renameable: false,
            });
        }
    }

    for (const action of semantic.actions) {
        if (action.name) {
            occurrences.push({
                key: actionOccurrenceKey(action),
                kind: 'action',
                name: action.name,
                qualifiedName: action.identity.qualifiedName,
                filePath: node.filePath,
                range: action.ast.nameRange || findIdentifierRange(node.document, action.name, action.range, {preferLast: true}),
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

            // State segments that walk up to the target action (e.g.
            // `/Parent.Inner.SetUp`) should be clickable too.
            const refPath = action.ast.refPath;
            if (refPath && refPath.segments.length > 1) {
                collectStateSegmentOccurrences(
                    semantic,
                    action.ownerStatePath,
                    refPath,
                    node.document,
                    node.filePath,
                    occurrences
                );
            }
        }

        collectActionOperationOccurrences(action.ast, node.document, variablesByName, occurrences);

        // Block-local temporary variables live inside a lifecycle action's
        // operation block. Each action is its own scope: same-named temps
        // in sibling actions must stay independent.
        collectTempVariableOccurrences(
            action.ast.operationsList,
            node.document,
            node.filePath,
            variablesByName,
            `action:${action.identity.id}`,
            occurrences
        );
    }

    for (const importItem of semantic.imports) {
        const target = importTargetRange(snapshot, importItem);
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
            targetFilePath: target.filePath,
            targetRange: target.range,
        });
        occurrences.push({
            key: buildStateAliasKey(importItem, aliasCountMap),
            kind: 'import',
            name: importItem.alias,
            qualifiedName: importItem.mountedStatePath.join('.'),
            filePath: node.filePath,
            range: importItem.pathRange,
            role: 'definition',
            containerName: importItem.ownerStatePath.join('.'),
            renameable: false,
            targetFilePath: target.filePath,
            targetRange: target.range,
        });

        const importedSemantic = importItem.entryFile
            ? snapshot.nodes[importItem.entryFile]?.semantic
            : undefined;
        const importedRootState = importedSemantic
            ? findRootState(importedSemantic)
            : undefined;

        for (const eventMapping of importItem.eventMappings) {
            collectEventPathOccurrences(
                semantic,
                importItem.ownerStatePath,
                eventMapping.targetEvent,
                node.document,
                node.filePath,
                occurrences,
                true
            );

            if (importedSemantic && importedRootState) {
                collectEventPathOccurrences(
                    importedSemantic,
                    importedRootState.identity.path,
                    eventMapping.sourceEvent,
                    node.document,
                    node.filePath,
                    occurrences,
                    false
                );
            }
        }
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
                const target = importTargetRange(snapshot, aliasImport);
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
                    targetFilePath: target.filePath,
                    targetRange: target.range,
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
                const target = importTargetRange(snapshot, aliasImport);
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
                    targetFilePath: target.filePath,
                    targetRange: target.range,
                });
            }
        }

        if (transition.guard) {
            collectExpressionOccurrences(transition.guard, node.document, variablesByName, occurrences);
        }

        for (const statement of transition.ast.postOperations || []) {
            collectOperationOccurrences(statement, node.document, variablesByName, occurrences);
        }

        // `effect { ... }` blocks on a transition get their own block-local
        // temp-variable scope, keyed on the transition identity.
        collectTempVariableOccurrences(
            transition.ast.postOperations,
            node.document,
            node.filePath,
            variablesByName,
            `effect:${transition.identity.id}`,
            occurrences
        );

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

            // For chain- or absolute-scoped triggers the raw path may carry
            // intermediate state segments (e.g. `/Parent.Inner.Evt`). Collect
            // each state segment as a state reference so click-to-navigate
            // works for the path components, not just the final event name.
            const chainTrigger = transition.ast.trigger?.kind === 'chainTrigger'
                ? transition.ast.trigger
                : undefined;
            if (chainTrigger && chainTrigger.eventPath.segments.length > 1) {
                collectStateSegmentOccurrences(
                    semantic,
                    transition.ownerStatePath,
                    chainTrigger.eventPath,
                    node.document,
                    node.filePath,
                    occurrences
                );
            }
        }
    }

    return dedupeOccurrences(occurrences);
}

async function buildSymbolGraph(document: TextDocumentLike): Promise<FcstmWorkspaceSymbolGraph> {
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const occurrences = dedupeOccurrences(
        Object.values(snapshot.nodes).flatMap(node => collectNodeOccurrences(node, snapshot))
    );
    return {
        rootFile: snapshot.rootFile,
        occurrences,
        rootDocument: snapshot.nodes[snapshot.rootFile]?.document || document,
        snapshot,
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
    return graph.occurrences
        .filter(item => item.key === occurrence.key && item.role === 'definition')
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
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

    if (occurrence.kind === 'import' && occurrence.targetFilePath) {
        return makeLocation(
            occurrence.targetFilePath,
            occurrence.targetRange || createRange(0, 0, 0, 0)
        );
    }

    const definition = findDefinitionOccurrence(graph, occurrence);
    if (definition?.kind === 'import' && definition.targetFilePath) {
        return makeLocation(
            definition.targetFilePath,
            definition.targetRange || createRange(0, 0, 0, 0)
        );
    }

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

    return sortReferences(visibleOccurrences(graph.occurrences
        .filter(item => item.key === occurrence.key && (includeDeclaration || item.role !== 'definition'))
    )
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

    return visibleOccurrences(graph.occurrences
        .filter(item => item.key === occurrence.key && item.filePath === graph.rootFile)
    )
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
            if (occurrence.kind === 'tempVariable') {
                // Block-local temps are file- and block-private; excluding
                // them keeps the workspace symbol picker clean.
                continue;
            }
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
    for (const item of graph.occurrences.filter(candidate => candidate.key === occurrence.key && candidate.renameable)) {
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
