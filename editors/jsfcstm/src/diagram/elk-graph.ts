/**
 * FCSTM diagram IR -> ELK compound-graph input.
 *
 * Pure function: no elkjs or DOM references here so both the extension
 * host and the webview bundle can import this module and reproduce the
 * same input graph bit-for-bit.
 */
import type {
    FcstmDiagram,
    FcstmDiagramAction,
    FcstmDiagramEvent,
    FcstmDiagramState,
    FcstmDiagramTransition,
    FcstmElkEdge,
    FcstmElkGraph,
    FcstmElkNode,
    ResolvedFcstmDiagramPreviewOptions,
} from './model';

// Character metrics for a monospaced 14px font, used to pre-measure label
// boxes so ELK can pack them without our SVG labels overflowing later.
const CHAR_WIDTH = 8.2;
const LINE_HEIGHT = 18;
const STATE_TITLE_HEIGHT = 30;
const LEAF_MIN_WIDTH = 140;
const LEAF_MIN_HEIGHT = 58;

/**
 * Glyphs used to visually distinguish transition-label components from
 * each other. Event / guard / effect each get their own mark so labels
 * stay readable even without a background rectangle.
 */
export const TRANSITION_LABEL_GLYPHS = {
    event: '●',
    guard: '◇',
    effect: '▸',
};

/** Measure a (possibly multi-line) label rectangle for ELK. */
export function measureLabel(
    text: string,
    padX = 16,
    padY = 8
): { width: number; height: number } {
    const lines = String(text).split('\n');
    const longest = Math.max(1, ...lines.map(line => line.length));
    const width = Math.ceil(longest * CHAR_WIDTH + padX * 2);
    const height = Math.ceil(lines.length * LINE_HEIGHT + padY * 2);
    return { width, height };
}

function truncate(value: string, maxLength: number): string {
    if (value.length <= maxLength) {
        return value;
    }
    return `${value.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function formatEventSummary(event: FcstmDiagramEvent): string {
    return event.displayName ? `${event.displayName} (${event.name})` : event.name;
}

function formatActionSummary(action: FcstmDiagramAction): string {
    const aspect = action.aspect ? ` ${action.aspect}` : '';
    const prefix = action.globalAspect ? '>> ' : '';
    if (action.mode === 'abstract') {
        return `${prefix}${action.stage}${aspect} abstract ${action.name || ''}`.trim();
    }
    if (action.mode === 'ref') {
        return `${prefix}${action.stage}${aspect} ref`;
    }
    return `${prefix}${action.name ? `${action.stage}${aspect} ${action.name}` : `${action.stage}${aspect}`}`;
}

/**
 * Pick the trigger label for a transition, following the Phase-10
 * eventNameFormat ordering.
 */
function formatTriggerLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): string {
    if (!options.showEvents || !transition.eventQualifiedName) {
        return '';
    }
    for (const part of options.eventNameFormat) {
        const candidate = (() => {
            switch (part) {
                case 'extra_name':
                    return transition.eventDisplayName;
                case 'name':
                    return transition.eventName;
                case 'path':
                    return transition.eventAbsolutePath;
                case 'relpath':
                    return transition.eventRelativePath;
                default:
                    return undefined;
            }
        })();
        if (candidate) {
            return candidate;
        }
    }
    return transition.eventName || '';
}

function formatGuardLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): string {
    if (!options.showTransitionGuards || !transition.guardLabel) {
        return '';
    }
    return `[${transition.guardLabel.trim()}]`;
}

/**
 * For each transition, decide what goes into the edge label and whether
 * the effect needs to be deferred to the side-panel notes.
 */
function resolveTransitionLabeling(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): { eventLabel: string; guardLabel: string; inlineEffect: string; hasNoteEffect: boolean } {
    const eventLabel = formatTriggerLabel(transition, options);
    const guardLabel = formatGuardLabel(transition, options);

    let inlineEffect = '';
    let hasNoteEffect = false;

    if (options.showTransitionEffects && transition.effectLines && transition.effectLines.length > 0) {
        const body = transition.effectLines
            .slice(1, Math.max(1, transition.effectLines.length - 1))
            .map(line => line.trim())
            .filter(Boolean);
        if (body.length > 0) {
            if (options.transitionEffectMode === 'inline') {
                // Multi-line, indented; first line carries the ▸ glyph,
                // continuations are indented under it for readability.
                const visible = body.slice(0, options.maxTransitionEffectLines);
                const suffix = body.length > visible.length ? ` +${body.length - visible.length}` : '';
                const lines = visible.map((line, i) => i === 0 ? line : `  ${line}`);
                if (suffix) {
                    lines[lines.length - 1] = lines[lines.length - 1] + suffix;
                }
                inlineEffect = lines.join('\n');
            } else if (options.transitionEffectMode === 'note') {
                // Same multi-line body; the renderer wraps it in a note
                // pad with a folded-corner background.
                const visible = body.slice(0, options.maxTransitionEffectLines);
                const suffix = body.length > visible.length ? ` +${body.length - visible.length}` : '';
                const lines = visible.map((line, i) => i === 0 ? line : `  ${line}`);
                if (suffix) {
                    lines[lines.length - 1] = lines[lines.length - 1] + suffix;
                }
                inlineEffect = lines.join('\n');
                hasNoteEffect = true;
            }
        }
    }

    return { eventLabel, guardLabel, inlineEffect, hasNoteEffect };
}

/**
 * Compose the edge-label text as one line per component with a small
 * glyph prefix so event / guard / effect stay visually distinguishable
 * even when the label has no background rectangle.
 *
 * Event lines keep their raw name (no glyph) on their own line; guards
 * are wrapped in ``[...]`` and prefixed with ``◇``; inline effects keep
 * the leading ``▸`` so they don't look like another guard or event.
 */
function composeEdgeLabel(
    eventLabel: string,
    guardLabel: string,
    inlineEffect: string
): string {
    const parts: string[] = [];
    if (eventLabel) {
        parts.push(`${TRANSITION_LABEL_GLYPHS.event} ${eventLabel}`);
    }
    if (guardLabel) {
        parts.push(`${TRANSITION_LABEL_GLYPHS.guard} ${guardLabel}`);
    }
    if (inlineEffect) {
        // Strip the legacy leading "/" so we don't end up with "▸ / ..."
        const body = inlineEffect.replace(/^\s*\/\s*/, '');
        parts.push(`${TRANSITION_LABEL_GLYPHS.effect} ${body}`);
    }
    return parts.join('\n');
}

/**
 * Build per-state leaf-detail lines that appear inside leaf state boxes.
 * Composite states never render inline details; their shape already says
 * enough.
 */
function leafDetailLines(
    state: FcstmDiagramState,
    options: ResolvedFcstmDiagramPreviewOptions
): { eventLabels: string[]; actionLabels: string[] } {
    if (state.children.length > 0) {
        return { eventLabels: [], actionLabels: [] };
    }
    const eventLabels: string[] = [];
    const actionLabels: string[] = [];
    if (options.showStateEvents && state.events.length > 0) {
        const visible = state.events.slice(0, options.maxStateEvents).map(formatEventSummary);
        const suffix = state.events.length > visible.length ? `+${state.events.length - visible.length}` : '';
        if (suffix) visible.push(suffix);
        eventLabels.push(...visible);
    }
    if (options.showStateActions && state.actions.length > 0) {
        const visible = state.actions.slice(0, options.maxStateActions).map(formatActionSummary);
        const suffix = state.actions.length > visible.length ? `+${state.actions.length - visible.length}` : '';
        if (suffix) visible.push(suffix);
        actionLabels.push(...visible);
    }
    return { eventLabels, actionLabels };
}

const initId = (ownerQN: string) => `__init__::${ownerQN}`;
const exitId = (ownerQN: string) => `__exit__::${ownerQN}`;

/**
 * Build the ELK graph from a diagram IR + resolved options.
 *
 * The returned graph is stable and deterministic for the same input, so
 * snapshot-style tests can lock it down.
 */
export function buildFcstmElkGraph(
    diagram: FcstmDiagram,
    options: ResolvedFcstmDiagramPreviewOptions,
    extras: { collapsedStateIds?: ReadonlySet<string> } = {}
): FcstmElkGraph {
    const collapsed = extras.collapsedStateIds || new Set<string>();

    const buildStateNode = (state: FcstmDiagramState): FcstmElkNode => {
        const isCollapsed = collapsed.has(state.qualifiedName);
        const title = state.displayName ? `${state.displayName} (${state.name})` : state.name;
        const { width: titleW, height: titleH } = measureLabel(title, 18, 6);
        const leafDetails = leafDetailLines(state, options);

        // Leaf states (and collapsed composites) now show only their title
        // in the diagram; the detail summary lives in the Details side panel
        // so the diagram stays uncluttered. We still keep eventLabels /
        // actionLabels on the meta so the Details panel can read them
        // without re-traversing the source model.
        if (state.children.length === 0 || isCollapsed) {
            const width = Math.max(LEAF_MIN_WIDTH, titleW + 24);
            const height = Math.max(LEAF_MIN_HEIGHT, titleH + 14);
            return {
                id: state.qualifiedName,
                width,
                height,
                labels: [{ text: title, width: titleW, height: titleH }],
                fcstm: {
                    kind: 'state',
                    qualifiedName: state.qualifiedName,
                    displayName: state.displayName,
                    pseudo: state.pseudo,
                    composite: state.children.length > 0,
                    collapsed: isCollapsed,
                    sourceRange: state.range,
                    eventLabels: leafDetails.eventLabels,
                    actionLabels: leafDetails.actionLabels,
                },
            };
        }

        const children = state.children.map(buildStateNode);
        const edges: FcstmElkEdge[] = [];
        const pseudo = { init: false, exit: false };

        for (const transition of state.transitions) {
            if (transition.sourceKind === 'init') pseudo.init = true;
            if (transition.targetKind === 'exit') pseudo.exit = true;
        }
        if (pseudo.init) {
            children.push({
                id: initId(state.qualifiedName),
                width: 18,
                height: 18,
                fcstm: { kind: 'pseudoInit', qualifiedName: `${state.qualifiedName}.#init` },
            });
        }
        if (pseudo.exit) {
            children.push({
                id: exitId(state.qualifiedName),
                width: 22,
                height: 22,
                fcstm: { kind: 'pseudoExit', qualifiedName: `${state.qualifiedName}.#exit` },
            });
        }

        let edgeIdx = 0;
        for (const transition of state.transitions) {
            const sourceId = transition.sourceKind === 'init'
                ? initId(state.qualifiedName)
                : transition.sourceStatePath?.join('.');
            const targetId = transition.targetKind === 'exit'
                ? exitId(state.qualifiedName)
                : transition.targetStatePath?.join('.');
            if (!sourceId || !targetId) {
                continue;
            }
            const { eventLabel, guardLabel, inlineEffect, hasNoteEffect } =
                resolveTransitionLabeling(transition, options);
            const labelText = composeEdgeLabel(eventLabel, guardLabel, inlineEffect);
            const edge: FcstmElkEdge = {
                id: `${state.qualifiedName}:e${edgeIdx++}`,
                sources: [sourceId],
                targets: [targetId],
                fcstm: {
                    kind: 'transition',
                    transitionId: transition.id,
                    eventColor: transition.eventColor,
                    forced: transition.forced,
                    transitionKind: transition.forced
                        ? 'normalAll'
                        : (transition.targetKind === 'exit' ? 'exit' : transition.sourceKind === 'init' ? 'entry' : 'normal'),
                    sourceRange: transition.range,
                    eventLabel,
                    guardLabel,
                    effectLines: transition.effectLines,
                    hasNoteEffect,
                },
            };
            if (labelText) {
                const { width, height } = measureLabel(labelText, 10, 4);
                edge.labels = [{ text: labelText, width, height }];
            }
            edges.push(edge);
        }

        return {
            id: state.qualifiedName,
            labels: [{ text: title, width: titleW, height: STATE_TITLE_HEIGHT }],
            children,
            edges,
            layoutOptions: {
                'elk.padding': '[top=54,left=28,bottom=28,right=28]',
            },
            fcstm: {
                kind: 'state',
                qualifiedName: state.qualifiedName,
                displayName: state.displayName,
                pseudo: state.pseudo,
                composite: true,
                collapsed: false,
                sourceRange: state.range,
                eventLabels: leafDetails.eventLabels,
                actionLabels: leafDetails.actionLabels,
            },
        };
    };

    return {
        id: '__canvas__',
        layoutOptions: {
            'elk.algorithm': 'layered',
            'elk.direction': options.direction === 'LR' ? 'RIGHT' : 'DOWN',
            'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
            'elk.edgeRouting': 'ORTHOGONAL',
            // Wider breathing room than the first draft — users explicitly
            // asked for a less cramped layout.
            'elk.spacing.nodeNode': '80',
            'elk.layered.spacing.nodeNodeBetweenLayers': '110',
            'elk.spacing.edgeNode': '42',
            'elk.spacing.edgeEdge': '30',
            'elk.spacing.edgeLabel': '24',
            'elk.spacing.componentComponent': '64',
            'elk.layered.spacing.baseValue': '48',
            'elk.layered.spacing.edgeNodeBetweenLayers': '46',
            'elk.edgeLabels.placement': 'CENTER',
            'elk.layered.nodePlacement.favorStraightEdges': 'true',
            'elk.padding': '[top=36,left=36,bottom=36,right=36]',
        },
        children: [buildStateNode(diagram.rootState)],
        edges: [],
        fcstm: { kind: 'canvas' },
    };
}

export const __elkGraphInternals = {
    resolveTransitionLabeling,
    composeEdgeLabel,
    initId,
    exitId,
};
