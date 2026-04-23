<script setup lang="ts">
import type {PreviewWebviewState} from '../types';

defineProps<{state: PreviewWebviewState}>();
</script>

<template>
    <div class="fcstm-toolbar">
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
    </div>
</template>

<style scoped>
.fcstm-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    padding: 8px 14px;
    border: 1px solid var(--fcstm-border-soft);
    border-radius: 12px;
    background: var(--fcstm-surface-raised);
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
</style>
