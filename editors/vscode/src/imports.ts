/**
 * FCSTM import-aware lightweight workspace helpers.
 *
 * This module intentionally stays lightweight. It provides enough import
 * parsing, file resolution, and workspace indexing for editor features such as
 * diagnostics, go-to-definition, hover summaries, and import-focused
 * completion, without turning the extension into a full language server.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { getParser } from './parser';

interface ParseTreeNode {
    start?: { line?: number; column?: number; text?: string };
    stop?: { line?: number; column?: number; text?: string };
    children?: ParseTreeNode[];
    getText?: () => string;
    constructor?: { name: string };
    state_id?: { text?: string };
    event_name?: { text?: string };
    extra_name?: { text?: string };
    import_path?: { text?: string; line?: number; column?: number };
    state_alias?: { text?: string };
    source_event?: { getText?: () => string };
}

export interface ImportEntry {
    sourcePath: string;
    alias: string;
    extraName?: string;
    statePath: string[];
    pathRange: vscode.Range;
    aliasRange: vscode.Range;
    statementRange: vscode.Range;
}

export interface ParsedDocumentInfo {
    imports: ImportEntry[];
    explicitVariables: string[];
    rootStateName?: string;
    absoluteEvents: string[];
}

export interface ResolvedImportTarget {
    sourcePath: string;
    resolvedFile?: string;
    exists: boolean;
    entryFile?: string;
    missing: boolean;
    rootStateName?: string;
    absoluteEvents: string[];
    explicitVariables: string[];
}

export interface ImportCycle {
    files: string[];
}

interface FileSummary {
    filePath: string;
    entryFile?: string;
    exists: boolean;
    rootStateName?: string;
    absoluteEvents: string[];
    explicitVariables: string[];
    imports: { sourcePath: string; resolvedFile?: string; missing: boolean }[];
}

function unquoteText(value: string): string {
    if (
        (value.startsWith('"') && value.endsWith('"'))
        || (value.startsWith('\'') && value.endsWith('\''))
    ) {
        return value.slice(1, -1);
    }
    return value;
}

function tokenText(token?: { text?: string }): string {
    return token?.text || '';
}

function makeTokenRange(
    token: { line?: number; column?: number; text?: string } | undefined,
    document: vscode.TextDocument
): vscode.Range | undefined {
    if (!token || token.line == null || token.column == null) {
        return undefined;
    }

    const line = Math.max(0, Math.min((token.line || 1) - 1, document.lineCount - 1));
    const lineText = document.lineAt(line).text;
    const column = Math.max(0, Math.min(token.column || 0, lineText.length));
    const text = token.text || '';
    const end = Math.max(column + 1, Math.min(column + text.length, lineText.length));
    return new vscode.Range(line, column, line, end);
}

function makeNodeRange(
    node: ParseTreeNode,
    document: vscode.TextDocument
): vscode.Range | undefined {
    const startToken = node.start;
    const stopToken = node.stop;
    if (
        !startToken
        || !stopToken
        || startToken.line == null
        || startToken.column == null
        || stopToken.line == null
        || stopToken.column == null
    ) {
        return undefined;
    }

    const startLine = Math.max(0, Math.min(startToken.line - 1, document.lineCount - 1));
    const endLine = Math.max(0, Math.min(stopToken.line - 1, document.lineCount - 1));
    const endColumn = Math.max(
        stopToken.column + 1,
        stopToken.column + (stopToken.text ? stopToken.text.length : 1)
    );

    return new vscode.Range(startLine, startToken.column, endLine, endColumn);
}

function fallbackRangeFromText(
    document: vscode.TextDocument,
    text: string,
    search: string,
    startLine = 0
): vscode.Range {
    const lines = text.split('\n');
    for (let line = startLine; line < lines.length; line++) {
        const column = lines[line].indexOf(search);
        if (column >= 0) {
            return new vscode.Range(line, column, line, column + search.length);
        }
    }

    return new vscode.Range(0, 0, 0, 1);
}

function normalizeFile(filePath: string): string {
    return path.normalize(path.resolve(filePath));
}

function resolveImportReference(ownerFile: string, sourcePath: string): ResolvedImportTarget {
    const absolutePath = path.isAbsolute(sourcePath)
        ? normalizeFile(sourcePath)
        : normalizeFile(path.join(path.dirname(ownerFile), sourcePath));
    const directExists = fs.existsSync(absolutePath) && fs.statSync(absolutePath).isFile();

    if (directExists) {
        return {
            sourcePath,
            resolvedFile: absolutePath,
            entryFile: absolutePath,
            exists: true,
            missing: false,
            absoluteEvents: [],
            explicitVariables: [],
        };
    }

    const mainCandidate = normalizeFile(path.join(absolutePath, 'main.fcstm'));
    const mainExists = fs.existsSync(mainCandidate) && fs.statSync(mainCandidate).isFile();
    if (mainExists) {
        return {
            sourcePath,
            resolvedFile: absolutePath,
            entryFile: mainCandidate,
            exists: true,
            missing: false,
            absoluteEvents: [],
            explicitVariables: [],
        };
    }

    return {
        sourcePath,
        resolvedFile: absolutePath,
        exists: false,
        missing: true,
        absoluteEvents: [],
        explicitVariables: [],
    };
}

function addUnique(target: string[], value: string | undefined): void {
    if (value && !target.includes(value)) {
        target.push(value);
    }
}

export class FcstmImportWorkspaceIndex {
    private readonly parser = getParser();
    private readonly summaryCache = new Map<string, FileSummary>();

    async parseDocument(document: vscode.TextDocument): Promise<ParsedDocumentInfo> {
        const tree = await this.parser.parseTree(document.getText());
        if (!tree) {
            return {
                imports: [],
                explicitVariables: [],
                absoluteEvents: [],
            };
        }

        return this.extractFromTree(tree as ParseTreeNode, document);
    }

    async resolveImportsForDocument(document: vscode.TextDocument): Promise<ResolvedImportTarget[]> {
        const parsed = await this.parseDocument(document);
        const ownerFile = document.uri.fsPath;

        return parsed.imports.map(importEntry => {
            const resolved = resolveImportReference(ownerFile, importEntry.sourcePath);
            if (resolved.entryFile) {
                const summary = this.readFileSummary(resolved.entryFile);
                resolved.rootStateName = summary.rootStateName;
                resolved.absoluteEvents = [...summary.absoluteEvents];
                resolved.explicitVariables = [...summary.explicitVariables];
            }
            return resolved;
        });
    }

    async getResolvedImportAtPosition(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<{ entry: ImportEntry; target: ResolvedImportTarget } | null> {
        const parsed = await this.parseDocument(document);
        const targetImport = parsed.imports.find(item => this.rangeContains(item.pathRange, position));
        if (!targetImport) {
            return null;
        }

        const resolved = resolveImportReference(document.uri.fsPath, targetImport.sourcePath);
        if (resolved.entryFile) {
            const summary = this.readFileSummary(resolved.entryFile);
            resolved.rootStateName = summary.rootStateName;
            resolved.absoluteEvents = [...summary.absoluteEvents];
            resolved.explicitVariables = [...summary.explicitVariables];
        }

        return { entry: targetImport, target: resolved };
    }

    async collectImportDiagnostics(document: vscode.TextDocument): Promise<vscode.Diagnostic[]> {
        const parsed = await this.parseDocument(document);
        const diagnostics: vscode.Diagnostic[] = [];
        const stateAliasSeen = new Map<string, Set<string>>();

        for (const importEntry of parsed.imports) {
            const stateKey = importEntry.statePath.join('.') || '<root>';
            let aliasSet = stateAliasSeen.get(stateKey);
            if (!aliasSet) {
                aliasSet = new Set<string>();
                stateAliasSeen.set(stateKey, aliasSet);
            }

            if (aliasSet.has(importEntry.alias)) {
                const diagnostic = new vscode.Diagnostic(
                    importEntry.aliasRange,
                    `Duplicate import alias ${JSON.stringify(importEntry.alias)} in state ${JSON.stringify(stateKey)}.`,
                    vscode.DiagnosticSeverity.Error
                );
                diagnostic.source = 'fcstm';
                diagnostics.push(diagnostic);
            } else {
                aliasSet.add(importEntry.alias);
            }

            const resolved = resolveImportReference(document.uri.fsPath, importEntry.sourcePath);
            if (resolved.missing) {
                const diagnostic = new vscode.Diagnostic(
                    importEntry.pathRange,
                    `Import source ${JSON.stringify(importEntry.sourcePath)} cannot be resolved from ${JSON.stringify(path.dirname(document.uri.fsPath))}.`,
                    vscode.DiagnosticSeverity.Error
                );
                diagnostic.source = 'fcstm';
                diagnostics.push(diagnostic);
            }
        }

        const cycles = this.collectCyclesFromDocument(document.uri.fsPath, parsed.imports);
        for (const cycle of cycles) {
            const firstHop = cycle.files[1];
            const importEntry = parsed.imports.find(item => {
                const resolved = resolveImportReference(document.uri.fsPath, item.sourcePath);
                return resolved.entryFile && normalizeFile(resolved.entryFile) === firstHop;
            });
            const range = importEntry?.pathRange || new vscode.Range(0, 0, 0, 1);
            const diagnostic = new vscode.Diagnostic(
                range,
                `Circular import detected: ${cycle.files.map(item => path.basename(item)).join(' -> ')}.`,
                vscode.DiagnosticSeverity.Warning
            );
            diagnostic.source = 'fcstm';
            diagnostics.push(diagnostic);
        }

        return diagnostics;
    }

    private extractFromTree(tree: ParseTreeNode, document: vscode.TextDocument): ParsedDocumentInfo {
        const imports: ImportEntry[] = [];
        const explicitVariables = this.extractExplicitVariables(document.getText());
        const absoluteEvents: string[] = [];
        let rootStateName: string | undefined;

        const visit = (node: ParseTreeNode, statePath: string[]) => {
            if (!node) {
                return;
            }

            const nodeName = node.constructor?.name;
            let currentStatePath = statePath;

            if (
                nodeName === 'LeafStateDefinitionContext'
                || nodeName === 'CompositeStateDefinitionContext'
            ) {
                const stateName = tokenText(node.state_id);
                currentStatePath = stateName ? [...statePath, stateName] : statePath;
                if (!rootStateName && currentStatePath.length > 0) {
                    rootStateName = currentStatePath[0];
                }
            } else if (nodeName === 'Event_definitionContext') {
                const eventName = tokenText(node.event_name);
                if (eventName && statePath.length === 1) {
                    addUnique(absoluteEvents, `/${eventName}`);
                }
            } else if (nodeName === 'Import_event_mappingContext') {
                const sourceText = node.source_event?.getText?.();
                if (sourceText && sourceText.startsWith('/')) {
                    addUnique(absoluteEvents, sourceText);
                }
            } else if (nodeName === 'Import_statementContext') {
                const sourcePath = unquoteText(tokenText(node.import_path));
                const alias = tokenText(node.state_alias);
                const pathRange = makeTokenRange(node.import_path, document)
                    || fallbackRangeFromText(document, document.getText(), tokenText(node.import_path));
                const aliasRange = makeTokenRange(node.state_alias, document)
                    || fallbackRangeFromText(document, document.getText(), alias);
                const statementRange = makeNodeRange(node, document)
                    || pathRange;
                imports.push({
                    sourcePath,
                    alias,
                    extraName: unquoteText(tokenText(node.extra_name) || ''),
                    statePath: [...statePath],
                    pathRange,
                    aliasRange,
                    statementRange,
                });
            }

            for (const child of node.children || []) {
                visit(child, currentStatePath);
            }
        };

        visit(tree, []);

        return {
            imports,
            explicitVariables,
            rootStateName,
            absoluteEvents,
        };
    }

    private readFileSummary(filePath: string): FileSummary {
        const key = normalizeFile(filePath);
        const cached = this.summaryCache.get(key);
        if (cached) {
            return cached;
        }

        if (!fs.existsSync(key) || !fs.statSync(key).isFile()) {
            const missingSummary: FileSummary = {
                filePath: key,
                exists: false,
                absoluteEvents: [],
                explicitVariables: [],
                imports: [],
            };
            this.summaryCache.set(key, missingSummary);
            return missingSummary;
        }

        const content = fs.readFileSync(key, 'utf8');
        const summary = this.summarizeTextFile(key, content);
        this.summaryCache.set(key, summary);
        return summary;
    }

    private summarizeTextFile(filePath: string, text: string): FileSummary {
        const explicitVariables = this.extractExplicitVariables(text);
        const absoluteEvents: string[] = [];
        const imports: { sourcePath: string; resolvedFile?: string; missing: boolean }[] = [];

        let match: RegExpExecArray | null;
        const eventPattern = /^\s*event\s+([A-Za-z_][A-Za-z0-9_]*)\b/gm;
        while ((match = eventPattern.exec(text)) !== null) {
            addUnique(absoluteEvents, `/${match[1]}`);
        }

        const importPattern = /import\s+(['"])([^'"]+)\1\s+as\s+([A-Za-z_][A-Za-z0-9_]*)/g;
        while ((match = importPattern.exec(text)) !== null) {
            const resolved = resolveImportReference(filePath, match[2]);
            imports.push({
                sourcePath: match[2],
                resolvedFile: resolved.entryFile,
                missing: resolved.missing,
            });
        }

        const rootMatch = /\bstate\s+([A-Za-z_][A-Za-z0-9_]*)\b/.exec(text);
        return {
            filePath: normalizeFile(filePath),
            entryFile: normalizeFile(filePath),
            exists: true,
            rootStateName: rootMatch?.[1],
            absoluteEvents,
            explicitVariables,
            imports,
        };
    }

    private collectCyclesFromDocument(
        ownerFile: string,
        imports: ImportEntry[]
    ): ImportCycle[] {
        const cycles: ImportCycle[] = [];
        const ownerKey = normalizeFile(ownerFile);

        for (const importEntry of imports) {
            const resolved = resolveImportReference(ownerFile, importEntry.sourcePath);
            if (!resolved.entryFile) {
                continue;
            }
            const cycle = this.detectCycle(ownerKey, resolved.entryFile, [ownerKey]);
            if (cycle) {
                cycles.push(cycle);
            }
        }

        return cycles;
    }

    private detectCycle(ownerFile: string, currentFile: string, chain: string[]): ImportCycle | null {
        const currentKey = normalizeFile(currentFile);
        if (chain.includes(currentKey)) {
            return {
                files: [...chain, currentKey],
            };
        }

        const summary = this.readFileSummary(currentKey);
        if (!summary.exists) {
            return null;
        }

        const nextChain = [...chain, currentKey];
        for (const item of summary.imports) {
            if (!item.resolvedFile) {
                continue;
            }

            const nextKey = normalizeFile(item.resolvedFile);
            if (nextKey === ownerFile) {
                return {
                    files: [...nextChain, ownerFile],
                };
            }

            const nested = this.detectCycle(ownerFile, nextKey, nextChain);
            if (nested) {
                return nested;
            }
        }

        return null;
    }

    private extractExplicitVariables(text: string): string[] {
        const explicitVariables: string[] = [];
        const variablePattern = /^\s*def\s+(?:int|float)\s+([A-Za-z_][A-Za-z0-9_]*)\b/gm;
        let match: RegExpExecArray | null;
        while ((match = variablePattern.exec(text)) !== null) {
            addUnique(explicitVariables, match[1]);
        }
        return explicitVariables;
    }

    private rangeContains(range: vscode.Range, position: vscode.Position): boolean {
        if (position.line < range.start.line || position.line > range.end.line) {
            return false;
        }
        if (position.line === range.start.line && position.character < range.start.character) {
            return false;
        }
        if (position.line === range.end.line && position.character > range.end.character) {
            return false;
        }
        return true;
    }
}

let workspaceIndexInstance: FcstmImportWorkspaceIndex | null = null;

export function getImportWorkspaceIndex(): FcstmImportWorkspaceIndex {
    if (!workspaceIndexInstance) {
        workspaceIndexInstance = new FcstmImportWorkspaceIndex();
    }
    return workspaceIndexInstance;
}
