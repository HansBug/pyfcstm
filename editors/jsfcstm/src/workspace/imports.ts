import * as fs from 'fs';
import * as path from 'path';

import {getParser} from '../dsl/parser';
import {
    fallbackRangeFromText,
    FcstmDiagnostic,
    getDocumentFilePath,
    makeNodeRange,
    makeTokenRange,
    ParseTreeNode,
    rangeContains,
    TextDocumentLike,
    TextPositionLike,
    TextRange,
    tokenText,
} from '../utils/text';

export interface ImportEntry {
    sourcePath: string;
    alias: string;
    extraName?: string;
    statePath: string[];
    pathRange: TextRange;
    aliasRange: TextRange;
    statementRange: TextRange;
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

function normalizeFile(filePath: string): string {
    return path.normalize(path.resolve(filePath));
}

export function resolveImportReference(ownerFile: string, sourcePath: string): ResolvedImportTarget {
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

    async parseDocument(document: TextDocumentLike): Promise<ParsedDocumentInfo> {
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

    async resolveImportsForDocument(document: TextDocumentLike): Promise<ResolvedImportTarget[]> {
        const parsed = await this.parseDocument(document);
        const ownerFile = getDocumentFilePath(document);

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
        document: TextDocumentLike,
        position: TextPositionLike
    ): Promise<{ entry: ImportEntry; target: ResolvedImportTarget } | null> {
        const parsed = await this.parseDocument(document);
        const targetImport = parsed.imports.find(item => rangeContains(item.pathRange, position));
        if (!targetImport) {
            return null;
        }

        const resolved = resolveImportReference(getDocumentFilePath(document), targetImport.sourcePath);
        if (resolved.entryFile) {
            const summary = this.readFileSummary(resolved.entryFile);
            resolved.rootStateName = summary.rootStateName;
            resolved.absoluteEvents = [...summary.absoluteEvents];
            resolved.explicitVariables = [...summary.explicitVariables];
        }

        return {entry: targetImport, target: resolved};
    }

    async collectImportDiagnostics(document: TextDocumentLike): Promise<FcstmDiagnostic[]> {
        const parsed = await this.parseDocument(document);
        const diagnostics: FcstmDiagnostic[] = [];
        const stateAliasSeen = new Map<string, Set<string>>();
        const ownerFile = getDocumentFilePath(document);

        for (const importEntry of parsed.imports) {
            const stateKey = importEntry.statePath.join('.') || '<root>';
            let aliasSet = stateAliasSeen.get(stateKey);
            if (!aliasSet) {
                aliasSet = new Set<string>();
                stateAliasSeen.set(stateKey, aliasSet);
            }

            if (aliasSet.has(importEntry.alias)) {
                diagnostics.push({
                    range: importEntry.aliasRange,
                    message: `Duplicate import alias ${JSON.stringify(importEntry.alias)} in state ${JSON.stringify(stateKey)}.`,
                    severity: 'error',
                    source: 'fcstm',
                });
            } else {
                aliasSet.add(importEntry.alias);
            }

            const resolved = resolveImportReference(ownerFile, importEntry.sourcePath);
            if (resolved.missing) {
                diagnostics.push({
                    range: importEntry.pathRange,
                    message: `Import source ${JSON.stringify(importEntry.sourcePath)} cannot be resolved from ${JSON.stringify(path.dirname(ownerFile))}.`,
                    severity: 'error',
                    source: 'fcstm',
                });
            }
        }

        const cycles = this.collectCyclesFromDocument(ownerFile, parsed.imports);
        for (const cycle of cycles) {
            const firstHop = cycle.files[1];
            const importEntry = parsed.imports.find(item => {
                const resolved = resolveImportReference(ownerFile, item.sourcePath);
                return resolved.entryFile && normalizeFile(resolved.entryFile) === firstHop;
            });
            diagnostics.push({
                range: importEntry?.pathRange || fallbackRangeFromText(document, document.getText(), '', 0),
                message: `Circular import detected: ${cycle.files.map(item => path.basename(item)).join(' -> ')}.`,
                severity: 'warning',
                source: 'fcstm',
            });
        }

        return diagnostics;
    }

    private extractFromTree(tree: ParseTreeNode, document: TextDocumentLike): ParsedDocumentInfo {
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
}

let workspaceIndexInstance: FcstmImportWorkspaceIndex | null = null;

export function getImportWorkspaceIndex(): FcstmImportWorkspaceIndex {
    if (!workspaceIndexInstance) {
        workspaceIndexInstance = new FcstmImportWorkspaceIndex();
    }
    return workspaceIndexInstance;
}
