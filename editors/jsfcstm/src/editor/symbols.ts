import {getParser} from '../dsl/parser';
import {
    createRange,
    ParseTreeNode,
    TextDocumentLike,
    TextRange,
} from '../utils/text';

export type FcstmSymbolKind = 'variable' | 'class' | 'event';

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
            selectionRange: range,
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
            selectionRange: range,
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
            selectionRange: range,
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

export async function collectDocumentSymbols(
    document: TextDocumentLike
): Promise<FcstmDocumentSymbol[]> {
    const tree = await getParser().parseTree(document.getText());
    if (!tree) {
        return [];
    }

    return extractDocumentSymbolsFromTree(tree as ParseTreeNode, document);
}
