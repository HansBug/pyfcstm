import assert from 'node:assert/strict';

import type * as ModelModule from '@pyfcstm/jsfcstm/model';
import {createDocument, packageModule} from './support';

const modelModule = require('@pyfcstm/jsfcstm/model') as typeof ModelModule;
const ZERO_RANGE = {
    start: {line: 0, character: 0},
    end: {line: 0, character: 0},
} as const;

function normalizeTransition(transition: {
    fromState: string;
    toState: string;
    event?: {path_name: string};
    parentPath: string[];
}): {
    fromState: string;
    toState: string;
    event: string | null;
    parent: string;
} {
    return {
        fromState: transition.fromState,
        toState: transition.toState,
        event: transition.event?.path_name || null,
        parent: transition.parentPath.join('.'),
    };
}

function createRawLeafState(name: string, path: string[]) {
    return {
        kind: 'state',
        pyModelType: 'State',
        range: ZERO_RANGE,
        text: `state ${name};`,
        name,
        path,
        pathName: path.join('.'),
        path_name: path.join('.'),
        substates: {},
        events: {},
        transitions: [],
        namedFunctions: {},
        named_functions: {},
        onEnters: [],
        on_enters: [],
        onDurings: [],
        on_durings: [],
        onExits: [],
        on_exits: [],
        onDuringAspects: [],
        on_during_aspects: [],
        parentPath: path.slice(0, -1),
        parent_path: path.slice(0, -1),
        substateNameToId: {},
        substate_name_to_id: {},
        extraName: undefined,
        extra_name: undefined,
        isPseudo: false,
        is_pseudo: false,
        isLeafState: true,
        is_leaf_state: true,
        isRootState: false,
        is_root_state: false,
        isStoppable: true,
        is_stoppable: true,
    };
}

function createHydrationRawStateMachine() {
    const rawInteger = {
        kind: 'integer',
        pyModelType: 'Integer',
        range: ZERO_RANGE,
        text: '1',
        value: 1,
    };
    const rawEvent = {
        kind: 'event',
        pyModelType: 'Event',
        range: ZERO_RANGE,
        text: 'Tick',
        name: 'Tick',
        statePath: ['Root'],
        state_path: ['Root'],
        path: ['Root', 'Tick'],
        pathName: 'Root.Tick',
        path_name: 'Root.Tick',
        extraName: undefined,
        extra_name: undefined,
        declared: true,
        origins: ['declared'],
    };
    const rawOperation = {
        kind: 'operation',
        pyModelType: 'Operation',
        range: ZERO_RANGE,
        text: 'counter = 1;',
        varName: 'counter',
        var_name: 'counter',
        expr: rawInteger,
    };
    const rawBranch = {
        kind: 'ifBlockBranch',
        pyModelType: 'IfBlockBranch',
        range: ZERO_RANGE,
        text: 'else { counter = 1; }',
        condition: null,
        statements: [rawOperation],
    };
    const rawIfBlock = {
        kind: 'ifBlock',
        pyModelType: 'IfBlock',
        range: ZERO_RANGE,
        text: 'if [true] { counter = 1; } else { counter = 1; }',
        branches: [rawBranch, rawBranch],
    };
    const rawAction = {
        kind: 'onStage',
        pyModelType: 'OnStage',
        range: ZERO_RANGE,
        text: 'enter Init { counter = 1; }',
        stage: 'enter',
        aspect: undefined,
        name: 'Init',
        doc: undefined,
        operations: [rawOperation, rawIfBlock],
        isAbstract: false,
        is_abstract: false,
        isRef: false,
        is_ref: false,
        isAspect: false,
        is_aspect: false,
        mode: 'operations',
        statePath: ['Root', 'Init'],
        state_path: ['Root', 'Init'],
        funcName: 'Root.Init',
        func_name: 'Root.Init',
        parentPath: ['Root'],
        parent_path: ['Root'],
        refStatePath: undefined,
        ref_state_path: undefined,
        refResolved: false,
        ref_resolved: false,
        refTargetQualifiedName: undefined,
        ref_target_qualified_name: undefined,
    };
    const sharedState = createRawLeafState('Shared', ['Root', 'Shared']);
    const rawTransition = {
        kind: 'transition',
        pyModelType: 'Transition',
        range: ZERO_RANGE,
        text: '[*] -> Shared : Tick;',
        fromState: 'INIT_STATE',
        from_state: 'INIT_STATE',
        toState: 'Shared',
        to_state: 'Shared',
        event: rawEvent,
        guard: undefined,
        effects: [rawOperation],
        parentPath: ['Root'],
        parent_path: ['Root'],
        sourceStatePath: undefined,
        source_state_path: undefined,
        targetStatePath: ['Root', 'Shared'],
        target_state_path: ['Root', 'Shared'],
        sourceKind: 'init',
        targetKind: 'state',
        transitionKind: 'entry',
        forced: false,
        declaredInStatePath: ['Root'],
        declared_in_state_path: ['Root'],
        triggerScope: 'chain',
        trigger_scope: 'chain',
    };
    const rawRootState = {
        kind: 'state',
        pyModelType: 'State',
        range: ZERO_RANGE,
        text: 'state Root { }',
        name: 'Root',
        path: ['Root'],
        pathName: 'Root',
        path_name: 'Root',
        substates: {
            Shared: sharedState,
            SharedAlias: sharedState,
        },
        events: {
            Tick: rawEvent,
        },
        transitions: [rawTransition],
        namedFunctions: {
            Init: rawAction,
        },
        named_functions: {
            Init: rawAction,
        },
        onEnters: [rawAction],
        on_enters: [rawAction],
        onDurings: [],
        on_durings: [],
        onExits: [],
        on_exits: [],
        onDuringAspects: [],
        on_during_aspects: [],
        parentPath: undefined,
        parent_path: undefined,
        substateNameToId: {
            Shared: 0,
            SharedAlias: 1,
        },
        substate_name_to_id: {
            Shared: 0,
            SharedAlias: 1,
        },
        extraName: undefined,
        extra_name: undefined,
        isPseudo: false,
        is_pseudo: false,
        isLeafState: false,
        is_leaf_state: false,
        isRootState: true,
        is_root_state: true,
        isStoppable: false,
        is_stoppable: false,
    };

    return {
        kind: 'stateMachine',
        pyModelType: 'StateMachine',
        range: ZERO_RANGE,
        text: 'state Root { }',
        filePath: '/tmp/raw-model.fcstm',
        defines: {},
        rootState: rawRootState,
        root_state: rawRootState,
        allStates: [rawRootState, sharedState],
        all_states: [rawRootState, sharedState],
        allEvents: [rawEvent],
        all_events: [rawEvent],
        allTransitions: [rawTransition],
        all_transitions: [rawTransition],
        allActions: [rawAction],
        all_actions: [rawAction],
        lookups: {
            definesByName: {},
            statesByPath: {
                Root: rawRootState,
                'Root.Shared': sharedState,
            },
            eventsByPathName: {
                'Root.Tick': rawEvent,
            },
            namedFunctionsByPath: {
                'Root.Init': rawAction,
            },
            transitionsByParentPath: {
                Root: [rawTransition],
            },
        },
    };
}

describe('jsfcstm state-machine model', () => {
    it('builds a pyfcstm-aligned model with implicit events, forced transitions, and refs', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Parent {',
            '        event Tick;',
            '        enter Setup { counter = 1; }',
            '        state A;',
            '        state B;',
            '        state Nested {',
            '            state Leaf;',
            '            [*] -> Leaf;',
            '        }',
            '        [*] -> A : /Boot;',
            '        A -> B :: Go;',
            '        B -> A : Tick;',
            '        !Nested -> [*] : /Shutdown;',
            '    }',
            '    state UsesRef {',
            '        enter ref /Parent.Setup;',
            '    }',
            '    [*] -> Parent;',
            '}',
        ].join('\n'), '/tmp/model.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const model = packageModule.buildStateMachineModel(ast);
        const subpathModel = modelModule.buildStateMachineModelFromAst(ast);

        assert.ok(model);
        assert.ok(subpathModel);
        assert.equal(subpathModel?.rootState.name, 'Root');

        assert.deepEqual(Object.keys(model?.defines || {}), ['counter']);
        assert.equal(model?.defines.counter.type, 'int');
        assert.equal(model?.defines.counter.init.pyModelType, 'Integer');
        assert.equal((model?.defines.counter.init as {value: number}).value, 0);

        const rootState = model?.rootState;
        assert.ok(rootState);
        assert.deepEqual(rootState?.substate_name_to_id, {Parent: 0, UsesRef: 1});
        assert.deepEqual(Object.keys(rootState?.events || {}).sort(), ['Boot', 'Shutdown']);
        assert.deepEqual(rootState?.transitions.map(normalizeTransition), [
            {
                fromState: 'INIT_STATE',
                toState: 'Parent',
                event: null,
                parent: 'Root',
            },
        ]);

        const parent = rootState?.substates.Parent;
        assert.ok(parent);
        assert.deepEqual(parent?.substate_name_to_id, {A: 0, B: 1, Nested: 2});
        assert.deepEqual(Object.keys(parent?.events || {}), ['Tick']);
        assert.deepEqual(parent?.transitions.map(normalizeTransition), [
            {
                fromState: 'Nested',
                toState: 'EXIT_STATE',
                event: 'Root.Shutdown',
                parent: 'Root.Parent',
            },
            {
                fromState: 'INIT_STATE',
                toState: 'A',
                event: 'Root.Boot',
                parent: 'Root.Parent',
            },
            {
                fromState: 'A',
                toState: 'B',
                event: 'Root.Parent.A.Go',
                parent: 'Root.Parent',
            },
            {
                fromState: 'B',
                toState: 'A',
                event: 'Root.Parent.Tick',
                parent: 'Root.Parent',
            },
        ]);

        const nested = parent?.substates.Nested;
        assert.ok(nested);
        assert.deepEqual(nested?.transitions.map(normalizeTransition), [
            {
                fromState: 'Leaf',
                toState: 'EXIT_STATE',
                event: 'Root.Shutdown',
                parent: 'Root.Parent.Nested',
            },
            {
                fromState: 'INIT_STATE',
                toState: 'Leaf',
                event: null,
                parent: 'Root.Parent.Nested',
            },
        ]);

        const refAction = rootState?.substates.UsesRef.onEnters[0];
        assert.ok(refAction);
        assert.deepEqual(refAction?.ref_state_path, ['Root', 'Parent', 'Setup']);
        assert.equal(refAction?.ref_resolved, true);
        assert.equal(refAction?.ref_target_qualified_name, 'Root.Parent.Setup');
        assert.equal(parent?.onEnters[0].func_name, 'Root.Parent.Setup');
        assert.equal(model?.lookups.namedFunctionsByPath['Root.Parent.Setup'], parent?.onEnters[0]);
        assert.equal(model?.lookups.eventsByPathName['Root.Shutdown'], rootState?.events.Shutdown);
    });

    it('normalizes operation blocks and math constants into the stable model layer', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def float temperature = 25.0;',
            'state Root {',
            '    enter Init {',
            '        counter = 1;',
            '        if [counter > 0] {',
            '            temperature = sin(pi);',
            '        } else {',
            '            temperature = 0.0;',
            '        }',
            '    }',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [counter > 0 && temperature >= 20.0] effect {',
            '        value = counter + 1;',
            '        counter = value;',
            '    }',
            '}',
        ].join('\n'), '/tmp/model-ops.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const model = modelModule.buildStateMachineModel(ast);

        assert.ok(model);
        const initAction = model?.rootState.onEnters[0];
        assert.ok(initAction);
        assert.equal(initAction?.name, 'Init');
        assert.equal(initAction?.operations.length, 2);
        assert.equal(initAction?.operations[0].pyModelType, 'Operation');
        assert.equal((initAction?.operations[0] as {var_name: string}).var_name, 'counter');
        assert.equal((initAction?.operations[0] as {expr: {value: number}}).expr.value, 1);

        const ifBlock = initAction?.operations[1];
        assert.equal(ifBlock?.pyModelType, 'IfBlock');
        assert.equal((ifBlock as {branches: unknown[]}).branches.length, 2);

        const firstBranch = (ifBlock as {
            branches: Array<{
                condition: {pyModelType: string; op: string; x: {name: string}; y: {value: number}};
                statements: Array<{expr: {pyModelType: string; func: string; x: {pyModelType: string; value: number}}}>;
            }>;
        }).branches[0];
        assert.equal(firstBranch.condition.pyModelType, 'BinaryOp');
        assert.equal(firstBranch.condition.op, '>');
        assert.equal(firstBranch.condition.x.name, 'counter');
        assert.equal(firstBranch.condition.y.value, 0);
        assert.equal(firstBranch.statements[0].expr.pyModelType, 'UFunc');
        assert.equal(firstBranch.statements[0].expr.func, 'sin');
        assert.equal(firstBranch.statements[0].expr.x.pyModelType, 'Float');
        assert.equal(firstBranch.statements[0].expr.x.value, Math.PI);

        const elseBranch = (ifBlock as {
            branches: Array<{condition: unknown; statements: Array<{expr: {pyModelType: string; value: number}}>}>;
        }).branches[1];
        assert.equal(elseBranch.condition, null);
        assert.equal(elseBranch.statements[0].expr.pyModelType, 'Float');
        assert.equal(elseBranch.statements[0].expr.value, 0);

        const transition = model?.rootState.transitions.find(item => item.fromState === 'Idle');
        assert.ok(transition);
        assert.equal(transition?.guard?.pyModelType, 'BinaryOp');
        assert.equal((transition?.guard as {op: string}).op, '&&');

        const leftGuard = (transition?.guard as {
            x: {pyModelType: string; op: string; x: {name: string}; y: {value: number}};
            y: {pyModelType: string; op: string; x: {name: string}; y: {value: number}};
        }).x;
        assert.equal(leftGuard.pyModelType, 'BinaryOp');
        assert.equal(leftGuard.op, '>');
        assert.equal(leftGuard.x.name, 'counter');
        assert.equal(leftGuard.y.value, 0);

        const rightGuard = (transition?.guard as {
            x: unknown;
            y: {pyModelType: string; op: string; x: {name: string}; y: {value: number}};
        }).y;
        assert.equal(rightGuard.pyModelType, 'BinaryOp');
        assert.equal(rightGuard.op, '>=');
        assert.equal(rightGuard.x.name, 'temperature');
        assert.equal(rightGuard.y.value, 20);

        assert.deepEqual(transition?.effects.map(effect => ({
            type: effect.pyModelType,
            varName: (effect as {var_name?: string}).var_name || null,
            exprType: (effect as {expr?: {pyModelType: string}}).expr?.pyModelType || null,
        })), [
            {type: 'Operation', varName: 'value', exprType: 'BinaryOp'},
            {type: 'Operation', varName: 'counter', exprType: 'Variable'},
        ]);
    });

    it('supports semantic-input building and tolerates unresolved references without throwing', async () => {
        const document = createDocument([
            'state Root {',
            '    enter { ; }',
            '    exit ref MissingHook;',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> MissingState : /Boot;',
            '}',
        ].join('\n'), '/tmp/model-semantic.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const semantic = packageModule.buildSemanticDocument(ast);
        const model = modelModule.buildStateMachineModelFromSemantic(semantic);

        assert.ok(model);
        assert.equal(model?.rootState.onEnters[0].operations.length, 0);
        assert.deepEqual(model?.rootState.onEnters[0].state_path, ['Root', null]);
        assert.equal(model?.rootState.onExits[0].ref_resolved, false);
        assert.deepEqual(model?.rootState.onExits[0].ref_state_path, ['Root', 'MissingHook']);

        const transition = model?.rootState.transitions.find(item => item.fromState === 'A');
        assert.ok(transition);
        assert.equal(transition?.targetStatePath, undefined);
        assert.equal(transition?.target_state_path, undefined);
        assert.equal(transition?.event?.path_name, 'Root.Boot');
        assert.deepEqual(model?.lookups.transitionsByParentPath.Root, model?.rootState.transitions);

        assert.equal(modelModule.buildStateMachineModel(null), null);
        assert.equal(modelModule.buildStateMachineModelFromAst(null), null);
        assert.equal(modelModule.buildStateMachineModelFromSemantic(null), null);
    });

    it('covers boolean, unary, conditional, and parenthesized expression normalization', async () => {
        const document = createDocument([
            'def int value = 0;',
            'state Root {',
            '    enter Evaluate {',
            '        value = ((!false && true) ? round(tau) : (1 + 2));',
            '    }',
            '}',
        ].join('\n'), '/tmp/model-expr.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const model = modelModule.buildStateMachineModel(ast);

        assert.ok(model);
        const operation = model?.rootState.onEnters[0].operations[0] as {
            expr: {
                pyModelType: string;
                cond: {
                    pyModelType: string;
                    op: string;
                    x: {pyModelType: string; op: string; x: {pyModelType: string; value: boolean}};
                    y: {pyModelType: string; value: boolean};
                };
                ifTrue: {pyModelType: string; func: string; x: {pyModelType: string; value: number}};
                ifFalse: {pyModelType: string; op: string; x: {value: number}; y: {value: number}};
            };
        };

        assert.equal(operation.expr.pyModelType, 'ConditionalOp');
        assert.equal(operation.expr.cond.pyModelType, 'BinaryOp');
        assert.equal(operation.expr.cond.op, '&&');
        assert.equal(operation.expr.cond.x.pyModelType, 'UnaryOp');
        assert.equal(operation.expr.cond.x.op, '!');
        assert.equal(operation.expr.cond.x.x.pyModelType, 'Boolean');
        assert.equal(operation.expr.cond.x.x.value, false);
        assert.equal(operation.expr.cond.y.pyModelType, 'Boolean');
        assert.equal(operation.expr.cond.y.value, true);
        assert.equal(operation.expr.ifTrue.pyModelType, 'UFunc');
        assert.equal(operation.expr.ifTrue.func, 'round');
        assert.equal(operation.expr.ifTrue.x.pyModelType, 'Float');
        assert.equal(operation.expr.ifTrue.x.value, Math.PI * 2);
        assert.equal(operation.expr.ifFalse.pyModelType, 'BinaryOp');
        assert.equal(operation.expr.ifFalse.op, '+');
        assert.equal(operation.expr.ifFalse.x.value, 1);
        assert.equal(operation.expr.ifFalse.y.value, 2);
    });

    it('hydrates cached raw nodes consistently across shared references', () => {
        const model = modelModule.hydrateStateMachine(createHydrationRawStateMachine() as never);

        assert.equal(model.rootState.substates.Shared, model.rootState.substates.SharedAlias);
        assert.equal(model.rootState.substates.Shared.parent, model.rootState);
        assert.equal(model.rootState.onEnters[0], model.lookups.namedFunctionsByPath['Root.Init']);
        assert.equal(model.rootState.onEnters[0].operations[0], model.rootState.transitions[0].effects[0]);
        assert.equal(
            (model.rootState.onEnters[0].operations[1] as {branches: unknown[]}).branches[0],
            (model.rootState.onEnters[0].operations[1] as {branches: unknown[]}).branches[1]
        );
    });

    it('throws on unsupported raw expression kinds during hydration', () => {
        const raw = createHydrationRawStateMachine() as {
            defines: Record<string, unknown>;
        };
        raw.defines.bad = {
            kind: 'varDefine',
            pyModelType: 'VarDefine',
            range: ZERO_RANGE,
            text: 'def int bad = ???;',
            name: 'bad',
            type: 'int',
            init: {
                kind: 'mystery',
                pyModelType: 'Variable',
                range: ZERO_RANGE,
                text: '???',
                name: 'mystery',
            },
        };

        assert.throws(
            () => modelModule.hydrateStateMachine(raw as never),
            /Unsupported raw expression kind: mystery/
        );
    });

    it('resolves event references from state and machine helpers and validates bad paths', async () => {
        const document = createDocument([
            'state Root {',
            '    event Global;',
            '    state Parent {',
            '        event ParentEvent;',
            '        state Child {',
            '            event LocalEvent;',
            '        }',
            '        [*] -> Child;',
            '    }',
            '    [*] -> Parent;',
            '}',
        ].join('\n'), '/tmp/model-events.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const model = modelModule.buildStateMachineModel(ast);

        assert.ok(model);
        const child = model!.rootState.substates.Parent.substates.Child;
        assert.equal(child.resolve_event('/Global').path_name, 'Root.Global');
        assert.equal(child.resolve_event('.ParentEvent').path_name, 'Root.Parent.ParentEvent');
        assert.equal(child.resolve_event('LocalEvent').path_name, 'Root.Parent.Child.LocalEvent');
        assert.equal(model!.resolve_event('Root.Parent.ParentEvent').path_name, 'Root.Parent.ParentEvent');

        assert.throws(() => model!.resolve_event(''), /Event path cannot be empty/);
        assert.throws(
            () => model!.resolve_event('Other.ParentEvent'),
            /does not match state machine root/
        );
        assert.throws(() => model!.resolve_event('Root.Parent.Missing'), /Event "Missing" not found/);

        assert.throws(() => child.resolve_event('/'), /cannot be just/);
        assert.throws(() => child.resolve_event('Bad..Path'), /Invalid relative event reference/);
        assert.throws(() => child.resolve_event('...ParentEvent'), /goes beyond root state/);
        assert.throws(() => child.resolve_event('/Parent.Missing'), /Event "Missing" not found in state "Root.Parent"/);
    });
});
