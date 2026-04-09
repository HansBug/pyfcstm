import type {
    Event,
    OnAspect,
    OnStage,
    State,
    StateMachine,
    Transition,
} from '../model';
import {getWorkspaceGraph, type FcstmWorkspaceGraphSnapshot} from '../workspace';
import type {TextDocumentLike} from '../utils/text';
import type {
    FcstmDiagram,
    FcstmDiagramAction,
    FcstmDiagramEvent,
    FcstmDiagramEventLegendItem,
    FcstmDiagramState,
    FcstmDiagramTransition,
    FcstmDiagramVariable,
} from './model';

const DEFAULT_EVENT_PALETTE = [
    '#4E79A7',
    '#F28E2B',
    '#E15759',
    '#76B7B2',
    '#59A14F',
    '#EDC948',
    '#B07AA1',
    '#FF9DA7',
    '#9C755F',
    '#BAB0AC',
];

function joinPath(parts: string[]): string {
    return parts.join('.');
}

function isPrefix(prefix: string[], target: string[] | undefined): target is string[] {
    if (!target || prefix.length > target.length) {
        return false;
    }
    for (let index = 0; index < prefix.length; index += 1) {
        if (prefix[index] !== target[index]) {
            return false;
        }
    }
    return true;
}

function buildVariableList(machine: StateMachine): FcstmDiagramVariable[] {
    return Object.values(machine.defines).map(definition => ({
        name: definition.name,
        valueType: definition.type,
        initializer: definition.init.text || '',
    }));
}

function buildEventLabel(event: Event): string {
    if (event.extraName) {
        return `${event.extraName} (${event.name})`;
    }
    return event.name;
}

function formatEventReference(transition: Transition): string {
    const event = transition.event;
    if (!event) {
        return '';
    }

    if (transition.triggerScope === 'local') {
        return event.name;
    }
    if (transition.triggerScope === 'absolute') {
        return `/${joinPath(event.path.slice(1))}`;
    }
    if (transition.triggerScope === 'chain') {
        return formatChainEventReference(transition);
    }

    if (event.path.length > 1) {
        return `/${joinPath(event.path.slice(1))}`;
    }
    return event.name;
}

function formatTriggerText(transition: Transition): string {
    const event = transition.event;
    if (!event) {
        return '';
    }

    const reference = formatEventReference(transition);
    if (event.extraName) {
        return `${event.extraName} (${reference})`;
    }
    return reference;
}

function formatActionPath(action: OnStage | OnAspect): string {
    return action.statePath
        .map(segment => segment === null ? '<unnamed>' : segment)
        .join('.');
}

function buildActionLabel(action: OnStage | OnAspect): string {
    const prefix = action.is_aspect
        ? `>> ${action.stage} ${action.aspect || ''}`.trim()
        : `${action.stage}${action.aspect ? ` ${action.aspect}` : ''}`;

    if (action.mode === 'abstract') {
        return `${prefix} abstract ${action.funcName}`;
    }
    if (action.mode === 'ref') {
        const target = action.refTargetQualifiedName
            || (action.refStatePath ? joinPath(action.refStatePath) : action.funcName);
        return `${prefix} ref ${target}`;
    }
    if (action.name) {
        return `${prefix} ${action.name}`;
    }
    if (action.operations.length > 0) {
        return `${prefix} {${action.operations.length} op${action.operations.length === 1 ? '' : 's'}}`;
    }
    return `${prefix} {}`;
}

function buildAction(action: OnStage | OnAspect): FcstmDiagramAction {
    return {
        name: action.name,
        qualifiedName: formatActionPath(action),
        stage: action.stage,
        aspect: action.aspect,
        mode: action.mode,
        abstract: action.is_abstract,
        reference: action.is_ref,
        globalAspect: action.is_aspect,
        operationCount: action.operations.length,
        label: buildActionLabel(action),
        range: action.range,
    };
}

function buildEvent(event: Event): FcstmDiagramEvent {
    return {
        name: event.name,
        qualifiedName: event.pathName,
        displayName: event.extraName,
        declared: event.declared,
        origins: [...event.origins],
        range: event.range,
    };
}

function formatChainEventReference(transition: Transition): string {
    const event = transition.event;
    if (!event) {
        return '';
    }

    if (isPrefix(transition.parentPath, event.statePath)) {
        const relativeStatePath = event.statePath.slice(transition.parentPath.length);
        if (relativeStatePath.length > 0) {
            return `${joinPath(relativeStatePath)}.${event.name}`;
        }
        return event.name;
    }

    if (event.path.length > 1) {
        return `/${joinPath(event.path.slice(1))}`;
    }
    return event.name;
}

function formatTriggerLabel(transition: Transition): string | undefined {
    if (!transition.event) {
        return undefined;
    }

    if (transition.triggerScope === 'local') {
        return `:: ${formatTriggerText(transition)}`;
    }

    return `: ${formatTriggerText(transition)}`;
}

function buildEffectLines(transition: Transition): string[] {
    if (transition.effects.length === 0) {
        return [];
    }

    const lines: string[] = ['effect {'];
    for (const statement of transition.effects) {
        const rawText = statement.text || '';
        const statementLines = rawText
            .split(/\r?\n/)
            .map(line => line.trim())
            .filter(Boolean);

        if (statementLines.length === 0) {
            lines.push('    ...');
            continue;
        }

        for (const line of statementLines) {
            lines.push(`    ${line}`);
        }
    }
    lines.push('}');
    return lines;
}

function buildTransitionLabel(
    sourceLabel: string,
    targetLabel: string,
    triggerLabel: string | undefined,
    guardLabel: string | undefined,
    hasEffects: boolean,
    forced: boolean
): string {
    const parts: string[] = [];

    if (forced) {
        parts.push('!');
    }
    parts.push(sourceLabel, '->', targetLabel);

    if (triggerLabel) {
        parts.push(triggerLabel);
    }
    if (guardLabel) {
        parts.push(`if [${guardLabel}]`);
    }
    if (hasEffects) {
        parts.push('effect');
    }

    return parts.join(' ').replace(/\s+/g, ' ').trim();
}

function buildTransition(
    transition: Transition,
    eventColors: Record<string, string>
): FcstmDiagramTransition {
    const sourceLabel = transition.fromState === 'INIT_STATE' ? '[*]' : transition.fromState;
    const targetLabel = transition.toState === 'EXIT_STATE' ? '[*]' : transition.toState;
    const triggerLabel = formatTriggerLabel(transition);
    const guardLabel = transition.guard ? transition.guard.text || '' : undefined;
    const effectLines = buildEffectLines(transition);
    const eventQualifiedName = transition.event?.pathName;

    return {
        id: `${joinPath(transition.parentPath)}::${sourceLabel}->${targetLabel}::${transition.range.start.line}:${transition.range.start.character}`,
        sourceLabel,
        targetLabel,
        triggerLabel,
        guardLabel,
        effectLines,
        label: buildTransitionLabel(
            sourceLabel,
            targetLabel,
            triggerLabel,
            guardLabel,
            effectLines.length > 0,
            transition.forced
        ),
        forced: transition.forced,
        sourceKind: transition.sourceKind,
        targetKind: transition.targetKind,
        sourceStatePath: transition.sourceStatePath ? [...transition.sourceStatePath] : undefined,
        targetStatePath: transition.targetStatePath ? [...transition.targetStatePath] : undefined,
        eventQualifiedName,
        eventColor: eventQualifiedName ? eventColors[eventQualifiedName] : undefined,
        range: transition.range,
    };
}

function collectEventColors(machine: StateMachine): Record<string, string> {
    const counts = new Map<string, number>();
    for (const transition of machine.allTransitions) {
        if (transition.event) {
            counts.set(
                transition.event.pathName,
                (counts.get(transition.event.pathName) || 0) + 1
            );
        }
    }

    const result: Record<string, string> = {};
    let colorIndex = 0;
    for (const eventPath of [...counts.keys()].sort()) {
        if ((counts.get(eventPath) || 0) < 2) {
            continue;
        }
        result[eventPath] = DEFAULT_EVENT_PALETTE[colorIndex % DEFAULT_EVENT_PALETTE.length];
        colorIndex += 1;
    }
    return result;
}

function buildEventLegend(machine: StateMachine, eventColors: Record<string, string>): FcstmDiagramEventLegendItem[] {
    const counts = new Map<string, number>();
    for (const transition of machine.allTransitions) {
        if (transition.event) {
            counts.set(
                transition.event.pathName,
                (counts.get(transition.event.pathName) || 0) + 1
            );
        }
    }

    return Object.keys(eventColors)
        .sort()
        .map(eventPath => {
            const event = machine.lookups.eventsByPathName[eventPath];
            return {
                qualifiedName: eventPath,
                label: event ? buildEventLabel(event) : eventPath.split('.').pop() || eventPath,
                transitionCount: counts.get(eventPath) || 0,
                color: eventColors[eventPath],
            };
        });
}

function buildStateNode(
    state: State,
    eventColors: Record<string, string>
): FcstmDiagramState {
    const actions: FcstmDiagramAction[] = [];
    const enters = state.onEnters.map(buildAction);
    const durings = state.onDurings.map(buildAction);
    const exits = state.onExits.map(buildAction);
    const aspects = state.onDuringAspects.map(buildAction);
    actions.push(...enters, ...durings, ...exits, ...aspects);

    return {
        id: state.pathName,
        name: state.name,
        qualifiedName: state.pathName,
        displayName: state.extraName,
        pseudo: state.isPseudo,
        leaf: state.isLeafState,
        root: state.isRootState,
        range: state.range,
        events: Object.values(state.events).map(buildEvent),
        actions,
        transitions: state.transitions.map(transition => buildTransition(transition, eventColors)),
        children: Object.values(state.substates).map(child => buildStateNode(child, eventColors)),
    };
}

/**
 * Build diagram IR from an already-hydrated jsfcstm state-machine model.
 */
export function buildFcstmDiagramFromStateMachine(machine: StateMachine | null): FcstmDiagram | null {
    if (!machine) {
        return null;
    }

    const eventColors = collectEventColors(machine);

    return {
        kind: 'diagram',
        filePath: machine.filePath,
        machineName: machine.rootState.name,
        summary: {
            variables: Object.keys(machine.defines).length,
            states: machine.allStates.length,
            events: machine.allEvents.length,
            transitions: machine.allTransitions.length,
            actions: machine.allActions.length,
        },
        variables: buildVariableList(machine),
        eventLegend: buildEventLegend(machine, eventColors),
        rootState: buildStateNode(machine.rootState, eventColors),
    };
}

/**
 * Build diagram IR from a workspace snapshot, including import-expanded models.
 */
export function buildFcstmDiagramFromWorkspaceSnapshot(
    snapshot: FcstmWorkspaceGraphSnapshot,
    filePath?: string
): FcstmDiagram | null {
    const targetFile = filePath || snapshot.rootFile;
    const node = snapshot.nodes[targetFile];
    return buildFcstmDiagramFromStateMachine(node ? node.model : null);
}

/**
 * Build diagram IR directly from a text document.
 *
 * This path uses the workspace graph so unsaved editor contents and imported
 * modules can participate in the preview.
 */
export async function buildFcstmDiagramFromDocument(
    document: TextDocumentLike
): Promise<FcstmDiagram | null> {
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    return buildFcstmDiagramFromWorkspaceSnapshot(snapshot);
}

export {
    buildActionLabel as formatFcstmDiagramActionLabel,
    buildEventLabel as formatFcstmDiagramEventLabel,
    buildTransitionLabel as formatFcstmDiagramTransitionLabel,
};
