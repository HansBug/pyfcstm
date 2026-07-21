<script setup lang="ts">
import {computed, nextTick, ref, watch} from 'vue';
import type {PreviewWebviewState, SelectionRef, TextRange} from '../types';
import {selectionKindForSourceMap} from '../standalone-data';

const props = defineProps<{
    sourceHtml: string;
    sourceAvailable?: boolean;
    sourceUnavailableReason?: string;
    sourceMap?: PreviewWebviewState['sourceMap'];
    sourceLineMap?: PreviewWebviewState['sourceLineMap'];
    sourceDocuments?: PreviewWebviewState['sourceDocuments'];
    sourceDocumentId?: string;
    selection: SelectionRef;
    hover: SelectionRef;
}>();
const emit = defineEmits<{
    (event: 'select', value: SelectionRef): void;
    (event: 'hover', value: SelectionRef): void;
}>();
const panel = ref<HTMLElement | null>(null);
const documentId = ref(props.sourceDocumentId || Object.keys(props.sourceDocuments || {})[0] || 'main.fcstm');

const currentDocument = computed(() => props.sourceDocuments?.[documentId.value]);
const currentSourceHtml = computed(() => currentDocument.value?.html || props.sourceHtml);

function idsForLine(line: string): string[] {
    const raw = props.sourceLineMap?.[`${documentId.value}:${line}`]
        || (documentId.value === props.sourceDocumentId ? props.sourceLineMap?.[line] : undefined);
    if (Array.isArray(raw)) return raw;
    return raw ? [raw] : [];
}

function nextIdForLine(line: string): string | undefined {
    const ids = idsForLine(line);
    if (!ids.length) return undefined;
    const current = props.selection?.id || props.hover?.id;
    if (!current) return ids[0];
    const index = ids.indexOf(current);
    return ids[(index + 1) % ids.length];
}

const activeId = computed(() => props.hover?.id || props.selection?.id || null);
const activeLines = computed(() => {
    const id = activeId.value;
    const item = id && props.sourceMap?.[id];
    if (item?.documentId && item.documentId !== documentId.value) return new Set<number>();
    const range = item?.range;
    if (!range) return new Set<number>();
    const lines = new Set<number>();
    for (let line = range.start.line; line <= range.end.line; line += 1) lines.add(line);
    return lines;
});

function onClick(event: MouseEvent) {
    const target = (event.target as HTMLElement | null)?.closest('.fcstm-source-line');
    const line = target?.getAttribute('data-line');
    if (line === null || line === undefined) return;
    const id = nextIdForLine(line);
    if (id) emit('select', selectionKindForSourceMap(props.sourceMap, id));
}

function onMouseOver(event: MouseEvent) {
    const target = (event.target as HTMLElement | null)?.closest('.fcstm-source-line');
    const line = target?.getAttribute('data-line');
    if (line === null || line === undefined) return;
    const ids = idsForLine(line);
    const current = props.selection?.id;
    const id = current && ids.includes(current) ? current : ids[0];
    emit('hover', id ? selectionKindForSourceMap(props.sourceMap, id) : null);
}

watch(activeId, (id) => {
    const nextDocument = id && props.sourceMap?.[id]?.documentId;
    if (nextDocument && props.sourceDocuments?.[nextDocument]) documentId.value = nextDocument;
    void scrollActive();
});

function onMouseOut(event: MouseEvent) {
    const next = (event.relatedTarget as HTMLElement | null)?.closest?.('.fcstm-source-line');
    if (next) return;
    emit('hover', null);
}

async function scrollActive() {
    await nextTick();
    if (!panel.value) return;
    for (const line of panel.value.querySelectorAll('.fcstm-source-line')) {
        const lineNumber = Number(line.getAttribute('data-line'));
        line.classList.toggle('fcstm-source-line--active', activeLines.value.has(lineNumber));
    }
    if (!activeId.value) return;
    const item = props.sourceMap?.[activeId.value];
    if (item?.documentId && item.documentId !== documentId.value) return;
    const range = item?.range;
    if (!range) return;
    const line = panel.value.querySelector(`[data-line="${range.start.line}"]`);
    (line as HTMLElement | null)?.scrollIntoView({block: 'nearest'});
}
watch(activeId, scrollActive);
</script>

<template>
    <section ref="panel" class="fcstm-source-panel" @click="onClick" @mouseover="onMouseOver" @mouseout="onMouseOut">
        <div class="fcstm-source-panel__header">
            <span>FCSTM 源码</span>
            <select v-if="sourceDocuments && Object.keys(sourceDocuments).length > 1" v-model="documentId" aria-label="选择源码文件">
                <option v-for="(document, id) in sourceDocuments" :key="id" :value="id">{{ document.label }}</option>
            </select>
        </div>
        <div v-if="sourceAvailable === false" class="fcstm-source-panel__unavailable">
            {{ sourceUnavailableReason || '当前模型没有可用的 FCSTM 源码，源码联动已停用。' }}
        </div>
        <pre v-else class="fcstm-source-panel__code"><code v-html="currentSourceHtml"></code></pre>
    </section>
</template>

<style>
.fcstm-source-panel { display: flex; flex: 1 1 0; min-width: 0; min-height: 220px; flex-direction: column; overflow: hidden; border: 1px solid var(--fcstm-border-soft); border-radius: 10px; background: var(--fcstm-surface-raised); }
.fcstm-source-panel__header { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--fcstm-border-soft); color: var(--fcstm-muted); font-weight: 700; }
.fcstm-source-panel__header select {
    max-width: 55%;
    min-width: 0;
    border: 1px solid var(--fcstm-border);
    border-radius: 5px;
    padding: 4px 28px 4px 8px;
    background-color: var(--fcstm-control-bg);
    color: var(--fcstm-fg);
    color-scheme: light dark;
    font: inherit;
}
.fcstm-source-panel__header select:hover,
.fcstm-source-panel__header select:focus {
    border-color: var(--fcstm-accent);
    outline: 2px solid color-mix(in srgb, var(--fcstm-accent) 28%, transparent);
    outline-offset: 1px;
}
.fcstm-source-panel__header option {
    background: var(--fcstm-control-menu-bg);
    color: var(--fcstm-fg);
}
.fcstm-source-panel__code { flex: 1 1 auto; overflow: auto; margin: 0; padding: 12px; color: var(--fcstm-fg); font-family: var(--fcstm-mono); font-size: 12px; line-height: 1.55; tab-size: 4; white-space: normal; }
.fcstm-source-panel__code > code { display: block; min-width: max-content; }
.fcstm-source-panel__unavailable { margin: auto; padding: 24px; color: var(--fcstm-muted); text-align: center; }
.fcstm-source-line {
    position: relative;
    display: block;
    min-height: 1.55em;
    padding: 0 6px 0 4.5em;
    border-left: 3px solid transparent;
    cursor: pointer;
    white-space: pre;
}
.fcstm-source-line::before {
    position: absolute;
    top: 0;
    left: 0;
    width: 3.5em;
    color: var(--fcstm-line-number);
    content: attr(data-line-number);
    text-align: right;
    user-select: none;
}
.fcstm-source-line:hover { background: rgba(45, 106, 168, .10); }
.fcstm-source-line--active { border-left-color: var(--fcstm-accent); background: rgba(45, 106, 168, .13); }
</style>
