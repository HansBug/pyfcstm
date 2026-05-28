import assert from 'node:assert/strict';

import {packageModule} from './support';

const {loadCodesRegistry, loadInspectModelSchema} = packageModule;

describe('diagnostics resources (PR-A)', () => {
    describe('schema.json bundled', () => {
        it('loads as a valid JSON schema document', () => {
            const schema = loadInspectModelSchema();
            assert.equal(schema.title, 'ModelInspect');
            assert.equal((schema as {$schema?: string}).$schema, 'https://json-schema.org/draft-07/schema#');
        });

        it('required keys cover the contract surface', () => {
            const schema = loadInspectModelSchema() as {required: string[]};
            const required = new Set(schema.required);
            for (const key of [
                'root_state_path',
                'states',
                'transitions',
                'variables',
                'events',
                'metrics',
                'reachability_graph',
                'event_emission_map',
                'var_dataflow',
                'aspect_impact_map',
                'action_ref_graph',
                'diagnostics',
            ]) {
                assert.ok(required.has(key), `schema.required missing ${key}`);
            }
        });
    });

    describe('codes.json bundled', () => {
        it('loads with at least the 14 Layer 1 E_* codes', () => {
            const registry = loadCodesRegistry();
            const errorCodes = Object.keys(registry).filter(k => k.startsWith('E_'));
            assert.ok(errorCodes.length >= 14, `expected >= 14 E_* codes, got ${errorCodes.length}`);
        });

        it('every entry declares severity and description', () => {
            const registry = loadCodesRegistry();
            for (const [code, spec] of Object.entries(registry)) {
                assert.ok(['error', 'warning', 'info'].includes(spec.severity), `${code} severity invalid: ${spec.severity}`);
                assert.ok(typeof spec.description === 'string' && spec.description.length > 0, `${code} missing description`);
            }
        });

        it('E_*/W_*/I_* prefix matches declared severity', () => {
            const registry = loadCodesRegistry();
            for (const [code, spec] of Object.entries(registry)) {
                if (spec.severity === 'error') {
                    assert.ok(code.startsWith('E_'), `${code} severity error must start with E_`);
                } else if (spec.severity === 'warning') {
                    assert.ok(code.startsWith('W_'), `${code} severity warning must start with W_`);
                } else if (spec.severity === 'info') {
                    assert.ok(code.startsWith('I_'), `${code} severity info must start with I_`);
                }
            }
        });
    });
});
