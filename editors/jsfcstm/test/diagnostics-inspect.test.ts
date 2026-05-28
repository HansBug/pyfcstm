import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

const {inspectModel} = packageModule;

const SIMPLE_DSL = `
def int counter = 0;
def float temp = 25.0;
state Root {
    state Idle;
    state Active { during { counter = counter + 1; } }
    [*] -> Idle;
    Idle -> Active : if [counter > 0];
    Active -> Idle :: Pause;
}
`;

const COMPOSITE_DSL = `
def int x = 0;
state Outer {
    state Inner {
        state A;
        state B;
        [*] -> A;
        A -> B :: Go;
    }
    state Sibling;
    [*] -> Inner;
    Inner -> Sibling :: Done;
    >> during before { x = x + 1; }
}
`;

async function buildMachine(src: string) {
    const document = createDocument(src, '/tmp/inspect.fcstm');
    const ast = await packageModule.parseAstDocument(document);
    const machine = packageModule.buildStateMachineModel(ast);
    if (!machine) {
        throw new Error('buildStateMachineModel returned null');
    }
    return machine;
}

describe('diagnostics/inspect (PR-A)', () => {
    describe('basic structure', () => {
        it('returns top-level shape', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.equal(report.root_state_path, 'Root');
            assert.equal(report.states.length, 3);
            assert.equal(report.transitions.length, 3);
            assert.equal(report.variables.length, 2);
            assert.equal(report.events.length, 1);
        });

        it('flags composite vs leaf states', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const byPath: Record<string, typeof report.states[number]> = {};
            for (const s of report.states) byPath[s.path] = s;
            assert.equal(byPath['Root'].is_composite, true);
            assert.equal(byPath['Root'].is_leaf, false);
            assert.equal(byPath['Root.Idle'].is_leaf, true);
            assert.equal(byPath['Root.Active'].is_leaf, true);
        });

        it('captures initial targets with unconditional flag', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const root = report.states.find(s => s.path === 'Root');
            assert.ok(root);
            assert.equal(root!.initial_targets.length, 1);
            const target = root!.initial_targets[0];
            assert.equal(target.target, 'Root.Idle');
            assert.equal(target.guard, null);
            assert.equal(target.event, null);
            assert.equal(target.is_unconditional, true);
        });

        it('flags initial transitions with [*] from_path marker', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const inits = report.transitions.filter(t => t.from_path === '[*]');
            assert.equal(inits.length, 1);
            assert.equal(inits[0].to_path, 'Root.Idle');
        });

        it('captures transition guards as text', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const guarded = report.transitions.filter(t => t.guard !== null);
            assert.equal(guarded.length, 1);
            assert.ok(guarded[0].guard && guarded[0].guard.includes('counter'));
        });

        it('captures qualified event names with local scope', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const withEvent = report.transitions.filter(t => t.event !== null);
            assert.equal(withEvent.length, 1);
            assert.equal(withEvent[0].event, 'Root.Active.Pause');
            assert.equal(withEvent[0].event_scope, 'local');
        });

        it('populates variable info with init and reads/writes', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const counter = report.variables.find(v => v.name === 'counter');
            assert.ok(counter);
            assert.equal(counter!.type, 'int');
            assert.equal(counter!.init_value, '0');
            assert.ok(counter!.read_in_states.includes('Root.Active'));
            assert.ok(counter!.written_in_states.includes('Root.Active'));
            assert.ok(counter!.read_in_guards.some(p => p[0] === 'Root.Idle'));

            const temp = report.variables.find(v => v.name === 'temp');
            assert.ok(temp);
            assert.equal(temp!.read_in_states.length, 0);
            assert.equal(temp!.written_in_states.length, 0);
            assert.equal(temp!.participates_directly, false);
        });
    });

    describe('aggregate metrics', () => {
        it('counts leaves, composites, transitions, vars, events', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const m = report.metrics;
            assert.equal(m.n_states_leaf, 2);
            assert.equal(m.n_states_composite, 1);
            assert.equal(m.n_states_pseudo, 0);
            assert.equal(m.n_transitions_normal, 3);
            assert.equal(m.n_transitions_forced, 0);
            assert.equal(m.n_events, 1);
            assert.equal(m.n_variables, 2);
            assert.equal(m.var_to_leaf_ratio, 1.0);
            assert.equal(m.max_hierarchy_depth, 1);
        });
    });

    describe('view graphs', () => {
        it('reachability graph keyed by every state path', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const expected = report.states.map(s => s.path).sort();
            const actual = Object.keys(report.reachability_graph).sort();
            assert.deepEqual(actual, expected);
        });

        it('reachability captures Idle <-> Active', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.ok(report.reachability_graph['Root.Idle'].includes('Root.Active'));
            assert.ok(report.reachability_graph['Root.Active'].includes('Root.Idle'));
        });

        it('event emission map lists source states', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.deepEqual(report.event_emission_map, {
                'Root.Active.Pause': ['Root.Active'],
            });
        });

        it('var dataflow populated per variable', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.deepEqual(report.var_dataflow['counter'], {
                reads: ['Root.Active'],
                writes: ['Root.Active'],
            });
            assert.deepEqual(report.var_dataflow['temp'], {reads: [], writes: []});
        });

        it('aspect impact empty when no aspect actions', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.deepEqual(report.aspect_impact_map, {});
        });

        it('action ref graph keys exist for inline during action', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.ok(Object.keys(report.action_ref_graph).includes('Root.Active:<inline>'));
        });
    });

    describe('composite + aspect coverage', () => {
        it('hierarchy depth correct', async () => {
            const report = inspectModel(await buildMachine(COMPOSITE_DSL));
            assert.equal(report.metrics.max_hierarchy_depth, 2);
        });

        it('aspect impact map lists descendant leaves', async () => {
            const report = inspectModel(await buildMachine(COMPOSITE_DSL));
            assert.deepEqual(
                new Set(report.aspect_impact_map['Outer']),
                new Set(['Outer.Inner.A', 'Outer.Inner.B', 'Outer.Sibling']),
            );
        });

        it('aspect_coverage metric matches descendant leaf count', async () => {
            const report = inspectModel(await buildMachine(COMPOSITE_DSL));
            assert.equal(report.metrics.aspect_coverage['Outer'], 3);
        });
    });

    describe('toJson / JSON-stable output', () => {
        it('serializes via JSON.stringify without throwing', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const text = JSON.stringify(report);
            assert.equal(typeof text, 'string');
            const parsed = JSON.parse(text);
            assert.equal(parsed.root_state_path, 'Root');
        });

        it('diagnostics array empty for PR-A', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            assert.deepEqual(report.diagnostics, []);
        });

        it('top-level keys mirror the shared schema', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const keys = Object.keys(report).sort();
            assert.deepEqual(keys, [
                'action_ref_graph',
                'aspect_impact_map',
                'diagnostics',
                'event_emission_map',
                'events',
                'metrics',
                'reachability_graph',
                'root_state_path',
                'states',
                'transitions',
                'var_dataflow',
                'variables',
            ]);
        });
    });

    // PR-A-coverage: hit the uncovered code paths in
    // ``editors/jsfcstm/src/diagnostics/inspect.ts`` —
    // ``inspectModelToJson`` round-trip helper, ``effectsText`` + the
    // effect-statement var-dataflow walker, ``walkExprCollect`` cases
    // for BinaryOp/UnaryOp/ConditionalOp inside effects, and the
    // ``IfBlock`` reads/writes walker.
    describe('extended coverage (PR-A-coverage)', () => {
        const EFFECTS_DSL = `
def int counter = 0;
def int last = 0;
def int total = 0;
state Root {
    state Idle;
    state Active;
    [*] -> Idle;
    Idle -> Active : if [counter > 0] effect {
        last = counter;
        counter = counter + 1;
        total = (counter > 10) ? counter * 2 : counter - last;
    };
    Active -> Idle :: Pause effect {
        if [counter > 5] {
            counter = 0;
        } else {
            counter = counter + 1;
        }
    };
}
`;

        it('inspectModelToJson returns a structurally equal but reference-independent copy', async () => {
            const report = inspectModel(await buildMachine(EFFECTS_DSL));
            const cloned = packageModule.inspectModelToJson(report);
            // Round-trip is structurally equal to the original.
            assert.deepEqual(cloned, JSON.parse(JSON.stringify(report)));
            // BUT it must be a distinct object — same-reference would
            // mean the helper returned the original (or aliased it).
            assert.notStrictEqual(cloned, report);
            // Mutation-isolation: mutating the clone must NOT touch the
            // original. This is the assertion that proves the "deep
            // copy" claim — assert.deepEqual with the json-roundtrip
            // form alone is a self-reflexive equation when the impl IS
            // that round-trip.
            const originalSnapshot = JSON.stringify(report);
            (cloned as { variables: unknown[] }).variables.push({mutated: true});
            assert.equal(JSON.stringify(report), originalSnapshot,
                'mutating the clone should not affect the original report');
        });

        it('walks effect-side expressions (ternary + binary) to record reads', async () => {
            const report = inspectModel(await buildMachine(EFFECTS_DSL));
            // ``counter`` is read inside the effect (RHS of ``last =
            // counter`` AND inside ``counter + 1`` AND inside the
            // ternary's condition and branches). The walker must
            // descend through BinaryOp + ConditionalOp + UnaryOp
            // nodes to find every read.
            assert.ok(report.var_dataflow['counter']);
            assert.ok(report.var_dataflow['counter'].reads.includes('Root.Idle'));
            // ``last`` is only read inside the ternary's else branch
            // (``counter - last``) — proves the ConditionalOp.ifFalse
            // walker visited.
            assert.ok(report.var_dataflow['last']);
            assert.ok(report.var_dataflow['last'].reads.includes('Root.Idle'));
        });

        it('per-variable VariableInfo captures effect writes per from→to pair', async () => {
            // ``var_dataflow.writes`` records state-block writes only
            // (enter/during/exit). Transition-effect writes go into
            // ``variables[i].written_in_effects`` as [from, to] pairs.
            const report = inspectModel(await buildMachine(EFFECTS_DSL));
            const counter = report.variables.find(v => v.name === 'counter');
            assert.ok(counter);
            // Idle -> Active transition effect writes counter.
            const pairs = counter!.written_in_effects;
            const hasIdleActive = pairs.some(p => p[0] === 'Root.Idle' && p[1] === 'Root.Active');
            assert.ok(hasIdleActive,
                `expected ['Root.Idle', 'Root.Active'] in counter.written_in_effects, got ${JSON.stringify(pairs)}`);
        });

        it('walks IfBlock inside transition effect to collect reads/writes', async () => {
            const report = inspectModel(await buildMachine(EFFECTS_DSL));
            // The Active -> Idle :: Pause effect has an if/else where
            // both branches reassign counter; the IfBlock walker must
            // visit branch.statements. Verify via written_in_effects.
            const counter = report.variables.find(v => v.name === 'counter');
            assert.ok(counter);
            const pairs = counter!.written_in_effects;
            const hasActiveIdle = pairs.some(p => p[0] === 'Root.Active' && p[1] === 'Root.Idle');
            assert.ok(hasActiveIdle,
                `expected counter to be written in Active->Idle effect (if-block branches), got ${JSON.stringify(pairs)}`);
        });

        it('effectsText surfaces effect text on BOTH transitions, including the IfBlock-bearing one', async () => {
            // Tightened (PR-A-coverage Codex I3): pin both transitions
            // — the guard-effect one (Idle→Active) and the if-block
            // effect one (Active→Idle). The latter is the case that
            // exercises ``walkStmtReadsWrites`` IfBlock branch.
            const report = inspectModel(await buildMachine(EFFECTS_DSL));
            const idleToActive = report.transitions.find(
                t => t.from_path === 'Root.Idle' && t.to_path === 'Root.Active',
            );
            assert.ok(idleToActive, 'expected Root.Idle → Root.Active transition');
            assert.ok(
                typeof idleToActive!.effect === 'string' && idleToActive!.effect!.length > 0,
                `Idle→Active effect text empty: ${JSON.stringify(idleToActive!.effect)}`,
            );
            const activeToIdle = report.transitions.find(
                t => t.from_path === 'Root.Active' && t.to_path === 'Root.Idle',
            );
            assert.ok(activeToIdle, 'expected Root.Active → Root.Idle transition');
            assert.ok(
                typeof activeToIdle!.effect === 'string' && activeToIdle!.effect!.length > 0,
                `Active→Idle (IfBlock-bearing) effect text empty: ${JSON.stringify(activeToIdle!.effect)}`,
            );
        });

        it('var_dataflow stays empty when no effects use the variable', async () => {
            // A variable referenced only by guard / external read should
            // not leak into the ``writes`` list.
            const dsl = `
def int sensor = 0;
state Root { state A; state B; [*] -> A; A -> B : if [sensor > 0]; }
`;
            const report = inspectModel(await buildMachine(dsl));
            const sensor = report.var_dataflow['sensor'];
            assert.ok(sensor);
            assert.equal(sensor.writes.length, 0);
        });
    });
});
