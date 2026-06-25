import assert from 'node:assert/strict';

import {
    collectNumericWarnings,
} from '../src/diagnostics/analyzers/numeric';
import {
    inspectModel,
    refsWithSuggestedFix,
    type ModelDiagnosticJson,
} from '../src/diagnostics';
import {buildStateMachineModel} from '../src/model';
import {parseAstDocument} from '../src/ast';
import {createDocument, packageModule} from './support';

const MIN_SIGNED_INT64_TEXT = '-9223372036854775808';
const MAX_SIGNED_INT64_TEXT = '9223372036854775807';
const TOO_LARGE_SIGNED_INT64_TEXT = '9223372036854775808';
const TOO_SMALL_SIGNED_INT64_TEXT = '-9223372036854775809';

const NUMERIC_CODES = new Set([
    'W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE',
    'W_NUMERIC_CONSTANT_DIVISION_BY_ZERO',
    'W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE',
    'W_NUMERIC_FLOAT_BITWISE',
]);

const C_FAMILY_TARGET_TEMPLATES = ['c', 'c_poll', 'cpp', 'cpp_poll'];

async function buildMachine(src: string) {
    const document = createDocument(src, '/tmp/diagnostics-numeric.fcstm');
    const ast = await parseAstDocument(document);
    const machine = buildStateMachineModel(ast);
    if (!machine) {
        throw new Error('buildStateMachineModel returned null');
    }
    return machine;
}

async function numericDiagnostics(source: string): Promise<ModelDiagnosticJson[]> {
    const report = inspectModel(await buildMachine(source));
    return report.diagnostics.filter(item => NUMERIC_CODES.has(item.code));
}

function diagnosticsFor(diagnostics: ModelDiagnosticJson[], code: string): ModelDiagnosticJson[] {
    return diagnostics.filter(item => item.code === code);
}

function assertRegistryRefs(diagnostic: ModelDiagnosticJson): void {
    const registry = packageModule.loadCodesRegistry();
    const spec = registry[diagnostic.code];
    assert.ok(spec, `${diagnostic.code} missing from bundled registry`);
    assert.equal(diagnostic.severity, spec.severity);
    const refsSpec = spec.refs ?? {};
    for (const [fieldName, fieldSpec] of Object.entries(refsSpec)) {
        if (fieldSpec.required) {
            assert.ok(
                Object.prototype.hasOwnProperty.call(diagnostic.refs, fieldName),
                `${diagnostic.code} refs missing required ${fieldName}`,
            );
        }
        const value = diagnostic.refs[fieldName];
        if (value === undefined) continue;
        if (fieldSpec.enum) {
            assert.equal(typeof value, 'string', `${diagnostic.code}.${fieldName} must be a string enum`);
            assert.ok(fieldSpec.enum.includes(value), `${diagnostic.code}.${fieldName} has invalid enum value ${value}`);
        }
        if (fieldSpec.item_enum || fieldSpec.exact_values) {
            assert.ok(Array.isArray(value), `${diagnostic.code}.${fieldName} must be an array`);
        }
        if (fieldSpec.item_enum && Array.isArray(value)) {
            for (const item of value) {
                assert.equal(typeof item, 'string', `${diagnostic.code}.${fieldName} item must be a string`);
                assert.ok(fieldSpec.item_enum.includes(item), `${diagnostic.code}.${fieldName} invalid item ${item}`);
            }
        }
        if (fieldSpec.exact_values) {
            assert.deepEqual(value, fieldSpec.exact_values, `${diagnostic.code}.${fieldName} exact values drifted`);
        }
    }

    const refsWithoutSuggestedFix = {...diagnostic.refs};
    delete refsWithoutSuggestedFix.suggested_fix;
    assert.deepEqual(
        diagnostic.refs,
        refsWithSuggestedFix(diagnostic.code, refsWithoutSuggestedFix),
        `${diagnostic.code} bypassed refsWithSuggestedFix() normalization`,
    );
}

function assertTargetProfileRefs(diagnostic: ModelDiagnosticJson): void {
    assertRegistryRefs(diagnostic);
    assert.equal(diagnostic.refs.target_family, 'c_family');
    assert.deepEqual(diagnostic.refs.target_templates, C_FAMILY_TARGET_TEMPLATES);
    assert.equal(String(diagnostic.message).includes('C/C++'), true);
    assert.equal(String(diagnostic.message).includes('Python'), true);
    assert.equal(String(diagnostic.refs.runtime_note).includes('C/C++'), true);
    assert.equal(String(diagnostic.refs.runtime_note).includes('Python'), true);
}

describe('diagnostics/numeric', () => {
    it('keeps nullable analyzer entry as a no-op', () => {
        assert.deepEqual(collectNumericWarnings(null), []);
        assert.deepEqual(collectNumericWarnings(undefined), []);
    });

    it('reports signed int64 literal range boundaries for C-family templates', async () => {
        for (const [literalText, shouldWarn] of [
            [TOO_LARGE_SIGNED_INT64_TEXT, true],
            [`+${TOO_LARGE_SIGNED_INT64_TEXT}`, true],
            [MIN_SIGNED_INT64_TEXT, false],
            [MAX_SIGNED_INT64_TEXT, false],
            [TOO_SMALL_SIGNED_INT64_TEXT, true],
        ] as const) {
            const diagnostics = diagnosticsFor(await numericDiagnostics(`
def int value = ${literalText};
state Root { state A; [*] -> A; }
`), 'W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE');

            if (!shouldWarn) {
                assert.deepEqual(diagnostics, [], literalText);
                continue;
            }

            assert.equal(diagnostics.length, 1, literalText);
            const diagnostic = diagnostics[0];
            assertTargetProfileRefs(diagnostic);
            assert.equal(diagnostic.refs.context, 'var_initializer');
            assert.equal(diagnostic.refs.var_name, 'value');
            assert.equal(diagnostic.refs.literal_text, literalText);
            assert.equal(diagnostic.refs.min_value_text, MIN_SIGNED_INT64_TEXT);
            assert.equal(diagnostic.refs.max_value_text, MAX_SIGNED_INT64_TEXT);
            assert.equal(diagnostic.refs.target_bits, 64);
            assert.equal(diagnostic.refs.signed, true);
        }
    });

    it('uses RHS-only constant folding for division and modulo by zero', async () => {
        const diagnostics = diagnosticsFor(await numericDiagnostics(`
def int result = 0;
def int input = 1;
def int denom = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B effect {
        result = input / (1 - 1);
        result = input % (2 - 2);
        result = input / denom;
    };
}
`), 'W_NUMERIC_CONSTANT_DIVISION_BY_ZERO');

        assert.deepEqual(
            diagnostics.map(item => [item.refs.operator, item.refs.rhs_text]),
            [['/', '1 - 1'], ['%', '2 - 2']],
        );
        for (const diagnostic of diagnostics) {
            assertTargetProfileRefs(diagnostic);
            assert.equal(diagnostic.refs.context, 'transition_effect');
            assert.equal(diagnostic.refs.statement_kind, 'operation_assignment');
        }
    });

    it('reports only constant shift counts outside the 64-bit C-family profile', async () => {
        const diagnostics = diagnosticsFor(await numericDiagnostics(`
def int flags = 1;
def int amount = 64;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B effect {
        flags = flags << -1;
        flags = flags >> 64;
        flags = flags << 0;
        flags = flags << 63;
        flags = flags << amount;
    };
}
`), 'W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE');

        assert.deepEqual(
            diagnostics.map(item => [item.refs.operator, item.refs.shift_count_text]),
            [['<<', '-1'], ['>>', '64']],
        );
        for (const diagnostic of diagnostics) {
            assertTargetProfileRefs(diagnostic);
            assert.equal(diagnostic.refs.target_bits, 64);
            assert.equal(diagnostic.refs.context, 'transition_effect');
            assert.equal(diagnostic.refs.statement_kind, 'operation_assignment');
        }
    });

    it('reports float-shaped operands in C-family bitwise and shift expressions', async () => {
        for (const [expr, expectedTypes, expectedSources] of [
            ['1.5 & flags', ['float', 'int'], ['literal', 'declared_var']],
            ['gain | flags', ['float', 'int'], ['declared_var', 'declared_var']],
            ['(gain + 1.0) ^ flags', ['float', 'int'], ['local_expression', 'declared_var']],
            ['(1 / 2) & flags', ['float', 'int'], ['local_expression', 'declared_var']],
            ['sin(1) & flags', ['float', 'int'], ['local_expression', 'declared_var']],
            ['abs(gain) & flags', ['float', 'int'], ['local_expression', 'declared_var']],
            ['((flags > 0) ? 1.0 : 0) & flags', ['float', 'int'], ['local_expression', 'declared_var']],
        ] as const) {
            const diagnostics = diagnosticsFor(await numericDiagnostics(`
def int flags = 1;
def float gain = 1.5;
state Root {
    state A { during { flags = ${expr}; } }
    [*] -> A;
}
`), 'W_NUMERIC_FLOAT_BITWISE');

            assert.equal(diagnostics.length, 1, expr);
            const diagnostic = diagnostics[0];
            assertTargetProfileRefs(diagnostic);
            assert.equal(diagnostic.refs.operator, expr.includes('<<') ? '<<' : expr.match(/[&^|]/)![0]);
            assert.deepEqual(diagnostic.refs.operand_types, expectedTypes, expr);
            assert.deepEqual(diagnostic.refs.operand_type_sources, expectedSources, expr);
        }
    });

    it('does not report int-shaped local expressions as float bitwise risks', async () => {
        const diagnostics = diagnosticsFor(await numericDiagnostics(`
def int flags = 1;
state Root {
    state A {
        during {
            flags = (1 + 2) & flags;
            flags = sign(1.5) & flags;
            flags = ceil(1.5) & flags;
        }
    }
    [*] -> A;
}
`), 'W_NUMERIC_FLOAT_BITWISE');

        assert.deepEqual(diagnostics, []);
    });

    it('allows float shift expressions to overlap with shift-count warnings', async () => {
        const diagnostics = await numericDiagnostics(`
def int flags = 1;
def float gain = 1.5;
state Root {
    state A { during { flags = gain << 64; } }
    [*] -> A;
}
`);

        assert.equal(diagnosticsFor(diagnostics, 'W_NUMERIC_FLOAT_BITWISE').length, 1);
        assert.equal(diagnosticsFor(diagnostics, 'W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE').length, 1);
    });

    it('scans public expression contexts, if conditions, and nested assignments', async () => {
        const diagnostics = await numericDiagnostics(`
def int initialized = 1 / 0;
def int flags = 1;
state Root {
    state A {
        during {
            if [flags / 0 > 0] {
                if [flags > 0] {
                    flags = flags << 64;
                }
            }
        }
    }
    state B;
    [*] -> A;
    A -> B : if [flags / 0 > 0];
    B -> A effect { flags = flags / 0; };
}
`);

        const divisionContexts = diagnosticsFor(diagnostics, 'W_NUMERIC_CONSTANT_DIVISION_BY_ZERO')
            .map(item => [item.refs.context, item.refs.statement_kind ?? null]);
        assert.deepEqual(divisionContexts, [
            ['var_initializer', null],
            ['guard', null],
            ['transition_effect', 'operation_assignment'],
            ['lifecycle_action', null],
        ]);

        const shiftDiagnostics = diagnosticsFor(diagnostics, 'W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE');
        assert.equal(shiftDiagnostics.length, 1);
        assert.equal(shiftDiagnostics[0].refs.context, 'lifecycle_action');
        assert.equal(shiftDiagnostics[0].refs.statement_kind, 'operation_assignment');
    });

    it('does not duplicate diagnostics through abstract or ref lifecycle actions', async () => {
        const diagnostics = diagnosticsFor(await numericDiagnostics(`
def int value = 1;
state Root {
    state A {
        enter abstract HardwareInit;
        enter Inline { value = value / 0; }
        enter ref Inline;
    }
    [*] -> A;
}
`), 'W_NUMERIC_CONSTANT_DIVISION_BY_ZERO');

        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].refs.context, 'lifecycle_action');
        assert.equal(diagnostics[0].refs.statement_kind, 'operation_assignment');
    });
});
