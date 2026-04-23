/**
 * Shared message / state types between the extension host and the
 * Vue-powered webview. Imported by both sides.
 */

export type PreviewLayoutMode = 'side' | 'alone';

export interface PreviewSummaryEntry {
    label: string;
    value: number;
}

export interface PreviewSharedEventView {
    label: string;
    qualifiedName: string;
    transitionCount: number;
    color: string;
}

// Payload details: mirrored from jsfcstm FcstmDiagramStateDetail /
// FcstmDiagramTransitionDetail but redeclared here so the webview bundle
// has no dependency on the full jsfcstm chain.
export interface PreviewStateDetail {
    qualifiedName: string;
    displayName?: string;
    name: string;
    kind: 'leaf' | 'composite' | 'pseudoState';
    events: Array<{name: string; displayName?: string}>;
    actions: Array<{
        stage: string;
        aspect?: string;
        mode: string;
        name?: string;
        globalAspect?: boolean;
        body?: string;
    }>;
    transitionIds: string[];
    sourceRange?: TextRange;
}

export interface PreviewTransitionDetail {
    transitionId: string;
    from: string;
    to: string;
    kind: 'entry' | 'normal' | 'exit' | 'forced';
    forced: boolean;
    eventLabel?: string;
    eventQualifiedName?: string;
    triggerScope?: 'local' | 'chain' | 'absolute';
    guardLabel?: string;
    effectLines?: string[];
    eventColor?: string;
    sourceRange?: TextRange;
}

export interface TextRange {
    start: {line: number; character: number};
    end: {line: number; character: number};
}

export interface PreviewResolvedOptions {
    detailLevel: 'minimal' | 'normal' | 'full';
    direction: 'TB' | 'LR';
    showVariableDefinitions: boolean;
    showEvents: boolean;
    showTransitionGuards: boolean;
    showTransitionEffects: boolean;
    transitionEffectMode: 'note' | 'inline' | 'hide';
    eventVisualizationMode: 'none' | 'color' | 'legend' | 'both';
    showStateEvents: boolean;
    showStateActions: boolean;
    eventNameFormat: string[];
    maxStateEvents: number;
    maxStateActions: number;
    maxTransitionEffectLines: number;
    maxLabelLength: number;
}

export interface PreviewPayload {
    filePath: string;
    machineName: string;
    summary: {
        variables: number;
        states: number;
        events: number;
        transitions: number;
        actions: number;
    };
    variables: Array<{name: string; valueType: string; initializer: string}>;
    eventLegend: Array<{
        qualifiedName: string;
        label: string;
        transitionCount: number;
        color: string;
    }>;
    graph: PreviewElkGraph;
    effectNotes: Array<{
        title: string;
        meta?: string;
        effectText: string;
        eventColor?: string;
    }>;
    options: PreviewResolvedOptions;
    states: PreviewStateDetail[];
    transitions: PreviewTransitionDetail[];
}

export interface PreviewElkGraph extends PreviewElkNode {
    id: '__canvas__';
    layoutOptions: Record<string, string>;
    children: PreviewElkNode[];
    edges: PreviewElkEdge[];
}

export interface PreviewElkNode {
    id: string;
    width?: number;
    height?: number;
    x?: number;
    y?: number;
    labels?: Array<{text: string; width: number; height: number; x?: number; y?: number}>;
    children?: PreviewElkNode[];
    edges?: PreviewElkEdge[];
    layoutOptions?: Record<string, string>;
    fcstm?: PreviewElkNodeMeta;
}

export interface PreviewElkNodeMeta {
    kind: 'state' | 'pseudoInit' | 'pseudoExit' | 'canvas';
    qualifiedName?: string;
    displayName?: string;
    pseudo?: boolean;
    composite?: boolean;
    collapsed?: boolean;
    sourceRange?: TextRange;
    eventLabels?: string[];
    actionLabels?: string[];
}

export interface PreviewElkEdge {
    id: string;
    sources: string[];
    targets: string[];
    labels?: Array<{text: string; width: number; height: number; x?: number; y?: number}>;
    sections?: Array<{
        startPoint: {x: number; y: number};
        endPoint: {x: number; y: number};
        bendPoints?: Array<{x: number; y: number}>;
    }>;
    fcstm?: PreviewElkEdgeMeta;
}

export interface PreviewElkEdgeMeta {
    kind: 'transition';
    transitionId: string;
    eventColor?: string;
    forced?: boolean;
    transitionKind: 'entry' | 'normal' | 'exit' | 'normalAll' | 'exitAll';
    sourceRange?: TextRange;
    eventLabel?: string;
    guardLabel?: string;
    effectLines?: string[];
    hasNoteEffect?: boolean;
}

export interface PreviewWebviewState {
    title: string;
    filePath: string;
    rootStateName?: string;
    payload?: PreviewPayload;
    previewOptions: PreviewResolvedOptions;
    collapsedStateIds: string[];
    emptyTitle: string;
    emptyMessage: string;
    summary: PreviewSummaryEntry[];
    variables: string[];
    sharedEvents: PreviewSharedEventView[];
}

export type SelectionRef =
    | {kind: 'state' | 'composite-state' | 'pseudo-init' | 'pseudo-exit'; id: string}
    | {kind: 'transition'; id: string}
    | null;

export type WebviewInboundMessage =
    | {type: 'patchOptions'; options: Record<string, unknown>}
    | {type: 'setCollapsed'; collapsed: string[]}
    | {type: 'revealSource'; range: TextRange}
    | {type: 'setLayoutMode'; mode: PreviewLayoutMode}
    | {type: 'exportSvg'; svg: string}
    | {type: 'exportPng'; base64: string}
    | {type: 'exportError'; message: string};

/**
 * Host → webview messages that carry editor-driven cues rather than a full
 * state push. The webview distinguishes them from state updates by the
 * discriminant ``type`` field, which state payloads do not set.
 */
export type HostOutboundCue =
    | {type: 'setActiveRange'; range: TextRange | null};
