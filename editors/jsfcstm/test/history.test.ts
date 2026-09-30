import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';
import {HISTORY_DIAGNOSTIC_CASES, HISTORY_MODEL_CASES} from './fixtures/history-parity';

let documentIndex = 0;

function document(text: string) {
    documentIndex += 1;
    return createDocument(text, `/tmp/jsfcstm-history-${documentIndex}.fcstm`);
}

async function model(text: string) {
    const ast = await packageModule.parseAstDocument(document(text));
    assert.ok(ast);
    const machine = packageModule.buildStateMachineModel(ast);
    assert.ok(machine);
    return machine;
}

function stateAt(machine: Awaited<ReturnType<typeof model>>, path: string) {
    return machine.allStates.find(state => state.path.join('.') === path)!;
}

function charOf(text: string, line: number, needle: string): number {
    return text.split('\n')[line].indexOf(needle);
}

const WASHER = HISTORY_MODEL_CASES.washer.source;

describe('jsfcstm history syntax', () => {
    it('collects history declarations and history targets on every transition form', async () => {
        const ast = await packageModule.parseAstDocument(document([
            'state R {',
            '    state Off;',
            '    state O {',
            '        state A;',
            '        state W { state W1; [*] -> W1; }',
            '        [*] -> A;',
            '        /*',
            '         * resume',
            '         */',
            '        [H] -> A;',
            '        [H*] -> W.W1;',
            '    }',
            '    [*] -> O.[H*];',
            '    Off -> O.[H] :: Resume + [1 > 0] effect { }',
            '    !O -> O.[H*] :: Again;',
            '    !* -> O.[H];',
            '    Off -> O;',
            '}',
        ].join('\n')));
        assert.ok(ast?.rootState);
        const owner = ast.rootState.substates.find(state => state.name === 'O')!;
        assert.deepEqual(
            owner.histories.map(item => [item.pyNodeType, item.historyKind, item.history_kind, item.defaultPath, item.default_path]),
            [
                ['HistoryDefinition', 'shallow', 'shallow', ['A'], ['A']],
                ['HistoryDefinition', 'deep', 'deep', ['W', 'W1'], ['W', 'W1']],
            ],
        );
        assert.equal(owner.histories[0].doc, 'resume');
        assert.ok(owner.statements.some(item => item.kind === 'historyDefinition'));
        assert.deepEqual(
            ast.rootState.transitions.map(item => [item.transitionKind, item.targetStateName, item.targetHistory ?? null]),
            [['entry', 'O', 'deep'], ['normal', 'O', 'shallow'], ['normal', 'O', null]],
        );
        assert.equal(ast.rootState.transitions[1].comboTrigger?.isCombo, true);
        assert.deepEqual(
            ast.rootState.forceTransitions.map(item => [item.transitionKind, item.target_history]),
            [['normal', 'deep'], ['normalAll', 'shallow']],
        );
    });
});

describe('jsfcstm history lowering', () => {
    for (const [name, testCase] of Object.entries(HISTORY_MODEL_CASES)) {
        it(`records the same owner metadata as pyfcstm for ${name}`, async () => {
            const machine = await model(testCase.source);
            assert.deepEqual(
                machine.historyOwners.map(owner => ({
                    owner_path: owner.owner_path,
                    record_variable: owner.record_variable,
                    goto_variable: owner.goto_variable,
                    defaults: owner.defaults,
                    leaf_ids: owner.leaf_ids,
                })),
                testCase.owners,
            );
            assert.equal(machine.history_owners, machine.historyOwners);
        });
    }

    it('numbers owner tags that would collide after underscore collapsing, as pyfcstm does', async () => {
        // ``R.A_B`` and ``R.A.B`` both join to ``A_B``; ``goto`` is the shared
        // restore target's tag.  Expected names come from pyfcstm.
        const machine = await model([
            'state R {',
            '    state Off;',
            '    state A_B { state X; [*] -> X; [H] -> X; }',
            '    state A {',
            '        state B { state Y; [*] -> Y; [H] -> Y; }',
            '        state C;',
            '        [*] -> C;',
            '        C -> B.[H] :: Back;',
            '    }',
            '    state goto { state Z; [*] -> Z; [H] -> Z; }',
            '    [*] -> Off;',
            '    Off -> A_B.[H] :: E1;',
            '    Off -> A :: E2;',
            '    Off -> goto.[H] :: E3;',
            '    !A_B -> Off :: S1;',
            '    !A -> Off :: S2;',
            '    !goto -> Off :: S3;',
            '}',
        ].join('\n'));
        assert.deepEqual(
            machine.historyOwners.map(owner => [owner.owner_path.join('.'), owner.record_variable]),
            [['R.A_B', '__hist_A_B'], ['R.A.B', '__hist_A_B_2'], ['R.goto', '__hist_goto_2']],
        );
    });

    it('conjoins the gate with the guard of a gated initial the author wrote', async () => {
        const machine = await model([
            'def int x = 0;',
            'state R {',
            '    state Off;',
            '    state O {',
            '        state A;',
            '        state B;',
            '        [*] -> A : if [x == 0] effect { x = 1; }',
            '        [*] -> B;',
            '        [H] -> B;',
            '        A -> B :: Go;',
            '    }',
            '    [*] -> Off;',
            '    Off -> O.[H] :: Resume;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n'));
        const gated = stateAt(machine, 'R.O').init_transitions.find(item => item.historyRole === 'gated')!;
        assert.equal(gated.toState, 'A');
        const guard = gated.guard as unknown as {op: string; y: unknown};
        assert.equal(guard.op, '&&');
        assert.equal(guard.y, gated.historyUserGuard);
    });

    it('marks history entries, routes, merged and gated initials', async () => {
        const machine = await model(WASHER);
        const entries = stateAt(machine, 'Washer').transitions.filter(item => item.fromState === 'Paused');
        assert.deepEqual(entries.map(item => [item.event?.name, item.target_history ?? null]), [
            ['Fresh', null], ['Shallow', 'shallow'], ['Deep', 'deep'],
        ]);
        assert.deepEqual(
            stateAt(machine, 'Washer.Program').init_transitions.map(item => [item.toState, item.history_role]),
            [['Wash', 'route'], ['Idle', 'merged']],
        );
        const wash = stateAt(machine, 'Washer.Program.Wash').init_transitions;
        assert.deepEqual(wash.map(item => [item.toState, item.historyRole]), [
            ['Fill', 'route'], ['Agitate', 'route'], ['Fill', 'gated'],
        ]);
        assert.equal(wash[2].history_user_guard, undefined);
        assert.equal(machine.defines.__hist_goto.type, 'int');
        assert.equal(machine.historyDiagnostics.length, 0);
    });

    it('keeps the user guard of a merged initial', async () => {
        const machine = await model(HISTORY_MODEL_CASES['blocked-merged'].source);
        const merged = stateAt(machine, 'R.O.K').init_transitions.find(item => item.historyRole === 'merged')!;
        assert.equal(merged.historyUserGuard?.pyModelType, 'BinaryOp');
        assert.equal(merged.history_user_guard, merged.historyUserGuard);
    });

    it('splits an evented initial through a generated gate', async () => {
        const machine = await model(HISTORY_MODEL_CASES.evented.source);
        const gate = stateAt(machine, 'R.O.__hist_gate_1');
        assert.ok(gate.isHistoryGate && gate.is_history_gate && gate.isPseudo);
        assert.ok(machine.allStates.includes(gate));
        const owner = stateAt(machine, 'R.O');
        assert.deepEqual(owner.transitions.map(item => [item.fromState, item.toState, item.historyRole ?? null]), [
            ['INIT_STATE', 'B', 'route'],
            ['INIT_STATE', 'A', 'route'],
            ['A', 'EXIT_STATE', null],
            ['B', 'EXIT_STATE', null],
            ['INIT_STATE', '__hist_gate_1', 'gate'],
            ['A', 'B', null],
            ['__hist_gate_1', 'A', 'gated'],
        ]);
        const gated = owner.transitions[6];
        assert.equal(gated.event?.name, 'Kick');
        assert.equal(gated.triggerScope, 'chain');
        assert.deepEqual(gated.sourceStatePath, ['R', 'O', '__hist_gate_1']);
        assert.equal(machine.allTransitions.length, machine.allStates.reduce((count, state) => count + state.transitions.length, 0));
    });

    it('keeps an absolute event scope when gating an evented initial', async () => {
        const machine = await model([
            'state R {',
            '    state Off;',
            '    state O { state A; [*] -> A : /Go; [H] -> A; }',
            '    [*] -> Off;',
            '    Off -> O.[H] :: Resume;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n'));
        const gated = stateAt(machine, 'R.O').transitions.find(item => item.historyRole === 'gated')!;
        assert.equal(gated.triggerScope, 'absolute');
    });

    it('only the terminal combo edge enters the history', async () => {
        const machine = await model(HISTORY_MODEL_CASES.combo.source);
        const root = stateAt(machine, 'R');
        const combo = root.transitions.filter(item => item.fromState === 'Off' && item.toState.startsWith('__combo_'));
        const terminal = root.transitions.find(item => item.fromState.startsWith('__combo_'))!;
        assert.equal(combo.length, 1);
        assert.equal(combo[0].targetHistory, undefined);
        assert.equal(terminal.target_history, 'deep');
        assert.deepEqual(terminal.effects.map(item => (item as {var_name: string}).var_name), ['__hist_goto']);
    });

    it('carries history targets through forced expansion but not into inherited exits', async () => {
        const machine = await model([
            'state R {',
            '    state A { state A1; [*] -> A1; }',
            '    state O { state B; [*] -> B; [H] -> B; }',
            '    [*] -> A;',
            '    !* -> O.[H] :: Go;',
            '}',
        ].join('\n'));
        const root = stateAt(machine, 'R');
        assert.deepEqual(root.transitions.filter(item => item.forced).map(item => [item.fromState, item.target_history]), [
            ['A', 'shallow'], ['O', 'shallow'],
        ]);
        const inherited = stateAt(machine, 'R.A').transitions.filter(item => item.forced);
        assert.ok(inherited.length > 0);
        assert.ok(inherited.every(item => item.targetHistory === undefined));
        assert.equal(machine.forcedTransitions[0].originalRaw, '! * -> O.[H] :: Go;');
    });

    it('leaves machines without history untouched', async () => {
        const machine = await model('def int x = 0; state R { state A; state B; [*] -> A; A -> B :: Go; }');
        assert.deepEqual(machine.historyOwners, []);
        assert.deepEqual(Object.keys(machine.defines), ['x']);
        assert.ok(machine.allStates.every(state => !state.isHistoryGate));
    });
});

describe('jsfcstm history diagnostics', () => {
    for (const [name, testCase] of Object.entries(HISTORY_DIAGNOSTIC_CASES)) {
        it(`reports what pyfcstm reports for ${name}`, async () => {
            const doc = document(testCase.source);
            const history = (await packageModule.collectDocumentDiagnostics(doc))
                .filter(item => (item.code ?? '').includes('HISTORY'));
            assert.deepEqual(
                history.map(item => ({code: item.code, severity: item.severity, refs: item.data})),
                testCase.expected,
            );
            for (const item of history) {
                assert.equal(item.source, 'fcstm');
                assert.ok(item.message.length > 0);
                assert.ok(item.range.end.line > item.range.start.line || item.range.end.character > item.range.start.character);
            }
        });
    }

    for (const [name, lines, expected] of [
        [
            'reach the defaults of the kinds they name',
            [
                'state R {',
                '    state Off;',
                '    state O { state A; state Lost; state Def; [*] -> A; [H] -> Def; }',
                '    state D {',
                '        state A; state X;',
                '        state W { state W1; state W2; state W3; [*] -> W1; }',
                '        [*] -> A;',
                '        [H*] -> W.W2;',
                '        !W -> X :: Up;',
                '    }',
                '    [*] -> Off;',
                '    Off -> O.[H] :: Go;',
                '    !O -> Off :: Stop;',
                '    !Off -> D.[H*] :: Deep;',
                '}',
            ],
            // the deep default path is entered as ordinary targets, W1 included
            ['R.D.W.W3', 'R.O.Lost'],
        ],
        [
            'open a default only through the history entry',
            [
                'state R {',
                '    state Off; state Dead;',
                '    state O { state A; state D; [*] -> A; [H] -> D; }',
                '    [*] -> Off;',
                '    Off -> O :: Go;',
                '    Dead -> O.[H] :: Resume;',
                '    !O -> Off :: Stop;',
                '}',
            ],
            ['R.Dead', 'R.O.D'],
        ],
        [
            'open the history of a forced target only',
            [
                'state R {',
                '    state T3 { state S4; state S6; [*] -> S4; [H] -> S6; }',
                '    state S11 { state T13; [*] -> T13; [H] -> T13; }',
                '    [*] -> T3;',
                '    !* -> S11.[H] :: Go;',
                '}',
            ],
            ['R.T3.S6'],
        ],
    ] as Array<[string, string[], string[]]>) {
        it(`reports unreachable states as pyfcstm does when history entries ${name}`, async () => {
            const unreachable = (await packageModule.collectDocumentDiagnostics(document(lines.join('\n'))))
                .filter(item => item.code === 'W_UNREACHABLE_STATE')
                .map(item => /State "([^"]+)"/.exec(item.message)![1])
                .sort();
            assert.deepEqual(unreachable, expected);
        });
    }

    it('still reports declaration errors unrelated to an imported default', async () => {
        const cases: Array<[string, string[]]> = [
            ['state Host { import "./module.fcstm" as M; state A; [*] -> A; [H*] -> M.B; }', ['root_owner']],
            ['state Host { state Off; state O { import "./module.fcstm" as M; state A; [*] -> A; [H*] -> M.B; [H*] -> M.C; } [*] -> Off; Off -> O.[H*] :: Go; }', ['duplicate']],
            ['state Host { state Off; state O { import "./module.fcstm" as M; state A; [*] -> A; [H] -> M.B; } [*] -> Off; Off -> O.[H] :: Go; }', ['default_not_direct_child']],
        ];
        for (const [text, reasons] of cases) {
            const diagnostics = await packageModule.collectDocumentDiagnostics(document(text));
            assert.deepEqual(
                diagnostics.filter(item => item.code === 'E_HISTORY_DECLARATION_INVALID').map(item => (item.data as {reason: string}).reason),
                reasons,
            );
        }
    });

    it('enters the local states of a default that continues into an imported module', async () => {
        const text = [
            'state Host {',
            '    state Off;',
            '    state O {',
            '        state C { import "./module.fcstm" as M; state X; [*] -> X; }',
            '        state A;',
            '        [*] -> A;',
            '        [H*] -> C.M.B;',
            '    }',
            '    [*] -> Off;',
            '    Off -> O.[H*] :: Go;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n');
        const codes = (await packageModule.collectDocumentDiagnostics(document(text))).map(item => item.code ?? '');
        assert.deepEqual(codes.filter(code => code.includes('HISTORY') || code === 'W_UNREACHABLE_STATE'), []);
    });

    it('lets a history entry reach what a restore re-enters in the reachability graph', async () => {
        const report = packageModule.inspectModel(await model([
            'state Root {',
            '    state S; state P;',
            '    state O { state A; state Y; [*] -> A; [H] -> A; [H*] -> Y; Y -> [*]; }',
            '    [*] -> S;',
            '    S -> O.[H*] :: Deep;',
            '    O -> P;',
            '    P -> O.[H] :: Back;',
            '}',
        ].join('\n')));
        assert.deepEqual(report.reachability_graph['Root.P'], ['Root.O', 'Root.O.A', 'Root.O.Y']);
    });

    it('does not fail when a deep owner holds a transition into an import alias', async () => {
        const text = [
            'state R {',
            '    state Off;',
            '    state O { import "./module.fcstm" as M; state A; [*] -> A; [H*] -> A; A -> M :: Go; }',
            '    [*] -> Off;',
            '    Off -> O.[H*] :: Enter;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document(text));
        assert.deepEqual(diagnostics.filter(item => (item.code ?? '').includes('HISTORY')), []);
    });

    it('leaves an owner whose children all come from imports to the assembled model', async () => {
        const text = [
            'state R {',
            '    state Off;',
            '    state O { import "./module.fcstm" as M; [*] -> M; [H*] -> M.B; [H] -> M; }',
            '    [*] -> Off;',
            '    Off -> O.[H*] :: Deep;',
            '    Off -> O.[H] :: Shallow;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n');
        const codes = (await packageModule.collectDocumentDiagnostics(document(text))).map(item => item.code ?? '');
        assert.deepEqual(codes.filter(code => code.includes('HISTORY')), []);
    });

    it('still reports the states behind a misspelled default', async () => {
        const text = [
            'state Host {',
            '    state Off;',
            '    state O {',
            '        state C { state X; [*] -> X; }',
            '        state A;',
            '        [*] -> A;',
            '        [H*] -> C.Typo;',
            '    }',
            '    [*] -> Off;',
            '    Off -> O.[H*] :: Go;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n');
        const unreachable = (await packageModule.collectDocumentDiagnostics(document(text)))
            .filter(item => item.code === 'W_UNREACHABLE_STATE')
            .map(item => /State "([^"]+)"/.exec(item.message)![1]);
        assert.ok(unreachable.includes('Host.O.C.X'), unreachable.join(','));
    });

    it('uses the first valid declaration of a kind for reachability, as pyfcstm does', async () => {
        const unreachable = async (lines: string[]) => (await packageModule.collectDocumentDiagnostics(document(lines.join('\n'))))
            .filter(item => item.code === 'W_UNREACHABLE_STATE')
            .map(item => /State "([^"]+)"/.exec(item.message)![1])
            .sort();
        const shell = (body: string, kind: string) => [
            'state Host {',
            '    state Off;',
            `    state O { state A; state Z; pseudo state P; state C { state X; [*] -> X; } [*] -> A; ${body} }`,
            '    [*] -> Off;',
            `    Off -> O.${kind} :: Go;`,
            '    !O -> Off :: Stop;',
            '}',
        ];
        // a shallow default names one child, so the second declaration is kept
        assert.deepEqual(await unreachable(shell('[H] -> C.X; [H] -> Z;', '[H]')), ['Host.O.C', 'Host.O.C.X', 'Host.O.P']);
        // a default never names a pseudo state
        assert.deepEqual(await unreachable(shell('[H*] -> P; [H*] -> C.X;', '[H*]')), ['Host.O.P', 'Host.O.Z']);
    });

    it('leaves a default that enters an imported module to the assembled model', async () => {
        const text = [
            'state Host {',
            '    state Off;',
            '    state O {',
            '        state A;',
            '        import "./module.fcstm" as M;',
            '        [*] -> A;',
            '        [H*] -> M.B;',
            '    }',
            '    [*] -> Off;',
            '    Off -> O.[H*] :: Deep;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n');
        const codes = (await packageModule.collectDocumentDiagnostics(document(text))).map(item => item.code ?? '');
        assert.deepEqual(codes.filter(code => code.includes('HISTORY')), []);
    });

    it('keeps reporting when a history entry leaves an unknown source', async () => {
        const text = [
            'state R {',
            '    state Off;',
            '    import "./module.fcstm" as M;',
            '    state O { state A; state B; [*] -> A; [H] -> B; }',
            '    [*] -> Off;',
            '    Of -> O.[H] :: Resume;',
            '    M -> O.[H] :: Back;',
            '    !O -> Off :: Stop;',
            '}',
        ].join('\n');
        const codes = (await packageModule.collectDocumentDiagnostics(document(text))).map(item => item.code);
        assert.ok(codes.includes('E_MISSING_STATE'), codes.join(','));
    });

    it('points declaration errors at the declaration', async () => {
        const text = HISTORY_DIAGNOSTIC_CASES['default-not-direct-child'].source;
        const doc = document(text);
        const [item] = (await packageModule.collectDocumentDiagnostics(doc))
            .filter(entry => entry.code === 'E_HISTORY_DECLARATION_INVALID');
        const line = text.split('\n')[item.range.start.line];
        assert.ok(line.slice(item.range.start.character).startsWith('[H] -> W.W1;'));
    });
});

function canonical(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
    if (value !== null && typeof value === 'object') {
        return `{${Object.keys(value).sort().map(name => `${JSON.stringify(name)}:${canonical((value as Record<string, unknown>)[name])}`).join(',')}}`;
    }
    return JSON.stringify(value);
}

describe('jsfcstm history inspect', () => {
    for (const [name, testCase] of Object.entries(HISTORY_MODEL_CASES)) {
        it(`builds the same initial targets and unconditional-entry findings as pyfcstm for ${name}`, async () => {
            const report = packageModule.inspectModel(await model(testCase.source));
            const targets = Object.fromEntries(
                report.states.filter(state => state.initial_targets.length > 0).map(state => [state.path, state.initial_targets]),
            );
            assert.deepEqual(targets, testCase.initial_targets);
            if (testCase.transitions) {
                // The model as written: no lowered edge, history entries marked.
                assert.deepEqual(
                    report.transitions.map(t => ({
                        from_path: t.from_path, to_path: t.to_path, event: t.event, guard: t.guard, effect: t.effect,
                        transition_index: t.transition_index, target_history: t.target_history,
                    })),
                    testCase.transitions,
                );
                assert.deepEqual(report.reachability_graph[report.root_state_path], testCase.root_reachable);
                assert.deepEqual(report.metrics, testCase.metrics);
                assert.deepEqual(
                    report.diagnostics.map(item => canonical({code: item.code, refs: item.refs})).sort(),
                    testCase.findings!.map(canonical).sort(),
                );
            }
            assert.deepEqual(
                report.diagnostics
                    .filter(item => item.code === 'W_INITIAL_UNCONDITIONAL_MISSING')
                    .map(item => Object.fromEntries(
                        ['composite_path', 'existing_conditional_count', 'first_child_name']
                            .filter(key => key in item.refs)
                            .map(key => [key, item.refs[key]]),
                    )),
                testCase.unconditional_missing,
            );
        });
    }
});

describe('jsfcstm history editor support', () => {
    it('offers history markers at the start of a composite body', async () => {
        const text = 'state R {\n    state A;\n    \n}';
        const items = await packageModule.collectCompletionItems(document(text), {line: 2, character: 4});
        assert.ok(items.some(item => item.label === '[H]' && item.kind === 'keyword'));
        assert.ok(items.some(item => item.label === '[H*]'));
    });

    it('offers history markers after an opening bracket', async () => {
        const text = 'state R {\n    state A;\n    [\n}';
        const items = await packageModule.collectCompletionItems(document(text), {line: 2, character: 5});
        assert.deepEqual(items.map(item => item.label).sort(), ['[*]', '[H*]', '[H]']);
    });

    it('offers the markers a target state declares after its name', async () => {
        const lines = WASHER.split('\n');
        const line = lines.findIndex(item => item.includes('Paused -> Program.[H] :: Shallow;'));
        const edited = [...lines];
        edited[line] = '    Paused -> Program.';
        const items = await packageModule.collectCompletionItems(document(edited.join('\n')), {
            line,
            character: edited[line].length,
        });
        assert.deepEqual(items.map(item => item.label).sort(), ['[H*]', '[H]']);

        edited[line] = '    Paused -> Program.[H';
        const partial = await packageModule.collectCompletionItems(document(edited.join('\n')), {
            line,
            character: edited[line].length,
        });
        assert.ok(partial.some(item => item.label === '[H]'));

        edited[line] = '    Paused -> Paused.';
        const leaf = await packageModule.collectCompletionItems(document(edited.join('\n')), {
            line,
            character: edited[line].length,
        });
        assert.deepEqual(leaf, []);

        edited[line] = '    Paused -> Nowhere.';
        const unknown = await packageModule.collectCompletionItems(document(edited.join('\n')), {
            line,
            character: edited[line].length,
        });
        assert.deepEqual(unknown.map(item => item.label).sort(), ['[H*]', '[H]']);

        const outside = await packageModule.collectCompletionItems(document('A -> B.'), {line: 0, character: 7});
        assert.deepEqual(outside.map(item => item.label).sort(), ['[H*]', '[H]']);
    });

    it('treats a history target as one target when completing its trigger', async () => {
        const text = 'state R {\n    state A;\n    state O { state B; [*] -> B; [H] -> B; }\n    [*] -> A;\n    A -> O.[H] :: \n}';
        const items = await packageModule.collectCompletionItems(document(text), {line: 4, character: 18});
        assert.ok(!items.some(item => item.label === '[H]'));
        const after = 'state R {\n    state A;\n    state O { state B; [*] -> B; [H] -> B; }\n    [*] -> A;\n    A -> O.[H] \n}';
        const next = await packageModule.collectCompletionItems(document(after), {line: 4, character: 15});
        assert.ok(next.some(item => item.label === 'effect' || item.label === '::'));
    });

    it('documents the markers on hover', () => {
        const line = '    Paused -> Program.[H*] :: Deep; Other -> Program.[H] :: Shallow;';
        assert.equal(packageModule.findHoverInfo(line, line.indexOf('[H*]') + 1, '')?.title, 'Deep History');
        assert.equal(packageModule.findHoverInfo(line, line.indexOf('[H]') + 2, '')?.title, 'Shallow History');
        assert.equal(packageModule.findHoverInfo('    [*] -> A;', 5, '')?.title, 'Pseudo-State Marker');
    });

    it('colours the markers as operators', async () => {
        const text = 'state R {\n    state O { state A; [*] -> A; [H*] -> A; }\n    [*] -> O.[H*];\n}';
        const tokens = await packageModule.collectSemanticTokens(document(text));
        const legend = packageModule.getFcstmSemanticTokensLegend();
        let line = 0;
        let character = 0;
        const operators: string[] = [];
        for (let index = 0; index < tokens.data.length; index += 5) {
            line += tokens.data[index];
            character = tokens.data[index] === 0 ? character + tokens.data[index + 1] : tokens.data[index + 1];
            if (legend.tokenTypes[tokens.data[index + 3]] === 'operator') {
                operators.push(text.split('\n')[line].substr(character, tokens.data[index + 2]));
            }
        }
        assert.equal(operators.filter(item => item === '[H*]').length, 2);
    });

    it('formats history markers as single tokens', () => {
        const source = [
            'def int H = 0;',
            'state R {',
            'state O {state A;[*]->A;',
            '/* resume */',
            '[H]->A;[H*]  ->  A;}',
            '[*] -> O.[H];',
            'state B;',
            'B->O.[H*]::Go;',
            'B->B : if [H>1];',
            '}',
            '',
        ].join('\n');
        const [edit] = packageModule.formatDocumentText(document(source));
        assert.equal(edit.newText, [
            'def int H = 0;',
            'state R {',
            '    state O {',
            '        state A;',
            '        [*] -> A;',
            '        /*',
            '         * resume',
            '         */',
            '        [H] -> A;',
            '        [H*] -> A;',
            '    }',
            '    [*] -> O.[H];',
            '    state B;',
            '    B -> O.[H*] :: Go;',
            '    B -> B : if [H > 1];',
            '}',
            '',
        ].join('\n'));
    });

    it('only treats a comment before a complete marker statement as its documentation', () => {
        for (const source of ['state R;\n/* tail */\n', 'state R {\n    state A;\n    [*] -> A;\n}\n/* tail */ [H]']) {
            const [edit] = packageModule.formatDocumentText(document(source));
            assert.ok((edit?.newText ?? source).includes('/* tail */'));
        }
    });

    it('lists history declarations and history targets in the outline', async () => {
        const symbols = await packageModule.collectDocumentSymbols(document(WASHER));
        const flatten = (items: typeof symbols): typeof symbols => items.flatMap(item => [item, ...flatten(item.children)]);
        const names = flatten(symbols).map(item => item.name);
        assert.ok(names.includes('[H] -> Idle'));
        assert.ok(names.includes('[H*] -> Wash.Fill'));
        assert.ok(names.includes('Paused -> Program.[H] :: Shallow'));
        assert.ok(names.includes('Paused -> Program.[H*] :: Deep'));
        const deep = flatten(symbols).find(item => item.name === '[H*] -> Wash.Fill')!;
        assert.equal(deep.detail, 'deep history');
    });

    it('resolves the state named by a history target', async () => {
        const doc = document(WASHER);
        const line = WASHER.split('\n').findIndex(item => item.includes('Program.[H*] :: Deep'));
        const definition = await packageModule.resolveDefinitionLocation(doc, {
            line,
            character: charOf(WASHER, line, 'Program.[H*]') + 2,
        });
        assert.ok(definition);
        const programLine = WASHER.split('\n').findIndex(item => item.includes('state Program'));
        assert.equal(definition.range.start.line, programLine);
    });
});
