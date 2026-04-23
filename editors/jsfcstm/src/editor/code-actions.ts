import {pathToFileURL} from 'node:url';

import type {FcstmSemanticDocument, FcstmSemanticImport, FcstmSemanticState, FcstmSemanticVariable} from '../semantics';
import {FcstmDiagnostic, TextDocumentLike, TextRange, createRange} from '../utils/text';
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

function findDuplicateVariableByRange(
    semantic: FcstmSemanticDocument,
    range: TextRange
): FcstmSemanticVariable | undefined {
    const candidates = semantic.variables
        .filter(variable => rangeIntersects(variable.range, range));
    if (candidates.length === 0) {
        return undefined;
    }
    // Only duplicates (second and later definitions of the same name) should
    // be removable. The first definition has no duplicateVariable diagnostic.
    const grouped = new Map<string, FcstmSemanticVariable[]>();
    for (const variable of semantic.variables) {
        const bucket = grouped.get(variable.name) || [];
        bucket.push(variable);
        grouped.set(variable.name, bucket);
    }
    return candidates.find(candidate => {
        const bucket = grouped.get(candidate.name) || [];
        return bucket.length > 1 && bucket[0] !== candidate;
    });
}

function extractIdentifierFromMessage(message: string): string | undefined {
    return message.match(/"([^"]+)"/)?.[1];
}

function guessVariableType(semantic: FcstmSemanticDocument): 'int' | 'float' {
    for (const variable of semantic.variables) {
        return variable.valueType;
    }
    return 'int';
}

function planVariableInsertion(
    document: TextDocumentLike,
    semantic: FcstmSemanticDocument,
    name: string
): {range: TextRange; newText: string} {
    const valueType = guessVariableType(semantic);
    const declaration = `def ${valueType} ${name} = 0;\n`;

    if (semantic.variables.length > 0) {
        const last = semantic.variables[semantic.variables.length - 1];
        const insertionLine = last.range.end.line + 1;
        const zeroRange = createRange(insertionLine, 0, insertionLine, 0);
        return {range: zeroRange, newText: declaration};
    }
    return {range: createRange(0, 0, 0, 0), newText: declaration};
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
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.duplicateVariable) {
            const duplicate = findDuplicateVariableByRange(semantic, diagnostic.range);
            if (duplicate) {
                actions.push({
                    title: `Remove duplicate definition of ${JSON.stringify(duplicate.name)}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, duplicate.range, ''),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.undefinedVariable) {
            const name = extractIdentifierFromMessage(diagnostic.message);
            if (name && /^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
                const insertion = planVariableInsertion(document, semantic, name);
                actions.push({
                    title: `Define ${JSON.stringify(name)} at the top of the file`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, insertion.range, insertion.newText),
                });
            }
        }
    }

    return actions;
}
