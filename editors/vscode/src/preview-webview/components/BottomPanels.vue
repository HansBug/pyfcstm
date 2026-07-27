<script setup lang="ts">
import {NCollapse, NCollapseItem, NTag} from 'naive-ui';
import type {PreviewSharedEventView} from '../types';

defineProps<{
    variables: string[];
    sharedEvents: PreviewSharedEventView[];
}>();
</script>

<template>
    <div class="fcstm-bottom">
        <div v-if="variables.length" class="fcstm-bottom__card">
            <n-collapse>
                <n-collapse-item>
                    <template #header>
                        <div class="fcstm-bottom__summary">
                            <span class="fcstm-bottom__title">Variables</span>
                            <n-tag size="tiny" round :bordered="false">
                                {{ variables.length }}
                            </n-tag>
                        </div>
                    </template>
                    <ul class="fcstm-bottom__list">
                        <li v-for="(v, i) in variables" :key="i" class="fcstm-bottom__mono">{{ v }}</li>
                    </ul>
                </n-collapse-item>
            </n-collapse>
        </div>
        <div v-if="sharedEvents.length" class="fcstm-bottom__card">
            <n-collapse>
                <n-collapse-item>
                    <template #header>
                        <div class="fcstm-bottom__summary">
                            <span class="fcstm-bottom__title">Shared Events</span>
                            <n-tag size="tiny" round :bordered="false">
                                {{ sharedEvents.length }}
                            </n-tag>
                        </div>
                    </template>
                    <ul class="fcstm-bottom__list">
                        <li v-for="ev in sharedEvents" :key="ev.qualifiedName" class="fcstm-bottom__event">
                            <span class="fcstm-bottom__swatch" :style="{backgroundColor: ev.color}"></span>
                            <div>
                                <div>{{ ev.label }}</div>
                                <div class="fcstm-bottom__muted">
                                    {{ ev.transitionCount }} transition{{ ev.transitionCount === 1 ? '' : 's' }} · {{ ev.qualifiedName }}
                                </div>
                            </div>
                        </li>
                    </ul>
                </n-collapse-item>
            </n-collapse>
        </div>
    </div>
</template>

<style>
.fcstm-bottom {
    display: grid;
    /* Two cards sit side by side; a lone card spans the row instead of
       leaving the other half of the shell empty. The min() keeps the track
       from flooring at 320px in a narrower shell, which would push the cards
       past the right edge and add a horizontal scrollbar. */
    grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
    gap: 10px;
}
.fcstm-bottom__card {
    border: 1px solid var(--fcstm-border-soft);
    border-radius: 12px;
    background: var(--fcstm-surface-raised);
    padding: 4px 12px;
}
.fcstm-bottom__summary {
    display: flex;
    align-items: center;
    gap: 8px;
}
.fcstm-bottom__title {
    font-weight: 700;
    font-size: 12px;
}
.fcstm-bottom__list {
    margin: 0;
    padding: 4px 0 10px 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.fcstm-bottom__mono {
    font-family: var(--fcstm-mono);
    font-size: 11px;
    word-break: break-word;
}
.fcstm-bottom__event {
    display: grid;
    grid-template-columns: 10px 1fr;
    gap: 10px;
    align-items: start;
}
.fcstm-bottom__swatch {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    margin-top: 4px;
}
.fcstm-bottom__muted {
    font-size: 10px;
    color: var(--fcstm-muted);
    margin-top: 2px;
}
</style>
