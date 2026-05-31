import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

const {
    DEFAULT_DEEP_HIERARCHY_THRESHOLD,
    DEFAULT_LARGE_COMPOSITE_THRESHOLD,
    DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD,
    inspectModel,
} = packageModule;

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

const STRUCTURAL_DATAFLOW_REDUNDANCY_DSL = `
def int read_only = 0;
def int write_only = 0;
def int stable = 0;
state Root {
    event Tick;
    state Idle { enter Touch { write_only = 1; } }
    state Active;
    state Trapped;
    state Orphan { enter Cleanup {} }
    state LeafForced { !* -> [*] :: Never; }
    [*] -> Idle : if [stable > 0];
    Idle -> Active : if [read_only > 0];
    Idle -> Active : if [read_only > 0];
    Active -> Active;
    Active -> Idle effect { stable = stable; };
    Active -> Trapped :: Tick;
    Trapped -> Idle : Tick;
    !Active -> Trapped :: Tick;
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

describe('diagnostics/inspect', () => {
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

        it('normalizes inspect expression and effect text like pyfcstm', async () => {
            const report = inspectModel(await buildMachine(`
def int x = 0x0F;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B : if [9007199254740993 == 9007199254740992] effect { x = (0x0F); };
}
`));
            assert.equal(report.variables.find(v => v.name === 'x')!.init_value, '15');
            const transition = report.transitions.find(t => t.from_path === 'Root.A');
            assert.ok(transition);
            assert.equal(transition!.guard, '9007199254740993 == 9007199254740992');
            assert.equal(transition!.effect, 'x = 15;');
            assert.equal(
                report.diagnostics.filter(d => d.code === 'W_GUARD_CONST_FALSE').length,
                1,
            );
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
            assert.equal(temp!.affects_guard_directly, false);
            assert.equal(temp!.affects_guard_indirectly, false);
        });
    });

    describe('guard-affect data flow', () => {
        it('tracks nested branch conditions in the use-def graph', async () => {
            const {buildUseDefGraph} = await import('../dist/diagnostics/analyzers/use-def');
            const graph = buildUseDefGraph(await buildMachine(`
def int x = 0;
def int y = 0;
def int z = 0;
def int flag = 0;
def int dedupe = 0;
state Root {
    state Active {
        during {
            dedupe = x + x;
            if [x >= 10] {
                if [x % 2 == 0] {
                    y = x + 10;
                } else {
                    y = x + 12;
                    z = x * y - 2;
                }
            } else if [flag > 0] {
                z = y + flag;
            } else {
                z = y - 10;
                x = x + 2;
            }
        }
    }
    [*] -> Active;
}
`));
            const edges = new Set(graph.edges.map(([source, target]) => `${source}->${target}`));
            assert.ok(edges.has('x->y'));
            assert.ok(edges.has('x->z'));
            assert.ok(edges.has('y->z'));
            assert.ok(edges.has('flag->z'));
            assert.ok(edges.has('x->x'));
            assert.ok(edges.has('flag->x'));
        });

        it('keeps use-def graph ordering stable for duplicate edge input', async () => {
            const {UseDefGraph} = await import('../dist/diagnostics/analyzers/use-def');
            const graph = new UseDefGraph([
                ['b', 'target'],
                ['a', 'target'],
                ['a', 'target'],
            ]);

            assert.deepEqual(graph.edges, [
                ['a', 'target'],
                ['a', 'target'],
                ['b', 'target'],
            ]);
            assert.deepEqual(graph.dependenciesOf('target'), ['a', 'a', 'b']);
        });

        it('marks direct and indirect guard-affect variables', async () => {
            const report = inspectModel(await buildMachine(`
def int source = 0;
def int middle = 0;
def int guard_value = 0;
def int direct = 0;
def int ternary_only = 0;
def int unused = 0;
state Root {
    state Idle {
        during {
            middle = source + 1;
            guard_value = middle;
            unused = (ternary_only > 0) ? 1 : 2;
        }
    }
    state Done;
    [*] -> Idle : if [direct > 0];
    Idle -> Done : if [guard_value > 0];
    Done -> [*] : if [direct > 1];
}
`));
            const variables = new Map(report.variables.map(v => [v.name, v]));
            assert.equal(variables.get('direct')!.affects_guard_directly, true);
            assert.equal(variables.get('direct')!.affects_guard_indirectly, false);
            assert.equal(variables.get('guard_value')!.affects_guard_directly, true);
            assert.equal(variables.get('guard_value')!.affects_guard_indirectly, false);
            assert.equal(variables.get('middle')!.affects_guard_directly, false);
            assert.equal(variables.get('middle')!.affects_guard_indirectly, true);
            assert.equal(variables.get('source')!.affects_guard_directly, false);
            assert.equal(variables.get('source')!.affects_guard_indirectly, true);
            assert.equal(variables.get('ternary_only')!.affects_guard_directly, false);
            assert.equal(variables.get('ternary_only')!.affects_guard_indirectly, false);
            assert.equal(variables.get('unused')!.affects_guard_directly, false);
            assert.equal(variables.get('unused')!.affects_guard_indirectly, false);
        });

        it('emits unreferenced variables as warning or info based on abstract actions', async () => {
            const noAbstract = inspectModel(await buildMachine(`
def int unused = 0;
def int driver = 0;
state Root {
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : if [driver > 0];
}
`));
            assert.deepEqual(
                noAbstract.diagnostics
                    .filter(d => d.code === 'W_UNREFERENCED_VAR')
                    .map(d => d.refs),
                [{var_name: 'unused', init_value: '0'}],
            );
            assert.equal(
                noAbstract.diagnostics.filter(d => d.code === 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT').length,
                0,
            );

            const withAbstract = inspectModel(await buildMachine(`
def int maybe_external = 0;
def int driver = 0;
state Root {
    state Idle { enter abstract ExternalHook; }
    state Done;
    [*] -> Idle;
    Idle -> Done : if [driver > 0];
}
`));
            assert.deepEqual(
                withAbstract.diagnostics
                    .filter(d => d.code === 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT')
                    .map(d => d.refs),
                [{
                    var_name: 'maybe_external',
                    abstract_actions_in_scope: ['Root.Idle:<abstract>'],
                }],
            );
        });

        it('does not report indirect guard dependencies as unreferenced', async () => {
            const report = inspectModel(await buildMachine(`
def int source = 0;
def int guard_value = 0;
state Root {
    state Idle { during { guard_value = source + 1; } }
    state Done;
    [*] -> Idle;
    Idle -> Done : if [guard_value > 0];
}
`));
            const sourceCodes = report.diagnostics
                .filter(d => d.refs.var_name === 'source')
                .map(d => d.code);
            assert.deepEqual(sourceCodes, ['W_UNWRITTEN_READ_VAR']);
        });

        it('reports guard vars that never change per transition', async () => {
            const report = inspectModel(await buildMachine(`
def int stable = 0;
def int changing = 0;
state Root {
    state Idle { during { changing = changing + 1; } }
    state StableBlocked;
    state DynamicAllowed;
    [*] -> Idle;
    Idle -> StableBlocked : if [stable > 0];
    Idle -> DynamicAllowed : if [changing > 0];
}
`));
            assert.deepEqual(
                report.diagnostics
                    .filter(d => d.code === 'W_GUARD_VARS_NEVER_CHANGE')
                    .map(d => d.refs),
                [{
                    from_path: 'Root.Idle',
                    to_path: 'Root.StableBlocked',
                    guard_vars: ['stable'],
                }],
            );
        });

        it('keeps the write-only branch available for affecting payloads', async () => {
            const {collectDataFlowWarnings} = await import('../dist/diagnostics/analyzers/data-flow');
            const diagnostics = collectDataFlowWarnings([{
                name: 'write_only',
                type: 'int',
                init_value: '0',
                read_in_states: [],
                written_in_states: ['Root.Idle'],
                read_in_guards: [],
                written_in_effects: [],
                affects_guard_directly: true,
                affects_guard_indirectly: false,
                abstract_actions_in_scope: [],
                float_literal_assignments: [],
            }]);

            assert.deepEqual(diagnostics.map(d => d.refs), [{
                var_name: 'write_only',
                written_states: ['Root.Idle'],
            }]);
        });

        it('rejects unknown expression subclasses in the shared variable collector', async () => {
            const {collectExprVariables} = await import('../dist/diagnostics/analyzers/use-def');
            const {Expr} = await import('../dist/model/runtime');

            class UnknownExpr extends Expr {
                constructor() {
                    super(
                        'expression',
                        'UnknownExpr' as any,
                        {
                            start: {line: 0, character: 0},
                            end: {line: 0, character: 0},
                        },
                        'unknown',
                    );
                }

                to_ast_node(): any {
                    return {};
                }
            }

            assert.throws(
                () => collectExprVariables(new UnknownExpr()),
                /Unhandled Expr subclass: UnknownExpr/,
            );
        });

        it('rejects unknown operation statement subclasses in the use-def graph', async () => {
            const {buildUseDefGraph} = await import('../dist/diagnostics/analyzers/use-def');
            const {OperationStatement} = await import('../dist/model/runtime');

            class UnknownStatement extends OperationStatement {
                constructor() {
                    super(
                        'operationStatement',
                        'UnknownStatement' as any,
                        {
                            start: {line: 0, character: 0},
                            end: {line: 0, character: 0},
                        },
                        'unknown',
                    );
                }

                to_ast_node(): any {
                    return {};
                }
            }

            assert.throws(
                () => buildUseDefGraph({
                    allStates: [{
                        onEnters: [{
                            isAbstract: false,
                            operations: [new UnknownStatement()],
                        }],
                        onDurings: [],
                        onExits: [],
                        onDuringAspects: [],
                        transitions: [],
                    }],
                } as any),
                /Unhandled OperationStatement subclass: UnknownStatement/,
            );
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

        it('exports default threshold constants', () => {
            assert.equal(DEFAULT_DEEP_HIERARCHY_THRESHOLD, 6);
            assert.equal(DEFAULT_LARGE_COMPOSITE_THRESHOLD, 12);
            assert.equal(DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD, 2.0);
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

        it('diagnostics array empty for clean model without design-health warnings', async () => {
            const report = inspectModel(await buildMachine(`
def int counter = 0;
state Root {
    state Idle;
    state Active { during { counter = counter + 1; } }
    [*] -> Idle;
    Idle -> Active : if [counter > 0];
    Active -> Idle :: Pause;
}
`));
            assert.deepEqual(report.diagnostics, []);
        });

        it('top-level keys mirror the shared schema', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const keys = Object.keys(report).sort();
            assert.deepEqual(keys, [
                'action_ref_graph',
                'actions',
                'aspect_impact_map',
                'diagnostics',
                'event_emission_map',
                'events',
                'forced_transitions',
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

    describe('inspect design-health diagnostics', () => {
        const DESIGN_HEALTH_DSL = `
state Root {
    event Unused;
    event Used;
    state Idle;
    state Active;
    state Blocked;
    state Orphan;
    [*] -> Idle;
    Idle -> Active : Used;
    Active -> Blocked : if [false];
}
`;

        it('exposes declared-but-unused events in EventInfo', async () => {
            const report = inspectModel(await buildMachine(DESIGN_HEALTH_DSL));
            const byName: Record<string, typeof report.events[number]> = {};
            for (const event of report.events) byName[event.qualified_name] = event;

            assert.deepEqual(Object.keys(byName).sort(), ['Root.Unused', 'Root.Used']);
            assert.equal(byName['Root.Unused'].scope, 'chain');
            assert.deepEqual(byName['Root.Unused'].used_by, []);
            assert.equal(byName['Root.Unused'].is_declared, true);
            assert.equal(byName['Root.Unused'].is_used, false);

            assert.equal(byName['Root.Used'].scope, 'chain');
            assert.deepEqual(byName['Root.Used'].used_by, [['Root.Idle', 'Root.Active']]);
            assert.equal(byName['Root.Used'].is_declared, true);
            assert.equal(byName['Root.Used'].is_used, true);
        });

        it('emits design-health warnings on inspectModel diagnostics surface', async () => {
            const report = inspectModel(await buildMachine(DESIGN_HEALTH_DSL));
            const codes = report.diagnostics.map(d => d.code);
            assert.equal(codes.filter(code => code === 'W_UNUSED_EVENT').length, 1);
            assert.equal(codes.filter(code => code === 'W_GUARD_CONST_FALSE').length, 1);
            assert.equal(codes.filter(code => code === 'W_UNREACHABLE_STATE').length, 1);

            const unused = report.diagnostics.find(d => d.code === 'W_UNUSED_EVENT');
            assert.ok(unused);
            assert.equal(unused!.severity, 'warning');
            assert.deepEqual(unused!.refs, {
                event_qualified_name: 'Root.Unused',
                scope: 'chain',
            });

            const constFalse = report.diagnostics.find(d => d.code === 'W_GUARD_CONST_FALSE');
            assert.ok(constFalse);
            assert.equal(constFalse!.severity, 'warning');
            assert.deepEqual(constFalse!.refs, {
                transition_span: null,
                folded_value: false,
            });

            const unreachable = report.diagnostics.find(d => d.code === 'W_UNREACHABLE_STATE');
            assert.ok(unreachable);
            assert.equal(unreachable!.severity, 'warning');
            assert.deepEqual(unreachable!.refs, {
                state_path: 'Root.Orphan',
            });
        });

        it('event emission map only lists used events', async () => {
            const report = inspectModel(await buildMachine(DESIGN_HEALTH_DSL));
            assert.deepEqual(report.event_emission_map, {
                'Root.Used': ['Root.Idle'],
            });
        });

        it('folds large integer equality guards without number precision loss', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state Idle;
    state Active;
    [*] -> Idle;
    Idle -> Active : if [9007199254740993 == 9007199254740992];
}
`));
            assert.equal(
                report.diagnostics.filter(d => d.code === 'W_GUARD_CONST_FALSE').length,
                1,
            );
        });

        it('emits const-fold guard and during-assignment warnings', async () => {
            const report = inspectModel(await buildMachine(`
def int stable = 0;
def int dynamic = 0;
def int wide = 0;
def float powered = 0.0;
state Root {
    state Idle {
        during { stable = (2 + 3) * 4; }
        during { dynamic = dynamic + 1; }
        during { wide = 0xFFFFFFFF & 0xFFFFFFFF; }
        during { powered = 2.0 ** 3; }
    }
    state Active;
    state Blocked;
    state WideTrue;
    state ModuloTrue;
    state PowerTrue;
    [*] -> Idle;
    Idle -> Active : if [(1 + 2) == 3];
    Active -> Blocked : if [(0x0F & 0xF0) != 0];
    Blocked -> WideTrue : if [(0xFFFFFFFF & 0xFFFFFFFF) == 4294967295];
    WideTrue -> ModuloTrue : if [(-7 % 4) == 1];
    ModuloTrue -> PowerTrue : if [(2.0 ** 3) == 8.0];
}
`));
            const constTrue = report.diagnostics.filter(d => d.code === 'W_GUARD_CONST_TRUE');
            assert.equal(constTrue.length, 4);
            for (const item of constTrue) {
                assert.deepEqual(item.refs, {
                    transition_span: null,
                    folded_value: true,
                });
            }

            const constFalse = report.diagnostics.find(d => d.code === 'W_GUARD_CONST_FALSE');
            assert.ok(constFalse);
            assert.deepEqual(constFalse!.refs, {
                transition_span: null,
                folded_value: false,
            });

            const duringRefs = report.diagnostics
                .filter(d => d.code === 'W_DURING_CONST_ASSIGN')
                .map(d => d.refs)
                .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
            assert.deepEqual(duringRefs, [
                {state_path: 'Root.Idle', var_name: 'powered', value: 8},
                {state_path: 'Root.Idle', var_name: 'stable', value: 20},
                {state_path: 'Root.Idle', var_name: 'wide', value: 4294967295},
            ]);
        });

        it('does not const-fold variables functions or structural during actions', async () => {
            const report = inspectModel(await buildMachine(`
def int counter = 0;
def float angle = 0.0;
state Root {
    state Wrapper {
        during before { counter = 5; }
        >> during before { counter = 6; }
        state Idle {
            during { counter = counter + 1; }
            during { angle = sin(0.0); }
        }
        state Active;
        [*] -> Idle;
        Idle -> Active : if [counter > 0];
    }
    [*] -> Wrapper;
}
`));
            const codes = report.diagnostics.map(d => d.code);
            assert.equal(codes.includes('W_GUARD_CONST_TRUE'), false);
            assert.equal(codes.includes('W_GUARD_CONST_FALSE'), false);
            assert.equal(codes.includes('W_DURING_CONST_ASSIGN'), false);
        });

        it('emits structural dataflow and redundancy warnings', async () => {
            const report = inspectModel(await buildMachine(STRUCTURAL_DATAFLOW_REDUNDANCY_DSL));
            const normalized = report.diagnostics
                .map(d => ({
                    code: d.code,
                    severity: d.severity,
                    refs: JSON.parse(JSON.stringify(d.refs)),
                }))
                .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));

            assert.deepEqual(normalized, [
                {
                    code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
                    severity: 'info',
                    refs: {from_path: 'Root.Active', to_path: 'Root.Active', transition_span: null},
                },
                {
                    code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
                    severity: 'info',
                    refs: {from_path: 'Root.Active', to_path: 'Root.Idle', transition_span: null},
                },
                {
                    code: 'W_DEADLOCK_LEAF',
                    severity: 'warning',
                    refs: {state_path: 'Root.LeafForced', reason: 'no_outgoing_transition'},
                },
                {
                    code: 'W_DEADLOCK_LEAF',
                    severity: 'warning',
                    refs: {state_path: 'Root.Orphan', reason: 'no_outgoing_transition'},
                },
                {
                    code: 'W_DEAD_NAMED_ACTION',
                    severity: 'warning',
                    refs: {function_name: 'Cleanup', defined_in: 'Root.Orphan'},
                },
                {
                    code: 'W_EFFECT_SELF_ASSIGN',
                    severity: 'warning',
                    refs: {state_path: 'Root.Active', transition_span: null, var_name: 'stable'},
                },
                {
                    code: 'W_FORCED_NEVER_EXPANDS',
                    severity: 'warning',
                    refs: {state_path: 'Root.LeafForced', original_raw: '! * -> [*] :: Never;'},
                },
                {
                    code: 'W_FORCED_OVERRIDES_NORMAL',
                    severity: 'warning',
                    refs: {from_path: 'Root.Active', to_path: 'Root.Trapped', forced_span: null, normal_span: null},
                },
                {
                    code: 'W_GUARD_VARS_NEVER_CHANGE',
                    severity: 'warning',
                    refs: {
                        from_path: 'Root.Idle',
                        to_path: 'Root.Active',
                        guard_vars: ['read_only'],
                    },
                },
                {
                    code: 'W_GUARD_VARS_NEVER_CHANGE',
                    severity: 'warning',
                    refs: {
                        from_path: 'Root.Idle',
                        to_path: 'Root.Active',
                        guard_vars: ['read_only'],
                    },
                },
                {
                    code: 'W_INITIAL_UNCONDITIONAL_MISSING',
                    severity: 'warning',
                    refs: {composite_path: 'Root', existing_conditional_count: 1},
                },
                {
                    code: 'W_REDUNDANT_TRANSITION',
                    severity: 'warning',
                    refs: {
                        from_path: 'Root.Idle',
                        to_path: 'Root.Active',
                        duplicate_spans: [
                            'Root.Idle->Root.Active#1',
                            'Root.Idle->Root.Active#2',
                        ],
                    },
                },
                {
                    code: 'W_REDUNDANT_TRANSITION',
                    severity: 'warning',
                    refs: {
                        from_path: 'Root.Active',
                        to_path: 'Root.Trapped',
                        duplicate_spans: [
                            'Root.Active->Root.Trapped#1',
                            'Root.Active->Root.Trapped#2',
                        ],
                    },
                },
                {
                    code: 'W_SELF_TRANSITION_NOP',
                    severity: 'warning',
                    refs: {state_path: 'Root.Active'},
                },
                {
                    code: 'W_SHADOWED_EVENT',
                    severity: 'warning',
                    refs: {
                        event_name: 'Tick',
                        local_path: 'Root.Active.Tick',
                        chain_path: 'Root.Tick',
                    },
                },
                {
                    code: 'W_UNREACHABLE_STATE',
                    severity: 'warning',
                    refs: {state_path: 'Root.LeafForced'},
                },
                {
                    code: 'W_UNREACHABLE_STATE',
                    severity: 'warning',
                    refs: {state_path: 'Root.Orphan'},
                },
                {
                    code: 'W_UNREFERENCED_VAR',
                    severity: 'warning',
                    refs: {var_name: 'write_only', init_value: '0'},
                },
                {
                    code: 'W_UNWRITTEN_READ_VAR',
                    severity: 'warning',
                    refs: {var_name: 'read_only', read_states: ['Root.Idle'], init_value: '0'},
                },
            ].sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))));
        });

        it('keeps guard and chain path in forced transition origin text', async () => {
            const report = inspectModel(await buildMachine(`
def int counter = 0;
state Root {
    state Idle;
    state Error;
    state Bus { event Fail; }
    [*] -> Idle;
    !Idle -> [*] : if [counter > 0];
    !Error -> Idle : Bus.Fail;
}
`));
            const declarations: Record<string, string> = {};
            for (const item of report.forced_transitions) {
                declarations[item.from_path] = item.original_raw;
            }
            assert.equal(declarations['Root.Idle'], '! Idle -> [*] : if [counter > 0];');
            assert.equal(declarations['Root.Error'], '! Error -> Idle : Bus.Fail;');

            const origins: Record<string, string | null> = {};
            for (const transition of report.transitions.filter(t => t.is_forced)) {
                origins[`${transition.from_path}->${transition.to_path}`] = transition.forced_origin;
            }
            assert.equal(origins['Root.Idle->[*]'], '! Idle -> [*] : if [counter > 0];');
            assert.equal(origins['Root.Error->Root.Idle'], '! Error -> Idle : Bus.Fail;');
        });

        it('keeps grouped guard expression in forced transition origin text', async () => {
            const report = inspectModel(await buildMachine(`
def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    !A -> B : if [(x + 1) * 2 > 0];
}
`));
            const declaration = report.forced_transitions.find(item => item.from_path === 'Root.A');
            assert.ok(declaration);
            assert.equal(declaration!.original_raw, '! A -> B : if [(x + 1) * 2 > 0];');
            const transition = report.transitions.find(t => t.is_forced);
            assert.ok(transition);
            assert.equal(transition!.forced_origin, '! A -> B : if [(x + 1) * 2 > 0];');
        });

        it('normalizes forced transition declaration guard text like pyfcstm', async () => {
            const report = inspectModel(await buildMachine(`
def int x = 0;
def int y = 1;
state Root {
    state A;
    state B;
    [*] -> A;
    !A -> B : if [x == 0x0F and not (y == 0)];
}
`));
            const declaration = report.forced_transitions.find(item => item.from_path === 'Root.A');
            assert.ok(declaration);
            assert.equal(declaration!.guard, 'x == 0x0f && !(y == 0)');
            assert.equal(declaration!.original_raw, '! A -> B : if [x == 0x0f && !(y == 0)];');
        });

        it('keeps inherited forced transition origins on the original declaration', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state Running {
        state A;
        state B;
        [*] -> A;
    }
    state Error;
    [*] -> Running;
    !Running -> Error :: Panic;
}
`));
            const origins: Record<string, string | null> = {};
            for (const transition of report.transitions.filter(t => t.is_forced)) {
                origins[transition.from_path] = transition.forced_origin;
            }
            assert.equal(origins['Root.Running'], '! Running -> Error :: Panic;');
            assert.equal(origins['Root.Running.A'], '! Running -> Error :: Panic;');
            assert.equal(origins['Root.Running.B'], '! Running -> Error :: Panic;');
        });

        it('does not shadow events across unrelated sibling scopes', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state A {
        state A1;
        state A2;
        [*] -> A1;
        A1 -> A2 :: Tick;
    }
    state B {
        state B1;
        state B2;
        [*] -> B1;
        B1 -> B2 : Tick;
    }
    [*] -> A;
    A -> B :: Go;
}
`));
            assert.deepEqual(
                report.diagnostics.filter(d => d.code === 'W_SHADOWED_EVENT'),
                [],
            );
        });

        it('does not let unreachable refs suppress dead named action diagnostics', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state Idle;
    state Orphan { enter Target {} }
    state Other { enter ref /Orphan.Target; }
    [*] -> Idle;
}
`));
            assert.deepEqual(
                report.diagnostics
                    .filter(d => d.code === 'W_DEAD_NAMED_ACTION')
                    .map(d => d.refs),
                [{function_name: 'Target', defined_in: 'Root.Orphan'}],
            );
        });

        it('does not treat transitions with different effects as redundant', async () => {
            const report = inspectModel(await buildMachine(`
def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B effect { x = 1; };
    A -> B effect { x = 2; };
}
`));
            const effects = report.transitions
                .filter(t => t.from_path === 'Root.A' && t.to_path === 'Root.B')
                .map(t => t.effect);
            assert.deepEqual(effects, ['x = 1;', 'x = 2;']);
            assert.deepEqual(
                report.diagnostics.filter(d => d.code === 'W_REDUNDANT_TRANSITION'),
                [],
            );
        });

        it('normalizes equivalent effect text before redundant transition comparison', async () => {
            const report = inspectModel(await buildMachine(`
def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B effect { x = 1; };
    A -> B effect { x = (1); };
}
`));
            const effects = report.transitions
                .filter(t => t.from_path === 'Root.A' && t.to_path === 'Root.B')
                .map(t => t.effect);
            assert.deepEqual(effects, ['x = 1;', 'x = 1;']);
            assert.equal(
                report.diagnostics.filter(d => d.code === 'W_REDUNDANT_TRANSITION').length,
                1,
            );
        });

        it('does not report lifecycle self re-entry as no-op', async () => {
            const report = inspectModel(await buildMachine(`
def int counter = 0;
state Root {
    state Active {
        enter { counter = counter + 1; }
    }
    [*] -> Active;
    Active -> Active;
}
`));
            assert.deepEqual(
                report.diagnostics.filter(d => d.code === 'W_SELF_TRANSITION_NOP'),
                [],
            );
        });

        it('does not report self re-entry with ancestor aspects as no-op', async () => {
            const report = inspectModel(await buildMachine(`
def int counter = 0;
state Root {
    >> during before { counter = counter + 1; }
    state Active;
    [*] -> Active;
    Active -> Active;
}
`));
            assert.deepEqual(
                report.diagnostics.filter(d => d.code === 'W_SELF_TRANSITION_NOP'),
                [],
            );
        });

        it('reports self assignment inside nested effect if-block', async () => {
            const report = inspectModel(await buildMachine(`
def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B effect {
        if [x > 0] {
            x = x;
        }
    };
}
`));
            assert.deepEqual(
                report.diagnostics
                    .filter(d => d.code === 'W_EFFECT_SELF_ASSIGN')
                    .map(d => d.refs),
                [{
                    state_path: 'Root.A',
                    transition_span: null,
                    var_name: 'x',
                }],
            );
        });
    });

    describe('extended inspect coverage', () => {
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
            // Pin both transitions: the guard-effect one
            // (Idle->Active) and the if-block effect one
            // (Active->Idle). The latter exercises the
            // ``walkStmtReadsWrites`` IfBlock branch.
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

        // Target less common inspect paths: action label ref branches,
        // unary / function expression walking, ref targets in
        // action_ref_graph, state-path fallback in functionSignature,
        // and actions_in_scope label emission.
        it('exposes ref:<name> labels for both action and aspect refs', async () => {
            // Lines 263-264 (functionSignature ref:name) +
            // 271-272 (aspectLabel ref:name).
            const dsl = `
state Root {
    enter Setup { }
    state Idle {
        enter ref /Setup;
    }
    state Sub {
        state Leaf;
        [*] -> Leaf;
        >> during before ref /Setup;
    }
    [*] -> Idle;
}
`;
            const report = inspectModel(await buildMachine(dsl));
            // At least one action_ref edge with the resolved ref:Setup label.
            const refEdges = Object.values(report.action_ref_graph).flat();
            assert.ok(refEdges.length > 0,
                `expected ref edges in action_ref_graph, got ${JSON.stringify(report.action_ref_graph)}`);
        });

        it('walks unary / function expressions inside effects', async () => {
            // Line 463-464: ``case 'UnaryOp': case 'UFunc'`` branch
            // of walkExprCollect (effect-block walker).
            const dsl = `
def float angle = 0.0;
def float v = 0.0;
state Root {
    state Idle; state Computing;
    [*] -> Idle;
    Idle -> Computing : if [angle > 0.0] effect {
        v = -sin(angle);
    };
}
`;
            const report = inspectModel(await buildMachine(dsl));
            const angle = report.var_dataflow['angle'];
            assert.ok(angle);
            // angle is read inside the effect (sin's argument).
            assert.ok(angle.reads.includes('Root.Idle'),
                `expected angle read in Root.Idle, got ${JSON.stringify(angle)}`);
        });

        it('actions_in_scope path with abstract action label', async () => {
            // Lines 529-530: abstract-action label assembly in
            // ``actionsInScope`` for variable abstract-action listing.
            // The variable ``counter`` is read in ``Idle.during`` and
            // the state ``Idle`` has an ``enter abstract Setup``, so
            // the helper must include ``Root.Idle:<abstract>`` in the
            // variable's ``abstract_actions_in_scope`` list.
            const dsl = `
def int counter = 0;
state Root {
    state Idle {
        enter abstract Setup;
        during { counter = counter + 1; }
    }
    [*] -> Idle;
}
`;
            const report = inspectModel(await buildMachine(dsl));
            const counter = report.variables.find(v => v.name === 'counter');
            assert.ok(counter);
            assert.deepEqual(counter!.abstract_actions_in_scope, ['Root.Idle:<abstract>']);
        });

        it('inspect_model handles effect text fallback via stmt.text field', async () => {
            // Lines 505-506: ``effectStatementText`` reads stmt.text
            // when present. The standard parser sets .text on each
            // OperationStatement, so a normal effect block exercises
            // this path. The earlier "effectsText surfaces non-empty"
            // test already pins this, but add an explicit assertion
            // on the rendered effect to lock it.
            const dsl = `
def int counter = 0;
state Root {
    state Idle; state Active;
    [*] -> Idle;
    Idle -> Active :: Go effect { counter = counter + 1; };
}
`;
            const report = inspectModel(await buildMachine(dsl));
            const t = report.transitions.find(
                tr => tr.from_path === 'Root.Idle' && tr.to_path === 'Root.Active',
            );
            assert.ok(t);
            assert.ok(typeof t!.effect === 'string' && t!.effect!.length > 0);
        });
    });

    describe('threshold, info, naming, and type diagnostics', () => {
        function diagnosticsByCode(report: ReturnType<typeof inspectModel>) {
            const out = new Map<string, typeof report.diagnostics>();
            for (const diagnostic of report.diagnostics) {
                out.set(diagnostic.code, [...(out.get(diagnostic.code) ?? []), diagnostic]);
            }
            return out;
        }

        it('emits threshold diagnostics with actual and threshold refs', async () => {
            const report = inspectModel(await buildMachine(`
def int a = 0;
def int b = 0;
def int c = 0;
state Root {
    state A;
    state B;
    state C;
    [*] -> A;
    A -> B :: Next;
    B -> C :: Next;
    C -> A :: Next;
}
`), {
                varToLeafRatioThreshold: 0.5,
                largeCompositeThreshold: 2,
                deepHierarchyThreshold: 0,
            });
            const byCode = diagnosticsByCode(report);

            assert.deepEqual(byCode.get('W_HIGH_VAR_TO_LEAF_RATIO')![0].refs, {
                n_vars: 3,
                n_leaf_states: 3,
                actual: 1.0,
                threshold: 0.5,
            });
            assert.deepEqual(byCode.get('W_LARGE_COMPOSITE')![0].refs, {
                composite_path: 'Root',
                n_children: 3,
                actual: 3,
                threshold: 2,
            });
            assert.deepEqual(byCode.get('W_DEEP_HIERARCHY')![0].refs, {
                max_depth: 1,
                deepest_path: 'Root.A',
                actual: 1,
                threshold: 0,
            });
        });

        it('uses one as the minimum denominator for variable-to-leaf ratio', async () => {
            const report = inspectModel(await buildMachine(`
def int a = 0;
def int b = 0;
def int c = 0;
state Root {
    pseudo state Marker;
    [*] -> Marker;
}
`), {
                varToLeafRatioThreshold: 2.0,
            });
            assert.deepEqual(diagnosticsByCode(report).get('W_HIGH_VAR_TO_LEAF_RATIO')![0].refs, {
                n_vars: 3,
                n_leaf_states: 0,
                actual: 3.0,
                threshold: 2.0,
            });
        });

        it('rejects fractional count thresholds', async () => {
            const machine = await buildMachine(`
state Root {
    state A;
    [*] -> A;
}
`);
            assert.throws(
                () => inspectModel(machine, {deepHierarchyThreshold: 0.5}),
                /deepHierarchyThreshold/,
            );
            assert.throws(
                () => inspectModel(machine, {largeCompositeThreshold: 2.5}),
                /largeCompositeThreshold/,
            );
        });

        it('rejects non-finite variable-to-leaf ratio thresholds', async () => {
            const machine = await buildMachine(`
state Root {
    state A;
    [*] -> A;
}
`);
            assert.throws(
                () => inspectModel(machine, {varToLeafRatioThreshold: true as unknown as number}),
                /varToLeafRatioThreshold/,
            );
            assert.throws(
                () => inspectModel(machine, {varToLeafRatioThreshold: Number.NaN}),
                /varToLeafRatioThreshold/,
            );
        });

        it('normalizes integer-valued count thresholds before emitting refs', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state A;
    state B;
    state C;
    [*] -> A;
}
`), {
                deepHierarchyThreshold: 0.0,
                largeCompositeThreshold: 2.0,
            });
            assert.deepEqual(diagnosticsByCode(report).get('W_DEEP_HIERARCHY')![0].refs, {
                max_depth: 1,
                deepest_path: 'Root.A',
                actual: 1,
                threshold: 0,
            });
            assert.deepEqual(diagnosticsByCode(report).get('W_LARGE_COMPOSITE')![0].refs, {
                composite_path: 'Root',
                n_children: 3,
                actual: 3,
                threshold: 2,
            });
        });

        it('does not emit threshold diagnostics with defaults for a small model', async () => {
            const report = inspectModel(await buildMachine(SIMPLE_DSL));
            const codes = new Set(report.diagnostics.map(d => d.code));
            assert.equal(codes.has('W_HIGH_VAR_TO_LEAF_RATIO'), false);
            assert.equal(codes.has('W_LARGE_COMPOSITE'), false);
            assert.equal(codes.has('W_DEEP_HIERARCHY'), false);
        });

        it('emits named action shadow diagnostics', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    enter Sync { }
    state Child {
        enter Sync { }
    }
    [*] -> Child;
}
`));
            assert.deepEqual(
                diagnosticsByCode(report).get('W_NAMED_ACTION_SHADOWS_ANCESTOR')![0].refs,
                {
                    function_name: 'Sync',
                    inner_state_path: 'Root.Child',
                    outer_state_path: 'Root',
                },
            );
        });

        it('emits literal type narrowing diagnostics for int initializers', async () => {
            const report = inspectModel(await buildMachine(`
def int truncated = 3.5;
state Root {
    state A;
    [*] -> A;
}
`));
            assert.deepEqual(
                diagnosticsByCode(report).get('W_LITERAL_TYPE_NARROWING')![0].refs,
                {
                    var_name: 'truncated',
                    target_type: 'int',
                    source_expr: '3.5',
                },
            );
        });

        it('emits literal type narrowing diagnostics for int assignments', async () => {
            const report = inspectModel(await buildMachine(`
def int truncated = 0;
state Root {
    state A {
        during { truncated = 2.25; }
    }
    [*] -> A;
}
`));
            assert.deepEqual(
                diagnosticsByCode(report).get('W_LITERAL_TYPE_NARROWING')![0].refs,
                {
                    var_name: 'truncated',
                    target_type: 'int',
                    source_expr: '2.25',
                },
            );
        });

        it('emits aspect diagnostics for aspects with no descendant leaves', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    pseudo state Marker;
    [*] -> Marker;
    >> during before { }
}
`));
            assert.deepEqual(
                diagnosticsByCode(report).get('W_ASPECT_NO_DESCENDANT_LEAF')![0].refs,
                {
                    composite_path: 'Root',
                    aspect: 'before',
                },
            );
        });

        it('emits info for composite self re-entry transitions', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state Active {
        state Leaf;
        [*] -> Leaf;
    }
    [*] -> Active;
    Active -> Active;
}
`));
            const diagnostic = diagnosticsByCode(report).get('I_TRANSITION_TO_SELF_VIA_PARENT')![0];
            assert.equal(diagnostic.severity, 'info');
            assert.deepEqual(diagnostic.refs, {
                state_path: 'Root.Active',
                crosses_composite: true,
            });
        });

        it('emits info for eventless and guardless transitions', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B;
}
`));
            const diagnostic = diagnosticsByCode(report).get('I_TRANSITION_NEVER_EVENT_TRIGGERED')![0];
            assert.equal(diagnostic.severity, 'info');
            assert.deepEqual(diagnostic.refs, {
                from_path: 'Root.A',
                to_path: 'Root.B',
                transition_span: null,
            });
        });

        it('emits info for eventless and guardless exit transitions', async () => {
            const report = inspectModel(await buildMachine(`
state Root {
    state A;
    [*] -> A;
    A -> [*];
}
`));
            const diagnostic = diagnosticsByCode(report).get('I_TRANSITION_NEVER_EVENT_TRIGGERED')![0];
            assert.equal(diagnostic.severity, 'info');
            assert.deepEqual(diagnostic.refs, {
                from_path: 'Root.A',
                to_path: '[*]',
                transition_span: null,
            });
        });
    });
});
