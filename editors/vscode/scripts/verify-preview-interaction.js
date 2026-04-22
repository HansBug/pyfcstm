#!/usr/bin/env node
/*
 * Verifies the FCSTM preview webview pointer interaction contract:
 *   - drag past the threshold cancels any click (pan, not click)
 *   - plain click on chevron toggles collapse
 *   - plain click on a state / transition / label → select + show details
 *   - plain click on empty canvas clears the current selection
 *   - Ctrl/Cmd + click on an element with a source range reveals it
 *
 * The policy lives in src/preview-interaction.ts so both the inlined
 * webview script and this Node test consume the same contract.
 */

const fs = require('fs');
const path = require('path');

const {
    decidePreviewPointerAction,
    PREVIEW_DRAG_THRESHOLD_PX,
} = require('../out/preview-interaction.js');

const checkpoints = [];
function check(label, cond) {
    checkpoints.push({label, ok: Boolean(cond)});
    console.log(`${cond ? '\x1b[32m✅\x1b[0m' : '\x1b[31m❌\x1b[0m'} ${label}`);
}

// 1. Drag past threshold → click suppressed.
for (const kind of ['state', 'composite-state', 'transition', 'transition-label', 'chevron', null]) {
    check(
        `drag past threshold cancels click on ${kind === null ? '<empty>' : kind}`,
        decidePreviewPointerAction({kind, modifier: false, dragMovedPx: PREVIEW_DRAG_THRESHOLD_PX + 1, hasRange: true}).type === 'none'
    );
}

// 2. Plain click on chevron toggles collapse; Ctrl+click reveals source
check(
    'plain click on chevron toggles collapse',
    decidePreviewPointerAction({kind: 'chevron', modifier: false, dragMovedPx: 0, hasRange: true}).type === 'toggleCollapse'
);
check(
    'Ctrl+click on chevron reveals source (not toggle)',
    decidePreviewPointerAction({kind: 'chevron', modifier: true, dragMovedPx: 0, hasRange: true}).type === 'revealSource'
);

// 3. Plain click on state / transition / label → select (the new behaviour).
for (const kind of ['state', 'composite-state', 'transition', 'transition-label', 'pseudo-init', 'pseudo-exit']) {
    check(
        `plain click on ${kind} selects it (and opens Details)`,
        decidePreviewPointerAction({kind, modifier: false, dragMovedPx: 0, hasRange: true}).type === 'select'
    );
}

// 4. Plain click on empty canvas clears selection.
check(
    'plain click on empty canvas clears selection',
    decidePreviewPointerAction({kind: null, modifier: false, dragMovedPx: 0, hasRange: false}).type === 'clearSelection'
);

// 5. Ctrl/Cmd + click reveals source when element has a range.
for (const kind of ['state', 'composite-state', 'transition', 'transition-label', 'chevron']) {
    check(
        `Ctrl/Cmd+click on ${kind} with range reveals source`,
        decidePreviewPointerAction({kind, modifier: true, dragMovedPx: 0, hasRange: true}).type === 'revealSource'
    );
}

// 6. Ctrl/Cmd + click without a range is a no-op (can't jump).
check(
    'Ctrl/Cmd+click on state without range does nothing',
    decidePreviewPointerAction({kind: 'state', modifier: true, dragMovedPx: 0, hasRange: false}).type === 'none'
);
check(
    'Ctrl/Cmd+click on pseudo-init without range does nothing',
    decidePreviewPointerAction({kind: 'pseudo-init', modifier: true, dragMovedPx: 0, hasRange: false}).type === 'none'
);

// 7. Threshold sanity.
check(
    'drag threshold is a small positive pixel count',
    typeof PREVIEW_DRAG_THRESHOLD_PX === 'number' && PREVIEW_DRAG_THRESHOLD_PX > 0 && PREVIEW_DRAG_THRESHOLD_PX < 20
);

// 8. Inlined webview copy tracks the policy.
const previewSrc = fs.readFileSync(path.resolve(__dirname, '..', 'out', 'preview.js'), 'utf8');
check(
    'preview.js embeds decidePreviewPointerAction inside the webview script',
    previewSrc.includes('function decidePreviewPointerAction')
);
check(
    'preview.js embeds SELECTABLE_KINDS in the webview click handler',
    previewSrc.includes('SELECTABLE_KINDS')
);
check(
    'preview.js handles select and clearSelection actions',
    previewSrc.includes("'select'") && previewSrc.includes("'clearSelection'")
);
check(
    'preview.js PREVIEW_DRAG_THRESHOLD_PX constant is embedded',
    previewSrc.includes('PREVIEW_DRAG_THRESHOLD_PX')
);
check(
    'preview.js checks both ctrlKey and metaKey for reveal-source',
    previewSrc.includes('ev.ctrlKey') && previewSrc.includes('ev.metaKey')
);
check(
    'preview.js tracks dragMovedPx via Math.hypot',
    previewSrc.includes('Math.hypot(dx, dy)')
);
check(
    'preview.js no longer short-circuits mousedown on data-fcstm-kind targets',
    !previewSrc.match(/mousedown[\s\S]{0,200}closest\(['"]\[data-fcstm-kind\]['"]\)[\s\S]{0,40}return/)
);
check(
    'preview.js toggles modifier-held class on keydown/keyup',
    previewSrc.includes('modifier-held') && previewSrc.includes('keydown') && previewSrc.includes('keyup')
);
check(
    'preview.js still posts revealSource messages to the extension host',
    previewSrc.includes("type: 'revealSource'") || previewSrc.includes('type: "revealSource"')
);
check(
    'preview.js renders Details card UI (state actions, transition event/guard/effect)',
    previewSrc.includes('renderStateDetails') && previewSrc.includes('renderTransitionDetails')
);
check(
    'preview.js adds fcstm-selected class to highlight current selection',
    previewSrc.includes('fcstm-selected')
);
check(
    'preview.js exposes Reveal-source button in the Details header',
    previewSrc.includes('details-reveal')
);
check(
    'preview.js draws transition labels with a white halo (paint-order stroke) — no more solid rect background',
    previewSrc.includes('paint-order="stroke"') && previewSrc.includes('stroke-width="3"')
);
check(
    'preview.js distinguishes leaf / composite / pseudo states with data-fcstm-variant',
    previewSrc.includes('data-fcstm-variant')
);
check(
    'preview.js no longer renders leaf-state event/action detail list (those live in the Details panel)',
    !/meta\.eventLabels \|\| \[\]\)\.concat\(meta\.actionLabels/.test(previewSrc)
);

const passed = checkpoints.filter(c => c.ok).length;
const failed = checkpoints.length - passed;
console.log('');
console.log('\x1b[36mSummary\x1b[0m');
console.log('\x1b[36m-------\x1b[0m');
console.log(`Total checkpoints: ${checkpoints.length}`);
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
if (failed > 0) {
    console.error('\x1b[31mPreview interaction verification failed.\x1b[0m');
    process.exitCode = 1;
} else {
    console.log('\x1b[32mAll preview interaction checkpoints passed.\x1b[0m');
}
