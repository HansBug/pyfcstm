/**
 * Temporary boundary until region model construction and active-query lowering
 * exist. Remove each rejection with its model implementation, then delete this
 * module. Execution and rendering support are checked by their own entry points.
 */
import type {FcstmAstDocument, FcstmAstNodeBase} from './model';
import type {FcstmDiagnostic} from '../utils/text';

/** Refuse parsed features before an executable model can omit their behavior. */
export function collectUnsupportedSyntaxDiagnostics(ast: FcstmAstDocument): FcstmDiagnostic[] {
    const diagnostics: FcstmDiagnostic[] = [];
    const visited = new Set<object>();
    const sites = new Set<string>();
    function visit(value: unknown): void {
        if (value === null || typeof value !== 'object' || visited.has(value)) return;
        visited.add(value);
        const node = value as FcstmAstNodeBase;
        const feature = node.pyNodeType === 'RegionDefinition' ? 'region'
            : node.pyNodeType === 'ActiveStateQuery' ? 'active' : null;
        if (feature !== null) {
            const site = `${feature}:${JSON.stringify(node.range)}`;
            if (!sites.has(site)) {
                sites.add(site);
                diagnostics.push({
                    code: 'E_UNSUPPORTED_FEATURE', severity: 'error', source: 'fcstm',
                    range: node.range,
                    message: `The '${feature}' feature is parsed but is not supported by model construction.`,
                    data: {feature, source_path: ast.filePath},
                });
            }
            return;
        }
        for (const child of Object.values(value)) visit(child);
    }
    visit(ast);
    return diagnostics;
}
