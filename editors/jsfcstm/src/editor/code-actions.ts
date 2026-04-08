import {pathToFileURL} from 'node:url';

import type {FcstmSemanticDocument, FcstmSemanticImport, FcstmSemanticState} from '../semantics';
import {FcstmDiagnostic, TextDocumentLike, TextRange} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {FCSTM_DIAGNOSTIC_CODES} from './analyzers';
import {rangeIntersects} from './ranges';
import type {FcstmWorkspaceEdit} from './references';

export type FcstmCodeActionKind = 'quickfix' | 'refactor.rename';

export interface FcstmCodeAction {
    title: string;
    kind: FcstmCodeActionKind;
    diagnostics?: FcstmDiagnostic[];
    edit?: FcstmWorkspaceEdit;
}

function makeFileUri(document: TextDocumentLike): string {
    const filePath = document.filePath || document.uri?.fsPath || '';
    return filePath.startsWith('file:') ? filePath : pathToFileURL(filePath).toString();
}

function createWorkspaceEdit(document: TextDocumentLike, range: TextRange, newText: string): FcstmWorkspaceEdit {
    return {
        changes: {
            [makeFileUri(document)]: [{
                range,
                newText,
            }],
        },
    };
}

function findImportByRange(semantic: FcstmSemanticDocument, range: TextRange): FcstmSemanticImport | undefined {
    return semantic.imports.find(item => rangeIntersects(item.range, range));
}

function findStateByRange(semantic: FcstmSemanticDocument, range: TextRange): FcstmSemanticState | undefined {
    return semantic.states.find(item => rangeIntersects(item.range, range));
}

function uniqueCaseInsensitiveStateCandidates(
    semantic: FcstmSemanticDocument,
    currentName: string
): string[] {
    const normalized = currentName.toLowerCase();
    return [...new Set(
        semantic.states
            .map(item => item.name)
            .filter(name => name.toLowerCase() === normalized && name !== currentName)
    )];
}

/**
 * Build code actions / quick fixes for the selected FCSTM range.
 */
export async function collectCodeActions(
    document: TextDocumentLike,
    range: TextRange,
    diagnostics: FcstmDiagnostic[] = []
): Promise<FcstmCodeAction[]> {
    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    if (!semantic) {
        return [];
    }

    const actions: FcstmCodeAction[] = [];
    const relevantDiagnostics = diagnostics.filter(item => rangeIntersects(item.range, range));

    for (const diagnostic of relevantDiagnostics) {
        if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.missingImport) {
            const importItem = findImportByRange(semantic, diagnostic.range);
            if (importItem) {
                actions.push({
                    title: `Remove unresolved import ${JSON.stringify(importItem.sourcePath)}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, importItem.range, ''),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.duplicateImportMapping) {
            const importItem = findImportByRange(semantic, diagnostic.range);
            const duplicateMapping = importItem?.ast.mappings.find(item => rangeIntersects(item.range, diagnostic.range));
            if (duplicateMapping) {
                actions.push({
                    title: `Remove duplicate import mapping ${JSON.stringify(duplicateMapping.text)}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, duplicateMapping.range, ''),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.unusedEvent) {
            const event = semantic.events.find(item => (
                item.declared
                && item.declarationAst
                && rangeIntersects(item.declarationAst.range, diagnostic.range)
            ));
            if (event?.declarationAst) {
                actions.push({
                    title: `Remove unused event ${JSON.stringify(event.name)}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, event.declarationAst.range, ''),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.unresolvedState) {
            const stateName = diagnostic.message.match(/"([^"]+)"/)?.[1];
            if (!stateName) {
                continue;
            }

            const candidates = uniqueCaseInsensitiveStateCandidates(semantic, stateName);
            if (candidates.length === 1) {
                actions.push({
                    title: `Change to ${candidates[0]}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, diagnostic.range, candidates[0]),
                });
            }
        }
    }

    return actions;
}
