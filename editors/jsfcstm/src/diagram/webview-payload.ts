/**
 * Package everything the webview preview panel needs in a single JSON
 * payload. The webview bundles elkjs + svg-renderer; the extension host
 * only parses source + ships this payload across the postMessage bridge.
 */
import {buildFcstmDiagramFromDocument} from './builder';
import {buildFcstmElkGraph} from './elk-graph';
import {resolveFcstmDiagramPreviewOptions} from './options';
import {collectFcstmDiagramEffectNotes} from './render';
import type {
    FcstmDiagram,
    FcstmDiagramPreviewOptionsInput,
    FcstmDiagramState,
    FcstmDiagramStateDetail,
    FcstmDiagramTransition,
    FcstmDiagramTransitionDetail,
    FcstmDiagramWebviewPayload,
} from './model';
import type {TextDocumentLike} from '../utils/text';

/**
 * Flatten the hierarchical state model into the detail arrays that the
 * preview's "Details" side panel consumes when the user selects a state
 * or a transition in the diagram.
 */
function collectStateAndTransitionDetails(diagram: FcstmDiagram): {
    states: FcstmDiagramStateDetail[];
    transitions: FcstmDiagramTransitionDetail[];
} {
    const states: FcstmDiagramStateDetail[] = [];
    const transitions: FcstmDiagramTransitionDetail[] = [];

    function pushState(state: FcstmDiagramState): void {
        if (state.root) {
            for (const child of state.children) {
                pushState(child);
            }
            for (const transition of state.transitions) {
                transitions.push(mapTransition(transition, state));
            }
            return;
        }
        const kind: FcstmDiagramStateDetail['kind'] = state.pseudo
            ? 'pseudoState'
            : (state.children.length > 0 ? 'composite' : 'leaf');
        const transitionIds = state.transitions.map(t => t.id);
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
            transitionIds,
            sourceRange: state.range,
        });
        for (const child of state.children) {
            pushState(child);
        }
        for (const transition of state.transitions) {
            transitions.push(mapTransition(transition, state));
        }
    }

    function mapTransition(transition: FcstmDiagramTransition, owner: FcstmDiagramState): FcstmDiagramTransitionDetail {
        const sourcePath = transition.sourceStatePath?.join('.') || `${owner.qualifiedName}.#init`;
        const targetPath = transition.targetStatePath?.join('.') || `${owner.qualifiedName}.#exit`;
        let kind: FcstmDiagramTransitionDetail['kind'];
        if (transition.forced) {
            kind = 'forced';
        } else if (transition.sourceKind === 'init') {
            kind = 'entry';
        } else if (transition.targetKind === 'exit') {
            kind = 'exit';
        } else {
            kind = 'normal';
        }
        return {
            transitionId: transition.id,
            from: sourcePath,
            to: targetPath,
            kind,
            forced: transition.forced,
            eventLabel: transition.triggerLabel || transition.eventName || transition.eventDisplayName,
            eventQualifiedName: transition.eventQualifiedName,
            triggerScope: transition.triggerScope,
            guardLabel: transition.guardLabel,
            effectLines: transition.effectLines,
            eventColor: transition.eventColor,
            sourceRange: transition.range,
        };
    }

    pushState(diagram.rootState);
    return {states, transitions};
}

/**
 * Build the webview payload for a TextDocument-like input. ``collapsedStateIds``
 * survives across re-renders so the webview can re-request a fresh layout
 * with user-toggled state collapse preserved.
 */
export async function buildFcstmDiagramWebviewPayload(
    document: TextDocumentLike,
    previewOptions: FcstmDiagramPreviewOptionsInput = undefined,
    extras: { collapsedStateIds?: ReadonlyArray<string> | ReadonlySet<string> } = {}
): Promise<FcstmDiagramWebviewPayload | null> {
    const diagram = await buildFcstmDiagramFromDocument(document);
    if (!diagram) {
        return null;
    }
    const options = resolveFcstmDiagramPreviewOptions(previewOptions);
    const collapsedSet: ReadonlySet<string> = extras.collapsedStateIds
        ? (extras.collapsedStateIds instanceof Set
            ? extras.collapsedStateIds
            : new Set(extras.collapsedStateIds))
        : new Set<string>();
    const graph = buildFcstmElkGraph(diagram, options, { collapsedStateIds: collapsedSet });
    const effectNotes = collectFcstmDiagramEffectNotes(diagram, options);
    const {states, transitions} = collectStateAndTransitionDetails(diagram);

    return {
        filePath: diagram.filePath,
        machineName: diagram.machineName,
        summary: diagram.summary,
        variables: diagram.variables,
        eventLegend: diagram.eventLegend,
        graph,
        effectNotes,
        options,
        states,
        transitions,
    };
}
