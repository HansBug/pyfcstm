/**
 * Runtime accessor for the shared diagnostic codes registry.
 *
 * The canonical registry lives at ``pyfcstm/diagnostics/codes.yaml`` in
 * the repository root. The jsfcstm build script
 * (``scripts/sync-runtime-assets.js``) converts it to JSON and syncs
 * the result into ``src/diagnostics/codes.json`` before TypeScript
 * compilation. The JSON contents are inlined via ``require`` so
 * downstream bundlers ship the catalog inside a single bundle and the
 * published npm tarball needs no YAML dependency on the consumer side.
 */

// eslint-disable-next-line @typescript-eslint/no-var-requires
const rawCodesContents = require('./codes.json') as Record<string, RawCodeSpec>;

/** One field inside a diagnostic code's ``refs`` schema. */
export interface CodeFieldSpec {
    type: string;
    required?: boolean;
    description?: string;
    enum?: readonly string[];
    item_enum?: readonly string[];
    exact_values?: readonly string[];
}

/** Structured LLM-facing guidance attached to a diagnostic code. */
export interface ForLlmSpec {
    summary: string;
    recommended_actions: Array<Record<string, unknown>>;
    do_not: string[];
}

/** Structured auto-fix metadata declared by ``codes.yaml``. */
export interface SuggestedFixSpec {
    kind: 'insert' | 'delete' | 'replace';
    target: string;
    anchor_ref: string;
    text_template?: string;
    rationale: string;
}

/** Specification for a single diagnostic code as expressed in ``codes.yaml``. */
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
    deprecated_in?: string;
    removed_in?: string | null;
    replaced_by?: string;
}

interface RawCodeSpec extends CodeSpec {
    alias_of?: string;
}

/** Mapping ``code -> CodeSpec``. */
export type CodeRegistry = Record<string, CodeSpec>;

const severityPrefixes: Record<CodeSpec['severity'], string> = {
    error: 'E_',
    warning: 'W_',
    info: 'I_',
};

const aliasKeys = new Set(['alias_of', 'deprecated_in', 'removed_in']);

function requireVersion(value: unknown, code: string, field: string): string {
    // Python's packaging.Version in the source audit is the single version
    // syntax/order authority. JS only rejects absent metadata and preserves
    // the validated string; duplicating a partial PEP 440 parser here would
    // make the two runtimes disagree on otherwise valid release versions.
    if (typeof value !== 'string' || value.trim().length === 0) {
        throw new Error(`Diagnostic code alias ${code} has invalid ${field}`);
    }
    return value.trim();
}

function resolveCodesRegistry(raw: Record<string, RawCodeSpec>): CodeRegistry {
    const resolved: CodeRegistry = {};
    const resolving = new Set<string>();

    function resolve(code: string): CodeSpec {
        const existing = resolved[code];
        if (existing) return existing;
        const entry = raw[code];
        if (!entry) {
            throw new Error(`Diagnostic code alias target is not registered: ${code}`);
        }
        if (resolving.has(code)) {
            throw new Error(`Diagnostic code alias cycle detected at ${code}`);
        }
        resolving.add(code);
        if (entry.alias_of === undefined) {
            const active = {...entry};
            delete active.alias_of;
            resolved[code] = active;
            resolving.delete(code);
            return active;
        }
        for (const key of Object.keys(entry)) {
            if (!aliasKeys.has(key)) {
                throw new Error(`Diagnostic code alias ${code} has unsupported key ${key}`);
            }
        }
        if (typeof entry.alias_of !== 'string' || entry.alias_of.trim().length === 0) {
            throw new Error(`Diagnostic code alias ${code} must name a target`);
        }
        const deprecatedIn = requireVersion(entry.deprecated_in, code, 'deprecated_in');
        const removedIn = entry.removed_in === undefined || entry.removed_in === null
            ? undefined
            : requireVersion(entry.removed_in, code, 'removed_in');
        const aliasTarget = entry.alias_of.trim();
        const target = resolve(aliasTarget);
        if (target.replaced_by) {
            throw new Error(
                `Diagnostic code alias ${code} must point directly to an active code`,
            );
        }
        if (!target.severity || !code.startsWith(severityPrefixes[target.severity])) {
            throw new Error(
                `Diagnostic code alias ${code} does not match the target severity prefix`,
            );
        }
        const alias: CodeSpec = {
            ...target,
            emit_tier: 'catalog_only',
            deprecated_in: deprecatedIn,
            removed_in: removedIn,
            replaced_by: aliasTarget,
        };
        resolved[code] = alias;
        resolving.delete(code);
        return alias;
    }

    for (const code of Object.keys(raw)) resolve(code);
    return resolved;
}

const codesContents = resolveCodesRegistry(rawCodesContents);

/** Load the bundled diagnostic code registry. */
export function loadCodesRegistry(): CodeRegistry {
    return codesContents;
}

/** Return the registry entry for an active or deprecated code spelling. */
export function resolveDiagnosticCode(code: string): CodeSpec | undefined {
    return codesContents[code];
}

/** Return the active spelling for a known code, preserving unknown codes. */
export function canonicalizeDiagnosticCode(code: string): string {
    return codesContents[code]?.replaced_by ?? code;
}
