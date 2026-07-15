import * as fs from 'node:fs';
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
}

interface RightPaneViewport {
    id: string;
    width: number;
    height: number;
}

// These are shell dimensions, not a bare browser canvas.  The first case is
// a typical 1920px-wide VSCode window with a 720px-tall work area; the second
// is a compact laptop split.  The actual Stage rectangle is measured after the Toolbar, OptionsBar
// and Details drawer have been mounted by the production webview bundle.
const RIGHT_PANE_VIEWPORTS: RightPaneViewport[] = [
    {id: 'desktop-half', width: 960, height: 720},
    {id: 'compact-half', width: 768, height: 600},
    {id: 'wide-half', width: 1280, height: 800},
];

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
        delete node.layoutOptions['elk.layered.spacing.edgeNodeBetweenLayers'];
        delete node.layoutOptions['elk.layered.spacing.edgeEdgeBetweenLayers'];
    }
    for (const child of node.children || []) removeNestedSpacing(child, false);
}

function measure(graph: any): GeometryMetrics {
    const {boxes, edgeOffsets} = collectElkLayoutGeometry(graph);
    const result: GeometryMetrics = {sections: 0, malformed: 0, short: 0, minTerminal: null};

    function visit(node: any): void {
        for (const edge of node.edges || []) {
            const sourceId = edge.sources?.[0];
            const targetId = edge.targets?.[0];
            if (!sourceId || !targetId || sourceId === targetId) continue;
            const box = boxes.get(targetId);
            const offset = edgeOffsets.get(edge.id);
            if (!offset) {
                throw new Error(`edge ${edge.id}: owner offset missing during geometry collection`);
            }
            for (const section of edge.sections || []) {
                result.sections += 1;
                const points: Point[] = [
                    section.startPoint,
                    ...(section.bendPoints || []),
                    section.endPoint,
                ].map(point => ({x: point.x + offset.x, y: point.y + offset.y}));
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

function previewWebviewHtml(state: PreviewWebviewState): string {
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
            svgWidth,
            svgHeight,
            transform: inner.style.transform,
            svgChildren: svg.children.length,
            stageEmpty: Boolean(document.querySelector('.fcstm-stage__empty')),
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
        '</style><style>html,body,#app{margin:0;padding:0;width:100%;height:100%;min-height:100%;}</style></head><body>' +
        errorProbe + vscodeStub + initialState + '<div id="app"></div><script>' + elkJs + '</script><script>' + webviewJs +
        '</script>' + metricsProbe + '</body></html>';
}

interface BrowserMetrics {
    windowWidth: number;
    windowHeight: number;
    stage: {left: number; top: number; width: number; height: number};
    inner: {left: number; top: number; right: number; bottom: number};
    svgWidth: number;
    svgHeight: number;
    transform: string;
    svgChildren: number;
    stageEmpty: boolean;
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
    if (metrics.windowWidth !== viewport.width || metrics.windowHeight !== viewport.height) {
        throw new Error(
            `webview viewport is ${metrics.windowWidth}x${metrics.windowHeight}; ` +
            `expected ${viewport.width}x${viewport.height}`
        );
    }
    const png = readPngDimensions(pngPath);
    if (png.width !== viewport.width || png.height !== viewport.height) {
        throw new Error(
            `right-pane screenshot is ${png.width}x${png.height}; expected ${viewport.width}x${viewport.height}`
        );
    }
    if (metrics.stage.width <= 0 || metrics.stage.height <= 0 || metrics.svgWidth <= 0 ||
        metrics.svgHeight <= 0 || metrics.svgChildren === 0 || metrics.stageEmpty) {
        throw new Error(`right-pane webview did not render a usable Stage for ${pngPath}: ${JSON.stringify(metrics)}`);
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
    const close = (actual: number, wanted: number): boolean => Math.abs(actual - wanted) <= 0.02;
    if (!close(tx, expected.tx) || !close(ty, expected.ty) || !close(scale, expected.scale)) {
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

interface PageRectSnapshot {
    stage: {width: number; height: number; left: number; top: number};
    inner: {left: number; top: number; right: number; bottom: number};
}

async function readPageRects(ws: any, id: number): Promise<PageRectSnapshot> {
    const value = await evaluatePage(ws, id, `(() => {
        const stage = document.querySelector('.fcstm-stage__viewport');
        const inner = document.querySelector('.fcstm-stage__inner');
        if (!stage || !inner) return '';
        const s = stage.getBoundingClientRect();
        const i = inner.getBoundingClientRect();
        return JSON.stringify({
            stage: {width: s.width, height: s.height, left: s.left, top: s.top},
            inner: {left: i.left, top: i.top, right: i.right, bottom: i.bottom},
        });
    })()`);
    if (!value) throw new Error('preview page did not expose Stage rectangles');
    try {
        return JSON.parse(value) as PageRectSnapshot;
    } catch (error) {
        if (!(error instanceof SyntaxError)) throw error;
        throw new Error(`invalid Stage rectangle snapshot: ${String(error)}`);
    }
}

function assertRectInside(snapshot: PageRectSnapshot, label: string): void {
    const stageRight = snapshot.stage.left + snapshot.stage.width;
    const stageBottom = snapshot.stage.top + snapshot.stage.height;
    if (snapshot.inner.left < snapshot.stage.left - 1 || snapshot.inner.top < snapshot.stage.top - 1 ||
        snapshot.inner.right > stageRight + 1 || snapshot.inner.bottom > stageBottom + 1) {
        throw new Error(`${label}: transformed diagram is clipped by Stage: ${JSON.stringify(snapshot)}`);
    }
}

async function exerciseDrawerResize(ws: any, id: number): Promise<number> {
    const before = await readPageRects(ws, ++id);
    assertRectInside(before, 'before drawer resize');
    await evaluatePage(ws, ++id, `(() => {
        const button = document.querySelector('.fcstm-bottom-drawer__toggle');
        if (!button) throw new Error('drawer toggle missing');
        button.click();
        return true;
    })()`);
    await new Promise(resolve => setTimeout(resolve, 350));
    const collapsed = await readPageRects(ws, ++id);
    if (collapsed.stage.height <= before.stage.height + 20) {
        throw new Error(`drawer collapse did not enlarge Stage: ${JSON.stringify({before, collapsed})}`);
    }
    assertRectInside(collapsed, 'after drawer collapse');
    await evaluatePage(ws, ++id, `(() => {
        const button = document.querySelector('.fcstm-bottom-drawer__toggle');
        if (!button) throw new Error('drawer toggle missing after collapse');
        button.click();
        return true;
    })()`);
    await new Promise(resolve => setTimeout(resolve, 350));
    const restored = await readPageRects(ws, ++id);
    if (Math.abs(restored.stage.height - before.stage.height) > 1) {
        throw new Error(`drawer restore did not return Stage height: ${JSON.stringify({before, restored})}`);
    }
    // This final assertion is the regression guard: without the production
    // ResizeObserver, the expanded drawer leaves the larger collapsed-scale
    // diagram clipped by the smaller Stage.
    assertRectInside(restored, 'after drawer restore');
    return id;
}

async function captureWebviewScreenshot(
    chrome: string,
    htmlPath: string,
    pngPath: string,
    viewport: RightPaneViewport,
    exerciseResize: boolean,
): Promise<string> {
    const vscodeDir = path.resolve(process.env.PYFCSTM_VSCODE_DIR || process.cwd());
    const requireFromVscode = createRequire(path.join(vscodeDir, 'package.json'));
    const WebSocket = requireFromVscode('ws') as any;
    const port = 9200 + (process.pid % 700);
    const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-preview-chrome-'));
    const browser = spawn(chrome, [
        '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
        '--disable-dev-shm-usage', `--user-data-dir=${profileDir}`,
        `--remote-debugging-port=${port}`, `--window-size=${viewport.width},${viewport.height}`, 'about:blank',
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
            width: viewport.width,
            height: viewport.height,
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
        if (exerciseResize) id = await exerciseDrawerResize(ws, id);
        const shot = await rpcSend(ws, ++id, 'Page.captureScreenshot', {
            format: 'png',
            fromSurface: true,
            captureBeyondViewport: false,
        });
        fs.writeFileSync(pngPath, Buffer.from(shot.data, 'base64'));
        return marker;
    } finally {
        if (ws) ws.close();
        browser.kill('SIGTERM');
        if (browser.exitCode === null) {
            await new Promise<void>(resolve => browser.once('exit', () => resolve()));
        }
        fs.rmSync(profileDir, {recursive: true, force: true});
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
    const html = previewWebviewHtml(state);
    fs.writeFileSync(htmlPath, html);
    let encodedMetrics: string;
    try {
        // The actual capture uses CDP so ``viewport`` is the webview content
        // rectangle rather than Chrome's outer window (which includes an
        // implementation-dependent 87px headless frame offset).
        encodedMetrics = await captureWebviewScreenshot(chrome, htmlPath, pngPath, viewport, exerciseResize);
    } finally {
        fs.rmSync(htmlPath, {force: true});
    }
    const metrics = readBrowserMetrics(encodedMetrics, pngPath, viewport) as BrowserMetrics & ScreenshotMetrics;
    return {
        shellViewportWidth: metrics.windowWidth,
        shellViewportHeight: metrics.windowHeight,
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
                            viewport.id === 'desktop-half' && direction === 'TB',
                        )
                        : null,
                };
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

    const fixedFailures = reports.filter(item => item.fixed.malformed > 0 || item.fixed.short > 0);
    const baselineFailures = reports.filter(item => item.baseline.malformed > 0 || item.baseline.short > 0);
    const crossingRegressions = reports.filter(item => item.layout.fixed.crossings > item.layout.baseline.crossings);
    const areaDeltas = reports.map(item => item.layout.areaDeltaPercent);
    const report = {
        generatedAt: new Date().toISOString(),
        fixtureCount: fixtureNames.length,
        directions: ['TB', 'LR'],
        rightPaneViewports: RIGHT_PANE_VIEWPORTS,
        productionPostProcess: 'smoothGraphEdges',
        terminalMinimumPx: MIN_TERMINAL_SEGMENT,
        fitToViewMargin: PREVIEW_FIT_MARGIN_PX,
        screenshotEvidence: chrome ? 'production preview-webview App shell' : 'not available',
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
