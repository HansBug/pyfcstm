import assert from 'node:assert/strict';
import * as path from 'node:path';

import {
    createDocument,
    completionModule,
    packageModule,
    trackTempDir,
    withPatchedProperty,
    writeFile,
} from './support';

describe('jsfcstm completion support', () => {
    it('detects comment and string contexts', () => {
        assert.equal(packageModule.isInComment('value // comment'), true);
        assert.equal(packageModule.isInComment('value # comment'), true);
        assert.equal(packageModule.isInComment('value /* block'), true);
        assert.equal(packageModule.isInComment('value /* closed */'), false);

        assert.equal(packageModule.isInString('"open string'), true);
        assert.equal(packageModule.isInString('\'open string'), true);
        assert.equal(packageModule.isInString('"escaped \\" quote"'), false);
        assert.equal(packageModule.isInString('plain text'), false);
    });

    it('returns no completions inside comments or strings', async () => {
        const commentDocument = createDocument('// state', '/tmp/comment.fcstm');
        const stringDocument = createDocument('"state"', '/tmp/string.fcstm');

        const commentItems = await packageModule.collectCompletionItems(commentDocument, {line: 0, character: 8});
        const stringItems = await packageModule.collectCompletionItems(stringDocument, {line: 0, character: 6});

        assert.deepEqual(commentItems, []);
        assert.deepEqual(stringItems, []);
    });

    it('returns keyword, math, symbol, and import-aware completions', async () => {
        const dir = trackTempDir('jsfcstm-completion-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        writeFile(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

        const beforeAliasDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" \n}',
            hostFile
        );
        const beforeNamedDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" as Worker\n}',
            hostFile
        );
        const importHeaderDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" as Worker {\n}\n}',
            hostFile
        );
        const importBodyDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker {',
            '        ',
            '    }',
            '}',
        ].join('\n'), hostFile);
        const generalDocument = createDocument(
            'def int counter = 0;\nstate Root { event Start; }',
            '/tmp/general.fcstm'
        );

        const beforeAlias = await packageModule.collectCompletionItems(beforeAliasDocument, {line: 1, character: 27});
        assert.ok(beforeAlias.some(item => item.label === 'as' && item.kind === 'keyword'));

        const beforeNamed = await packageModule.collectCompletionItems(beforeNamedDocument, {line: 1, character: 37});
        assert.ok(beforeNamed.some(item => item.label === 'named' && item.kind === 'keyword'));

        const importHeader = await packageModule.collectCompletionItems(importHeaderDocument, {
            line: 1,
            character: importHeaderDocument.lineAt(1).text.length,
        });
        assert.ok(importHeader.some(item => item.label === 'def' && item.kind === 'keyword'));
        assert.ok(importHeader.some(item => item.label === 'event' && item.kind === 'keyword'));

        const importBody = await packageModule.collectCompletionItems(importBodyDocument, {line: 2, character: 8});
        assert.ok(importBody.some(item => item.label === 'speed' && item.kind === 'variable'));
        assert.ok(importBody.some(item => item.label === '/Start' && item.kind === 'event'));

        const generalItems = await packageModule.collectCompletionItems(generalDocument, {line: 1, character: 5});
        assert.ok(generalItems.some(item => item.label === 'state' && item.kind === 'keyword'));
        assert.ok(generalItems.some(item => item.label === 'pi' && item.kind === 'constant'));
        assert.ok(generalItems.some(item => item.label === 'sin' && item.kind === 'function'));
        assert.ok(generalItems.some(item => item.label === 'counter' && item.kind === 'variable'));
        assert.ok(generalItems.some(item => item.label === 'sin' && item.insertTextFormat === 'snippet'));
    });

    it('adds path-aware and action-aware contextual completions', async () => {
        const document = createDocument([
            'state Root {',
            '    event Start;',
            '    enter ResetCounter {',
            '    }',
            '    state Idle;',
            '    [*] -> Idle;',
            '    Idle -> Idle : /',
            '    exit ref Re',
            '}',
        ].join('\n'), '/tmp/contextual-completion.fcstm');

        const eventItems = await packageModule.collectCompletionItems(document, {
            line: 6,
            character: document.lineAt(6).text.length,
        });
        assert.ok(eventItems.some(item => item.label === '/Start' && item.kind === 'event'));

        const actionItems = await packageModule.collectCompletionItems(document, {
            line: 7,
            character: document.lineAt(7).text.length,
        });
        assert.ok(actionItems.some(item => item.label === 'Root.ResetCounter' && item.kind === 'function'));
    });

    it('limits scoped state, event, and import alias completions to visible lookup scopes', async () => {
        const document = createDocument([
            'state Root {',
            '    event RootEvent;',
            '    import "./root.fcstm" as RootWorker;',
            '    state Parent {',
            '        event ParentEvent;',
            '        import "./parent.fcstm" as ParentWorker;',
            '        state Leaf;',
            '        state Hidden {',
            '            event HiddenEvent;',
            '            state DeepHidden;',
            '        }',
            '        Leaf -> ',
            '        Leaf -> Leaf : ',
            '    }',
            '    state Outside {',
            '        event OutsideEvent;',
            '        import "./outside.fcstm" as OutsideWorker;',
            '        state DeepOutside;',
            '    }',
            '}',
        ].join('\n'), '/tmp/scoped-completion.fcstm');

        const stateItems = await packageModule.collectCompletionItems(document, {
            line: 11,
            character: document.lineAt(11).text.length,
        });
        assert.ok(stateItems.some(item => item.label === 'Leaf' && item.kind === 'class'));
        assert.ok(stateItems.some(item => item.label === 'Hidden' && item.kind === 'class'));
        assert.ok(stateItems.some(item => item.label === 'ParentWorker' && item.kind === 'class'));
        assert.equal(stateItems.some(item => item.label === 'Parent'), false);
        assert.equal(stateItems.some(item => item.label === 'DeepHidden'), false);
        assert.equal(stateItems.some(item => item.label === 'Outside'), false);
        assert.equal(stateItems.some(item => item.label === 'RootWorker'), false);
        assert.equal(stateItems.some(item => item.label === 'DeepOutside'), false);
        assert.equal(stateItems.some(item => item.label === 'OutsideWorker'), false);

        const eventItems = await packageModule.collectCompletionItems(document, {
            line: 12,
            character: document.lineAt(12).text.length,
        });
        assert.ok(eventItems.some(item => item.label === 'ParentEvent' && item.kind === 'event'));
        assert.equal(eventItems.some(item => item.label === 'RootEvent'), false);
        assert.equal(eventItems.some(item => item.label === 'HiddenEvent'), false);
        assert.equal(eventItems.some(item => item.label === 'OutsideEvent'), false);
    });

    it('keeps nested transition and absolute-path completions focused on semantic scope', async () => {
        const baseText = [
            'def int a = 0;',
            'def int b = 0x0 * 0;',
            'def int round_count = 0;',
            'state TrafficLight {',
            '    state InService {',
            '        state Red;',
            '        state Yellow;',
            '        state Green;',
            '        [*] -> Red :: Start effect {',
            '            b = 0x1;',
            '        };',
            '        Green -> Yellow : /Idle.E2;',
            '    }',
            '    state Idle {',
            '        event E2 named \'fuck E2\';',
            '    };',
            '    [*] -> InService;',
            '}',
        ].join('\n');

        const topTargetDocument = createDocument(
            baseText.replace('[*] -> InService;', '[*] -> Ye'),
            '/tmp/trafficlight-top-target.fcstm'
        );
        const topTargetLine = 16;
        const topTargetItems = await packageModule.collectCompletionItems(topTargetDocument, {
            line: topTargetLine,
            character: topTargetDocument.lineAt(topTargetLine).text.length,
        });
        assert.ok(topTargetItems.some(item => item.label === 'InService' && item.kind === 'class'));
        assert.ok(topTargetItems.some(item => item.label === 'Idle' && item.kind === 'class'));
        assert.equal(topTargetItems.some(item => item.label === 'Yellow'), false);

        const innerTargetDocument = createDocument(
            baseText.replace('Green -> Yellow : /Idle.E2;', 'Green -> Id'),
            '/tmp/trafficlight-inner-target.fcstm'
        );
        const innerTargetLine = 11;
        const innerTargetItems = await packageModule.collectCompletionItems(innerTargetDocument, {
            line: innerTargetLine,
            character: innerTargetDocument.lineAt(innerTargetLine).text.length,
        });
        assert.ok(innerTargetItems.some(item => item.label === 'Red' && item.kind === 'class'));
        assert.ok(innerTargetItems.some(item => item.label === 'Yellow' && item.kind === 'class'));
        assert.ok(innerTargetItems.some(item => item.label === 'Green' && item.kind === 'class'));
        assert.equal(innerTargetItems.some(item => item.label === 'Idle'), false);
        assert.equal(innerTargetItems.some(item => item.label === 'InService'), false);

        const absolutePathDocument = createDocument(
            baseText.replace('Green -> Yellow : /Idle.E2;', 'Green -> Yellow : /Idle.'),
            '/tmp/trafficlight-absolute-path.fcstm'
        );
        const absolutePathItems = await packageModule.collectCompletionItems(absolutePathDocument, {
            line: innerTargetLine,
            character: absolutePathDocument.lineAt(innerTargetLine).text.length,
        });
        assert.ok(absolutePathItems.some(item => item.label === '/Idle.E2' && item.kind === 'event'));
        assert.equal(absolutePathItems.some(item => item.label === 'before'), false);
        assert.equal(absolutePathItems.some(item => item.label === 'after'), false);
    });

    it('keeps completion alive for the user-reported full-sample target edits', async () => {
        const baseText = [
            'def int a = 0;',
            'def int b = 0x0 * 0;',
            'def int round_count = 0;  // define variables',
            'state TrafficLight {',
            '    >> during before {',
            '        a = 0;',
            '    }',
            '    >> during before abstract FFT;',
            '    >> during before abstract TTT /* this is the line */;',
            '    >> during after {',
            '        a = 0xff;',
            '        b = 0x1;',
            '    }',
            '',
            '    state InService {',
            '        state Red {',
            '            during {',
            '                a = 0x1 << 2;',
            '            }',
            '        }',
            '        state Yellow;',
            '        state Green;',
            '        [*] -> Red :: Start effect {',
            '            b = 0x1;',
            '        };',
            '        Red -> Green effect {',
            '            b = 0x3;',
            '        };',
            '        Green -> Yellow effect {',
            '            b = 0x2;',
            '        };',
            '        Yellow -> Red : if [a >= 10] effect {',
            '            b = 0x1;',
            '            round_count = round_count + 1;',
            '        };',
            '        Green -> Yellow : /Idle.E2;',
            '        Yellow -> Yellow : /E2;',
            '    }',
            '    state Idle;',
            '',
            '    [*] -> InService;',
            '    InService -> Idle :: Maintain;',
            '    Idle -> Idle :: E2;',
            '    Idle -> [*];',
            '}',
        ].join('\n');

        const rootDocument = createDocument(
            baseText.replace('    Idle -> [*];', '    Idle -> Id'),
            '/tmp/trafficlight-reported-root-target.fcstm'
        );
        const rootLine = rootDocument.lineCount - 2;
        const rootItems = await packageModule.collectCompletionItems(rootDocument, {
            line: rootLine,
            character: rootDocument.lineAt(rootLine).text.length,
        });
        assert.ok(rootItems.some(item => item.label === 'Idle' && item.kind === 'class'));
        assert.ok(rootItems.some(item => item.label === 'InService' && item.kind === 'class'));
        assert.equal(rootItems.some(item => item.label === 'Yellow'), false);

        const nestedDocument = createDocument(
            baseText.replace('        Green -> Yellow effect {', '        Green -> Yel effect {'),
            '/tmp/trafficlight-reported-nested-target.fcstm'
        );
        const nestedLine = nestedDocument.getText().split('\n').findIndex(line => line.includes('Green -> Yel effect {'));
        const nestedColumn = nestedDocument.lineAt(nestedLine).text.indexOf('Yel') + 'Yel'.length;
        const nestedItems = await packageModule.collectCompletionItems(nestedDocument, {
            line: nestedLine,
            character: nestedColumn,
        });
        assert.ok(nestedItems.some(item => item.label === 'Yellow' && item.kind === 'class'));
        assert.ok(nestedItems.some(item => item.label === 'Red' && item.kind === 'class'));
        assert.ok(nestedItems.some(item => item.label === 'Green' && item.kind === 'class'));
        assert.equal(nestedItems.some(item => item.label === 'Idle'), false);
    });

    it('distinguishes chain, local, and absolute event-trigger completions by semantic scope', async () => {
        const document = createDocument([
            'state Root {',
            '    event RootEvent;',
            '    state Parent {',
            '        event ParentEvent;',
            '        state Leaf {',
            '            event LeafEvent;',
            '            state Child;',
            '            [*] -> Child;',
            '        }',
            '        Leaf -> Leaf :',
            '        Leaf -> Leaf ::',
            '        Leaf -> Leaf : /',
            '        Leaf -> Leaf : /Parent.',
            '    }',
            '}',
        ].join('\n'), '/tmp/trigger-scope-completion.fcstm');

        const chainItems = await packageModule.collectCompletionItems(document, {
            line: 9,
            character: document.lineAt(9).text.length,
        });
        assert.ok(chainItems.some(item => item.label === 'ParentEvent' && item.kind === 'event'));
        assert.equal(chainItems.find(item => item.label === 'ParentEvent')?.insertText, ' ParentEvent');
        assert.equal(chainItems.some(item => item.label === 'LeafEvent'), false);
        assert.equal(chainItems.some(item => item.label === 'RootEvent'), false);
        assert.equal(chainItems.some(item => item.label === 'Entering'), false);
        assert.equal(chainItems.some(item => item.kind !== 'event'), false);

        const localItems = await packageModule.collectCompletionItems(document, {
            line: 10,
            character: document.lineAt(10).text.length,
        });
        assert.ok(localItems.some(item => item.label === 'LeafEvent' && item.kind === 'event'));
        assert.equal(localItems.find(item => item.label === 'LeafEvent')?.insertText, ' LeafEvent');
        assert.equal(localItems.some(item => item.label === 'ParentEvent'), false);
        assert.equal(localItems.some(item => item.label === 'RootEvent'), false);
        assert.equal(localItems.some(item => item.kind !== 'event'), false);

        const absoluteRootItems = await packageModule.collectCompletionItems(document, {
            line: 11,
            character: document.lineAt(11).text.length,
        });
        assert.ok(absoluteRootItems.some(item => item.label === '/Parent' && item.kind === 'class'));
        assert.ok(absoluteRootItems.some(item => item.label === '/RootEvent' && item.kind === 'event'));
        assert.equal(absoluteRootItems.find(item => item.label === '/Parent')?.insertText, 'Parent');
        assert.equal(absoluteRootItems.find(item => item.label === '/RootEvent')?.insertText, 'RootEvent');
        assert.equal(absoluteRootItems.some(item => item.label === 'ParentEvent'), false);
        assert.equal(absoluteRootItems.some(item => item.label === 'Entering'), false);

        const absoluteNestedItems = await packageModule.collectCompletionItems(document, {
            line: 12,
            character: document.lineAt(12).text.length,
        });
        assert.ok(absoluteNestedItems.some(item => item.label === '/Parent.ParentEvent' && item.kind === 'event'));
        assert.ok(absoluteNestedItems.some(item => item.label === '/Parent.Leaf' && item.kind === 'class'));
        assert.equal(absoluteNestedItems.some(item => item.label === '/RootEvent'), false);
        assert.equal(absoluteNestedItems.some(item => item.label === 'before'), false);
        assert.equal(absoluteNestedItems.some(item => item.label === 'after'), false);
        assert.equal(absoluteNestedItems.find(item => item.label === '/Parent.ParentEvent')?.insertText, 'ParentEvent');
        assert.equal(absoluteNestedItems.find(item => item.label === '/Parent.Leaf')?.insertText, 'Leaf');
    });

    it('formats trigger completion insert text for implicit local events and pre-spaced chain events', async () => {
        const localDocument = createDocument([
            'state TrafficLight {',
            '    state Idle;',
            '    Idle -> Idle :: E2;',
            '    Idle -> Idle ::',
            '}',
        ].join('\n'), '/tmp/local-trigger-insert-text.fcstm');
        const localItems = await packageModule.collectCompletionItems(localDocument, {
            line: 3,
            character: localDocument.lineAt(3).text.length,
        });
        assert.ok(localItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(localItems.find(item => item.label === 'E2')?.insertText, ' E2');

        const chainDocument = createDocument([
            'state Root {',
            '    event E2;',
            '    state Idle;',
            '    Idle -> Idle : ',
            '}',
        ].join('\n'), '/tmp/chain-trigger-insert-text.fcstm');
        const chainItems = await packageModule.collectCompletionItems(chainDocument, {
            line: 3,
            character: chainDocument.lineAt(3).text.length,
        });
        assert.ok(chainItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(chainItems.find(item => item.label === 'E2')?.insertText, 'E2');
    });

    it('keeps local and chain trigger completions active for spaced and unspaced partial prefixes', async () => {
        const document = createDocument([
            'state Root {',
            '    event E2;',
            '    state Idle {',
            '        event E2;',
            '    }',
            '    Idle -> Idle :: E2;',
            '    Idle -> Idle : E2;',
            '    Idle -> Idle ::E',
            '    Idle -> Idle :: E',
            '    Idle -> Idle :E',
            '    Idle -> Idle : E',
            '}',
        ].join('\n'), '/tmp/trigger-partial-prefixes.fcstm');

        const localNoSpaceItems = await packageModule.collectCompletionItems(document, {
            line: 7,
            character: document.lineAt(7).text.length,
        });
        assert.ok(localNoSpaceItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(localNoSpaceItems.find(item => item.label === 'E2')?.detail, 'Root.Idle.E2');
        assert.equal(localNoSpaceItems.find(item => item.label === 'E2')?.insertText, ' E2');

        const localSpacedItems = await packageModule.collectCompletionItems(document, {
            line: 8,
            character: document.lineAt(8).text.length,
        });
        assert.ok(localSpacedItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(localSpacedItems.find(item => item.label === 'E2')?.detail, 'Root.Idle.E2');
        assert.equal(localSpacedItems.find(item => item.label === 'E2')?.insertText, 'E2');

        const chainNoSpaceItems = await packageModule.collectCompletionItems(document, {
            line: 9,
            character: document.lineAt(9).text.length,
        });
        assert.ok(chainNoSpaceItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(chainNoSpaceItems.find(item => item.label === 'E2')?.detail, 'Root.E2');
        assert.equal(chainNoSpaceItems.find(item => item.label === 'E2')?.insertText, ' E2');

        const chainSpacedItems = await packageModule.collectCompletionItems(document, {
            line: 10,
            character: document.lineAt(10).text.length,
        });
        assert.ok(chainSpacedItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(chainSpacedItems.find(item => item.label === 'E2')?.detail, 'Root.E2');
        assert.equal(chainSpacedItems.find(item => item.label === 'E2')?.insertText, 'E2');
    });

    it('offers root-scope chain and local completions for same-named E2 events without conflating namespaces', async () => {
        const document = createDocument([
            'state TrafficLight {',
            '    state InService {',
            '        state Yellow;',
            '        Green -> Yellow : /Idle.E2;',
            '        Yellow -> Yellow : /E2;',
            '    }',
            '    state Idle;',
            '    Idle -> Idle :: E2;',
            '    Idle -> Idle ::',
            '    Idle -> Idle :',
            '}',
        ].join('\n'), '/tmp/root-chain-vs-local-e2.fcstm');

        const localItems = await packageModule.collectCompletionItems(document, {
            line: 8,
            character: document.lineAt(8).text.length,
        });
        assert.ok(localItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(localItems.find(item => item.label === 'E2')?.insertText, ' E2');
        assert.equal(localItems.find(item => item.label === 'E2')?.detail, 'TrafficLight.Idle.E2');
        assert.equal(localItems.some(item => item.label === 'Idle' && item.kind === 'event'), false);

        const chainItems = await packageModule.collectCompletionItems(document, {
            line: 9,
            character: document.lineAt(9).text.length,
        });
        assert.ok(chainItems.some(item => item.label === 'E2' && item.kind === 'event'));
        assert.equal(chainItems.find(item => item.label === 'E2')?.insertText, ' E2');
        assert.equal(chainItems.find(item => item.label === 'E2')?.detail, 'TrafficLight.E2');
        assert.notEqual(
            localItems.find(item => item.label === 'E2')?.detail,
            chainItems.find(item => item.label === 'E2')?.detail
        );
        assert.equal(chainItems.some(item => item.label === 'Idle' && item.kind === 'event'), false);
    });

    it('offers pseudo-state marker completions for source and target positions', async () => {
        const document = createDocument([
            'state Root {',
            '    state Idle;',
            '    [',
            '    Idle -> ',
            '}',
        ].join('\n'), '/tmp/pseudo-state-marker-completion.fcstm');

        const sourceItems = await packageModule.collectCompletionItems(document, {
            line: 2,
            character: document.lineAt(2).text.length,
        });
        assert.ok(sourceItems.some(item => item.label === '[*]' && item.kind === 'keyword'));
        assert.equal(sourceItems.find(item => item.label === '[*]')?.insertText, '[*]');

        const targetItems = await packageModule.collectCompletionItems(document, {
            line: 3,
            character: document.lineAt(3).text.length,
        });
        assert.ok(targetItems.some(item => item.label === '[*]' && item.kind === 'keyword'));
        assert.equal(targetItems.find(item => item.label === '[*]')?.insertText, '[*]');
        assert.ok(targetItems.some(item => item.label === 'Idle' && item.kind === 'class'));
    });

    it('completes absolute trigger paths without duplicating the slash prefix', async () => {
        const document = createDocument([
            'state TrafficLight {',
            '    state InService;',
            '    state Idle;',
            '    event E2;',
            '    Idle -> Idle : /',
            '}',
        ].join('\n'), '/tmp/absolute-trigger-path-insert-text.fcstm');

        const items = await packageModule.collectCompletionItems(document, {
            line: 4,
            character: document.lineAt(4).text.length,
        });

        assert.ok(items.some(item => item.label === '/Idle' && item.kind === 'class'));
        assert.equal(items.find(item => item.label === '/Idle')?.insertText, 'Idle');
        assert.ok(items.some(item => item.label === '/E2' && item.kind === 'event'));
        assert.equal(items.find(item => item.label === '/E2')?.insertText, 'E2');
        assert.equal(items.some(item => item.label === '//'), false);
        assert.equal(items.some(item => item.insertText?.startsWith('/')), false);
    });

    it('only offers legal existing event candidates for absolute path trigger completions', async () => {
        const document = createDocument([
            'state Root {',
            '    state Idle {',
            '        event E2;',
            '    }',
            '    Idle -> Idle : /Idle.E2;',
            '    Idle -> Idle : /Idle.',
            '}',
        ].join('\n'), '/tmp/absolute-trigger-legal-events-only.fcstm');

        const items = await packageModule.collectCompletionItems(document, {
            line: 5,
            character: document.lineAt(5).text.length,
        });
        const eventLabels = items
            .filter(item => item.kind === 'event')
            .map(item => item.label)
            .sort();

        assert.deepEqual(eventLabels, ['/Idle.E2']);
        assert.equal(items.some(item => item.label === '/Idle./Idle.'), false);
        assert.equal(items.some(item => item.insertText === '/Idle.'), false);
    });

    it('handles parser-null and missing-import-target completion branches', async () => {
        const parser = packageModule.getParser();
        const index = packageModule.getImportWorkspaceIndex();
        const document = createDocument(
            'state Root {\n    import "./missing.fcstm" as Missing {\n    }\n}',
            '/tmp/missing-import.fcstm'
        );

        await withPatchedProperty(parser, 'parseTree', async () => null, async () => {
            const items = await packageModule.collectCompletionItems(document, {line: 0, character: 3});
            assert.ok(items.some(item => item.label === 'state'));
            assert.equal(items.some(item => item.label === 'Missing'), false);
        });

        await withPatchedProperty(index, 'resolveImportsForDocument', async () => [], async () => {
            const items = await packageModule.collectCompletionItems(document, {line: 2, character: 4});
            assert.ok(items.some(item => item.label === 'def'));
            assert.equal(items.some(item => item.detail === 'Imported variable'), false);
        });
    });

    it('gracefully falls back to keyword completions when semantic AST building cannot recover', async () => {
        const document = createDocument('def ', '/tmp/incomplete-definition.fcstm');

        const items = await packageModule.collectCompletionItems(document, {line: 0, character: 4});

        assert.ok(items.some(item => item.label === 'int' && item.kind === 'keyword'));
        assert.ok(items.some(item => item.label === 'pi' && item.kind === 'constant'));
        assert.ok(items.some(item => item.label === 'sin' && item.kind === 'function'));
    });

    it('falls back to parse-tree symbol completions when semantic construction fails on partial input', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def int count = 1;',
            'state Root {',
            '    enter {',
            '        cou',
            '    }',
            '}',
        ].join('\n'), '/tmp/partial-symbol.fcstm');

        const items = await packageModule.collectCompletionItems(document, {line: 4, character: 11});

        assert.ok(items.some(item => item.label === 'counter' && item.kind === 'variable'));
        assert.ok(items.some(item => item.label === 'count' && item.kind === 'variable'));
    });

    it('offers state and event completions for partial symbols typed on an otherwise empty line', async () => {
        const rootDocument = createDocument([
            'state Root {',
            '    state Idle;',
            '    event InitDone;',
            '    Id',
            '}',
        ].join('\n'), '/tmp/blank-line-root-symbol.fcstm');

        const rootItems = await packageModule.collectCompletionItems(rootDocument, {
            line: 3,
            character: rootDocument.lineAt(3).text.length,
        });
        assert.ok(rootItems.some(item => item.label === 'Idle' && item.kind === 'class'));

        const eventDocument = createDocument([
            'state Root {',
            '    event InitDone;',
            '    Ini',
            '}',
        ].join('\n'), '/tmp/blank-line-event-symbol.fcstm');

        const eventItems = await packageModule.collectCompletionItems(eventDocument, {
            line: 2,
            character: eventDocument.lineAt(2).text.length,
        });
        assert.ok(eventItems.some(item => item.label === 'InitDone' && item.kind === 'event'));

        const nestedDocument = createDocument([
            'state Root {',
            '    state InService {',
            '        state Yellow;',
            '        Yel',
            '    }',
            '}',
        ].join('\n'), '/tmp/blank-line-nested-symbol.fcstm');

        const nestedItems = await packageModule.collectCompletionItems(nestedDocument, {
            line: 3,
            character: nestedDocument.lineAt(3).text.length,
        });
        assert.ok(nestedItems.some(item => item.label === 'Yellow' && item.kind === 'class'));
    });

    it('exposes stable keyword, constant, and function catalogs', () => {
        assert.ok(completionModule.KEYWORDS.includes('state'));
        assert.ok(completionModule.KEYWORDS.includes('import'));
        assert.ok(completionModule.MATH_CONSTANTS.some(item => item.name === 'pi'));
        assert.ok(completionModule.MATH_FUNCTIONS.some(item => item.name === 'sqrt'));
    });
});
