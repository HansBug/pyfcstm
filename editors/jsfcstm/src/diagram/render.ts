import type {
    FcstmDiagram,
    FcstmDiagramEffectNote,
    FcstmDiagramAction,
    FcstmDiagramMermaidRenderResult,
    FcstmDiagramPreviewOptionsInput,
    FcstmDiagramRenderedTransition,
    FcstmDiagramState,
    FcstmDiagramTransition,
    ResolvedFcstmDiagramPreviewOptions,
} from './model';
import {resolveFcstmDiagramPreviewOptions} from './options';

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

function dedupeLabels(parts: Array<string | undefined>): string[] {
    const result: string[] = [];
    for (const part of parts) {
        if (!part) {
            continue;
        }
        if (!result.includes(part)) {
            result.push(part);
        }
    }
    return result;
}

function formatCompositeLabel(parts: Array<string | undefined>): string | undefined {
    const compactParts = dedupeLabels(parts);
    if (compactParts.length === 0) {
        return undefined;
    }
    if (compactParts.length === 1) {
        return compactParts[0];
    }
    return `${compactParts[0]} (${compactParts.slice(1).join(' / ')})`;
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
    options: ResolvedFcstmDiagramPreviewOptions
): string[] {
    if (state.children.length > 0) {
        return [];
    }

    const lines: string[] = [];

    if (options.showStateEvents && state.events.length > 0) {
        const eventLabels = state.events.map(event => sanitizeMermaidText(
            formatCompositeLabel([
                event.displayName,
                event.name,
            ]) || event.name
        ));
        lines.push(`events: ${summarizeItems(eventLabels, options.maxStateEvents)}`);
    }

    if (options.showStateActions && state.actions.length > 0) {
        const actionLabels = state.actions.map(action => sanitizeMermaidText(
            formatActionForSummary(action)
        ));
        lines.push(`actions: ${summarizeItems(actionLabels, options.maxStateActions)}`);
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

function collectEffectBodyLines(transition: FcstmDiagramTransition): string[] {
    if (transition.effectLines.length <= 2) {
        return [];
    }
    return transition.effectLines
        .slice(1, transition.effectLines.length - 1)
        .map(line => line.trim())
        .filter(Boolean);
}

function formatTransitionEventLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): string | undefined {
    if (!options.showEvents || !transition.eventQualifiedName) {
        return undefined;
    }

    return formatCompositeLabel(options.eventNameFormat.map(part => {
        if (part === 'name') {
            return transition.eventName;
        }
        if (part === 'extra_name') {
            return transition.eventDisplayName;
        }
        if (part === 'path') {
            return transition.eventAbsolutePath;
        }
        if (part === 'relpath') {
            return transition.eventRelativePath;
        }
        return undefined;
    })) || transition.eventRelativePath || transition.eventName;
}

function formatTransitionGuardLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): string | undefined {
    if (!options.showTransitionGuards || !transition.guardLabel) {
        return undefined;
    }
    return `[${sanitizeMermaidText(transition.guardLabel)}]`;
}

function formatTransitionInlineEffectLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): string | undefined {
    if (!options.showTransitionEffects || options.transitionEffectMode !== 'inline') {
        return undefined;
    }

    const statements = collectEffectBodyLines(transition);
    if (statements.length === 0) {
        return undefined;
    }

    const visibleStatements = statements.slice(0, options.maxTransitionEffectLines);
    const suffix = statements.length > visibleStatements.length
        ? ` +${statements.length - visibleStatements.length} lines`
        : '';
    return truncateText(
        sanitizeMermaidText(`${visibleStatements.join(' ')}${suffix}`),
        options.maxLabelLength
    );
}

function buildTransitionLabel(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): string | undefined {
    const parts = dedupeLabels([
        formatTransitionEventLabel(transition, options),
        formatTransitionGuardLabel(transition, options),
    ]);
    const inlineEffect = formatTransitionInlineEffectLabel(transition, options);
    const baseLabel = parts.join(' ');

    if (inlineEffect) {
        return baseLabel
            ? truncateText(sanitizeMermaidText(`${baseLabel} / ${inlineEffect}`), options.maxLabelLength)
            : truncateText(sanitizeMermaidText(`/ ${inlineEffect}`), options.maxLabelLength);
    }

    if (!baseLabel) {
        return undefined;
    }
    return truncateText(sanitizeMermaidText(baseLabel), options.maxLabelLength);
}

function indent(depth: number): string {
    return '    '.repeat(depth);
}

function shouldColorTransition(
    transition: FcstmDiagramTransition,
    options: ResolvedFcstmDiagramPreviewOptions
): boolean {
    return (
        (options.eventVisualizationMode === 'color' || options.eventVisualizationMode === 'both')
        && Boolean(transition.eventColor)
    );
}

function buildTransitionLine(
    transition: FcstmDiagramTransition,
    aliases: Map<string, string>,
    childAliasesByName: Map<string, string>,
    options: ResolvedFcstmDiagramPreviewOptions
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
    options: ResolvedFcstmDiagramPreviewOptions,
    lines: string[],
    detailLines: string[],
    renderedTransitions: FcstmDiagramRenderedTransition[],
    depth: number
): void {
    if (state.root && state.children.length > 0) {
        const childAliasesByName = new Map<string, string>();
        for (const child of state.children) {
            const childAlias = aliases.get(child.qualifiedName);
            if (childAlias) {
                childAliasesByName.set(child.name, childAlias);
            }
            renderStateBlock(child, aliases, options, lines, detailLines, renderedTransitions, depth);
        }

        for (const transition of state.transitions) {
            const transitionLine = buildTransitionLine(transition, aliases, childAliasesByName, options);
            if (transitionLine) {
                lines.push(`${indent(depth)}${transitionLine}`);
                renderedTransitions.push({
                    id: transition.id,
                    eventColor: shouldColorTransition(transition, options) ? transition.eventColor : undefined,
                });
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
        renderStateBlock(child, aliases, options, lines, detailLines, renderedTransitions, depth + 1);
    }

    for (const transition of state.transitions) {
        const transitionLine = buildTransitionLine(transition, aliases, childAliasesByName, options);
        if (transitionLine) {
            lines.push(`${indent(depth + 1)}${transitionLine}`);
            renderedTransitions.push({
                id: transition.id,
                eventColor: shouldColorTransition(transition, options) ? transition.eventColor : undefined,
            });
        }
    }

    lines.push(`${indent(depth)}}`);
}

function transitionSummaryTitle(transition: FcstmDiagramTransition): string {
    return `${transition.sourceLabel} -> ${transition.targetLabel}`;
}

/**
 * Collect transition-effect notes for note-mode preview rendering.
 */
export function collectFcstmDiagramEffectNotes(
    diagram: FcstmDiagram,
    previewOptions: FcstmDiagramPreviewOptionsInput = undefined
): FcstmDiagramEffectNote[] {
    const options = resolveFcstmDiagramPreviewOptions(previewOptions);
    if (!options.showTransitionEffects || options.transitionEffectMode !== 'note') {
        return [];
    }

    const notes: FcstmDiagramEffectNote[] = [];

    const visit = (state: FcstmDiagramState) => {
        for (const transition of state.transitions) {
            const effectBodyLines = collectEffectBodyLines(transition);
            if (effectBodyLines.length === 0) {
                continue;
            }

            const metaParts = dedupeLabels([
                formatTransitionEventLabel(transition, options),
                formatTransitionGuardLabel(transition, options),
            ]);
            notes.push({
                transitionId: transition.id,
                title: transitionSummaryTitle(transition),
                meta: metaParts.length > 0 ? metaParts.join(' · ') : undefined,
                effectText: transition.effectLines.join('\n'),
                lineCount: effectBodyLines.length,
                eventColor: shouldColorTransition(transition, options) ? transition.eventColor : undefined,
            });
        }

        for (const child of state.children) {
            visit(child);
        }
    };

    visit(diagram.rootState);
    return notes;
}

/**
 * Render the diagram IR into Mermaid ``stateDiagram-v2`` source plus transition metadata.
 */
export async function renderFcstmDiagramMermaidView(
    diagram: FcstmDiagram,
    previewOptions: FcstmDiagramPreviewOptionsInput = undefined
): Promise<FcstmDiagramMermaidRenderResult> {
    const options = resolveFcstmDiagramPreviewOptions(previewOptions);
    const aliases = collectStateAliases(diagram.rootState);
    const diagramLines: string[] = [
        '%% FCSTM Mermaid preview generated by jsfcstm',
        'stateDiagram-v2',
        `direction ${options.direction}`,
    ];
    const detailLines: string[] = [];
    const renderedTransitions: FcstmDiagramRenderedTransition[] = [];

    renderStateBlock(
        diagram.rootState,
        aliases,
        options,
        diagramLines,
        detailLines,
        renderedTransitions,
        0
    );

    if (detailLines.length > 0) {
        diagramLines.push('');
        for (const detailLine of detailLines) {
            diagramLines.push(detailLine);
        }
    }

    return {
        source: diagramLines.join('\n'),
        renderedTransitions,
    };
}

/**
 * Render the diagram IR into Mermaid ``stateDiagram-v2`` source.
 */
export async function renderFcstmDiagramMermaid(
    diagram: FcstmDiagram,
    previewOptions: FcstmDiagramPreviewOptionsInput = undefined
): Promise<string> {
    const rendered = await renderFcstmDiagramMermaidView(diagram, previewOptions);
    return rendered.source;
}

export {
    formatTransitionEventLabel as formatFcstmDiagramTransitionEventLabel,
    formatTransitionInlineEffectLabel as formatFcstmDiagramTransitionInlineEffectLabel,
    formatTransitionGuardLabel as formatFcstmDiagramTransitionGuardLabel,
};
