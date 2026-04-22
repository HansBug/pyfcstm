#!/usr/bin/env node
/*
 * Verifies the FCSTM preview webview pointer interaction contract:
 *   - plain click pans (no revealSource) when drag movement > threshold
 *   - plain click on a chevron toggles collapse, not revealSource
 *   - plain click on a state does nothing (prevents click-stealing)
 *   - Ctrl/Cmd + click on an element with range reveals the source
 *
 * The decision helper lives at src/preview-interaction.ts so both the
 * webview script (inlined copy) and this test consume the same policy.
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

// 1. Drag past threshold → plain click suppressed, regardless of target.
check(
    'drag past threshold cancels click on state (plain)',
    decidePreviewPointerAction({kind: 'state', modifier: false, dragMovedPx: PREVIEW_DRAG_THRESHOLD_PX + 1, hasRange: true}).type === 'none'
);
check(
    'drag past threshold cancels click on state (modifier held)',
    decidePreviewPointerAction({kind: 'state', modifier: true, dragMovedPx: PREVIEW_DRAG_THRESHOLD_PX + 1, hasRange: true}).type === 'none'
);
check(
    'drag past threshold cancels click on chevron',
    decidePreviewPointerAction({kind: 'chevron', modifier: false, dragMovedPx: PREVIEW_DRAG_THRESHOLD_PX + 1, hasRange: true}).type === 'none'
);

// 2. Plain click on chevron within threshold → toggleCollapse.
check(
    'plain click on chevron toggles collapse',
    decidePreviewPointerAction({kind: 'chevron', modifier: false, dragMovedPx: 0, hasRange: true}).type === 'toggleCollapse'
);
check(
    'plain click on chevron toggles collapse even with stale 1-2px jitter',
    decidePreviewPointerAction({kind: 'chevron', modifier: false, dragMovedPx: PREVIEW_DRAG_THRESHOLD_PX - 1, hasRange: true}).type === 'toggleCollapse'
);

// 3. Plain click on non-chevron elements does nothing (reveal is opt-in).
for (const kind of ['state', 'composite-state', 'transition', 'transition-label', 'pseudo-init', 'pseudo-exit']) {
    check(
        `plain click on ${kind} is a no-op (prevents click-stealing from pan)`,
        decidePreviewPointerAction({kind, modifier: false, dragMovedPx: 0, hasRange: true}).type === 'none'
    );
}

// 4. Ctrl/Cmd + click reveals source when element has a source range.
for (const kind of ['state', 'composite-state', 'transition', 'transition-label', 'chevron']) {
    check(
        `Ctrl/Cmd+click on ${kind} with range reveals source`,
        decidePreviewPointerAction({kind, modifier: true, dragMovedPx: 0, hasRange: true}).type === 'revealSource'
    );
}

// 5. Ctrl/Cmd + click on elements without a range is a no-op.
check(
    'Ctrl/Cmd+click on state without range does nothing',
    decidePreviewPointerAction({kind: 'state', modifier: true, dragMovedPx: 0, hasRange: false}).type === 'none'
);
check(
    'Ctrl/Cmd+click on pseudo-init (no range) does nothing',
    decidePreviewPointerAction({kind: 'pseudo-init', modifier: true, dragMovedPx: 0, hasRange: false}).type === 'none'
);

// 6. Clicks outside any data-fcstm-kind element are ignored.
check(
    'null kind (click on empty viewport) is ignored',
    decidePreviewPointerAction({kind: null, modifier: true, dragMovedPx: 0, hasRange: false}).type === 'none'
);

// 7. Threshold constant is sane.
check(
    'drag threshold is a small positive pixel count',
    typeof PREVIEW_DRAG_THRESHOLD_PX === 'number' && PREVIEW_DRAG_THRESHOLD_PX > 0 && PREVIEW_DRAG_THRESHOLD_PX < 20
);

// 8. The webview HTML template wires up modifier-aware click and drag threshold.
//    This keeps the inlined copy in preview.ts in sync with the helper policy.
const previewSrc = fs.readFileSync(path.resolve(__dirname, '..', 'out', 'preview.js'), 'utf8');
check(
    'preview.js embeds decidePreviewPointerAction inside the webview script',
    previewSrc.includes('function decidePreviewPointerAction')
);
check(
    'preview.js uses PREVIEW_DRAG_THRESHOLD_PX in the webview script',
    previewSrc.includes('PREVIEW_DRAG_THRESHOLD_PX')
);
check(
    'preview.js checks ctrlKey or metaKey for reveal-source',
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
    previewSrc.includes('modifier-held') && previewSrc.includes("keydown") && previewSrc.includes('keyup')
);
check(
    'preview.js still posts revealSource messages to the extension host',
    previewSrc.includes("type: 'revealSource'") || previewSrc.includes('type: "revealSource"')
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
