<script setup lang="ts">
import {NSelect, NCheckbox, NSpace} from 'naive-ui';
import type {PreviewResolvedOptions} from '../types';

const props = defineProps<{options: PreviewResolvedOptions}>();
const emit = defineEmits<{
    (e: 'patch', options: Partial<PreviewResolvedOptions>): void;
}>();

const effectOptions = [
    {label: 'Hide effects',   value: 'hide'},
    {label: 'Inline effects', value: 'inline'},
    {label: 'Note effects',   value: 'note'},
];

function patch(key: keyof PreviewResolvedOptions, value: unknown) {
    emit('patch', {[key]: value} as Partial<PreviewResolvedOptions>);
}
</script>

<template>
    <div class="fcstm-options">
        <div class="fcstm-options__group">
            <label class="fcstm-options__label">Effects</label>
            <n-select
                :value="props.options.transitionEffectMode"
                size="small"
                :options="effectOptions"
                :consistent-menu-width="false"
                style="min-width: 132px"
                @update:value="(v: string) => patch('transitionEffectMode', v)"
            />
        </div>

        <n-space size="small" align="center" class="fcstm-options__toggles">
            <n-checkbox
                :checked="props.options.showEvents"
                @update:checked="(v: boolean) => patch('showEvents', v)"
            >Events</n-checkbox>
            <n-checkbox
                :checked="props.options.showTransitionGuards"
                @update:checked="(v: boolean) => patch('showTransitionGuards', v)"
            >Guards</n-checkbox>
        </n-space>
    </div>
</template>

<style scoped>
.fcstm-options {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px 14px;
    padding: 8px 14px;
    border: 1px solid var(--fcstm-border-soft);
    border-radius: 12px;
    background: var(--fcstm-surface-raised);
}
.fcstm-options__group {
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.fcstm-options__label {
    font-size: 10px;
    letter-spacing: 0.06em;
    color: var(--fcstm-muted);
    text-transform: uppercase;
    font-weight: 700;
}
.fcstm-options__toggles {
    flex-wrap: wrap;
    row-gap: 6px;
}
</style>
