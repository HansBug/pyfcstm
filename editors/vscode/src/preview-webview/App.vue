<script setup lang="ts">
import {computed, onMounted, onUnmounted, provide, ref} from 'vue';
import {
    NConfigProvider, NMessageProvider, darkTheme,
} from 'naive-ui';
import Toolbar from './components/Toolbar.vue';
import OptionsBar from './components/OptionsBar.vue';
import Stage from './components/Stage.vue';
import DetailsPanel from './components/DetailsPanel.vue';
import BottomPanels from './components/BottomPanels.vue';
import DiagnosticsCard from './components/DiagnosticsCard.vue';
import {bridge} from './composables/useBridge';
import type {
    PreviewWebviewState, SelectionRef, PreviewResolvedOptions,
    TextRange, PreviewStateDetail, PreviewTransitionDetail,
} from './types';
import type {PaletteId, PaletteMode} from './render/palette';

type ColorMode = 'light' | 'dark' | 'auto';
const STORAGE_KEY_PALETTE = 'fcstm.preview.palette';
const STORAGE_KEY_MODE = 'fcstm.preview.mode';
function readStorage(key: string): string | null {
    try { return typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null; } catch { return null; }
}
function writeStorage(key: string, value: string) {
    try { if (typeof localStorage !== 'undefined') localStorage.setItem(key, value); } catch { /* no-op */ }
}

// Initial state is serialised into window by the HTML shell.
declare const __FCSTM_INITIAL_STATE__: PreviewWebviewState;
const initialState: PreviewWebviewState = (window as unknown as {
    __FCSTM_INITIAL_STATE__?: PreviewWebviewState;
}).__FCSTM_INITIAL_STATE__ || (typeof __FCSTM_INITIAL_STATE__ !== 'undefined' ? __FCSTM_INITIAL_STATE__ : {
    title: 'FCSTM Preview',
    filePath: '',
    previewOptions: {
        detailLevel: 'normal',
        direction: 'TB',
        showVariableDefinitions: true,
        showEvents: true,
        showTransitionGuards: true,
        showTransitionEffects: true,
        transitionEffectMode: 'note',
        eventVisualizationMode: 'both',
        showStateEvents: true,
        showStateActions: false,
        eventNameFormat: ['extra_name', 'relpath'],
        maxStateEvents: 4,
        maxStateActions: 4,
        maxTransitionEffectLines: 8,
        maxLabelLength: 160,
    },
    collapsedStateIds: [],
    emptyTitle: 'FCSTM Preview',
    emptyMessage: 'Preparing preview...',
    summary: [],
    variables: [],
    sharedEvents: [],
    diagnostics: [],
    status: 'ok',
    statusText: 'Loading preview',
});

const state = ref<PreviewWebviewState>(initialState);
const selection = ref<SelectionRef>(null);
const vscode = bridge();

// Palette + colour-mode state. Mode can be 'auto' (follow VSCode), or
// user-overridden to a fixed 'light' / 'dark'. Palette picks the named
// skin (default / nord / solarized / darcula).
const palette = ref<PaletteId>(((readStorage(STORAGE_KEY_PALETTE) as PaletteId) || 'default'));
const colorMode = ref<ColorMode>(((readStorage(STORAGE_KEY_MODE) as ColorMode) || 'auto'));

function applyMode(value: ColorMode) {
    colorMode.value = value;
    writeStorage(STORAGE_KEY_MODE, value);
    syncBodyClasses();
}
function applyPalette(value: PaletteId) {
    palette.value = value;
    writeStorage(STORAGE_KEY_PALETTE, value);
    syncBodyClasses();
}

// Apply .fcstm-mode-dark / .fcstm-mode-light / .fcstm-palette-<name>
// classes to <body> so both Vue-component CSS and Naive UI can see
// the current preferences without threading props everywhere.
function detectVscodeDark(): boolean {
    if (typeof document === 'undefined') return false;
    return document.body.classList.contains('vscode-dark') ||
        document.body.classList.contains('vscode-high-contrast');
}
function syncBodyClasses() {
    if (typeof document === 'undefined') return;
    const body = document.body;
    body.classList.remove('fcstm-mode-light', 'fcstm-mode-dark');
    const effective = colorMode.value === 'auto'
        ? (detectVscodeDark() ? 'dark' : 'light')
        : colorMode.value;
    body.classList.add(`fcstm-mode-${effective}`);
    for (const cls of Array.from(body.classList)) {
        if (cls.startsWith('fcstm-palette-')) body.classList.remove(cls);
    }
    body.classList.add(`fcstm-palette-${palette.value}`);
}

const effectiveMode = computed<PaletteMode>(() => {
    if (colorMode.value === 'light') return 'light';
    if (colorMode.value === 'dark') return 'dark';
    return detectVscodeDark() ? 'dark' : 'light';
});

function setState(next: PreviewWebviewState) {
    state.value = next;
    vscode.setState(next);
}

function rangeLength(range: TextRange): number {
    const lineSpan = range.end.line - range.start.line;
    if (lineSpan > 0) {
        return lineSpan * 100000 + range.end.character;
    }
    return Math.max(0, range.end.character - range.start.character);
}

function positionWithin(range: TextRange, target: TextRange): boolean {
    // ``target`` is typically the editor cursor range (often zero width).
    // A range "contains" the target when the target start is not before
    // the range start and the target end is not after the range end.
    const startOk = target.start.line > range.start.line
        || (target.start.line === range.start.line
            && target.start.character >= range.start.character);
    const endOk = target.end.line < range.end.line
        || (target.end.line === range.end.line
            && target.end.character <= range.end.character);
    return startOk && endOk;
}

function findInnermostStateForRange(
    states: PreviewStateDetail[] | undefined,
    target: TextRange
): PreviewStateDetail | null {
    if (!states) return null;
    let best: PreviewStateDetail | null = null;
    let bestLength = Number.POSITIVE_INFINITY;
    for (const state of states) {
        const range = state.sourceRange;
        if (!range) continue;
        if (!positionWithin(range, target)) continue;
        const length = rangeLength(range);
        if (length < bestLength) {
            best = state;
            bestLength = length;
        }
    }
    return best;
}

function findTransitionForRange(
    transitions: PreviewTransitionDetail[] | undefined,
    target: TextRange
): PreviewTransitionDetail | null {
    if (!transitions) return null;
    let best: PreviewTransitionDetail | null = null;
    let bestLength = Number.POSITIVE_INFINITY;
    for (const transition of transitions) {
        const range = transition.sourceRange;
        if (!range) continue;
        if (!positionWithin(range, target)) continue;
        const length = rangeLength(range);
        if (length < bestLength) {
            best = transition;
            bestLength = length;
        }
    }
    return best;
}

function selectionForRange(
    payload: PreviewWebviewState['payload'] | undefined,
    target: TextRange
): SelectionRef {
    if (!payload) return null;
    // Prefer a transition hit because transitions usually have tighter
    // ranges than their enclosing state. Fall back to the innermost state
    // covering the cursor.
    const transition = findTransitionForRange(payload.transitions, target);
    if (transition) {
        return {kind: 'transition', id: transition.transitionId};
    }
    const state = findInnermostStateForRange(payload.states, target);
    if (state) {
        if (state.kind === 'composite') {
            return {kind: 'composite-state', id: state.qualifiedName};
        }
        if (state.kind === 'pseudoState') {
            return {kind: 'state', id: state.qualifiedName};
        }
        return {kind: 'state', id: state.qualifiedName};
    }
    return null;
}

function applyActiveRange(range: TextRange | null) {
    if (!range) {
        selection.value = null;
        return;
    }
    const next = selectionForRange(state.value.payload, range);
    selection.value = next;
}

function onMessage(ev: MessageEvent) {
    const data = ev.data as unknown;
    if (data && typeof data === 'object') {
        const maybeCue = data as {type?: string};
        if (maybeCue.type === 'setActiveRange') {
            const cue = maybeCue as {type: 'setActiveRange'; range: TextRange | null};
            applyActiveRange(cue.range);
            return;
        }
    }
    setState(data as PreviewWebviewState);
}

let themeObserver: MutationObserver | null = null;

onMounted(() => {
    window.addEventListener('message', onMessage);
    const stored = vscode.getState();
    if (stored) {
        state.value = stored;
    }
    syncBodyClasses();
    if (typeof MutationObserver !== 'undefined') {
        // Only react to VSCode-owned theme class flips (vscode-dark /
        // vscode-high-contrast). Reacting to *any* body-class change
        // created a feedback loop with our own fcstm-palette-* /
        // fcstm-mode-* writes, which pinned the CPU at 100% and
        // eventually took VSCode down when the user toggled Palette /
        // Mode a few times.
        const isDark = (cls: string) => /\bvscode-dark\b|\bvscode-high-contrast\b/.test(cls);
        themeObserver = new MutationObserver((mutations) => {
            for (const m of mutations) {
                if (m.type !== 'attributes' || m.attributeName !== 'class') continue;
                const prev = (m.oldValue as string | null) || '';
                const cur = document.body.className;
                if (isDark(prev) !== isDark(cur)) {
                    syncBodyClasses();
                    return;
                }
            }
        });
        themeObserver.observe(document.body, {
            attributes: true,
            attributeFilter: ['class'],
            attributeOldValue: true,
        });
    }
});

onUnmounted(() => {
    window.removeEventListener('message', onMessage);
    themeObserver?.disconnect();
    themeObserver = null;
});

// Provide selection to nested components that need to sync with it.
provide('selection', selection);
provide('state', state);

function patchOptions(options: Partial<PreviewResolvedOptions>) {
    vscode.postMessage({type: 'patchOptions', options});
}

function toggleCollapse(id: string) {
    const set = new Set(state.value.collapsedStateIds || []);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    vscode.postMessage({type: 'setCollapsed', collapsed: Array.from(set)});
}

function revealSource(range: {start: {line: number; character: number}; end: {line: number; character: number}}) {
    vscode.postMessage({type: 'revealSource', range});
}

function setLayoutMode(mode: 'side' | 'alone') {
    vscode.postMessage({type: 'setLayoutMode', mode});
}

function exportSvg(svg: string) {
    vscode.postMessage({type: 'exportSvg', svg});
}

function exportPng(base64: string) {
    vscode.postMessage({type: 'exportPng', base64});
}

function exportError(message: string) {
    vscode.postMessage({type: 'exportError', message});
}

// Naive UI follows the effective mode (user override wins over auto).
const naiveTheme = computed(() => effectiveMode.value === 'dark' ? darkTheme : null);
</script>

<template>
    <n-config-provider :theme="naiveTheme" abstract>
        <n-message-provider>
            <div class="fcstm-preview-shell">
                <Toolbar
                    :state="state"
                    @set-layout-mode="setLayoutMode"
                    @export-svg="exportSvg"
                    @export-png="exportPng"
                    @export-error="exportError"
                />
                <OptionsBar
                    :options="state.previewOptions"
                    :palette="palette"
                    :color-mode="colorMode"
                    @patch="patchOptions"
                    @palette="applyPalette"
                    @color-mode="applyMode"
                />
                <Stage
                    :state="state"
                    :selection="selection"
                    :palette="palette"
                    :mode="effectiveMode"
                    @select="(sel: SelectionRef) => (selection = sel)"
                    @toggle-collapse="toggleCollapse"
                    @reveal-source="revealSource"
                />
                <DetailsPanel
                    :state="state"
                    :selection="selection"
                    @reveal-source="revealSource"
                    @select="(sel: SelectionRef) => (selection = sel)"
                />
                <DiagnosticsCard :diagnostics="state.diagnostics" />
                <BottomPanels
                    :variables="state.variables"
                    :shared-events="state.sharedEvents"
                />
            </div>
        </n-message-provider>
    </n-config-provider>
</template>

<style>
:root {
    color-scheme: light dark;
    --fcstm-surface: color-mix(in srgb, var(--vscode-editor-background, #fff) 86%, #e6f1fb 14%);
    --fcstm-surface-raised: color-mix(in srgb, var(--vscode-editor-background, #fff) 78%, #ffffff 22%);
    --fcstm-border: rgba(94, 140, 194, 0.45);
    --fcstm-border-soft: rgba(94, 140, 194, 0.22);
    --fcstm-muted: var(--vscode-descriptionForeground, #6a7280);
    --fcstm-fg: var(--vscode-editor-foreground, #1f2937);
    --fcstm-accent: #2d6aa8;
    --fcstm-warning: #b7791f;
    --fcstm-error: #b33a3a;
    --fcstm-mono: "JetBrains Mono", "Fira Code", Consolas, monospace;
}

body.vscode-dark,
body.vscode-high-contrast,
body.fcstm-mode-dark {
    --fcstm-surface: color-mix(in srgb, var(--vscode-editor-background, #1e1e1e) 90%, #2c3e52 10%);
    --fcstm-surface-raised: color-mix(in srgb, var(--vscode-editor-background, #1e1e1e) 82%, #3a4f66 18%);
    --fcstm-border: rgba(133, 172, 212, 0.38);
    --fcstm-border-soft: rgba(133, 172, 212, 0.22);
    --fcstm-accent: #6ba4d8;
    --fcstm-fg: var(--vscode-editor-foreground, #dfe1e5);
    --fcstm-muted: var(--vscode-descriptionForeground, #9aa5b4);
}
/* User may force light mode regardless of VSCode's theme. */
body.fcstm-mode-light {
    --fcstm-surface: color-mix(in srgb, var(--vscode-editor-background, #ffffff) 86%, #e6f1fb 14%);
    --fcstm-surface-raised: color-mix(in srgb, var(--vscode-editor-background, #ffffff) 78%, #ffffff 22%);
    --fcstm-border: rgba(94, 140, 194, 0.45);
    --fcstm-border-soft: rgba(94, 140, 194, 0.22);
    --fcstm-accent: #2d6aa8;
    --fcstm-fg: var(--vscode-editor-foreground, #1f2937);
    --fcstm-muted: var(--vscode-descriptionForeground, #6a7280);
}

html, body, #app {
    margin: 0;
    padding: 0;
    height: 100%;
    min-height: 100%;
}

body {
    color: var(--fcstm-fg);
    background:
        radial-gradient(circle at top left, rgba(97, 149, 213, 0.12), transparent 38%),
        var(--fcstm-surface);
    font-family: var(--fcstm-mono);
    font-size: 13px;
    line-height: 1.5;
}

#app {
    display: flex;
    min-height: 100%;
}

.fcstm-preview-shell {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    width: 100%;
    box-sizing: border-box;
    flex: 1;
    min-height: 0;
}
</style>
