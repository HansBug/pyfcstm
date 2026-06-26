/**
 * Runtime accessor for the shared diagnostic codes registry.
 *
 * The canonical registry lives at ``pyfcstm/diagnostics/codes.yaml`` in
 * the repository root. The jsfcstm build script
 * (``scripts/sync-runtime-assets.js``) converts it to JSON and syncs
 * the result into ``src/diagnostics/codes.json`` before TypeScript
 * compilation. The JSON contents are inlined via ``resolveJsonModule``
 * so downstream bundlers ship the catalog inside a single bundle and
 * the published npm tarball needs no YAML dependency on the consumer
 * side.
 */

// eslint-disable-next-line @typescript-eslint/no-var-requires
const codesContents = require('./codes.json') as Record<string, CodeSpec>;

/**
 * One field inside a diagnostic code's ``refs`` schema.
 */
export interface CodeFieldSpec {
    type: string;
    required?: boolean;
    description?: string;
    enum?: readonly string[];
    item_enum?: readonly string[];
    exact_values?: readonly string[];
}

/**
 * Structured LLM-facing guidance attached to a diagnostic code.
 */
export interface ForLlmSpec {
    summary: string;
    recommended_actions: Array<Record<string, unknown>>;
    do_not: string[];
}

/**
 * Structured auto-fix metadata declared by ``codes.yaml``.
 */
export interface SuggestedFixSpec {
    kind: 'insert' | 'delete' | 'replace';
    target: string;
    anchor_ref: string;
    text_template?: string;
    rationale: string;
}

/**
 * Specification for a single diagnostic code as expressed in
 * ``codes.yaml``.
 */
export interface CodeSpec {
    severity: 'error' | 'warning' | 'info';
    span_object?:
        | 'state_identifier'
        | 'transition'
        | 'guard_expression'
        | 'effect_statement'
        | 'composite_block'
        | 'named_action_declaration'
        | 'event_declaration'
        | 'variable_declaration'
        | 'expression'
        | 'lifecycle_action'
        | 'import_statement';
    description: string;
    refs?: Record<string, CodeFieldSpec>;
    capability?: 'pure_static' | 'const_fold' | 'requires_solver' | 'requires_simulation';
    emit_tier?:
        | 'static_pipeline'
        | 'lookup_api'
        | 'partial_static_pipeline'
        | 'verify_pipeline'
        | 'catalog_only';
    for_llm?: ForLlmSpec;
    suggested_fix?: SuggestedFixSpec;
    example_dsl?: string;
}

/**
 * Mapping ``code -> CodeSpec``.
 */
export type CodeRegistry = Record<string, CodeSpec>;

/**
 * Load the bundled diagnostic code registry.
 */
export function loadCodesRegistry(): CodeRegistry {
    return codesContents;
}
