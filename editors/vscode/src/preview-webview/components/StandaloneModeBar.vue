<script setup lang="ts">
import type {PreviewWebviewState} from '../types';

defineProps<{mode: NonNullable<PreviewWebviewState['standaloneMode']>}>();
const emit = defineEmits<{(event: 'change', mode: 'fcstm' | 'diagram' | 'compare'): void}>();
</script>

<template>
    <nav class="fcstm-standalone-mode" aria-label="查看模式">
        <button type="button" :class="{active: mode === 'fcstm'}" @click="emit('change', 'fcstm')">FCSTM</button>
        <button type="button" :class="{active: mode === 'diagram'}" @click="emit('change', 'diagram')">图形</button>
        <button type="button" :class="{active: mode === 'compare'}" @click="emit('change', 'compare')">对比</button>
    </nav>
</template>

<style scoped>
.fcstm-standalone-mode { display: flex; gap: 4px; padding: 4px; border: 1px solid var(--fcstm-border-soft); border-radius: 10px; background: var(--fcstm-surface-raised); width: fit-content; }
.fcstm-standalone-mode button { border: 0; border-radius: 7px; padding: 5px 12px; color: var(--fcstm-muted); background: transparent; cursor: pointer; font: inherit; }
.fcstm-standalone-mode button.active { color: var(--fcstm-fg); background: rgba(45, 106, 168, .16); font-weight: 700; }
</style>
