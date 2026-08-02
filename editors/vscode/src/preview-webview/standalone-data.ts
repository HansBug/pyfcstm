import {buildFcstmElkGraph} from '../../../jsfcstm/src/diagram/elk-graph';
import {collectFcstmDiagramEffectNotes} from '../../../jsfcstm/src/diagram/render';
import {resolveFcstmDiagramPreviewOptions} from '../../../jsfcstm/src/diagram/options';
import type {
    FcstmDiagram, FcstmDiagramState, FcstmDiagramTransition,
} from '../../../jsfcstm/src/diagram/model';
import type {
    PreviewPayload, PreviewResolvedOptions, PreviewStateDetail,
    PreviewTransitionDetail, PreviewWebviewState, SelectionRef,
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
    collapsedStateIds: ReadonlyArray<string> = state.collapsedStateIds || [],
): PreviewWebviewState {
    const diagram = state.standaloneDiagram;
    if (!state.standalone || !diagram) return state;
    // On the first build `previewOptions` still holds what the document wrote,
    // which is sparse by design; afterwards it holds the resolved set and
    // `documentOptions` holds that original. Keeping it is what stops a reader's
    // first click from dropping the author's `detailLevel` and `direction`,
    // neither of which the options bar can put back.
    const documentOptions = state.documentOptions
        || (state.previewOptions as Partial<PreviewResolvedOptions>)
        || {};
    // Two sparse records, merged. Never the resolved set: an explicit value
    // beats the preset, so resolving one and feeding it back makes every
    // default permanent -- which is how choosing `hide` once used to leave the
    // effect mode stuck there.
    // No way in but the merge. There used to be a parameter for an explicit
    // input, and every defect this file has had came through it: a caller
    // handing back the resolved set froze each default as a choice, and a
    // caller handing back only the reader's record dropped the document's.
    // Both are now unsayable rather than merely discouraged.
    const options = resolveFcstmDiagramPreviewOptions({
        ...documentOptions,
        ...(state.optionOverrides || {}),
    });
    const graph = buildFcstmElkGraph(diagram, options, {
        collapsedStateIds: new Set(collapsedStateIds),
    });
    const details = collectDetails(diagram);
    const showsEventLegend =
        options.eventVisualizationMode === 'legend' || options.eventVisualizationMode === 'both';
    const payload: PreviewPayload = {
        filePath: '',
        machineName: diagram.machineName,
        summary: diagram.summary,
        variables: diagram.variables,
        eventLegend: diagram.eventLegend,
        graph,
        // The host path has collected these since it was written
        // (`webview-payload.ts`); the standalone builder shipped an empty array,
        // so `transitionEffectMode: note` had nowhere to put an effect and the
        // side panel stayed blank whatever the detail level said.
        effectNotes: collectFcstmDiagramEffectNotes(diagram, options),
        options,
        states: details.states,
        transitions: details.transitions,
    };
    return {
        ...state,
        previewOptions: options,
        documentOptions,
        optionOverrides: state.optionOverrides,
        collapsedStateIds: [...collapsedStateIds],
        payload,
        summary: Object.entries(diagram.summary).map(([label, value]) => ({label, value})),
        variables: diagram.variables.map(item => `${item.name}: ${item.initializer}`),
        // `none` and `color` put events on the edges and nowhere else, so the
        // legend is not always wanted. The host path gates this the same way
        // (`preview.ts`, `buildSharedEvents`); the standalone builder listed
        // every event whatever the mode asked for.
        sharedEvents: showsEventLegend
            ? diagram.eventLegend.map(item => ({
                label: item.label,
                qualifiedName: item.qualifiedName,
                transitionCount: item.transitionCount,
                color: item.color,
            }))
            : [],
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
