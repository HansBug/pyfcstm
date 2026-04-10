import type {
    FcstmDiagram,
    FcstmDiagramAction,
    FcstmDiagramRenderOptions,
    FcstmDiagramState,
    FcstmDiagramTransition,
} from './model';

interface ResolvedRenderOptions {
    direction: 'TB' | 'LR';
    maxStateEvents: number;
    maxStateActions: number;
    maxTransitionEffectLines: number;
    maxLabelLength: number;
}

const DEFAULT_RENDER_OPTIONS: ResolvedRenderOptions = {
    direction: 'TB',
    maxStateEvents: 4,
    maxStateActions: 4,
    maxTransitionEffectLines: 3,
    maxLabelLength: 160,
};

function sanitizeMermaidText(value: string): string {
    return value
        .replace(/\r?\n/g, ' ')
        .replace(/"/g, '\'')
        .replace(/;/g, ',')
        .replace(/\s+/g, ' ')
        .trim();
}

function truncateText(value: string, maxLength: number): string {
    if (value.length <= maxLength) {
        return value;
    }
    return `${value.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

function summarizeItems(items: string[], limit: number): string {
    if (items.length <= limit) {
        return items.join(', ');
    }
    return `${items.slice(0, limit).join(', ')}, +${items.length - limit}`;
}

function formatStateLabel(state: FcstmDiagramState): string {
    const labelParts = state.displayName
        ? `${state.displayName} (${state.name})`
        : state.name;
    const metrics: string[] = [];

    if (state.pseudo) {
        metrics.push('pseudo');
    }
    if (state.children.length > 0) {
        if (state.events.length > 0) {
            metrics.push(`${state.events.length}e`);
        }
        if (state.actions.length > 0) {
            metrics.push(`${state.actions.length}a`);
        }
        metrics.push(`${state.children.length}s`);
    }

    if (metrics.length > 0) {
        return `${labelParts} [${metrics.join('/')}]`;
    }
    return labelParts;
}

function formatActionForSummary(action: FcstmDiagramAction): string {
    if (action.globalAspect) {
        const aspect = action.aspect ? ` ${action.aspect}` : '';
        if (action.mode === 'abstract') {
            return `aspect ${action.stage}${aspect} abstract ${action.name || action.qualifiedName}`;
        }
        if (action.mode === 'ref') {
            return `aspect ${action.stage}${aspect} ref`;
        }
        return `aspect ${action.stage}${aspect} ${action.name || `${action.operationCount} op`}`;
    }

    const aspect = action.aspect ? ` ${action.aspect}` : '';
    if (action.mode === 'abstract') {
        return `${action.stage}${aspect} abstract ${action.name || action.qualifiedName}`;
    }
    if (action.mode === 'ref') {
        return `${action.stage}${aspect} ref`;
    }
    if (action.name) {
        return `${action.stage}${aspect} ${action.name}`;
    }
    return `${action.stage}${aspect} ${action.operationCount} op${action.operationCount === 1 ? '' : 's'}`;
}

function buildStateDetailLines(
    state: FcstmDiagramState,
    options: ResolvedRenderOptions
): string[] {
    if (state.children.length > 0) {
        return [];
    }

    const lines: string[] = [];

    if (state.events.length > 0) {
        const eventLabels = state.events.map(event => sanitizeMermaidText(
            event.displayName ? `${event.displayName} (${event.name})` : event.name
        ));
        lines.push(`events: ${summarizeItems(eventLabels, options.maxStateEvents)}`);
    }

    if (state.actions.length > 0) {
        const actionLabels = state.actions.map(action => sanitizeMermaidText(
            formatActionForSummary(action)
        ));
        lines.push(`actions: ${summarizeItems(actionLabels, options.maxStateActions)}`);
    }

    if (state.children.length > 0 && !state.root) {
        lines.push(`substates: ${state.children.length}`);
    }

    return lines.map(line => truncateText(line, options.maxLabelLength));
}

function collectStateAliases(state: FcstmDiagramState): Map<string, string> {
    const aliases = new Map<string, string>();
    let index = 0;

    const visit = (currentState: FcstmDiagramState) => {
        index += 1;
        aliases.set(currentState.qualifiedName, `state_${index}`);
        for (const child of currentState.children) {
            visit(child);
        }
    };

    visit(state);
    return aliases;
}

function formatTriggerForTransition(triggerLabel: string | undefined): string | undefined {
    if (!triggerLabel) {
        return undefined;
    }

    if (triggerLabel.startsWith('::')) {
        return `local ${triggerLabel.slice(2).trim()}`;
    }
    if (triggerLabel.startsWith(':')) {
        return `event ${triggerLabel.slice(1).trim()}`;
    }
    return triggerLabel.trim();
}

function formatEffectForTransition(
    transition: FcstmDiagramTransition,
    options: ResolvedRenderOptions
): string | undefined {
    if (transition.effectLines.length === 0) {
        return undefined;
    }

    const statements = transition.effectLines
        .slice(1, Math.max(1, transition.effectLines.length - 1))
        .map(line => sanitizeMermaidText(line.replace(/;+\s*$/g, '')))
        .filter(Boolean);

    if (statements.length === 0) {
        return 'effect';
    }

    const summarizedStatements = statements.slice(0, options.maxTransitionEffectLines);
    const suffix = statements.length > summarizedStatements.length
        ? ` +${statements.length - summarizedStatements.length}`
        : '';
    return `effect ${summarizedStatements.join(', ')}${suffix}`;
}

function buildTransitionLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedRenderOptions
): string | undefined {
    const parts: string[] = [];

    if (transition.forced) {
        parts.push('forced');
    }

    const trigger = formatTriggerForTransition(transition.triggerLabel);
    if (trigger) {
        parts.push(trigger);
    }

    if (transition.guardLabel) {
        parts.push(`if ${sanitizeMermaidText(transition.guardLabel)}`);
    }

    const effect = formatEffectForTransition(transition, options);
    if (effect) {
        parts.push(effect);
    }

    if (parts.length === 0) {
        return undefined;
    }

    return truncateText(sanitizeMermaidText(parts.join(' | ')), options.maxLabelLength);
}

function indent(depth: number): string {
    return '    '.repeat(depth);
}

function buildTransitionLine(
    transition: FcstmDiagramTransition,
    aliases: Map<string, string>,
    childAliasesByName: Map<string, string>,
    options: ResolvedRenderOptions
): string | null {
    const source = transition.sourceKind === 'init'
        ? '[*]'
        : (
            transition.sourceStatePath
                ? aliases.get(transition.sourceStatePath.join('.'))
                : childAliasesByName.get(transition.sourceLabel)
        );
    const target = transition.targetKind === 'exit'
        ? '[*]'
        : (
            transition.targetStatePath
                ? aliases.get(transition.targetStatePath.join('.'))
                : childAliasesByName.get(transition.targetLabel)
        );

    if (!source || !target) {
        return null;
    }

    const label = buildTransitionLabel(transition, options);
    if (!label) {
        return `${source} --> ${target}`;
    }
    return `${source} --> ${target} : ${label}`;
}

function renderStateBlock(
    state: FcstmDiagramState,
    aliases: Map<string, string>,
    options: ResolvedRenderOptions,
    lines: string[],
    detailLines: string[],
    depth: number
): void {
    if (state.root && state.children.length > 0) {
        const childAliasesByName = new Map<string, string>();
        for (const child of state.children) {
            const childAlias = aliases.get(child.qualifiedName);
            if (childAlias) {
                childAliasesByName.set(child.name, childAlias);
            }
            renderStateBlock(child, aliases, options, lines, detailLines, depth);
        }

        for (const transition of state.transitions) {
            const transitionLine = buildTransitionLine(transition, aliases, childAliasesByName, options);
            if (transitionLine) {
                lines.push(`${indent(depth)}${transitionLine}`);
            }
        }
        return;
    }

    const alias = aliases.get(state.qualifiedName);
    if (!alias) {
        return;
    }

    const stateLabel = sanitizeMermaidText(formatStateLabel(state));
    const stateDetails = buildStateDetailLines(state, options);
    for (const detail of stateDetails) {
        detailLines.push(`${alias} : ${detail}`);
    }

    if (state.children.length === 0) {
        lines.push(`${indent(depth)}state "${stateLabel}" as ${alias}`);
        return;
    }

    lines.push(`${indent(depth)}state "${stateLabel}" as ${alias} {`);
    const childAliasesByName = new Map<string, string>();
    for (const child of state.children) {
        const childAlias = aliases.get(child.qualifiedName);
        if (childAlias) {
            childAliasesByName.set(child.name, childAlias);
        }
        renderStateBlock(child, aliases, options, lines, detailLines, depth + 1);
    }

    for (const transition of state.transitions) {
        const transitionLine = buildTransitionLine(transition, aliases, childAliasesByName, options);
        if (transitionLine) {
            lines.push(`${indent(depth + 1)}${transitionLine}`);
        }
    }

    lines.push(`${indent(depth)}}`);
}

/**
 * Render the diagram IR into Mermaid ``stateDiagram-v2`` source.
 */
export async function renderFcstmDiagramMermaid(
    diagram: FcstmDiagram,
    renderOptions: Partial<FcstmDiagramRenderOptions> = {}
): Promise<string> {
    const options: ResolvedRenderOptions = {
        ...DEFAULT_RENDER_OPTIONS,
        ...renderOptions,
    };
    const aliases = collectStateAliases(diagram.rootState);
    const diagramLines: string[] = [
        '%% FCSTM Mermaid preview generated by jsfcstm',
        'stateDiagram-v2',
        `direction ${options.direction}`,
    ];
    const detailLines: string[] = [];

    renderStateBlock(diagram.rootState, aliases, options, diagramLines, detailLines, 0);

    if (detailLines.length > 0) {
        diagramLines.push('');
        for (const detailLine of detailLines) {
            diagramLines.push(detailLine);
        }
    }

    return diagramLines.join('\n');
}
