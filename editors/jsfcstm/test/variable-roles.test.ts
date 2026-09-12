import assert from 'node:assert/strict';
import {createDocument, packageModule} from './support';
import {collectSemanticAnalysisDiagnosticsFromSemantic} from '@pyfcstm/jsfcstm/editor';

const declarations = [
    ['def', 'control', ' = 1'], ['control', 'control', ' = 1'],
    ['input', 'input_dynamic', ''], ['input dynamic', 'input_dynamic', ''],
    ['param', 'input_static', ' = 1'], ['input static', 'input_static', ' = 1'],
    ['output', 'output', ' = 1'],
];

async function parse(text: string) {
    const document = createDocument(text, '/tmp/roles.fcstm');
    const ast = await packageModule.parseAstDocument(document);
    assert.ok(ast);
    return {document, ast};
}

describe('variable role DSL', () => {
    for (const [prefix, role, init] of declarations) {
        for (const type of ['int', 'float']) {
            it(`parses ${prefix} ${type} declarations with source documentation`, async () => {
                const {ast} = await parse(`/* measured value */\n${prefix} ${type} value${init}; state Root;`);
                assert.equal(ast.variables[0].role, role);
                assert.equal(ast.variables[0].spelling, prefix);
                assert.equal(ast.variables[0].initializer === null, role === 'input_dynamic');
                assert.equal(ast.variables[0].doc, 'measured value');
                assert.equal(ast.variables[0].range.start.character, 0);
            });
        }
    }
});

describe('variable role model', () => {
    for (const [prefix, role, init] of declarations) {
        it(`preserves ${prefix} in model AST exports`, async () => {
            const {ast} = await parse(`${prefix} int value${init}; state Root;`);
            const model = packageModule.buildStateMachineModel(ast)!;
            assert.ok(model);
            assert.equal(model.defines.value.role, role);
            assert.equal(model.defines.value.init === null, role === 'input_dynamic');
            const exported = model.to_ast_node();
            assert.equal(exported.variables[0].spelling, prefix);
            assert.equal(packageModule.buildStateMachineModel(exported)!.defines.value.role, role);
        });
    }
    it('exposes immutable partitions in global declaration order', async () => {
        const {ast} = await parse('output int first = 0; input int sensor; def int count = 1; param int limit = 2; output int last = 0; state Root;');
        const model = packageModule.buildStateMachineModel(ast)!;
        for (const [partition, names] of [
            [model.control_variables, ['count']], [model.dynamic_inputs, ['sensor']],
            [model.static_inputs, ['limit']], [model.output_variables, ['first', 'last']],
            [model.persistent_variables, ['first', 'count', 'last']],
        ] as const) {
            assert.deepEqual(Object.keys(partition), names);
            assert.ok(Object.isFrozen(partition));
            for (const name of names) assert.equal(partition[name], model.defines[name]);
            assert.throws(() => { (partition as Record<string, unknown>).extra = model.defines.count; }, TypeError);
        }
    });
});

describe('variable role diagnostics', () => {
    for (const prefix of ['input', 'input dynamic', 'param', 'input static']) {
        for (const body of [
            'state Root { enter { value = 1; } }',
            'state Root { exit { value = 1; } }',
            'state Root { during { if [True] {} else { value = 1; } } }',
            'state Root { during { if [True] {} else if [False] { value = 1; } } }',
            'state Root { >> during before { value = 1; } state A; [*] -> A; }',
            'state Root { >> during after { value = 1; } state A; [*] -> A; }',
            'state Root { state A { enter { value = 1; } } [*] -> A; }',
            'state Root { state A; state B; [*] -> A; A -> B effect { value = 1; } }',
            'state Root { state A; [*] -> A; A -> [*] effect { value = 1; } }',
            'state Root { enter Set { value = 1; } exit ref Set; }',
        ]) {
            it(`rejects a write to ${prefix} in ${body}`, async () => {
                const isStatic = prefix === 'param' || prefix === 'input static';
                const {document, ast} = await parse(`${prefix} int value${isStatic ? ' = 0' : ''}; ${body}`);
                assert.equal(packageModule.buildStateMachineModel(ast), null);
                const diagnostics = collectSemanticAnalysisDiagnosticsFromSemantic(packageModule.buildSemanticDocument(ast)!, document);
                assert.ok(diagnostics.some(item => item.code === (isStatic ? 'E_STATIC_INPUT_WRITE' : 'E_DYNAMIC_INPUT_WRITE')));
            });
        }
    }
    for (const [declaration, body, code] of [
        ['input int value = 1;', 'state Root;', 'E_DYNAMIC_INPUT_INITIALIZER'],
        ['param int value;', 'state Root;', 'E_VARIABLE_INITIALIZER_REQUIRED'],
        ['input int value;', 'state Root { during { value = 1; } }', 'E_DYNAMIC_INPUT_WRITE'],
        ['param int value = 1;', 'state Root { during { if [True] { value = 2; } else { value = 3; } } }', 'E_STATIC_INPUT_WRITE'],
        ['input int value;', 'state Root { state A; [*] -> A effect { value = 1; } }', 'E_DYNAMIC_INPUT_WRITE'],
    ]) {
        it(`rejects ${code} before model construction`, async () => {
            const {document, ast} = await parse(declaration + body);
            assert.equal(packageModule.buildStateMachineModel(ast), null);
            const semantic = packageModule.buildSemanticDocument(ast)!;
            const diagnostics = collectSemanticAnalysisDiagnosticsFromSemantic(semantic, document);
            assert.ok(diagnostics.some(item => item.code === code && item.data?.var_name === 'value'));
        });
    }
    it('publishes roles without false dead-variable warnings for external interfaces', async () => {
        const {ast} = await parse('input int sensor; param int limit = 2; output int command = 0; def int count = 0; state Root { state A; state B; [*] -> A; A -> B : if [sensor > limit] effect { command = 1; } }');
        const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
        assert.deepEqual(report.variables.map(variable => variable.role), ['input_dynamic', 'input_static', 'output', 'control']);
        assert.equal(report.variables[0].init_value, '');
        assert.ok(report.diagnostics.some(item => item.code === 'W_UNREFERENCED_VAR' && item.refs.var_name === 'count'));
        assert.ok(!report.diagnostics.some(item => item.code === 'W_GUARD_VARS_NEVER_CHANGE'));
        assert.ok(!report.diagnostics.some(item => ['W_UNREFERENCED_VAR', 'W_UNWRITTEN_READ_VAR', 'W_WRITE_ONLY_VAR'].includes(item.code) && item.refs.var_name !== 'count'));
    });
});

describe('programmatic variable declarations', () => {
    it('defaults optional legacy role metadata to control at every model boundary', async () => {
        const {ast} = await parse('def int value = 1; state Root;');
        const {role, ...legacyDefinition} = ast.variables[0];
        const legacyAst = {...ast, variables: [legacyDefinition], definitions: [legacyDefinition]};
        assert.equal(packageModule.buildSemanticDocument(legacyAst)!.variables[0].role, 'control');
        const model = packageModule.buildStateMachineModel(legacyAst)!;
        assert.equal(model.defines.value.role, 'control');
        const {role: exportedRole, ...rawDefinition} = model.defines.value;
        const definition = packageModule.hydrateStateMachine({
            ...model, defines: {value: rawDefinition},
        } as any).defines.value;
        assert.equal(definition.role, 'control');
    });
    for (const expression of [
        'other', '-other', 'other + 1', '1 + other', 'sin(other)', '(other)',
        '(other > 0) ? 1 : 0', '(1 > 0) ? other : 0', '(1 > 0) ? 1 : other',
        '(1 > 0) ? 1 : 0',
    ]) {
        it(`validates references in a public AST initializer: ${expression}`, async () => {
            const {document, ast} = await parse(`def int value = 0; def int other = 1; state Root { enter { value = ${expression}; } }`);
            const assignment = ast.rootState!.enters[0].operations![0];
            assert.equal(assignment.kind, 'assignmentStatement');
            if (assignment.kind !== 'assignmentStatement') throw new Error('expected assignment');
            const definition = {...ast.variables[0], initializer: assignment.expression, expr: assignment.expression};
            const input = {...ast, variables: [definition, ast.variables[1]], definitions: [definition, ast.variables[1]]};
            const diagnostics = collectSemanticAnalysisDiagnosticsFromSemantic(packageModule.buildSemanticDocument(input)!, document);
            assert.equal(diagnostics.some(item => item.code === 'E_INITIALIZER_VARIABLE_REFERENCE'), expression.includes('other'));
            assert.equal(packageModule.buildStateMachineModel(input) === null, expression.includes('other'));
        });
    }
    it('renders dynamic declarations without an initializer in diagrams', async () => {
        const diagram = await packageModule.buildFcstmDiagramFromDocument(createDocument('input int sensor; state Root;', '/tmp/input-diagram.fcstm'));
        assert.ok(diagram);
        assert.equal(diagram!.variables[0].initializer, '');
    });
});

describe('reserved variable role keywords', () => {
    for (const keyword of ['control', 'input', 'dynamic', 'static', 'param', 'output']) {
        it(`rejects ${keyword} as a variable, state, event, or action name`, async () => {
            for (const source of [
                `def int ${keyword} = 0; state Root;`, `state ${keyword};`,
                `state Root { event ${keyword}; }`, `state Root { enter ${keyword} {} }`,
            ]) {
                assert.equal((await packageModule.getParser().parse(source)).success, false);
            }
        });
    }
    for (const modifier of ['dynamic', 'static']) {
        for (const gap of [' ', '\t', '\n', ' // sample\n', ' # sample\n']) {
            it(`parses input ${modifier} separated by ${JSON.stringify(gap)}`, async () => {
                const {ast} = await parse(`input${gap}${modifier} int value${modifier === 'static' ? ' = 1' : ''}; state Root;`);
                assert.equal(ast.variables[0].spelling, `input ${modifier}`);
            });
        }
    }
});

describe('guard change advice for external interfaces', () => {
    for (const [declaration, expected] of [
        ['input int setting;', false], ['param int setting = 1;', false],
        ['output int setting = 1;', false], ['def int setting = 1;', true],
    ] as const) {
        it(`analyzes ${declaration} according to ownership`, async () => {
            const {ast} = await parse(`${declaration} state Root {state A;state B;[*] -> A; A -> B : if [setting > 0];}`);
            const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
            assert.equal(report.diagnostics.some(d => d.code === 'W_GUARD_VARS_NEVER_CHANGE'), expected);
        });
    }
});
