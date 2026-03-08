/**
 * FCSTM Document Symbols Provider
 *
 * This module provides document symbols (outline) for FCSTM documents by
 * extracting variables, states, and events from the parse tree.
 */

import * as vscode from 'vscode';
import { getParser } from './parser';

/**
 * Parse tree node interface (minimal typing for ANTLR parse tree)
 */
interface ParseTreeNode {
    start?: { line: number; column: number };
    stop?: { line: number; column: number };
    children?: ParseTreeNode[];
    getText?: () => string;
    getChildCount?: () => number;
    getChild?: (index: number) => ParseTreeNode;
    constructor?: { name: string };
}

/**
 * Document symbols provider for FCSTM documents
 */
export class FcstmDocumentSymbolProvider implements vscode.DocumentSymbolProvider {
    private readonly parser = getParser();

    async provideDocumentSymbols(
        document: vscode.TextDocument,
        _token: vscode.CancellationToken
    ): Promise<vscode.DocumentSymbol[]> {
        try {
            const text = document.getText();
            const tree = await this.parser.parseTree(text);

            if (!tree) {
                return [];
            }

            return this.extractSymbols(tree as ParseTreeNode, document);
        } catch (error) {
            console.error('Error extracting symbols:', error);
            return [];
        }
    }

    /**
     * Extract symbols from parse tree
     */
    private extractSymbols(
        tree: ParseTreeNode,
        document: vscode.TextDocument
    ): vscode.DocumentSymbol[] {
        const symbols: vscode.DocumentSymbol[] = [];

        if (!tree.children) {
            return symbols;
        }

        // Walk through top-level children
        for (const child of tree.children) {
            if (!child.constructor?.name) {
                continue;
            }

            const nodeName = child.constructor.name;

            // Extract variable definitions
            if (nodeName === 'Def_assignmentContext') {
                const symbol = this.extractVariableSymbol(child, document);
                if (symbol) {
                    symbols.push(symbol);
                }
            }
            // Extract state definitions
            else if (
                nodeName === 'LeafStateDefinitionContext' ||
                nodeName === 'CompositeStateDefinitionContext'
            ) {
                const symbol = this.extractStateSymbol(child, document);
                if (symbol) {
                    symbols.push(symbol);
                }
            }
        }

        return symbols;
    }

    /**
     * Extract variable definition symbol
     */
    private extractVariableSymbol(
        node: ParseTreeNode,
        document: vscode.TextDocument
    ): vscode.DocumentSymbol | null {
        try {
            // def_assignment: 'def' var_type=('int' | 'float') var_name=ID '=' initial_assignment ';'
            const children = node.children || [];
            let varName = '';
            let varType = '';

            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                const text = child.getText?.() || '';

                // Find type
                if (text === 'int' || text === 'float') {
                    varType = text;
                }
                // Find variable name (ID after type)
                else if (varType && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(text)) {
                    varName = text;
                    break;
                }
            }

            if (!varName) {
                return null;
            }

            const range = this.getNodeRange(node, document);
            const selectionRange = this.getNodeRange(node, document);

            return new vscode.DocumentSymbol(
                varName,
                varType,
                vscode.SymbolKind.Variable,
                range,
                selectionRange
            );
        } catch {
            return null;
        }
    }

    /**
     * Extract state definition symbol
     */
    private extractStateSymbol(
        node: ParseTreeNode,
        document: vscode.TextDocument
    ): vscode.DocumentSymbol | null {
        try {
            const children = node.children || [];
            let stateName = '';
            let isPseudo = false;
            let displayName = '';

            // Check for pseudo keyword and extract state name
            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                const text = child.getText?.() || '';

                if (text === 'pseudo') {
                    isPseudo = true;
                } else if (text === 'state') {
                    // Next identifier is the state name
                    if (i + 1 < children.length) {
                        const nextChild = children[i + 1];
                        const nextText = nextChild.getText?.() || '';
                        if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                            stateName = nextText;
                        }
                    }
                } else if (text === 'named' && i + 1 < children.length) {
                    // Extract display name from string literal
                    const nextChild = children[i + 1];
                    const nextText = nextChild.getText?.() || '';
                    displayName = nextText.replace(/^["']|["']$/g, '');
                }
            }

            if (!stateName) {
                return null;
            }

            const range = this.getNodeRange(node, document);
            const selectionRange = this.getNodeRange(node, document);

            const detail = isPseudo ? 'pseudo state' : displayName || '';
            const kind = vscode.SymbolKind.Class;

            const symbol = new vscode.DocumentSymbol(
                stateName,
                detail,
                kind,
                range,
                selectionRange
            );

            // Extract nested symbols for composite states
            if (node.constructor?.name === 'CompositeStateDefinitionContext') {
                const nestedSymbols = this.extractNestedSymbols(node, document);
                nestedSymbols.forEach(nested => symbol.children.push(nested));
            }

            return symbol;
        } catch {
            return null;
        }
    }

    /**
     * Extract nested symbols from composite state
     */
    private extractNestedSymbols(
        node: ParseTreeNode,
        document: vscode.TextDocument
    ): vscode.DocumentSymbol[] {
        const symbols: vscode.DocumentSymbol[] = [];

        if (!node.children) {
            return symbols;
        }

        // Look for state_inner_statement nodes
        for (const child of node.children) {
            if (!child.children) {
                continue;
            }

            // Recursively search for nested states and events
            for (const innerChild of child.children) {
                const nodeName = innerChild.constructor?.name;

                if (
                    nodeName === 'LeafStateDefinitionContext' ||
                    nodeName === 'CompositeStateDefinitionContext'
                ) {
                    const symbol = this.extractStateSymbol(innerChild, document);
                    if (symbol) {
                        symbols.push(symbol);
                    }
                } else if (nodeName === 'Event_definitionContext') {
                    const symbol = this.extractEventSymbol(innerChild, document);
                    if (symbol) {
                        symbols.push(symbol);
                    }
                }
            }
        }

        return symbols;
    }

    /**
     * Extract event definition symbol
     */
    private extractEventSymbol(
        node: ParseTreeNode,
        document: vscode.TextDocument
    ): vscode.DocumentSymbol | null {
        try {
            // event_definition: 'event' event_name=ID ('named' display_name=STRING_LITERAL)? ';'
            const children = node.children || [];
            let eventName = '';
            let displayName = '';

            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                const text = child.getText?.() || '';

                if (text === 'event') {
                    // Next identifier is the event name
                    if (i + 1 < children.length) {
                        const nextChild = children[i + 1];
                        const nextText = nextChild.getText?.() || '';
                        if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                            eventName = nextText;
                        }
                    }
                } else if (text === 'named' && i + 1 < children.length) {
                    // Extract display name from string literal
                    const nextChild = children[i + 1];
                    const nextText = nextChild.getText?.() || '';
                    displayName = nextText.replace(/^["']|["']$/g, '');
                }
            }

            if (!eventName) {
                return null;
            }

            const range = this.getNodeRange(node, document);
            const selectionRange = this.getNodeRange(node, document);

            return new vscode.DocumentSymbol(
                eventName,
                displayName || '',
                vscode.SymbolKind.Event,
                range,
                selectionRange
            );
        } catch {
            return null;
        }
    }

    /**
     * Get VSCode range from parse tree node
     */
    private getNodeRange(
        node: ParseTreeNode,
        document: vscode.TextDocument
    ): vscode.Range {
        const startLine = Math.max(0, (node.start?.line || 1) - 1);
        const startColumn = Math.max(0, node.start?.column || 0);
        const stopLine = Math.max(0, (node.stop?.line || 1) - 1);
        const stopColumn = Math.max(0, (node.stop?.column || 0) + 1);

        return new vscode.Range(
            new vscode.Position(
                Math.min(startLine, document.lineCount - 1),
                startColumn
            ),
            new vscode.Position(
                Math.min(stopLine, document.lineCount - 1),
                stopColumn
            )
        );
    }
}
