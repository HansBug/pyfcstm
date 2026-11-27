/**
 * Region structure and activity-query diagnostics.
 *
 * These checks read the parsed document, because the repeated region names and
 * empty regions they report never reach the model. They mirror
 * ``pyfcstm.model.region.validate_region_structure`` and the binding rules of
 * ``pyfcstm.model.active``, so both ends report the same code and reason for
 * the same input. The grammar already refuses a state that mixes states with
 * regions, a region owner with its own transitions, and a query in a persistent
 * initializer, so the reasons ``mixed_children``, ``owner_statements`` and
 * ``initializer`` cannot arise from text and are not reported here.
 *
 * The module contains:
 * - :func:`collectRegionDiagnostics` - ``E_REGION_STRUCTURE``, ``E_DUPLICATE_REGION`` and ``E_ACTIVE_QUERY_TARGET``
 *
 * A query whose path enters an imported module is not judged here, because the
 * imported states exist only after the imports are assembled; it is bound
 * against the assembled model when the diagram is built.
 */
import type {
    FcstmAstDocument,
    FcstmAstNodeBase,
    FcstmAstRegionDefinition,
    FcstmAstStateDefinition,
} from '../ast';
import type {FcstmDiagnostic, TextDocumentLike} from '../utils/text';
import {findIdentifierRange} from './ranges';

type Scope = FcstmAstStateDefinition | FcstmAstRegionDefinition;

const IDENTIFIER = /^[A-Za-z_][A-Za-z_0-9]*$/;

function regionsOf(node: Scope): FcstmAstRegionDefinition[] {
    return node.kind === 'regionDefinition' ? [] : node.regions;
}

function regionOwnerImports(node: Scope): FcstmAstStateDefinition['imports'] {
    return node.kind === 'regionDefinition' ? [] : node.imports;
}

function hasRegions(node: Scope): boolean {
    return regionsOf(node).length > 0 || node.substates.some(hasRegions);
}

function structureReason(node: Scope): 'empty_region' | 'history_boundary' | null {
    if (node.kind === 'regionDefinition' && node.substates.length === 0) return 'empty_region';
    const owner = node as FcstmAstStateDefinition;
    if (owner.histories?.length > 0 && hasRegions(node)) return 'history_boundary';
    return null;
}

function checkStructure(
    node: Scope,
    path: string[],
    document: TextDocumentLike,
    sourcePath: string,
    diagnostics: FcstmDiagnostic[],
): boolean {
    const here = [...path, node.name];
    const regions = regionsOf(node);
    let invalid = false;
    const reason = structureReason(node);
    if (reason !== null) {
        invalid = true;
        diagnostics.push({
            range: findIdentifierRange(document, node.name, node.range),
            message: `Invalid region structure at ${here.join('.')} (${reason}).`,
            severity: 'error',
            source: 'fcstm',
            code: 'E_REGION_STRUCTURE',
            data: {namespace_path: here.join('.'), reason, source_path: sourcePath},
        });
    }
    const seen = new Map<string, FcstmAstRegionDefinition>();
    for (const region of regions) {
        const previous = seen.get(region.name);
        if (previous) {
            invalid = true;
            diagnostics.push({
                range: findIdentifierRange(document, region.name, region.range),
                message: `Duplicate region ${JSON.stringify(region.name)} in ${here.join('.')}.`,
                severity: 'error',
                source: 'fcstm',
                code: 'E_DUPLICATE_REGION',
                data: {
                    region_name: region.name,
                    owner_path: here.join('.'),
                    previous_span: previous.range,
                    source_path: sourcePath,
                },
            });
        }
        seen.set(region.name, region);
    }
    for (const child of [...node.substates, ...regions]) {
        invalid = checkStructure(child, here, document, sourcePath, diagnostics) || invalid;
    }
    return invalid;
}

function bindQuery(root: FcstmAstStateDefinition, path: string): string | null {
    const parts = path.startsWith('/') ? [root.name, ...path.slice(1).split('.')] : path.split('.');
    if (!parts.every(part => IDENTIFIER.test(part)) || parts[0] !== root.name) return 'invalid_path';
    let current: Scope = root;
    for (const segment of parts.slice(1)) {
        const next: Scope | undefined = current.substates.find(item => item.name === segment)
            ?? regionsOf(current).find(item => item.name === segment);
        if (!next) {
            // A segment that names an import alias leads into a module that only
            // the assembled model knows; leave such a path to it.
            return regionOwnerImports(current).some(item => item.alias === segment) ? null : 'not_found';
        }
        current = next;
    }
    if (current.kind === 'regionDefinition') return 'region';
    return (current as FcstmAstStateDefinition).pseudo ? 'pseudo' : null;
}

function checkQueries(
    root: FcstmAstStateDefinition,
    sourcePath: string,
    diagnostics: FcstmDiagnostic[],
): void {
    const visited = new Set<object>();
    // A query shared by the guard fields of one transition is reported once.
    const reported = new Set<string>();
    const visit = (value: unknown): void => {
        if (value === null || typeof value !== 'object' || visited.has(value)) return;
        visited.add(value);
        const node = value as FcstmAstNodeBase & {path?: string};
        if (node.pyNodeType === 'ActiveStateQuery' && typeof node.path === 'string') {
            const reason = bindQuery(root, node.path);
            if (reason !== null && !reported.has(JSON.stringify(node.range))) {
                reported.add(JSON.stringify(node.range));
                diagnostics.push({
                    range: node.range,
                    message: `Active query ${JSON.stringify(node.path)} cannot be bound (${reason}).`,
                    severity: 'error',
                    source: 'fcstm',
                    code: 'E_ACTIVE_QUERY_TARGET',
                    data: {state_path: node.path, reason, source_path: sourcePath},
                });
            }
            return;
        }
        for (const child of Object.values(value)) visit(child);
    };
    visit(root);
}

/**
 * Check the region structure and the activity queries of one parsed document.
 *
 * Queries are checked only when the region structure is sound, as the Python
 * model does, because an unsound structure has no namespace to bind them in.
 *
 * @param ast The parsed document.
 * @param document The text the diagnostics point into.
 * @returns The diagnostics, in document traversal order.
 */
export function collectRegionDiagnostics(ast: FcstmAstDocument, document: TextDocumentLike): FcstmDiagnostic[] {
    const root = ast.rootState;
    if (!root) return [];
    const diagnostics: FcstmDiagnostic[] = [];
    const invalid = checkStructure(root, [], document, ast.filePath, diagnostics);
    if (!invalid) checkQueries(root, ast.filePath, diagnostics);
    return diagnostics;
}
