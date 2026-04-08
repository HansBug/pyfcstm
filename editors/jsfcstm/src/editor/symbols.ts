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
} from '../semantics';
import {getWorkspaceGraph} from '../workspace';
import {findIdentifierRange} from './ranges';

export type FcstmSymbolKind = 'variable' | 'class' | 'event' | 'function' | 'module';

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

function actionSymbolName(action: FcstmSemanticAction): string {
    if (action.name) {
        return action.name;
    }
    if (action.mode === 'abstract') {
        return `${action.stage} abstract`;
    }
    if (action.mode === 'ref') {
        return `${action.stage} ref`;
    }
    return action.aspect ? `${action.stage} ${action.aspect}` : action.stage;
}

function buildSemanticActionSymbol(
    action: FcstmSemanticAction,
    document: TextDocumentLike
): FcstmDocumentSymbol {
    const detail: string[] = [action.stage];
    if (action.aspect) {
        detail.push(action.aspect);
    }
    if (action.mode === 'abstract') {
        detail.push('abstract');
    } else if (action.mode === 'ref' && action.ref?.rawPath) {
        detail.push(`ref ${action.ref.rawPath}`);
    } else if (action.mode === 'operations') {
        detail.push('operations');
    }

    return {
        name: actionSymbolName(action),
        detail: detail.join(' '),
        kind: 'function',
        range: action.range,
        selectionRange: findIdentifierRange(
            document,
            action.name || action.ref?.rawPath.split('.').pop() || action.stage,
            action.range,
            {preferLast: true}
        ),
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
    const actions = (semantic.actions || [])
        .filter(item => item.ownerStateId === state.identity.id)
        .map(item => buildSemanticActionSymbol(item, document));

    return {
        name: state.name,
        detail: state.pseudo ? 'pseudo state' : state.displayName || '',
        kind: 'class',
        range: state.range,
        selectionRange: findIdentifierRange(document, state.name, state.range),
        children: [...imports, ...actions, ...declaredEvents, ...childStates],
    };
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
