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
    FcstmDiagramPreviewOptionsInput,
    FcstmDiagramWebviewPayload,
} from './model';
import type {TextDocumentLike} from '../utils/text';

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

    return {
        filePath: diagram.filePath,
        machineName: diagram.machineName,
        summary: diagram.summary,
        variables: diagram.variables,
        eventLegend: diagram.eventLegend,
        graph,
        effectNotes,
        options,
    };
}
