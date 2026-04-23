import * as fs from 'fs';
import * as path from 'path';

import type {FcstmAstDocument} from '../ast';
import {parseAstDocument} from '../ast';
import {
    buildStateMachineModel,
    type StateMachine as FcstmStateMachineModel,
} from '../model';
import {
    applyImportDefMappings,
    applyImportEventMappings,
    buildSemanticDocument,
    type FcstmSemanticDocument,
    type FcstmSemanticImport,
} from '../semantics';
import {getDocumentFilePath, TextDocumentLike} from '../utils/text';
import {buildStateMachineModelFromWorkspaceSnapshot} from './model-assembly';

export interface FcstmWorkspaceOverlay {
    filePath: string;
    text: string;
}

export interface FcstmImportResolution {
    ownerFile: string;
    sourcePath: string;
    resolvedFile?: string;
    entryFile?: string;
    exists: boolean;
    missing: boolean;
    import: FcstmSemanticImport;
    target?: FcstmWorkspaceGraphNode;
}

export interface FcstmImportCycle {
    files: string[];
}

export interface FcstmWorkspaceGraphNode {
    filePath: string;
    document: TextDocumentLike;
    ast: FcstmAstDocument | null;
    semantic: FcstmSemanticDocument | null;
    model: FcstmStateMachineModel | null;
    imports: FcstmImportResolution[];
}

export interface FcstmWorkspaceGraphSnapshot {
    rootFile: string;
    nodes: Record<string, FcstmWorkspaceGraphNode>;
    order: string[];
    cycles: FcstmImportCycle[];
}

interface TraversalState {
    nodes: Map<string, FcstmWorkspaceGraphNode>;
    order: string[];
    cycles: FcstmImportCycle[];
    cycleKeys: Set<string>;
    stack: string[];
}

function normalizeFile(filePath: string): string {
    return path.normalize(path.resolve(filePath));
}

function splitLines(text: string): string[] {
    return text.split('\n');
}

function createTextDocument(filePath: string, text: string): TextDocumentLike {
    const lines = splitLines(text);
    return {
        filePath,
        uri: {fsPath: filePath},
        lineCount: lines.length,
        getText() {
            return text;
        },
        lineAt(line: number) {
            return {
                text: lines[line] || '',
            };
        },
    };
}

export function resolveImportReference(ownerFile: string, sourcePath: string): {
    sourcePath: string;
    resolvedFile?: string;
    entryFile?: string;
    exists: boolean;
    missing: boolean;
} {
    const normalizedOwnerFile = normalizeFile(ownerFile);
    const absolutePath = path.isAbsolute(sourcePath)
        ? normalizeFile(sourcePath)
        : normalizeFile(path.join(path.dirname(normalizedOwnerFile), sourcePath));
    const directExists = fs.existsSync(absolutePath) && fs.statSync(absolutePath).isFile();

    if (directExists) {
        return {
            sourcePath,
            resolvedFile: absolutePath,
            entryFile: absolutePath,
            exists: true,
            missing: false,
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
        };
    }

    return {
        sourcePath,
        resolvedFile: absolutePath,
        exists: false,
        missing: true,
    };
}

function makeCycleKey(files: string[]): string {
    return files.join(' -> ');
}

export class FcstmWorkspaceGraph {
    private readonly overlays = new Map<string, FcstmWorkspaceOverlay>();

    setOverlay(filePath: string, text: string): void {
        const normalizedFile = normalizeFile(filePath);
        this.overlays.set(normalizedFile, {
            filePath: normalizedFile,
            text,
        });
    }

    removeOverlay(filePath: string): void {
        this.overlays.delete(normalizeFile(filePath));
    }

    clearOverlays(): void {
        this.overlays.clear();
    }

    getOverlay(filePath: string): FcstmWorkspaceOverlay | undefined {
        return this.overlays.get(normalizeFile(filePath));
    }

    async buildSnapshotForDocument(document: TextDocumentLike): Promise<FcstmWorkspaceGraphSnapshot> {
        const filePath = getDocumentFilePath(document);
        if (!filePath) {
            const ast = await parseAstDocument(document);
            const semantic = buildSemanticDocument(ast);
            return {
                rootFile: '<memory>',
                nodes: {
                    '<memory>': {
                        filePath: '<memory>',
                        document,
                        ast,
                        semantic,
                        model: buildStateMachineModel(ast),
                        imports: [],
                    },
                },
                order: ['<memory>'],
                cycles: [],
            };
        }

        const normalizedFile = normalizeFile(filePath);
        const state = this.createTraversalState();
        await this.traverseDocument(document, normalizedFile, state);
        this.hydrateModels(normalizedFile, state);
        return this.snapshotFromState(normalizedFile, state);
    }

    async buildSnapshotForFile(filePath: string): Promise<FcstmWorkspaceGraphSnapshot> {
        const normalizedFile = normalizeFile(filePath);
        const state = this.createTraversalState();
        await this.traverseFile(normalizedFile, state);
        this.hydrateModels(normalizedFile, state);
        return this.snapshotFromState(normalizedFile, state);
    }

    async getSemanticDocument(document: TextDocumentLike): Promise<FcstmSemanticDocument | null> {
        const snapshot = await this.buildSnapshotForDocument(document);
        return snapshot.nodes[snapshot.rootFile]?.semantic || null;
    }

    async getSemanticDocumentForFile(filePath: string): Promise<FcstmSemanticDocument | null> {
        const snapshot = await this.buildSnapshotForFile(filePath);
        return snapshot.nodes[snapshot.rootFile]?.semantic || null;
    }

    async getStateMachineModel(document: TextDocumentLike): Promise<FcstmStateMachineModel | null> {
        const snapshot = await this.buildSnapshotForDocument(document);
        return snapshot.nodes[snapshot.rootFile]?.model || null;
    }

    async getStateMachineModelForFile(filePath: string): Promise<FcstmStateMachineModel | null> {
        const snapshot = await this.buildSnapshotForFile(filePath);
        return snapshot.nodes[snapshot.rootFile]?.model || null;
    }

    private createTraversalState(): TraversalState {
        return {
            nodes: new Map<string, FcstmWorkspaceGraphNode>(),
            order: [],
            cycles: [],
            cycleKeys: new Set<string>(),
            stack: [],
        };
    }

    private snapshotFromState(
        rootFile: string,
        state: TraversalState
    ): FcstmWorkspaceGraphSnapshot {
        return {
            rootFile,
            nodes: Object.fromEntries(state.nodes.entries()),
            order: [...state.order],
            cycles: [...state.cycles],
        };
    }

    private async traverseFile(
        filePath: string,
        state: TraversalState
    ): Promise<FcstmWorkspaceGraphNode | undefined> {
        const document = this.loadDocument(filePath);
        if (!document) {
            return undefined;
        }

        return this.traverseDocument(document, filePath, state);
    }

    private async traverseDocument(
        document: TextDocumentLike,
        filePath: string,
        state: TraversalState
    ): Promise<FcstmWorkspaceGraphNode> {
        if (state.nodes.has(filePath)) {
            return state.nodes.get(filePath) as FcstmWorkspaceGraphNode;
        }

        const ast = await parseAstDocument(document);
        const semantic = buildSemanticDocument(ast);
        const model = buildStateMachineModel(semantic || ast);
        const node: FcstmWorkspaceGraphNode = {
            filePath,
            document,
            ast,
            semantic,
            model,
            imports: [],
        };

        state.nodes.set(filePath, node);
        state.order.push(filePath);

        if (!semantic) {
            return node;
        }

        state.stack.push(filePath);
        try {
            for (const semanticImport of semantic.imports) {
                const resolved = resolveImportReference(filePath, semanticImport.sourcePath);
                semanticImport.resolvedFile = resolved.resolvedFile;
                semanticImport.entryFile = resolved.entryFile;
                semanticImport.exists = resolved.exists;
                semanticImport.missing = resolved.missing;

                const resolution: FcstmImportResolution = {
                    ownerFile: filePath,
                    sourcePath: semanticImport.sourcePath,
                    resolvedFile: resolved.resolvedFile,
                    entryFile: resolved.entryFile,
                    exists: resolved.exists,
                    missing: resolved.missing,
                    import: semanticImport,
                };
                node.imports.push(resolution);

                if (!resolved.entryFile) {
                    continue;
                }

                const targetFile = normalizeFile(resolved.entryFile);
                if (state.stack.includes(targetFile)) {
                    this.recordCycle([...state.stack, targetFile], state);
                    continue;
                }

                const targetNode = state.nodes.get(targetFile) || await this.traverseFile(targetFile, state);
                if (!targetNode) {
                    continue;
                }

                resolution.target = targetNode;
                this.hydrateImport(semanticImport, targetNode.semantic, targetFile);
            }
        } finally {
            state.stack.pop();
        }

        return node;
    }

    private hydrateModels(rootFile: string, state: TraversalState): void {
        const nodes = Object.fromEntries(state.nodes.entries());
        for (const [filePath, node] of state.nodes.entries()) {
            try {
                node.model = buildStateMachineModelFromWorkspaceSnapshot(
                    {
                        rootFile,
                        nodes,
                    },
                    filePath
                ) || buildStateMachineModel(node.semantic || node.ast);
            } catch {
                node.model = buildStateMachineModel(node.semantic || node.ast);
            }
        }
    }

    private hydrateImport(
        semanticImport: FcstmSemanticImport,
        targetSemantic: FcstmSemanticDocument | null,
        targetFile: string
    ): void {
        if (!targetSemantic) {
            semanticImport.exists = true;
            semanticImport.missing = false;
            semanticImport.entryFile = targetFile;
            semanticImport.sourceVariables = [];
            semanticImport.sourceAbsoluteEvents = [];
            semanticImport.mappedVariables = [];
            semanticImport.mappedAbsoluteEvents = [];
            return;
        }

        semanticImport.targetModuleId = targetSemantic.module.identity.id;
        semanticImport.targetRootStateName = targetSemantic.summary.rootStateName;
        semanticImport.sourceVariables = [...targetSemantic.summary.explicitVariables];
        semanticImport.sourceAbsoluteEvents = [...targetSemantic.summary.absoluteEvents];
        semanticImport.mappedVariables = applyImportDefMappings(
            semanticImport.sourceVariables,
            semanticImport.defMappings
        );
        semanticImport.mappedAbsoluteEvents = applyImportEventMappings(
            semanticImport.sourceAbsoluteEvents,
            semanticImport.eventMappings
        );
    }

    private recordCycle(files: string[], state: TraversalState): void {
        const key = makeCycleKey(files);
        if (state.cycleKeys.has(key)) {
            return;
        }

        state.cycleKeys.add(key);
        state.cycles.push({files});
    }

    private loadDocument(filePath: string): TextDocumentLike | null {
        const overlay = this.getOverlay(filePath);
        if (overlay) {
            return createTextDocument(overlay.filePath, overlay.text);
        }

        const normalizedFile = normalizeFile(filePath);
        if (!fs.existsSync(normalizedFile) || !fs.statSync(normalizedFile).isFile()) {
            return null;
        }

        return createTextDocument(normalizedFile, fs.readFileSync(normalizedFile, 'utf8'));
    }
}

let workspaceGraphInstance: FcstmWorkspaceGraph | null = null;

export function getWorkspaceGraph(): FcstmWorkspaceGraph {
    if (!workspaceGraphInstance) {
        workspaceGraphInstance = new FcstmWorkspaceGraph();
    }

    return workspaceGraphInstance;
}
