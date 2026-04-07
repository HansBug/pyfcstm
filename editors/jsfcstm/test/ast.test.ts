import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

describe('jsfcstm AST builder', () => {
    it('builds a structured AST for variables, actions, forced transitions, and imports', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def float temperature = 25.5;',
            'state Root named "System Root" {',
            '    event Start named "Start Event";',
            '    enter Init {',
            '        counter = counter + 1;',
            '        if [counter > 0] {',
            '            temperature = temperature + 1.0;',
            '        } else {',
            '            temperature = 0.0;',
            '        }',
            '    }',
            '    during before ref /Shared.Setup;',
            '    !* -> [*] : /Fault;',
            '    import "./worker.fcstm" as Worker named "Worker Module" {',
            '        def sensor_* -> io_$1;',
            '        event /Start -> /Bus.Start named "Bus Start";',
            '    }',
            '    pseudo state Junction;',
            '}',
        ].join('\n'), '/tmp/ast.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        assert.ok(ast);
        assert.equal(ast?.pyNodeType, 'StateMachineDSLProgram');
        assert.equal(ast?.definitions, ast?.variables);
        assert.equal(ast?.root_state, ast?.rootState);
        assert.equal(ast?.variables.length, 2);
        assert.deepEqual(ast?.variables.map(item => [item.name, item.valueType]), [
            ['counter', 'int'],
            ['temperature', 'float'],
        ]);
        assert.deepEqual(ast?.variables.map(item => [item.pyNodeType, item.deftype, item.expr.pyNodeType]), [
            ['DefAssignment', 'int', 'Integer'],
            ['DefAssignment', 'float', 'Float'],
        ]);
        assert.equal(ast?.rootState?.name, 'Root');
        assert.equal(ast?.rootState?.displayName, 'System Root');
        assert.equal(ast?.rootState?.pyNodeType, 'StateDefinition');
        assert.equal(ast?.rootState?.extra_name, 'System Root');
        assert.equal(ast?.rootState?.composite, true);
        assert.equal(ast?.rootState?.enters.length, 1);
        assert.equal(ast?.rootState?.durings.length, 1);
        assert.equal(ast?.rootState?.force_transitions.length, 1);
        assert.equal(ast?.rootState?.imports.length, 1);
        assert.equal(ast?.rootState?.substates.length, 1);

        const statements = ast?.rootState?.statements || [];
        const event = statements.find(item => item.kind === 'eventDefinition');
        assert.equal(event?.kind, 'eventDefinition');
        assert.equal(event?.displayName, 'Start Event');
        assert.equal(event?.pyNodeType, 'EventDefinition');
        assert.equal(event?.extra_name, 'Start Event');

        const enterAction = statements.find(item => item.kind === 'action' && item.stage === 'enter');
        assert.equal(enterAction?.kind, 'action');
        assert.equal(enterAction?.name, 'Init');
        assert.equal(enterAction?.pyNodeType, 'EnterOperations');
        assert.equal(enterAction?.operationsList, enterAction?.operations?.statements);
        assert.equal(enterAction?.operations?.statements.length, 2);
        const ifStatement = enterAction?.operations?.statements[1];
        assert.equal(ifStatement?.kind, 'ifStatement');
        assert.equal(ifStatement?.pyNodeType, 'OperationIf');
        assert.equal(ifStatement?.branches.length, 2);
        assert.equal(ifStatement?.branches[0].pyNodeType, 'OperationIfBranch');
        assert.equal(ifStatement?.branches[0].condition?.pyNodeType, 'BinaryOp');
        assert.equal(ifStatement?.branches[1].condition, null);
        assert.equal(ifStatement?.branches[1].statements.length, 1);
        assert.ok(ifStatement?.elseBlock);

        const refAction = statements.find(item => item.kind === 'action' && item.mode === 'ref');
        assert.equal(refAction?.kind, 'action');
        assert.equal(refAction?.refPath?.text, '/Shared.Setup');
        assert.equal(refAction?.pyNodeType, 'DuringRefFunction');
        assert.equal(refAction?.ref, refAction?.refPath);
        assert.equal(refAction?.aspect, 'before');

        const forcedTransition = statements.find(item => item.kind === 'forcedTransition');
        assert.equal(forcedTransition?.kind, 'forcedTransition');
        assert.equal(forcedTransition?.pyNodeType, 'ForceTransitionDefinition');
        assert.equal(forcedTransition?.transitionKind, 'exitAll');
        assert.equal(forcedTransition?.sourceKind, 'all');
        assert.equal(forcedTransition?.targetKind, 'exit');
        assert.equal(forcedTransition?.trigger?.kind, 'chainTrigger');
        assert.equal(forcedTransition?.trigger?.eventPath.text, '/Fault');
        assert.equal(forcedTransition?.from_state, 'ALL');
        assert.equal(forcedTransition?.to_state, 'EXIT_STATE');
        assert.equal(forcedTransition?.event_id?.pyNodeType, 'ChainID');
        assert.deepEqual(forcedTransition?.event_id?.path, ['Fault']);

        const importStatement = statements.find(item => item.kind === 'importStatement');
        assert.equal(importStatement?.kind, 'importStatement');
        assert.equal(importStatement?.pyNodeType, 'ImportStatement');
        assert.equal(importStatement?.sourcePath, './worker.fcstm');
        assert.equal(importStatement?.source_path, './worker.fcstm');
        assert.equal(importStatement?.alias, 'Worker');
        assert.equal(importStatement?.displayName, 'Worker Module');
        assert.equal(importStatement?.extra_name, 'Worker Module');
        assert.deepEqual(importStatement?.pathRange.start, {line: 14, character: 11});
        assert.deepEqual(importStatement?.aliasRange.start, {line: 14, character: 31});
        assert.equal(importStatement?.mappings.length, 2);
        assert.equal(importStatement?.mappings[0].kind, 'importDefMapping');
        assert.equal(importStatement?.mappings[0].pyNodeType, 'ImportDefMapping');
        assert.equal(importStatement?.mappings[0].selector.kind, 'importDefPatternSelector');
        assert.equal(importStatement?.mappings[0].selector.pyNodeType, 'ImportDefPatternSelector');
        assert.equal(importStatement?.mappings[0].selector.pattern, 'sensor_*');
        assert.equal(importStatement?.mappings[0].targetTemplate, 'io_$1');
        assert.equal(importStatement?.mappings[0].target_template.pyNodeType, 'ImportDefTargetTemplate');
        assert.equal(importStatement?.mappings[0].target_template.template, 'io_$1');
        assert.equal(importStatement?.mappings[1].kind, 'importEventMapping');
        assert.equal(importStatement?.mappings[1].pyNodeType, 'ImportEventMapping');
        assert.equal(importStatement?.mappings[1].sourceEvent.text, '/Start');
        assert.equal(importStatement?.mappings[1].source_event, importStatement?.mappings[1].sourceEvent);
        assert.equal(importStatement?.mappings[1].targetEvent.text, '/Bus.Start');
        assert.equal(importStatement?.mappings[1].extra_name, 'Bus Start');

        const pseudoState = statements.find(item => item.kind === 'stateDefinition' && item.name === 'Junction');
        assert.equal(pseudoState?.kind, 'stateDefinition');
        assert.equal(pseudoState?.pseudo, true);
        assert.equal(pseudoState?.is_pseudo, true);
    });

    it('returns null when no parse tree can be produced', async () => {
        const parser = packageModule.getParser();
        const document = createDocument('state Root;', '/tmp/no-ast.fcstm');
        const original = parser.parseTree;
        parser.parseTree = async () => null;

        try {
            const ast = await packageModule.parseAstDocument(document);
            assert.equal(ast, null);
        } finally {
            parser.parseTree = original;
        }
    });
});
