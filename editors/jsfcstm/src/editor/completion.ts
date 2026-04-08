import {getParser, type LexToken} from '../dsl/parser';
import type {
    FcstmSemanticDocument,
    FcstmSemanticTransition,
    FcstmSemanticState,
} from '../semantics';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {getWorkspaceGraph} from '../workspace';
import {collectSymbolsFromTree} from './symbols';
import {
    ParseTreeNode,
    rangeContains,
    TextDocumentLike,
    TextPositionLike,
    TextRange,
} from '../utils/text';
import {rangeLength} from './ranges';

export type FcstmCompletionKind =
    | 'keyword'
    | 'constant'
    | 'function'
    | 'variable'
    | 'class'
    | 'event';

export interface FcstmCompletionItem {
    label: string;
    kind: FcstmCompletionKind;
    detail?: string;
    documentation?: string;
    insertText?: string;
    insertTextFormat?: 'plain' | 'snippet';
    sortText?: string;
}

interface FcstmContextCompletionResult {
    matched: boolean;
    items: FcstmCompletionItem[];
}

type FcstmSyntaxCompletionContext =
    | { kind: 'none' }
    | { kind: 'transitionTarget'; transition?: FcstmSemanticTransition; partial?: string }
    | { kind: 'localEvent'; transition?: FcstmSemanticTransition; sourceStateName?: string; partial?: string }
    | { kind: 'chainEvent'; transition?: FcstmSemanticTransition; partial?: string }
    | { kind: 'absoluteEventPath'; rawPath: string }
    | { kind: 'actionRef' }
    | { kind: 'pseudoStateMarker'; partial?: string };

type FcstmImportCompletionContext =
    | { kind: 'none' }
    | { kind: 'importAliasKeyword' }
    | { kind: 'importNamedKeyword' }
    | { kind: 'importBlock' };

export const KEYWORDS = [
    'state', 'pseudo', 'named', 'def', 'event', 'import', 'as',
    'enter', 'during', 'exit', 'before', 'after',
    'abstract', 'ref', 'effect', 'if', 'else',
    'int', 'float',
    'and', 'or', 'not'
];

export const MATH_CONSTANTS = [
    {name: 'pi', detail: 'π ≈ 3.14159', documentation: 'The mathematical constant π (pi)'},
    {name: 'E', detail: 'e ≈ 2.71828', documentation: 'The mathematical constant e (Euler\'s number)'},
    {name: 'tau', detail: 'τ ≈ 6.28318', documentation: 'The mathematical constant τ (tau), equal to 2π'},
    {name: 'true', detail: 'boolean', documentation: 'Boolean true value'},
    {name: 'false', detail: 'boolean', documentation: 'Boolean false value'},
    {name: 'True', detail: 'boolean', documentation: 'Boolean true value (Python-style)'},
    {name: 'False', detail: 'boolean', documentation: 'Boolean false value (Python-style)'}
];

export const MATH_FUNCTIONS = [
    {name: 'sin', params: '(x)', doc: 'Sine function'},
    {name: 'cos', params: '(x)', doc: 'Cosine function'},
    {name: 'tan', params: '(x)', doc: 'Tangent function'},
    {name: 'asin', params: '(x)', doc: 'Arcsine function'},
    {name: 'acos', params: '(x)', doc: 'Arccosine function'},
    {name: 'atan', params: '(x)', doc: 'Arctangent function'},
    {name: 'sinh', params: '(x)', doc: 'Hyperbolic sine function'},
    {name: 'cosh', params: '(x)', doc: 'Hyperbolic cosine function'},
    {name: 'tanh', params: '(x)', doc: 'Hyperbolic tangent function'},
    {name: 'asinh', params: '(x)', doc: 'Inverse hyperbolic sine function'},
    {name: 'acosh', params: '(x)', doc: 'Inverse hyperbolic cosine function'},
    {name: 'atanh', params: '(x)', doc: 'Inverse hyperbolic tangent function'},
    {name: 'sqrt', params: '(x)', doc: 'Square root function'},
    {name: 'cbrt', params: '(x)', doc: 'Cube root function'},
    {name: 'exp', params: '(x)', doc: 'Exponential function (e^x)'},
    {name: 'log', params: '(x)', doc: 'Natural logarithm (base e)'},
    {name: 'log10', params: '(x)', doc: 'Base-10 logarithm'},
    {name: 'log2', params: '(x)', doc: 'Base-2 logarithm'},
    {name: 'log1p', params: '(x)', doc: 'Natural logarithm of (1 + x)'},
    {name: 'abs', params: '(x)', doc: 'Absolute value'},
    {name: 'ceil', params: '(x)', doc: 'Ceiling function (round up)'},
    {name: 'floor', params: '(x)', doc: 'Floor function (round down)'},
    {name: 'round', params: '(x)', doc: 'Round to nearest integer'},
    {name: 'trunc', params: '(x)', doc: 'Truncate to integer'},
    {name: 'sign', params: '(x)', doc: 'Sign function (-1, 0, or 1)'}
];

export function isInComment(text: string): boolean {
    if (text.includes('//')) {
        return true;
    }
    if (text.includes('#')) {
        return true;
    }
    const openCount = (text.match(/\/\*/g) || []).length;
    const closeCount = (text.match(/\*\//g) || []).length;
    return openCount > closeCount;
}

export function isInString(text: string): boolean {
    let inDoubleQuote = false;
    let inSingleQuote = false;

    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        const prevChar = i > 0 ? text[i - 1] : '';

        if (char === '"' && prevChar !== '\\') {
            inDoubleQuote = !inDoubleQuote;
        } else if (char === '\'' && prevChar !== '\\') {
            inSingleQuote = !inSingleQuote;
        }
    }

    return inDoubleQuote || inSingleQuote;
}

function getKeywordCompletions(): FcstmCompletionItem[] {
    return KEYWORDS.map(keyword => ({
        label: keyword,
        kind: 'keyword',
        sortText: `0_${keyword}`,
    }));
}

function getConstantCompletions(): FcstmCompletionItem[] {
    return MATH_CONSTANTS.map(constant => ({
        label: constant.name,
        kind: 'constant',
        detail: constant.detail,
        documentation: constant.documentation,
        sortText: `1_${constant.name}`,
    }));
}

function getFunctionCompletions(): FcstmCompletionItem[] {
    return MATH_FUNCTIONS.map(func => ({
        label: func.name,
        kind: 'function',
        detail: func.params,
        documentation: func.doc,
        insertText: `${func.name}($1)$0`,
        insertTextFormat: 'snippet',
        sortText: `2_${func.name}`,
    }));
}

async function getDocumentSymbolCompletions(document: TextDocumentLike): Promise<FcstmCompletionItem[]> {
    const items: FcstmCompletionItem[] = [];
    const tree = await getParser().parseTree(document.getText());
    if (!tree) {
        return items;
    }

    const fallbackSymbols = collectSymbolsFromTree(tree as ParseTreeNode);
    for (const variable of fallbackSymbols.variables) {
        items.push({
            label: variable,
            kind: 'variable',
            sortText: `3_${variable}`,
        });
    }
    for (const state of fallbackSymbols.states) {
        items.push({
            label: state,
            kind: 'class',
            sortText: `4_${state}`,
        });
    }
    for (const event of fallbackSymbols.events) {
        if (!isValidIdentifierSegment(event)) {
            continue;
        }
        items.push({
            label: event,
            kind: 'event',
            sortText: `5_${event}`,
        });
    }

    return items;
}

function findInnermostState(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticState | undefined {
    return semantic.states
        .filter(state => rangeContains(state.range, position))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function collectLookupStates(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticState[] {
    const statesById = new Map(semantic.states.map(item => [item.identity.id, item]));
    const currentState = findInnermostState(semantic, position);
    const states: FcstmSemanticState[] = [];

    let cursor = currentState;
    while (cursor) {
        states.push(cursor);
        cursor = cursor.parentStateId ? statesById.get(cursor.parentStateId) : undefined;
    }

    if (states.length === 0 && semantic.machine.rootStateId) {
        const rootState = statesById.get(semantic.machine.rootStateId);
        if (rootState) {
            states.push(rootState);
        }
    }

    return states;
}

function getCurrentScopeState(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticState | undefined {
    const currentState = findInnermostState(semantic, position);
    if (currentState) {
        return currentState;
    }

    return semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : undefined;
}

function findRootState(semantic: FcstmSemanticDocument): FcstmSemanticState | undefined {
    return semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : semantic.states.find(item => !item.parentStateId);
}

function matchesPartial(candidate: string, partial: string): boolean {
    return !partial || candidate.toLowerCase().startsWith(partial.toLowerCase());
}

function isValidIdentifierSegment(text: string): boolean {
    return /^[A-Za-z_][A-Za-z0-9_]*$/.test(text);
}

function comparePositions(left: TextPositionLike, right: TextPositionLike): number {
    if (left.line !== right.line) {
        return left.line - right.line;
    }

    return left.character - right.character;
}

function findSemanticTransitionAtPosition(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticTransition | undefined {
    return semantic.transitions
        .filter(item => rangeContains(item.range, position))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function findStateById(
    semantic: FcstmSemanticDocument,
    stateId?: string
): FcstmSemanticState | undefined {
    if (!stateId) {
        return undefined;
    }

    return semantic.states.find(item => item.identity.id === stateId);
}

function isQuotedToken(token: LexToken | undefined): boolean {
    const text = token?.text || '';
    return (text.startsWith('"') && text.endsWith('"')) || (text.startsWith('\'') && text.endsWith('\''));
}

function extractImportCompletionContextFromLineTokens(tokens: LexToken[]): FcstmImportCompletionContext {
    if ((tokens[0]?.text || '') !== 'import') {
        return {kind: 'none'};
    }

    if (tokens.length >= 2 && isQuotedToken(tokens[1]) && !tokens.some(token => token.text === 'as')) {
        return {kind: 'importAliasKeyword'};
    }

    const asIndex = tokens.findIndex(token => token.text === 'as');
    if (asIndex >= 0) {
        const aliasToken = tokens[asIndex + 1];
        const namedIndex = tokens.findIndex(token => token.text === 'named');
        const braceIndex = tokens.findIndex(token => token.text === '{');
        if (aliasToken && namedIndex < 0 && braceIndex < 0) {
            return {kind: 'importNamedKeyword'};
        }
    }

    if (tokens.some(token => token.text === '{')) {
        return {kind: 'importBlock'};
    }

    return {kind: 'none'};
}

function extractSyntaxCompletionContextFromLineTokens(
    tokens: LexToken[],
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSyntaxCompletionContext {
    if (tokens.length === 1 && tokens[0]?.text === '[') {
        return {kind: 'pseudoStateMarker', partial: '['};
    }

    const refIndex = tokens.findIndex(token => token.text === 'ref');
    if (refIndex >= 0) {
        return {kind: 'actionRef'};
    }

    const arrowIndex = tokens.findIndex(token => token.text === '->');
    if (arrowIndex < 0) {
        return {kind: 'none'};
    }

    const transition = findSemanticTransitionAtPosition(semantic, position);
    const afterArrow = tokens.slice(arrowIndex + 1);
    const sourceStateName = tokens[arrowIndex - 1]?.text;
    if (afterArrow.length === 0) {
        return {kind: 'transitionTarget', transition, partial: ''};
    }

    const targetToken = afterArrow[0];
    const operatorToken = afterArrow[1];
    if (!targetToken) {
        return {kind: 'transitionTarget', transition, partial: ''};
    }

    if (!operatorToken) {
        return {kind: 'transitionTarget', transition, partial: targetToken.text};
    }

    if (operatorToken.text === '::') {
        const partial = afterArrow.slice(2).map(token => token.text).join('');
        return {kind: 'localEvent', transition, sourceStateName, partial};
    }

    if (operatorToken.text === ':') {
        const rawPath = afterArrow.slice(2).map(token => token.text).join('');
        if (rawPath.startsWith('/')) {
            return {kind: 'absoluteEventPath', rawPath};
        }

        if (rawPath === 'if') {
            return {kind: 'none'};
        }

        return {kind: 'chainEvent', transition, partial: rawPath};
    }

    return {kind: 'transitionTarget', transition};
}

function findTransitionOperatorToken(
    tokens: LexToken[],
    operatorText: ':' | '::'
): LexToken | undefined {
    const arrowIndex = tokens.findIndex(token => token.text === '->');
    if (arrowIndex < 0) {
        return undefined;
    }

    return tokens.slice(arrowIndex + 1).find(token => token.text === operatorText);
}

function getTriggerInsertTextPrefix(
    beforeCursor: string,
    operatorToken: LexToken | undefined
): string {
    if (!operatorToken) {
        return '';
    }

    const operatorEnd = operatorToken.column + operatorToken.text.length;
    const afterOperatorText = beforeCursor.slice(operatorEnd);
    if (afterOperatorText.startsWith(' ') || afterOperatorText.startsWith('\t')) {
        return '';
    }

    return ' ';
}

function makePseudoStateCompletionItem(): FcstmCompletionItem {
    return {
        label: '[*]',
        kind: 'keyword',
        detail: 'Pseudo-state marker',
        insertText: '[*]',
        sortText: '0_init_marker',
    };
}

function pushPseudoStateMarker(
    items: FcstmCompletionItem[],
    partial = ''
): void {
    if (!matchesPartial('[*]', partial)) {
        return;
    }

    items.push(makePseudoStateCompletionItem());
}

function pushChildStateNames(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[],
    options: {
        includeSelf?: boolean;
        pathPrefix?: string;
        insertTextPrefix?: string;
        partial?: string;
        detailPrefix?: string;
        sortPrefix?: string;
    } = {}
): void {
    if (!scopeState) {
        return;
    }

    const {
        includeSelf = false,
        pathPrefix = '',
        insertTextPrefix = pathPrefix,
        partial = '',
        detailPrefix,
        sortPrefix = '4_state',
    } = options;
    const seen = new Set<string>();

    if (includeSelf && !seen.has(scopeState.name) && matchesPartial(scopeState.name, partial)) {
        seen.add(scopeState.name);
        items.push({
            label: `${pathPrefix}${scopeState.name}`,
            kind: 'class',
            detail: detailPrefix || scopeState.identity.path.join('.'),
            insertText: `${insertTextPrefix}${scopeState.name}`,
            sortText: `${sortPrefix}_${scopeState.name}`,
        });
    }

    for (const candidate of semantic.states.filter(item => item.parentStateId === scopeState.identity.id)) {
        if (seen.has(candidate.name) || !matchesPartial(candidate.name, partial)) {
            continue;
        }

        seen.add(candidate.name);
        items.push({
            label: `${pathPrefix}${candidate.name}`,
            kind: 'class',
            detail: detailPrefix || candidate.identity.path.join('.'),
            insertText: `${insertTextPrefix}${candidate.name}`,
            sortText: `${sortPrefix}_${candidate.name}`,
        });
    }
}

function pushVisibleImportAliases(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[]
): void {
    if (!scopeState) {
        return;
    }

    const seen = new Set<string>();

    for (const importItem of semantic.imports.filter(item => item.ownerStateId === scopeState.identity.id)) {
        if (seen.has(importItem.alias)) {
            continue;
        }

        seen.add(importItem.alias);
        items.push({
            label: importItem.alias,
            kind: 'class',
            detail: 'Imported state alias',
            sortText: `4_import_${importItem.alias}`,
        });
    }
}

function pushDeclaredEventsForState(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[],
    options: {
        pathPrefix?: string;
        insertTextPrefix?: string;
        partial?: string;
        detailPrefix?: string;
        sortPrefix?: string;
        declaredOnly?: boolean;
    } = {}
): void {
    if (!scopeState) {
        return;
    }

    const {
        pathPrefix = '',
        insertTextPrefix = pathPrefix,
        partial = '',
        detailPrefix,
        sortPrefix = '5_event',
        declaredOnly = true,
    } = options;
    const seen = new Set<string>();

    for (const event of semantic.events.filter(item => (
        (!declaredOnly || item.declared)
        && item.statePath.join('.') === scopeState.identity.path.join('.')
    ))) {
        if (
            seen.has(event.name)
            || !isValidIdentifierSegment(event.name)
            || !matchesPartial(event.name, partial)
        ) {
            continue;
        }

        seen.add(event.name);
        items.push({
            label: `${pathPrefix}${event.name}`,
            kind: 'event',
            detail: detailPrefix || event.identity.qualifiedName,
            insertText: `${insertTextPrefix}${event.name}`,
            sortText: `${sortPrefix}_${event.name}`,
        });
    }
}

function pushVisibleNamedActions(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[],
    items: FcstmCompletionItem[]
): void {
    const seen = new Set<string>();
    for (const scopeState of lookupStates) {
        for (const action of semantic.actions.filter(item => item.ownerStateId === scopeState.identity.id && item.name)) {
            if (!action.name || seen.has(action.identity.qualifiedName)) {
                continue;
            }

            seen.add(action.identity.qualifiedName);
            items.push({
                label: action.identity.qualifiedName,
                kind: 'function',
                detail: 'Named lifecycle action',
                insertText: action.identity.qualifiedName,
                sortText: `2_ref_${action.identity.qualifiedName}`,
            });
        }
    }
}

function findStateOwningRangeStart(
    semantic: FcstmSemanticDocument,
    range: TextRange | undefined
): FcstmSemanticState | undefined {
    if (!range) {
        return undefined;
    }

    return semantic.states
        .filter(state => rangeContains(state.range, range.start))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function hasPathMatch(candidates: string[][], expectedPath: string[]): boolean {
    const expectedKey = expectedPath.join('.');
    return candidates.some(path => path.join('.') === expectedKey);
}

function collectDerivedEventContainerPaths(
    semantic: FcstmSemanticDocument,
    event: FcstmSemanticDocument['events'][number],
    position?: TextPositionLike
): {
    declarationPath?: string[];
    localPaths: string[][];
    chainPaths: string[][];
    absolutePaths: string[][];
} {
    const localPathMap = new Map<string, string[]>();
    const chainPathMap = new Map<string, string[]>();
    const absolutePathMap = new Map<string, string[]>();
    const declarationPath = findStateOwningRangeStart(semantic, event.declarationAst?.range)?.identity.path;

    for (const transition of semantic.transitions) {
        if (!transition.trigger || transition.trigger.eventId !== event.identity.id) {
            continue;
        }
        if (position && comparePositions(transition.trigger.range.start, position) > 0) {
            continue;
        }

        if (transition.trigger.scope === 'local' && transition.sourceStatePath) {
            localPathMap.set(transition.sourceStatePath.join('.'), transition.sourceStatePath);
        } else if (transition.trigger.scope === 'chain') {
            chainPathMap.set(transition.ownerStatePath.join('.'), transition.ownerStatePath);
        } else if (transition.trigger.scope === 'absolute') {
            const containerPath = transition.trigger.normalizedPath.slice(0, -1);
            absolutePathMap.set(containerPath.join('.'), containerPath);
        }
    }

    return {
        declarationPath,
        localPaths: [...localPathMap.values()],
        chainPaths: [...chainPathMap.values()],
        absolutePaths: [...absolutePathMap.values()],
    };
}

function eventMatchesScopeState(
    semantic: FcstmSemanticDocument,
    event: FcstmSemanticDocument['events'][number],
    scopeState: FcstmSemanticState,
    scope: 'local' | 'chain' | 'absolute',
    position?: TextPositionLike
): boolean {
    const {declarationPath, localPaths, chainPaths, absolutePaths} = collectDerivedEventContainerPaths(
        semantic,
        event,
        position
    );

    if (declarationPath && declarationPath.join('.') === scopeState.identity.path.join('.')) {
        return true;
    }

    if (scope === 'local') {
        return hasPathMatch(localPaths, scopeState.identity.path);
    }
    if (scope === 'chain') {
        const rootState = findRootState(semantic);
        const isRootScope = Boolean(rootState && rootState.identity.path.join('.') === scopeState.identity.path.join('.'));
        return hasPathMatch(chainPaths, scopeState.identity.path)
            || (isRootScope && hasPathMatch(absolutePaths, scopeState.identity.path));
    }
    return hasPathMatch(absolutePaths, scopeState.identity.path);
}

function pushVisibleScopedEvents(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    scope: 'local' | 'chain' | 'absolute',
    items: FcstmCompletionItem[],
    options: {
        position?: TextPositionLike;
        pathPrefix?: string;
        insertTextPrefix?: string;
        partial?: string;
        detailPrefix?: string;
        sortPrefix?: string;
    } = {}
): void {
    if (!scopeState) {
        return;
    }

    const {
        pathPrefix = '',
        insertTextPrefix = pathPrefix,
        position,
        partial = '',
        detailPrefix,
        sortPrefix = '5_event',
    } = options;
    const seen = new Set<string>();

    for (const event of semantic.events) {
        if (
            seen.has(event.name)
            || !isValidIdentifierSegment(event.name)
            || !matchesPartial(event.name, partial)
            || !eventMatchesScopeState(semantic, event, scopeState, scope, position)
        ) {
            continue;
        }

        seen.add(event.name);
        items.push({
            label: `${pathPrefix}${event.name}`,
            kind: 'event',
            detail: detailPrefix || event.identity.qualifiedName,
            insertText: `${insertTextPrefix}${event.name}`,
            sortText: `${sortPrefix}_${event.name}`,
        });
    }
}

function resolveVisibleStateReference(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[],
    stateName?: string
): FcstmSemanticState | undefined {
    if (!stateName) {
        return undefined;
    }

    const rootState = semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : undefined;
    if (rootState?.name === stateName) {
        return rootState;
    }

    for (const scopeState of lookupStates) {
        const candidate = semantic.states.find(item => (
            item.parentStateId === scopeState.identity.id
            && item.name === stateName
        ));
        if (candidate) {
            return candidate;
        }
    }

    const uniqueGlobalMatches = semantic.states.filter(item => item.name === stateName);
    return uniqueGlobalMatches.length === 1 ? uniqueGlobalMatches[0] : undefined;
}

function collectScopedSymbolCompletions(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    const seen = new Set<string>();
    const lookupStates = collectLookupStates(semantic, position);
    const currentScope = getCurrentScopeState(semantic, position);

    for (const variable of semantic.variables) {
        pushUniqueCompletion(items, seen, {
            label: variable.name,
            kind: 'variable',
            sortText: `3_${variable.name}`,
        });
    }

    for (const candidate of collectStateAndImportCompletions(semantic, currentScope)) {
        pushUniqueCompletion(items, seen, candidate);
    }

    for (const candidate of collectEventCompletions(semantic, lookupStates)) {
        pushUniqueCompletion(items, seen, candidate);
    }

    for (const candidate of collectNamedActionCompletions(semantic, lookupStates)) {
        pushUniqueCompletion(items, seen, candidate);
    }

    return items;
}

function collectStateAndImportCompletions(
    semantic: FcstmSemanticDocument,
    currentScope: FcstmSemanticState | undefined
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    pushChildStateNames(semantic, currentScope, items, {
        sortPrefix: '4_scoped_state',
    });
    pushVisibleImportAliases(semantic, currentScope, items);
    return items;
}

function collectEventCompletions(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[]
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    for (const scopeState of lookupStates) {
        pushDeclaredEventsForState(semantic, scopeState, items, {
            sortPrefix: '5_scoped_event',
        });
    }
    return items;
}

function collectNamedActionCompletions(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[]
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    pushVisibleNamedActions(semantic, lookupStates, items);
    return items;
}

async function getActiveImportEntry(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<{ sourcePath: string } | null> {
    const parsed = await getImportWorkspaceIndex().parseDocument(document);
    const entry = parsed.imports.find(item => rangeContains(item.statementRange, position));
    return entry ? {sourcePath: entry.sourcePath} : null;
}

async function getImportAwareCompletions(
    document: TextDocumentLike,
    position: TextPositionLike,
    lineTokens: LexToken[]
): Promise<FcstmContextCompletionResult> {
    const items: FcstmCompletionItem[] = [];
    const syntaxContext = extractImportCompletionContextFromLineTokens(lineTokens);
    let matched = syntaxContext.kind !== 'none';

    if (syntaxContext.kind === 'importAliasKeyword') {
        items.push({
            label: 'as',
            kind: 'keyword',
            sortText: '0_as',
        });
    }

    if (syntaxContext.kind === 'importNamedKeyword') {
        items.push({
            label: 'named',
            kind: 'keyword',
            sortText: '0_named',
        });
    }

    if (syntaxContext.kind === 'importBlock') {
        items.push({
            label: 'def',
            kind: 'keyword',
            sortText: '0_def_import',
        });
        items.push({
            label: 'event',
            kind: 'keyword',
            sortText: '0_event_import',
        });
    }

    const activeImport = await getActiveImportEntry(document, position);
    if (!activeImport) {
        return {matched, items};
    }

    matched = true;
    items.push({
        label: 'def',
        kind: 'keyword',
        sortText: '0_def_import',
    });
    items.push({
        label: 'event',
        kind: 'keyword',
        sortText: '0_event_import',
    });
    const resolved = await getImportWorkspaceIndex().resolveImportsForDocument(document);
    const target = resolved.find(item => item.sourcePath === activeImport.sourcePath);
    if (!target) {
        return {matched, items};
    }

    for (const variableName of target.explicitVariables) {
        items.push({
            label: variableName,
            kind: 'variable',
            detail: 'Imported variable',
            sortText: `3_import_var_${variableName}`,
        });
    }

    for (const eventPath of target.absoluteEvents) {
        items.push({
            label: eventPath,
            kind: 'event',
            detail: 'Imported absolute event',
            sortText: `5_import_event_${eventPath}`,
        });
    }

    return {matched, items};
}

function pushUniqueCompletion(
    items: FcstmCompletionItem[],
    seen: Set<string>,
    item: FcstmCompletionItem
): void {
    const key = `${item.kind}:${item.label}:${item.insertText || ''}`;
    if (seen.has(key)) {
        return;
    }

    seen.add(key);
    items.push(item);
}

function resolveAbsoluteStatePath(
    semantic: FcstmSemanticDocument,
    pathSegments: string[]
): FcstmSemanticState | undefined {
    let current = findRootState(semantic);
    if (!current) {
        return undefined;
    }

    for (const segment of pathSegments) {
        const next = semantic.states.find(item => (
            item.parentStateId === current?.identity.id
            && item.name === segment
        ));
        if (!next) {
            return undefined;
        }
        current = next;
    }

    return current;
}

function collectAbsolutePathCompletions(
    semantic: FcstmSemanticDocument,
    rawPath: string,
    position: TextPositionLike
): FcstmContextCompletionResult {
    const normalizedPath = rawPath.startsWith('/') ? rawPath.slice(1) : rawPath;
    const pathParts = normalizedPath ? normalizedPath.split('.') : [];
    const endsWithDot = normalizedPath.endsWith('.');
    const partial = endsWithDot ? '' : (pathParts.pop() || '');
    const parentSegments = pathParts.filter(Boolean);
    const containerState = resolveAbsoluteStatePath(semantic, parentSegments);
    if (!containerState) {
        return {matched: true, items: []};
    }

    const pathPrefix = parentSegments.length > 0
        ? `/${parentSegments.join('.')}.`
        : '/';
    const items: FcstmCompletionItem[] = [];
    pushChildStateNames(semantic, containerState, items, {
        pathPrefix,
        insertTextPrefix: '',
        partial,
        sortPrefix: '4_abs_state',
        detailPrefix: 'Absolute state path',
    });
    pushVisibleScopedEvents(semantic, containerState, 'absolute', items, {
        position,
        pathPrefix,
        insertTextPrefix: '',
        partial,
        sortPrefix: '5_abs_event',
        detailPrefix: 'Absolute event path',
    });

    return {matched: true, items};
}

async function collectContextAwareCompletions(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike,
    lineTokens: LexToken[],
    beforeCursor: string
): Promise<FcstmContextCompletionResult> {
    const items: FcstmCompletionItem[] = [];
    const lookupStates = collectLookupStates(semantic, position);
    const currentScope = getCurrentScopeState(semantic, position);
    const syntaxContext = extractSyntaxCompletionContextFromLineTokens(lineTokens, semantic, position);

    if (syntaxContext.kind === 'absoluteEventPath') {
        return collectAbsolutePathCompletions(semantic, syntaxContext.rawPath, position);
    }

    if (syntaxContext.kind === 'pseudoStateMarker') {
        pushPseudoStateMarker(items, syntaxContext.partial);
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'actionRef') {
        pushVisibleNamedActions(semantic, lookupStates, items);
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'localEvent') {
        const insertTextPrefix = getTriggerInsertTextPrefix(
            beforeCursor,
            findTransitionOperatorToken(lineTokens, '::')
        );
        const sourceState = syntaxContext.transition?.sourceStateId
            ? findStateById(semantic, syntaxContext.transition.sourceStateId)
            : resolveVisibleStateReference(semantic, lookupStates, syntaxContext.sourceStateName || syntaxContext.transition?.sourceStateName);
        pushVisibleScopedEvents(semantic, sourceState, 'local', items, {
            position,
            insertTextPrefix,
            partial: syntaxContext.partial,
            sortPrefix: '5_local_event',
        });
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'chainEvent') {
        const insertTextPrefix = getTriggerInsertTextPrefix(
            beforeCursor,
            findTransitionOperatorToken(lineTokens, ':')
        );
        const ownerState = syntaxContext.transition
            ? findStateById(semantic, syntaxContext.transition.ownerStateId)
            : currentScope;
        pushVisibleScopedEvents(semantic, ownerState, 'chain', items, {
            position,
            insertTextPrefix,
            partial: syntaxContext.partial,
            sortPrefix: '5_chain_event',
        });
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'transitionTarget') {
        pushPseudoStateMarker(items, syntaxContext.partial);
        pushChildStateNames(semantic, currentScope, items, {
            includeSelf: false,
            sortPrefix: '4_target_state',
        });
        pushVisibleImportAliases(semantic, currentScope, items);
        return {matched: true, items};
    }

    return {matched: false, items: []};
}

export async function collectCompletionItems(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmCompletionItem[]> {
    const items: FcstmCompletionItem[] = [];
    const seen = new Set<string>();
    const lineText = document.lineAt(position.line).text;
    const beforeCursor = lineText.substring(0, position.character);

    if (isInComment(beforeCursor) || isInString(beforeCursor)) {
        return items;
    }

    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    const lineTokens = await getParser().lex(beforeCursor);
    const importAware = await getImportAwareCompletions(document, position, lineTokens);
    const contextAware = semantic
        ? await collectContextAwareCompletions(semantic, position, lineTokens, beforeCursor)
        : {matched: false, items: []} as FcstmContextCompletionResult;

    if (importAware.matched || contextAware.matched) {
        for (const item of contextAware.items) {
            pushUniqueCompletion(items, seen, item);
        }
        for (const item of importAware.items) {
            pushUniqueCompletion(items, seen, item);
        }
        return items;
    }

    for (const item of getKeywordCompletions()) {
        pushUniqueCompletion(items, seen, item);
    }
    for (const item of getConstantCompletions()) {
        pushUniqueCompletion(items, seen, item);
    }
    for (const item of getFunctionCompletions()) {
        pushUniqueCompletion(items, seen, item);
    }
    if (semantic) {
        for (const item of collectScopedSymbolCompletions(semantic, position)) {
            pushUniqueCompletion(items, seen, item);
        }
    } else {
        for (const item of await getDocumentSymbolCompletions(document)) {
            pushUniqueCompletion(items, seen, item);
        }
    }

    return items;
}
