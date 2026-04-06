/**
 * FCSTM Completion Provider
 *
 * This module provides code completion for FCSTM documents including:
 * - Keywords
 * - Built-in constants
 * - Built-in functions
 * - Document-local symbols (variables, states, events)
 */

import * as vscode from 'vscode';
import { getParser } from './parser';
import { getImportWorkspaceIndex } from './imports';

/**
 * FCSTM keywords
 */
const KEYWORDS = [
    'state', 'pseudo', 'named', 'def', 'event', 'import', 'as',
    'enter', 'during', 'exit', 'before', 'after',
    'abstract', 'ref', 'effect', 'if', 'else',
    'int', 'float',
    'and', 'or', 'not'
];

/**
 * Built-in math constants
 */
const MATH_CONSTANTS = [
    { name: 'pi', detail: 'π ≈ 3.14159', documentation: 'The mathematical constant π (pi)' },
    { name: 'E', detail: 'e ≈ 2.71828', documentation: 'The mathematical constant e (Euler\'s number)' },
    { name: 'tau', detail: 'τ ≈ 6.28318', documentation: 'The mathematical constant τ (tau), equal to 2π' },
    { name: 'true', detail: 'boolean', documentation: 'Boolean true value' },
    { name: 'false', detail: 'boolean', documentation: 'Boolean false value' },
    { name: 'True', detail: 'boolean', documentation: 'Boolean true value (Python-style)' },
    { name: 'False', detail: 'boolean', documentation: 'Boolean false value (Python-style)' }
];

/**
 * Built-in math functions
 */
const MATH_FUNCTIONS = [
    { name: 'sin', params: '(x)', doc: 'Sine function' },
    { name: 'cos', params: '(x)', doc: 'Cosine function' },
    { name: 'tan', params: '(x)', doc: 'Tangent function' },
    { name: 'asin', params: '(x)', doc: 'Arcsine function' },
    { name: 'acos', params: '(x)', doc: 'Arccosine function' },
    { name: 'atan', params: '(x)', doc: 'Arctangent function' },
    { name: 'sinh', params: '(x)', doc: 'Hyperbolic sine function' },
    { name: 'cosh', params: '(x)', doc: 'Hyperbolic cosine function' },
    { name: 'tanh', params: '(x)', doc: 'Hyperbolic tangent function' },
    { name: 'asinh', params: '(x)', doc: 'Inverse hyperbolic sine function' },
    { name: 'acosh', params: '(x)', doc: 'Inverse hyperbolic cosine function' },
    { name: 'atanh', params: '(x)', doc: 'Inverse hyperbolic tangent function' },
    { name: 'sqrt', params: '(x)', doc: 'Square root function' },
    { name: 'cbrt', params: '(x)', doc: 'Cube root function' },
    { name: 'exp', params: '(x)', doc: 'Exponential function (e^x)' },
    { name: 'log', params: '(x)', doc: 'Natural logarithm (base e)' },
    { name: 'log10', params: '(x)', doc: 'Base-10 logarithm' },
    { name: 'log2', params: '(x)', doc: 'Base-2 logarithm' },
    { name: 'log1p', params: '(x)', doc: 'Natural logarithm of (1 + x)' },
    { name: 'abs', params: '(x)', doc: 'Absolute value' },
    { name: 'ceil', params: '(x)', doc: 'Ceiling function (round up)' },
    { name: 'floor', params: '(x)', doc: 'Floor function (round down)' },
    { name: 'round', params: '(x)', doc: 'Round to nearest integer' },
    { name: 'trunc', params: '(x)', doc: 'Truncate to integer' },
    { name: 'sign', params: '(x)', doc: 'Sign function (-1, 0, or 1)' }
];

/**
 * Parse tree node interface
 */
interface ParseTreeNode {
    start?: { line: number; column: number };
    stop?: { line: number; column: number };
    children?: ParseTreeNode[];
    getText?: () => string;
    constructor?: { name: string };
}

/**
 * Completion provider for FCSTM documents
 */
export class FcstmCompletionProvider implements vscode.CompletionItemProvider {
    private readonly parser = getParser();
    private readonly importIndex = getImportWorkspaceIndex();

    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken,
        _context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];

        // Check if we're in a comment or string
        const lineText = document.lineAt(position.line).text;
        const beforeCursor = lineText.substring(0, position.character);

        if (this.isInComment(beforeCursor) || this.isInString(beforeCursor)) {
            return items;
        }

        // Add keyword completions
        items.push(...this.getKeywordCompletions());

        // Add built-in constant completions
        items.push(...this.getConstantCompletions());

        // Add built-in function completions
        items.push(...this.getFunctionCompletions());

        // Add document-local symbol completions
        const localSymbols = await this.getDocumentSymbols(document);
        items.push(...localSymbols);

        // Add import-aware completions
        items.push(...await this.getImportAwareCompletions(document, position));

        return items;
    }

    /**
     * Check if position is in a comment
     */
    private isInComment(text: string): boolean {
        // Check for line comments
        if (text.includes('//')) {
            return true;
        }
        if (text.includes('#')) {
            return true;
        }
        // Simple check for block comments (not perfect but good enough)
        const openCount = (text.match(/\/\*/g) || []).length;
        const closeCount = (text.match(/\*\//g) || []).length;
        return openCount > closeCount;
    }

    /**
     * Check if position is in a string
     */
    private isInString(text: string): boolean {
        let inDoubleQuote = false;
        let inSingleQuote = false;

        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            const prevChar = i > 0 ? text[i - 1] : '';

            if (char === '"' && prevChar !== '\\') {
                inDoubleQuote = !inDoubleQuote;
            } else if (char === "'" && prevChar !== '\\') {
                inSingleQuote = !inSingleQuote;
            }
        }

        return inDoubleQuote || inSingleQuote;
    }

    /**
     * Get keyword completions
     */
    private getKeywordCompletions(): vscode.CompletionItem[] {
        return KEYWORDS.map(keyword => {
            const item = new vscode.CompletionItem(keyword, vscode.CompletionItemKind.Keyword);
            item.sortText = `0_${keyword}`;
            return item;
        });
    }

    /**
     * Get constant completions
     */
    private getConstantCompletions(): vscode.CompletionItem[] {
        return MATH_CONSTANTS.map(constant => {
            const item = new vscode.CompletionItem(constant.name, vscode.CompletionItemKind.Constant);
            item.detail = constant.detail;
            item.documentation = new vscode.MarkdownString(constant.documentation);
            item.sortText = `1_${constant.name}`;
            return item;
        });
    }

    /**
     * Get function completions
     */
    private getFunctionCompletions(): vscode.CompletionItem[] {
        return MATH_FUNCTIONS.map(func => {
            const item = new vscode.CompletionItem(func.name, vscode.CompletionItemKind.Function);
            item.detail = func.params;
            item.documentation = new vscode.MarkdownString(func.doc);
            item.insertText = new vscode.SnippetString(`${func.name}($1)$0`);
            item.sortText = `2_${func.name}`;
            return item;
        });
    }

    /**
     * Get document-local symbol completions
     */
    private async getDocumentSymbols(document: vscode.TextDocument): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];

        try {
            const text = document.getText();
            const tree = await this.parser.parseTree(text);

            if (!tree) {
                return items;
            }

            const symbols = this.extractSymbols(tree as ParseTreeNode);

            // Add variable completions
            symbols.variables.forEach(varName => {
                const item = new vscode.CompletionItem(varName, vscode.CompletionItemKind.Variable);
                item.sortText = `3_${varName}`;
                items.push(item);
            });

            // Add state completions
            symbols.states.forEach(stateName => {
                const item = new vscode.CompletionItem(stateName, vscode.CompletionItemKind.Class);
                item.sortText = `4_${stateName}`;
                items.push(item);
            });

            // Add event completions
            symbols.events.forEach(eventName => {
                const item = new vscode.CompletionItem(eventName, vscode.CompletionItemKind.Event);
                item.sortText = `5_${eventName}`;
                items.push(item);
            });
        } catch {
            // Ignore errors, just return what we have
        }

        return items;
    }

    /**
     * Get import-aware completions
     */
    private async getImportAwareCompletions(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];
        const lineText = document.lineAt(position.line).text;
        const beforeCursor = lineText.substring(0, position.character);

        if (/\bimport\b/.test(beforeCursor) && !/\bas\b/.test(beforeCursor)) {
            const asItem = new vscode.CompletionItem('as', vscode.CompletionItemKind.Keyword);
            asItem.sortText = '0_as';
            items.push(asItem);
        }

        if (/\bimport\b/.test(beforeCursor) && /\bas\b/.test(beforeCursor) && !/\bnamed\b/.test(beforeCursor)) {
            const namedItem = new vscode.CompletionItem('named', vscode.CompletionItemKind.Keyword);
            namedItem.sortText = '0_named';
            items.push(namedItem);
        }

        if (/\bimport\b/.test(beforeCursor) && /\{\s*$/.test(beforeCursor)) {
            const defItem = new vscode.CompletionItem('def', vscode.CompletionItemKind.Keyword);
            defItem.sortText = '0_def_import';
            items.push(defItem);

            const eventItem = new vscode.CompletionItem('event', vscode.CompletionItemKind.Keyword);
            eventItem.sortText = '0_event_import';
            items.push(eventItem);
        }

        const resolved = await this.importIndex.resolveImportsForDocument(document);
        const activeImport = await this.getActiveImportEntry(document, position);
        if (!activeImport) {
            return items;
        }

        const target = resolved.find(item => item.sourcePath === activeImport.sourcePath);
        if (!target) {
            return items;
        }

        for (const variableName of target.explicitVariables) {
            const item = new vscode.CompletionItem(variableName, vscode.CompletionItemKind.Variable);
            item.detail = 'Imported variable';
            item.sortText = `3_import_var_${variableName}`;
            items.push(item);
        }

        for (const eventPath of target.absoluteEvents) {
            const item = new vscode.CompletionItem(eventPath, vscode.CompletionItemKind.Event);
            item.detail = 'Imported absolute event';
            item.sortText = `5_import_event_${eventPath}`;
            items.push(item);
        }

        return items;
    }

    private async getActiveImportEntry(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<{ sourcePath: string } | null> {
        const parsed = await this.importIndex.parseDocument(document);
        const entry = parsed.imports.find(item =>
            position.line >= item.statementRange.start.line
            && position.line <= item.statementRange.end.line
        );
        return entry ? { sourcePath: entry.sourcePath } : null;
    }

    /**
     * Extract symbols from parse tree
     */
    private extractSymbols(tree: ParseTreeNode): {
        variables: Set<string>;
        states: Set<string>;
        events: Set<string>;
    } {
        const variables = new Set<string>();
        const states = new Set<string>();
        const events = new Set<string>();

        const visit = (node: ParseTreeNode) => {
            if (!node) return;

            const nodeName = node.constructor?.name;

            // Extract variable names
            if (nodeName === 'Def_assignmentContext') {
                const varName = this.extractVariableName(node);
                if (varName) variables.add(varName);
            }
            // Extract state names
            else if (nodeName === 'LeafStateDefinitionContext' || nodeName === 'CompositeStateDefinitionContext') {
                const stateName = this.extractStateName(node);
                if (stateName) states.add(stateName);
            }
            // Extract event names
            else if (nodeName === 'Event_definitionContext') {
                const eventName = this.extractEventName(node);
                if (eventName) events.add(eventName);
            }

            // Recursively visit children
            if (node.children) {
                node.children.forEach(child => visit(child));
            }
        };

        visit(tree);

        return { variables, states, events };
    }

    /**
     * Extract variable name from def_assignment node
     */
    private extractVariableName(node: ParseTreeNode): string | null {
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

    /**
     * Extract state name from state definition node
     */
    private extractStateName(node: ParseTreeNode): string | null {
        const children = node.children || [];

        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            const text = child.getText?.() || '';

            if (text === 'state') {
                if (i + 1 < children.length) {
                    const nextText = children[i + 1].getText?.() || '';
                    if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                        return nextText;
                    }
                }
            }
        }

        return null;
    }

    /**
     * Extract event name from event definition node
     */
    private extractEventName(node: ParseTreeNode): string | null {
        const children = node.children || [];

        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            const text = child.getText?.() || '';

            if (text === 'event') {
                if (i + 1 < children.length) {
                    const nextText = children[i + 1].getText?.() || '';
                    if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(nextText)) {
                        return nextText;
                    }
                }
            }
        }

        return null;
    }
}
