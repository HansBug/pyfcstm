<script setup lang="ts">
import {computed} from 'vue';
import {NButton, NTag, NEmpty} from 'naive-ui';
import type {
    PreviewWebviewState, SelectionRef,
    PreviewStateDetail, PreviewTransitionDetail, TextRange,
} from '../types';

const props = defineProps<{
    state: PreviewWebviewState;
    selection: SelectionRef;
}>();
const emit = defineEmits<{
    (e: 'revealSource', range: TextRange): void;
    (e: 'select', sel: SelectionRef): void;
}>();

const detail = computed<PreviewStateDetail | PreviewTransitionDetail | null>(() => {
    const sel = props.selection;
    const payload = props.state.payload;
    if (!sel || !payload) return null;
    if (sel.kind === 'transition') {
        return payload.transitions.find(t => t.transitionId === sel.id) || null;
    }
    return payload.states.find(s => s.qualifiedName === sel.id) || null;
});

const isTransition = computed(() =>
    props.selection?.kind === 'transition' && detail.value !== null
);
const stateDetail = computed(() =>
    (!isTransition.value && detail.value) as PreviewStateDetail | null
);
const transitionDetail = computed(() =>
    (isTransition.value && detail.value) as PreviewTransitionDetail | null
);

function kindLabel() {
    if (isTransition.value && transitionDetail.value) {
        return (transitionDetail.value.forced ? 'forced ' : '') + transitionDetail.value.kind;
    }
    return stateDetail.value?.kind || '';
}

function displayTitle() {
    if (stateDetail.value) {
        return stateDetail.value.displayName
            ? `${stateDetail.value.displayName} (${stateDetail.value.name})`
            : stateDetail.value.name;
    }
    if (transitionDetail.value) {
        return `${transitionDetail.value.from} → ${transitionDetail.value.to}`;
    }
    return 'Details';
}

function revealCurrent() {
    const d = detail.value;
    if (d && d.sourceRange) {
        emit('revealSource', d.sourceRange);
    }
}

function jumpToTransition(id: string) {
    emit('select', {kind: 'transition', id});
}
</script>

<template>
    <div class="fcstm-details">
        <div class="fcstm-details__header">
            <div class="fcstm-details__title-block">
                <div class="fcstm-details__title">{{ displayTitle() }}</div>
                <n-tag v-if="detail" round size="small" :bordered="false">
                    {{ kindLabel() }}
                </n-tag>
            </div>
            <n-button
                v-if="detail && detail.sourceRange"
                size="small" quaternary round
                @click="revealCurrent"
            >Reveal source</n-button>
        </div>
        <div v-if="!detail" class="fcstm-details__hint">
            Plain click on a state or transition to inspect it.
            Ctrl/Cmd+click jumps to the source. Click empty space to clear.
        </div>
        <div v-else class="fcstm-details__sections">
            <template v-if="stateDetail">
                <section>
                    <div class="fcstm-details__section-title">Qualified name</div>
                    <div class="fcstm-details__mono">{{ stateDetail.qualifiedName }}</div>
                </section>
                <section v-if="stateDetail.events.length">
                    <div class="fcstm-details__section-title">Events</div>
                    <ul class="fcstm-details__list">
                        <li v-for="ev in stateDetail.events" :key="ev.name">
                            {{ ev.displayName ? ev.displayName + ' (' + ev.name + ')' : ev.name }}
                        </li>
                    </ul>
                </section>
                <section v-if="stateDetail.actions.length">
                    <div class="fcstm-details__section-title">Actions</div>
                    <ul class="fcstm-details__list">
                        <li v-for="(action, idx) in stateDetail.actions" :key="idx">
                            <n-tag size="tiny" round :bordered="false" class="fcstm-details__badge">
                                {{ action.stage }}
                            </n-tag>
                            <n-tag v-if="action.aspect" size="tiny" round :bordered="false" class="fcstm-details__badge">
                                {{ action.aspect }}
                            </n-tag>
                            <n-tag v-if="action.globalAspect" size="tiny" round :bordered="false" type="warning" class="fcstm-details__badge">
                                &gt;&gt; aspect
                            </n-tag>
                            <n-tag v-if="action.mode && action.mode !== 'operations'" size="tiny" round :bordered="false" type="info" class="fcstm-details__badge">
                                {{ action.mode }}
                            </n-tag>
                            <span>{{ action.name || action.body || '' }}</span>
                        </li>
                    </ul>
                </section>
                <section v-if="stateDetail.transitionIds.length">
                    <div class="fcstm-details__section-title">Outgoing transitions</div>
                    <ul class="fcstm-details__list">
                        <li v-for="tid in stateDetail.transitionIds" :key="tid">
                            <a href="#" class="fcstm-details__link" @click.prevent="jumpToTransition(tid)">
                                {{ tid }}
                            </a>
                        </li>
                    </ul>
                </section>
            </template>
            <template v-if="transitionDetail">
                <section v-if="transitionDetail.eventLabel">
                    <div class="fcstm-details__section-title">Event</div>
                    <div>
                        {{ transitionDetail.eventLabel }}
                        <span v-if="transitionDetail.triggerScope" class="fcstm-details__muted">
                            ({{ transitionDetail.triggerScope }})
                        </span>
                    </div>
                    <div v-if="transitionDetail.eventQualifiedName" class="fcstm-details__muted fcstm-details__mono">
                        {{ transitionDetail.eventQualifiedName }}
                    </div>
                </section>
                <section v-if="transitionDetail.guardLabel">
                    <div class="fcstm-details__section-title">Guard</div>
                    <div class="fcstm-details__mono">[{{ transitionDetail.guardLabel }}]</div>
                </section>
                <section v-if="transitionDetail.effectLines && transitionDetail.effectLines.length">
                    <div class="fcstm-details__section-title">Effect</div>
                    <pre class="fcstm-details__code">{{ transitionDetail.effectLines.join('\n') }}</pre>
                </section>
            </template>
        </div>
    </div>
</template>

<style>
.fcstm-details {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 14px;
    border: 1px solid var(--fcstm-border-soft);
    border-radius: 14px;
    background: var(--fcstm-surface-raised);
}
.fcstm-details__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}
.fcstm-details__title-block {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    min-width: 0;
}
.fcstm-details__title {
    font-weight: 700;
    font-size: 13px;
    word-break: break-all;
}
.fcstm-details__hint {
    font-size: 12px;
    color: var(--fcstm-muted);
    padding: 8px 0;
}
.fcstm-details__sections {
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.fcstm-details__section-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--fcstm-muted);
    font-weight: 700;
    margin-bottom: 4px;
}
.fcstm-details__list {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
}
.fcstm-details__badge {
    margin-right: 4px;
}
.fcstm-details__mono {
    font-family: var(--fcstm-mono);
    font-size: 12px;
    word-break: break-all;
}
.fcstm-details__muted {
    color: var(--fcstm-muted);
    font-size: 11px;
}
.fcstm-details__code {
    margin: 0;
    padding: 8px 10px;
    background: rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    font-family: var(--fcstm-mono);
    font-size: 11px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
}
.fcstm-details__link {
    color: var(--fcstm-accent);
    text-decoration: none;
    font-family: var(--fcstm-mono);
    font-size: 12px;
}
.fcstm-details__link:hover { text-decoration: underline; }
</style>
