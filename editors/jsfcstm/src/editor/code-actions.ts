import {pathToFileURL} from 'node:url';

import type {FcstmSemanticDocument, FcstmSemanticImport, FcstmSemanticVariable} from '../semantics';
import {FcstmDiagnostic, TextDocumentLike, TextRange, createRange} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {FCSTM_DIAGNOSTIC_CODES} from './analyzers';
import {collectInspectModelDiagnostics, diagnosticKey} from './diagnostics';
import {rangeIntersects} from './ranges';
import type {FcstmWorkspaceEdit} from './references';
import {planSuggestedFixEdit, suggestedFixFromDiagnostic} from './suggested-fixes';

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

// ``findStateByRange`` removed — was defined but never invoked by any
// caller in this module or any consumer. PR-A-coverage audit (rule 3:
// dead code → delete).

function findDuplicateVariableByRange(
    semantic: FcstmSemanticDocument,
    range: TextRange
): FcstmSemanticVariable | undefined {
    const candidates = semantic.variables
        .filter(variable => rangeIntersects(variable.range, range));
    /* c8 ignore start */
    // Defensive: when no variable falls inside ``range`` we don't
    // have a quickfix target. Caller (code-action provider) only
    // invokes this with ranges intersecting an actual variable token.
    if (candidates.length === 0) {
        return undefined;
    }
    /* c8 ignore stop */
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
    const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(document);
    const node = snapshot.nodes[snapshot.rootFile];
    const semantic = node?.semantic;
    /* c8 ignore start */
    // Defensive: code-action provider only invokes against parsed
    // documents in the workspace graph; semantic is always present.
    if (!semantic) {
        return [];
    }
    /* c8 ignore stop */

    const actions: FcstmCodeAction[] = [];
    const relevantDiagnostics = diagnostics.filter(item => (
        !suggestedFixFromDiagnostic(item) && rangeIntersects(item.range, range)
    ));
    if (node?.model) {
        const existing = new Set<string>();
        const serverSuggestedKeysAtRange = new Set(
            collectInspectModelDiagnostics(document, semantic, node.model)
                .filter(diagnostic => (
                    suggestedFixFromDiagnostic(diagnostic) &&
                    rangeIntersects(diagnostic.range, range)
                ))
                .map(diagnosticKey),
        );
        for (const diagnostic of collectInspectModelDiagnostics(
            document,
            semantic,
            node.model,
            [],
            {rangeMode: 'issue'},
        )) {
            if (!suggestedFixFromDiagnostic(diagnostic)) continue;
            const key = diagnosticKey(diagnostic);
            // Suggested-fix diagnostics can have two useful server-derived
            // ranges: an edit-oriented published range and a broader issue
            // range for cursor discovery. Never use client-supplied
            // suggested_fix payloads as authorization for either range.
            if (!rangeIntersects(diagnostic.range, range) && !serverSuggestedKeysAtRange.has(key)) continue;
            if (existing.has(key)) continue;
            existing.add(key);
            relevantDiagnostics.push(diagnostic);
        }
    }

    for (const diagnostic of relevantDiagnostics) {
        const suggestedFix = suggestedFixFromDiagnostic(diagnostic);
        if (suggestedFix) {
            const plan = planSuggestedFixEdit(document, semantic, diagnostic);
            if (plan) {
                actions.push({
                    title: `${suggestedFix.rationale} (${diagnostic.code ?? 'suggested fix'})`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, plan.range, plan.newText),
                });
            }
            continue;
        }

        if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.importNotFound) {
            const importItem = findImportByRange(semantic, diagnostic.range);
            if (importItem) {
                actions.push({
                    title: `Remove unresolved import ${JSON.stringify(importItem.sourcePath)}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, importItem.range, ''),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.importDuplicateMapping) {
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
        } else if (
            diagnostic.code === FCSTM_DIAGNOSTIC_CODES.missingState
            || diagnostic.code === FCSTM_DIAGNOSTIC_CODES.danglingTransition
        ) {
            // Both E_MISSING_STATE (source state unresolved) and
            // E_DANGLING_TRANSITION (target state unresolved) carry the
            // offending state name in the diagnostic message; offer the
            // same "rename to a close match" quick fix for either case.
            const stateName = diagnostic.message.match(/"([^"]+)"/)?.[1];
            /* c8 ignore start */
            // Defensive: the diagnostic message template always wraps
            // the offending state name in double quotes; missing
            // capture indicates a future message-format change.
            if (!stateName) {
                continue;
            }
            /* c8 ignore stop */

            const candidates = uniqueCaseInsensitiveStateCandidates(semantic, stateName);
            if (candidates.length === 1) {
                actions.push({
                    title: `Change to ${candidates[0]}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, diagnostic.range, candidates[0]),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.duplicateVar) {
            const duplicate = findDuplicateVariableByRange(semantic, diagnostic.range);
            if (duplicate) {
                actions.push({
                    title: `Remove duplicate definition of ${JSON.stringify(duplicate.name)}`,
                    kind: 'quickfix',
                    diagnostics: [diagnostic],
                    edit: createWorkspaceEdit(document, duplicate.range, ''),
                });
            }
        } else if (diagnostic.code === FCSTM_DIAGNOSTIC_CODES.undefinedVar) {
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
