import assert from 'node:assert/strict';

import {
    collectConstFoldWarnings,
    foldConditionExpression,
    foldNumericExpression,
} from '../src/diagnostics/analyzers/const-fold';
import {collectDesignHealthWarnings as collectDesignHealthWarningsFromIndex} from '../src/diagnostics/analyzers';
import {inspectModel} from '../src/diagnostics';
import {buildStateMachineModel} from '../src/model';
import {parseAstDocument} from '../src/ast';
import {createDocument} from './support';

async function buildMachine(src: string) {
    const document = createDocument(src, '/tmp/const-fold.fcstm');
    const ast = await parseAstDocument(document);
    const machine = buildStateMachineModel(ast);
    if (!machine) {
        throw new Error('buildStateMachineModel returned null');
    }
    return machine;
}

async function guardExpression(src: string) {
    const machine = await buildMachine(`
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B : if [${src}];
}
`);
    const transition = machine.allStates
        .flatMap(state => state.transitions)
        .find(item => item.guard);
    assert.ok(transition && transition.guard);
    return transition.guard;
}

async function assignmentExpression(src: string) {
    const machine = await buildMachine(`
def int x = 0;
state Root {
    state A {
        during { x = ${src}; }
    }
    [*] -> A;
}
`);
    const state = machine.allStates.find(item => item.path.join('.') === 'Root.A');
    assert.ok(state);
    const statement = state!.onDurings[0].operations[0];
    assert.ok(statement && 'expr' in statement);
    return (statement as {expr: unknown}).expr;
}

describe('diagnostics/const-fold', () => {
    it('folds numeric literal operators and unsupported cases', async () => {
        assert.equal(foldNumericExpression(await assignmentExpression('+5')), 5);
        assert.equal(foldNumericExpression(await assignmentExpression('-5')), -5);
        assert.equal(foldNumericExpression(await assignmentExpression('2 - 7')), -5);
        assert.equal(foldNumericExpression(await assignmentExpression('3 * 4')), 12);
        assert.equal(foldNumericExpression(await assignmentExpression('7 / 2')), 3.5);
        assert.equal(foldNumericExpression(await assignmentExpression('7 % 4')), 3);
        assert.equal(foldNumericExpression(await assignmentExpression('-7 % 4')), 1);
        assert.equal(foldNumericExpression(await assignmentExpression('2 ** 3')), 8);
        assert.equal(foldNumericExpression(await assignmentExpression('2.0 ** 3')), 8);
        assert.equal(foldNumericExpression(await assignmentExpression('2 ** 3.0')), 8);
        assert.equal(foldNumericExpression(await assignmentExpression('8 >> 1')), 4);
        assert.equal(foldNumericExpression(await assignmentExpression('5 ^ 3')), 6);
        assert.equal(foldNumericExpression(await assignmentExpression('0xFFFFFFFF & 0xFFFFFFFF')), 4294967295);
        assert.equal(foldNumericExpression(await assignmentExpression('(1 << 40) >> 8')), 4294967296);
        assert.equal(foldNumericExpression(await assignmentExpression('(1 > 0) ? 9 : 10')), 9);
        assert.equal(foldNumericExpression(await assignmentExpression('9007199254740991 + 1')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('2 ** 53')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('x + 1')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('1 / 0')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('1 << -1')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('1.0 & 1')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('(1.0 + 0) & 1')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('(2 / 2) & 1')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('1 << 2048')), null);
        assert.equal(foldNumericExpression(await assignmentExpression('0 ** -1')), null);
        assert.equal(foldNumericExpression({}), null);
    });

    it('folds boolean comparisons without unsafe integer precision loss', async () => {
        assert.equal(foldConditionExpression(await guardExpression('!false')), true);
        assert.equal(foldConditionExpression(await guardExpression('+1 == 1')), true);
        assert.equal(foldConditionExpression(await guardExpression('1 < 2')), true);
        assert.equal(foldConditionExpression(await guardExpression('1 <= 1')), true);
        assert.equal(foldConditionExpression(await guardExpression('2 > 1')), true);
        assert.equal(foldConditionExpression(await guardExpression('2 >= 2')), true);
        assert.equal(foldConditionExpression(await guardExpression('true == false')), false);
        assert.equal(foldConditionExpression(await guardExpression('true != false')), true);
        assert.equal(foldConditionExpression(await guardExpression('(1 > 0) ? false : true')), false);
        assert.equal(foldConditionExpression(await guardExpression('(0.1 + 0.2) == 0.3')), false);
        assert.equal(foldConditionExpression(await guardExpression('(0.1 + 0.2) != 0.3')), true);
        assert.equal(
            foldConditionExpression(await guardExpression('9007199254740993 == 9007199254740992')),
            false,
        );
        assert.equal(
            foldConditionExpression(await guardExpression('9007199254740993 > 9007199254740992')),
            true,
        );
        assert.equal(
            foldConditionExpression(await guardExpression('-9007199254740993 < -9007199254740992')),
            true,
        );
        assert.equal(foldConditionExpression(await guardExpression('(0xFFFFFFFF & 0xFFFFFFFF) == 4294967295')), true);
        assert.equal(foldConditionExpression(await guardExpression('(-7 % 4) == 1')), true);
        assert.equal(foldConditionExpression(await guardExpression('(1.0 & 1) == 1')), null);
        assert.equal(foldConditionExpression(await guardExpression('((1.0 + 0) & 1) == 1')), null);
        assert.equal(foldConditionExpression(await guardExpression('((2 / 2) & 1) == 1')), null);
        assert.equal(foldConditionExpression(await guardExpression('(1 << 2048) == 0')), null);
        assert.equal(
            foldConditionExpression(await guardExpression('(9007199254740992 + 1) == 9007199254740993')),
            null,
        );
        assert.equal(
            foldConditionExpression(await guardExpression('(2 ** 53) == 9007199254740992')),
            null,
        );
        assert.equal(foldConditionExpression(await guardExpression('1.0 < 9007199254740993')), null);
        assert.equal(foldConditionExpression(await guardExpression('9007199254740993 == 1.0')), null);
        assert.equal(foldConditionExpression(await guardExpression('sin(0) == 0')), null);
        assert.equal(foldConditionExpression(await guardExpression('x > 0')), null);
        assert.equal(foldConditionExpression({}), null);
    });

    it('collects warnings and skips nonordinary during actions', async () => {
        assert.deepEqual(collectConstFoldWarnings(null), []);
        const machine = await buildMachine(`
def int stable = 0;
def int dynamic = 0;
state Root {
    state Wrapper {
        during before { stable = 1; }
        >> during before { stable = 2; }
        state Idle {
            during { stable = (2 + 3) * 4; }
            during { dynamic = dynamic + 1; }
        }
        state Active;
        [*] -> Idle;
        Idle -> Active : if [(1 + 2) == 3];
        Active -> Idle : if [9007199254740993 == 9007199254740992];
    }
    [*] -> Wrapper;
}
`);
        const warnings = collectConstFoldWarnings(machine);
        assert.deepEqual(
            warnings.map(item => item.code).sort(),
            ['W_DURING_CONST_ASSIGN', 'W_GUARD_CONST_FALSE', 'W_GUARD_CONST_TRUE'],
        );
        assert.deepEqual(
            inspectModel(machine).diagnostics
                .filter(item => item.code.startsWith('W_GUARD_CONST') || item.code === 'W_DURING_CONST_ASSIGN')
                .map(item => item.code)
                .sort(),
            ['W_DURING_CONST_ASSIGN', 'W_GUARD_CONST_FALSE', 'W_GUARD_CONST_TRUE'],
        );
    });

    it('formats special transition endpoints as DSL markers in messages', async () => {
        const diagnostics = collectConstFoldWarnings(await buildMachine(`
state Root {
    state Idle;
    [*] -> Idle : if [true];
    Idle -> [*] : if [false];
}
`));
        const messages = diagnostics.map(item => item.message);
        assert.ok(messages.some(message => message.includes('"[*]" -> "Idle"')));
        assert.ok(messages.some(message => message.includes('"Idle" -> "[*]"')));
        assert.equal(messages.some(message => message.includes('INIT_STATE') || message.includes('EXIT_STATE')), false);
    });

    it('keeps minimal const-false fallback when design-health helper has no machine', () => {
        const diagnostics = collectDesignHealthWarningsFromIndex(
            [],
            [{
                from_path: 'Root.Idle',
                to_path: 'Root.Active',
                event: null,
                event_scope: null,
                guard: '1 == 2',
                effect: null,
                effect_self_assigns: [],
                is_forced: false,
                forced_origin: null,
            }],
            [],
            [],
            [],
            [],
            {
                n_states_leaf: 0,
                n_states_composite: 0,
                n_states_pseudo: 0,
                max_hierarchy_depth: 0,
                n_transitions_normal: 1,
                n_transitions_forced: 0,
                n_events: 0,
                n_variables: 0,
                var_to_leaf_ratio: 0,
                aspect_coverage: {},
                abstract_action_inventory: [],
            },
            {},
        );
        assert.deepEqual(diagnostics.map(item => item.code), ['W_GUARD_CONST_FALSE']);
    });
});
