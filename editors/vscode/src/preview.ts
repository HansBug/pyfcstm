import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

import * as vscode from 'vscode';
import {
    buildFcstmDiagramWebviewPayload,
    collectDocumentDiagnostics,
    getWorkspaceGraph,
    resolveFcstmDiagramPreviewOptions,
    type FcstmDiagramPreviewOptions,
    type FcstmDiagramWebviewPayload,
    type ResolvedFcstmDiagramPreviewOptions,
} from '@pyfcstm/jsfcstm';

type PreviewLayoutMode = 'side' | 'alone';

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
    payload?: FcstmDiagramWebviewPayload;
    previewOptions: ResolvedFcstmDiagramPreviewOptions;
    collapsedStateIds: string[];
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
        // Fall through to development-time fallback
    }

    return fs.readFileSync(
        path.join(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'),
        'utf8'
    );
}

const elkBrowserBundle = loadElkBrowserBundle();

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

function createPreviewHtml(
    webview: vscode.Webview,
    elkRuntimeScript: string,
    initialState: PreviewWebviewState
): string {
    const nonce = createNonce();
    const initialData = toScriptLiteral(initialState);
    const elkRuntime = escapeInlineScript(elkRuntimeScript);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data: blob:; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'nonce-${nonce}' ${webview.cspSource} 'unsafe-eval';" />
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
        * { box-sizing: border-box; }
        html, body { margin: 0; padding: 0; height: 100%; }
        body {
            color: var(--fg);
            background:
                radial-gradient(circle at top left, rgba(97, 149, 213, 0.14), transparent 34%),
                linear-gradient(180deg, color-mix(in srgb, var(--bg) 88%, #e6f1fb 12%), var(--bg));
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
            display: flex;
            flex-direction: column;
            min-height: 100%;
        }
        .shell {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 12px;
            flex: 1;
            min-height: 0;
        }
        .hidden { display: none !important; }

        .toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--panel);
            padding: 8px 12px;
        }
        .toolbar-title { font-size: 14px; font-weight: 700; margin-right: auto; }
        .toolbar-sub {
            font-size: 11px; color: var(--muted); word-break: break-all; flex-basis: 100%;
        }
        .toolbar-group {
            display: inline-flex; align-items: center; gap: 4px;
            border: 1px solid var(--border); border-radius: 999px; padding: 2px;
            background: rgba(255, 255, 255, 0.05);
        }
        .btn {
            border: none; background: transparent; color: var(--fg);
            padding: 5px 10px; border-radius: 999px; font-size: 11px;
            cursor: pointer; font-family: inherit;
            display: inline-flex; align-items: center; gap: 5px;
        }
        .btn:hover { background: rgba(45, 106, 168, 0.16); color: var(--accent); }
        .btn[aria-pressed="true"] { background: rgba(45, 106, 168, 0.24); color: var(--accent); font-weight: 700; }
        .btn.solo { border: 1px solid var(--border); border-radius: 8px; }
        .badge {
            display: inline-flex; align-items: center; padding: 3px 9px;
            border-radius: 999px; font-size: 11px; font-weight: 700;
            background: rgba(45, 106, 168, 0.14); color: var(--accent);
        }
        .badge.warning { background: rgba(183, 121, 31, 0.16); color: var(--warning); }
        .badge.error { background: rgba(179, 58, 58, 0.16); color: var(--error); }

        .options {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
            padding: 8px 12px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px 12px;
            align-items: center;
        }
        .option-field { display: flex; flex-direction: column; gap: 3px; min-width: 96px; }
        .option-label {
            font-size: 10px; font-weight: 700;
            letter-spacing: 0.04em; color: var(--muted); text-transform: uppercase;
        }
        .option-select {
            border: 1px solid var(--border); border-radius: 8px;
            background: rgba(255, 255, 255, 0.08); color: var(--fg);
            padding: 5px 8px; font-size: 11px;
            font-family: inherit;
        }
        .option-toggle {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 5px 10px;
            border: 1px solid var(--border); border-radius: 8px;
            background: rgba(255, 255, 255, 0.06);
            font-size: 11px; cursor: pointer; user-select: none;
        }
        .option-toggle input { margin: 0; }

        .summary {
            display: flex; flex-wrap: wrap; gap: 6px;
        }
        .summary-badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 4px 10px; border-radius: 999px;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.06);
            font-size: 11px; color: var(--muted);
        }
        .summary-value { color: var(--fg); font-weight: 700; }

        .stage {
            position: relative;
            flex: 1;
            min-height: 280px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.04);
            overflow: hidden;
        }
        .viewport {
            position: absolute; inset: 0;
            overflow: hidden;
            cursor: grab;
        }
        .viewport.dragging { cursor: grabbing; }
        .viewport-inner {
            position: absolute; left: 0; top: 0;
            transform-origin: 0 0;
        }
        .viewport-inner svg {
            display: block;
            user-select: none;
        }
        /* chevron always toggles on plain click, so it keeps pointer cursor. */
        .viewport-inner [data-fcstm-kind="chevron"] {
            cursor: pointer;
        }
        /* Other elements adopt the viewport's grab/grabbing cursor by default;
           only when a modifier is held do they offer the code-tracking cursor
           used by the Ctrl/Cmd+click reveal-source action. */
        body.modifier-held .viewport-inner [data-fcstm-kind="state"][data-fcstm-range-start-line],
        body.modifier-held .viewport-inner [data-fcstm-kind="composite-state"][data-fcstm-range-start-line],
        body.modifier-held .viewport-inner [data-fcstm-kind="transition"][data-fcstm-range-start-line],
        body.modifier-held .viewport-inner [data-fcstm-kind="transition-label"][data-fcstm-range-start-line],
        body.modifier-held .viewport-inner [data-fcstm-kind="chevron"][data-fcstm-range-start-line] {
            cursor: pointer;
        }
        .viewport-inner [data-fcstm-kind="state"]:hover > rect,
        .viewport-inner [data-fcstm-kind="composite-state"]:hover > rect {
            stroke-width: 2.6px;
            filter: brightness(1.05);
        }
        body.modifier-held .viewport-inner [data-fcstm-kind]:hover,
        body.modifier-held .viewport-inner [data-fcstm-kind="transition"]:hover {
            filter: brightness(1.05);
        }

        .stage-hint {
            position: absolute; left: 12px; bottom: 10px;
            font-size: 10px; color: var(--muted);
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 3px 8px;
            pointer-events: none;
            opacity: 0.85;
        }
        .zoom-controls {
            position: absolute; bottom: 14px; right: 14px;
            display: flex; flex-direction: column; gap: 4px;
            background: rgba(255, 255, 255, 0.85);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 3px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12);
        }
        .zoom-controls .btn { color: #183b61; padding: 4px 8px; font-size: 12px; }
        .zoom-level {
            text-align: center; font-size: 10px; color: #3470a8;
            border-top: 1px solid var(--border); padding-top: 3px;
        }

        .stage-empty {
            position: absolute; inset: 18px;
            border: 1px dashed var(--border);
            border-radius: 14px;
            padding: 20px;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; gap: 8px;
        }
        .stage-empty-title { font-size: 16px; font-weight: 700; }
        .stage-empty-message {
            font-size: 12px; color: var(--muted);
            white-space: pre-wrap; word-break: break-word; max-width: 560px;
        }

        .side-panels {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px;
        }
        .card {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
            padding: 10px 12px;
        }
        .card-title { font-size: 12px; font-weight: 700; margin-bottom: 8px; }
        .card-list {
            list-style: none; margin: 0; padding: 0;
            display: flex; flex-direction: column; gap: 6px;
        }
        .card-item { font-size: 11px; line-height: 1.45; word-break: break-word; }
        .card-item.mono { font-family: inherit; }
        .event-item {
            display: grid; grid-template-columns: 10px 1fr; gap: 8px; align-items: start;
        }
        .event-swatch { width: 10px; height: 10px; border-radius: 999px; margin-top: 4px; }
        .event-meta { font-size: 10px; color: var(--muted); margin-top: 2px; }
        .effect-card {
            border: 1px solid var(--border);
            border-left-width: 4px;
            border-radius: 10px;
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.05);
        }
        .effect-heading { font-size: 11px; font-weight: 700; margin-bottom: 3px; }
        .effect-meta { font-size: 10px; color: var(--muted); margin-bottom: 6px; }
        .effect-code {
            margin: 0; white-space: pre-wrap; word-break: break-word;
            font-size: 11px; line-height: 1.5;
        }
        .diag-item { border-left: 3px solid var(--border); padding-left: 9px; }
        .diag-item.error { border-left-color: var(--error); }
        .diag-item.warning { border-left-color: var(--warning); }
        .diag-meta { font-size: 10px; color: var(--muted); margin-bottom: 2px; }
        .diag-msg { font-size: 11px; line-height: 1.45; }
    </style>
</head>
<body>
    <div class="shell">
        <div class="toolbar">
            <div class="toolbar-title" id="title"></div>
            <div class="toolbar-group" role="group" aria-label="View Mode">
                <button class="btn" id="mode-side" aria-pressed="true" title="Split view (code + diagram)">Split</button>
                <button class="btn" id="mode-alone" aria-pressed="false" title="Diagram only">Diagram</button>
            </div>
            <div class="toolbar-group">
                <button class="btn" id="btn-fit" title="Fit to view">Fit</button>
                <button class="btn" id="btn-actual" title="Actual size (100%)">1:1</button>
                <button class="btn" id="btn-export-svg" title="Export SVG">SVG</button>
                <button class="btn" id="btn-export-png" title="Export PNG">PNG</button>
            </div>
            <span class="badge" id="status"></span>
            <div class="toolbar-sub" id="file-path"></div>
        </div>

        <div class="options" id="options">
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
            <label class="option-toggle"><input type="checkbox" id="option-events" /><span>Events</span></label>
            <label class="option-toggle"><input type="checkbox" id="option-guards" /><span>Guards</span></label>
            <label class="option-toggle"><input type="checkbox" id="option-variables" /><span>Variables</span></label>
            <label class="option-toggle"><input type="checkbox" id="option-state-events" /><span>State Events</span></label>
            <label class="option-toggle"><input type="checkbox" id="option-state-actions" /><span>Actions</span></label>
        </div>

        <section class="summary" id="summary"></section>

        <div class="stage" id="stage">
            <div class="viewport" id="viewport" title="Drag to pan · wheel to zoom · click chevron to collapse · Ctrl/Cmd+click to reveal source">
                <div class="viewport-inner" id="viewport-inner"></div>
            </div>
            <div class="stage-empty hidden" id="stage-empty">
                <div class="stage-empty-title" id="stage-empty-title">FCSTM Preview</div>
                <div class="stage-empty-message" id="stage-empty-message"></div>
            </div>
            <div class="zoom-controls">
                <button class="btn" id="btn-zoom-in" title="Zoom in">+</button>
                <button class="btn" id="btn-zoom-out" title="Zoom out">-</button>
                <div class="zoom-level" id="zoom-level">100%</div>
            </div>
            <div class="stage-hint" id="stage-hint" aria-hidden="true">Drag to pan · Ctrl/Cmd+click to jump to source</div>
        </div>

        <section class="side-panels">
            <div class="card hidden" id="variables-card">
                <div class="card-title">Variables</div>
                <ul class="card-list" id="variables-list"></ul>
            </div>
            <div class="card hidden" id="shared-events-card">
                <div class="card-title">Shared Events</div>
                <ul class="card-list" id="shared-events-list"></ul>
            </div>
            <div class="card hidden" id="effects-card">
                <div class="card-title">Transition Effects</div>
                <div id="effects-list"></div>
            </div>
            <div class="card hidden" id="diagnostics-card">
                <div class="card-title">Diagnostics</div>
                <ul class="card-list" id="diagnostics-list"></ul>
            </div>
        </section>
    </div>

    <script nonce="${nonce}">
/* FCSTM embedded ELK runtime */
${elkRuntime}
    </script>
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const initialState = ${initialData};

        const $ = (id) => document.getElementById(id);
        const titleNode = $('title');
        const filePathNode = $('file-path');
        const statusNode = $('status');
        const summaryNode = $('summary');
        const stageNode = $('stage');
        const viewportNode = $('viewport');
        const viewportInnerNode = $('viewport-inner');
        const stageEmptyNode = $('stage-empty');
        const stageEmptyTitle = $('stage-empty-title');
        const stageEmptyMessage = $('stage-empty-message');
        const zoomLevelNode = $('zoom-level');
        const variablesCard = $('variables-card');
        const variablesList = $('variables-list');
        const sharedEventsCard = $('shared-events-card');
        const sharedEventsList = $('shared-events-list');
        const effectsCard = $('effects-card');
        const effectsList = $('effects-list');
        const diagnosticsCard = $('diagnostics-card');
        const diagnosticsList = $('diagnostics-list');

        const detailSelect = $('option-detail');
        const effectsSelect = $('option-effects');
        const sharedEventsSelect = $('option-shared-events');
        const eventsToggle = $('option-events');
        const guardsToggle = $('option-guards');
        const variablesToggle = $('option-variables');
        const stateEventsToggle = $('option-state-events');
        const stateActionsToggle = $('option-state-actions');

        const modeSideBtn = $('mode-side');
        const modeAloneBtn = $('mode-alone');
        const fitBtn = $('btn-fit');
        const actualBtn = $('btn-actual');
        const exportSvgBtn = $('btn-export-svg');
        const exportPngBtn = $('btn-export-png');
        const zoomInBtn = $('btn-zoom-in');
        const zoomOutBtn = $('btn-zoom-out');

        const elk = new ELK();
        let renderToken = 0;
        let currentState = null;
        let collapsedSet = new Set();
        let viewTransform = { tx: 0, ty: 0, scale: 1 };
        let currentSvgString = '';
        let currentSvgBounds = { width: 0, height: 0 };

        function setTransform(tx, ty, scale) {
            viewTransform.tx = tx;
            viewTransform.ty = ty;
            viewTransform.scale = Math.max(0.1, Math.min(8, scale));
            viewportInnerNode.style.transform =
                'translate(' + viewTransform.tx + 'px,' + viewTransform.ty + 'px) scale(' + viewTransform.scale + ')';
            zoomLevelNode.textContent = Math.round(viewTransform.scale * 100) + '%';
        }

        function fitToView() {
            if (!currentSvgBounds.width || !currentSvgBounds.height) return;
            const rect = viewportNode.getBoundingClientRect();
            const margin = 16;
            const availW = Math.max(40, rect.width - margin * 2);
            const availH = Math.max(40, rect.height - margin * 2);
            const scale = Math.min(availW / currentSvgBounds.width, availH / currentSvgBounds.height, 1);
            const tx = (rect.width - currentSvgBounds.width * scale) / 2;
            const ty = (rect.height - currentSvgBounds.height * scale) / 2;
            setTransform(tx, ty, scale);
        }

        function actualSize() {
            const rect = viewportNode.getBoundingClientRect();
            const tx = Math.max(0, (rect.width - currentSvgBounds.width) / 2);
            const ty = Math.max(0, (rect.height - currentSvgBounds.height) / 2);
            setTransform(tx, ty, 1);
        }

        viewportNode.addEventListener('wheel', (ev) => {
            if (!currentSvgString) return;
            ev.preventDefault();
            const delta = -ev.deltaY;
            const factor = Math.exp(delta * 0.0015);
            const next = viewTransform.scale * factor;
            const rect = viewportNode.getBoundingClientRect();
            const cx = ev.clientX - rect.left;
            const cy = ev.clientY - rect.top;
            const worldX = (cx - viewTransform.tx) / viewTransform.scale;
            const worldY = (cy - viewTransform.ty) / viewTransform.scale;
            const newScale = Math.max(0.1, Math.min(8, next));
            const newTx = cx - worldX * newScale;
            const newTy = cy - worldY * newScale;
            setTransform(newTx, newTy, newScale);
        }, { passive: false });

        // Interaction model (mirrors editors/vscode/src/preview-interaction.ts):
        //   - mousedown anywhere starts a drag; pan only takes effect if the
        //     pointer actually moves beyond PREVIEW_DRAG_THRESHOLD_PX.
        //   - plain click on a chevron toggles collapse.
        //   - Ctrl/Cmd + click on any element that carries a source range
        //     reveals that range in the editor (code-tracking style).
        //   - all other plain clicks are ignored so drag/zoom stay usable.
        const PREVIEW_DRAG_THRESHOLD_PX = 4;
        let dragState = null;
        let dragMovedPx = 0;

        function decidePreviewPointerAction(input) {
            if (input.dragMovedPx > PREVIEW_DRAG_THRESHOLD_PX) return { type: 'none' };
            if (!input.kind) return { type: 'none' };
            if (input.kind === 'chevron' && !input.modifier) return { type: 'toggleCollapse' };
            if (input.modifier && input.hasRange) return { type: 'revealSource' };
            return { type: 'none' };
        }

        viewportNode.addEventListener('mousedown', (ev) => {
            if (ev.button !== 0) return;
            dragState = { startX: ev.clientX, startY: ev.clientY, tx: viewTransform.tx, ty: viewTransform.ty };
            dragMovedPx = 0;
            viewportNode.classList.add('dragging');
        });
        window.addEventListener('mousemove', (ev) => {
            if (!dragState) return;
            const dx = ev.clientX - dragState.startX;
            const dy = ev.clientY - dragState.startY;
            dragMovedPx = Math.max(dragMovedPx, Math.hypot(dx, dy));
            setTransform(dragState.tx + dx, dragState.ty + dy, viewTransform.scale);
        });
        window.addEventListener('mouseup', () => {
            if (dragState) {
                dragState = null;
                viewportNode.classList.remove('dragging');
            }
        });

        viewportNode.addEventListener('click', (ev) => {
            const movedPx = dragMovedPx;
            dragMovedPx = 0;
            const target = ev.target && ev.target.closest && ev.target.closest('[data-fcstm-kind]');
            const kind = target ? target.getAttribute('data-fcstm-kind') : null;
            const range = target ? readRange(target) : null;
            const modifier = Boolean(ev.ctrlKey || ev.metaKey);
            const action = decidePreviewPointerAction({
                kind,
                modifier,
                dragMovedPx: movedPx,
                hasRange: Boolean(range),
            });
            if (action.type === 'toggleCollapse') {
                const id = target.getAttribute('data-fcstm-id');
                toggleCollapse(id);
                return;
            }
            if (action.type === 'revealSource' && range) {
                vscode.postMessage({ type: 'revealSource', range });
                return;
            }
        });

        // Highlight targetable elements with the code-tracking cursor only
        // while a modifier key is held, matching JetBrains-style Ctrl+click.
        function updateModifierState(ev) {
            const held = Boolean(ev.ctrlKey || ev.metaKey);
            document.body.classList.toggle('modifier-held', held);
        }
        window.addEventListener('keydown', updateModifierState);
        window.addEventListener('keyup', updateModifierState);
        window.addEventListener('blur', () => document.body.classList.remove('modifier-held'));

        function readRange(el) {
            const sl = el.getAttribute('data-fcstm-range-start-line');
            const sc = el.getAttribute('data-fcstm-range-start-character');
            const el_ = el.getAttribute('data-fcstm-range-end-line');
            const ec = el.getAttribute('data-fcstm-range-end-character');
            if (sl === null) return null;
            return {
                start: { line: +sl, character: +sc },
                end: { line: +el_, character: +ec },
            };
        }

        function toggleCollapse(id) {
            if (!id) return;
            if (collapsedSet.has(id)) {
                collapsedSet.delete(id);
            } else {
                collapsedSet.add(id);
            }
            vscode.postMessage({ type: 'setCollapsed', collapsed: Array.from(collapsedSet) });
        }

        function layoutOptions(graph) {
            return graph.layoutOptions || {};
        }

        async function layoutAndRender(state) {
            const token = ++renderToken;
            const payload = state.payload;
            if (!payload) {
                showEmpty(state.emptyTitle || 'FCSTM Preview', state.emptyMessage || 'No diagram available.');
                return;
            }
            try {
                const laid = await elk.layout(payload.graph);
                if (token !== renderToken) return;
                currentSvgString = renderSvgFromLaidOut(laid, state);
                currentSvgBounds = { width: Math.ceil(laid.width || 0) + 24, height: Math.ceil(laid.height || 0) + 24 };
                viewportInnerNode.innerHTML = currentSvgString;
                stageEmptyNode.classList.add('hidden');
                fitToView();
            } catch (err) {
                showEmpty('Layout failed', err && err.message ? err.message : String(err));
            }
        }

        function showEmpty(title, msg) {
            currentSvgString = '';
            currentSvgBounds = { width: 0, height: 0 };
            viewportInnerNode.innerHTML = '';
            stageEmptyTitle.textContent = title;
            stageEmptyMessage.textContent = msg;
            stageEmptyNode.classList.remove('hidden');
        }

        // Embedded renderer — mirrors svg-renderer.ts from jsfcstm but runs on
        // the already-laid-out ELK graph inside the webview.
        function renderSvgFromLaidOut(canvas, state) {
            const STYLE = {
                canvasPadding: 24,
                stateFill: '#ffffff',
                stateStroke: '#7da9d7',
                stateTitleColor: '#183b61',
                compositeFill: '#f4f8fc',
                compositeStroke: '#8cb3dc',
                pseudoStateFill: '#f3e6e6',
                pseudoStateStroke: '#b07575',
                initFill: '#2d6aa8',
                exitOuterStroke: '#2d6aa8',
                exitInnerFill: '#2d6aa8',
                edgeStroke: '#3470a8',
                edgeLabelBg: '#ffffff',
                edgeLabelBorder: '#c2d4e8',
                edgeLabelText: '#183b61',
                fontFamily: '"JetBrains Mono","Fira Code",Consolas,monospace',
                forcedEdgeDasharray: '6 4',
                entryEdgeWeight: 1.7,
                normalEdgeWeight: 1.4,
            };
            function esc(v) {
                return String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'})[c]);
            }
            function q(a, v) { return a + '="' + esc(v) + '"'; }
            function rangeAttrs(prefix, r) {
                if (!r) return '';
                return 'data-' + prefix + '-start-line="' + r.start.line + '" ' +
                       'data-' + prefix + '-start-character="' + r.start.character + '" ' +
                       'data-' + prefix + '-end-line="' + r.end.line + '" ' +
                       'data-' + prefix + '-end-character="' + r.end.character + '"';
            }
            const width = Math.ceil(canvas.width || 0) + STYLE.canvasPadding;
            const height = Math.ceil(canvas.height || 0) + STYLE.canvasPadding;
            const out = [];
            const direction = (state.previewOptions && state.previewOptions.direction) || 'TB';
            out.push('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + width + ' ' + height + '" ' +
                'width="' + width + '" height="' + height + '" ' + q('font-family', STYLE.fontFamily) +
                ' font-size="14" data-fcstm-canvas="true" data-fcstm-direction="' + direction + '">');
            out.push('<defs><marker id="fcstm-arrow" viewBox="0 0 10 10" refX="9" refY="5" ' +
                'markerWidth="10" markerHeight="10" orient="auto-start-reverse" markerUnits="userSpaceOnUse">' +
                '<path d="M0,0 L10,5 L0,10 z" fill="' + STYLE.edgeStroke + '"/></marker></defs>');
            out.push('<rect x="0" y="0" width="' + width + '" height="' + height + '" fill="transparent"/>');

            function drawEdge(edge, ox, oy) {
                const meta = edge.fcstm;
                const kind = (meta && meta.transitionKind) || 'normal';
                const forced = Boolean(meta && meta.forced);
                const color = (meta && meta.eventColor) || STYLE.edgeStroke;
                const weight = (kind === 'entry' || kind === 'exit') ? STYLE.entryEdgeWeight : STYLE.normalEdgeWeight;
                const dash = forced ? STYLE.forcedEdgeDasharray : '';
                for (const section of (edge.sections || [])) {
                    const pts = [
                        [section.startPoint.x + ox, section.startPoint.y + oy],
                        ...(section.bendPoints || []).map(p => [p.x + ox, p.y + oy]),
                        [section.endPoint.x + ox, section.endPoint.y + oy],
                    ];
                    const d = pts.map(([x, y], i) => (i === 0 ? 'M' : 'L') + x.toFixed(2) + ',' + y.toFixed(2)).join(' ');
                    out.push('<path ' + q('d', d) + ' fill="none" stroke="' + color + '" stroke-width="' + weight + '" ' +
                        (dash ? 'stroke-dasharray="' + dash + '" ' : '') +
                        'marker-end="url(#fcstm-arrow)" ' +
                        q('data-fcstm-kind', 'transition') + ' ' +
                        q('data-fcstm-id', (meta && meta.transitionId) || edge.id) + ' ' +
                        rangeAttrs('fcstm-range', meta && meta.sourceRange) + ' />');
                }
                for (const label of (edge.labels || [])) {
                    const lx = (label.x || 0) + ox;
                    const ly = (label.y || 0) + oy;
                    const lw = label.width || 0;
                    const lh = label.height || 0;
                    out.push('<g ' + q('data-fcstm-kind', 'transition-label') + ' ' +
                        q('data-fcstm-id', (meta && meta.transitionId) || edge.id) + ' ' +
                        rangeAttrs('fcstm-range', meta && meta.sourceRange) + '>');
                    out.push('<rect x="' + (lx - 4) + '" y="' + (ly - 2) + '" width="' + (lw + 8) + '" height="' + (lh + 4) +
                        '" rx="5" ry="5" fill="' + STYLE.edgeLabelBg + '" stroke="' + STYLE.edgeLabelBorder + '" stroke-width="0.8"/>');
                    const lines = String(label.text).split('\\n');
                    const lineOffset = lh / Math.max(1, lines.length);
                    for (let i = 0; i < lines.length; i++) {
                        out.push('<text x="' + (lx + 4) + '" y="' + (ly + lineOffset * (i + 0.7) + 2) + '" fill="' + color + '" font-size="12">' + esc(lines[i]) + '</text>');
                    }
                    out.push('</g>');
                }
            }

            function drawNode(node, ox, oy, depth) {
                const x = (node.x || 0) + ox;
                const y = (node.y || 0) + oy;
                const w = node.width || 0;
                const h = node.height || 0;
                const meta = node.fcstm;
                if (!meta || meta.kind === 'canvas') {
                    for (const c of (node.children || [])) drawNode(c, x, y, depth + 1);
                    for (const e of (node.edges || [])) drawEdge(e, x, y);
                    return;
                }
                if (meta.kind === 'pseudoInit') {
                    out.push('<circle cx="' + (x + w / 2) + '" cy="' + (y + h / 2) + '" r="' + (Math.min(w, h) / 2) +
                        '" fill="' + STYLE.initFill + '" ' + q('data-fcstm-kind', 'pseudo-init') + ' ' + q('data-fcstm-id', node.id) + '/>');
                    return;
                }
                if (meta.kind === 'pseudoExit') {
                    const r = Math.min(w, h) / 2;
                    const cx = x + w / 2;
                    const cy = y + h / 2;
                    out.push('<g ' + q('data-fcstm-kind', 'pseudo-exit') + ' ' + q('data-fcstm-id', node.id) + '>' +
                        '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="#ffffff" stroke="' + STYLE.exitOuterStroke + '" stroke-width="1.6"/>' +
                        '<circle cx="' + cx + '" cy="' + cy + '" r="' + Math.max(0, r - 4) + '" fill="' + STYLE.exitInnerFill + '"/></g>');
                    return;
                }
                const isComposite = Boolean(meta.composite);
                const isPseudo = Boolean(meta.pseudo);
                const fill = isPseudo ? STYLE.pseudoStateFill : (isComposite && !meta.collapsed ? STYLE.compositeFill : STYLE.stateFill);
                const stroke = isPseudo ? STYLE.pseudoStateStroke : (isComposite ? STYLE.compositeStroke : STYLE.stateStroke);
                const labelText = (node.labels && node.labels[0] && node.labels[0].text) || meta.qualifiedName || node.id;
                out.push('<g ' + q('data-fcstm-kind', isComposite ? 'composite-state' : 'state') + ' ' +
                    q('data-fcstm-id', meta.qualifiedName || node.id) + ' ' +
                    q('data-fcstm-pseudo', String(isPseudo)) + ' ' +
                    q('data-fcstm-composite', String(isComposite)) + ' ' +
                    q('data-fcstm-collapsed', String(Boolean(meta.collapsed))) + ' ' +
                    rangeAttrs('fcstm-range', meta.sourceRange) + '>');
                out.push('<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" ' +
                    'rx="' + (isComposite ? 16 : 10) + '" ry="' + (isComposite ? 16 : 10) + '" ' +
                    'fill="' + fill + '" stroke="' + stroke + '" stroke-width="1.6" ' +
                    (isPseudo ? 'stroke-dasharray="4 3" ' : '') + '/>');
                if (isComposite && !meta.collapsed) {
                    out.push('<text x="' + (x + 16) + '" y="' + (y + 22) + '" fill="' + STYLE.stateTitleColor +
                        '" font-weight="700" font-size="14">' + esc(labelText) + '</text>');
                    out.push('<line x1="' + (x + 8) + '" y1="' + (y + 30) + '" x2="' + (x + w - 8) + '" y2="' + (y + 30) +
                        '" stroke="' + STYLE.compositeStroke + '" stroke-opacity="0.55" stroke-width="1"/>');
                } else {
                    const detailLines = (meta.eventLabels || []).concat(meta.actionLabels || []);
                    if (detailLines.length === 0) {
                        out.push('<text x="' + (x + w / 2) + '" y="' + (y + h / 2 + 5) + '" fill="' + STYLE.stateTitleColor +
                            '" font-weight="600" text-anchor="middle">' + esc(labelText) + '</text>');
                    } else {
                        const titleY = y + 22;
                        out.push('<text x="' + (x + w / 2) + '" y="' + titleY + '" fill="' + STYLE.stateTitleColor +
                            '" font-weight="700" text-anchor="middle">' + esc(labelText) + '</text>');
                        out.push('<line x1="' + (x + 8) + '" y1="' + (titleY + 6) + '" x2="' + (x + w - 8) + '" y2="' + (titleY + 6) +
                            '" stroke="' + STYLE.stateStroke + '" stroke-opacity="0.4" stroke-width="1"/>');
                        let ly = titleY + 22;
                        for (const line of detailLines) {
                            out.push('<text x="' + (x + 12) + '" y="' + ly + '" fill="' + STYLE.stateTitleColor + '" font-size="12" font-weight="400">' + esc(line) + '</text>');
                            ly += 16;
                        }
                    }
                }
                if (isComposite) {
                    const cx = x + w - 22;
                    const cy = y + 14;
                    const collapsed = Boolean(meta.collapsed);
                    const d = collapsed ? 'M' + cx + ',' + cy + ' l4,4 l4,-4' : 'M' + cx + ',' + (cy + 2) + ' l4,-4 l4,4';
                    out.push('<path d="' + d + '" fill="none" stroke="' + STYLE.stateTitleColor + '" stroke-width="1.8" ' +
                        'stroke-linecap="round" stroke-linejoin="round" ' +
                        q('data-fcstm-kind', 'chevron') + ' ' + q('data-fcstm-id', meta.qualifiedName || node.id) + ' ' +
                        rangeAttrs('fcstm-range', meta.sourceRange) + '/>');
                }
                out.push('</g>');
                if (!meta.collapsed) {
                    for (const c of (node.children || [])) drawNode(c, x, y, depth + 1);
                    for (const e of (node.edges || [])) drawEdge(e, x, y);
                }
            }

            drawNode(canvas, 0, 0, 0);
            out.push('</svg>');
            return out.join('\\n');
        }

        function renderSummary(state) {
            summaryNode.innerHTML = '';
            if (!state.summary.length) { summaryNode.classList.add('hidden'); return; }
            summaryNode.classList.remove('hidden');
            for (const entry of state.summary) {
                const b = document.createElement('div'); b.className = 'summary-badge';
                const l = document.createElement('span'); l.textContent = entry.label;
                const v = document.createElement('span'); v.className = 'summary-value'; v.textContent = String(entry.value);
                b.appendChild(l); b.appendChild(v); summaryNode.appendChild(b);
            }
        }

        function renderVariables(state) {
            variablesList.innerHTML = '';
            if (!state.variables.length) { variablesCard.classList.add('hidden'); return; }
            variablesCard.classList.remove('hidden');
            for (const v of state.variables) {
                const li = document.createElement('li'); li.className = 'card-item mono'; li.textContent = v;
                variablesList.appendChild(li);
            }
        }

        function renderSharedEvents(state) {
            sharedEventsList.innerHTML = '';
            if (!state.sharedEvents.length) { sharedEventsCard.classList.add('hidden'); return; }
            sharedEventsCard.classList.remove('hidden');
            for (const e of state.sharedEvents) {
                const li = document.createElement('li'); li.className = 'card-item event-item';
                const s = document.createElement('span'); s.className = 'event-swatch'; s.style.backgroundColor = e.color;
                const body = document.createElement('div');
                const lbl = document.createElement('div'); lbl.textContent = e.label;
                const meta = document.createElement('div'); meta.className = 'event-meta';
                meta.textContent = e.transitionCount + ' transition' + (e.transitionCount === 1 ? '' : 's') + ' · ' + e.qualifiedName;
                body.appendChild(lbl); body.appendChild(meta);
                li.appendChild(s); li.appendChild(body);
                sharedEventsList.appendChild(li);
            }
        }

        function renderEffects(state) {
            effectsList.innerHTML = '';
            if (!state.effectNotes.length) { effectsCard.classList.add('hidden'); return; }
            effectsCard.classList.remove('hidden');
            for (const note of state.effectNotes) {
                const card = document.createElement('div'); card.className = 'effect-card';
                card.style.borderLeftColor = note.color || 'var(--border)';
                const h = document.createElement('div'); h.className = 'effect-heading'; h.textContent = note.title;
                card.appendChild(h);
                if (note.meta) {
                    const m = document.createElement('div'); m.className = 'effect-meta'; m.textContent = note.meta;
                    card.appendChild(m);
                }
                const pre = document.createElement('pre'); pre.className = 'effect-code'; pre.textContent = note.effectText;
                card.appendChild(pre);
                effectsList.appendChild(card);
            }
        }

        function renderDiagnostics(state) {
            diagnosticsList.innerHTML = '';
            if (!state.diagnostics.length) { diagnosticsCard.classList.add('hidden'); return; }
            diagnosticsCard.classList.remove('hidden');
            for (const d of state.diagnostics) {
                const li = document.createElement('li');
                li.className = 'card-item diag-item ' + (d.severity === 'error' ? 'error' : 'warning');
                const meta = document.createElement('div'); meta.className = 'diag-meta';
                meta.textContent = d.severity.toUpperCase() + ' · ' + d.location;
                const msg = document.createElement('div'); msg.className = 'diag-msg'; msg.textContent = d.message;
                li.appendChild(meta); li.appendChild(msg);
                diagnosticsList.appendChild(li);
            }
        }

        function renderOptions(state) {
            const o = state.previewOptions;
            detailSelect.value = o.detailLevel;
            effectsSelect.value = o.transitionEffectMode;
            sharedEventsSelect.value = o.eventVisualizationMode;
            eventsToggle.checked = o.showEvents;
            guardsToggle.checked = o.showTransitionGuards;
            variablesToggle.checked = o.showVariableDefinitions;
            stateEventsToggle.checked = o.showStateEvents;
            stateActionsToggle.checked = o.showStateActions;
        }

        async function applyState(state) {
            currentState = state;
            collapsedSet = new Set(state.collapsedStateIds || []);
            titleNode.textContent = state.rootStateName ? (state.title + ' · ' + state.rootStateName) : state.title;
            filePathNode.textContent = state.filePath || '';
            statusNode.textContent = state.statusText;
            statusNode.className = 'badge ' + (state.status === 'ok' ? '' : state.status);
            renderOptions(state);
            renderSummary(state);
            renderVariables(state);
            renderSharedEvents(state);
            renderEffects(state);
            renderDiagnostics(state);
            vscode.setState(state);
            if (state.payload) {
                await layoutAndRender(state);
            } else {
                showEmpty(state.emptyTitle || state.title, state.emptyMessage || 'No diagram available.');
            }
        }

        window.addEventListener('message', (ev) => { void applyState(ev.data); });

        function patch(options) { vscode.postMessage({ type: 'patchOptions', options }); }
        detailSelect.addEventListener('change', () => patch({ detailLevel: detailSelect.value }));
        effectsSelect.addEventListener('change', () => patch({ transitionEffectMode: effectsSelect.value }));
        sharedEventsSelect.addEventListener('change', () => patch({ eventVisualizationMode: sharedEventsSelect.value }));
        eventsToggle.addEventListener('change', () => patch({ showEvents: eventsToggle.checked }));
        guardsToggle.addEventListener('change', () => patch({ showTransitionGuards: guardsToggle.checked }));
        variablesToggle.addEventListener('change', () => patch({ showVariableDefinitions: variablesToggle.checked }));
        stateEventsToggle.addEventListener('change', () => patch({ showStateEvents: stateEventsToggle.checked }));
        stateActionsToggle.addEventListener('change', () => patch({ showStateActions: stateActionsToggle.checked }));

        modeSideBtn.addEventListener('click', () => vscode.postMessage({ type: 'setLayoutMode', mode: 'side' }));
        modeAloneBtn.addEventListener('click', () => vscode.postMessage({ type: 'setLayoutMode', mode: 'alone' }));
        fitBtn.addEventListener('click', fitToView);
        actualBtn.addEventListener('click', actualSize);
        zoomInBtn.addEventListener('click', () => {
            const rect = viewportNode.getBoundingClientRect();
            const cx = rect.width / 2, cy = rect.height / 2;
            const worldX = (cx - viewTransform.tx) / viewTransform.scale;
            const worldY = (cy - viewTransform.ty) / viewTransform.scale;
            const ns = viewTransform.scale * 1.2;
            setTransform(cx - worldX * ns, cy - worldY * ns, ns);
        });
        zoomOutBtn.addEventListener('click', () => {
            const rect = viewportNode.getBoundingClientRect();
            const cx = rect.width / 2, cy = rect.height / 2;
            const worldX = (cx - viewTransform.tx) / viewTransform.scale;
            const worldY = (cy - viewTransform.ty) / viewTransform.scale;
            const ns = viewTransform.scale / 1.2;
            setTransform(cx - worldX * ns, cy - worldY * ns, ns);
        });

        exportSvgBtn.addEventListener('click', () => {
            if (!currentSvgString) return;
            vscode.postMessage({ type: 'exportSvg', svg: currentSvgString });
        });
        exportPngBtn.addEventListener('click', async () => {
            if (!currentSvgString) return;
            try {
                const blob = new Blob([currentSvgString], { type: 'image/svg+xml;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const img = new Image();
                const w = currentSvgBounds.width, h = currentSvgBounds.height;
                await new Promise((resolve, reject) => {
                    img.onload = () => resolve();
                    img.onerror = (e) => reject(e);
                    img.src = url;
                });
                const scale = 2;
                const canvas = document.createElement('canvas');
                canvas.width = Math.max(1, Math.ceil(w * scale));
                canvas.height = Math.max(1, Math.ceil(h * scale));
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                URL.revokeObjectURL(url);
                const dataUrl = canvas.toDataURL('image/png');
                const b64 = dataUrl.slice(dataUrl.indexOf(',') + 1);
                vscode.postMessage({ type: 'exportPng', base64: b64 });
            } catch (err) {
                vscode.postMessage({ type: 'exportError', message: err && err.message ? err.message : String(err) });
            }
        });

        window.addEventListener('resize', () => {
            if (currentSvgString) fitToView();
        });

        void applyState(vscode.getState() || initialState);
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
    private previewOptions: FcstmDiagramPreviewOptions = {detailLevel: 'normal'};
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
            diagnostics: [],
            status: 'ok',
            statusText: 'Loading preview',
        };
        this.panel.webview.html = createPreviewHtml(this.panel.webview, elkBrowserBundle, initialState);
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
            const [payload, diagnostics] = await Promise.all([
                buildFcstmDiagramWebviewPayload(document, this.previewOptions, {
                    collapsedStateIds: this.collapsedStateIds,
                }),
                collectDocumentDiagnostics(document),
            ]);
            const diagnosticViews = diagnostics.map(buildDiagnosticView);
            const errorCount = diagnosticViews.filter(d => d.severity === 'error').length;
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
                rootStateName: payload ? payload.machineName : undefined,
                payload: payload || undefined,
                previewOptions,
                collapsedStateIds: Array.from(this.collapsedStateIds),
                emptyTitle: title,
                emptyMessage: diagnostics.length > 0 ? diagnostics[0].message : 'No diagram available.',
                summary: buildSummaryEntries(payload),
                variables: buildVariables(payload, previewOptions),
                sharedEvents: buildSharedEvents(payload, previewOptions),
                effectNotes: buildEffectNotes(payload),
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
                collapsedStateIds: Array.from(this.collapsedStateIds),
                emptyTitle: title,
                emptyMessage: message,
                summary: [],
                variables: [],
                sharedEvents: [],
                effectNotes: [],
                diagnostics: [{severity: 'error', message, location: 'preview'}],
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
