import {
    createRange,
    ParseTreeNode,
    TextDocumentLike,
    TextRange,
} from '../utils/text';
import type {
    FcstmSemanticAction,
    FcstmSemanticDocument,
    FcstmSemanticImport,
    FcstmSemanticState,
    FcstmSemanticTransition,
} from '../semantics';
import {getWorkspaceGraph} from '../workspace';
import {findIdentifierRange} from './ranges';

export type FcstmSymbolKind =
    | 'variable'
    | 'class'
    | 'event'
    | 'function'
    | 'method'
    | 'module';

export interface FcstmDocumentSymbol {
    name: string;
    detail: string;
    kind: FcstmSymbolKind;
    range: TextRange;
    selectionRange: TextRange;
    children: FcstmDocumentSymbol[];
}

export interface FcstmCollectedSymbols {
    variables: string[];
    states: string[];
    events: string[];
}

function comparePositions(
    left: TextRange['start'],
    right: TextRange['start']
): number {
    if (left.line !== right.line) {
        return left.line - right.line;
    }

    return left.character - right.character;
}

function compareDocumentSymbols(
    left: FcstmDocumentSymbol,
    right: FcstmDocumentSymbol
): number {
    const startDiff = comparePositions(left.selectionRange.start, right.selectionRange.start);
    if (startDiff !== 0) {
        return startDiff;
    }

    const endDiff = comparePositions(left.selectionRange.end, right.selectionRange.end);
    if (endDiff !== 0) {
        return endDiff;
    }

    return left.name.localeCompare(right.name);
}

function sortDocumentSymbols(
    symbols: FcstmDocumentSymbol[]
): FcstmDocumentSymbol[] {
    return [...symbols].sort(compareDocumentSymbols);
}

function mergeSymbolRanges(
    symbols: FcstmDocumentSymbol[],
    fallback: TextRange
): TextRange {
    if (symbols.length === 0) {
        return fallback;
    }

    let start = symbols[0].range.start;
    let end = symbols[0].range.end;

    for (const symbol of symbols.slice(1)) {
        if (comparePositions(symbol.range.start, start) < 0) {
            start = symbol.range.start;
        }
        if (comparePositions(symbol.range.end, end) > 0) {
            end = symbol.range.end;
        }
    }

    return createRange(start.line, start.character, end.line, end.character);
}

function pluralize(count: number, singular: string, plural = `${singular}s`): string {
    return `${count} ${count === 1 ? singular : plural}`;
}

function buildGroupSymbol(
    name: string,
    detail: string,
    children: FcstmDocumentSymbol[],
    fallbackRange: TextRange
): FcstmDocumentSymbol {
    const sortedChildren = sortDocumentSymbols(children);
    return {
        name,
        detail,
        kind: 'module',
        range: mergeSymbolRanges(sortedChildren, fallbackRange),
        selectionRange: sortedChildren[0]?.selectionRange || fallbackRange,
        children: sortedChildren,
    };
}

function getNodeRange(node: ParseTreeNode, document: TextDocumentLike): TextRange {
    const safeLineCount = Math.max(1, document.lineCount);
    const startLine = Math.max(0, (node.start?.line || 1) - 1);
    const startColumn = Math.max(0, node.start?.column || 0);
    const stopLine = Math.max(0, (node.stop?.line || 1) - 1);
    const stopColumn = Math.max(0, (node.stop?.column || 0) + 1);

    return createRange(
        Math.min(startLine, safeLineCount - 1),
        startColumn,
        Math.min(stopLine, safeLineCount - 1),
        stopColumn
    );
}

function extractVariableName(node: ParseTreeNode): string | null {
    const children = node.children || [];
    let varType = '';

    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        const text = child.getText?.() || '';

        if (text === 'int' || text === 'float') {
            varType = text;
        } else if (varType && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(text)) {
            return text;
        }
    }

    return null;
}

function extractStateName(node: ParseTreeNode): string | null {
    const children = node.children || [];

    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        const text = child.getText?.() || '';

        if (text === 'state' && i + 1 < children.length) {
            const nextText = children[i + 1].getText?.() || '';
            if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                return nextText;
            }
        }
    }

    return null;
}

function extractEventName(node: ParseTreeNode): string | null {
    const children = node.children || [];

    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        const text = child.getText?.() || '';

        if (text === 'event' && i + 1 < children.length) {
            const nextText = children[i + 1].getText?.() || '';
            if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                return nextText;
            }
        }
    }

    return null;
}

export function collectSymbolsFromTree(tree: ParseTreeNode): FcstmCollectedSymbols {
    const variables = new Set<string>();
    const states = new Set<string>();
    const events = new Set<string>();

    const visit = (node: ParseTreeNode) => {
        if (!node) {
            return;
        }

        const nodeName = node.constructor?.name;
        if (nodeName === 'Def_assignmentContext') {
            const varName = extractVariableName(node);
            if (varName) {
                variables.add(varName);
            }
        } else if (
            nodeName === 'LeafStateDefinitionContext'
            || nodeName === 'CompositeStateDefinitionContext'
        ) {
            const stateName = extractStateName(node);
            if (stateName) {
                states.add(stateName);
            }
        } else if (nodeName === 'Event_definitionContext') {
            const eventName = extractEventName(node);
            if (eventName) {
                events.add(eventName);
            }
        }

        for (const child of node.children || []) {
            visit(child);
        }
    };

    visit(tree);

    return {
        variables: [...variables],
        states: [...states],
        events: [...events],
    };
}

function extractVariableSymbol(
    node: ParseTreeNode,
    document: TextDocumentLike
): FcstmDocumentSymbol | null {
    try {
        const children = node.children || [];
        let varName = '';
        let varType = '';

        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            const text = child.getText?.() || '';

            if (text === 'int' || text === 'float') {
                varType = text;
            } else if (varType && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(text)) {
                varName = text;
                break;
            }
        }

        if (!varName) {
            return null;
        }

        const range = getNodeRange(node, document);
        return {
            name: varName,
            detail: varType,
            kind: 'variable',
            range,
            selectionRange: findIdentifierRange(document, varName, range),
            children: [],
        };
    } catch {
        return null;
    }
}

function extractEventSymbol(
    node: ParseTreeNode,
    document: TextDocumentLike
): FcstmDocumentSymbol | null {
    try {
        const children = node.children || [];
        let eventName = '';
        let displayName = '';

        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            const text = child.getText?.() || '';

            if (text === 'event' && i + 1 < children.length) {
                const nextText = children[i + 1].getText?.() || '';
                if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                    eventName = nextText;
                }
            } else if (text === 'named' && i + 1 < children.length) {
                displayName = (children[i + 1].getText?.() || '').replace(/^["']|["']$/g, '');
            }
        }

        if (!eventName) {
            return null;
        }

        const range = getNodeRange(node, document);
        return {
            name: eventName,
            detail: displayName || '',
            kind: 'event',
            range,
            selectionRange: findIdentifierRange(document, eventName, range),
            children: [],
        };
    } catch {
        return null;
    }
}

function extractNestedSymbols(
    node: ParseTreeNode,
    document: TextDocumentLike
): FcstmDocumentSymbol[] {
    const symbols: FcstmDocumentSymbol[] = [];

    for (const child of node.children || []) {
        for (const innerChild of child.children || []) {
            const nodeName = innerChild.constructor?.name;

            if (
                nodeName === 'LeafStateDefinitionContext'
                || nodeName === 'CompositeStateDefinitionContext'
            ) {
                const symbol = extractStateSymbol(innerChild, document);
                if (symbol) {
                    symbols.push(symbol);
                }
            } else if (nodeName === 'Event_definitionContext') {
                const symbol = extractEventSymbol(innerChild, document);
                if (symbol) {
                    symbols.push(symbol);
                }
            }
        }
    }

    return symbols;
}

function extractStateSymbol(
    node: ParseTreeNode,
    document: TextDocumentLike
): FcstmDocumentSymbol | null {
    try {
        const children = node.children || [];
        let stateName = '';
        let isPseudo = false;
        let displayName = '';

        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            const text = child.getText?.() || '';

            if (text === 'pseudo') {
                isPseudo = true;
            } else if (text === 'state' && i + 1 < children.length) {
                const nextText = children[i + 1].getText?.() || '';
                if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                    stateName = nextText;
                }
            } else if (text === 'named' && i + 1 < children.length) {
                displayName = (children[i + 1].getText?.() || '').replace(/^["']|["']$/g, '');
            }
        }

        if (!stateName) {
            return null;
        }

        const range = getNodeRange(node, document);
        const symbol: FcstmDocumentSymbol = {
            name: stateName,
            detail: isPseudo ? 'pseudo state' : displayName || '',
            kind: 'class',
            range,
            selectionRange: findIdentifierRange(document, stateName, range),
            children: [],
        };

        if (node.constructor?.name === 'CompositeStateDefinitionContext') {
            symbol.children.push(...extractNestedSymbols(node, document));
        }

        return symbol;
    } catch {
        return null;
    }
}

export function extractDocumentSymbolsFromTree(
    tree: ParseTreeNode,
    document: TextDocumentLike
): FcstmDocumentSymbol[] {
    const symbols: FcstmDocumentSymbol[] = [];

    for (const child of tree.children || []) {
        const nodeName = child.constructor?.name;

        if (nodeName === 'Def_assignmentContext') {
            const symbol = extractVariableSymbol(child, document);
            if (symbol) {
                symbols.push(symbol);
            }
        } else if (
            nodeName === 'LeafStateDefinitionContext'
            || nodeName === 'CompositeStateDefinitionContext'
        ) {
            const symbol = extractStateSymbol(child, document);
            if (symbol) {
                symbols.push(symbol);
            }
        }
    }

    return symbols;
}

function buildSemanticEventSymbol(
    name: string,
    detail: string,
    range: TextRange,
    document: TextDocumentLike
): FcstmDocumentSymbol {
    return {
        name,
        detail,
        kind: 'event',
        range,
        selectionRange: findIdentifierRange(document, name, range),
        children: [],
    };
}

function buildSemanticImportSymbol(item: FcstmSemanticImport): FcstmDocumentSymbol {
    return {
        name: item.alias,
        detail: item.sourcePath,
        kind: 'module',
        range: item.range,
        selectionRange: item.aliasRange,
        children: [],
    };
}

/**
 * Human-friendly symbol name for a lifecycle or aspect action.
 *
 *   enter { … }                → enter
 *   exit { … }                 → exit
 *   during { … }               → during
 *   enter Setup { … }          → Setup
 *   enter abstract Init        → Init
 *   enter ref Foo.Bar          → enter ref Foo.Bar
 *   >> during before { … }     → >> during before
 *   >> during after abstract X → X
 */
function actionSymbolName(action: FcstmSemanticAction): string {
    if (action.name) {
        return action.name;
    }
    if (action.mode === 'ref') {
        const refPath = action.ref?.rawPath;
        const aspectPrefix = action.isGlobalAspect ? '>> ' : '';
        const aspectSuffix = action.aspect ? ` ${action.aspect}` : '';
        return `${aspectPrefix}${action.stage}${aspectSuffix} ref${refPath ? ' ' + refPath : ''}`;
    }
    if (action.isGlobalAspect) {
        return action.aspect ? `>> ${action.stage} ${action.aspect}` : `>> ${action.stage}`;
    }
    return action.aspect ? `${action.stage} ${action.aspect}` : action.stage;
}

/**
 * Compact detail for a lifecycle / aspect action.
 *
 * The icon (`Method`) and name already carry most of the structural
 * information (stage + aspect). The detail should surface the *mode* in
 * a single word — `abstract` / `ref` / `operations` — plus an optional
 * summary of the body for operation blocks.
 */
function actionSymbolDetail(action: FcstmSemanticAction): string {
    if (action.mode === 'abstract') {
        return 'abstract';
    }
    if (action.mode === 'ref') {
        return action.ref?.rawPath ? `ref ${action.ref.rawPath}` : 'ref';
    }
    const summary = summarizeOperationBody(action.operationsText);
    return summary ? `{ ${summary} }` : '{ … }';
}

function summarizeOperationBody(text: string | undefined): string {
    if (!text) {
        return '';
    }
    const compact = text.replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/\/\/[^\n]*/g, '')
        .replace(/[\s\t]+/g, ' ')
        .replace(/^\s*\{\s*|\s*\}\s*$/g, '')
        .trim();
    if (!compact) {
        return '';
    }
    const firstStatement = compact.split(';')[0].trim();
    const display = firstStatement.length > 0 ? firstStatement + ';' : compact;
    return truncateForDetail(display, 48);
}

function truncateForDetail(text: string, max: number): string {
    if (text.length <= max) {
        return text;
    }
    return text.slice(0, Math.max(0, max - 1)).trimEnd() + '…';
}

function buildSemanticActionSymbol(
    action: FcstmSemanticAction,
    document: TextDocumentLike
): FcstmDocumentSymbol {
    const selectionAnchor =
        action.name
        || action.ref?.rawPath.split('.').pop()
        || action.stage;
    return {
        name: actionSymbolName(action),
        detail: actionSymbolDetail(action),
        kind: 'method',
        range: action.range,
        selectionRange: findIdentifierRange(document, selectionAnchor, action.range, {preferLast: true}),
        children: [],
    };
}

function transitionSourceName(transition: FcstmSemanticTransition): string {
    if (transition.sourceKind === 'init') {
        return '[*]';
    }
    if (transition.sourceKind === 'all') {
        return '!*';
    }

    return transition.sourceStateName || '?';
}

function transitionTargetName(transition: FcstmSemanticTransition): string {
    if (transition.targetKind === 'exit') {
        return '[*]';
    }

    return transition.targetStateName || '?';
}

function transitionSymbolName(transition: FcstmSemanticTransition): string {
    const base = `${transitionSourceName(transition)} -> ${transitionTargetName(transition)}`;
    if (!transition.trigger) {
        return base;
    }

    const separator = transition.trigger.scope === 'local' ? '::' : ':';
    return `${base} ${separator} ${transition.trigger.rawText}`;
}

/**
 * Compact, user-facing detail string for a transition.
 *
 * The label already carries source / target / trigger, so the detail
 * concentrates on the things the label can't easily convey: the semantic
 * role (entry / exit / forced), the guard expression, and whether an
 * effect block is present. This is kept short because the outline panel
 * clips long detail strings.
 */
function transitionSymbolDetail(
    transition: FcstmSemanticTransition,
    document: TextDocumentLike
): string {
    const parts: string[] = [];
    if (transition.transitionKind === 'entry') {
        parts.push('initial');
    } else if (transition.transitionKind === 'exit' || transition.transitionKind === 'exitAll') {
        parts.push('terminal');
    }
    if (transition.forced) {
        parts.push('forced');
    }
    const guardText = extractRangeText(document, transition.guard?.range);
    if (guardText) {
        parts.push(`if [${truncateForDetail(guardText, 40)}]`);
    } else if (transition.guard) {
        parts.push('guarded');
    }
    if (transition.effectText?.trim()) {
        parts.push('effect');
    }
    return parts.join(' ');
}

function extractRangeText(document: TextDocumentLike, range: TextRange | undefined): string {
    if (!range) {
        return '';
    }
    const [lo, hi] = comparePositions(range.start, range.end) <= 0
        ? [range.start, range.end]
        : [range.end, range.start];
    if (lo.line === hi.line) {
        const lineText = document.lineAt(lo.line).text;
        return lineText.substring(lo.character, hi.character).trim();
    }
    const lines: string[] = [];
    for (let line = lo.line; line <= hi.line; line++) {
        const text = document.lineAt(line).text;
        const start = line === lo.line ? lo.character : 0;
        const end = line === hi.line ? hi.character : text.length;
        lines.push(text.substring(start, end));
    }
    return lines.join(' ').replace(/\s+/g, ' ').trim();
}

function buildSemanticTransitionSymbol(
    transition: FcstmSemanticTransition,
    document: TextDocumentLike
): FcstmDocumentSymbol {
    const selectionHint = transition.sourceStateName || transition.targetStateName;
    return {
        name: transitionSymbolName(transition),
        detail: transitionSymbolDetail(transition, document),
        kind: 'function',
        range: transition.range,
        selectionRange: selectionHint
            ? findIdentifierRange(document, selectionHint, transition.range)
            : transition.range,
        children: [],
    };
}

function buildSemanticStateSymbol(
    state: FcstmSemanticState,
    semantic: FcstmSemanticDocument,
    document: TextDocumentLike
): FcstmDocumentSymbol {
    const childStates = (semantic.states || [])
        .filter(candidate => candidate.parentStateId === state.identity.id)
        .map(candidate => buildSemanticStateSymbol(candidate, semantic, document));
    const declaredEvents = (semantic.events || [])
        .filter(event => event.declared && event.statePath.join('.') === state.identity.path.join('.'))
        .map(event => buildSemanticEventSymbol(event.name, event.displayName || '', event.range, document));
    const imports = (semantic.imports || [])
        .filter(item => item.ownerStateId === state.identity.id)
        .map(item => buildSemanticImportSymbol(item));
    const ownedActions = (semantic.actions || [])
        .filter(item => item.ownerStateId === state.identity.id);
    const actionSymbols = ownedActions
        .map(item => buildSemanticActionSymbol(item, document));
    const transitions = (semantic.transitions || [])
        .filter(item => item.ownerStateId === state.identity.id)
        .map(item => buildSemanticTransitionSymbol(item, document));
    const stateChildren: FcstmDocumentSymbol[] = [];

    // Child layout for a state (in render order):
    //
    //   - Imports group   (only when the state owns any `import ...`)
    //   - Events  group
    //   - Actions (lifecycle + aspect) — flattened directly under the
    //     state in source order. The previous `Actions → Lifecycle /
    //     Aspects` double-wrapper made simple states feel deeply nested,
    //     so we drop it and rely on per-action names + icons instead.
    //   - Transitions group
    //   - States      group (nested child states)
    //
    // Groups are kept for categories that can grow large (events,
    // transitions, nested states); single actions stay flat.

    if (imports.length > 0) {
        stateChildren.push(buildGroupSymbol(
            'Imports',
            pluralize(imports.length, 'import'),
            imports,
            state.range
        ));
    }
    if (declaredEvents.length > 0) {
        stateChildren.push(buildGroupSymbol(
            'Events',
            pluralize(declaredEvents.length, 'event'),
            declaredEvents,
            state.range
        ));
    }
    for (const action of actionSymbols) {
        stateChildren.push(action);
    }
    if (transitions.length > 0) {
        stateChildren.push(buildGroupSymbol(
            'Transitions',
            pluralize(transitions.length, 'transition'),
            transitions,
            state.range
        ));
    }
    if (childStates.length > 0) {
        stateChildren.push(buildGroupSymbol(
            'States',
            pluralize(childStates.length, 'state'),
            childStates,
            state.range
        ));
    }

    stateChildren.sort(compareDocumentSymbols);

    return {
        name: state.name,
        detail: buildStateDetail(state, {
            transitionCount: transitions.length,
            childStateCount: childStates.length,
            eventCount: declaredEvents.length,
            actionCount: actionSymbols.length,
        }),
        kind: 'class',
        range: state.range,
        selectionRange: findIdentifierRange(document, state.name, state.range),
        children: stateChildren,
    };
}

/**
 * Compose a short state-level detail string that carries the most useful
 * signal at a glance: either a named-state display string, a pseudo-state
 * marker, or a rough shape summary for composite states (how many
 * transitions / child states). The VSCode outline renders this alongside
 * the state name.
 */
function buildStateDetail(
    state: FcstmSemanticState,
    counts: {transitionCount: number; childStateCount: number; eventCount: number; actionCount: number}
): string {
    if (state.pseudo) {
        return 'pseudo state';
    }
    if (state.displayName) {
        return state.displayName;
    }
    const fragments: string[] = [];
    if (counts.childStateCount > 0) {
        fragments.push(pluralize(counts.childStateCount, 'state'));
    }
    if (counts.transitionCount > 0) {
        fragments.push(pluralize(counts.transitionCount, 'transition'));
    }
    if (counts.eventCount > 0) {
        fragments.push(pluralize(counts.eventCount, 'event'));
    }
    return fragments.join(' · ');
}

function extractDocumentSymbolsFromSemantic(
    semantic: FcstmSemanticDocument | null,
    document: TextDocumentLike
): FcstmDocumentSymbol[] {
    if (!semantic) {
        return [];
    }

    const variables = (semantic.variables || []).map(variable => ({
        name: variable.name,
        detail: variable.valueType,
        kind: 'variable' as const,
        range: variable.range,
        selectionRange: findIdentifierRange(document, variable.name, variable.range),
        children: [],
    }));
    const rootStates = (semantic.states || [])
        .filter(state => !state.parentStateId)
        .map(state => buildSemanticStateSymbol(state, semantic, document));

    return [...variables, ...rootStates];
}

export async function collectDocumentSymbols(
    document: TextDocumentLike
): Promise<FcstmDocumentSymbol[]> {
    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    return extractDocumentSymbolsFromSemantic(semantic, document);
}
