<script setup lang="ts">
import {NAlert} from 'naive-ui';
import type {PreviewDiagnosticView} from '../types';

defineProps<{diagnostics: PreviewDiagnosticView[]}>();
</script>

<template>
    <div v-if="diagnostics.length" class="fcstm-diagnostics">
        <div class="fcstm-diagnostics__title">Diagnostics</div>
        <div class="fcstm-diagnostics__list">
            <n-alert
                v-for="(d, i) in diagnostics"
                :key="i"
                :type="d.severity === 'error' ? 'error' : 'warning'"
                size="small"
                :show-icon="false"
                :bordered="false"
                class="fcstm-diagnostics__item"
            >
                <template #header>
                    <span class="fcstm-diagnostics__meta">
                        {{ d.severity.toUpperCase() }} · {{ d.location }}
                    </span>
                </template>
                {{ d.message }}
            </n-alert>
        </div>
    </div>
</template>

<style>
.fcstm-diagnostics {
    border: 1px solid var(--fcstm-border-soft);
    border-radius: 12px;
    background: var(--fcstm-surface-raised);
    padding: 10px 12px;
}
.fcstm-diagnostics__title {
    font-weight: 700;
    font-size: 12px;
    margin-bottom: 6px;
}
.fcstm-diagnostics__list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.fcstm-diagnostics__item {
    border-radius: 8px;
}
.fcstm-diagnostics__meta {
    font-size: 10px;
    letter-spacing: 0.04em;
    color: var(--fcstm-muted);
    text-transform: uppercase;
}
</style>
