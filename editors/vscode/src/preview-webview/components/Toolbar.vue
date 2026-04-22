<script setup lang="ts">
import {computed, h} from 'vue';
import {NButton, NButtonGroup, NTag, NIcon, NTooltip} from 'naive-ui';
import {
    BrowsersOutline, EyeOutline,
    ScanOutline, ResizeOutline,
    DownloadOutline, Image as ImageOutline,
} from '@vicons/ionicons5';
import type {PreviewWebviewState} from '../types';

const props = defineProps<{state: PreviewWebviewState}>();
const emit = defineEmits<{
    (e: 'setLayoutMode', mode: 'side' | 'alone'): void;
    (e: 'exportSvg', svg: string): void;
    (e: 'exportPng', base64: string): void;
    (e: 'exportError', message: string): void;
    (e: 'fit'): void;
    (e: 'actual'): void;
}>();

const title = computed(() => {
    if (props.state.rootStateName) return `${props.state.title} · ${props.state.rootStateName}`;
    return props.state.title;
});

const statusType = computed(() => {
    if (props.state.status === 'error') return 'error';
    if (props.state.status === 'warning') return 'warning';
    return 'info';
});

function withIcon(Icon: unknown) {
    return () => h(NIcon, null, {default: () => h(Icon as never)});
}

function requestFit() {
    window.dispatchEvent(new CustomEvent('fcstm-fit'));
}
function requestActual() {
    window.dispatchEvent(new CustomEvent('fcstm-actual'));
}
function requestExportSvg() {
    window.dispatchEvent(new CustomEvent('fcstm-export-svg'));
}
function requestExportPng() {
    window.dispatchEvent(new CustomEvent('fcstm-export-png'));
}
</script>

<template>
    <div class="fcstm-toolbar">
        <div class="fcstm-toolbar__title-block">
            <div class="fcstm-toolbar__title">{{ title }}</div>
            <div class="fcstm-toolbar__path">{{ state.filePath || '<memory>' }}</div>
        </div>

        <n-tag :type="statusType" round size="small" :bordered="false">
            {{ state.statusText }}
        </n-tag>

        <div class="fcstm-toolbar__summary">
            <span
                v-for="entry in state.summary"
                :key="entry.label"
                class="fcstm-toolbar__summary-chip"
            >
                <span class="fcstm-toolbar__summary-label">{{ entry.label }}</span>
                <span class="fcstm-toolbar__summary-value">{{ entry.value }}</span>
            </span>
        </div>

        <div class="fcstm-toolbar__actions">
            <n-button-group size="small">
                <n-tooltip :delay="400">
                    <template #trigger>
                        <n-button
                            quaternary round
                            :focusable="false"
                            :render-icon="withIcon(BrowsersOutline)"
                            @click="emit('setLayoutMode', 'side')"
                        >Split</n-button>
                    </template>
                    Split view — diagram beside the editor
                </n-tooltip>
                <n-tooltip :delay="400">
                    <template #trigger>
                        <n-button
                            quaternary round
                            :focusable="false"
                            :render-icon="withIcon(EyeOutline)"
                            @click="emit('setLayoutMode', 'alone')"
                        >Diagram</n-button>
                    </template>
                    Diagram only — preview takes the full column
                </n-tooltip>
            </n-button-group>

            <n-button-group size="small">
                <n-tooltip :delay="400">
                    <template #trigger>
                        <n-button
                            quaternary round
                            :focusable="false"
                            :render-icon="withIcon(ScanOutline)"
                            @click="requestFit"
                        >Fit</n-button>
                    </template>
                    Fit diagram to view
                </n-tooltip>
                <n-tooltip :delay="400">
                    <template #trigger>
                        <n-button
                            quaternary round
                            :focusable="false"
                            :render-icon="withIcon(ResizeOutline)"
                            @click="requestActual"
                        >1:1</n-button>
                    </template>
                    Actual size (100%)
                </n-tooltip>
            </n-button-group>

            <n-button-group size="small">
                <n-tooltip :delay="400">
                    <template #trigger>
                        <n-button
                            quaternary round
                            :focusable="false"
                            :render-icon="withIcon(DownloadOutline)"
                            @click="requestExportSvg"
                        >SVG</n-button>
                    </template>
                    Export SVG
                </n-tooltip>
                <n-tooltip :delay="400">
                    <template #trigger>
                        <n-button
                            quaternary round
                            :focusable="false"
                            :render-icon="withIcon(ImageOutline)"
                            @click="requestExportPng"
                        >PNG</n-button>
                    </template>
                    Export PNG (2× raster)
                </n-tooltip>
            </n-button-group>
        </div>
    </div>
</template>

<style scoped>
.fcstm-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    padding: 10px 14px;
    border: 1px solid var(--fcstm-border);
    border-radius: 14px;
    background: var(--fcstm-surface-raised);
    backdrop-filter: blur(6px);
}
.fcstm-toolbar__title-block {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1 1 auto;
}
.fcstm-toolbar__title {
    font-weight: 700;
    font-size: 14px;
    color: var(--fcstm-fg);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.fcstm-toolbar__path {
    font-size: 11px;
    color: var(--fcstm-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.fcstm-toolbar__summary {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}
.fcstm-toolbar__summary-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(45, 106, 168, 0.10);
    font-size: 11px;
    color: var(--fcstm-muted);
}
.fcstm-toolbar__summary-value {
    color: var(--fcstm-fg);
    font-weight: 700;
}
.fcstm-toolbar__actions {
    display: flex;
    gap: 6px;
    align-items: center;
}
</style>
