<script setup lang="ts">
import {h, nextTick, onMounted, onUnmounted, ref, watch} from 'vue';
import {NButton, NDropdown, NIcon, NTooltip} from 'naive-ui';
import {
    AddOutline, RemoveOutline,
    ScanOutline, ResizeOutline,
    ImageOutline, CodeOutline,
} from '@vicons/ionicons5';
import {renderSvg, type RenderedSvg} from '../render/svg';
import {smoothGraphEdges} from '../../../../jsfcstm/src/diagram/render/edge-smoother';
import type {PaletteId, PaletteMode} from '../../../../jsfcstm/src/diagram/render/palette';
import {getElk} from '../composables/useElk';
import {asPointerKind, decidePreviewPointerAction, PREVIEW_DRAG_THRESHOLD_PX} from '../interaction';
import {computePreviewFit} from '../layout';
import type {PreviewWebviewState, SelectionRef, TextRange, PreviewElkNode, PreviewPayload} from '../types';
import {
    assertWithinExportLimits,
    expandSvgForExport,
    EXPORT_PNG_SCALE,
    RASTER_MAX_SIDE,
    rasterScaleWithinLimits,
    renderVectorPdf,
    type SvgExpander,
} from '../../../../jsfcstm/src/diagram/export';

const props = defineProps<{
    state: PreviewWebviewState;
    selection: SelectionRef;
    hover: SelectionRef;
    palette: PaletteId;
    mode: PaletteMode;
}>();
const emit = defineEmits<{
    (e: 'select', sel: SelectionRef): void;
    (e: 'hover', sel: SelectionRef): void;
    (e: 'toggleCollapse', id: string): void;
    (e: 'revealSource', range: TextRange, target: SelectionRef): void;
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
let viewportResizeObserver: ResizeObserver | null = null;
let resizeFrame: number | null = null;

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

// Classes that only a defect in this code produces. Every standard error type
// derives from Error, so an `instanceof Error` guard is a bare catch: it turned
// a renderer bug into "Layout failed: x is not a function", blaming the user's
// model for a mistake of ours. These are re-raised so the host still sees them.
// RangeError is deliberately absent: elkjs is GWT-compiled and reports a
// deeply nested graph as "Maximum call stack size exceeded", which is a
// property of the user's model rather than a defect here, and that case should
// stay a recoverable "Layout failed" panel.
const RENDERER_BUG_TYPES = [TypeError, ReferenceError, SyntaxError, EvalError, URIError];

/**
 * Message for a failure this component is expected to recover from.
 *
 * DOMException covers the documented failure modes of DOMParser, the canvas,
 * and the Clipboard API; plain Error covers ELK, svg2pdf, and the guards this
 * component throws itself. Anything else propagates.
 */
function expectedErrorMessage(error: unknown): string {
    if (RENDERER_BUG_TYPES.some(type => error instanceof type)) throw error;
    if (typeof DOMException !== 'undefined' && error instanceof DOMException) return error.message;
    if (error instanceof Error) return error.message;
    throw error;
}

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
    const transform = computePreviewFit(rect, svgBounds.value);
    setTransform(transform.tx, transform.ty, transform.scale);
}
function scheduleFitToView() {
    if (!viewportRef.value || !svgBounds.value.width) return;
    if (resizeFrame !== null) return;
    if (typeof window.requestAnimationFrame !== 'function') {
        fitToView();
        return;
    }
    resizeFrame = window.requestAnimationFrame(() => {
        resizeFrame = null;
        fitToView();
    });
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
        const initialView = props.state.standaloneViewState;
        // An all-null transform means the producer expressed no preference, so
        // the document opens showing the whole diagram; applying 100% / no pan
        // literally clips every graph taller than the stage on first paint. The
        // nulls come from the producer rather than being inferred from the
        // values, so an explicit 100% at the origin stays requestable.
        const requestedTransform = Boolean(initialView) && (
            initialView.zoom !== null || initialView.panX !== null || initialView.panY !== null
        );
        if (props.state.standalone && requestedTransform) {
            setTransform(initialView.panX ?? 0, initialView.panY ?? 0, initialView.zoom ?? 1);
        } else {
            fitToView();
        }
    } catch (err) {
        // ELK and the SVG DOM report layout problems as Error/DOMException;
        // a TypeError here would be our bug, so the helper re-raises it rather
        // than presenting it as a problem with the model.
        const message = expectedErrorMessage(err);
        isEmpty.value = true;
        emptyTitle.value = 'Layout failed';
        emptyMessage.value = message;
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
        // Chevrons intentionally share the composite's fcstm-id so
        // the collapse-toggle handler can find the owning state, but
        // they are not the visual target of a selection — tagging
        // their own <rect> produces a spurious double-halo at the
        // top-right corner.
        if (kind === 'chevron') continue;
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

function applyHover() {
    if (!innerRef.value) return;
    for (const el of innerRef.value.querySelectorAll('.fcstm-source-hover')) {
        el.classList.remove('fcstm-source-hover');
    }
    const hover = props.hover;
    if (!hover) return;
    for (const el of innerRef.value.querySelectorAll('[data-fcstm-kind][data-fcstm-id]')) {
        const kind = el.getAttribute('data-fcstm-kind');
        const id = el.getAttribute('data-fcstm-id');
        if (id !== hover.id) continue;
        if (hover.kind === 'transition') {
            if (kind === 'transition' || kind === 'transition-label') el.classList.add('fcstm-source-hover');
        } else if (kind !== 'chevron') {
            el.classList.add('fcstm-source-hover');
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
    if (kind !== 'transition' && kind !== 'transition-label') {
        const stateId = el.getAttribute('data-fcstm-id');
        if (stateId && (kind === 'state' || kind === 'chevron')) {
            emit('hover', {kind: 'state', id: stateId});
        } else {
            emit('hover', null);
        }
        return;
    }
    const id = el.getAttribute('data-fcstm-id');
    if (!id) return;
    emit('hover', {kind: 'transition', id});
    clearHover();
    for (const r of relatedElementsForId(id)) r.classList.add('fcstm-related-hover');
}
function onMouseOut(ev: MouseEvent) {
    const to = (ev.relatedTarget as HTMLElement | null)?.closest?.('[data-fcstm-kind][data-fcstm-id]');
    if (to) {
        const kind = to.getAttribute('data-fcstm-kind');
        if (kind === 'transition' || kind === 'transition-label') return;
    }
    emit('hover', null);
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
    // `[data-fcstm-id]` beside the kind, as the four other hit-tests in this
    // file already require. Without it this one stopped at whatever carried a
    // mark, and the detail rows inside a state body carry one: a click landed
    // on a label, `closest` went no further, and the state under the cursor --
    // which had highlighted on hover, because hover does ask for the id --
    // did nothing.
    const target = (ev.target as HTMLElement)?.closest?.('[data-fcstm-kind][data-fcstm-id]');
    const kind = asPointerKind(target?.getAttribute('data-fcstm-kind'));
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
        // The element is known here. Letting the host resolve the range back to
        // an element picks whichever one in *any* source document has the
        // smallest range covering that line, which selects the wrong thing in a
        // model assembled from several files.
        const id = target?.getAttribute('data-fcstm-id') || '';
        const isTransition = kind === 'transition' || kind === 'transition-label';
        emit('revealSource', range, id ? {kind: isTransition ? 'transition' : 'state', id} : null);
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
/**
 * Shared PNG renderer used by both Export (save to disk) and Copy
 * (to clipboard). They go through the same ``<canvas>`` pipeline so
 * the pixel output is byte-identical: same scale, same white fill,
 * same draw order. Returns a Blob so callers can convert to whatever
 * transport they need.
 */
async function rasterizeSvg(svg: string, scale: number): Promise<{blob: Blob; width: number; height: number}> {
    const svgBlob = new Blob([svg], {type: 'image/svg+xml;charset=utf-8'});
    const url = URL.createObjectURL(svgBlob);
    try {
        const img = new Image();
        await new Promise<void>((resolve, reject) => {
            img.onload = () => resolve();
            img.onerror = (e) => reject(e);
            img.src = url;
        });
        // Clamped to what a browser will actually rasterise. Past its side
        // limit `toBlob` returns null with no error, which used to leave a tall
        // diagram with no PNG — and, through the all-or-nothing export below,
        // no SVG or PDF either.
        const fit = rasterScaleWithinLimits(
            svgBounds.value.width,
            svgBounds.value.height,
            scale,
        );
        // Clamped after rounding, not just after scaling. `ceil(h * (CAP / h))`
        // lands one pixel past CAP for about a tenth of integer heights, and the
        // two ceils together can push the product past the area cap — which the
        // browser enforces exactly, so the PNG is lost. The PDF page had the
        // same hazard and fixes it the same way.
        const width = Math.min(
            RASTER_MAX_SIDE,
            Math.max(1, Math.ceil(svgBounds.value.width * fit)),
        );
        const height = Math.min(
            RASTER_MAX_SIDE,
            Math.max(1, Math.ceil(svgBounds.value.height * fit)),
        );
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('canvas 2d context unavailable');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);
        const blob = await new Promise<Blob>((resolve, reject) => {
            canvas.toBlob(b => {
                if (b) resolve(b);
                else reject(new Error('canvas.toBlob returned null'));
            }, 'image/png');
        });
        return {blob, width, height};
    } finally {
        URL.revokeObjectURL(url);
    }
}

function getSvgExpander(): SvgExpander | undefined {
    return (window as unknown as {
        __FCSTM_EXPAND_SVG__?: SvgExpander;
    }).__FCSTM_EXPAND_SVG__;
}

async function renderCurrentSvgToPng(): Promise<Blob> {
    // Refused before anything is rasterised, and with the same limits the
    // synchronous Python export uses. Without this call the product limits exist
    // only in their own unit tests: the clamp inside `rasterizeSvg` would quietly
    // reduce an oversized request instead, and a caller who asked for a scale
    // would never learn it was not honoured.
    assertWithinExportLimits(
        svgBounds.value.width,
        svgBounds.value.height,
        EXPORT_PNG_SCALE,
    );
    const expanded = await expandSvgForExport(svgString, getSvgExpander());
    const {blob} = await rasterizeSvg(expanded, EXPORT_PNG_SCALE);
    return blob;
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

function uint8ToBase64(bytes: Uint8Array): string {
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunk)));
    }
    return (typeof btoa !== 'undefined' ? btoa : (s: string) => Buffer.from(s, 'binary').toString('base64'))(binary);
}

async function renderCurrentSvgToPdf(): Promise<Uint8Array> {
    // A vector PDF has no scale, so only the unscaled geometry is checked; the
    // encoded-size limit is enforced where the bytes are, on the Python side.
    assertWithinExportLimits(svgBounds.value.width, svgBounds.value.height, 1);
    return renderVectorPdf(
        svgString,
        {width: svgBounds.value.width, height: svgBounds.value.height},
        getSvgExpander(),
    );
}

/**
 * Unified export. Renders SVG, PNG and PDF up front and ships all
 * three to the extension in a single message; the format the user
 * picks in the QuickPick decides which payload gets written. SVG is
 * a string dump, PNG uses the standard canvas pipeline, and PDF is
 * generated by the vector-only ``svg2pdf.js`` adapter. All three stay
 * in lockstep with the current view.
 *
 * Rendered in parallel via ``Promise.all`` so the combined latency is
 * dominated by the slowest export rather than the sum.
 */
async function onExportEvt() {
    if (!svgString) return;
    try {
        // Two failures hide inside one call. Validating the on-screen SVG is
        // genuinely fatal -- a malformed diagram puts every format out of reach
        // -- so it stays outside the settled set. Expanding it is not: the
        // string has already parsed by then, so a font-inlining failure used to
        // discard all three formats including the one that needed no expanding.
        const canonical = await expandSvgForExport(svgString);
        const failed: string[] = [];
        let expanded = canonical;
        const expander = getSvgExpander();
        if (!expander) {
            // An absent expander is not an error, so `expandSvgForExport` returns
            // the canonical form without throwing. That left this variable named
            // `expanded` while holding a document that still carries `<text>` and a
            // `font-family`, and the host handed it to the user as an export --
            // which renders differently anywhere the fonts differ. The capability
            // being absent has to be said out loud, because the file looks fine.
            failed.push(
                'SVG font expansion: this host provides no expander, so the SVG '
                + 'still depends on fonts and is not self-contained',
            );
        } else {
            try {
                expanded = await expandSvgForExport(svgString, expander);
            } catch (err) {
                // The expander inlines fonts and re-parses its own output; both
                // report failure as Error/DOMException, and the helper re-raises
                // renderer defects rather than letting them read as export errors.
                failed.push(`SVG font expansion: ${expectedErrorMessage(err)}`);
            }
        }
        // Settled per format rather than all-or-nothing. The SVG is a string
        // that needs neither a canvas nor a PDF writer, so a raster failure
        // must not be able to withhold it.
        const [png, pdf] = await Promise.allSettled([
            // Through the same helper the other two entry points use, so the
            // export command cannot skip the size guard. Calling `rasterizeSvg`
            // directly here left the one path a user actually reaches unguarded
            // while both guarded paths were only reachable from context menus.
            renderCurrentSvgToPng().then(blobToBase64),
            renderCurrentSvgToPdf().then(uint8ToBase64),
        ]);
        if (png.status === 'rejected') failed.push(`PNG: ${expectedErrorMessage(png.reason)}`);
        if (pdf.status === 'rejected') failed.push(`PDF: ${expectedErrorMessage(pdf.reason)}`);
        window.dispatchEvent(new CustomEvent('fcstm-emit', {detail: {
            type: 'exportDiagram',
            payload: {
                svg: expanded,
                pngBase64: png.status === 'fulfilled' ? png.value : '',
                pdfBase64: pdf.status === 'fulfilled' ? pdf.value : '',
                failed,
            },
        }}));
    } catch (err) {
        // Canvas, DOMParser, svg2pdf.js, and the WebAssembly export path report
        // their documented failures as Error/DOMException; renderer defects are
        // re-raised by the helper instead of surfacing as an export error.
        window.dispatchEvent(new CustomEvent('fcstm-emit', {detail: {
            type: 'exportError',
            payload: expectedErrorMessage(err),
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

function notifyCopy(kind: 'png' | 'svg', err?: string, caveat?: string) {
    // A caveat is not a failure: the copy happened, but the caller needs to know
    // something about what landed on the clipboard. Reporting it through the error
    // channel would say the copy failed, and dropping it would say nothing at all.
    const detail = err
        ? {type: 'copyError', payload: `Copy ${kind.toUpperCase()} failed: ${err}`}
        : {
            type: 'copyDone',
            payload: `Copied ${kind.toUpperCase()} to clipboard`
                + (caveat ? ` — ${caveat}` : ''),
        };
    window.dispatchEvent(new CustomEvent('fcstm-emit', {detail}));
}

async function copySvgToClipboard() {
    if (!svgString) return;
    try {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            // The same product as Export → Save SVG. Where the host provides an
            // expander that means glyphs are already paths and pasting into an
            // external tool does not depend on the viewer's font stack; where it
            // does not, the copy still happens and says so, because a document
            // that renders differently elsewhere looks identical here.
            const expander = getSvgExpander();
            const expanded = await expandSvgForExport(svgString, expander);
            await navigator.clipboard.writeText(expanded);
            notifyCopy(
                'svg',
                undefined,
                expander
                    ? undefined
                    : 'this host cannot expand fonts, so the SVG is not self-contained',
            );
            return;
        }
        throw new Error('clipboard API not available');
    } catch (err) {
        // The clipboard API reports permission and format failures as
        // DOMException; renderer defects are re-raised by the helper.
        notifyCopy('svg', expectedErrorMessage(err));
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
        // Canvas and the clipboard API report their documented failures as
        // Error/DOMException; renderer defects and unknown thrown values are
        // re-raised by the helper.
        notifyCopy('png', expectedErrorMessage(err));
    }
}

function onCopyPngEvt() { void copyPngToClipboard(); }
function onCopySvgEvt() { void copySvgToClipboard(); }

onMounted(() => {
    window.addEventListener('mousemove', onMouseMoveWindow);
    window.addEventListener('mouseup', onMouseUpWindow);
    window.addEventListener('fcstm-fit', onFitEvt as EventListener);
    window.addEventListener('fcstm-actual', onActualEvt as EventListener);
    window.addEventListener('fcstm-export', onExportEvt as EventListener);
    window.addEventListener('fcstm-copy-png', onCopyPngEvt as EventListener);
    window.addEventListener('fcstm-copy-svg', onCopySvgEvt as EventListener);
    window.addEventListener('resize', onFitEvt);
    if (typeof ResizeObserver !== 'undefined' && viewportRef.value) {
        viewportResizeObserver = new ResizeObserver(() => {
            // Drawer drag/collapse changes the Stage without a window resize.
            // Re-fit against the actual right-pane viewport so the diagram
            // cannot remain at a scale that is now clipped.
            scheduleFitToView();
        });
        viewportResizeObserver.observe(viewportRef.value);
    }
    void relayout();
});
onUnmounted(() => {
    window.removeEventListener('mousemove', onMouseMoveWindow);
    window.removeEventListener('mouseup', onMouseUpWindow);
    window.removeEventListener('fcstm-fit', onFitEvt as EventListener);
    window.removeEventListener('fcstm-actual', onActualEvt as EventListener);
    window.removeEventListener('fcstm-export', onExportEvt as EventListener);
    window.removeEventListener('fcstm-copy-png', onCopyPngEvt as EventListener);
    window.removeEventListener('fcstm-copy-svg', onCopySvgEvt as EventListener);
    window.removeEventListener('resize', onFitEvt);
    if (resizeFrame !== null && typeof window.cancelAnimationFrame === 'function') {
        window.cancelAnimationFrame(resizeFrame);
    }
    resizeFrame = null;
    viewportResizeObserver?.disconnect();
    viewportResizeObserver = null;
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
watch(() => props.hover, () => {
    applyHover();
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
/* Hover brightness on the body rect only, never on the halo ring —
   otherwise hovering a selected composite would tint the halo too. */
.fcstm-stage__inner [data-fcstm-kind="state"]:hover > rect:not(.fcstm-halo),
.fcstm-stage__inner [data-fcstm-kind="composite-state"]:hover > rect:not(.fcstm-halo) {
    filter: brightness(1.03);
}
/* Leaves and pseudo-exit circles keep the stroke-override approach:
   no title bar to cover them, so the body stroke can be recolored
   directly. Composites use a dedicated halo ring instead (see below). */
.fcstm-stage__inner [data-fcstm-kind="state"].fcstm-selected > rect,
.fcstm-stage__inner [data-fcstm-kind].fcstm-selected > circle {
    stroke: #c8761a !important;
    stroke-width: 2.6 !important;
    filter: drop-shadow(0 0 4px rgba(200, 118, 26, 0.5));
}
/* Halo ring for expanded composites. Invisible until selected, then
   a stroke-only rect sitting just outside the body — the title-bar
   fill cannot cover it and the chevron's own <rect> is not it. */
.fcstm-stage__inner .fcstm-halo {
    fill: none;
    stroke: transparent;
    stroke-width: 0;
}
.fcstm-stage__inner [data-fcstm-kind="composite-state"].fcstm-selected > .fcstm-halo {
    stroke: #c8761a;
    stroke-width: 2.6;
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
    stroke: #2d6aa8 !important;
    stroke-width: 3.2 !important;
    filter: none !important;
}
.fcstm-stage__inner [data-fcstm-kind="state"].fcstm-source-hover > rect:not(.fcstm-halo),
.fcstm-stage__inner [data-fcstm-kind="composite-state"].fcstm-source-hover > .fcstm-halo {
    stroke: #2d6aa8 !important;
    stroke-width: 2.4 !important;
    filter: drop-shadow(0 0 4px rgba(45, 106, 168, 0.45));
}
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-source-hover > text {
    stroke: #2d6aa8 !important;
    fill: #2d6aa8 !important;
}
.fcstm-stage__inner [data-fcstm-kind="transition"].fcstm-source-hover {
    fill: none !important;
    stroke: #2d6aa8 !important;
    stroke-width: 3.2 !important;
    filter: none !important;
}
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-hover > text {
    font-weight: 700;
    paint-order: stroke;
}
/* Effect/guard notes keep their semantic background shape, but hover only
   changes the border. Filtering the parent label group would turn that
   note polygon into the hover shadow instead of highlighting the edge. */
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-hover > path:first-child,
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-related-hover > path:nth-child(2),
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-source-hover > path:first-child,
.fcstm-stage__inner [data-fcstm-kind="transition-label"].fcstm-source-hover > path:nth-child(2) {
    stroke: #2d6aa8 !important;
    stroke-width: 1.3 !important;
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
