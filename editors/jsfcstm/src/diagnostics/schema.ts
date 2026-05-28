/**
 * Runtime accessor for the shared diagnostics JSON schema.
 *
 * The canonical schema lives at ``pyfcstm/diagnostics/schema.json`` in
 * the repository root. The jsfcstm build script
 * (``scripts/sync-runtime-assets.js``) syncs it into
 * ``src/diagnostics/schema.json`` before TypeScript compilation, so
 * the contents are inlined via ``resolveJsonModule`` and downstream
 * bundlers (e.g. esbuild used by the VSCode extension) ship the schema
 * inside a single bundle without needing the JSON file as a separate
 * VSIX asset.
 */

// eslint-disable-next-line @typescript-eslint/no-var-requires
const schemaContents = require('./schema.json') as Record<string, unknown>;

/**
 * Load the bundled inspect-model schema as a plain JavaScript object.
 */
export function loadInspectModelSchema(): Record<string, unknown> {
    return schemaContents;
}
