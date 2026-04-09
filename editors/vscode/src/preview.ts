import * as crypto from 'crypto';
import * as path from 'path';

import * as vscode from 'vscode';
import {
    buildFcstmDiagramFromDocument,
    collectDocumentDiagnostics,
    getWorkspaceGraph,
    renderFcstmDiagramSvg,
} from '@pyfcstm/jsfcstm';

interface PreviewDiagnosticView {
    severity: string;
    message: string;
    location: string;
}

interface PreviewWebviewState {
    title: string;
    filePath: string;
    rootStateName?: string;
    svg: string;
    diagnostics: PreviewDiagnosticView[];
    status: 'ok' | 'warning' | 'error';
    statusText: string;
}

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

function escapeHtml(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function basenameForDocument(document: vscode.TextDocument): string {
    const fileName = document.fileName || document.uri.fsPath || document.uri.toString();
    return path.basename(fileName);
}

function buildEmptyPreviewSvg(title: string, message: string): string {
    const safeTitle = escapeHtml(title);
    const safeMessage = escapeHtml(message);

    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="220" viewBox="0 0 960 220" role="img">',
        '<style>',
        '.bg{fill:#f7fbff;}',
        '.panel{fill:#ffffff;stroke:#92b8e6;stroke-width:1.5;}',
        '.title{font:700 24px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#1d446b;}',
        '.message{font:500 14px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#527393;}',
        '</style>',
        '<rect class="bg" x="0" y="0" width="960" height="220" />',
        '<rect class="panel" x="24" y="24" rx="18" ry="18" width="912" height="172" />',
        `<text class="title" x="48" y="74">${safeTitle}</text>`,
        `<text class="message" x="48" y="112">${safeMessage}</text>`,
        '</svg>',
    ].join('');
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

function buildDiagnosticView(
    diagnostic: Awaited<ReturnType<typeof collectDocumentDiagnostics>>[number]
): PreviewDiagnosticView {
    const line = diagnostic.range.start.line + 1;
    const column = diagnostic.range.start.character + 1;
    return {
        severity: diagnostic.severity,
        message: diagnostic.message,
        location: `L${line}:C${column}`,
    };
}

function createPreviewHtml(
    webview: vscode.Webview,
    initialState: PreviewWebviewState
): string {
    const nonce = createNonce();
    const initialData = toScriptLiteral(initialState);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data:; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'nonce-${nonce}';" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FCSTM Preview</title>
    <style>
        :root {
            --bg: var(--vscode-editor-background);
            --fg: var(--vscode-editor-foreground);
            --muted: var(--vscode-descriptionForeground);
            --panel: rgba(87, 132, 186, 0.10);
            --border: rgba(94, 140, 194, 0.45);
            --accent: #2d6aa8;
            --warning: #b7791f;
            --error: #b33a3a;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 16px;
            color: var(--fg);
            background:
                radial-gradient(circle at top left, rgba(97, 149, 213, 0.14), transparent 34%),
                linear-gradient(180deg, color-mix(in srgb, var(--bg) 88%, #e6f1fb 12%), var(--bg));
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
        }

        .shell {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .meta {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--panel);
            padding: 14px 16px;
        }

        .title-row {
            display: flex;
            align-items: center;
            gap: 12px;
            justify-content: space-between;
            flex-wrap: wrap;
        }

        .title {
            font-size: 16px;
            font-weight: 700;
        }

        .subtitle {
            margin-top: 6px;
            font-size: 12px;
            color: var(--muted);
            word-break: break-all;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: rgba(45, 106, 168, 0.14);
            color: var(--accent);
        }

        .badge.warning {
            background: rgba(183, 121, 31, 0.16);
            color: var(--warning);
        }

        .badge.error {
            background: rgba(179, 58, 58, 0.16);
            color: var(--error);
        }

        .preview {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.04);
            padding: 12px;
            overflow: auto;
        }

        .preview svg {
            display: block;
            width: auto;
            max-width: none;
            height: auto;
        }

        .diagnostics {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.03);
            padding: 12px 14px;
        }

        .diagnostics.hidden {
            display: none;
        }

        .diagnostics-title {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .diagnostic-list {
            list-style: none;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .diagnostic-item {
            border-left: 3px solid var(--border);
            padding-left: 10px;
        }

        .diagnostic-item.error {
            border-left-color: var(--error);
        }

        .diagnostic-item.warning {
            border-left-color: var(--warning);
        }

        .diagnostic-meta {
            font-size: 11px;
            color: var(--muted);
            margin-bottom: 2px;
        }

        .diagnostic-message {
            font-size: 12px;
            line-height: 1.45;
        }
    </style>
</head>
<body>
    <div class="shell">
        <section class="meta">
            <div class="title-row">
                <div class="title" id="title"></div>
                <div class="badge" id="status"></div>
            </div>
            <div class="subtitle" id="file-path"></div>
        </section>
        <section class="preview" id="preview"></section>
        <section class="diagnostics hidden" id="diagnostics">
            <div class="diagnostics-title">Diagnostics</div>
            <ul class="diagnostic-list" id="diagnostic-list"></ul>
        </section>
    </div>
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const titleNode = document.getElementById('title');
        const filePathNode = document.getElementById('file-path');
        const statusNode = document.getElementById('status');
        const previewNode = document.getElementById('preview');
        const diagnosticsNode = document.getElementById('diagnostics');
        const diagnosticListNode = document.getElementById('diagnostic-list');
        const initialState = ${initialData};

        function render(state) {
            vscode.setState(state);
            titleNode.textContent = state.rootStateName
                ? state.title + ' · ' + state.rootStateName
                : state.title;
            filePathNode.textContent = state.filePath || '<memory>';
            statusNode.textContent = state.statusText;
            statusNode.className = 'badge ' + (state.status === 'ok' ? '' : state.status);
            previewNode.innerHTML = state.svg;
            diagnosticListNode.innerHTML = '';

            if (state.diagnostics.length > 0) {
                diagnosticsNode.classList.remove('hidden');
                for (const diagnostic of state.diagnostics) {
                    const item = document.createElement('li');
                    item.className = 'diagnostic-item ' + (diagnostic.severity === 'error' ? 'error' : 'warning');

                    const meta = document.createElement('div');
                    meta.className = 'diagnostic-meta';
                    meta.textContent = diagnostic.severity.toUpperCase() + ' · ' + diagnostic.location;

                    const message = document.createElement('div');
                    message.className = 'diagnostic-message';
                    message.textContent = diagnostic.message;

                    item.appendChild(meta);
                    item.appendChild(message);
                    diagnosticListNode.appendChild(item);
                }
            } else {
                diagnosticsNode.classList.add('hidden');
            }
        }

        window.addEventListener('message', event => {
            render(event.data);
        });

        render(vscode.getState() || initialState);
    </script>
</body>
</html>`;
}

/**
 * Live right-side preview panel for FCSTM documents.
 */
export class FcstmPreviewController implements vscode.Disposable {
    private panel: vscode.WebviewPanel | null = null;
    private readonly disposables: vscode.Disposable[] = [];
    private currentDocumentUri: string | null = null;
    private updateTimer: NodeJS.Timeout | undefined;
    private updateSequence = 0;

    constructor(private readonly context: vscode.ExtensionContext) {
        const graph = getWorkspaceGraph();
        for (const document of vscode.workspace.textDocuments) {
            if (isFcstmDocument(document)) {
                graph.setOverlay(document.uri.fsPath, document.getText());
            }
        }

        this.disposables.push(
            vscode.commands.registerCommand('fcstm.preview.open', (resource?: vscode.Uri) => this.open(resource)),
            vscode.workspace.onDidOpenTextDocument(document => {
                this.syncOverlay(document);
            }),
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
            })
        );
    }

    dispose(): void {
        if (this.updateTimer) {
            clearTimeout(this.updateTimer);
            this.updateTimer = undefined;
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

    private async open(resource?: vscode.Uri): Promise<void> {
        const document = await this.resolveDocument(resource);
        if (!document || !isFcstmDocument(document)) {
            await vscode.window.showWarningMessage('Open an FCSTM document first.');
            return;
        }

        if (!this.panel) {
            this.panel = vscode.window.createWebviewPanel(
                'fcstmPreview',
                `FCSTM Preview: ${basenameForDocument(document)}`,
                {
                    preserveFocus: true,
                    viewColumn: vscode.ViewColumn.Beside,
                },
                {
                    enableFindWidget: true,
                    enableScripts: true,
                    retainContextWhenHidden: true,
                }
            );
            this.panel.onDidDispose(() => {
                this.panel = null;
                this.currentDocumentUri = null;
            }, null, this.disposables);

            const initialState: PreviewWebviewState = {
                title: basenameForDocument(document),
                filePath: document.uri.fsPath,
                svg: buildEmptyPreviewSvg('FCSTM Preview', 'Preparing preview...'),
                diagnostics: [],
                status: 'ok',
                statusText: 'Loading preview',
            };
            this.panel.webview.html = createPreviewHtml(this.panel.webview, initialState);
        } else {
            this.panel.reveal(vscode.ViewColumn.Beside, true);
        }

        this.scheduleRefresh(document, true);
    }

    private async resolveDocument(resource?: vscode.Uri): Promise<vscode.TextDocument | null> {
        if (resource && isFcstmUri(resource)) {
            const existingDocument = vscode.workspace.textDocuments.find(document => document.uri.toString() === resource.toString());
            if (existingDocument) {
                return existingDocument;
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
        const execute = () => {
            void this.refresh(document);
        };

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
            const [diagram, diagnostics] = await Promise.all([
                buildFcstmDiagramFromDocument(document),
                collectDocumentDiagnostics(document),
            ]);

            const diagnosticViews = diagnostics.map(buildDiagnosticView);
            const errorCount = diagnosticViews.filter(item => item.severity === 'error').length;
            const warningCount = diagnosticViews.length - errorCount;
            const status = errorCount > 0 ? 'error' : warningCount > 0 ? 'warning' : 'ok';
            const statusText = errorCount > 0
                ? `${errorCount} error${errorCount === 1 ? '' : 's'}`
                : warningCount > 0
                    ? `${warningCount} warning${warningCount === 1 ? '' : 's'}`
                    : 'Live preview';
            const title = basenameForDocument(document);

            state = {
                title,
                filePath: document.uri.fsPath || document.uri.toString(),
                rootStateName: diagram ? diagram.machineName : undefined,
                svg: diagram
                    ? await renderFcstmDiagramSvg(diagram)
                    : buildEmptyPreviewSvg(title, diagnostics.length > 0 ? diagnostics[0].message : 'No diagram available.'),
                diagnostics: diagnosticViews,
                status,
                statusText,
            };
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            const title = basenameForDocument(document);
            state = {
                title,
                filePath: document.uri.fsPath || document.uri.toString(),
                svg: buildEmptyPreviewSvg(title, message),
                diagnostics: [{
                    severity: 'error',
                    message,
                    location: 'preview',
                }],
                status: 'error',
                statusText: 'Preview failed',
            };
        }

        if (!this.panel || sequence !== this.updateSequence) {
            return;
        }

        this.panel.title = `FCSTM Preview: ${basenameForDocument(document)}`;
        void this.panel.webview.postMessage(state);
    }
}
