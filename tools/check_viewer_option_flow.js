/*
 * Hold the standalone viewer's option flow: what the document asked for, what
 * the reader chose since, and what the two resolve to.
 *
 * `resolveFcstmDiagramPreviewOptions` fills every key from the detail preset
 * and lets an explicit value beat it, so the resolved set must never be fed
 * back in: doing so freezes each default as a choice. Two defects came from
 * that in successive rounds -- choosing "hide" left the effect mode stuck
 * there, and a reader's first click dropped the `detailLevel` and `direction`
 * the document was saved with, neither of which has a control to restore.
 *
 * There is no test suite under `editors/vscode/`, which is how both reached a
 * release. This is a maintenance gate rather than a unit test: it drives the
 * real builder through the sequence a reader performs.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const {createRequire} = require('module');

const ROOT = path.resolve(__dirname, '..');
// esbuild from the extension, the same one `build_viewer.js` uses to produce
// the bundled viewer. ts-node would be the obvious choice and is the wrong one:
// it lives in the jsfcstm devDependencies, and the job that runs this gate
// installs the extension's packages and not those -- a difference this gate
// went red on the first time it reached CI.
const requireFromVscode = createRequire(
    path.join(ROOT, 'editors/vscode', 'package.json'));
const esbuild = requireFromVscode('esbuild');

const bundleDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pyfcstm-option-flow-'));
const bundlePath = path.join(bundleDir, 'standalone-data.cjs');
esbuild.buildSync({
    entryPoints: [path.join(ROOT, 'editors/vscode/src/preview-webview/standalone-data.ts')],
    outfile: bundlePath,
    bundle: true,
    platform: 'node',
    format: 'cjs',
    target: 'es2019',
    logLevel: 'silent',
});
const {buildStandaloneState} = require(bundlePath);

const failures = [];
let checks = 0;
const check = (label, actual, expected) => {
    checks += 1;
    if (actual !== expected) failures.push(`${label}: expected ${expected}, got ${actual}`);
};

// Exactly the shape the Python side writes: sparse, the eight keys a preset
// governs left out, carrying the author's own two.
const diagram = {
    machineName: 'M', summary: {}, variables: [], eventLegend: [],
    rootState: {
        qualifiedName: 'R', name: 'R', displayName: '', pseudo: false,
        events: [], actions: [], transitions: [], children: [], range: null,
    },
};
let state = buildStandaloneState({
    standalone: true, standaloneDiagram: diagram, collapsedStateIds: [],
    title: '', filePath: '',
    previewOptions: {detailLevel: 'full', direction: 'LR'},
});
check('detail level after load', state.previewOptions.detailLevel, 'full');
check('direction after load', state.previewOptions.direction, 'LR');

// One unrelated click must not cost the document its own settings.
state = buildStandaloneState({...state, optionOverrides: {showTransitionGuards: false}});
check('detail level after one click', state.previewOptions.detailLevel, 'full');
check('direction after one click', state.previewOptions.direction, 'LR');
check('the click itself', state.previewOptions.showTransitionGuards, false);

// `hide` clamps the effects flag; choosing a mode afterwards has to work.
state = buildStandaloneState({
    ...state,
    optionOverrides: {...state.optionOverrides, transitionEffectMode: 'hide'},
});
check('effect mode set to hide', state.previewOptions.transitionEffectMode, 'hide');
state = buildStandaloneState({
    ...state,
    optionOverrides: {...state.optionOverrides, transitionEffectMode: 'note'},
});
check('effect mode back to note', state.previewOptions.transitionEffectMode, 'note');

// Collapsing a state touches no option.
state = buildStandaloneState({...state, collapsedStateIds: ['R']}, ['R']);
check('detail level after collapse', state.previewOptions.detailLevel, 'full');
check('effect mode after collapse', state.previewOptions.transitionEffectMode, 'note');
check('guards after collapse', state.previewOptions.showTransitionGuards, false);

fs.rmSync(bundleDir, {recursive: true, force: true});

if (failures.length > 0) {
    for (const failure of failures) console.error(`viewer option flow: ${failure}`);
    process.exit(1);
}
console.log(`viewer option flow: ${checks} checks passed`);
