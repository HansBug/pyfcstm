/**
 * Visual regression harness for the ELK-based FCSTM preview.
 *
 * Reads every ``.fcstm`` fixture under ``test/fixtures/visual`` and, for
 * each of the three detail levels (minimal / normal / full), runs the
 * full extension-side pipeline (parser → diagram IR → elk graph → elkjs
 * layout → svg-renderer) and rasterises the SVG via headless Chrome.
 *
 * The harness is intentionally side-effect free except for writing PNGs
 * under ``test/snapshots/visual`` and a small ``index.html`` for human
 * review. It exits non-zero if any fixture fails to render.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const {spawnSync} = require('child_process');
const ELK = require('elkjs');

const {
    buildFcstmDiagramFromDocument,
    buildFcstmElkGraph,
    renderFcstmDiagramSvg,
    resolveFcstmDiagramPreviewOptions,
} = require('../dist');

const FIXTURE_DIR = path.resolve(__dirname, '..', 'test', 'fixtures', 'visual');
const SNAPSHOT_DIR = path.resolve(__dirname, '..', 'test', 'snapshots', 'visual');

class InMemoryDoc {
    constructor(filePath) {
        this._filePath = filePath;
        this._text = fs.readFileSync(filePath, 'utf8');
        this._lines = this._text.split('\n');
        this.lineCount = this._lines.length;
        const uri = 'file://' + filePath;
        this.uri = {scheme: 'file', fsPath: filePath, path: filePath, toString: () => uri};
        this.fileName = filePath;
        this.languageId = 'fcstm';
    }
    getText() { return this._text; }
    lineAt(line) {
        const text = this._lines[line] || '';
        return {text, range: {start: {line, character: 0}, end: {line, character: text.length}}};
    }
}

function locateChrome() {
    for (const candidate of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
        const result = spawnSync('which', [candidate]);
        if (result.status === 0 && result.stdout.toString().trim()) {
            return result.stdout.toString().trim();
        }
    }
    return null;
}

async function renderFixture(elk, fixturePath, detail, outDir) {
    const name = path.basename(fixturePath, '.fcstm');
    const doc = new InMemoryDoc(fixturePath);
    const diagram = await buildFcstmDiagramFromDocument(doc);
    if (!diagram) {
        throw new Error(`buildFcstmDiagramFromDocument returned null for ${fixturePath}`);
    }
    const options = resolveFcstmDiagramPreviewOptions(detail);
    const graph = buildFcstmElkGraph(diagram, options);
    const laidOut = await elk.layout(graph);
    const svg = renderFcstmDiagramSvg(laidOut, options);
    const svgPath = path.join(outDir, `${name}.${detail}.svg`);
    fs.writeFileSync(svgPath, svg);
    return {svgPath, svg, laidOut, name};
}

function screenshotSvg(chromeBin, svgPath, pngPath, viewport = {width: 1600, height: 1400}) {
    // Render the SVG inside a minimal HTML wrapper so Chrome lays it out
    // at natural size without forcing a scroll bar.
    const htmlPath = svgPath.replace(/\.svg$/, '.html');
    const relSvg = path.basename(svgPath);
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>visual</title>
<style>
  html,body{margin:0;padding:0;background:#ffffff;font-family:'JetBrains Mono',monospace}
  .wrap{padding:16px;display:flex;justify-content:flex-start;align-items:flex-start}
  .wrap object{display:block;max-width:none}
  .wrap svg{display:block;max-width:none}
</style>
</head><body><div class="wrap"><object type="image/svg+xml" data="${relSvg}"></object></div></body></html>`;
    fs.writeFileSync(htmlPath, html);
    const args = [
        '--headless=new',
        '--disable-gpu',
        '--hide-scrollbars',
        '--virtual-time-budget=4000',
        `--window-size=${viewport.width},${viewport.height}`,
        `--screenshot=${pngPath}`,
        `file://${htmlPath}`,
    ];
    const result = spawnSync(chromeBin, args, {stdio: 'pipe'});
    if (result.status !== 0) {
        throw new Error(`chrome failed for ${svgPath}: ${result.stderr && result.stderr.toString()}`);
    }
    fs.unlinkSync(htmlPath);
    return pngPath;
}

async function main() {
    const chrome = locateChrome();
    if (!chrome) {
        console.error('no google-chrome/chromium found on PATH; skipping screenshots');
    }
    if (!fs.existsSync(FIXTURE_DIR)) {
        console.error(`fixtures directory not found: ${FIXTURE_DIR}`);
        process.exit(1);
    }
    fs.mkdirSync(SNAPSHOT_DIR, {recursive: true});

    const elk = new ELK();
    const fixtures = fs.readdirSync(FIXTURE_DIR).filter(f => f.endsWith('.fcstm')).sort();
    if (fixtures.length === 0) {
        console.error('no fixtures found');
        process.exit(1);
    }

    const detailLevels = ['minimal', 'normal', 'full'];
    const report = [];

    for (const fixture of fixtures) {
        const fixturePath = path.join(FIXTURE_DIR, fixture);
        for (const detail of detailLevels) {
            const {svgPath, svg, laidOut} = await renderFixture(elk, fixturePath, detail, SNAPSHOT_DIR);
            const pngPath = svgPath.replace(/\.svg$/, '.png');
            if (chrome) {
                screenshotSvg(chrome, svgPath, pngPath);
            }
            report.push({
                fixture,
                detail,
                svg: path.basename(svgPath),
                png: path.basename(pngPath),
                width: laidOut.width,
                height: laidOut.height,
                size: svg.length,
            });
            console.log(`[${detail}] ${fixture} -> ${path.basename(svgPath)} (${laidOut.width}x${laidOut.height}, svg ${svg.length}B)`);
        }
    }

    // Also write a compact index.html for human review / comparison.
    const indexLines = [
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>FCSTM visual snapshots</title>',
        '<style>',
        'body{font-family:system-ui,sans-serif;margin:24px;background:#f8fafc;color:#0f172a}',
        'h1{margin-top:0}',
        '.row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}',
        '.col{background:#ffffff;border:1px solid #cbd5e1;border-radius:8px;padding:12px;flex:1;min-width:300px}',
        '.col h3{margin:0 0 8px;font-size:14px;color:#475569}',
        '.col img{width:100%;border:1px solid #e2e8f0;border-radius:4px}',
        '</style>',
        `</head><body><h1>FCSTM visual snapshots (${new Date().toISOString()})</h1>`,
    ];
    const byFixture = {};
    for (const entry of report) {
        byFixture[entry.fixture] = byFixture[entry.fixture] || [];
        byFixture[entry.fixture].push(entry);
    }
    for (const fixture of Object.keys(byFixture).sort()) {
        indexLines.push(`<h2>${fixture}</h2><div class="row">`);
        for (const entry of byFixture[fixture]) {
            indexLines.push(
                `<div class="col"><h3>${entry.detail} (${entry.width}×${entry.height})</h3>` +
                (fs.existsSync(path.join(SNAPSHOT_DIR, entry.png))
                    ? `<img src="${entry.png}" alt="${entry.fixture} ${entry.detail}"/>`
                    : `<em>screenshot unavailable</em>`) +
                `</div>`
            );
        }
        indexLines.push('</div>');
    }
    indexLines.push('</body></html>');
    fs.writeFileSync(path.join(SNAPSHOT_DIR, 'index.html'), indexLines.join('\n'));
    fs.writeFileSync(path.join(SNAPSHOT_DIR, 'report.json'), JSON.stringify(report, null, 2));
    console.log(`wrote ${report.length} snapshots + index.html to ${SNAPSHOT_DIR}`);
}

main().catch(err => {
    console.error(err.stack || err.message);
    process.exit(1);
});
