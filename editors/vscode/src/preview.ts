import * as crypto from 'crypto';
import * as path from 'path';

import * as vscode from 'vscode';
import {
    buildFcstmDiagramFromDocument,
    collectFcstmDiagramEffectNotes,
    collectDocumentDiagnostics,
    getWorkspaceGraph,
    renderFcstmDiagramMermaidView,
    resolveFcstmDiagramPreviewOptions,
    type FcstmDiagramPreviewOptions,
    type ResolvedFcstmDiagramPreviewOptions,
} from '@pyfcstm/jsfcstm';

interface PreviewDiagnosticView {
    severity: string;
    message: string;
    location: string;
}

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
    mermaidSource?: string;
    previewOptions: ResolvedFcstmDiagramPreviewOptions;
    transitionColors: Array<string | null>;
    emptyTitle: string;
    emptyMessage: string;
    summary: PreviewSummaryEntry[];
    variables: string[];
    sharedEvents: PreviewSharedEventView[];
    effectNotes: PreviewEffectNoteView[];
    diagnostics: PreviewDiagnosticView[];
    status: 'ok' | 'warning' | 'error';
    statusText: string;
}

function loadMermaidBrowserBundle(): string {
    try {
        const inlineModule = require('@fcstm/mermaid-inline');
        if (typeof inlineModule === 'string') {
            return inlineModule;
        }
        if (inlineModule && typeof inlineModule.default === 'string') {
            return inlineModule.default;
        }
    } catch {
        // Fall through to the development-time file fallback used by the
        // verification scripts that execute the tsc output directly.
    }

    const fs = require('fs') as typeof import('fs');
    return fs.readFileSync(
        path.join(__dirname, '..', 'node_modules', 'mermaid', 'dist', 'mermaid.min.js'),
        'utf8'
    );
}

const mermaidBrowserBundle = loadMermaidBrowserBundle();

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

function buildPreviewSummaryEntries(diagram: Awaited<ReturnType<typeof buildFcstmDiagramFromDocument>>): PreviewSummaryEntry[] {
    if (!diagram) {
        return [];
    }

    return [
        {label: 'vars', value: diagram.summary.variables},
        {label: 'states', value: diagram.summary.states},
        {label: 'events', value: diagram.summary.events},
        {label: 'transitions', value: diagram.summary.transitions},
        {label: 'actions', value: diagram.summary.actions},
    ];
}

function buildPreviewVariables(
    diagram: Awaited<ReturnType<typeof buildFcstmDiagramFromDocument>>,
    options: ResolvedFcstmDiagramPreviewOptions
): string[] {
    if (!diagram || !options.showVariableDefinitions) {
        return [];
    }

    return diagram.variables.map(variable => `def ${variable.valueType} ${variable.name} = ${variable.initializer}`);
}

function buildPreviewSharedEvents(
    diagram: Awaited<ReturnType<typeof buildFcstmDiagramFromDocument>>,
    options: ResolvedFcstmDiagramPreviewOptions
): PreviewSharedEventView[] {
    if (!diagram || (options.eventVisualizationMode !== 'legend' && options.eventVisualizationMode !== 'both')) {
        return [];
    }

    return diagram.eventLegend.map(item => ({
        label: item.label,
        qualifiedName: `/${item.qualifiedName.split('.').slice(1).join('.')}`,
        transitionCount: item.transitionCount,
        color: item.color,
    }));
}

function buildPreviewEffectNotes(
    diagram: Awaited<ReturnType<typeof buildFcstmDiagramFromDocument>>,
    options: ResolvedFcstmDiagramPreviewOptions
): PreviewEffectNoteView[] {
    if (!diagram) {
        return [];
    }

    return collectFcstmDiagramEffectNotes(diagram, options).map(note => ({
        title: note.title,
        meta: note.meta,
        effectText: note.effectText,
        color: note.eventColor,
    }));
}

function createPreviewHtml(
    webview: vscode.Webview,
    mermaidRuntimeScript: string,
    initialState: PreviewWebviewState
): string {
    const nonce = createNonce();
    const initialData = toScriptLiteral(initialState);
    const mermaidRuntime = escapeInlineScript(mermaidRuntimeScript);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data:; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'nonce-${nonce}' ${webview.cspSource};" />
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

        .hidden {
            display: none !important;
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

        .summary {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .summary-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.08);
            font-size: 12px;
            color: var(--muted);
        }

        .summary-value {
            color: var(--fg);
            font-weight: 700;
        }

        .options {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.05);
            padding: 12px 14px;
        }

        .options-title {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .options-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px 12px;
            align-items: end;
        }

        .option-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 108px;
        }

        .option-field.toggle {
            min-width: auto;
        }

        .option-label {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: var(--muted);
            text-transform: uppercase;
        }

        .option-select {
            border: 1px solid var(--border);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.08);
            color: var(--fg);
            padding: 7px 10px;
            font-size: 12px;
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
        }

        .option-toggle {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 7px 10px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.06);
            font-size: 12px;
            cursor: pointer;
            user-select: none;
        }

        .option-toggle input {
            margin: 0;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
        }

        .info-card {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.05);
            padding: 12px 14px;
        }

        .info-title {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .info-list {
            list-style: none;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .info-item {
            font-size: 12px;
            line-height: 1.45;
            color: var(--fg);
            word-break: break-word;
        }

        .info-item.mono {
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
        }

        .event-item {
            display: grid;
            grid-template-columns: 10px 1fr;
            gap: 10px;
            align-items: start;
        }

        .event-swatch {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            margin-top: 4px;
        }

        .event-meta {
            font-size: 11px;
            color: var(--muted);
            margin-top: 2px;
        }

        .preview {
            display: flex;
            justify-content: flex-start;
            align-items: flex-start;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.04);
            padding: 10px;
            overflow: auto;
        }

        .preview-inner {
            width: max-content;
            min-width: 100%;
            min-height: 260px;
        }

        .preview-inner svg {
            display: block;
            width: auto;
            height: auto;
            max-width: none;
        }

        .preview-empty {
            border: 1px dashed var(--border);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.05);
            padding: 22px;
        }

        .preview-empty-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .preview-empty-message {
            font-size: 13px;
            line-height: 1.55;
            color: var(--muted);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .preview-loading {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(45, 106, 168, 0.16);
            color: var(--accent);
            font-size: 12px;
            font-weight: 700;
        }

        .mermaid svg {
            display: block;
            margin: 0 auto;
        }

        .mermaid .edgeLabel rect {
            fill: rgba(255, 255, 255, 0.96) !important;
        }

        .mermaid .label foreignObject div,
        .mermaid .edgeLabel foreignObject div {
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace !important;
        }

        .mermaid .state-title {
            font-weight: 700;
        }

        .effects {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.03);
            padding: 12px 14px;
        }

        .effects.hidden {
            display: none;
        }

        .effects-title {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .effect-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .effect-card {
            border: 1px solid var(--border);
            border-left-width: 4px;
            border-radius: 12px;
            padding: 12px 14px;
            background: rgba(255, 255, 255, 0.05);
        }

        .effect-heading {
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .effect-meta {
            font-size: 11px;
            color: var(--muted);
            margin-bottom: 8px;
        }

        .effect-code {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-size: 12px;
            line-height: 1.5;
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
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
        <section class="options" id="options">
            <div class="options-title">Preview Options</div>
            <div class="options-grid">
                <label class="option-field">
                    <span class="option-label">Detail</span>
                    <select class="option-select" id="option-detail">
                        <option value="minimal">minimal</option>
                        <option value="normal">normal</option>
                        <option value="full">full</option>
                    </select>
                </label>
                <label class="option-field">
                    <span class="option-label">Effects</span>
                    <select class="option-select" id="option-effects">
                        <option value="note">note</option>
                        <option value="inline">inline</option>
                        <option value="hide">hide</option>
                    </select>
                </label>
                <label class="option-field">
                    <span class="option-label">Shared Events</span>
                    <select class="option-select" id="option-shared-events">
                        <option value="none">none</option>
                        <option value="color">color</option>
                        <option value="legend">legend</option>
                        <option value="both">both</option>
                    </select>
                </label>
                <label class="option-toggle">
                    <input type="checkbox" id="option-events" />
                    <span>Events</span>
                </label>
                <label class="option-toggle">
                    <input type="checkbox" id="option-guards" />
                    <span>Guards</span>
                </label>
                <label class="option-toggle">
                    <input type="checkbox" id="option-variables" />
                    <span>Variables</span>
                </label>
                <label class="option-toggle">
                    <input type="checkbox" id="option-state-events" />
                    <span>State Events</span>
                </label>
                <label class="option-toggle">
                    <input type="checkbox" id="option-state-actions" />
                    <span>Actions</span>
                </label>
            </div>
        </section>
        <section class="summary" id="summary"></section>
        <section class="info-grid">
            <section class="info-card" id="variables-card">
                <div class="info-title">Variables</div>
                <ul class="info-list" id="variables-list"></ul>
            </section>
            <section class="info-card" id="shared-events-card">
                <div class="info-title">Shared Events</div>
                <ul class="info-list" id="shared-events-list"></ul>
            </section>
        </section>
        <section class="preview">
            <div class="preview-inner" id="preview"></div>
        </section>
        <section class="effects hidden" id="effects">
            <div class="effects-title">Transition Effects</div>
            <div class="effect-list" id="effect-list"></div>
        </section>
        <section class="diagnostics hidden" id="diagnostics">
            <div class="diagnostics-title">Diagnostics</div>
            <ul class="diagnostic-list" id="diagnostic-list"></ul>
        </section>
    </div>
    <script nonce="${nonce}">
        /* FCSTM embedded Mermaid runtime */
${mermaidRuntime}
    </script>
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const titleNode = document.getElementById('title');
        const filePathNode = document.getElementById('file-path');
        const statusNode = document.getElementById('status');
        const detailSelectNode = document.getElementById('option-detail');
        const effectsSelectNode = document.getElementById('option-effects');
        const sharedEventsSelectNode = document.getElementById('option-shared-events');
        const eventsToggleNode = document.getElementById('option-events');
        const guardsToggleNode = document.getElementById('option-guards');
        const variablesToggleNode = document.getElementById('option-variables');
        const stateEventsToggleNode = document.getElementById('option-state-events');
        const stateActionsToggleNode = document.getElementById('option-state-actions');
        const summaryNode = document.getElementById('summary');
        const variablesCardNode = document.getElementById('variables-card');
        const variablesListNode = document.getElementById('variables-list');
        const sharedEventsCardNode = document.getElementById('shared-events-card');
        const sharedEventsListNode = document.getElementById('shared-events-list');
        const previewNode = document.getElementById('preview');
        const effectsNode = document.getElementById('effects');
        const effectListNode = document.getElementById('effect-list');
        const diagnosticsNode = document.getElementById('diagnostics');
        const diagnosticListNode = document.getElementById('diagnostic-list');
        const initialState = ${initialData};
        let renderToken = 0;
        const mermaidApi = globalThis.mermaid;

        if (mermaidApi) {
            mermaidApi.initialize({
                startOnLoad: false,
                securityLevel: 'strict',
                theme: 'base',
                state: {
                    useMaxWidth: false,
                    nodeSpacing: 18,
                    rankSpacing: 28,
                    padding: 8,
                    fontSize: 17,
                    compositTitleSize: 22,
                },
                themeVariables: {
                    primaryColor: '#f8fbff',
                    primaryTextColor: '#183b61',
                    primaryBorderColor: '#7da9d7',
                    lineColor: '#2d6aa8',
                    tertiaryColor: '#eef5ff',
                    clusterBkg: '#f8fbff',
                    clusterBorder: '#8cb3dc',
                    labelBoxBkgColor: '#ffffff',
                    labelBoxBorderColor: '#aec8e7',
                    fontFamily: '"JetBrains Mono","Fira Code",Consolas,monospace',
                    fontSize: '17px',
                },
                themeCSS: [
                    '.statediagram-cluster rect { rx: 18px; ry: 18px; }',
                    '.statediagram-state rect { rx: 14px; ry: 14px; }',
                    '.statediagram-note rect { rx: 14px; ry: 14px; }',
                    '.nodeLabel, .nodeLabel p, .edgeLabel, .edgeLabel p { font-size: 17px !important; }',
                    '.cluster-label .nodeLabel, .cluster-label .nodeLabel p { font-size: 18px !important; font-weight: 700 !important; }',
                    '.statediagram .edgeLabel .label { padding: 6px 10px; }',
                ].join('\\n'),
            });
        }

        function postProcessRenderedSvg(state) {
            const svg = previewNode.querySelector('svg');
            if (!svg) {
                return;
            }

            svg.style.maxWidth = 'none';
            svg.style.height = 'auto';

            for (const node of previewNode.querySelectorAll('.nodeLabel, .edgeLabel, .labelBkg')) {
                if (node instanceof HTMLElement) {
                    node.style.fontSize = node.classList.contains('edgeLabel') ? '15px' : '16px';
                    node.style.lineHeight = '1.45';
                }
            }

            for (const node of previewNode.querySelectorAll('.cluster-label .nodeLabel')) {
                if (node instanceof HTMLElement) {
                    node.style.fontSize = '17px';
                    node.style.fontWeight = '700';
                }
            }

            const colors = Array.isArray(state.transitionColors) ? state.transitionColors : [];
            if (colors.length === 0) {
                return;
            }

            const edgePaths = Array.from(svg.querySelectorAll('.edgePath path.path, .edgePaths .edgePath path.path'));
            const edgeLabels = Array.from(svg.querySelectorAll('.edgeLabel'));
            const edgeLabelTextNodes = Array.from(svg.querySelectorAll('.edgeLabel tspan'));
            const edgeLabelBackgrounds = Array.from(svg.querySelectorAll('.edgeLabel rect'));

            for (const [index, color] of colors.entries()) {
                if (!color) {
                    continue;
                }

                const edgePath = edgePaths[index];
                if (edgePath instanceof SVGElement) {
                    edgePath.style.stroke = color;
                    edgePath.style.strokeWidth = '2.6px';
                }

                const edgeLabel = edgeLabels[index];
                if (edgeLabel instanceof SVGElement) {
                    edgeLabel.style.color = color;
                }

                const edgeLabelText = edgeLabelTextNodes[index];
                if (edgeLabelText instanceof SVGElement) {
                    edgeLabelText.style.fill = color;
                }

                const edgeLabelBackground = edgeLabelBackgrounds[index];
                if (edgeLabelBackground instanceof SVGElement) {
                    edgeLabelBackground.style.stroke = color;
                    edgeLabelBackground.style.strokeWidth = '1.2px';
                }
            }
        }

        function sendOptionPatch(options) {
            vscode.postMessage({
                type: 'patchOptions',
                options,
            });
        }

        function renderPreviewOptions(state) {
            const options = state.previewOptions;
            detailSelectNode.value = options.detailLevel;
            effectsSelectNode.value = options.transitionEffectMode;
            sharedEventsSelectNode.value = options.eventVisualizationMode;
            eventsToggleNode.checked = options.showEvents;
            guardsToggleNode.checked = options.showTransitionGuards;
            variablesToggleNode.checked = options.showVariableDefinitions;
            stateEventsToggleNode.checked = options.showStateEvents;
            stateActionsToggleNode.checked = options.showStateActions;
        }

        function renderEffectNotes(state) {
            effectListNode.innerHTML = '';
            if (!state.effectNotes.length) {
                effectsNode.classList.add('hidden');
                return;
            }

            effectsNode.classList.remove('hidden');
            for (const note of state.effectNotes) {
                const card = document.createElement('section');
                card.className = 'effect-card';
                card.style.borderLeftColor = note.color || 'var(--border)';

                const heading = document.createElement('div');
                heading.className = 'effect-heading';
                heading.textContent = note.title;
                card.appendChild(heading);

                if (note.meta) {
                    const meta = document.createElement('div');
                    meta.className = 'effect-meta';
                    meta.textContent = note.meta;
                    card.appendChild(meta);
                }

                const code = document.createElement('pre');
                code.className = 'effect-code';
                code.textContent = note.effectText;
                card.appendChild(code);
                effectListNode.appendChild(card);
            }
        }

        function renderSummary(state) {
            summaryNode.innerHTML = '';
            if (!state.summary.length) {
                summaryNode.classList.add('hidden');
                return;
            }

            summaryNode.classList.remove('hidden');
            for (const entry of state.summary) {
                const badge = document.createElement('div');
                badge.className = 'summary-badge';

                const label = document.createElement('span');
                label.textContent = entry.label;

                const value = document.createElement('span');
                value.className = 'summary-value';
                value.textContent = String(entry.value);

                badge.appendChild(label);
                badge.appendChild(value);
                summaryNode.appendChild(badge);
            }
        }

        function renderVariables(state) {
            variablesListNode.innerHTML = '';
            if (!state.variables.length) {
                variablesCardNode.classList.add('hidden');
                return;
            }

            variablesCardNode.classList.remove('hidden');
            for (const variable of state.variables) {
                const item = document.createElement('li');
                item.className = 'info-item mono';
                item.textContent = variable;
                variablesListNode.appendChild(item);
            }
        }

        function renderSharedEvents(state) {
            sharedEventsListNode.innerHTML = '';
            if (!state.sharedEvents.length) {
                sharedEventsCardNode.classList.add('hidden');
                return;
            }

            sharedEventsCardNode.classList.remove('hidden');
            for (const event of state.sharedEvents) {
                const item = document.createElement('li');
                item.className = 'info-item event-item';

                const swatch = document.createElement('span');
                swatch.className = 'event-swatch';
                swatch.style.backgroundColor = event.color;

                const body = document.createElement('div');
                const label = document.createElement('div');
                label.textContent = event.label;
                const meta = document.createElement('div');
                meta.className = 'event-meta';
                meta.textContent = event.transitionCount + ' transition' + (event.transitionCount === 1 ? '' : 's') + ' · ' + event.qualifiedName;

                body.appendChild(label);
                body.appendChild(meta);
                item.appendChild(swatch);
                item.appendChild(body);
                sharedEventsListNode.appendChild(item);
            }
        }

        function renderEmptyState(title, message) {
            previewNode.innerHTML = '';

            const emptyNode = document.createElement('div');
            emptyNode.className = 'preview-empty';

            const titleNode = document.createElement('div');
            titleNode.className = 'preview-empty-title';
            titleNode.textContent = title;

            const messageNode = document.createElement('div');
            messageNode.className = 'preview-empty-message';
            messageNode.textContent = message;

            emptyNode.appendChild(titleNode);
            emptyNode.appendChild(messageNode);
            previewNode.appendChild(emptyNode);
        }

        async function renderMermaidSource(source, state) {
            const currentToken = ++renderToken;
            previewNode.innerHTML = '';

            if (!mermaidApi) {
                renderEmptyState('Mermaid Unavailable', 'The Mermaid runtime script did not load inside the preview webview.');
                return;
            }

            const loadingNode = document.createElement('div');
            loadingNode.className = 'preview-loading';
            loadingNode.textContent = 'Rendering Mermaid preview...';
            previewNode.appendChild(loadingNode);

            try {
                const renderId = 'fcstm-mermaid-' + currentToken;
                const renderResult = await mermaidApi.render(renderId, source);
                if (currentToken !== renderToken) {
                    return;
                }

                previewNode.innerHTML = renderResult.svg;
                if (typeof renderResult.bindFunctions === 'function') {
                    renderResult.bindFunctions(previewNode);
                }
                postProcessRenderedSvg(state);
            } catch (error) {
                if (currentToken !== renderToken) {
                    return;
                }

                const message = error instanceof Error ? error.message : String(error);
                renderEmptyState('Mermaid Render Failed', message);
            }
        }

        async function render(state) {
            vscode.setState(state);
            titleNode.textContent = state.rootStateName
                ? state.title + ' · ' + state.rootStateName
                : state.title;
            filePathNode.textContent = state.filePath || '<memory>';
            statusNode.textContent = state.statusText;
            statusNode.className = 'badge ' + (state.status === 'ok' ? '' : state.status);
            renderPreviewOptions(state);
            renderSummary(state);
            renderVariables(state);
            renderSharedEvents(state);
            renderEffectNotes(state);
            diagnosticListNode.innerHTML = '';

            if (state.mermaidSource) {
                await renderMermaidSource(state.mermaidSource, state);
            } else {
                renderEmptyState(state.emptyTitle, state.emptyMessage);
            }

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
            void render(event.data);
        });

        detailSelectNode.addEventListener('change', () => {
            vscode.postMessage({
                type: 'setDetailLevel',
                detailLevel: detailSelectNode.value,
            });
        });
        effectsSelectNode.addEventListener('change', () => {
            sendOptionPatch({
                transitionEffectMode: effectsSelectNode.value,
            });
        });
        sharedEventsSelectNode.addEventListener('change', () => {
            sendOptionPatch({
                eventVisualizationMode: sharedEventsSelectNode.value,
            });
        });
        eventsToggleNode.addEventListener('change', () => {
            sendOptionPatch({
                showEvents: eventsToggleNode.checked,
            });
        });
        guardsToggleNode.addEventListener('change', () => {
            sendOptionPatch({
                showTransitionGuards: guardsToggleNode.checked,
            });
        });
        variablesToggleNode.addEventListener('change', () => {
            sendOptionPatch({
                showVariableDefinitions: variablesToggleNode.checked,
            });
        });
        stateEventsToggleNode.addEventListener('change', () => {
            sendOptionPatch({
                showStateEvents: stateEventsToggleNode.checked,
            });
        });
        stateActionsToggleNode.addEventListener('change', () => {
            sendOptionPatch({
                showStateActions: stateActionsToggleNode.checked,
            });
        });

        void render(vscode.getState() || initialState);
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
    private previewOptions: FcstmDiagramPreviewOptions = {detailLevel: 'normal'};

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

    private async handleWebviewMessage(message: unknown): Promise<void> {
        if (!message || typeof message !== 'object' || !this.panel) {
            return;
        }

        const payload = message as {
            type?: string;
            detailLevel?: string;
            options?: Partial<FcstmDiagramPreviewOptions>;
        };

        if (payload.type === 'setDetailLevel' && typeof payload.detailLevel === 'string') {
            this.previewOptions = {detailLevel: payload.detailLevel as FcstmDiagramPreviewOptions['detailLevel']};
            await this.refreshCurrentDocument();
            return;
        }

        if (payload.type === 'patchOptions' && payload.options && typeof payload.options === 'object') {
            this.previewOptions = {
                ...this.previewOptions,
                ...payload.options,
            };
            await this.refreshCurrentDocument();
        }
    }

    private async refreshCurrentDocument(): Promise<void> {
        if (!this.panel || !this.currentDocumentUri) {
            return;
        }

        const document = vscode.workspace.textDocuments.find(item => item.uri.toString() === this.currentDocumentUri)
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
                    localResourceRoots: [this.context.extensionUri],
                    retainContextWhenHidden: true,
                }
            );
            this.panel.onDidDispose(() => {
                this.panel = null;
                this.currentDocumentUri = null;
            }, null, this.disposables);
            this.panel.webview.onDidReceiveMessage(message => {
                void this.handleWebviewMessage(message);
            }, null, this.disposables);

            const initialOptions = resolveFcstmDiagramPreviewOptions(this.previewOptions);
            const initialState: PreviewWebviewState = {
                title: basenameForDocument(document),
                filePath: document.uri.fsPath,
                previewOptions: initialOptions,
                transitionColors: [],
                emptyTitle: 'FCSTM Preview',
                emptyMessage: 'Preparing Mermaid preview...',
                summary: [],
                variables: [],
                sharedEvents: [],
                effectNotes: [],
                diagnostics: [],
                status: 'ok',
                statusText: 'Loading preview',
            };
            this.panel.webview.html = createPreviewHtml(
                this.panel.webview,
                mermaidBrowserBundle,
                initialState
            );
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
            const previewOptions = resolveFcstmDiagramPreviewOptions(this.previewOptions);
            const [diagram, diagnostics] = await Promise.all([
                buildFcstmDiagramFromDocument(document),
                collectDocumentDiagnostics(document),
            ]);
            const renderResult = diagram
                ? await renderFcstmDiagramMermaidView(diagram, previewOptions)
                : null;

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
                mermaidSource: renderResult ? renderResult.source : undefined,
                previewOptions,
                transitionColors: renderResult
                    ? renderResult.renderedTransitions.map(item => item.eventColor || null)
                    : [],
                emptyTitle: title,
                emptyMessage: diagnostics.length > 0 ? diagnostics[0].message : 'No diagram available.',
                summary: buildPreviewSummaryEntries(diagram),
                variables: buildPreviewVariables(diagram, previewOptions),
                sharedEvents: buildPreviewSharedEvents(diagram, previewOptions),
                effectNotes: buildPreviewEffectNotes(diagram, previewOptions),
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
                previewOptions: resolveFcstmDiagramPreviewOptions(this.previewOptions),
                transitionColors: [],
                emptyTitle: title,
                emptyMessage: message,
                summary: [],
                variables: [],
                sharedEvents: [],
                effectNotes: [],
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
