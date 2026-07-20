export {
    buildFcstmDiagramFromDocument,
    buildFcstmDiagramFromStateMachine,
    buildFcstmDiagramFromWorkspaceSnapshot,
    formatFcstmDiagramActionLabel,
    formatFcstmDiagramEventLabel,
    formatFcstmDiagramTransitionLabel,
} from './builder';
export {resolveFcstmDiagramPreviewOptions} from './options';
export {
    collectFcstmDiagramEffectNotes,
    formatFcstmDiagramTransitionEventLabel,
    formatFcstmDiagramTransitionGuardLabel,
    formatFcstmDiagramTransitionInlineEffectLabel,
    renderFcstmDiagramMermaid,
    renderFcstmDiagramMermaidView,
} from './render';
export {
    buildFcstmElkGraph,
    collectElkLayoutGeometry,
    measureLabel as measureFcstmElkLabel,
    MIN_TERMINAL_SEGMENT,
    MIN_SELF_LOOP_SEGMENT,
    terminalApproach,
} from './elk-graph';
export type {FcstmElkLayoutGeometry, FcstmElkNodeBox, FcstmElkPoint} from './elk-graph';
export {
    renderFcstmDiagramSvg,
    renderSvg,
} from './svg-renderer';
export {
    smoothGraphEdges,
    DEFAULT_MIN_STUB_LEN,
} from './render/edge-smoother';
export {
    buildCrossingIndex,
    collectSegments,
    crossingsFor,
} from './render/crossings';
export {
    resolvePalette,
    PALETTE_IDS,
    PALETTE_LABEL,
} from './render/palette';
export type {
    CrossingIndex,
    ResolvedSegment,
} from './render/crossings';
export type {
    PaletteId,
    PaletteMode,
    SvgPalette,
} from './render/palette';
export type {RenderOptions, RenderedSvg} from './svg-renderer';
export {
    buildFcstmDiagramWebviewPayload,
} from './webview-payload';
export type {
    FcstmDiagram,
    FcstmDiagramAction,
    FcstmDiagramDetailLevel,
    FcstmDiagramEffectNote,
    FcstmDiagramEvent,
    FcstmDiagramEventNameFormatPart,
    FcstmDiagramEventVisualizationMode,
    FcstmDiagramMermaidRenderResult,
    FcstmDiagramPreviewOptions,
    FcstmDiagramPreviewOptionsInput,
    FcstmDiagramRenderedTransition,
    FcstmDiagramState,
    FcstmDiagramStateDetail,
    FcstmDiagramSummary,
    FcstmDiagramTransition,
    FcstmDiagramTransitionDetail,
    FcstmDiagramTransitionEffectMode,
    FcstmDiagramVariable,
    FcstmDiagramWebviewPayload,
    FcstmElkEdge,
    FcstmElkEdgeMeta,
    FcstmElkGraph,
    FcstmElkNode,
    FcstmElkNodeMeta,
    ResolvedFcstmDiagramPreviewOptions,
} from './model';
