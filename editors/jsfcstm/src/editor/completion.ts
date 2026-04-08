import {getParser} from '../dsl/parser';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {getWorkspaceGraph} from '../workspace';
import {collectSymbolsFromTree} from './symbols';
import {ParseTreeNode, rangeContains, TextDocumentLike, TextPositionLike} from '../utils/text';

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
    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    if (semantic) {
        for (const variable of semantic.variables) {
            items.push({
                label: variable.name,
                kind: 'variable',
                sortText: `3_${variable.name}`,
            });
        }
        for (const state of semantic.states) {
            items.push({
                label: state.name,
                kind: 'class',
                sortText: `4_${state.name}`,
            });
        }
        for (const event of semantic.events.filter(item => item.declared)) {
            items.push({
                label: event.name,
                kind: 'event',
                sortText: `5_${event.name}`,
            });
        }

        return items;
    }

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
): Promise<FcstmCompletionItem[]> {
    const items: FcstmCompletionItem[] = [];
    const lineText = document.lineAt(position.line).text;
    const beforeCursor = lineText.substring(0, position.character);

    if (/\bimport\b/.test(beforeCursor) && !/\bas\b/.test(beforeCursor)) {
        items.push({
            label: 'as',
            kind: 'keyword',
            sortText: '0_as',
        });
    }

    if (/\bimport\b/.test(beforeCursor) && /\bas\b/.test(beforeCursor) && !/\bnamed\b/.test(beforeCursor)) {
        items.push({
            label: 'named',
            kind: 'keyword',
            sortText: '0_named',
        });
    }

    if (/\bimport\b/.test(beforeCursor) && /\{\s*$/.test(beforeCursor)) {
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
        return items;
    }

    const resolved = await getImportWorkspaceIndex().resolveImportsForDocument(document);
    const target = resolved.find(item => item.sourcePath === activeImport.sourcePath);
    if (!target) {
        return items;
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

    return items;
}

export async function collectCompletionItems(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmCompletionItem[]> {
    const items: FcstmCompletionItem[] = [];
    const lineText = document.lineAt(position.line).text;
    const beforeCursor = lineText.substring(0, position.character);

    if (isInComment(beforeCursor) || isInString(beforeCursor)) {
        return items;
    }

    items.push(...getKeywordCompletions());
    items.push(...getConstantCompletions());
    items.push(...getFunctionCompletions());
    items.push(...await getDocumentSymbolCompletions(document));
    items.push(...await getImportAwareCompletions(document, position));

    return items;
}
