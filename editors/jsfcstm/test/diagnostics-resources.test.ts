import assert from 'node:assert/strict';

import {packageModule} from './support';

const {loadCodesRegistry, loadInspectModelSchema} = packageModule;

const numericCodes = [
    'W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE',
    'W_NUMERIC_CONSTANT_DIVISION_BY_ZERO',
    'W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE',
    'W_NUMERIC_FLOAT_BITWISE',
] as const;

const cFamilyTargetTemplates = ['c', 'c_poll', 'cpp', 'cpp_poll'];
const numericContexts = ['var_initializer', 'guard', 'transition_effect', 'lifecycle_action'];

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

        it('contains threshold, info, naming, and type diagnostic catalog entries', () => {
            const registry = loadCodesRegistry();
            for (const code of [
                'W_NAMED_ACTION_SHADOWS_ANCESTOR',
                'W_LITERAL_TYPE_NARROWING',
                'W_ASPECT_NO_DESCENDANT_LEAF',
                'W_HIGH_VAR_TO_LEAF_RATIO',
                'W_DEEP_HIERARCHY',
                'W_LARGE_COMPOSITE',
                'I_TRANSITION_TO_SELF_VIA_PARENT',
                'I_TRANSITION_NEVER_EVENT_TRIGGERED',
            ]) {
                assert.ok(registry[code], `${code} missing from bundled codes registry`);
            }
        });

        it('contains C/C++ numeric catalog-only diagnostics', () => {
            const registry = loadCodesRegistry();
            for (const code of numericCodes) {
                const spec = registry[code];
                assert.ok(spec, `${code} missing from bundled codes registry`);
                assert.equal(spec.severity, 'warning', `${code} must stay warning-level`);
                assert.equal(spec.emit_tier, 'catalog_only', `${code} must not emit before analyzers land`);
                assert.equal(spec.span_object, 'expression', `${code} must identify an expression`);
                assert.ok(spec.example_dsl, `${code} must keep a parseable example DSL contract`);
                assert.ok(spec.for_llm, `${code} must keep LLM-facing guidance`);
            }
        });

        it('locks numeric target-profile refs fields', () => {
            const registry = loadCodesRegistry();
            for (const code of numericCodes) {
                const refs = registry[code].refs ?? {};
                for (const field of ['target_family', 'target_templates', 'runtime_note', 'context', 'expr_text']) {
                    assert.ok(refs[field], `${code} refs missing ${field}`);
                    assert.equal(refs[field].required, true, `${code}.${field} must be required`);
                }
                assert.deepEqual(refs.target_family.enum, ['c_family']);
                assert.equal(refs.target_templates.type, 'list[str]');
                assert.deepEqual(refs.context.enum, numericContexts);
            }
        });

        it('locks numeric rule-specific refs fields', () => {
            const registry = loadCodesRegistry();

            const literalRefs = registry.W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE.refs ?? {};
            for (const field of ['literal_text', 'target_bits', 'signed', 'min_value_text', 'max_value_text']) {
                assert.equal(literalRefs[field]?.required, true, `literal range refs missing required ${field}`);
            }

            const divRefs = registry.W_NUMERIC_CONSTANT_DIVISION_BY_ZERO.refs ?? {};
            assert.equal(divRefs.operator?.required, true);
            assert.deepEqual(divRefs.operator?.enum, ['/', '%']);
            assert.equal(divRefs.rhs_text?.required, true);

            const shiftRefs = registry.W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE.refs ?? {};
            assert.equal(shiftRefs.operator?.required, true);
            assert.deepEqual(shiftRefs.operator?.enum, ['<<', '>>']);
            assert.equal(shiftRefs.target_bits?.required, true);
            assert.equal(shiftRefs.shift_count_text?.required, true);

            const bitwiseRefs = registry.W_NUMERIC_FLOAT_BITWISE.refs ?? {};
            assert.equal(bitwiseRefs.operator?.required, true);
            assert.deepEqual(bitwiseRefs.operator?.enum, ['&', '^', '|', '<<', '>>']);
            assert.equal(bitwiseRefs.operand_types?.required, true);
            assert.equal(bitwiseRefs.operand_type_sources?.required, true);
            assert.deepEqual(bitwiseRefs.statement_kind?.enum, ['operation_assignment']);
        });

        it('does not predeclare deferred verify-guidance numeric codes', () => {
            const registry = loadCodesRegistry();
            assert.equal(registry.W_NUMERIC_SHIFT_REQUIRES_PROOF, undefined);
            assert.equal(registry.I_NUMERIC_VERIFY_RECOMMENDED, undefined);
            assert.deepEqual(cFamilyTargetTemplates, ['c', 'c_poll', 'cpp', 'cpp_poll']);
        });
    });
});
