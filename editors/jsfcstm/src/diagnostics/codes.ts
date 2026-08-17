/**
 * Public compatibility module for the diagnostic code registry.
 *
 * The implementation lives in ``codes-registry.ts`` because this directory
 * also contains the generated ``codes.json`` asset. Node's extensionless
 * resolution prefers that JSON file under ts-node, so internal consumers use
 * the collision-free module name. This re-export keeps the historical
 * ``dist/diagnostics/codes`` build path available to package consumers.
 */
export * from './codes-registry';
