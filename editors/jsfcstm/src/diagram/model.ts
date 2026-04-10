/* c8 ignore file */
import type {TextRange} from '../utils/text';

/**
 * Summary counts exposed by the diagram layer.
 */
export interface FcstmDiagramSummary {
    variables: number;
    states: number;
    events: number;
    transitions: number;
    actions: number;
}

/**
 * Variable definition shown in the preview header.
 */
export interface FcstmDiagramVariable {
    name: string;
    valueType: 'int' | 'float';
    initializer: string;
}

/**
 * Event item declared on a state.
 */
export interface FcstmDiagramEvent {
    name: string;
    qualifiedName: string;
    displayName?: string;
    declared: boolean;
    origins: Array<'declared' | 'local' | 'chain' | 'absolute'>;
    range: TextRange;
}

/**
 * Lifecycle action item declared on a state.
 */
export interface FcstmDiagramAction {
    name?: string;
    qualifiedName: string;
    stage: 'enter' | 'during' | 'exit';
    aspect?: 'before' | 'after';
    mode: 'operations' | 'abstract' | 'ref';
    abstract: boolean;
    reference: boolean;
    globalAspect: boolean;
    operationCount: number;
    label: string;
    range: TextRange;
}

/**
 * Transition between sibling states or pseudo start/end nodes inside one scope.
 */
export interface FcstmDiagramTransition {
    id: string;
    sourceLabel: string;
    targetLabel: string;
    label: string;
    triggerLabel?: string;
    guardLabel?: string;
    effectLines: string[];
    eventName?: string;
    eventDisplayName?: string;
    eventRelativePath?: string;
    eventAbsolutePath?: string;
    triggerScope?: 'local' | 'chain' | 'absolute';
    forced: boolean;
    sourceKind: 'init' | 'state';
    targetKind: 'state' | 'exit';
    sourceStatePath?: string[];
    targetStatePath?: string[];
    eventQualifiedName?: string;
    eventColor?: string;
    range: TextRange;
}

/**
 * Repeated-event legend item used to color related transitions.
 */
export interface FcstmDiagramEventLegendItem {
    qualifiedName: string;
    label: string;
    transitionCount: number;
    color: string;
}

/**
 * Hierarchical state node in the diagram IR.
 */
export interface FcstmDiagramState {
    id: string;
    name: string;
    qualifiedName: string;
    displayName?: string;
    pseudo: boolean;
    leaf: boolean;
    root: boolean;
    range: TextRange;
    events: FcstmDiagramEvent[];
    actions: FcstmDiagramAction[];
    transitions: FcstmDiagramTransition[];
    children: FcstmDiagramState[];
}

/**
 * Top-level diagram IR for the FCSTM preview.
 */
export interface FcstmDiagram {
    kind: 'diagram';
    filePath: string;
    machineName: string;
    summary: FcstmDiagramSummary;
    variables: FcstmDiagramVariable[];
    eventLegend: FcstmDiagramEventLegendItem[];
    rootState: FcstmDiagramState;
}

/**
 * Preview detail-level preset aligned with the pyfcstm PlantUML option system.
 */
export type FcstmDiagramDetailLevel = 'minimal' | 'normal' | 'full';

/**
 * Supported event-name display elements.
 */
export type FcstmDiagramEventNameFormatPart = 'name' | 'extra_name' | 'path' | 'relpath';

/**
 * Supported transition-effect display modes.
 */
export type FcstmDiagramTransitionEffectMode = 'note' | 'inline' | 'hide';

/**
 * Shared-event visualization mode for the preview.
 */
export type FcstmDiagramEventVisualizationMode = 'none' | 'color' | 'legend' | 'both';

/**
 * Input options for the diagram preview and Mermaid renderer.
 */
export interface FcstmDiagramPreviewOptions {
    detailLevel?: FcstmDiagramDetailLevel;
    direction?: 'TB' | 'LR';
    showVariableDefinitions?: boolean;
    showEvents?: boolean;
    eventNameFormat?: FcstmDiagramEventNameFormatPart[];
    showTransitionGuards?: boolean;
    showTransitionEffects?: boolean;
    transitionEffectMode?: FcstmDiagramTransitionEffectMode;
    eventVisualizationMode?: FcstmDiagramEventVisualizationMode;
    showStateEvents?: boolean;
    showStateActions?: boolean;
    maxStateEvents?: number;
    maxStateActions?: number;
    maxTransitionEffectLines?: number;
    maxLabelLength?: number;
}

/**
 * Fully-resolved preview options with defaults applied.
 */
export interface ResolvedFcstmDiagramPreviewOptions {
    detailLevel: FcstmDiagramDetailLevel;
    direction: 'TB' | 'LR';
    showVariableDefinitions: boolean;
    showEvents: boolean;
    eventNameFormat: FcstmDiagramEventNameFormatPart[];
    showTransitionGuards: boolean;
    showTransitionEffects: boolean;
    transitionEffectMode: FcstmDiagramTransitionEffectMode;
    eventVisualizationMode: FcstmDiagramEventVisualizationMode;
    showStateEvents: boolean;
    showStateActions: boolean;
    maxStateEvents: number;
    maxStateActions: number;
    maxTransitionEffectLines: number;
    maxLabelLength: number;
}

/**
 * External preview-option input accepted by jsfcstm.
 */
export type FcstmDiagramPreviewOptionsInput =
    | FcstmDiagramDetailLevel
    | Partial<FcstmDiagramPreviewOptions>
    | null
    | undefined;

/**
 * Stable note payload for transition effects rendered outside the Mermaid edge label.
 */
export interface FcstmDiagramEffectNote {
    transitionId: string;
    title: string;
    meta?: string;
    effectText: string;
    lineCount: number;
    eventColor?: string;
}

/**
 * Transition order metadata for post-render color application in the webview layer.
 */
export interface FcstmDiagramRenderedTransition {
    id: string;
    eventColor?: string;
}

/**
 * Mermaid render result that carries the emitted source plus transition order metadata.
 */
export interface FcstmDiagramMermaidRenderResult {
    source: string;
    renderedTransitions: FcstmDiagramRenderedTransition[];
}
