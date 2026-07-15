'use strict';

const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const esbuild = require('esbuild');

const entry = path.resolve(__dirname, 'verify-preview-geometry.ts');
const jsfcstmEntry = path.resolve(__dirname, '../../jsfcstm/dist/diagram/index.js');
if (!fs.existsSync(jsfcstmEntry)) {
    throw new Error(`Missing ${jsfcstmEntry}; run \"cd ../jsfcstm && npm run build\" first.`);
}
for (const required of [
    path.resolve(__dirname, '..', 'dist', 'preview-webview.js'),
    path.resolve(__dirname, '..', 'dist', 'preview-webview.css'),
    path.resolve(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'),
]) {
    if (!fs.existsSync(required)) {
        throw new Error(`Missing ${required}; run \"npm run compile\" in editors/vscode first.`);
    }
}
const output = path.join(os.tmpdir(), `fcstm-preview-geometry-${process.pid}.cjs`);
const repoRoot = path.resolve(__dirname, '..', '..', '..');
const freshnessChecks = [
    {
        label: 'jsfcstm diagram bundle',
        artifact: jsfcstmEntry,
        sources: [
            path.join(repoRoot, 'editors/jsfcstm/src/diagram/elk-graph.ts'),
            path.join(repoRoot, 'editors/jsfcstm/src/diagram/index.ts'),
        ],
    },
    {
        label: 'preview webview bundle',
        artifact: path.resolve(__dirname, '..', 'dist', 'preview-webview.js'),
        sources: [
            path.resolve(__dirname, '..', 'src/preview-webview/App.vue'),
            path.resolve(__dirname, '..', 'src/preview-webview/components/Stage.vue'),
            path.resolve(__dirname, '..', 'src/preview-webview/layout.ts'),
            path.resolve(__dirname, '..', 'src/preview-webview/render/edge-smoother.ts'),
            path.resolve(__dirname, '..', 'src/preview-webview/render/svg.ts'),
        ],
    },
];
for (const check of freshnessChecks) {
    const artifactMtime = fs.statSync(check.artifact).mtimeMs;
    const newestSource = Math.max(...check.sources.map(source => fs.statSync(source).mtimeMs));
    if (artifactMtime + 1000 < newestSource) {
        throw new Error(
            `${check.label} is older than its source inputs; rebuild before running the geometry gate: ` +
            `${JSON.stringify({artifact: check.artifact, artifactMtime, newestSource})}`
        );
    }
}
const gitHead = spawnSync('git', ['rev-parse', 'HEAD'], {cwd: repoRoot, encoding: 'utf8'}).stdout.trim();
const expectedHead = process.env.PYFCSTM_GEOMETRY_EXPECTED_HEAD;
if (expectedHead && gitHead !== expectedHead) {
    throw new Error(`geometry gate is at ${gitHead || '<unknown>'}, expected ${expectedHead}`);
}
if (gitHead) process.env.PYFCSTM_GEOMETRY_GIT_HEAD = gitHead;
// This command is the evidence-producing right-pane gate.  A missing browser
// must fail closed instead of silently reducing the run to raw ELK geometry;
// callers doing a geometry-only smoke test may opt out explicitly.
if (process.env.PYFCSTM_ALLOW_NO_PREVIEW_BROWSER !== '1') {
    process.env.PYFCSTM_REQUIRE_PREVIEW_BROWSER = '1';
}
try {
    esbuild.buildSync({
        entryPoints: [entry],
        bundle: true,
        platform: 'node',
        format: 'cjs',
        target: 'node16',
        outfile: output,
        external: ['vscode'],
        logLevel: 'warning',
    });
    require(output);
} finally {
    fs.rmSync(output, {force: true});
}
