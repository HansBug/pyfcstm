import ELK, {
    type ElkExtendedEdge,
    type ElkLabel,
    type ElkNode,
    type ElkPoint,
    type LayoutOptions,
} from 'elkjs/lib/elk.bundled.js';
import {
    SVG,
    registerWindow,
    type Container as SvgContainer,
    type Svg as SvgDocument,
} from '@svgdotjs/svg.js';
import {createSVGWindow} from 'svgdom';

import type {
    FcstmDiagram,
    FcstmDiagramAction,
    FcstmDiagramEventLegendItem,
    FcstmDiagramRenderOptions,
    FcstmDiagramState,
    FcstmDiagramTransition,
    FcstmDiagramVariable,
} from './model';

interface Point {
    x: number;
    y: number;
}

interface Rect {
    x: number;
    y: number;
    width: number;
    height: number;
}

interface StateLayoutChild {
    state: FcstmDiagramState;
    layout: StateLayout;
    frame: Rect;
}

interface TransitionLabelLayout {
    frame: Rect;
    lines: string[];
    kind: 'label' | 'note';
}

interface TransitionSectionLayout {
    points: Point[];
}

interface TransitionLayout {
    transition: FcstmDiagramTransition;
    sections: TransitionSectionLayout[];
    labels: TransitionLabelLayout[];
}

interface StateLayout {
    width: number;
    height: number;
    title: string;
    metaLines: string[];
    children: StateLayoutChild[];
    edges: TransitionLayout[];
    startMarker?: Rect;
    endMarker?: Rect;
}

const DEFAULT_RENDER_OPTIONS: FcstmDiagramRenderOptions = {
    minWidth: 1320,
    headerHeight: 118,
    padding: 24,
    lineHeight: 18,
    titleHeight: 38,
    stateGap: 60,
    sectionGap: 16,
    childGap: 54,
    childColumnGap: 64,
    markerRadius: 11,
    notePadding: 10,
    panelGap: 16,
};

const SVG_NS = 'http://www.w3.org/2000/svg';
const elk = new ELK();

const DIAGRAM_STYLE = `
.fcstm-root-bg{fill:url(#fcstm-bg);}
.fcstm-title{font:700 28px "Aptos","Segoe UI","Helvetica Neue",sans-serif;fill:#163a60;letter-spacing:0.02em;}
.fcstm-subtitle{font:500 12px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#5b7795;}
.fcstm-summary-badge{fill:rgba(255,255,255,0.92);stroke:#a8c4e4;stroke-width:1.1;filter:url(#fcstm-shadow);}
.fcstm-summary-text{font:600 12px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#25517b;}
.fcstm-panel-box{fill:rgba(255,255,255,0.9);stroke:#b7cde6;stroke-width:1.15;filter:url(#fcstm-shadow);}
.fcstm-panel-title{font:700 13px "Aptos","Segoe UI","Helvetica Neue",sans-serif;fill:#214d79;}
.fcstm-panel-item{font:500 12px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#3f5f80;}
.fcstm-state-box{fill:#ffffff;stroke:#7da9d7;stroke-width:1.6;filter:url(#fcstm-shadow);}
.fcstm-state.composite .fcstm-state-box{fill:#fcfeff;}
.fcstm-state.leaf .fcstm-state-box{fill:#ffffff;}
.fcstm-state.pseudo .fcstm-state-box{fill:#fff5de;stroke:#bf9954;stroke-dasharray:8 5;}
.fcstm-state.root .fcstm-state-box{stroke:#356ea8;stroke-width:2;}
.fcstm-state-title-bar{fill:#dcebfb;}
.fcstm-state.pseudo .fcstm-state-title-bar{fill:#fde4af;}
.fcstm-state.root .fcstm-state-title-bar{fill:#c2daf5;}
.fcstm-state-title{font:700 15px "Aptos","Segoe UI","Helvetica Neue",sans-serif;fill:#173f67;}
.fcstm-state-kind-pill{fill:#eef5fd;stroke:#c2d8ef;stroke-width:1;}
.fcstm-state.pseudo .fcstm-state-kind-pill{fill:#fbe8bf;stroke:#d1b06d;}
.fcstm-state-kind{font:600 11px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#567390;}
.fcstm-state-meta{font:500 11px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#627a95;}
.fcstm-transition-path{fill:none;stroke:#2d6aa8;stroke-width:2.45;stroke-linejoin:round;stroke-linecap:round;}
.fcstm-transition-label-box{fill:rgba(255,255,255,0.96);stroke:#aec8e7;stroke-width:1;filter:url(#fcstm-shadow);}
.fcstm-transition-label-text{font:600 11px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#26527c;}
.fcstm-transition-note-box{fill:#fff5d0;stroke:#d7bc6f;stroke-width:1;filter:url(#fcstm-shadow);}
.fcstm-transition-note-fold{fill:#f2e2a1;stroke:#d7bc6f;stroke-width:1;}
.fcstm-transition-note-text{font:500 11px "JetBrains Mono","Fira Code","Consolas",monospace;fill:#6d5620;}
.fcstm-start-node{fill:#1f2a37;}
.fcstm-end-node-ring{fill:none;stroke:#1f2a37;stroke-width:2.1;}
.fcstm-end-node-core{fill:#1f2a37;}
.fcstm-machine-link{fill:none;stroke:#20364f;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round;}
`;

function appendSvgNode(
    document: any,
    parent: any,
    tagName: string,
    attributes: Record<string, string | number> = {},
    textContent?: string
): any {
    const node = document.createElementNS(SVG_NS, tagName);
    for (const [key, value] of Object.entries(attributes)) {
        node.setAttribute(key, String(value));
    }
    if (textContent !== undefined) {
        node.textContent = textContent;
    }
    parent.appendChild(node);
    return node;
}

function measureText(text: string): number {
    return text.length * 7.15;
}

function measureMaxText(lines: string[]): number {
    let width = 0;
    for (const line of lines) {
        width = Math.max(width, measureText(line));
    }
    return width;
}

function formatStateTitle(state: FcstmDiagramState): string {
    if (state.displayName) {
        return `${state.displayName} (${state.name})`;
    }
    return state.name;
}

function formatDiagramEventLabel(name: string, displayName?: string): string {
    if (displayName) {
        return `${displayName} (${name})`;
    }
    return name;
}

function summarizeNames(items: string[], limit: number): string {
    if (items.length <= limit) {
        return items.join(', ');
    }
    return `${items.slice(0, limit).join(', ')}, +${items.length - limit}`;
}

function buildActionGroupKey(action: FcstmDiagramAction): string {
    if (action.globalAspect) {
        return `>> ${action.stage}${action.aspect ? ` ${action.aspect}` : ''}`;
    }
    return `${action.stage}${action.aspect ? ` ${action.aspect}` : ''}`;
}

function buildStateMetaLines(state: FcstmDiagramState): string[] {
    const lines: string[] = [];

    if (state.events.length > 0) {
        lines.push(
            `events: ${summarizeNames(
                state.events.map(event => formatDiagramEventLabel(event.name, event.displayName)),
                3
            )}`
        );
    }

    if (state.actions.length > 0) {
        const actionLabels = state.actions.map(action => {
            const group = buildActionGroupKey(action);
            if (action.label.startsWith(group)) {
                return action.label;
            }
            return `${group} ${action.label}`.trim();
        });
        lines.push(`actions: ${summarizeNames(actionLabels, 2)}`);
    }

    return lines;
}

function buildTransitionPrimaryLines(transition: FcstmDiagramTransition): string[] {
    const lines: string[] = [];
    if (transition.forced) {
        lines.push('forced transition');
    }
    if (transition.triggerLabel) {
        lines.push(transition.triggerLabel);
    }
    if (transition.guardLabel) {
        lines.push(`if [${transition.guardLabel}]`);
    }
    return lines;
}

function measureBox(lines: string[], options: FcstmDiagramRenderOptions): Rect | null {
    if (lines.length === 0) {
        return null;
    }

    return {
        x: 0,
        y: 0,
        width: Math.max(88, measureMaxText(lines) + options.notePadding * 2),
        height: Math.max(
            options.lineHeight + options.notePadding * 2,
            lines.length * options.lineHeight + options.notePadding * 2
        ),
    };
}

function buildEdgeLabels(
    transition: FcstmDiagramTransition,
    options: FcstmDiagramRenderOptions
): ElkLabel[] {
    const labels: ElkLabel[] = [];
    const primaryLines = buildTransitionPrimaryLines(transition);
    const primaryBox = measureBox(primaryLines, options);
    if (primaryBox) {
        labels.push({
            id: `${transition.id}::label`,
            text: primaryLines.join('\n'),
            width: primaryBox.width,
            height: primaryBox.height,
        });
    }

    const noteBox = measureBox(transition.effectLines, options);
    if (noteBox) {
        labels.push({
            id: `${transition.id}::note`,
            text: transition.effectLines.join('\n'),
            width: noteBox.width,
            height: noteBox.height,
        });
    }

    return labels;
}

function stateKindLabel(state: FcstmDiagramState): string {
    if (state.root) {
        return 'root';
    }
    if (state.pseudo) {
        return 'pseudo';
    }
    if (state.leaf) {
        return 'leaf';
    }
    return 'composite';
}

function scopeLayoutOptions(hasEdges: boolean): LayoutOptions {
    return {
        'elk.algorithm': 'layered',
        'org.eclipse.elk.direction': 'DOWN',
        'org.eclipse.elk.edgeRouting': 'ORTHOGONAL',
        'org.eclipse.elk.edgeLabels.placement': 'CENTER',
        'org.eclipse.elk.layered.nodePlacement.favorStraightEdges': 'true',
        'org.eclipse.elk.layered.considerModelOrder': 'NODES_AND_EDGES',
        'org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers': hasEdges ? '92' : '64',
        'org.eclipse.elk.spacing.nodeNode': '56',
        'org.eclipse.elk.spacing.edgeNode': '34',
        'org.eclipse.elk.spacing.edgeEdge': '24',
        'org.eclipse.elk.spacing.edgeLabel': '12',
        'org.eclipse.elk.spacing.labelLabel': '10',
        'org.eclipse.elk.padding': '[top=20,left=20,bottom=20,right=20]',
    };
}

function buildScopeEdge(
    transition: FcstmDiagramTransition,
    state: FcstmDiagramState,
    childIdByName: Map<string, string>,
    startMarkerId: string | null,
    endMarkerId: string | null,
    options: FcstmDiagramRenderOptions
): ElkExtendedEdge | null {
    let sourceId: string | undefined;
    let targetId: string | undefined;

    if (transition.sourceKind === 'init') {
        sourceId = startMarkerId || undefined;
    } else {
        sourceId = childIdByName.get(transition.sourceLabel);
    }

    if (transition.targetKind === 'exit') {
        targetId = endMarkerId || undefined;
    } else {
        targetId = childIdByName.get(transition.targetLabel);
    }

    if (!sourceId || !targetId) {
        return null;
    }

    return {
        id: transition.id,
        sources: [sourceId],
        targets: [targetId],
        labels: buildEdgeLabels(transition, options),
        container: `${state.id}::__scope__`,
    };
}

function translateRect(rect: Rect, dx: number, dy: number): Rect {
    return {
        x: rect.x + dx,
        y: rect.y + dy,
        width: rect.width,
        height: rect.height,
    };
}

function translatePoints(points: Point[], dx: number, dy: number): Point[] {
    return points.map(point => ({
        x: point.x + dx,
        y: point.y + dy,
    }));
}

async function layoutState(
    state: FcstmDiagramState,
    options: FcstmDiagramRenderOptions
): Promise<StateLayout> {
    const title = formatStateTitle(state);
    const metaLines = buildStateMetaLines(state);
    const titleWidth = measureText(title) + 112;
    const metaWidth = measureMaxText(metaLines) + options.padding * 2 + 24;
    const headerHeight = options.titleHeight
        + (metaLines.length > 0 ? options.sectionGap + metaLines.length * options.lineHeight : 0);

    if (state.children.length === 0) {
        const width = Math.max(
            state.root ? 380 : 220,
            titleWidth + options.padding * 2,
            metaWidth
        );
        const height = Math.max(
            118,
            options.padding + headerHeight + options.padding
        );
        return {
            width,
            height,
            title,
            metaLines,
            children: [],
            edges: [],
        };
    }

    const childLayouts = await Promise.all(
        state.children.map(async child => ({
            state: child,
            layout: await layoutState(child, options),
        }))
    );
    const childIdByName = new Map(childLayouts.map(item => [item.state.name, item.state.id]));
    const hasStartMarker = state.transitions.some(transition => transition.sourceKind === 'init');
    const hasEndMarker = state.transitions.some(transition => transition.targetKind === 'exit');
    const startMarkerId = hasStartMarker ? `${state.id}::__init__` : null;
    const endMarkerId = hasEndMarker ? `${state.id}::__exit__` : null;

    const graphChildren: ElkNode[] = childLayouts.map(item => ({
        id: item.state.id,
        width: item.layout.width,
        height: item.layout.height,
    }));

    if (startMarkerId) {
        graphChildren.unshift({
            id: startMarkerId,
            width: options.markerRadius * 2,
            height: options.markerRadius * 2,
        });
    }
    if (endMarkerId) {
        graphChildren.push({
            id: endMarkerId,
            width: options.markerRadius * 2 + 2,
            height: options.markerRadius * 2 + 2,
        });
    }

    const graphEdges = state.transitions
        .map(transition => buildScopeEdge(transition, state, childIdByName, startMarkerId, endMarkerId, options))
        .filter((edge): edge is ElkExtendedEdge => Boolean(edge));

    const laidOutGraph = await elk.layout({
        id: `${state.id}::__scope__`,
        layoutOptions: scopeLayoutOptions(graphEdges.length > 0),
        children: graphChildren,
        edges: graphEdges,
    } as ElkNode) as ElkNode;

    const graphWidth = laidOutGraph.width || 0;
    const graphHeight = laidOutGraph.height || 0;
    const width = Math.max(
        state.root ? 680 : 380,
        titleWidth + options.padding * 2,
        metaWidth,
        graphWidth + options.padding * 2
    );
    const graphOffsetX = Math.max(options.padding, Math.round((width - graphWidth) / 2));
    const graphOffsetY = options.padding + headerHeight + options.sectionGap;
    const height = graphOffsetY + graphHeight + options.padding;
    const childFramesById = new Map<string, Rect>();
    let startMarker: Rect | undefined;
    let endMarker: Rect | undefined;

    for (const childNode of laidOutGraph.children || []) {
        const frame: Rect = {
            x: graphOffsetX + (childNode.x || 0),
            y: graphOffsetY + (childNode.y || 0),
            width: childNode.width || 0,
            height: childNode.height || 0,
        };

        if (childNode.id === startMarkerId) {
            startMarker = frame;
            continue;
        }
        if (childNode.id === endMarkerId) {
            endMarker = frame;
            continue;
        }

        childFramesById.set(childNode.id, frame);
    }

    const children: StateLayoutChild[] = childLayouts
        .map(item => {
            const frame = childFramesById.get(item.state.id);
            if (!frame) {
                return null;
            }
            return {
                state: item.state,
                layout: item.layout,
                frame,
            };
        })
        .filter((item): item is StateLayoutChild => Boolean(item));

    const edges: TransitionLayout[] = state.transitions.map(transition => {
        const laidOutEdge = (laidOutGraph.edges || []).find(item => item.id === transition.id);
        if (!laidOutEdge) {
            return {
                transition,
                sections: [],
                labels: [],
            };
        }

        const sections = (laidOutEdge.sections || [])
            .map(section => {
                const points = [
                    section.startPoint,
                    ...(section.bendPoints || []),
                    section.endPoint,
                ]
                    .filter((point): point is ElkPoint => Boolean(point))
                    .map(point => ({
                        x: graphOffsetX + point.x,
                        y: graphOffsetY + point.y,
                    }));

                return {
                    points,
                };
            })
            .filter(section => section.points.length >= 2);

        const primaryLines = buildTransitionPrimaryLines(transition);
        const labels = (laidOutEdge.labels || [])
            .map(label => {
                const frame = translateRect({
                    x: label.x || 0,
                    y: label.y || 0,
                    width: label.width || 0,
                    height: label.height || 0,
                }, graphOffsetX, graphOffsetY);

                if ((label.id || '').endsWith('::note')) {
                    return {
                        frame,
                        lines: transition.effectLines,
                        kind: 'note' as const,
                    };
                }

                return {
                    frame,
                    lines: primaryLines,
                    kind: 'label' as const,
                };
            })
            .filter(item => item.lines.length > 0);

        return {
            transition,
            sections,
            labels,
        };
    });

    return {
        width,
        height,
        title,
        metaLines,
        children,
        edges,
        startMarker,
        endMarker,
    };
}

function renderPolyline(points: Point[]): string {
    if (points.length === 0) {
        return '';
    }

    const [firstPoint, ...restPoints] = points;
    return `M ${firstPoint.x} ${firstPoint.y} ${restPoints.map(point => `L ${point.x} ${point.y}`).join(' ')}`;
}

function renderTextLine(
    container: SvgContainer,
    x: number,
    y: number,
    text: string,
    className: string
): void {
    const node = container.text(text);
    node.addClass(className);
    node.attr({x, y});
}

function buildPaintDefinitions(document: any, draw: SvgDocument): void {
    const defsNode = draw.defs().node;

    const gradientNode = appendSvgNode(document, defsNode, 'linearGradient', {
        id: 'fcstm-bg',
        x1: '0%',
        y1: '0%',
        x2: '100%',
        y2: '100%',
    });
    appendSvgNode(document, gradientNode, 'stop', {
        offset: '0%',
        'stop-color': '#f7fbff',
    });
    appendSvgNode(document, gradientNode, 'stop', {
        offset: '38%',
        'stop-color': '#eef5ff',
    });
    appendSvgNode(document, gradientNode, 'stop', {
        offset: '100%',
        'stop-color': '#e8f1fb',
    });

    const filterNode = appendSvgNode(document, defsNode, 'filter', {
        id: 'fcstm-shadow',
        x: '-20%',
        y: '-20%',
        width: '140%',
        height: '140%',
    });
    appendSvgNode(document, filterNode, 'feDropShadow', {
        dx: 0,
        dy: 5,
        stdDeviation: 10,
        'flood-color': '#5f88b8',
        'flood-opacity': 0.14,
    });

    const markerNode = appendSvgNode(document, defsNode, 'marker', {
        id: 'fcstm-arrowhead',
        markerWidth: 10,
        markerHeight: 10,
        refX: 8,
        refY: 5,
        orient: 'auto',
        markerUnits: 'strokeWidth',
        viewBox: '0 0 10 10',
    });
    appendSvgNode(document, markerNode, 'path', {
        d: 'M 0 0 L 10 5 L 0 10 z',
        fill: 'context-stroke',
    });

    appendSvgNode(document, draw.node, 'style', {type: 'text/css'}, DIAGRAM_STYLE);
}

function createSvgDocument(
    width: number,
    height: number,
    ariaLabel: string
): {draw: SvgDocument; document: any} {
    const window = createSVGWindow();
    const document = window.document;
    registerWindow(window as never, document as never);
    const draw = SVG(document.documentElement) as SvgDocument;
    draw.size(width, height).viewbox(0, 0, width, height);
    draw.attr({
        role: 'img',
        'aria-label': ariaLabel,
    });
    buildPaintDefinitions(document, draw);
    return {draw, document};
}

function renderVariablePanel(
    variables: FcstmDiagramVariable[],
    container: SvgContainer,
    x: number,
    y: number,
    width: number,
    options: FcstmDiagramRenderOptions
): number {
    if (variables.length === 0) {
        return 0;
    }

    const height = options.padding
        + options.lineHeight
        + variables.length * options.lineHeight
        + options.padding;
    const group = container.group()
        .addClass('fcstm-panel')
        .addClass('fcstm-variable-panel');

    group.rect(width, height)
        .move(x, y)
        .radius(18)
        .addClass('fcstm-panel-box');
    renderTextLine(group, x + options.padding, y + options.padding + 12, 'Variables', 'fcstm-panel-title');

    for (let index = 0; index < variables.length; index += 1) {
        const variable = variables[index];
        renderTextLine(
            group,
            x + options.padding,
            y + options.padding + options.lineHeight * (index + 2),
            `def ${variable.valueType} ${variable.name} = ${variable.initializer}`,
            'fcstm-panel-item'
        );
    }

    return height;
}

function renderEventLegendPanel(
    legend: FcstmDiagramEventLegendItem[],
    container: SvgContainer,
    x: number,
    y: number,
    width: number,
    options: FcstmDiagramRenderOptions
): number {
    if (legend.length === 0) {
        return 0;
    }

    const height = options.padding
        + options.lineHeight
        + legend.length * options.lineHeight
        + options.padding;
    const group = container.group()
        .addClass('fcstm-panel')
        .addClass('fcstm-event-legend');

    group.rect(width, height)
        .move(x, y)
        .radius(18)
        .addClass('fcstm-panel-box');
    renderTextLine(group, x + options.padding, y + options.padding + 12, 'Shared Events', 'fcstm-panel-title');

    for (let index = 0; index < legend.length; index += 1) {
        const item = legend[index];
        const lineY = y + options.padding + options.lineHeight * (index + 2);
        group.rect(12, 12)
            .move(x + options.padding, lineY - 11)
            .radius(3)
            .addClass('fcstm-event-swatch')
            .fill(item.color);
        renderTextLine(
            group,
            x + options.padding + 20,
            lineY,
            `${item.label} · ${item.transitionCount} transition${item.transitionCount === 1 ? '' : 's'} · /${item.qualifiedName.split('.').slice(1).join('.')}`,
            'fcstm-panel-item'
        );
    }

    return height;
}

function renderTransitionLabel(
    container: SvgContainer,
    label: TransitionLabelLayout,
    options: FcstmDiagramRenderOptions
): void {
    const group = container.group();

    if (label.kind === 'label') {
        group.addClass('fcstm-transition-label');
        group.rect(label.frame.width, label.frame.height)
            .move(label.frame.x, label.frame.y)
            .radius(10)
            .addClass('fcstm-transition-label-box');
        for (let index = 0; index < label.lines.length; index += 1) {
            renderTextLine(
                group,
                label.frame.x + options.notePadding,
                label.frame.y + options.notePadding + 13 + index * options.lineHeight,
                label.lines[index],
                'fcstm-transition-label-text'
            );
        }
        return;
    }

    group.addClass('fcstm-transition-note');
    group.rect(label.frame.width, label.frame.height)
        .move(label.frame.x, label.frame.y)
        .radius(12)
        .addClass('fcstm-transition-note-box');
    group.path(
        `M ${label.frame.x + label.frame.width - 20} ${label.frame.y} `
        + `L ${label.frame.x + label.frame.width} ${label.frame.y} `
        + `L ${label.frame.x + label.frame.width} ${label.frame.y + 20} Z`
    ).addClass('fcstm-transition-note-fold');

    for (let index = 0; index < label.lines.length; index += 1) {
        renderTextLine(
            group,
            label.frame.x + options.notePadding,
            label.frame.y + options.notePadding + 13 + index * options.lineHeight,
            label.lines[index],
            'fcstm-transition-note-text'
        );
    }
}

function renderState(
    container: SvgContainer,
    state: FcstmDiagramState,
    layout: StateLayout,
    x: number,
    y: number,
    options: FcstmDiagramRenderOptions
): void {
    const kind = stateKindLabel(state);
    const group = container.group()
        .addClass('fcstm-state')
        .attr({
            'data-state-id': state.id,
            'data-state-kind': kind,
        });

    if (state.root) {
        group.addClass('root');
    }
    if (state.pseudo) {
        group.addClass('pseudo');
    }
    if (state.leaf) {
        group.addClass('leaf');
    } else {
        group.addClass('composite');
    }

    group.rect(layout.width, layout.height)
        .move(x, y)
        .radius(22)
        .addClass('fcstm-state-box');
    group.rect(layout.width, options.titleHeight)
        .move(x, y)
        .radius(22)
        .addClass('fcstm-state-title-bar');
    renderTextLine(group, x + options.padding, y + 24, layout.title, 'fcstm-state-title');

    const kindWidth = Math.max(58, measureText(kind) + 18);
    const kindX = x + layout.width - options.padding - kindWidth;
    const kindY = y + 10;
    group.rect(kindWidth, 18)
        .move(kindX, kindY)
        .radius(9)
        .addClass('fcstm-state-kind-pill');
    renderTextLine(group, kindX + 9, kindY + 13, kind, 'fcstm-state-kind');

    for (let index = 0; index < layout.metaLines.length; index += 1) {
        renderTextLine(
            group,
            x + options.padding,
            y + options.padding + options.titleHeight + options.sectionGap + 12 + index * options.lineHeight,
            layout.metaLines[index],
            'fcstm-state-meta'
        );
    }

    if (layout.startMarker) {
        const frame = translateRect(layout.startMarker, x, y);
        group.circle(frame.width)
            .center(frame.x + frame.width / 2, frame.y + frame.height / 2)
            .addClass('fcstm-start-node');
    }

    if (layout.endMarker) {
        const frame = translateRect(layout.endMarker, x, y);
        group.circle(Math.max(12, frame.width))
            .center(frame.x + frame.width / 2, frame.y + frame.height / 2)
            .addClass('fcstm-end-node-ring');
        group.circle(Math.max(8, frame.width - 10))
            .center(frame.x + frame.width / 2, frame.y + frame.height / 2)
            .addClass('fcstm-end-node-core');
    }

    const edgeLayer = group.group();
    const childLayer = group.group();
    const labelLayer = group.group();

    for (const edge of layout.edges) {
        if (edge.sections.length === 0) {
            continue;
        }

        const transitionColor = edge.transition.eventColor || '#2d6aa8';
        for (const section of edge.sections) {
            edgeLayer.path(renderPolyline(translatePoints(section.points, x, y)))
                .addClass('fcstm-transition-path')
                .attr({'marker-end': 'url(#fcstm-arrowhead)'})
                .stroke({color: transitionColor});
        }
    }

    for (const child of layout.children) {
        renderState(
            childLayer,
            child.state,
            child.layout,
            x + child.frame.x,
            y + child.frame.y,
            options
        );
    }

    for (const edge of layout.edges) {
        for (const label of edge.labels) {
            renderTransitionLabel(
                labelLayer,
                {
                    kind: label.kind,
                    lines: label.lines,
                    frame: translateRect(label.frame, x, y),
                },
                options
            );
        }
    }
}

function measureHeaderWidth(diagram: FcstmDiagram): number {
    const variableLines = diagram.variables.map(
        variable => `def ${variable.valueType} ${variable.name} = ${variable.initializer}`
    );
    const eventLines = diagram.eventLegend.map(
        item => `${item.label} · ${item.transitionCount} transitions · /${item.qualifiedName.split('.').slice(1).join('.')}`
    );

    return Math.max(
        measureText(diagram.machineName) + 180,
        measureText(diagram.filePath || '<memory>') + 180,
        measureMaxText(variableLines) + 96,
        measureMaxText(eventLines) + 96
    );
}

/**
 * Render the diagram IR into a standalone SVG document string.
 */
export async function renderFcstmDiagramSvg(
    diagram: FcstmDiagram,
    renderOptions: Partial<FcstmDiagramRenderOptions> = {}
): Promise<string> {
    const options: FcstmDiagramRenderOptions = {
        ...DEFAULT_RENDER_OPTIONS,
        ...renderOptions,
    };
    const rootLayout = await layoutState(diagram.rootState, options);
    const width = Math.max(
        options.minWidth,
        rootLayout.width + options.padding * 2,
        measureHeaderWidth(diagram) + options.padding * 2
    );
    const panelWidth = width - options.padding * 2;
    const panelsTop = options.headerHeight;
    const variablePanelHeight = diagram.variables.length > 0
        ? options.padding + options.lineHeight + diagram.variables.length * options.lineHeight + options.padding
        : 0;
    const legendPanelTop = panelsTop + variablePanelHeight + (variablePanelHeight > 0 ? options.panelGap : 0);
    const legendPanelHeight = diagram.eventLegend.length > 0
        ? options.padding + options.lineHeight + diagram.eventLegend.length * options.lineHeight + options.padding
        : 0;
    const panelsHeight = variablePanelHeight
        + (variablePanelHeight > 0 && legendPanelHeight > 0 ? options.panelGap : 0)
        + legendPanelHeight;
    const graphTop = options.headerHeight + panelsHeight + (panelsHeight > 0 ? options.panelGap : 0);
    const rootX = Math.round((width - rootLayout.width) / 2);
    const rootY = graphTop + options.stateGap;
    const outerStart = {
        x: rootX + rootLayout.width / 2,
        y: graphTop + 20,
    };
    const outerEnd = {
        x: rootX + rootLayout.width / 2,
        y: rootY + rootLayout.height + options.stateGap / 2,
    };
    const height = outerEnd.y + options.stateGap;
    const summaryEntries = [
        `vars ${diagram.summary.variables}`,
        `states ${diagram.summary.states}`,
        `events ${diagram.summary.events}`,
        `transitions ${diagram.summary.transitions}`,
        `actions ${diagram.summary.actions}`,
    ];
    const {draw} = createSvgDocument(width, height, `FCSTM preview for ${diagram.machineName}`);

    draw.addClass('fcstm-preview-root');
    draw.rect(width, height)
        .move(0, 0)
        .addClass('fcstm-root-bg');
    renderTextLine(draw, options.padding, 42, diagram.machineName, 'fcstm-title');
    renderTextLine(draw, options.padding, 66, diagram.filePath || '<memory>', 'fcstm-subtitle');

    let badgeX = options.padding;
    for (const entry of summaryEntries) {
        const badgeWidth = Math.max(78, measureText(entry) + 24);
        draw.rect(badgeWidth, 28)
            .move(badgeX, 82)
            .radius(14)
            .addClass('fcstm-summary-badge');
        renderTextLine(draw, badgeX + 12, 101, entry, 'fcstm-summary-text');
        badgeX += badgeWidth + 12;
    }

    renderVariablePanel(
        diagram.variables,
        draw,
        options.padding,
        panelsTop,
        panelWidth,
        options
    );
    renderEventLegendPanel(
        diagram.eventLegend,
        draw,
        options.padding,
        legendPanelTop,
        panelWidth,
        options
    );

    draw.circle(options.markerRadius * 2)
        .center(outerStart.x, outerStart.y)
        .addClass('fcstm-start-node');
    draw.circle((options.markerRadius + 1) * 2)
        .center(outerEnd.x, outerEnd.y)
        .addClass('fcstm-end-node-ring');
    draw.circle(Math.max(8, (options.markerRadius - 5) * 2))
        .center(outerEnd.x, outerEnd.y)
        .addClass('fcstm-end-node-core');

    const rootTopAnchor = {
        x: rootX + rootLayout.width / 2,
        y: rootY,
    };
    const rootBottomAnchor = {
        x: rootX + rootLayout.width / 2,
        y: rootY + rootLayout.height,
    };
    draw.path(
        `M ${outerStart.x} ${outerStart.y + options.markerRadius} `
        + `L ${outerStart.x} ${outerStart.y + 28} `
        + `L ${rootTopAnchor.x} ${rootTopAnchor.y - 28} `
        + `L ${rootTopAnchor.x} ${rootTopAnchor.y}`
    ).addClass('fcstm-machine-link')
        .attr({'marker-end': 'url(#fcstm-arrowhead)'});
    draw.path(
        `M ${rootBottomAnchor.x} ${rootBottomAnchor.y} `
        + `L ${rootBottomAnchor.x} ${rootBottomAnchor.y + 28} `
        + `L ${outerEnd.x} ${outerEnd.y - 28} `
        + `L ${outerEnd.x} ${outerEnd.y - options.markerRadius}`
    ).addClass('fcstm-machine-link')
        .attr({'marker-end': 'url(#fcstm-arrowhead)'});

    renderState(draw, diagram.rootState, rootLayout, rootX, rootY, options);
    return draw.svg();
}
