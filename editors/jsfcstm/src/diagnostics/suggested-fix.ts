import type {CodeRegistry} from './codes';

// Import the JSON payload directly. In ts-node source tests, resolving
// ``./codes`` prefers ``codes.json`` over ``codes.ts``; using the explicit
// filename keeps source and built-package execution aligned.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const codesContents = require('./codes.json') as CodeRegistry;

export interface SuggestedFixPayload {
    kind: 'insert' | 'delete' | 'replace';
    target: string;
    anchor: {
        type: 'ref';
        ref: string;
    };
    text: string;
    rationale: string;
}

function lastPathSegment(value: unknown): string | undefined {
    if (typeof value !== 'string') return undefined;
    const parts = value.split('.');
    return parts[parts.length - 1];
}

function templateFieldNames(template: string): string[] {
    const out: string[] = [];
    const pattern = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;
    let match = pattern.exec(template);
    while (match !== null) {
        out.push(match[1]);
        match = pattern.exec(template);
    }
    return out;
}

function formatTemplate(template: string, values: Record<string, unknown>): string | null {
    for (const field of templateFieldNames(template)) {
        if (values[field] === undefined || values[field] === null) {
            return null;
        }
    }
    return template.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, field: string) => String(values[field]));
}

/**
 * Render a ``codes.yaml`` suggested-fix template for one diagnostic emit.
 */
export function renderSuggestedFix(
    code: string,
    refs: Record<string, unknown>,
): SuggestedFixPayload | null {
    const spec = codesContents[code];
    const suggested = spec?.suggested_fix;
    if (!suggested) return null;
    if (!suggested.anchor_ref.startsWith('refs.')) return null;
    const anchorField = suggested.anchor_ref.slice('refs.'.length);
    if (refs[anchorField] === undefined || refs[anchorField] === null) return null;

    const values: Record<string, unknown> = {...refs};
    const stateName = lastPathSegment(values.state_path);
    if (stateName !== undefined && values.state_name === undefined) {
        values.state_name = stateName;
    }
    const compositeName = lastPathSegment(values.composite_path);
    if (compositeName !== undefined && values.composite_name === undefined) {
        values.composite_name = compositeName;
    }

    const text = formatTemplate(suggested.text_template ?? '', values);
    if (text === null) return null;
    return {
        kind: suggested.kind,
        target: suggested.target,
        anchor: {
            type: 'ref',
            ref: suggested.anchor_ref,
        },
        text,
        rationale: suggested.rationale,
    };
}

/**
 * Copy ``refs`` and attach ``suggested_fix`` when code metadata can be
 * rendered safely for the current payload.
 */
export function refsWithSuggestedFix(
    code: string,
    refs: Record<string, unknown>,
): Record<string, unknown> {
    const out: Record<string, unknown> = {...refs};
    const fix = renderSuggestedFix(code, out);
    if (fix) {
        out.suggested_fix = fix;
    }
    return out;
}
