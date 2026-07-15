import * as fs from 'node:fs';
import * as crypto from 'node:crypto';
import * as http from 'node:http';
import {createRequire} from 'node:module';
import * as os from 'node:os';
import * as path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

import ELK from 'elkjs/lib/elk.bundled.js';

import {
    buildFcstmDiagramWebviewPayload,
    collectElkLayoutGeometry,
    MIN_TERMINAL_SEGMENT,
    MIN_SELF_LOOP_SEGMENT,
    resolveFcstmDiagramPreviewOptions,
    terminalApproach,
} from '../../jsfcstm/dist/diagram';
import {smoothGraphEdges} from '../src/preview-webview/render/edge-smoother';
import {buildCrossingIndex, collectSegments} from '../src/preview-webview/render/crossings';
import {renderSvg} from '../src/preview-webview/render/svg';
import {computePreviewFit, PREVIEW_FIT_MARGIN_PX} from '../src/preview-webview/layout';
import type {PreviewResolvedOptions, PreviewWebviewState} from '../src/preview-webview/types';

interface Point { x: number; y: number }

interface GeometryMetrics {
    sections: number;
    malformed: number;
    short: number;
    minTerminal: number | null;
    selfLoops: number;
    malformedSelfLoops: number;
    shortSelfLoops: number;
    minSelfLoopSegment: number | null;
}

interface FixtureReport {
    fixture: string;
    direction: 'TB' | 'LR';
    baseline: GeometryMetrics;
    fixed: GeometryMetrics;
    svg: {baseline: string; fixed: string};
    screenshots: Record<string, {
        baseline: ScreenshotMetrics | null;
        fixed: ScreenshotMetrics | null;
    }>;
    layout: {
        baseline: {width: number; height: number; crossings: number};
        fixed: {width: number; height: number; crossings: number};
        areaDeltaPercent: number;
    };
}

interface ScreenshotMetrics {
    shellViewportWidth: number;
    shellViewportHeight: number;
    rightPaneWidth: number;
    rightPaneHeight: number;
    stageViewportWidth: number;
    stageViewportHeight: number;
    svgWidth: number;
    svgHeight: number;
    tx: number;
    ty: number;
    scale: number;
    pngWidth: number;
    pngHeight: number;
    png: string;
    svgChildren: number;
    resize: ResizeExerciseMetrics | null;
}

interface ResizeExerciseMetrics {
    drag: {
        beforeStageHeight: number;
        draggedStageHeight: number;
        restoredStageHeight: number;
        beforeDrawerHeight: number;
        draggedDrawerHeight: number;
        restoredDrawerHeight: number;
        runtime: {
            before: RuntimeEvidence;
            dragged: RuntimeEvidence;
            restored: RuntimeEvidence;
        };
    };
    toggle: {
        beforeStageHeight: number;
        collapsedStageHeight: number;
        restoredStageHeight: number;
        beforeDrawerHeight: number;
        collapsedDrawerHeight: number;
        restoredDrawerHeight: number;
        runtime: {
            before: RuntimeEvidence;
            collapsed: RuntimeEvidence;
            restored: RuntimeEvidence;
        };
    };
}

interface RuntimeEvidence {
    pane: {left: number; top: number; width: number; height: number};
    stage: {left: number; top: number; width: number; height: number};
    drawer: {top: number; height: number; bottom: number};
    inner: {left: number; top: number; right: number; bottom: number};
    svg: {width: number; height: number; children: number};
    fitTransform: string;
    shellScroll: {width: number; height: number};
    paneScroll: {width: number; height: number};
}

interface RightPaneViewport {
    id: string;
    /** Full VSCode window CSS width used by the host-shell capture. */
    windowWidth: number;
    /** Full VSCode window CSS height used by the host-shell capture. */
    windowHeight: number;
    /** Width of the editor group occupied by the preview webview. */
    paneWidth: number;
    /** Approximate VSCode title/menu strip above the workbench. */
    topbarHeight: number;
    /** Approximate VSCode status bar below the workbench. */
    statusbarHeight: number;
}

interface PaneRect {
    left: number;
    top: number;
    width: number;
    height: number;
}

function rightPaneRect(viewport: RightPaneViewport): PaneRect {
    return {
        left: viewport.windowWidth - viewport.paneWidth,
        top: viewport.topbarHeight,
        width: viewport.paneWidth,
        height: viewport.windowHeight - viewport.topbarHeight - viewport.statusbarHeight,
    };
}

// These are full VSCode-workbench dimensions.  The preview is mounted in a
// right editor group that occupies exactly half of the window width; the
// left half is rendered as an editor placeholder by the evidence shell.  A
// bare Chrome viewport would miss the half-width constraint that triggers the
// real OptionsBar wrapping and Stage flex sizing behavior.
const RIGHT_PANE_VIEWPORTS: RightPaneViewport[] = [
    {id: 'compact-half', windowWidth: 1024, windowHeight: 768, paneWidth: 512, topbarHeight: 40, statusbarHeight: 22},
    {id: 'laptop-half', windowWidth: 1280, windowHeight: 800, paneWidth: 640, topbarHeight: 40, statusbarHeight: 22},
    {id: 'desktop-half', windowWidth: 1440, windowHeight: 900, paneWidth: 720, topbarHeight: 40, statusbarHeight: 22},
    {id: 'wide-half', windowWidth: 1920, windowHeight: 1080, paneWidth: 960, topbarHeight: 40, statusbarHeight: 22},
];

for (const viewport of RIGHT_PANE_VIEWPORTS) {
    const pane = rightPaneRect(viewport);
    if (viewport.paneWidth * 2 !== viewport.windowWidth || pane.height <= 0) {
        throw new Error(`invalid VSCode right-pane scenario: ${JSON.stringify(viewport)}`);
    }
}

class InMemoryDocument {
    readonly filePath: string;
    readonly uri: {fsPath: string; toString(): string};
    private readonly text: string;
    private readonly lines: string[];

    constructor(filePath: string) {
        this.filePath = filePath;
        this.text = fs.readFileSync(filePath, 'utf8');
        this.lines = this.text.split('\n');
        this.uri = {fsPath: filePath, toString: () => filePath};
    }

    get lineCount(): number { return this.lines.length; }
    getText(): string { return this.text; }
    lineAt(line: number): {text: string} { return {text: this.lines[line] || ''}; }
}

function clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

function removeNestedSpacing(node: any, isCanvas = true): void {
    if (!isCanvas && node.layoutOptions) {
        delete node.layoutOptions['elk.layered.spacing.nodeNodeBetweenLayers'];
        delete node.layoutOptions['elk.layered.spacing.edgeNodeBetweenLayers'];
        delete node.layoutOptions['elk.layered.spacing.edgeEdgeBetweenLayers'];
        delete node.layoutOptions['elk.spacing.nodeSelfLoop'];
    }
    for (const child of node.children || []) removeNestedSpacing(child, false);
}

function measure(graph: any): GeometryMetrics {
    const {boxes, edgeOffsets} = collectElkLayoutGeometry(graph);
    const result: GeometryMetrics = {
        sections: 0,
        malformed: 0,
        short: 0,
        minTerminal: null,
        selfLoops: 0,
        malformedSelfLoops: 0,
        shortSelfLoops: 0,
        minSelfLoopSegment: null,
    };

    function visit(node: any): void {
        for (const edge of node.edges || []) {
            const sourceId = edge.sources?.[0];
            const targetId = edge.targets?.[0];
            if (!sourceId || !targetId) {
                result.malformed += 1;
                continue;
            }
            const box = boxes.get(targetId);
            const offset = edgeOffsets.get(edge.id);
            if (!offset) {
                throw new Error(`edge ${edge.id}: owner offset missing during geometry collection`);
            }
            if (!edge.sections || edge.sections.length === 0) {
                result.malformed += 1;
                continue;
            }
            for (const section of edge.sections) {
                result.sections += 1;
                const points: Point[] = [
                    section.startPoint,
                    ...(section.bendPoints || []),
                    section.endPoint,
                ].map(point => ({x: point.x + offset.x, y: point.y + offset.y}));
                if (sourceId === targetId) {
                    result.selfLoops += 1;
                    if (points.length < 4) {
                        result.malformedSelfLoops += 1;
                        continue;
                    }
                    const lengths = points.slice(1).map((point, index) => Math.hypot(
                        point.x - points[index].x,
                        point.y - points[index].y,
                    ));
                    const loopMinimum = Math.min(...lengths);
                    result.minSelfLoopSegment = result.minSelfLoopSegment === null
                        ? loopMinimum
                        : Math.min(result.minSelfLoopSegment, loopMinimum);
                    if (loopMinimum < MIN_SELF_LOOP_SEGMENT) result.shortSelfLoops += 1;
                    continue;
                }
                const approach = box && points.length >= 2
                    ? terminalApproach(points[points.length - 2], points[points.length - 1], box)
                    : null;
                if (!approach) {
                    result.malformed += 1;
                } else {
                    result.minTerminal = result.minTerminal === null
                        ? approach.length
                        : Math.min(result.minTerminal, approach.length);
                    if (approach.length < MIN_TERMINAL_SEGMENT) result.short += 1;
                }
            }
        }
        for (const child of node.children || []) visit(child);
    }

    visit(graph);
    return result;
}

function toPreviewOptions(options: ReturnType<typeof resolveFcstmDiagramPreviewOptions>): PreviewResolvedOptions {
    return {
        detailLevel: options.detailLevel,
        direction: options.direction,
        showVariableDefinitions: options.showVariableDefinitions,
        showEvents: options.showEvents,
        showTransitionGuards: options.showTransitionGuards,
        showTransitionEffects: options.showTransitionEffects,
        transitionEffectMode: options.transitionEffectMode,
        eventVisualizationMode: options.eventVisualizationMode,
        showStateEvents: options.showStateEvents,
        showStateActions: options.showStateActions,
        eventNameFormat: [...options.eventNameFormat],
        maxStateEvents: options.maxStateEvents,
        maxStateActions: options.maxStateActions,
        maxTransitionEffectLines: options.maxTransitionEffectLines,
        maxLabelLength: options.maxLabelLength,
    };
}

function countCrossings(graph: any): number {
    let total = 0;
    const segments = collectSegments(graph);
    for (const points of buildCrossingIndex(segments).values()) total += points.length;
    return total;
}

function locateChrome(): string | null {
    for (const candidate of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
        const found = spawnSync('which', [candidate], {encoding: 'utf8'});
        if (found.status === 0 && found.stdout.trim()) return found.stdout.trim();
    }
    return null;
}

function readPngDimensions(pngPath: string): {width: number; height: number} {
    const data = fs.readFileSync(pngPath);
    const validSignature = data.length >= 24 &&
        data.readUInt32BE(0) === 0x89504e47 &&
        data.readUInt32BE(4) === 0x0d0a1a0a;
    if (!validSignature) {
        throw new Error(`invalid PNG signature: ${pngPath}`);
    }
    return {width: data.readUInt32BE(16), height: data.readUInt32BE(20)};
}

function sha256File(filePath: string): string {
    return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function scriptLiteral(value: unknown): string {
    return JSON.stringify(value)
        .replace(/</g, '\\u003c')
        .replace(/>/g, '\\u003e')
        .replace(/&/g, '\\u0026');
}

function previewState(
    payload: any,
    graph: any,
    fixtureName: string,
): PreviewWebviewState {
    const options = toPreviewOptions(payload.options);
    return {
        title: fixtureName,
        filePath: payload.filePath,
        rootStateName: payload.machineName,
        payload: {...payload, graph, options},
        previewOptions: options,
        collapsedStateIds: [],
        emptyTitle: fixtureName,
        emptyMessage: 'No diagram',
        summary: [
            {label: 'vars', value: payload.summary.variables},
            {label: 'states', value: payload.summary.states},
            {label: 'events', value: payload.summary.events},
            {label: 'transitions', value: payload.summary.transitions},
            {label: 'actions', value: payload.summary.actions},
        ],
        variables: options.showVariableDefinitions
            ? payload.variables.map((item: any) => `def ${item.valueType} ${item.name} = ${item.initializer}`)
            : [],
        sharedEvents: (options.eventVisualizationMode === 'legend' || options.eventVisualizationMode === 'both')
            ? payload.eventLegend.map((item: any) => ({
                label: item.label,
                qualifiedName: '/' + item.qualifiedName.split('.').slice(1).join('.'),
                transitionCount: item.transitionCount,
                color: item.color,
            }))
            : [],
    };
}

function previewWebviewHtml(state: PreviewWebviewState, viewport: RightPaneViewport): string {
    const vscodeStub = '<script>window.acquireVsCodeApi = () => ({ postMessage:()=>{}, getState:()=>null, setState:()=>{} });</script>';
    const initialState = `<script>window.__FCSTM_INITIAL_STATE__ = ${scriptLiteral(state)};</script>`;
    // ``run-preview-geometry.js`` bundles this file into a temporary CJS
    // artifact, so ``__dirname`` there is not the repository's vscode
    // directory.  The npm script deliberately runs from that directory;
    // allow an explicit override for callers that invoke the harness via CI.
    const vscodeDir = path.resolve(process.env.PYFCSTM_VSCODE_DIR || process.cwd());
    const webviewCss = fs.readFileSync(path.join(vscodeDir, 'dist', 'preview-webview.css'), 'utf8');
    const webviewJs = fs.readFileSync(path.join(vscodeDir, 'dist', 'preview-webview.js'), 'utf8');
    const elkJs = fs.readFileSync(path.join(vscodeDir, 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'), 'utf8');
    const pane = rightPaneRect(viewport);
    const shellCss = `<style>
html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
body { background: #1e1e1e; color: #cccccc; }
#vscode-window { display: grid; grid-template-rows: ${viewport.topbarHeight}px minmax(0, 1fr) ${viewport.statusbarHeight}px; width: 100%; height: 100%; }
#vscode-titlebar { display: flex; align-items: center; padding: 0 14px; box-sizing: border-box; background: #181818; color: #b8b8b8; font: 12px system-ui, sans-serif; }
#vscode-workbench { display: grid; grid-template-columns: minmax(0, 1fr) ${pane.width}px; min-width: 0; min-height: 0; }
#vscode-editor-pane { min-width: 0; min-height: 0; border-right: 1px solid #333333; background: #252526; overflow: hidden; }
#vscode-editor-tabs { height: 34px; box-sizing: border-box; padding: 9px 14px; border-bottom: 1px solid #333333; color: #9d9d9d; font: 12px system-ui, sans-serif; }
#vscode-editor-body { padding: 24px; color: #6f6f6f; font: 12px monospace; white-space: pre; }
#vscode-right-pane { min-width: 0; min-height: 0; width: ${pane.width}px; height: ${pane.height}px; overflow: hidden; background: #1e1e1e; }
#vscode-right-pane > #app { width: 100%; height: 100%; min-width: 0; min-height: 0; }
#vscode-statusbar { display: flex; align-items: center; padding: 0 12px; box-sizing: border-box; background: #007acc; color: #ffffff; font: 11px system-ui, sans-serif; }
</style>`;
    // The marker is written by the real webview after Vue + ELK settle.  It
    // records the actual Stage rectangle and the transform produced by the
    // production fitToView path, so screenshots cannot silently fall back to
    // a larger bare-SVG viewport.
    const metricsProbe = `<script>
(() => {
    const root = document.documentElement;
    let attempts = 0;
    const publish = () => {
        const stage = document.querySelector('.fcstm-stage__viewport');
        const svg = document.querySelector('.fcstm-stage__inner svg');
        const inner = document.querySelector('.fcstm-stage__inner');
        if (!stage || !svg || !inner || !inner.style.transform) {
            if (attempts++ < 600) setTimeout(publish, 50);
            return;
        }
        const stageRect = stage.getBoundingClientRect();
        const innerRect = inner.getBoundingClientRect();
        const svgWidth = Number(svg.getAttribute('width') || svg.viewBox.baseVal.width || 0);
        const svgHeight = Number(svg.getAttribute('height') || svg.viewBox.baseVal.height || 0);
        const payload = {
            windowWidth: window.innerWidth,
            windowHeight: window.innerHeight,
            stage: {left: stageRect.left, top: stageRect.top, width: stageRect.width, height: stageRect.height},
            inner: {left: innerRect.left, top: innerRect.top, right: innerRect.right, bottom: innerRect.bottom},
            rightPane: (() => {
                const rect = document.querySelector('#vscode-right-pane')?.getBoundingClientRect();
                return rect ? {left: rect.left, top: rect.top, width: rect.width, height: rect.height} : null;
            })(),
            svgWidth,
            svgHeight,
            transform: inner.style.transform,
            svgChildren: svg.children.length,
            stageEmpty: Boolean(document.querySelector('.fcstm-stage__empty')),
            shellScrollWidth: document.documentElement.scrollWidth,
            shellScrollHeight: document.documentElement.scrollHeight,
            paneScrollWidth: document.querySelector('#vscode-right-pane')?.scrollWidth || 0,
            paneScrollHeight: document.querySelector('#vscode-right-pane')?.scrollHeight || 0,
            shellChildren: Array.from(document.querySelectorAll('.fcstm-preview-shell > *')).map(element => {
                const rect = element.getBoundingClientRect();
                return {className: element.className, top: rect.top, height: rect.height, bottom: rect.bottom};
            }),
            errors: window.__FCSTM_PREVIEW_ERRORS__ || [],
        };
        root.setAttribute('data-fcstm-right-pane-metrics', btoa(unescape(encodeURIComponent(JSON.stringify(payload)))));
    };
    publish();
})();
</script>`;
    const errorProbe = '<script>window.__FCSTM_PREVIEW_ERRORS__=[];' +
        'window.addEventListener("error",e=>window.__FCSTM_PREVIEW_ERRORS__.push(String(e.error||e.message)));' +
        'window.addEventListener("unhandledrejection",e=>window.__FCSTM_PREVIEW_ERRORS__.push(String(e.reason)));</script>';
    return '<!doctype html><html><head><meta charset="utf-8"><style>' + webviewCss +
        '</style><style>html,body,#app{margin:0;padding:0;width:100%;height:100%;min-height:100%;}</style>' +
        shellCss + '</head><body>' + errorProbe + vscodeStub + initialState +
        '<div id="vscode-window">' +
        '<div id="vscode-titlebar">FCSTM Preview - VSCode workbench</div>' +
        '<div id="vscode-workbench"><div id="vscode-editor-pane"><div id="vscode-editor-tabs">machine.fcstm</div>' +
        '<div id="vscode-editor-body">state Machine {\n    // editor group\n}</div></div>' +
        '<div id="vscode-right-pane"><div id="app"></div></div></div>' +
        '<div id="vscode-statusbar">FCSTM  |  Preview</div></div>' +
        '<script>' + elkJs + '</script><script>' + webviewJs + '</script>' + metricsProbe + '</body></html>';
}

interface BrowserMetrics {
    windowWidth: number;
    windowHeight: number;
    stage: {left: number; top: number; width: number; height: number};
    inner: {left: number; top: number; right: number; bottom: number};
    rightPane: {left: number; top: number; width: number; height: number} | null;
    svgWidth: number;
    svgHeight: number;
    transform: string;
    svgChildren: number;
    stageEmpty: boolean;
    shellScrollWidth: number;
    shellScrollHeight: number;
    paneScrollWidth: number;
    paneScrollHeight: number;
    shellChildren?: Array<{className: string; top: number; height: number; bottom: number}>;
    errors?: string[];
}

function readBrowserMetrics(encoded: string, pngPath: string, viewport: RightPaneViewport): BrowserMetrics {
    if (!encoded) {
        throw new Error(`preview webview did not publish right-pane metrics for ${pngPath}`);
    }
    let metrics: BrowserMetrics;
    try {
        metrics = JSON.parse(Buffer.from(encoded, 'base64').toString('utf8')) as BrowserMetrics;
    } catch (error) {
        if (!(error instanceof SyntaxError) && !(error instanceof TypeError)) throw error;
        throw new Error(`invalid right-pane metrics for ${pngPath}: ${String(error)}`);
    }
    if (metrics.windowWidth !== viewport.windowWidth || metrics.windowHeight !== viewport.windowHeight) {
        throw new Error(
            `webview viewport is ${metrics.windowWidth}x${metrics.windowHeight}; ` +
            `expected full VSCode window ${viewport.windowWidth}x${viewport.windowHeight}`
        );
    }
    const png = readPngDimensions(pngPath);
    if (png.width !== viewport.windowWidth || png.height !== viewport.windowHeight) {
        throw new Error(
            `VSCode workbench screenshot is ${png.width}x${png.height}; ` +
            `expected ${viewport.windowWidth}x${viewport.windowHeight}`
        );
    }
    if (metrics.errors && metrics.errors.length > 0) {
        throw new Error(`preview webview reported runtime errors for ${pngPath}: ${metrics.errors.join('\n')}`);
    }
    if (metrics.stage.width <= 0 || metrics.stage.height <= 0 || metrics.svgWidth <= 0 ||
        metrics.svgHeight <= 0 || metrics.svgChildren === 0 || metrics.stageEmpty) {
        throw new Error(`right-pane webview did not render a usable Stage for ${pngPath}: ${JSON.stringify(metrics)}`);
    }
    const expectedPane = rightPaneRect(viewport);
    const close = (actual: number, wanted: number): boolean => Math.abs(actual - wanted) <= 1;
    if (!metrics.rightPane || !close(metrics.rightPane.left, expectedPane.left) ||
        !close(metrics.rightPane.top, expectedPane.top) ||
        !close(metrics.rightPane.width, expectedPane.width) ||
        !close(metrics.rightPane.height, expectedPane.height)) {
        throw new Error(
            `VSCode right-pane host geometry drifted for ${pngPath}: ` +
            `actual=${JSON.stringify(metrics.rightPane)}, expected=${JSON.stringify(expectedPane)}`
        );
    }
    if (metrics.shellScrollWidth > metrics.windowWidth || metrics.shellScrollHeight > metrics.windowHeight ||
        metrics.paneScrollWidth > expectedPane.width || metrics.paneScrollHeight > expectedPane.height) {
        throw new Error(
            `VSCode right-pane shell overflows its host for ${pngPath}: ` +
            JSON.stringify({window: [metrics.windowWidth, metrics.windowHeight],
                shellScroll: [metrics.shellScrollWidth, metrics.shellScrollHeight],
                pane: [expectedPane.width, expectedPane.height],
                paneScroll: [metrics.paneScrollWidth, metrics.paneScrollHeight],
                shellChildren: metrics.shellChildren})
        );
    }
    const paneRight = expectedPane.left + expectedPane.width;
    const paneBottom = expectedPane.top + expectedPane.height;
    if (metrics.stage.left < expectedPane.left - 1 || metrics.stage.top < expectedPane.top - 1 ||
        metrics.stage.left + metrics.stage.width > paneRight + 1 ||
        metrics.stage.top + metrics.stage.height > paneBottom + 1) {
        throw new Error(
            `Stage escapes the VSCode right editor group for ${pngPath}: ` +
            `pane=${JSON.stringify(expectedPane)}, stage=${JSON.stringify(metrics.stage)}`
        );
    }
    const transform = metrics.transform.match(
        /translate\(\s*([-+0-9.eE]+)px,\s*([-+0-9.eE]+)px\)\s*scale\(\s*([-+0-9.eE]+)\s*\)/
    );
    if (!transform) {
        throw new Error(`unable to parse production fit transform ${metrics.transform} for ${pngPath}`);
    }
    const tx = Number(transform[1]);
    const ty = Number(transform[2]);
    const scale = Number(transform[3]);
    const expected = computePreviewFit(metrics.stage, {width: metrics.svgWidth, height: metrics.svgHeight});
    const closeTransform = (actual: number, wanted: number): boolean => Math.abs(actual - wanted) <= 0.02;
    if (!closeTransform(tx, expected.tx) || !closeTransform(ty, expected.ty) || !closeTransform(scale, expected.scale)) {
        throw new Error(
            `production fit transform diverges from shared contract for ${pngPath}: ` +
            `actual=${JSON.stringify({tx, ty, scale})}, expected=${JSON.stringify(expected)}`
        );
    }
    const stageRight = metrics.stage.left + metrics.stage.width;
    const stageBottom = metrics.stage.top + metrics.stage.height;
    if (metrics.inner.left < metrics.stage.left - 1 || metrics.inner.top < metrics.stage.top - 1 ||
        metrics.inner.right > stageRight + 1 || metrics.inner.bottom > stageBottom + 1) {
        throw new Error(
            `fit-to-view content is clipped by the Stage viewport for ${pngPath}: ` +
            `stage=${JSON.stringify(metrics.stage)}, inner=${JSON.stringify(metrics.inner)}`
        );
    }
    return {
        windowWidth: metrics.windowWidth,
        windowHeight: metrics.windowHeight,
        stage: metrics.stage,
        svgWidth: metrics.svgWidth,
        svgHeight: metrics.svgHeight,
        rightPane: metrics.rightPane,
        shellScrollWidth: metrics.shellScrollWidth,
        shellScrollHeight: metrics.shellScrollHeight,
        paneScrollWidth: metrics.paneScrollWidth,
        paneScrollHeight: metrics.paneScrollHeight,
        shellChildren: metrics.shellChildren,
        transform: metrics.transform,
        tx,
        ty,
        scale,
        pngWidth: png.width,
        pngHeight: png.height,
        svgChildren: metrics.svgChildren,
    } as BrowserMetrics & ScreenshotMetrics;
}

function httpJson(port: number, endpoint: string): Promise<any> {
    return new Promise((resolve, reject) => {
        const request = http.get({host: '127.0.0.1', port, path: endpoint}, response => {
            let body = '';
            response.setEncoding('utf8');
            response.on('data', chunk => { body += chunk; });
            response.on('error', reject);
            response.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch (error) {
                    if (!(error instanceof SyntaxError)) throw error;
                    reject(error);
                }
            });
        });
        request.setTimeout(8000, () => request.destroy(new Error(`timed out reading Chrome ${endpoint}`)));
        request.on('error', reject);
    });
}

function rpcSend(ws: any, id: number, method: string, params: Record<string, unknown> = {}): Promise<any> {
    return new Promise((resolve, reject) => {
        const onMessage = (raw: Buffer | string) => {
            let body: any;
            try {
                body = JSON.parse(raw.toString());
            } catch (error) {
                if (!(error instanceof SyntaxError)) throw error;
                ws.off('message', onMessage);
                reject(error);
                return;
            }
            if (body.id !== id) return;
            ws.off('message', onMessage);
            if (body.error) {
                reject(new Error(`${method}: ${body.error.message}`));
                return;
            }
            resolve(body.result);
        };
        ws.on('message', onMessage);
        ws.send(JSON.stringify({id, method, params}));
    });
}

async function evaluatePage(ws: any, id: number, expression: string): Promise<any> {
    const result = await rpcSend(ws, id, 'Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true,
    });
    if (result?.exceptionDetails) {
        throw new Error(`preview page evaluation failed: ${result.exceptionDetails.text || expression}`);
    }
    return result?.result?.value;
}

interface RuntimePageSnapshot {
    stage: {width: number; height: number; left: number; top: number};
    inner: {left: number; top: number; right: number; bottom: number};
    pane: {left: number; top: number; width: number; height: number};
    drawer: {top: number; height: number; bottom: number};
    svgWidth: number;
    svgHeight: number;
    svgChildren: number;
    transform: string;
    shellScrollWidth: number;
    shellScrollHeight: number;
    paneScrollWidth: number;
    paneScrollHeight: number;
    errors: string[];
}

async function readRuntimePage(ws: any, id: number): Promise<RuntimePageSnapshot> {
    const value = await evaluatePage(ws, id, `(() => {
        const stage = document.querySelector('.fcstm-stage__viewport');
        const inner = document.querySelector('.fcstm-stage__inner');
        const pane = document.querySelector('#vscode-right-pane');
        const drawer = document.querySelector('.fcstm-bottom-drawer');
        const svg = document.querySelector('.fcstm-stage__inner svg');
        if (!stage || !inner || !pane || !drawer || !svg) return '';
        const s = stage.getBoundingClientRect();
        const i = inner.getBoundingClientRect();
        const p = pane.getBoundingClientRect();
        const d = drawer.getBoundingClientRect();
        return JSON.stringify({
            stage: {width: s.width, height: s.height, left: s.left, top: s.top},
            inner: {left: i.left, top: i.top, right: i.right, bottom: i.bottom},
            pane: {left: p.left, top: p.top, width: p.width, height: p.height},
            drawer: {top: d.top, height: d.height, bottom: d.bottom},
            svgWidth: Number(svg.getAttribute('width') || svg.viewBox.baseVal.width || 0),
            svgHeight: Number(svg.getAttribute('height') || svg.viewBox.baseVal.height || 0),
            svgChildren: svg.children.length,
            transform: inner.style.transform,
            shellScrollWidth: document.documentElement.scrollWidth,
            shellScrollHeight: document.documentElement.scrollHeight,
            paneScrollWidth: pane.scrollWidth,
            paneScrollHeight: pane.scrollHeight,
            errors: window.__FCSTM_PREVIEW_ERRORS__ || [],
        });
    })()`);
    if (!value) throw new Error('preview page did not expose runtime geometry');
    try {
        return JSON.parse(value) as RuntimePageSnapshot;
    } catch (error) {
        if (!(error instanceof SyntaxError)) throw error;
        throw new Error(`invalid runtime geometry snapshot: ${String(error)}`);
    }
}

function assertRuntimePage(snapshot: RuntimePageSnapshot, viewport: RightPaneViewport, label: string): void {
    const expectedPane = rightPaneRect(viewport);
    const close = (actual: number, wanted: number): boolean => Math.abs(actual - wanted) <= 1;
    if (!close(snapshot.pane.left, expectedPane.left) || !close(snapshot.pane.top, expectedPane.top) ||
        !close(snapshot.pane.width, expectedPane.width) || !close(snapshot.pane.height, expectedPane.height)) {
        throw new Error(`${label}: right pane geometry drifted: ${JSON.stringify({snapshot, expectedPane})}`);
    }
    if (snapshot.errors.length > 0 || snapshot.svgChildren === 0 || snapshot.svgWidth <= 0 || snapshot.svgHeight <= 0) {
        throw new Error(`${label}: preview runtime is unhealthy: ${JSON.stringify(snapshot)}`);
    }
    if (snapshot.shellScrollWidth > viewport.windowWidth || snapshot.shellScrollHeight > viewport.windowHeight ||
        snapshot.paneScrollWidth > expectedPane.width || snapshot.paneScrollHeight > expectedPane.height) {
        throw new Error(`${label}: right pane overflowed after resize: ${JSON.stringify(snapshot)}`);
    }
    const paneRight = expectedPane.left + expectedPane.width;
    const paneBottom = expectedPane.top + expectedPane.height;
    if (snapshot.stage.left < expectedPane.left - 1 || snapshot.stage.top < expectedPane.top - 1 ||
        snapshot.stage.left + snapshot.stage.width > paneRight + 1 ||
        snapshot.stage.top + snapshot.stage.height > paneBottom + 1) {
        throw new Error(`${label}: Stage escaped right pane: ${JSON.stringify(snapshot)}`);
    }
    const stageRight = snapshot.stage.left + snapshot.stage.width;
    const stageBottom = snapshot.stage.top + snapshot.stage.height;
    if (snapshot.inner.left < snapshot.stage.left - 1 || snapshot.inner.top < snapshot.stage.top - 1 ||
        snapshot.inner.right > stageRight + 1 || snapshot.inner.bottom > stageBottom + 1) {
        throw new Error(`${label}: transformed diagram is clipped by Stage: ${JSON.stringify(snapshot)}`);
    }
    const transform = snapshot.transform.match(
        /translate\(\s*([-+0-9.eE]+)px,\s*([-+0-9.eE]+)px\)\s*scale\(\s*([-+0-9.eE]+)\s*\)/
    );
    if (!transform) throw new Error(`${label}: production fit transform is missing: ${snapshot.transform}`);
    const expected = computePreviewFit(snapshot.stage, {width: snapshot.svgWidth, height: snapshot.svgHeight});
    if (Math.abs(Number(transform[1]) - expected.tx) > 0.02 ||
        Math.abs(Number(transform[2]) - expected.ty) > 0.02 ||
        Math.abs(Number(transform[3]) - expected.scale) > 0.02) {
        throw new Error(`${label}: fit transform drifted: ${JSON.stringify({snapshot, expected})}`);
    }
}

function runtimeEvidence(snapshot: RuntimePageSnapshot): RuntimeEvidence {
    return {
        pane: snapshot.pane,
        stage: snapshot.stage,
        drawer: snapshot.drawer,
        inner: snapshot.inner,
        svg: {width: snapshot.svgWidth, height: snapshot.svgHeight, children: snapshot.svgChildren},
        fitTransform: snapshot.transform,
        shellScroll: {width: snapshot.shellScrollWidth, height: snapshot.shellScrollHeight},
        paneScroll: {width: snapshot.paneScrollWidth, height: snapshot.paneScrollHeight},
    };
}

async function dispatchDrawerDrag(ws: any, id: number, deltaY: number): Promise<number> {
    await evaluatePage(ws, ++id, `(() => {
        const handle = document.querySelector('.fcstm-bottom-drawer__handle');
        if (!handle) throw new Error('drawer resize handle missing');
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        const endY = startY + ${deltaY};
        handle.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, button: 0, clientX: x, clientY: startY}));
        window.dispatchEvent(new MouseEvent('mousemove', {bubbles: true, buttons: 1, clientX: x, clientY: endY}));
        window.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, button: 0, clientX: x, clientY: endY}));
        return true;
    })()`);
    return id;
}

interface ResizeExerciseResult {
    id: number;
    metrics: ResizeExerciseMetrics;
}

async function exerciseDrawerResize(
    ws: any,
    id: number,
    viewport: RightPaneViewport,
): Promise<ResizeExerciseResult> {
    const before = await readRuntimePage(ws, ++id);
    assertRuntimePage(before, viewport, 'before drawer resize');

    // Exercise the real handle path first. Dragging down shrinks the drawer
    // and gives Stage more room, so the assertion remains valid even in the
    // compact 512px half-pane where Stage has a 240px minimum.  The
    // production handler computes ``startY - clientY``; therefore a positive
    // delta is the downward (drawer-shrinking) gesture.
    const dragDelta = Math.min(60, Math.max(24, Math.floor(before.drawer.height * 0.2)));
    id = await dispatchDrawerDrag(ws, id, dragDelta);
    await new Promise(resolve => setTimeout(resolve, 350));
    const dragged = await readRuntimePage(ws, ++id);
    assertRuntimePage(dragged, viewport, 'after drawer drag');
    if (dragged.stage.height <= before.stage.height + 10 || dragged.drawer.height >= before.drawer.height - 10) {
        throw new Error(`drawer drag did not resize the production layout: ${JSON.stringify({before, dragged})}`);
    }
    id = await dispatchDrawerDrag(ws, id, -dragDelta);
    await new Promise(resolve => setTimeout(resolve, 350));
    const dragRestored = await readRuntimePage(ws, ++id);
    assertRuntimePage(dragRestored, viewport, 'after drawer drag restore');
    if (Math.abs(dragRestored.stage.height - before.stage.height) > 1 ||
        Math.abs(dragRestored.drawer.height - before.drawer.height) > 1) {
        throw new Error(`drawer drag restore did not return original layout: ${JSON.stringify({before, dragRestored})}`);
    }

    await evaluatePage(ws, ++id, `(() => {
        const button = document.querySelector('.fcstm-bottom-drawer__toggle');
        if (!button) throw new Error('drawer toggle missing');
        button.click();
        return true;
    })()`);
    await new Promise(resolve => setTimeout(resolve, 350));
    const collapsed = await readRuntimePage(ws, ++id);
    assertRuntimePage(collapsed, viewport, 'after drawer collapse');
    if (collapsed.stage.height <= before.stage.height + 20) {
        throw new Error(`drawer collapse did not enlarge Stage: ${JSON.stringify({before, collapsed})}`);
    }
    await evaluatePage(ws, ++id, `(() => {
        const button = document.querySelector('.fcstm-bottom-drawer__toggle');
        if (!button) throw new Error('drawer toggle missing after collapse');
        button.click();
        return true;
    })()`);
    await new Promise(resolve => setTimeout(resolve, 350));
    const restored = await readRuntimePage(ws, ++id);
    assertRuntimePage(restored, viewport, 'after drawer restore');
    if (Math.abs(restored.stage.height - before.stage.height) > 1) {
        throw new Error(`drawer restore did not return Stage height: ${JSON.stringify({before, restored})}`);
    }
    return {
        id,
        metrics: {
            drag: {
                beforeStageHeight: before.stage.height,
                draggedStageHeight: dragged.stage.height,
                restoredStageHeight: dragRestored.stage.height,
                beforeDrawerHeight: before.drawer.height,
                draggedDrawerHeight: dragged.drawer.height,
                restoredDrawerHeight: dragRestored.drawer.height,
                runtime: {
                    before: runtimeEvidence(before),
                    dragged: runtimeEvidence(dragged),
                    restored: runtimeEvidence(dragRestored),
                },
            },
            toggle: {
                beforeStageHeight: before.stage.height,
                collapsedStageHeight: collapsed.stage.height,
                restoredStageHeight: restored.stage.height,
                beforeDrawerHeight: before.drawer.height,
                collapsedDrawerHeight: collapsed.drawer.height,
                restoredDrawerHeight: restored.drawer.height,
                runtime: {
                    before: runtimeEvidence(before),
                    collapsed: runtimeEvidence(collapsed),
                    restored: runtimeEvidence(restored),
                },
            },
        },
    };
}

async function captureWebviewScreenshot(
    chrome: string,
    htmlPath: string,
    pngPath: string,
    viewport: RightPaneViewport,
    exerciseResize: boolean,
): Promise<{marker: string; resize: ResizeExerciseMetrics | null}> {
    const vscodeDir = path.resolve(process.env.PYFCSTM_VSCODE_DIR || process.cwd());
    const requireFromVscode = createRequire(path.join(vscodeDir, 'package.json'));
    const WebSocket = requireFromVscode('ws') as any;
    const port = 9200 + (process.pid % 700);
    const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-preview-chrome-'));
    const browser = spawn(chrome, [
        '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
        '--disable-dev-shm-usage', `--user-data-dir=${profileDir}`,
        `--remote-debugging-port=${port}`, `--window-size=${viewport.windowWidth},${viewport.windowHeight}`, 'about:blank',
    ], {stdio: ['ignore', 'ignore', 'pipe']});
    let ws: any = null;
    try {
        const deadline = Date.now() + 8000;
        let pages: any[] = [];
        while (Date.now() < deadline) {
            try {
                pages = await httpJson(port, '/json/list');
                if (pages.some(page => page.type === 'page')) break;
            } catch (error) {
                if (!(error instanceof Error)) throw error;
                await new Promise(resolve => setTimeout(resolve, 80));
            }
        }
        const page = pages.find(item => item.type === 'page');
        if (!page?.webSocketDebuggerUrl) {
            throw new Error(`Chrome did not expose a page for ${htmlPath}`);
        }
        ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise<void>((resolve, reject) => {
            ws.once('open', resolve);
            ws.once('error', reject);
        });
        let id = 0;
        await rpcSend(ws, ++id, 'Runtime.enable');
        await rpcSend(ws, ++id, 'Page.enable');
        await rpcSend(ws, ++id, 'Emulation.setDeviceMetricsOverride', {
            width: viewport.windowWidth,
            height: viewport.windowHeight,
            deviceScaleFactor: 1,
            mobile: false,
        });
        await rpcSend(ws, ++id, 'Page.navigate', {url: pathToFileURL(htmlPath).toString()});

        const markerDeadline = Date.now() + 30000;
        let marker = '';
        while (Date.now() < markerDeadline) {
            const probe = await rpcSend(ws, ++id, 'Runtime.evaluate', {
                expression: 'document.documentElement.getAttribute("data-fcstm-right-pane-metrics") || ""',
                returnByValue: true,
            });
            marker = probe?.result?.value || '';
            if (marker) break;
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        if (!marker) {
            const diagnostics = await evaluatePage(ws, ++id,
                'JSON.stringify({title:document.title,body:(document.body?.innerText||"").slice(-1200),' +
                'errors:window.__FCSTM_PREVIEW_ERRORS__||[]})');
            throw new Error(`preview webview did not settle before screenshot: ${htmlPath}; diagnostics=${diagnostics}`);
        }
        let resize: ResizeExerciseMetrics | null = null;
        if (exerciseResize) {
            const exercise = await exerciseDrawerResize(ws, id, viewport);
            id = exercise.id;
            resize = exercise.metrics;
        }
        const shot = await rpcSend(ws, ++id, 'Page.captureScreenshot', {
            format: 'png',
            fromSurface: true,
            captureBeyondViewport: false,
        });
        fs.writeFileSync(pngPath, Buffer.from(shot.data, 'base64'));
        return {marker, resize};
    } finally {
        if (ws) ws.close();
        browser.kill('SIGTERM');
        if (browser.exitCode === null) {
            await new Promise<void>(resolve => browser.once('exit', () => resolve()));
        }
        fs.rmSync(profileDir, {recursive: true, force: true, maxRetries: 10, retryDelay: 100});
    }
}

async function screenshot(
    chrome: string,
    state: PreviewWebviewState,
    pngPath: string,
    viewport: RightPaneViewport,
    exerciseResize = false,
): Promise<ScreenshotMetrics> {
    const htmlPath = pngPath.replace(/\.png$/, '.html');
    const html = previewWebviewHtml(state, viewport);
    fs.writeFileSync(htmlPath, html);
    let capture: {marker: string; resize: ResizeExerciseMetrics | null};
    try {
        // The capture is the full VSCode-workbench shell.  The production
        // preview is mounted in the right editor group, whose half-width
        // rectangle is checked separately from the outer window dimensions.
        capture = await captureWebviewScreenshot(chrome, htmlPath, pngPath, viewport, exerciseResize);
    } finally {
        fs.rmSync(htmlPath, {force: true});
    }
    const metrics = readBrowserMetrics(capture.marker, pngPath, viewport) as BrowserMetrics & ScreenshotMetrics;
    return {
        shellViewportWidth: metrics.windowWidth,
        shellViewportHeight: metrics.windowHeight,
        rightPaneWidth: metrics.rightPane?.width || 0,
        rightPaneHeight: metrics.rightPane?.height || 0,
        stageViewportWidth: metrics.stage.width,
        stageViewportHeight: metrics.stage.height,
        svgWidth: metrics.svgWidth,
        svgHeight: metrics.svgHeight,
        tx: metrics.tx,
        ty: metrics.ty,
        scale: metrics.scale,
        pngWidth: metrics.pngWidth,
        pngHeight: metrics.pngHeight,
        png: path.basename(pngPath),
        svgChildren: metrics.svgChildren,
        resize: capture.resize,
    };
}

async function main(): Promise<void> {
    const fixtureDir = path.resolve(process.env.PYFCSTM_VISUAL_FIXTURES ||
        path.resolve(process.cwd(), '../jsfcstm/test/fixtures/visual'));
    const outputDir = path.resolve(process.env.PYFCSTM_GEOMETRY_OUTPUT ||
        path.resolve(process.cwd(), '../../artifacts/preview-geometry'));
    fs.rmSync(outputDir, {recursive: true, force: true});
    fs.mkdirSync(outputDir, {recursive: true});
    const fixtureNames = fs.readdirSync(fixtureDir).filter(name => name.endsWith('.fcstm')).sort();
    if (fixtureNames.length < 10) {
        throw new Error(`expected at least 10 visual fixtures, found ${fixtureNames.length}`);
    }

    const elk = new ELK();
    const reports: FixtureReport[] = [];
    const chrome = locateChrome();
    let drawerResizeExerciseCount = 0;
    let drawerDragExerciseCount = 0;
    if (!chrome && process.env.PYFCSTM_REQUIRE_PREVIEW_BROWSER === '1') {
        throw new Error('PYFCSTM_REQUIRE_PREVIEW_BROWSER=1 but no Chrome/Chromium executable was found');
    }
    for (const fixtureName of fixtureNames) {
        const sourcePath = path.join(fixtureDir, fixtureName);
        for (const direction of ['TB', 'LR'] as const) {
            const options = resolveFcstmDiagramPreviewOptions({detailLevel: 'normal', direction});
            const payload = await buildFcstmDiagramWebviewPayload(
                new InMemoryDocument(sourcePath),
                options,
            );
            if (!payload) throw new Error(`${fixtureName}: diagram construction returned null`);
            const fixedInput = clone(payload.graph);
            const baselineInput = clone(fixedInput);
            removeNestedSpacing(baselineInput);
            const baseline = await elk.layout(baselineInput) as any;
            const fixed = await elk.layout(clone(fixedInput)) as any;
            smoothGraphEdges(baseline);
            smoothGraphEdges(fixed);

            const stem = `${path.basename(fixtureName, '.fcstm')}.${direction}`;
            const baselineSvg = path.join(outputDir, `${stem}.baseline.svg`);
            const fixedSvg = path.join(outputDir, `${stem}.fixed.svg`);
            const previewOptions = toPreviewOptions(options);
            const baselineRendered = renderSvg(baseline, previewOptions);
            const fixedRendered = renderSvg(fixed, previewOptions);
            fs.writeFileSync(baselineSvg, baselineRendered.svg);
            fs.writeFileSync(fixedSvg, fixedRendered.svg);
            const screenshots: Record<string, {
                baseline: ScreenshotMetrics | null;
                fixed: ScreenshotMetrics | null;
            }> = {};
            for (const viewport of RIGHT_PANE_VIEWPORTS) {
                const baselinePng = path.join(outputDir, `${stem}.${viewport.id}.baseline.png`);
                const fixedPng = path.join(outputDir, `${stem}.${viewport.id}.fixed.png`);
                screenshots[viewport.id] = {
                    baseline: chrome
                        ? await screenshot(
                            chrome,
                            previewState(payload, baselineInput, fixtureName),
                            baselinePng,
                            viewport,
                        )
                        : null,
                    fixed: chrome
                        ? await screenshot(
                            chrome,
                            previewState(payload, fixedInput, fixtureName),
                            fixedPng,
                            viewport,
                            // Keep the drawer contract covered for every
                            // right-pane size and layout direction.
                            true,
                        )
                        : null,
                };
                if (chrome) {
                    drawerResizeExerciseCount += 1;
                    drawerDragExerciseCount += 1;
                }
            }
            const baselineArea = (baseline.width ?? 0) * (baseline.height ?? 0);
            const fixedArea = (fixed.width ?? 0) * (fixed.height ?? 0);
            reports.push({
                fixture: fixtureName,
                direction,
                baseline: measure(baseline),
                fixed: measure(fixed),
                svg: {baseline: path.basename(baselineSvg), fixed: path.basename(fixedSvg)},
                screenshots,
                layout: {
                    baseline: {
                        width: baseline.width ?? 0,
                        height: baseline.height ?? 0,
                        crossings: countCrossings(baseline),
                    },
                    fixed: {
                        width: fixed.width ?? 0,
                        height: fixed.height ?? 0,
                        crossings: countCrossings(fixed),
                    },
                    areaDeltaPercent: baselineArea > 0
                        ? ((fixedArea - baselineArea) / baselineArea) * 100
                        : 0,
                },
            });
        }
    }

    const fixedFailures = reports.filter(item => item.fixed.malformed > 0 || item.fixed.short > 0 ||
        item.fixed.malformedSelfLoops > 0 || item.fixed.shortSelfLoops > 0);
    const baselineFailures = reports.filter(item => item.baseline.malformed > 0 || item.baseline.short > 0 ||
        item.baseline.malformedSelfLoops > 0 || item.baseline.shortSelfLoops > 0);
    const crossingRegressions = reports.filter(item => item.layout.fixed.crossings > item.layout.baseline.crossings);
    const areaDeltas = reports.map(item => item.layout.areaDeltaPercent);
    const report = {
        generatedAt: new Date().toISOString(),
        evidence: {
            gitHead: process.env.PYFCSTM_GEOMETRY_GIT_HEAD || null,
            rightPaneModel: 'VSCode workbench shell with preview mounted in a 50% right editor group',
            sourceAndBundleHashes: {
                jsfcstmDiagramSources: process.env.PYFCSTM_GEOMETRY_JSFCSTM_SOURCE_HASH || null,
                previewWebviewSources: process.env.PYFCSTM_GEOMETRY_PREVIEW_SOURCE_HASH || null,
                jsfcstmDiagramBundle: sha256File(path.resolve(process.cwd(), '../jsfcstm/dist/diagram/index.js')),
                previewWebviewBundle: sha256File(path.resolve(process.cwd(), 'dist/preview-webview.js')),
                previewWebviewCss: sha256File(path.resolve(process.cwd(), 'dist/preview-webview.css')),
            },
        },
        fixtureCount: fixtureNames.length,
        directions: ['TB', 'LR'],
        rightPaneViewports: RIGHT_PANE_VIEWPORTS,
        productionPostProcess: 'smoothGraphEdges',
        terminalMinimumPx: MIN_TERMINAL_SEGMENT,
        fitToViewMargin: PREVIEW_FIT_MARGIN_PX,
        screenshotEvidence: chrome ? 'production preview-webview App shell inside VSCode-like right editor group' : 'not available',
        drawerResizeExerciseCount,
        drawerDragExerciseCount,
        baselineFailures: baselineFailures.length,
        fixedFailures: fixedFailures.length,
        sideEffects: {
            crossingRegressions: crossingRegressions.length,
            meanAreaDeltaPercent: areaDeltas.length > 0
                ? areaDeltas.reduce((sum, value) => sum + value, 0) / areaDeltas.length
                : 0,
            maxAreaDeltaPercent: areaDeltas.length > 0 ? Math.max(...areaDeltas) : 0,
        },
        reports,
    };
    fs.writeFileSync(path.join(outputDir, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({
        fixtureCount: fixtureNames.length,
        layoutCount: reports.length,
        baselineFailures: baselineFailures.length,
        fixedFailures: fixedFailures.length,
        crossingRegressions: crossingRegressions.length,
        screenshots: Boolean(chrome),
        screenshotViewports: RIGHT_PANE_VIEWPORTS.map(viewport => viewport.id),
        drawerResizeExerciseCount,
        drawerDragExerciseCount,
        outputDir,
    }, null, 2));
    if (fixedFailures.length > 0 || crossingRegressions.length > 0 ||
        (process.env.PYFCSTM_REQUIRE_PREVIEW_BROWSER === '1' && !chrome)) {
        throw new Error(
            `fixed geometry has ${fixedFailures.length} geometry failures and ` +
            `${crossingRegressions.length} crossing regressions`
        );
    }
}

void main().catch(error => {
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    process.exitCode = 1;
});
