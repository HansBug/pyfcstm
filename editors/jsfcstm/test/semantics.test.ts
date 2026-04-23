import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

function range() {
    return packageModule.createRange(0, 0, 0, 1);
}

describe('jsfcstm semantic model', () => {
    it('normalizes local, chain, absolute, ref, and forced-transition semantics', async () => {
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
            '        }',
            '        [*] -> A : /Boot;',
            '        A -> B :: Go;',
            '        B -> A : Tick;',
            '        !Nested -> [*] : /Shutdown;',
            '    }',
            '    state UsesRef {',
            '        enter ref /Parent.Setup;',
            '    }',
            '}',
        ].join('\n'), '/tmp/semantic.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const semantic = packageModule.buildSemanticDocument(ast);
        assert.ok(semantic);

        const statePaths = semantic?.states.map(item => item.identity.qualifiedName).sort();
        assert.deepEqual(statePaths, [
            'Root',
            'Root.Parent',
            'Root.Parent.A',
            'Root.Parent.B',
            'Root.Parent.Nested',
            'Root.Parent.Nested.Leaf',
            'Root.UsesRef',
        ]);

        const localEvent = semantic?.events.find(item => item.identity.qualifiedName === 'Root.Parent.A.Go');
        assert.ok(localEvent);
        assert.deepEqual(localEvent?.origins, ['local']);

        const chainEvent = semantic?.events.find(item => item.identity.qualifiedName === 'Root.Parent.Tick');
        assert.ok(chainEvent);
        assert.equal(chainEvent?.declared, true);
        assert.ok(chainEvent?.origins.includes('declared'));
        assert.ok(chainEvent?.origins.includes('chain'));

        const absoluteEvents = semantic?.events
            .filter(item => item.origins.includes('absolute'))
            .map(item => item.absolutePathText)
            .sort();
        assert.deepEqual(absoluteEvents, ['/Boot', '/Shutdown']);
        assert.deepEqual(semantic?.summary.absoluteEvents.sort(), ['/Boot', '/Shutdown']);

        const refAction = semantic?.actions.find(item => item.ownerStatePath.join('.') === 'Root.UsesRef');
        assert.ok(refAction?.ref);
        assert.equal(refAction?.ref?.resolved, true);
        assert.equal(refAction?.ref?.targetQualifiedName, 'Root.Parent.Setup');

        const forcedTransition = semantic?.transitions.find(item => item.transitionKind === 'exit');
        assert.ok(forcedTransition);
        assert.equal(forcedTransition?.forced, true);
        assert.equal(forcedTransition?.expandedTransitions.length, 2);
        assert.deepEqual(forcedTransition?.expandedTransitions.map(item => item.mode).sort(), [
            'direct',
            'exitToParent',
        ]);
        assert.deepEqual(forcedTransition?.expandedTransitions.map(item => item.sourceStatePath.join('.')).sort(), [
            'Root.Parent.Nested',
            'Root.Parent.Nested.Leaf',
        ]);

        const localTransition = semantic?.transitions.find(item => item.trigger?.scope === 'local');
        assert.equal(localTransition?.trigger?.qualifiedName, 'Root.Parent.A.Go');
        const chainTransition = semantic?.transitions.find(item => item.trigger?.scope === 'chain');
        assert.equal(chainTransition?.trigger?.qualifiedName, 'Root.Parent.Tick');
        const absoluteTransition = semantic?.transitions.find(item => item.trigger?.scope === 'absolute');
        assert.equal(absoluteTransition?.trigger?.qualifiedName, 'Root.Boot');
    });

    it('applies import def and event mappings deterministically', () => {
        assert.deepEqual(packageModule.applyImportDefMappings(
            ['sensor_temp', 'mode', 'keep'],
            [
                {
                    kind: 'importDefMapping',
                    range: packageModule.createRange(0, 0, 0, 1),
                    text: 'def sensor_* -> io_$1;',
                    selector: {
                        kind: 'importDefPatternSelector',
                        range: packageModule.createRange(0, 0, 0, 1),
                        text: 'sensor_*',
                        pattern: 'sensor_*',
                    },
                    targetTemplate: 'io_$1',
                },
                {
                    kind: 'importDefMapping',
                    range: packageModule.createRange(0, 0, 0, 1),
                    text: 'def * -> shared;',
                    selector: {
                        kind: 'importDefFallbackSelector',
                        range: packageModule.createRange(0, 0, 0, 1),
                        text: '*',
                    },
                    targetTemplate: 'shared',
                },
            ]
        ), ['io_temp', 'shared']);

        assert.deepEqual(packageModule.applyImportDefMappings(
            ['exact', 'left', 'keep'],
            [
                {
                    kind: 'importDefMapping',
                    range: range(),
                    text: 'def exact -> *;',
                    selector: {
                        kind: 'importDefExactSelector',
                        range: range(),
                        text: 'exact',
                        name: 'exact',
                    },
                    targetTemplate: '*',
                },
                {
                    kind: 'importDefMapping',
                    range: range(),
                    text: 'def {left,right} -> grouped;',
                    selector: {
                        kind: 'importDefSetSelector',
                        range: range(),
                        text: '{left,right}',
                        names: ['left', 'right'],
                    },
                    targetTemplate: 'grouped',
                },
                {
                    kind: 'importDefMapping',
                    range: range(),
                    text: 'def * -> keep;',
                    selector: {
                        kind: 'importDefFallbackSelector',
                        range: range(),
                        text: '*',
                    },
                    targetTemplate: 'keep',
                },
            ]
        ), ['exact', 'grouped', 'keep']);

        assert.deepEqual(packageModule.applyImportEventMappings(
            ['/Start', '/Stop'],
            [{
                kind: 'importEventMapping',
                range: packageModule.createRange(0, 0, 0, 1),
                text: 'event /Start -> /Bus.Start;',
                sourceEvent: {
                    kind: 'chainPath',
                    range: packageModule.createRange(0, 0, 0, 1),
                    text: '/Start',
                    isAbsolute: true,
                    segments: ['Start'],
                },
                targetEvent: {
                    kind: 'chainPath',
                    range: packageModule.createRange(0, 0, 0, 1),
                    text: '/Bus.Start',
                    isAbsolute: true,
                    segments: ['Bus', 'Start'],
                },
            }]
        ), ['/Bus.Start', '/Stop']);
    });

    it('resolves ancestor and global references while expanding all-state forced transitions', async () => {
        const document = createDocument([
            'def int value = 0;',
            'state Root {',
            '    state Shared {',
            '        enter GlobalHook { ; }',
            '        state Library {',
            '            state DeepTarget;',
            '        }',
            '    }',
            '    state A {',
            '        enter LocalSetup { ; }',
            '        state A1 {',
            '            enter ref LocalSetup;',
            '        }',
            '    }',
            '    state B {',
            '        state Inner {',
            '            enter ref GlobalHook;',
            '            state Branch {',
            '                state Active;',
            '                [*] -> Active;',
            '            }',
            '            [*] -> Branch;',
            '        }',
            '        state Leaf;',
            '        Inner -> DeepTarget :: Go effect { value = 1; }',
            '        Leaf -> Root;',
            '        !* -> [*] : /Shutdown;',
            '    }',
            '}',
        ].join('\n'), '/tmp/semantic-advanced.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const semantic = packageModule.buildSemanticDocument(ast);
        assert.ok(semantic);

        const localRef = semantic?.actions.find(action => action.ownerStatePath.join('.') === 'Root.A.A1');
        assert.equal(localRef?.ref?.resolved, true);
        assert.equal(localRef?.ref?.targetQualifiedName, 'Root.A.LocalSetup');

        const globalFallbackRef = semantic?.actions.find(action => action.ownerStatePath.join('.') === 'Root.B.Inner');
        assert.equal(globalFallbackRef?.ref?.resolved, true);
        assert.equal(globalFallbackRef?.ref?.targetQualifiedName, 'Root.Shared.GlobalHook');

        const transition = semantic?.transitions.find(item => item.effectText === 'value=1;');
        assert.ok(transition);
        assert.equal(transition?.trigger?.scope, 'local');
        assert.equal(transition?.targetStatePath?.join('.'), 'Root.Shared.Library.DeepTarget');

        const rootTransition = semantic?.transitions.find(item => item.targetStateName === 'Root');
        assert.equal(rootTransition?.targetStatePath?.join('.'), 'Root');

        const forcedTransition = semantic?.transitions.find(item => item.forced && item.sourceKind === 'all');
        assert.ok(forcedTransition);
        assert.deepEqual(
            forcedTransition?.expandedTransitions.map(item => [item.sourceStatePath.join('.'), item.mode]).sort(),
            [
                ['Root.B.Inner', 'direct'],
                ['Root.B.Inner.Branch.Active', 'exitToParent'],
                ['Root.B.Leaf', 'direct'],
            ]
        );
    });

    it('merges duplicate declared events into a single semantic event record', async () => {
        const document = createDocument([
            'state Root {',
            '    event Tick;',
            '    event Tick named "Tick Event";',
            '}',
        ].join('\n'), '/tmp/semantic-duplicate-event.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const semantic = packageModule.buildSemanticDocument(ast);
        const tickEvents = semantic?.events.filter(event => event.identity.qualifiedName === 'Root.Tick') || [];

        assert.equal(tickEvents.length, 1);
        assert.equal(tickEvents[0].displayName, 'Tick Event');
        assert.equal(tickEvents[0].declared, true);
        assert.deepEqual(tickEvents[0].origins, ['declared']);
        assert.equal(tickEvents[0].declarationAst?.displayName, 'Tick Event');
    });

    it('covers semantic fallback branches for missing refs and synthetic trigger shapes', () => {
        const ownerState = {
            kind: 'stateDefinition',
            pyNodeType: 'StateDefinition',
            range: range(),
            text: 'state Owner {}',
            name: 'Owner',
            pseudo: false,
            isPseudo: false,
            is_pseudo: false,
            composite: true,
            statements: [],
            events: [],
            imports: [],
            substates: [],
            transitions: [],
            enters: [],
            durings: [],
            exits: [],
            duringAspects: [],
            during_aspects: [],
            forceTransitions: [],
            force_transitions: [],
        };
        const rootState = {
            kind: 'stateDefinition',
            pyNodeType: 'StateDefinition',
            range: range(),
            text: 'state Root {}',
            name: 'Root',
            pseudo: false,
            isPseudo: false,
            is_pseudo: false,
            composite: true,
            statements: [ownerState],
            events: [],
            imports: [],
            substates: [ownerState],
            transitions: [],
            enters: [],
            durings: [],
            exits: [],
            duringAspects: [],
            during_aspects: [],
            forceTransitions: [],
            force_transitions: [],
        };
        const emptyPath = {
            kind: 'chainPath',
            pyNodeType: 'ChainID',
            range: range(),
            text: '',
            isAbsolute: false,
            is_absolute: false,
            segments: [],
            path: [],
        };
        const unresolvedRefAction = {
            kind: 'action',
            pyNodeType: 'EnterRefFunction',
            range: range(),
            text: 'enter ref ;',
            stage: 'enter',
            isGlobalAspect: false,
            mode: 'ref',
            operationsList: [],
            refPath: emptyPath,
            ref: emptyPath,
        };
        const localTriggerTransition = {
            kind: 'transition',
            pyNodeType: 'TransitionDefinition',
            range: range(),
            text: 'Owner -> [*] :: Wake;',
            transitionKind: 'normal',
            sourceKind: 'state',
            targetKind: 'exit',
            trigger: {
                kind: 'localTrigger',
                range: range(),
                text: '::Wake',
                eventName: 'Wake',
            },
            postOperations: [],
            post_operations: [],
        };
        const oddChainTransition = {
            kind: 'transition',
            pyNodeType: 'TransitionDefinition',
            range: range(),
            text: 'Owner -> [*] : Odd;',
            transitionKind: 'normal',
            sourceKind: 'init',
            targetKind: 'exit',
            trigger: {
                kind: 'chainTrigger',
                range: range(),
                text: ':Odd',
                eventPath: {
                    ...emptyPath,
                    text: 'Odd',
                },
            },
            postOperations: [],
            post_operations: [],
        };
        const missingForcedTransition = {
            kind: 'forcedTransition',
            pyNodeType: 'ForceTransitionDefinition',
            range: range(),
            text: '!Missing -> [*];',
            transitionKind: 'exit',
            sourceKind: 'state',
            sourceStateName: 'Missing',
            targetKind: 'exit',
            postOperations: [],
            post_operations: [],
        };
        const ast = {
            kind: 'document',
            pyNodeType: 'StateMachineDSLProgram',
            range: range(),
            text: 'state Root {}',
            filePath: '/tmp/semantic-fallback.fcstm',
            variables: [],
            definitions: [],
            rootState,
            root_state: rootState,
        };

        ownerState.statements.push(
            {kind: 'mysteryStatement', range: range(), text: '???'},
            unresolvedRefAction,
            localTriggerTransition,
            oddChainTransition,
            missingForcedTransition
        );
        ownerState.enters.push(unresolvedRefAction);
        ownerState.transitions.push(localTriggerTransition, oddChainTransition);
        ownerState.forceTransitions.push(missingForcedTransition);
        ownerState.force_transitions.push(missingForcedTransition);

        const semantic = packageModule.buildSemanticDocument(ast as unknown as packageModule.FcstmAstDocument);
        assert.ok(semantic);

        const unresolvedAction = semantic?.actions.find(action => action.ownerStatePath.join('.') === 'Root.Owner');
        assert.equal(unresolvedAction?.ref?.resolved, false);
        assert.equal(unresolvedAction?.ref?.targetQualifiedName, undefined);

        const localTransition = semantic?.transitions.find(item => item.trigger?.scope === 'local');
        assert.equal(localTransition?.trigger?.qualifiedName, 'Root.Owner.Wake');
        assert.equal(localTransition?.sourceStatePath, undefined);

        const oddTransition = semantic?.transitions.find(item => item.trigger?.rawText === 'Odd');
        assert.ok(oddTransition);
        assert.equal(oddTransition?.trigger?.qualifiedName, 'Root.Owner');

        const missingForced = semantic?.transitions.find(item => item.ast.text === '!Missing -> [*];');
        assert.deepEqual(missingForced?.expandedTransitions, []);
    });
});
