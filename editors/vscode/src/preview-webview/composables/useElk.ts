import type {PreviewElkGraph, PreviewElkNode} from '../types';

// ``ELK`` is provided by the browser bundle (elk.bundled.js) that the
// extension host inlines into the webview HTML before this module runs.
declare const ELK: {
    new(): {layout(graph: PreviewElkGraph): Promise<PreviewElkNode>};
};

let elkInstance: {layout(graph: PreviewElkGraph): Promise<PreviewElkNode>} | null = null;

export function getElk() {
    if (!elkInstance) {
        elkInstance = new ELK();
    }
    return elkInstance;
}
