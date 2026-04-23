import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

import * as vscode from 'vscode';
import {
    buildFcstmDiagramWebviewPayload,
    getWorkspaceGraph,
    resolveFcstmDiagramPreviewOptions,
    type FcstmDiagramPreviewOptions,
    type FcstmDiagramWebviewPayload,
    type ResolvedFcstmDiagramPreviewOptions,
} from '@pyfcstm/jsfcstm';

type PreviewLayoutMode = 'side' | 'alone';

interface PreviewSummaryEntry {
    label: string;
    value: number;
}

interface PreviewSharedEventView {
    label: string;
    qualifiedName: string;
    transitionCount: number;
    color: string;
}

interface PreviewEffectNoteView {
    title: string;
    meta?: string;
    effectText: string;
    color?: string;
}

interface PreviewWebviewState {
    title: string;
    filePath: string;
    rootStateName?: string;
    payload?: FcstmDiagramWebviewPayload;
    previewOptions: ResolvedFcstmDiagramPreviewOptions;
    collapsedStateIds: string[];
    emptyTitle: string;
    emptyMessage: string;
    summary: PreviewSummaryEntry[];
    variables: string[];
    sharedEvents: PreviewSharedEventView[];
    effectNotes: PreviewEffectNoteView[];
}

function loadElkBrowserBundle(): string {
    try {
        const inlineModule = require('@fcstm/elk-inline');
        if (typeof inlineModule === 'string') {
            return inlineModule;
        }
        if (inlineModule && typeof inlineModule.default === 'string') {
            return inlineModule.default;
        }
    } catch {
        // Fall through to the filesystem fallback below.
    }

    return fs.readFileSync(
        path.join(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'),
        'utf8'
    );
}

function loadPreviewWebviewBundle(): string {
    try {
        const inlineModule = require('@fcstm/preview-webview-inline');
        if (typeof inlineModule === 'string') {
            return inlineModule;
        }
        if (inlineModule && typeof inlineModule.default === 'string') {
            return inlineModule.default;
        }
    } catch {
        // Fall through to the filesystem fallback below.
    }

    // Fallback for tsc output (out/), where the esbuild inline plugin
    // hasn't run; read the production bundle from dist/.
    const candidates = [
        path.join(__dirname, 'preview-webview.js'),                    // dist/<> (esbuild output)
        path.resolve(__dirname, '..', 'dist', 'preview-webview.js'),   // out/ → dist/
    ];
    for (const candidate of candidates) {
        if (fs.existsSync(candidate)) {
            return fs.readFileSync(candidate, 'utf8');
        }
    }
    throw new Error(`preview-webview bundle not found in any of: ${candidates.join(', ')}`);
}

const elkBrowserBundle = loadElkBrowserBundle();
const previewWebviewBundle = loadPreviewWebviewBundle();

function isFcstmPath(filePath: string | undefined): boolean {
    return Boolean(filePath && filePath.toLowerCase().endsWith('.fcstm'));
}

function isFcstmDocument(document: vscode.TextDocument | undefined): document is vscode.TextDocument {
    return Boolean(document && (document.languageId === 'fcstm' || isFcstmPath(document.fileName) || isFcstmPath(document.uri.fsPath)));
}

function isFcstmUri(uri: vscode.Uri | undefined): uri is vscode.Uri {
    return Boolean(uri && isFcstmPath(uri.fsPath));
}

function hasFileSystemPath(document: vscode.TextDocument): boolean {
    return document.uri.scheme === 'file' && Boolean(document.uri.fsPath);
}

function basenameForDocument(document: vscode.TextDocument): string {
    const fileName = document.fileName || document.uri.fsPath || document.uri.toString();
    return path.basename(fileName);
}

function createNonce(): string {
    return crypto.randomBytes(16).toString('hex');
}

function toScriptLiteral<T>(value: T): string {
    return JSON.stringify(value)
        .replace(/</g, '\\u003c')
        .replace(/>/g, '\\u003e')
        .replace(/&/g, '\\u0026');
}

function escapeInlineScript(value: string): string {
    return value.replace(/<\/script/gi, '<\\/script');
}

function buildSummaryEntries(payload: FcstmDiagramWebviewPayload | null): PreviewSummaryEntry[] {
    if (!payload) {
        return [];
    }
    return [
        {label: 'vars', value: payload.summary.variables},
        {label: 'states', value: payload.summary.states},
        {label: 'events', value: payload.summary.events},
        {label: 'transitions', value: payload.summary.transitions},
        {label: 'actions', value: payload.summary.actions},
    ];
}

function buildVariables(
    payload: FcstmDiagramWebviewPayload | null,
    options: ResolvedFcstmDiagramPreviewOptions
): string[] {
    if (!payload || !options.showVariableDefinitions) {
        return [];
    }
    return payload.variables.map(v => `def ${v.valueType} ${v.name} = ${v.initializer}`);
}

function buildSharedEvents(
    payload: FcstmDiagramWebviewPayload | null,
    options: ResolvedFcstmDiagramPreviewOptions
): PreviewSharedEventView[] {
    if (!payload || (options.eventVisualizationMode !== 'legend' && options.eventVisualizationMode !== 'both')) {
        return [];
    }
    return payload.eventLegend.map(item => ({
        label: item.label,
        qualifiedName: `/${item.qualifiedName.split('.').slice(1).join('.')}`,
        transitionCount: item.transitionCount,
        color: item.color,
    }));
}

function buildEffectNotes(payload: FcstmDiagramWebviewPayload | null): PreviewEffectNoteView[] {
    if (!payload) {
        return [];
    }
    return payload.effectNotes.map(note => ({
        title: note.title,
        meta: note.meta,
        effectText: note.effectText,
        color: note.eventColor,
    }));
}

/**
 * Generate the webview HTML shell. The actual UI is a Vue 3 + Naive UI
 * app that the extension bundle inlines — we only provide a stable
 * mount point + the initial state + the elkjs runtime.
 */
function createPreviewHtml(
    webview: vscode.Webview,
    elkRuntimeScript: string,
    webviewAppScript: string,
    initialState: PreviewWebviewState
): string {
    const nonce = createNonce();
    const initialData = toScriptLiteral(initialState);
    const elkRuntime = escapeInlineScript(elkRuntimeScript);
    const appScript = escapeInlineScript(webviewAppScript);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data: blob:; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'nonce-${nonce}' ${webview.cspSource} 'unsafe-eval';" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FCSTM Preview</title>
    <style>
        html, body, #app { margin: 0; padding: 0; height: 100%; }
        body {
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            background: var(--vscode-editor-background, #fff);
            color: var(--vscode-editor-foreground, #1f2937);
        }
    </style>
</head>
<body>
    <div id="app"></div>
    <script nonce="${nonce}">
/* FCSTM embedded ELK runtime */
${elkRuntime}
    </script>
    <script nonce="${nonce}">
window.__FCSTM_INITIAL_STATE__ = ${initialData};
    </script>
    <script nonce="${nonce}">
/* FCSTM embedded preview-webview bundle (Vue 3 + Naive UI) */
${appScript}
    </script>
</body>
</html>`;
}

export class FcstmPreviewController implements vscode.Disposable {
    private panel: vscode.WebviewPanel | null = null;
    private readonly disposables: vscode.Disposable[] = [];
    private currentDocumentUri: string | null = null;
    private updateTimer: NodeJS.Timeout | undefined;
    private updateSequence = 0;
    private cursorTrackTimer: NodeJS.Timeout | undefined;
    private lastSentRangeKey = '';
    // detailLevel + eventVisualizationMode are no longer user-tunable from
    // the UI; the preview defaults to the full / both combo so the diagram
    // shows everything it can without the user having to hunt dropdowns.
    private previewOptions: FcstmDiagramPreviewOptions = {
        detailLevel: 'full',
        eventVisualizationMode: 'both',
        // Effects default to hidden — the diagram stays uncluttered until
        // the user explicitly opts into inline / note rendering.
        transitionEffectMode: 'hide',
    };
    private collapsedStateIds = new Set<string>();
    private layoutMode: PreviewLayoutMode = 'side';

    constructor(private readonly context: vscode.ExtensionContext) {
        const graph = getWorkspaceGraph();
        for (const document of vscode.workspace.textDocuments) {
            if (isFcstmDocument(document)) {
                graph.setOverlay(document.uri.fsPath, document.getText());
            }
        }

        this.disposables.push(
            vscode.commands.registerCommand('fcstm.preview.open', (resource?: vscode.Uri) => this.openWithMode('side', resource)),
            vscode.commands.registerCommand('fcstm.preview.openAlone', (resource?: vscode.Uri) => this.openWithMode('alone', resource)),
            vscode.commands.registerCommand('fcstm.preview.toggle', () => this.togglePreview()),
            vscode.workspace.onDidOpenTextDocument(document => this.syncOverlay(document)),
            vscode.workspace.onDidChangeTextDocument(event => {
                this.syncOverlay(event.document);
                if (this.panel && this.currentDocumentUri === event.document.uri.toString() && isFcstmDocument(event.document)) {
                    this.scheduleRefresh(event.document);
                } else if (this.panel && vscode.window.activeTextEditor && isFcstmDocument(vscode.window.activeTextEditor.document)) {
                    this.scheduleRefresh(vscode.window.activeTextEditor.document);
                }
            }),
            vscode.workspace.onDidSaveTextDocument(document => {
                this.syncOverlay(document);
                if (this.panel && this.currentDocumentUri === document.uri.toString()) {
                    this.scheduleRefresh(document);
                }
            }),
            vscode.workspace.onDidCloseTextDocument(document => {
                this.clearOverlay(document);
                if (this.panel && vscode.window.activeTextEditor && isFcstmDocument(vscode.window.activeTextEditor.document)) {
                    this.scheduleRefresh(vscode.window.activeTextEditor.document);
                }
            }),
            vscode.window.onDidChangeActiveTextEditor(editor => {
                if (this.panel && editor && isFcstmDocument(editor.document)) {
                    this.scheduleRefresh(editor.document);
                }
            }),
            vscode.window.onDidChangeTextEditorSelection(event => {
                if (!this.panel) {
                    return;
                }
                if (!isFcstmDocument(event.textEditor.document)) {
                    return;
                }
                const documentUri = event.textEditor.document.uri.toString();
                if (this.currentDocumentUri && this.currentDocumentUri !== documentUri) {
                    return;
                }
                this.scheduleCursorSync(event.textEditor);
            })
        );
    }

    dispose(): void {
        if (this.updateTimer) {
            clearTimeout(this.updateTimer);
            this.updateTimer = undefined;
        }
        if (this.cursorTrackTimer) {
            clearTimeout(this.cursorTrackTimer);
            this.cursorTrackTimer = undefined;
        }
        if (this.panel) {
            this.panel.dispose();
            this.panel = null;
        }
        while (this.disposables.length > 0) {
            const disposable = this.disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }

    private scheduleCursorSync(editor: vscode.TextEditor): void {
        if (this.cursorTrackTimer) {
            clearTimeout(this.cursorTrackTimer);
            this.cursorTrackTimer = undefined;
        }
        this.cursorTrackTimer = setTimeout(() => {
            this.cursorTrackTimer = undefined;
            this.sendCursorToWebview(editor);
        }, 80);
    }

    private sendCursorToWebview(editor: vscode.TextEditor): void {
        if (!this.panel) {
            return;
        }
        const selection = editor.selection;
        if (!selection || !selection.start || !selection.end) {
            return;
        }
        const range = {
            start: {line: selection.start.line, character: selection.start.character},
            end: {line: selection.end.line, character: selection.end.character},
        };
        const key = `${range.start.line}:${range.start.character}-${range.end.line}:${range.end.character}`;
        if (key === this.lastSentRangeKey) {
            return;
        }
        this.lastSentRangeKey = key;
        void this.panel.webview.postMessage({type: 'setActiveRange', range});
    }

    private async togglePreview(): Promise<void> {
        if (this.panel) {
            this.panel.dispose();
            this.panel = null;
            this.currentDocumentUri = null;
            return;
        }
        await this.openWithMode('side');
    }

    private async openWithMode(mode: PreviewLayoutMode, resource?: vscode.Uri): Promise<void> {
        const document = await this.resolveDocument(resource);
        if (!document || !isFcstmDocument(document)) {
            await vscode.window.showWarningMessage('Open an FCSTM document first.');
            return;
        }
        this.layoutMode = mode;
        const viewColumn = mode === 'alone' ? vscode.ViewColumn.Active : vscode.ViewColumn.Beside;
        if (this.panel) {
            this.panel.reveal(viewColumn, true);
        } else {
            this.createPanel(document, viewColumn);
        }
        this.scheduleRefresh(document, true);
    }

    private createPanel(document: vscode.TextDocument, viewColumn: vscode.ViewColumn): void {
        this.panel = vscode.window.createWebviewPanel(
            'fcstmPreview',
            `FCSTM Preview: ${basenameForDocument(document)}`,
            {preserveFocus: true, viewColumn},
            {
                enableFindWidget: true,
                enableScripts: true,
                localResourceRoots: [this.context.extensionUri],
                retainContextWhenHidden: true,
            }
        );
        this.panel.onDidDispose(() => {
            this.panel = null;
            this.currentDocumentUri = null;
        }, null, this.disposables);
        this.panel.webview.onDidReceiveMessage(msg => void this.handleWebviewMessage(msg), null, this.disposables);

        const initialOptions = resolveFcstmDiagramPreviewOptions(this.previewOptions);
        const initialState: PreviewWebviewState = {
            title: basenameForDocument(document),
            filePath: document.uri.fsPath,
            previewOptions: initialOptions,
            collapsedStateIds: Array.from(this.collapsedStateIds),
            emptyTitle: 'FCSTM Preview',
            emptyMessage: 'Preparing preview...',
            summary: [],
            variables: [],
            sharedEvents: [],
            effectNotes: [],
        };
        this.panel.webview.html = createPreviewHtml(
            this.panel.webview,
            elkBrowserBundle,
            previewWebviewBundle,
            initialState
        );
    }

    private async handleWebviewMessage(message: unknown): Promise<void> {
        if (!message || typeof message !== 'object' || !this.panel) {
            return;
        }
        const payload = message as {
            type?: string;
            options?: Partial<FcstmDiagramPreviewOptions>;
            range?: {start: {line: number; character: number}; end: {line: number; character: number}};
            collapsed?: string[];
            mode?: PreviewLayoutMode;
            svg?: string;
            base64?: string;
            message?: string;
        };

        switch (payload.type) {
            case 'patchOptions':
                if (payload.options && typeof payload.options === 'object') {
                    this.previewOptions = {...this.previewOptions, ...payload.options};
                    await this.refreshCurrentDocument();
                }
                return;
            case 'setCollapsed':
                this.collapsedStateIds = new Set(Array.isArray(payload.collapsed) ? payload.collapsed : []);
                await this.refreshCurrentDocument();
                return;
            case 'revealSource':
                if (payload.range) {
                    await this.revealSourceRange(payload.range);
                }
                return;
            case 'setLayoutMode':
                if (payload.mode === 'side' || payload.mode === 'alone') {
                    await this.switchLayoutMode(payload.mode);
                }
                return;
            case 'exportSvg':
                if (typeof payload.svg === 'string') {
                    await this.exportSvg(payload.svg);
                }
                return;
            case 'exportPng':
                if (typeof payload.base64 === 'string') {
                    await this.exportPng(payload.base64);
                }
                return;
            case 'exportError':
                if (payload.message) {
                    await vscode.window.showErrorMessage(`Export failed: ${payload.message}`);
                }
                return;
        }
    }

    private async switchLayoutMode(mode: PreviewLayoutMode): Promise<void> {
        if (!this.panel) {
            return;
        }
        if (this.layoutMode === mode) {
            return;
        }
        this.layoutMode = mode;
        const targetColumn = mode === 'alone' ? vscode.ViewColumn.Active : vscode.ViewColumn.Beside;
        this.panel.reveal(targetColumn, mode === 'alone' ? false : true);
    }

    private async revealSourceRange(range: {start: {line: number; character: number}; end: {line: number; character: number}}): Promise<void> {
        if (!this.currentDocumentUri) {
            return;
        }
        let document: vscode.TextDocument | undefined = vscode.workspace.textDocuments.find(d => d.uri.toString() === this.currentDocumentUri);
        if (!document) {
            try {
                document = await vscode.workspace.openTextDocument(vscode.Uri.parse(this.currentDocumentUri));
            } catch {
                return;
            }
        }
        const vsRange = new vscode.Range(
            new vscode.Position(range.start.line, range.start.character),
            new vscode.Position(range.end.line, range.end.character)
        );
        const editor = await vscode.window.showTextDocument(document, {
            viewColumn: vscode.ViewColumn.One,
            preserveFocus: false,
            preview: false,
            selection: vsRange,
        });
        editor.revealRange(vsRange, vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }

    private async exportSvg(svg: string): Promise<void> {
        const defaultUri = this.currentDocumentUri
            ? vscode.Uri.file(this.currentDocumentUri.replace(/^file:\/\//, '').replace(/\.fcstm$/i, '.svg'))
            : undefined;
        const uri = await vscode.window.showSaveDialog({
            defaultUri,
            filters: {'SVG Image': ['svg']},
            saveLabel: 'Export SVG',
        });
        if (!uri) {
            return;
        }
        await vscode.workspace.fs.writeFile(uri, Buffer.from(svg, 'utf8'));
        await vscode.window.showInformationMessage(`Exported SVG to ${uri.fsPath}`);
    }

    private async exportPng(base64: string): Promise<void> {
        const defaultUri = this.currentDocumentUri
            ? vscode.Uri.file(this.currentDocumentUri.replace(/^file:\/\//, '').replace(/\.fcstm$/i, '.png'))
            : undefined;
        const uri = await vscode.window.showSaveDialog({
            defaultUri,
            filters: {'PNG Image': ['png']},
            saveLabel: 'Export PNG',
        });
        if (!uri) {
            return;
        }
        await vscode.workspace.fs.writeFile(uri, Buffer.from(base64, 'base64'));
        await vscode.window.showInformationMessage(`Exported PNG to ${uri.fsPath}`);
    }

    private async refreshCurrentDocument(): Promise<void> {
        if (!this.panel || !this.currentDocumentUri) {
            return;
        }
        const document = vscode.workspace.textDocuments.find(d => d.uri.toString() === this.currentDocumentUri)
            || vscode.window.activeTextEditor?.document;
        if (document && isFcstmDocument(document)) {
            await this.refresh(document);
        }
    }

    private syncOverlay(document: vscode.TextDocument): void {
        if (!isFcstmDocument(document) || !hasFileSystemPath(document)) {
            return;
        }
        getWorkspaceGraph().setOverlay(document.uri.fsPath, document.getText());
    }

    private clearOverlay(document: vscode.TextDocument): void {
        if (!isFcstmDocument(document) || !hasFileSystemPath(document)) {
            return;
        }
        getWorkspaceGraph().removeOverlay(document.uri.fsPath);
    }

    private async resolveDocument(resource?: vscode.Uri): Promise<vscode.TextDocument | null> {
        if (resource && isFcstmUri(resource)) {
            const existing = vscode.workspace.textDocuments.find(d => d.uri.toString() === resource.toString());
            if (existing) {
                return existing;
            }
            return vscode.workspace.openTextDocument(resource);
        }
        const editor = vscode.window.activeTextEditor;
        if (editor && isFcstmDocument(editor.document)) {
            return editor.document;
        }
        return null;
    }

    private scheduleRefresh(document: vscode.TextDocument, immediate = false): void {
        const execute = () => void this.refresh(document);
        if (this.updateTimer) {
            clearTimeout(this.updateTimer);
            this.updateTimer = undefined;
        }
        if (immediate) {
            execute();
            return;
        }
        this.updateTimer = setTimeout(execute, 120);
    }

    private async refresh(document: vscode.TextDocument): Promise<void> {
        if (!this.panel || !isFcstmDocument(document)) {
            return;
        }
        const sequence = ++this.updateSequence;
        this.currentDocumentUri = document.uri.toString();

        let state: PreviewWebviewState;
        try {
            const previewOptions = resolveFcstmDiagramPreviewOptions(this.previewOptions);
            const payload = await buildFcstmDiagramWebviewPayload(document, this.previewOptions, {
                collapsedStateIds: this.collapsedStateIds,
            });
            const title = basenameForDocument(document);

            state = {
                title,
                filePath: document.uri.fsPath || document.uri.toString(),
                rootStateName: payload ? payload.machineName : undefined,
                payload: payload || undefined,
                previewOptions,
                collapsedStateIds: Array.from(this.collapsedStateIds),
                emptyTitle: title,
                emptyMessage: 'No diagram available.',
                summary: buildSummaryEntries(payload),
                variables: buildVariables(payload, previewOptions),
                sharedEvents: buildSharedEvents(payload, previewOptions),
                effectNotes: buildEffectNotes(payload),
            };
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            const title = basenameForDocument(document);
            state = {
                title,
                filePath: document.uri.fsPath || document.uri.toString(),
                previewOptions: resolveFcstmDiagramPreviewOptions(this.previewOptions),
                collapsedStateIds: Array.from(this.collapsedStateIds),
                emptyTitle: title,
                emptyMessage: message,
                summary: [],
                variables: [],
                sharedEvents: [],
                effectNotes: [],
            };
        }

        if (!this.panel || sequence !== this.updateSequence) {
            return;
        }
        this.panel.title = `FCSTM Preview: ${basenameForDocument(document)}`;
        void this.panel.webview.postMessage(state);

        // A fresh payload invalidates the last-sent range cache so the next
        // cursor movement still reaches the webview even if the line/column
        // numbers happen to repeat.
        this.lastSentRangeKey = '';
        const activeEditor = vscode.window.activeTextEditor;
        if (
            activeEditor
            && activeEditor.document.uri.toString() === this.currentDocumentUri
        ) {
            this.scheduleCursorSync(activeEditor);
        }
    }
}
