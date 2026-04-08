import {getParser} from '../dsl/parser';
import type {
    FcstmSemanticDocument,
    FcstmSemanticState,
} from '../semantics';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {getWorkspaceGraph} from '../workspace';
import {collectSymbolsFromTree} from './symbols';
import {ParseTreeNode, rangeContains, TextDocumentLike, TextPositionLike} from '../utils/text';
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

function pushChildStateNames(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[],
    options: {
        includeSelf?: boolean;
        pathPrefix?: string;
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
            insertText: `${pathPrefix}${scopeState.name}`,
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
            insertText: `${pathPrefix}${candidate.name}`,
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
        partial = '',
        detailPrefix,
        sortPrefix = '5_event',
    } = options;
    const seen = new Set<string>();

    for (const event of semantic.events.filter(item => (
        item.declared
        && item.statePath.join('.') === scopeState.identity.path.join('.')
    ))) {
        if (seen.has(event.name) || !matchesPartial(event.name, partial)) {
            continue;
        }

        seen.add(event.name);
        items.push({
            label: `${pathPrefix}${event.name}`,
            kind: 'event',
            detail: detailPrefix || event.identity.qualifiedName,
            insertText: `${pathPrefix}${event.name}`,
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
    position: TextPositionLike
): Promise<FcstmContextCompletionResult> {
    const items: FcstmCompletionItem[] = [];
    const lineText = document.lineAt(position.line).text;
    const beforeCursor = lineText.substring(0, position.character);
    let matched = false;

    if (/\bimport\b/.test(beforeCursor) && !/\bas\b/.test(beforeCursor)) {
        matched = true;
        items.push({
            label: 'as',
            kind: 'keyword',
            sortText: '0_as',
        });
    }

    if (/\bimport\b/.test(beforeCursor) && /\bas\b/.test(beforeCursor) && !/\bnamed\b/.test(beforeCursor)) {
        matched = true;
        items.push({
            label: 'named',
            kind: 'keyword',
            sortText: '0_named',
        });
    }

    if (/\bimport\b/.test(beforeCursor) && /\{\s*$/.test(beforeCursor)) {
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
    beforeCursor: string
): FcstmContextCompletionResult {
    const match = beforeCursor.match(/(^|[^:]):\s*\/([A-Za-z0-9_.]*)$/);
    if (!match) {
        return {matched: false, items: []};
    }

    const rawPath = match[2] || '';
    const pathParts = rawPath ? rawPath.split('.') : [];
    const endsWithDot = rawPath.endsWith('.');
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
        partial,
        sortPrefix: '4_abs_state',
        detailPrefix: 'Absolute state path',
    });
    pushDeclaredEventsForState(semantic, containerState, items, {
        pathPrefix,
        partial,
        sortPrefix: '5_abs_event',
        detailPrefix: 'Absolute event path',
    });

    return {matched: true, items};
}

function collectContextAwareCompletions(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike,
    beforeCursor: string
): FcstmContextCompletionResult {
    const items: FcstmCompletionItem[] = [];
    const lookupStates = collectLookupStates(semantic, position);
    const currentScope = getCurrentScopeState(semantic, position);

    const absolutePathResult = collectAbsolutePathCompletions(semantic, beforeCursor);
    if (absolutePathResult.matched) {
        return absolutePathResult;
    }

    if (/(^|\s)ref\s+[./A-Za-z0-9_]*$/.test(beforeCursor)) {
        pushVisibleNamedActions(semantic, lookupStates, items);
        return {matched: true, items};
    }

    if (/::\s*[A-Za-z0-9_.]*$/.test(beforeCursor)) {
        const sourceMatch = beforeCursor.match(/([A-Za-z_][A-Za-z0-9_]*)\s*->[^:]*::\s*[A-Za-z0-9_.]*$/);
        const sourceState = resolveVisibleStateReference(semantic, lookupStates, sourceMatch?.[1]);
        pushDeclaredEventsForState(semantic, sourceState, items, {
            sortPrefix: '5_local_event',
        });
        return {matched: true, items};
    }

    if (/(^|[^:]):\s*[A-Za-z0-9_.]*$/.test(beforeCursor) && !/:\s*\/[A-Za-z0-9_.]*$/.test(beforeCursor)) {
        for (const scopeState of lookupStates) {
            pushDeclaredEventsForState(semantic, scopeState, items, {
                sortPrefix: '5_chain_event',
            });
        }
        return {matched: true, items};
    }

    if (/->\s*[A-Za-z0-9_]*$/.test(beforeCursor)) {
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
    const importAware = await getImportAwareCompletions(document, position);
    const contextAware = semantic
        ? collectContextAwareCompletions(semantic, position, beforeCursor)
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
