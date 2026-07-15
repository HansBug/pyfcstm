import * as fs from 'node:fs';
import * as path from 'node:path';
import {spawnSync} from 'node:child_process';

import ELK from 'elkjs/lib/elk.bundled.js';

import {
    buildFcstmDiagramFromDocument,
    buildFcstmElkGraph,
    collectElkLayoutGeometry,
    MIN_TERMINAL_SEGMENT,
    resolveFcstmDiagramPreviewOptions,
    terminalApproach,
} from '../../jsfcstm/dist/diagram';
import {smoothGraphEdges} from '../src/preview-webview/render/edge-smoother';
import {buildCrossingIndex, collectSegments} from '../src/preview-webview/render/crossings';
import {renderSvg} from '../src/preview-webview/render/svg';
import type {PreviewResolvedOptions} from '../src/preview-webview/types';

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
    screenshots: {
        baseline: ScreenshotMetrics | null;
        fixed: ScreenshotMetrics | null;
    };
    layout: {
        baseline: {width: number; height: number; crossings: number};
        fixed: {width: number; height: number; crossings: number};
        areaDeltaPercent: number;
    };
}

interface ScreenshotMetrics {
    viewportWidth: number;
    viewportHeight: number;
    scale: number;
    pngWidth: number;
    pngHeight: number;
}

// The preview normally occupies the right half of a 1920px-wide VSCode
// window. Match Stage.vue's fitToView margin instead of treating Chrome's
// viewport as an unconstrained full-page canvas.
const PREVIEW_VIEWPORT = {width: 960, height: 720};
const PREVIEW_MARGIN = 16;

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

function screenshot(
    chrome: string,
    svgPath: string,
    pngPath: string,
    svgWidth: number,
    svgHeight: number,
): ScreenshotMetrics {
    const htmlPath = svgPath.replace(/\.svg$/, '.html');
    const availableWidth = Math.max(40, PREVIEW_VIEWPORT.width - PREVIEW_MARGIN * 2);
    const availableHeight = Math.max(40, PREVIEW_VIEWPORT.height - PREVIEW_MARGIN * 2);
    const scale = Math.min(availableWidth / svgWidth, availableHeight / svgHeight, 1);
    const offsetX = (PREVIEW_VIEWPORT.width - svgWidth * scale) / 2;
    const offsetY = (PREVIEW_VIEWPORT.height - svgHeight * scale) / 2;
    const html = '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}' +
        `.viewport{position:relative;width:${PREVIEW_VIEWPORT.width}px;height:${PREVIEW_VIEWPORT.height}px;` +
        'overflow:hidden;background:#fff}' +
        `.canvas{position:absolute;left:${offsetX}px;top:${offsetY}px;width:${svgWidth}px;` +
        `height:${svgHeight}px;transform:scale(${scale});transform-origin:0 0}` +
        'svg{display:block}</style>' +
        '<div class="viewport"><div class="canvas">' +
        fs.readFileSync(svgPath, 'utf8') + '</div></div>';
    fs.writeFileSync(htmlPath, html);
    const result = spawnSync(chrome, [
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--virtual-time-budget=3000',
        '--force-device-scale-factor=1',
        `--window-size=${PREVIEW_VIEWPORT.width},${PREVIEW_VIEWPORT.height}`,
        `--screenshot=${pngPath}`, `file://${htmlPath}`,
    ], {stdio: 'pipe'});
    fs.rmSync(htmlPath, {force: true});
    if (result.status !== 0) {
        throw new Error(`Chrome screenshot failed for ${svgPath}: ${result.stderr?.toString() || ''}`);
    }
    const png = readPngDimensions(pngPath);
    if (png.width !== PREVIEW_VIEWPORT.width || png.height !== PREVIEW_VIEWPORT.height) {
        throw new Error(
            `preview screenshot has unexpected dimensions ${png.width}x${png.height}; ` +
            `expected ${PREVIEW_VIEWPORT.width}x${PREVIEW_VIEWPORT.height}`
        );
    }
    return {
        viewportWidth: PREVIEW_VIEWPORT.width,
        viewportHeight: PREVIEW_VIEWPORT.height,
        scale,
        pngWidth: png.width,
        pngHeight: png.height,
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
    for (const fixtureName of fixtureNames) {
        const sourcePath = path.join(fixtureDir, fixtureName);
        const diagram = await buildFcstmDiagramFromDocument(new InMemoryDocument(sourcePath));
        if (!diagram) throw new Error(`${fixtureName}: diagram construction returned null`);
        for (const direction of ['TB', 'LR'] as const) {
            const options = resolveFcstmDiagramPreviewOptions({detailLevel: 'normal', direction});
            const fixedInput = buildFcstmElkGraph(diagram, options);
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
            let baselineScreenshot: ScreenshotMetrics | null = null;
            let fixedScreenshot: ScreenshotMetrics | null = null;
            if (chrome) {
                baselineScreenshot = screenshot(
                    chrome,
                    baselineSvg,
                    baselineSvg.replace(/\.svg$/, '.png'),
                    baselineRendered.width,
                    baselineRendered.height,
                );
                fixedScreenshot = screenshot(
                    chrome,
                    fixedSvg,
                    fixedSvg.replace(/\.svg$/, '.png'),
                    fixedRendered.width,
                    fixedRendered.height,
                );
            }
            const baselineArea = (baseline.width ?? 0) * (baseline.height ?? 0);
            const fixedArea = (fixed.width ?? 0) * (fixed.height ?? 0);
            reports.push({
                fixture: fixtureName,
                direction,
                baseline: measure(baseline),
                fixed: measure(fixed),
                svg: {baseline: path.basename(baselineSvg), fixed: path.basename(fixedSvg)},
                screenshots: {baseline: baselineScreenshot, fixed: fixedScreenshot},
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
        productionPostProcess: 'smoothGraphEdges',
        terminalMinimumPx: MIN_TERMINAL_SEGMENT,
        screenshotViewport: {
            width: PREVIEW_VIEWPORT.width,
            height: PREVIEW_VIEWPORT.height,
            fitToViewMargin: PREVIEW_MARGIN,
        },
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
        outputDir,
    }, null, 2));
    if (fixedFailures.length > 0 || crossingRegressions.length > 0) {
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
