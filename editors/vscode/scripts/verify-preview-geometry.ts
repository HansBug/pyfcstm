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
    layout: {
        baseline: {width: number; height: number; crossings: number};
        fixed: {width: number; height: number; crossings: number};
        areaDeltaPercent: number;
    };
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

function screenshot(chrome: string, svgPath: string, pngPath: string): void {
    const htmlPath = svgPath.replace(/\.svg$/, '.html');
    const html = '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}' +
        '.wrap{padding:16px}svg{display:block}</style><div class="wrap">' +
        fs.readFileSync(svgPath, 'utf8') + '</div>';
    fs.writeFileSync(htmlPath, html);
    const result = spawnSync(chrome, [
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--virtual-time-budget=3000',
        '--window-size=1800,1400', `--screenshot=${pngPath}`, `file://${htmlPath}`,
    ], {stdio: 'pipe'});
    fs.rmSync(htmlPath, {force: true});
    if (result.status !== 0) {
        throw new Error(`Chrome screenshot failed for ${svgPath}: ${result.stderr?.toString() || ''}`);
    }
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
            fs.writeFileSync(baselineSvg, renderSvg(baseline, previewOptions).svg);
            fs.writeFileSync(fixedSvg, renderSvg(fixed, previewOptions).svg);
            if (chrome) {
                screenshot(chrome, baselineSvg, baselineSvg.replace(/\.svg$/, '.png'));
                screenshot(chrome, fixedSvg, fixedSvg.replace(/\.svg$/, '.png'));
            }
            const baselineArea = (baseline.width ?? 0) * (baseline.height ?? 0);
            const fixedArea = (fixed.width ?? 0) * (fixed.height ?? 0);
            reports.push({
                fixture: fixtureName,
                direction,
                baseline: measure(baseline),
                fixed: measure(fixed),
                svg: {baseline: path.basename(baselineSvg), fixed: path.basename(fixedSvg)},
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
        terminalMinimumPx: 18,
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
