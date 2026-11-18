/**
 * Regions seen as state-shaped scopes.
 *
 * A region owns states, transitions, forced transitions, events and during
 * aspects exactly as a state does, and nothing else: no lifecycle actions, no
 * imports, no history, no display name. Treating it as a state-shaped
 * definition lets the model builder, the import assembly and the analyzers use
 * one set of scope rules for both; the few places where a region differs from a
 * state (it is not a transition endpoint, it is not stoppable, it is not
 * counted as a state) check ``isRegionView`` or the model's ``isRegion``.
 *
 * The module contains:
 * - :func:`regionAsStateDefinition` - the state-shaped view of one region
 * - :func:`astNamespaceChildren` - child states followed by the views of the regions
 * - :func:`astRegionViews` - the views of the regions of one state
 */
import type {FcstmAstRegionDefinition, FcstmAstStateDefinition} from './model';

const views = new WeakMap<FcstmAstRegionDefinition, FcstmAstStateDefinition>();

/**
 * Describe a region as a state-shaped definition.
 *
 * The view is created once per region and reused, so callers may use it as a
 * map key or compare it by identity. It shares the region's child arrays; it
 * never copies or modifies them.
 *
 * @param region A parsed region declaration.
 * @returns A definition with the region's name, states, transitions, forced
 *   transitions, events and aspects, empty lifecycle actions, imports, regions
 *   and histories, and ``isRegionView`` set.
 */
export function regionAsStateDefinition(region: FcstmAstRegionDefinition): FcstmAstStateDefinition {
    const cached = views.get(region);
    if (cached) return cached;
    const view: FcstmAstStateDefinition = {
        kind: 'stateDefinition',
        pyNodeType: 'StateDefinition',
        range: region.range,
        text: region.text,
        name: region.name,
        nameRange: region.nameRange,
        pseudo: false,
        isPseudo: false,
        is_pseudo: false,
        composite: true,
        statements: region.statements,
        events: region.events,
        imports: [],
        substates: region.substates,
        regions: [],
        transitions: region.transitions,
        enters: [],
        durings: [],
        exits: [],
        duringAspects: region.duringAspects,
        during_aspects: region.during_aspects,
        forceTransitions: region.forceTransitions,
        force_transitions: region.force_transitions,
        histories: [],
        doc: region.doc,
        isRegionView: true,
    };
    views.set(region, view);
    return view;
}

/**
 * List the regions of a state as state-shaped views, in declaration order.
 *
 * @param node A state definition (or the view of a region, which has none).
 */
export function astRegionViews(node: FcstmAstStateDefinition): FcstmAstStateDefinition[] {
    return (node.regions ?? []).map(regionAsStateDefinition);
}

/**
 * List the child scopes of a state: its states, then its regions.
 *
 * A state has either states or regions, so one of the two parts is empty.
 *
 * @param node A state definition or the view of a region.
 */
export function astNamespaceChildren(node: FcstmAstStateDefinition): FcstmAstStateDefinition[] {
    return [...node.substates, ...astRegionViews(node)];
}
