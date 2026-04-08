import {pathToFileURL} from 'node:url';

import {getWorkspaceGraph} from '../workspace';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {createRange, TextDocumentLike, TextPositionLike, TextRange} from '../utils/text';

/**
 * Definition target resolved from an FCSTM source location.
 */
export interface FcstmDefinitionLocation {
    uri: string;
    range: TextRange;
}

/**
 * Clickable document link resolved from FCSTM source.
 */
export interface FcstmDocumentLink {
    range: TextRange;
    target: string;
    tooltip?: string;
}

function toFileUri(filePath: string): string {
    return pathToFileURL(filePath).toString();
}

/**
 * Resolve definition locations for import-path navigation.
 *
 * The current FCSTM definition experience is intentionally conservative:
 * it only navigates import path strings to the imported module entry file.
 */
export async function resolveDefinitionLocation(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmDefinitionLocation | null> {
    const resolved = await getImportWorkspaceIndex().getResolvedImportAtPosition(document, position);
    if (!resolved?.target.entryFile) {
        return null;
    }

    return {
        uri: toFileUri(resolved.target.entryFile),
        range: createRange(0, 0, 0, 0),
    };
}

/**
 * Collect document links for import-path strings.
 */
export async function collectDocumentLinks(
    document: TextDocumentLike
): Promise<FcstmDocumentLink[]> {
    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    if (!semantic) {
        return [];
    }

    const links: FcstmDocumentLink[] = [];
    for (const item of semantic.imports) {
        const targetFile = item.entryFile || item.resolvedFile;
        if (!targetFile || item.missing) {
            continue;
        }

        links.push({
            range: item.pathRange,
            target: toFileUri(targetFile),
            tooltip: item.targetRootStateName
                ? `Open imported module ${item.targetRootStateName}`
                : 'Open imported module',
        });
    }

    return links;
}
