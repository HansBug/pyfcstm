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

// 8. Webview bundle (IIFE) carries the runtime that the preview actually
// executes. Verify the Vue + Naive UI shell is stitched together with the
// shared interaction policy + SVG renderer markers.
const webviewBundlePath = path.resolve(__dirname, '..', 'dist', 'preview-webview.js');
const webviewSrc = fs.existsSync(webviewBundlePath) ? fs.readFileSync(webviewBundlePath, 'utf8') : '';
check(
    'preview-webview bundle embeds the shared decidePreviewPointerAction policy',
    webviewSrc.includes('decidePreviewPointerAction')
);
check(
    'preview-webview bundle wires Ctrl/Cmd modifier into the click handler',
    webviewSrc.includes('ctrlKey') && webviewSrc.includes('metaKey')
);
check(
    'preview-webview bundle measures drag movement with Math.hypot',
    webviewSrc.includes('Math.hypot')
);
check(
    'preview-webview bundle dispatches reveal-source / set-collapsed messages',
    webviewSrc.includes('revealSource') && webviewSrc.includes('setCollapsed')
);
check(
    'preview-webview bundle uses the modifier-held class for the code-tracking cursor',
    webviewSrc.includes('modifier-held')
);
check(
    'preview-webview bundle includes the fcstm-related-hover label↔path highlight class',
    webviewSrc.includes('fcstm-related-hover')
);
check(
    'preview-webview bundle includes the fcstm-selected highlight class',
    webviewSrc.includes('fcstm-selected')
);
check(
    'preview-webview bundle has no Transition Effects card markup',
    !webviewSrc.includes('effects-card') && !webviewSrc.includes('Transition Effects')
);
check(
    'preview-webview bundle bootstraps a Vue 3 + Naive UI shell',
    webviewSrc.includes('createApp') && webviewSrc.includes('NConfigProvider')
);
check(
    'preview-webview bundle ships the toolbar / details / bottom-panel components',
    webviewSrc.includes('fcstm-toolbar') && webviewSrc.includes('fcstm-details') && webviewSrc.includes('fcstm-bottom')
);
check(
    'preview-webview SVG renderer marks the three state variants',
    webviewSrc.includes('data-fcstm-variant')
);
check(
    'preview-webview SVG renderer paints labels with a white halo (no solid rect background)',
    webviewSrc.includes('paint-order="stroke"')
);

// 9. Extension-host preview.ts no longer ships the legacy 1500-line
// inlined HTML template; it now defers to the Vue bundle.
const previewTsPath = path.resolve(__dirname, '..', 'src', 'preview.ts');
const previewTs = fs.existsSync(previewTsPath) ? fs.readFileSync(previewTsPath, 'utf8') : '';
check(
    'extension-host preview.ts no longer carries the legacy inlined webview script',
    !previewTs.includes('renderSvgFromLaidOut(') && !previewTs.includes('viewport-inner')
);
check(
    'extension-host preview.ts inlines the preview-webview Vue bundle into the HTML shell',
    previewTs.includes('loadPreviewWebviewBundle') && previewTs.includes('webviewAppScript')
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
