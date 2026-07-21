import {buildFcstmElkGraph} from '../../../jsfcstm/src/diagram/elk-graph';
import {resolveFcstmDiagramPreviewOptions} from '../../../jsfcstm/src/diagram/options';
import type {
    FcstmDiagram, FcstmDiagramState, FcstmDiagramTransition,
    FcstmDiagramPreviewOptionsInput,
} from '../../../jsfcstm/src/diagram/model';
import type {
    PreviewPayload, PreviewStateDetail, PreviewTransitionDetail,
    PreviewWebviewState, SelectionRef,
} from './types';

function collectDetails(diagram: FcstmDiagram): {
    states: PreviewStateDetail[];
    transitions: PreviewTransitionDetail[];
} {
    const states: PreviewStateDetail[] = [];
    const transitions: PreviewTransitionDetail[] = [];
    const visit = (state: FcstmDiagramState) => {
        const kind: PreviewStateDetail['kind'] = state.pseudo
            ? 'pseudoState' : (state.children.length ? 'composite' : 'leaf');
        states.push({
            qualifiedName: state.qualifiedName,
            displayName: state.displayName,
            name: state.name,
            kind,
            events: state.events.map(event => ({name: event.name, displayName: event.displayName})),
            actions: state.actions.map(action => ({
                stage: action.stage,
                aspect: action.aspect,
                mode: action.mode,
                name: action.name,
                globalAspect: action.globalAspect,
                body: action.label,
            })),
            transitionIds: state.transitions.map(item => item.id),
            sourceRange: state.range,
        });
        for (const transition of state.transitions) {
            transitions.push(mapTransition(transition, state));
        }
        for (const child of state.children) visit(child);
    };
    const mapTransition = (transition: FcstmDiagramTransition, owner: FcstmDiagramState): PreviewTransitionDetail => ({
        transitionId: transition.id,
        from: transition.sourceStatePath?.join('.') || `${owner.qualifiedName}.#init`,
        to: transition.targetStatePath?.join('.') || `${owner.qualifiedName}.#exit`,
        kind: transition.forced ? 'forced' : (transition.sourceKind === 'init'
            ? 'entry' : (transition.targetKind === 'exit' ? 'exit' : 'normal')),
        forced: transition.forced,
        eventLabel: transition.triggerLabel || transition.eventName || transition.eventDisplayName,
        eventQualifiedName: transition.eventQualifiedName,
        triggerScope: transition.triggerScope,
        guardLabel: transition.guardLabel,
        effectLines: transition.effectLines,
        eventColor: transition.eventColor,
        sourceRange: transition.range,
    });
    visit(diagram.rootState);
    return {states, transitions};
}

export function buildStandaloneState(
    state: PreviewWebviewState,
    optionsInput: FcstmDiagramPreviewOptionsInput = state.previewOptions,
    collapsedStateIds: ReadonlyArray<string> = state.collapsedStateIds || [],
): PreviewWebviewState {
    const diagram = state.standaloneDiagram;
    if (!state.standalone || !diagram) return state;
    const options = resolveFcstmDiagramPreviewOptions(optionsInput);
    const graph = buildFcstmElkGraph(diagram, options, {
        collapsedStateIds: new Set(collapsedStateIds),
    });
    const details = collectDetails(diagram);
    const payload: PreviewPayload = {
        filePath: '',
        machineName: diagram.machineName,
        summary: diagram.summary,
        variables: diagram.variables,
        eventLegend: diagram.eventLegend,
        graph,
        effectNotes: [],
        options,
        states: details.states,
        transitions: details.transitions,
    };
    return {
        ...state,
        previewOptions: options,
        collapsedStateIds: [...collapsedStateIds],
        payload,
        summary: Object.entries(diagram.summary).map(([label, value]) => ({label, value})),
        variables: diagram.variables.map(item => `${item.name}: ${item.initializer}`),
        sharedEvents: diagram.eventLegend.map(item => ({
            label: item.label,
            qualifiedName: item.qualifiedName,
            transitionCount: item.transitionCount,
            color: item.color,
        })),
    };
}

export function selectionKindForSourceMap(
    sourceMap: PreviewWebviewState['sourceMap'],
    id: string,
): SelectionRef {
    const item = sourceMap?.[id];
    if (!item) return null;
    return {kind: item.kind === 'transition' ? 'transition' : 'state', id};
}
