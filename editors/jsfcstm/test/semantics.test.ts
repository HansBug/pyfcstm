import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

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
});
