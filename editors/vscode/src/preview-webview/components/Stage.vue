<script setup lang="ts">
import {h, nextTick, onMounted, onUnmounted, ref, watch} from 'vue';
import {NButton, NDropdown, NIcon, NTooltip} from 'naive-ui';
import {
    AddOutline, RemoveOutline,
    ScanOutline, ResizeOutline,
    ImageOutline, CodeOutline,
} from '@vicons/ionicons5';
import {renderSvg, type RenderedSvg} from '../render/svg';
import {smoothGraphEdges} from '../render/edge-smoother';
import type {PaletteId, PaletteMode} from '../render/palette';
import {getElk} from '../composables/useElk';
import {decidePreviewPointerAction, PREVIEW_DRAG_THRESHOLD_PX} from '../interaction';
import type {PreviewWebviewState, SelectionRef, TextRange, PreviewElkNode, PreviewPayload} from '../types';

const props = defineProps<{
    state: PreviewWebviewState;
    selection: SelectionRef;
    palette: PaletteId;
    mode: PaletteMode;
}>();
const emit = defineEmits<{
    (e: 'select', sel: SelectionRef): void;
    (e: 'toggleCollapse', id: string): void;
    (e: 'revealSource', range: TextRange): void;
}>();

const viewportRef = ref<HTMLDivElement | null>(null);
const innerRef = ref<HTMLDivElement | null>(null);
const zoomLabel = ref('100%');

const isEmpty = ref(true);
const emptyTitle = ref('FCSTM Preview');
const emptyMessage = ref('');
const svgBounds = ref({width: 0, height: 0});
let svgString = '';
let layoutToken = 0;

const viewTransform = {tx: 0, ty: 0, scale: 1};
let dragState: null | {startX: number; startY: number; tx: number; ty: number} = null;
let dragMovedPx = 0;

// Cache the last successful layout so palette / mode changes can
// re-render without asking ELK to lay the graph out again. ELK's
// ``layout()`` mutates its input — running it twice on the same
// object (e.g. the live ``payload.graph``) accumulates edge sections
// and can corrupt state, which is what caused palette / mode flips
// to first freeze the webview and eventually drag VSCode down when
// users toggled them repeatedly.
let lastLaidOut: PreviewElkNode | null = null;
let lastLaidOutOptions: PreviewPayload['options'] | null = null;
let lastLaidOutSourceRef: unknown = null;

function setTransform(tx: number, ty: number, scale: number) {
    const next = Math.max(0.1, Math.min(8, scale));
    viewTransform.tx = tx;
    viewTransform.ty = ty;
    viewTransform.scale = next;
    if (innerRef.value) {
        innerRef.value.style.transform = `translate(${tx}px,${ty}px) scale(${next})`;
    }
    zoomLabel.value = Math.round(next * 100) + '%';
}

function fitToView() {
    if (!viewportRef.value || !svgBounds.value.width) return;
    const rect = viewportRef.value.getBoundingClientRect();
    const margin = 16;
    const availW = Math.max(40, rect.width - margin * 2);
    const availH = Math.max(40, rect.height - margin * 2);
    const scale = Math.min(availW / svgBounds.value.width, availH / svgBounds.value.height, 1);
    const tx = (rect.width - svgBounds.value.width * scale) / 2;
    const ty = (rect.height - svgBounds.value.height * scale) / 2;
    setTransform(tx, ty, scale);
}
function actualSize() {
    if (!viewportRef.value) return;
    const rect = viewportRef.value.getBoundingClientRect();
    const tx = Math.max(0, (rect.width - svgBounds.value.width) / 2);
    const ty = Math.max(0, (rect.height - svgBounds.value.height) / 2);
    setTransform(tx, ty, 1);
}
function zoomAtCenter(factor: number) {
    if (!viewportRef.value) return;
    const rect = viewportRef.value.getBoundingClientRect();
    const cx = rect.width / 2, cy = rect.height / 2;
    const worldX = (cx - viewTransform.tx) / viewTransform.scale;
    const worldY = (cy - viewTransform.ty) / viewTransform.scale;
    const ns = viewTransform.scale * factor;
    setTransform(cx - worldX * ns, cy - worldY * ns, ns);
}

function rerenderFromCache() {
    if (!lastLaidOut || !lastLaidOutOptions) return;
    const result: RenderedSvg = renderSvg(lastLaidOut, lastLaidOutOptions, {
        palette: props.palette,
        mode: props.mode,
    });
    svgString = result.svg;
    svgBounds.value = {width: result.width, height: result.height};
    if (innerRef.value) {
        innerRef.value.innerHTML = result.svg;
    }
    isEmpty.value = false;
    // Re-apply overlays on the new DOM without blowing away the
    // existing pan / zoom.
    void nextTick().then(() => {
        applySelection();
    });
}

async function relayout() {
    const token = ++layoutToken;
    const payload = props.state.payload;
    if (!payload) {
        isEmpty.value = true;
        emptyTitle.value = props.state.emptyTitle || 'FCSTM Preview';
        emptyMessage.value = props.state.emptyMessage || 'No diagram available.';
        lastLaidOut = null;
        lastLaidOutOptions = null;
        lastLaidOutSourceRef = null;
        return;
    }
    // Short-circuit: if the payload reference hasn't changed since the
    // last successful layout, just re-render with the cached geometry.
    // This is what lets palette / mode / collapse toggles feel instant
    // and — crucially — keeps us from feeding ELK a graph it has
    // already mutated.
    if (lastLaidOut && lastLaidOutSourceRef === payload.graph) {
        lastLaidOutOptions = payload.options;
        rerenderFromCache();
        return;
    }
    try {
        // ELK mutates its input; deep-clone so repeated runs on the
        // same payload.graph can't poison each other.
        const graphCopy = JSON.parse(JSON.stringify(payload.graph));
        const laid = await getElk().layout(graphCopy) as PreviewElkNode;
        if (token !== layoutToken) return;
        // ELK's orthogonal router occasionally lands the last segment
        // of an edge within a handful of pixels of the target port,
        // producing an ugly "stub" right under the arrowhead. Shift the
        // trailing / leading bend pair so the terminal segment is at
        // least 18px long.
        smoothGraphEdges(laid);
        lastLaidOut = laid;
        lastLaidOutOptions = payload.options;
        lastLaidOutSourceRef = payload.graph;
        const result: RenderedSvg = renderSvg(laid, payload.options, {
            palette: props.palette,
            mode: props.mode,
        });
        svgString = result.svg;
        svgBounds.value = {width: result.width, height: result.height};
        if (innerRef.value) {
            innerRef.value.innerHTML = result.svg;
        }
        isEmpty.value = false;
        await nextTick();
        applySelection();
        fitToView();
    } catch (err) {
        isEmpty.value = true;
        emptyTitle.value = 'Layout failed';
        emptyMessage.value = (err as Error)?.message || String(err);
    }
}

function readRange(el: Element): TextRange | null {
    const sl = el.getAttribute('data-fcstm-range-start-line');
    if (sl === null) return null;
    const sc = el.getAttribute('data-fcstm-range-start-character');
    const el2 = el.getAttribute('data-fcstm-range-end-line');
    const ec = el.getAttribute('data-fcstm-range-end-character');
    return {
        start: {line: +sl, character: +(sc || '0')},
        end: {line: +(el2 || '0'), character: +(ec || '0')},
    };
}

function applySelection() {
    if (!innerRef.value) return;
    for (const el of innerRef.value.querySelectorAll('.fcstm-selected, .fcstm-related-event')) {
        el.classList.remove('fcstm-selected');
        el.classList.remove('fcstm-related-event');
    }
    const sel = props.selection;
    if (!sel) return;
    const nodes = innerRef.value.querySelectorAll('[data-fcstm-kind][data-fcstm-id]');
    for (const el of nodes) {
        const kind = el.getAttribute('data-fcstm-kind');
        const id = el.getAttribute('data-fcstm-id');
        if (id !== sel.id) continue;
        if (sel.kind === 'transition') {
            if (kind === 'transition' || kind === 'transition-label') {
                el.classList.add('fcstm-selected');
            }
        } else {
            el.classList.add('fcstm-selected');
        }
    }
    // Related-event highlight: if the selected transition has an
    // eventQualifiedName, find every *other* transition that shares the
    // same event and tag its label so the user can see the whole family
    // fire together.
    if (sel.kind === 'transition' && props.state.payload) {
        const selected = props.state.payload.transitions.find(t => t.transitionId === sel.id);
        if (selected && selected.eventQualifiedName) {
            const related = props.state.payload.transitions.filter(t =>
                t.eventQualifiedName === selected.eventQualifiedName &&
                t.transitionId !== sel.id
            );
            for (const relTransition of related) {
                for (const el of nodes) {
                    if (el.getAttribute('data-fcstm-kind') !== 'transition-label') continue;
                    if (el.getAttribute('data-fcstm-id') !== relTransition.transitionId) continue;
                    el.classList.add('fcstm-related-event');
                }
            }
        }
    }
}

function relatedElementsForId(targetId: string): Element[] {
    if (!innerRef.value) return [];
    const nodes = innerRef.value.querySelectorAll(
        '[data-fcstm-kind="transition"][data-fcstm-id], [data-fcstm-kind="transition-label"][data-fcstm-id]'
    );
    return Array.from(nodes).filter(n => n.getAttribute('data-fcstm-id') === targetId);
}
function clearHover() {
    if (!innerRef.value) return;
    for (const n of innerRef.value.querySelectorAll('.fcstm-related-hover')) {
        n.classList.remove('fcstm-related-hover');
    }
}

function onMouseOver(ev: MouseEvent) {
    const el = (ev.target as HTMLElement)?.closest?.('[data-fcstm-kind][data-fcstm-id]');
    if (!el) return;
    const kind = el.getAttribute('data-fcstm-kind');
    if (kind !== 'transition' && kind !== 'transition-label') return;
    const id = el.getAttribute('data-fcstm-id');
    if (!id) return;
    clearHover();
    for (const r of relatedElementsForId(id)) r.classList.add('fcstm-related-hover');
}
function onMouseOut(ev: MouseEvent) {
    const to = (ev.relatedTarget as HTMLElement | null)?.closest?.('[data-fcstm-kind][data-fcstm-id]');
    if (to) {
        const kind = to.getAttribute('data-fcstm-kind');
        if (kind === 'transition' || kind === 'transition-label') return;
    }
    clearHover();
}

function onMouseDown(ev: MouseEvent) {
    if (ev.button !== 0) return;
    dragState = {startX: ev.clientX, startY: ev.clientY, tx: viewTransform.tx, ty: viewTransform.ty};
    dragMovedPx = 0;
    viewportRef.value?.classList.add('fcstm-stage__viewport--dragging');
}
function onMouseMoveWindow(ev: MouseEvent) {
    if (!dragState) return;
    const dx = ev.clientX - dragState.startX;
    const dy = ev.clientY - dragState.startY;
    dragMovedPx = Math.max(dragMovedPx, Math.hypot(dx, dy));
    setTransform(dragState.tx + dx, dragState.ty + dy, viewTransform.scale);
}
function onMouseUpWindow() {
    if (dragState) {
        dragState = null;
        viewportRef.value?.classList.remove('fcstm-stage__viewport--dragging');
    }
}

function onClick(ev: MouseEvent) {
    const moved = dragMovedPx;
    dragMovedPx = 0;
    const target = (ev.target as HTMLElement)?.closest?.('[data-fcstm-kind]');
    const kind = target?.getAttribute('data-fcstm-kind') as never;
    const range = target ? readRange(target) : null;
    const modifier = Boolean(ev.ctrlKey || ev.metaKey);
    const action = decidePreviewPointerAction({
        kind,
        modifier,
        dragMovedPx: moved,
        hasRange: Boolean(range),
    });
    if (action.type === 'toggleCollapse' && target) {
        const id = target.getAttribute('data-fcstm-id');
        if (id) emit('toggleCollapse', id);
        return;
    }
    if (action.type === 'revealSource' && range) {
        emit('revealSource', range);
        return;
    }
    if (action.type === 'select' && target) {
        const id = target.getAttribute('data-fcstm-id');
        if (!id) return;
        const isTransitionKind = kind === 'transition' || kind === 'transition-label';
        emit('select', {
            kind: isTransitionKind ? 'transition' : (kind === 'chevron' ? 'state' : kind),
            id,
        } as SelectionRef);
        return;
    }
    if (action.type === 'clearSelection') {
        emit('select', null);
        return;
    }
}

function onWheel(ev: WheelEvent) {
    if (!svgString) return;
    ev.preventDefault();
    const delta = -ev.deltaY;
    const factor = Math.exp(delta * 0.0015);
    const rect = viewportRef.value?.getBoundingClientRect();
    if (!rect) return;
    const cx = ev.clientX - rect.left;
    const cy = ev.clientY - rect.top;
    const worldX = (cx - viewTransform.tx) / viewTransform.scale;
    const worldY = (cy - viewTransform.ty) / viewTransform.scale;
    const newScale = viewTransform.scale * factor;
    setTransform(cx - worldX * newScale, cy - worldY * newScale, newScale);
}

// Toolbar → Stage custom events.
function onFitEvt() { fitToView(); }
function onActualEvt() { actualSize(); }
function onExportSvgEvt() {
    if (!svgString) return;
    window.dispatchEvent(new CustomEvent('fcstm-emit', {detail: {type: 'exportSvg', payload: svgString}}));
}
/**
 * Shared PNG renderer used by both Export (save to disk) and Copy
 * (to clipboard). They go through the same ``<canvas>`` pipeline so
 * the pixel output is byte-identical: same scale, same white fill,
 * same draw order. Returns a Blob so callers can convert to whatever
 * transport they need.
 */
async function renderCurrentSvgToPng(): Promise<Blob> {
    const svgBlob = new Blob([svgString], {type: 'image/svg+xml;charset=utf-8'});
    const url = URL.createObjectURL(svgBlob);
    try {
        const img = new Image();
        await new Promise<void>((resolve, reject) => {
            img.onload = () => resolve();
            img.onerror = (e) => reject(e);
            img.src = url;
        });
        const scale = 2;
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.ceil(svgBounds.value.width * scale));
        canvas.height = Math.max(1, Math.ceil(svgBounds.value.height * scale));
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('canvas 2d context unavailable');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        return await new Promise<Blob>((resolve, reject) => {
            canvas.toBlob(b => {
                if (b) resolve(b);
                else reject(new Error('canvas.toBlob returned null'));
            }, 'image/png');
        });
    } finally {
        URL.revokeObjectURL(url);
    }
}

async function blobToBase64(blob: Blob): Promise<string> {
    const buffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return (typeof btoa !== 'undefined' ? btoa : (s: string) => Buffer.from(s, 'binary').toString('base64'))(binary);
}

async function onExportPngEvt() {
    if (!svgString) return;
    try {
        const blob = await renderCurrentSvgToPng();
        const base64 = await blobToBase64(blob);
        window.dispatchEvent(new CustomEvent('fcstm-emit', {detail: {type: 'exportPng', payload: base64}}));
    } catch (err) {
        window.dispatchEvent(new CustomEvent('fcstm-emit', {detail: {
            type: 'exportError',
            payload: (err as Error)?.message || String(err),
        }}));
    }
}

// Right-click context menu — quick access to "copy as" actions so the
// user can drop the diagram straight into a doc, chat, or presentation
// without going through a save-to-disk round trip.
const menuVisible = ref(false);
const menuX = ref(0);
const menuY = ref(0);
const contextMenuOptions = [
    {
        label: 'Copy as PNG',
        key: 'copy-png',
        icon: () => h(NIcon, null, {default: () => h(ImageOutline)}),
    },
    {
        label: 'Copy as SVG',
        key: 'copy-svg',
        icon: () => h(NIcon, null, {default: () => h(CodeOutline)}),
    },
];
function onContextMenu(ev: MouseEvent) {
    if (!svgString) return;
    ev.preventDefault();
    menuVisible.value = false;
    nextTick(() => {
        menuX.value = ev.clientX;
        menuY.value = ev.clientY;
        menuVisible.value = true;
    });
}
function onContextMenuClickOutside() { menuVisible.value = false; }
function onContextMenuSelect(key: string) {
    menuVisible.value = false;
    if (key === 'copy-png') void copyPngToClipboard();
    else if (key === 'copy-svg') void copySvgToClipboard();
}

function notifyCopy(kind: 'png' | 'svg', err?: string) {
    const detail = err
        ? {type: 'copyError', payload: `Copy ${kind.toUpperCase()} failed: ${err}`}
        : {type: 'copyDone', payload: `Copied ${kind.toUpperCase()} to clipboard`};
    window.dispatchEvent(new CustomEvent('fcstm-emit', {detail}));
}

async function copySvgToClipboard() {
    if (!svgString) return;
    try {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            await navigator.clipboard.writeText(svgString);
            notifyCopy('svg');
            return;
        }
        throw new Error('clipboard API not available');
    } catch (err) {
        notifyCopy('svg', (err as Error)?.message || String(err));
    }
}

async function copyPngToClipboard() {
    if (!svgString) return;
    try {
        // Exactly the same pipeline as Export → Save PNG, so the
        // clipboard PNG is byte-identical to the saved one.
        const blob = await renderCurrentSvgToPng();
        const ClipboardItemCtor = (window as unknown as {
            ClipboardItem?: typeof ClipboardItem;
        }).ClipboardItem;
        if (ClipboardItemCtor && navigator.clipboard && 'write' in navigator.clipboard) {
            await navigator.clipboard.write([new ClipboardItemCtor({'image/png': blob})]);
            notifyCopy('png');
            return;
        }
        throw new Error('ClipboardItem not available');
    } catch (err) {
        notifyCopy('png', (err as Error)?.message || String(err));
    }
}

onMounted(() => {
    window.addEventListener('mousemove', onMouseMoveWindow);
    window.addEventListener('mouseup', onMouseUpWindow);
    window.addEventListener('fcstm-fit', onFitEvt as EventListener);
    window.addEventListener('fcstm-actual', onActualEvt as EventListener);
    window.addEventListener('fcstm-export-svg', onExportSvgEvt as EventListener);
    window.addEventListener('fcstm-export-png', onExportPngEvt as EventListener);
    window.addEventListener('resize', onFitEvt);
    void relayout();
});
onUnmounted(() => {
    window.removeEventListener('mousemove', onMouseMoveWindow);
    window.removeEventListener('mouseup', onMouseUpWindow);
    window.removeEventListener('fcstm-fit', onFitEvt as EventListener);
    window.removeEventListener('fcstm-actual', onActualEvt as EventListener);
    window.removeEventListener('fcstm-export-svg', onExportSvgEvt as EventListener);
    window.removeEventListener('fcstm-export-png', onExportPngEvt as EventListener);
    window.removeEventListener('resize', onFitEvt);
});

// Payload reference change → re-layout (different graph geometry).
watch(() => props.state.payload, () => {
    void relayout();
});
// Collapsed-state changes ship as a new payload from the extension, so
// the payload watch above already covers them. We keep a no-op watch
// here only to ensure the webview never tries to re-lay out on its
// own while the extension is still rebuilding.
watch(() => props.state.collapsedStateIds, () => { /* no-op */ });
// Palette / mode changes only re-skin the already-laid-out graph.
// Running elk.layout() again on the same payload is both unnecessary
// (ELK geometry is palette-agnostic) and actively harmful (ELK mutates
// its input, so repeated runs accumulate state).
watch(() => [props.palette, props.mode], () => {
    rerenderFromCache();
});
watch(() => props.selection, () => {
    applySelection();
}, {deep: true});

// Expose drag threshold for debugging / tests.
const _t = PREVIEW_DRAG_THRESHOLD_PX;
void _t;
</script>

<template>
    <div class="fcstm-stage">
        <div
            ref="viewportRef"
            class="fcstm-stage__viewport"
            title="Drag to pan · wheel to zoom · click chevron to collapse · Ctrl/Cmd+click to reveal source · right-click to copy"
            @wheel.prevent="onWheel"
            @mousedown="onMouseDown"
            @click="onClick"
            @mouseover="onMouseOver"
            @mouseout="onMouseOut"
            @contextmenu="onContextMenu"
        >
            <div ref="innerRef" class="fcstm-stage__inner"></div>
        </div>
        <n-dropdown
            trigger="manual"
            placement="bottom-start"
            :options="contextMenuOptions"
            :show="menuVisible"
            :x="menuX"
            :y="menuY"
            @clickoutside="onContextMenuClickOutside"
            @select="onContextMenuSelect"
        />
        <div v-if="isEmpty" class="fcstm-stage__empty">
            <div class="fcstm-stage__empty-title">{{ emptyTitle }}</div>
            <div class="fcstm-stage__empty-message">{{ emptyMessage }}</div>
        </div>
        <div class="fcstm-stage__zoom">
            <n-tooltip placement="left" :delay="400">
                <template #trigger>
                    <n-button quaternary circle size="small" @click="zoomAtCenter(1.2)">
                        <template #icon><n-icon><AddOutline /></n-icon></template>
                    </n-button>
                </template>
                Zoom in
            </n-tooltip>
            <div class="fcstm-stage__zoom-level">{{ zoomLabel }}</div>
            <n-tooltip placement="left" :delay="400">
                <template #trigger>
                    <n-button quaternary circle size="small" @click="zoomAtCenter(1 / 1.2)">
                        <template #icon><n-icon><RemoveOutline /></n-icon></template>
                    </n-button>
                </template>
                Zoom out
            </n-tooltip>
            <div class="fcstm-stage__zoom-divider"></div>
            <n-tooltip placement="left" :delay="400">
                <template #trigger>
                    <n-button quaternary circle size="small" @click="fitToView">
                        <template #icon><n-icon><ScanOutline /></n-icon></template>
                    </n-button>
                </template>
                Fit to view
            </n-tooltip>
            <n-tooltip placement="left" :delay="400">
                <template #trigger>
                    <n-button quaternary circle size="small" @click="actualSize">
                        <template #icon><n-icon><ResizeOutline /></n-icon></template>
                    </n-button>
                </template>
                Actual size (100%)
            </n-tooltip>
        </div>
        <div class="fcstm-stage__hint">
            Drag to pan · Ctrl/Cmd+click to jump to source · Click chevron to collapse
        </div>
    </div>
</template>

<style>
.fcstm-stage {
    position: relative;
    flex: 1;
    min-height: 320px;
    border: 1px solid var(--fcstm-border);
    border-radius: 14px;
    background: var(--fcstm-surface-raised);
    overflow: hidden;
}
.fcstm-stage__viewport {
    position: absolute;
    inset: 0;
    overflow: hidden;
    cursor: grab;
}
.fcstm-stage__viewport--dragging { cursor: grabbing; }
.fcstm-stage__inner {
    position: absolute;
    top: 0; left: 0;
    transform-origin: 0 0;
}
.fcstm-stage__inner svg { display: block; user-select: none; }

.fcstm-stage__inner [data-fcstm-kind="chevron"],
.fcstm-stage__inner [data-fcstm-kind="state"],
.fcstm-stage__inner [data-fcstm-kind="composite-state"],
.fcstm-stage__inner [data-fcstm-kind="transition"],
.fcstm-stage__inner [data-fcstm-kind="transition-label"],
.fcstm-stage__inner [data-fcstm-kind="pseudo-init"],
.fcstm-stage__inner [data-fcstm-kind="pseudo-exit"] {
    cursor: pointer;
}
body.modifier-held .fcstm-stage__inner [data-fcstm-kind][data-fcstm-range-start-line] {
    cursor: alias;
}
.fcstm-stage__inner [data-fcstm-kind="state"]:hover > rect,
.fcstm-stage__inner [data-fcstm-kind="composite-state"]:hover > rect {
    filter: brightness(1.03);
}
.fcstm-stage__inner [data-fcstm-kind].fcstm-selected > rect,
.fcstm-stage__inner [data-fcstm-kind].fcstm-selected > circle {
    stroke: #c8761a !important;
    stroke-width: 2.6 !important;
    filter: drop-shadow(0 0 4px rgba(200, 118, 26, 0.5));
}
.fcstm-stage__inner [data-fcstm-kind="transition"].fcstm-selected,
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-selected > text {
    stroke: #c8761a !important;
    stroke-width: 3 !important;
    filter: drop-shadow(0 0 3px rgba(200, 118, 26, 0.45));
}
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-selected > text {
    font-weight: 700;
}
.fcstm-stage__inner [data-fcstm-kind="transition"].fcstm-related-hover {
    stroke-width: 3.2 !important;
    filter: drop-shadow(0 0 3px rgba(45, 106, 168, 0.35));
}
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-hover > text {
    font-weight: 700;
    paint-order: stroke;
}
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-hover {
    filter: drop-shadow(0 0 2px rgba(45, 106, 168, 0.3));
}
/* Same-event labels light up with a softer teal halo when the user
   selects one transition in the event family; clearly distinct from
   the bright orange selected highlight. */
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-event > text {
    font-weight: 700;
    paint-order: stroke;
    stroke: rgba(0, 178, 148, 0.85) !important;
    stroke-width: 3 !important;
    stroke-linejoin: round;
    filter: drop-shadow(0 0 3px rgba(0, 178, 148, 0.45));
}
body.fcstm-mode-dark .fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-event > text {
    stroke: rgba(98, 220, 193, 0.9) !important;
    filter: drop-shadow(0 0 3px rgba(98, 220, 193, 0.55));
}

.fcstm-stage__empty {
    position: absolute;
    inset: 28px;
    border: 1px dashed var(--fcstm-border);
    border-radius: 14px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    text-align: center;
    pointer-events: none;
}
.fcstm-stage__empty-title { font-size: 16px; font-weight: 700; }
.fcstm-stage__empty-message {
    font-size: 12px;
    color: var(--fcstm-muted);
    white-space: pre-wrap;
    word-break: break-word;
    max-width: 620px;
}

.fcstm-stage__zoom {
    position: absolute;
    bottom: 14px; right: 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    background: var(--fcstm-surface-raised);
    border: 1px solid var(--fcstm-border);
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.fcstm-stage__zoom-level {
    font-size: 10px;
    color: var(--fcstm-accent);
    letter-spacing: 0.04em;
}
.fcstm-stage__zoom-divider {
    width: 70%;
    height: 1px;
    background: var(--fcstm-border-soft);
    margin: 4px 0 2px 0;
}
.fcstm-stage__hint {
    position: absolute;
    left: 14px; bottom: 10px;
    font-size: 10px;
    color: var(--fcstm-muted);
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid var(--fcstm-border-soft);
    border-radius: 999px;
    padding: 3px 10px;
    pointer-events: none;
    opacity: 0.9;
}
body.vscode-dark .fcstm-stage__hint,
body.vscode-high-contrast .fcstm-stage__hint {
    background: rgba(30, 30, 30, 0.65);
}
</style>
