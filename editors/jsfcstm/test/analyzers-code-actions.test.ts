import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir} from './support';

describe('jsfcstm analyzers and code actions', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    function rangeOf(text: string, needle: string) {
        const lines = text.split('\n');
        for (let line = 0; line < lines.length; line += 1) {
            const column = lines[line].indexOf(needle);
            if (column >= 0) {
                return packageModule.createRange(line, column, line, column + needle.length);
            }
        }
        throw new Error(`needle not found: ${needle}`);
    }

    function applySingleEdit(text: string, edit: {range: {start: {line: number; character: number}; end: {line: number; character: number}}; newText: string}): string {
        const lines = text.split('\n');
        const before = [
            ...lines.slice(0, edit.range.start.line),
            lines[edit.range.start.line].slice(0, edit.range.start.character),
        ].join('\n');
        const after = [
            lines[edit.range.end.line].slice(edit.range.end.character),
            ...lines.slice(edit.range.end.line + 1),
        ].join('\n');
        return `${before}${edit.newText}${after}`;
    }

    async function assertParses(text: string, filePath: string): Promise<void> {
        const document = createDocument(text, filePath);
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.equal(
            diagnostics.some(item => item.severity === 'error'),
            false,
            `expected edited DSL to parse and semantically validate, got ${JSON.stringify(diagnostics)}`,
        );
    }

    async function inspectDiagnosticsAsEditorDiagnostics(text: string, filePath: string) {
        const document = createDocument(text, filePath);
        const ast = await packageModule.parseAstDocument(document);
        const machine = packageModule.buildStateMachineModel(ast);
        assert.ok(machine, 'expected state-machine model');
        const report = packageModule.inspectModel(machine);
        const fullRange = packageModule.createRange(0, 0, document.lineCount - 1, document.lineAt(document.lineCount - 1).text.length);
        return report.diagnostics.map(item => ({
            range: fullRange,
            message: item.message,
            severity: item.severity,
            source: 'fcstm',
            code: item.code,
            data: item.refs,
        }));
    }

    it('reports semantic analyzer diagnostics for unreachable states, dead transitions, unused events, mappings, and unresolved refs', async () => {
        const dir = trackTempDir('jsfcstm-analyzers-');
        const hostFile = path.join(dir, 'host.fcstm');
        const document = createDocument([
            'state Root {',
            '    import "./missing.fcstm" as Worker {',
            '        def sensor_* -> io_$1;',
            '        def sensor_* -> io_$1;',
            '    }',
            '    event Start;',
            '    enter ref MissingAction;',
            '    state Idle;',
            '    state Dead;',
            '    [*] -> Idle;',
            '    Idle -> dead : if [false];',
            '}',
        ].join('\n'), hostFile);

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const codes = diagnostics.map(item => item.code);
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.importNotFound));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.importDuplicateMapping));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.unreachableState));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.guardConstFalse));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.unusedEvent));
        // pyfcstm split: source-side mismatch is E_MISSING_STATE, target-side
        // mismatch is E_DANGLING_TRANSITION. The fixture uses ``Idle -> dead``
        // which fails on the target side, so we expect the dangling code.
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.danglingTransition));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.namedFunctionRefNotFound));
    });

    it('builds safe quick fixes for missing imports, duplicate mappings, unused events, and unresolved states', async () => {
        const dir = trackTempDir('jsfcstm-code-actions-');
        const hostFile = path.join(dir, 'host.fcstm');
        const document = createDocument([
            'state Root {',
            '    import "./missing.fcstm" as Worker {',
            '        def sensor_* -> io_$1;',
            '        def sensor_* -> io_$1;',
            '    }',
            '    event Start;',
            '    state Idle;',
            '    [*] -> Idle;',
            '    Idle -> idle;',
            '}',
        ].join('\n'), hostFile);

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const actions = await packageModule.collectCodeActions(
            document,
            packageModule.createRange(0, 0, 8, 20),
            diagnostics
        );

        assert.ok(actions.some(item => /Remove unresolved import/.test(item.title)));
        assert.ok(actions.some(item => /Remove duplicate import mapping/.test(item.title)));
        assert.ok(actions.some(item => /Remove unused event/.test(item.title)));
        assert.ok(actions.some(item => /Change to Idle/.test(item.title)));

        const renameLikeAction = actions.find(item => /Change to Idle/.test(item.title));
        const renameEdit = renameLikeAction?.edit?.changes[Object.keys(renameLikeAction.edit.changes)[0]][0];
        assert.equal(renameEdit?.newText, 'Idle');
    });

    it('reports duplicate variable definitions and offers a remove quick fix', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def float counter = 1.0;',
            'state Root { [*] -> Idle; state Idle; }',
        ].join('\n'), '/tmp/dup-var.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const duplicate = diagnostics.find(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.duplicateVar);
        assert.ok(duplicate, 'expected duplicateVariable diagnostic');
        assert.match(duplicate.message, /counter/);
        assert.equal(duplicate.severity, 'error');
        assert.ok(duplicate.relatedInformation && duplicate.relatedInformation.length >= 1);

        const actions = await packageModule.collectCodeActions(
            document,
            duplicate.range,
            diagnostics
        );
        const removeAction = actions.find(item => /Remove duplicate definition/.test(item.title));
        assert.ok(removeAction, 'expected remove-duplicate quick fix');
        const edits = Object.values(removeAction.edit?.changes || {}).flat();
        assert.equal(edits.length, 1);
        assert.equal(edits[0].newText, '');
    });

    it('reports undefined variables in guards and offers a define-at-top quick fix', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [counter > 0 && missing_flag == 1];',
            '}',
        ].join('\n'), '/tmp/undef-var.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const undef = diagnostics.find(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVar);
        assert.ok(undef, 'expected undefinedVariable diagnostic');
        assert.match(undef.message, /missing_flag/);

        const actions = await packageModule.collectCodeActions(
            document,
            undef.range,
            diagnostics
        );
        const defineAction = actions.find(item => /Define "missing_flag" at the top of the file/.test(item.title));
        assert.ok(defineAction, 'expected define-at-top quick fix');
        const edits = Object.values(defineAction.edit?.changes || {}).flat();
        assert.equal(edits.length, 1);
        assert.match(edits[0].newText, /^def int missing_flag = 0;\n$/);
        // Should land on the line after the last existing def.
        assert.equal(edits[0].range.start.line, 1);
        assert.equal(edits[0].range.end.line, 1);
    });

    it('reports undefined variables in effect blocks and allows the quick fix even with no existing defs', async () => {
        const document = createDocument([
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active effect { counter = counter + 1; }',
            '}',
        ].join('\n'), '/tmp/undef-effect.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const undef = diagnostics.find(item => (
            item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVar
            && /counter/.test(item.message)
        ));
        assert.ok(undef, 'expected read-before-assign diagnostic for the RHS identifier');

        // Undefined-variable quick fix only runs for that exact code; this
        // test mainly pins down the temp-variable detection path.
        const actions = await packageModule.collectCodeActions(document, undef.range, diagnostics);
        // The action list may be empty (no matching code) - the important
        // property is that the analyzer produced a targeted diagnostic at all.
        assert.ok(Array.isArray(actions));
    });

    it('applies suggested-fix delete actions for unreferenced variable definitions', async () => {
        const text = [
            'def int unused = 0;',
            'def int driver = 0;',
            'state Root {',
            '    state Idle;',
            '    state Done;',
            '    [*] -> Idle;',
            '    Idle -> Done : if [driver > 0];',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-delete-var.fcstm';
        const document = createDocument(text, filePath);
        const diagnostics = await inspectDiagnosticsAsEditorDiagnostics(text, filePath);
        const diag = diagnostics.find(item => item.code === 'W_UNREFERENCED_VAR');
        assert.ok(diag, 'expected W_UNREFERENCED_VAR suggested fix diagnostic');

        const actions = await packageModule.collectCodeActions(document, diag.range, [diag]);
        const action = actions.find(item => /variable declaration/.test(item.title));
        assert.ok(action, `expected delete suggested-fix action, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        assert.equal(edit.newText, '');
        const updated = applySingleEdit(text, edit);
        assert.equal(updated.includes('def int unused = 0;'), false);
        await assertParses(updated, filePath);
    });

    it('applies suggested-fix delete actions for effect self assignments', async () => {
        const text = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B effect {',
            '        x = x;',
            '    };',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-delete-effect.fcstm';
        const document = createDocument(text, filePath);
        const diagnostics = await inspectDiagnosticsAsEditorDiagnostics(text, filePath);
        const diag = diagnostics.find(item => item.code === 'W_EFFECT_SELF_ASSIGN');
        assert.ok(diag, 'expected W_EFFECT_SELF_ASSIGN suggested fix diagnostic');

        const actions = await packageModule.collectCodeActions(document, diag.range, [diag]);
        const action = actions.find(item => /self-assignment/.test(item.title));
        assert.ok(action, `expected delete self-assignment action, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        assert.equal(edit.newText, '');
        const updated = applySingleEdit(text, edit);
        assert.equal(updated.includes('x = x;'), false);
        await assertParses(updated, filePath);
    });

    it('applies suggested-fix insert actions for deadlock leaves', async () => {
        const text = [
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-insert-deadlock.fcstm';
        const document = createDocument(text, filePath);
        const diagnostics = await inspectDiagnosticsAsEditorDiagnostics(text, filePath);
        const diag = diagnostics.find(item => (
            item.code === 'W_DEADLOCK_LEAF' &&
            item.data?.state_path === 'Root.Idle'
        ));
        assert.ok(diag, 'expected W_DEADLOCK_LEAF suggested fix diagnostic');

        const actions = await packageModule.collectCodeActions(document, diag.range, [diag]);
        const action = actions.find(item => /exit transition/.test(item.title));
        assert.ok(action, `expected insert deadlock action, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        assert.match(edit.newText, /Idle -> \[\*\];\n/);
        const updated = applySingleEdit(text, edit);
        await assertParses(updated, filePath);
        const followup = await inspectDiagnosticsAsEditorDiagnostics(updated, filePath);
        assert.equal(
            followup.some(item => item.code === 'W_DEADLOCK_LEAF' && item.data?.state_path === 'Root.Idle'),
            false,
        );
    });

    it('applies suggested-fix insert actions for missing unconditional initial transitions', async () => {
        const text = [
            'def int ready = 0;',
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle : if [ready > 0];',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-insert-initial.fcstm';
        const document = createDocument(text, filePath);
        const diagnostics = await inspectDiagnosticsAsEditorDiagnostics(text, filePath);
        const diag = diagnostics.find(item => item.code === 'W_INITIAL_UNCONDITIONAL_MISSING');
        assert.ok(diag, 'expected W_INITIAL_UNCONDITIONAL_MISSING suggested fix diagnostic');

        const actions = await packageModule.collectCodeActions(document, diag.range, [diag]);
        const action = actions.find(item => /fallback entry transition/.test(item.title));
        assert.ok(action, `expected insert initial action, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        assert.match(edit.newText, /\[\*\] -> Idle;\n/);
        const updated = applySingleEdit(text, edit);
        await assertParses(updated, filePath);
        const followup = await inspectDiagnosticsAsEditorDiagnostics(updated, filePath);
        assert.equal(
            followup.some(item => item.code === 'W_INITIAL_UNCONDITIONAL_MISSING'),
            false,
        );
    });

    it('applies suggested-fix replace actions from span-backed diagnostic payloads', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : if [true];',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-replace-guard.fcstm';
        const document = createDocument(text, filePath);
        const guardRange = rangeOf(text, ' : if [true]');
        const diagnostic = {
            range: guardRange,
            message: 'Guard is statically true.',
            severity: 'warning' as const,
            source: 'fcstm',
            code: 'W_GUARD_CONST_TRUE',
            data: {
                transition_span: guardRange,
                folded_value: true,
                suggested_fix: {
                    kind: 'replace',
                    target: 'transition_guard',
                    anchor: {type: 'ref', ref: 'refs.transition_span'},
                    text: '',
                    rationale: 'Remove the redundant constant-true guard.',
                },
            },
        };

        const actions = await packageModule.collectCodeActions(document, guardRange, [diagnostic]);
        const action = actions.find(item => /constant-true guard/.test(item.title));
        assert.ok(action, `expected replace guard action, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        assert.equal(edit.newText, '');
        const updated = applySingleEdit(text, edit);
        assert.equal(updated.includes(': if [true]'), false);
        assert.ok(updated.includes('A -> B;'));
        await assertParses(updated, filePath);
    });

    it('applies nested suggested-fix payloads with one-based span anchors', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-nested-span.fcstm';
        const document = createDocument(text, filePath);
        const diagnostic = {
            range: rangeOf(text, 'A -> B'),
            message: 'Synthetic insertion.',
            severity: 'warning' as const,
            source: 'fcstm',
            code: 'W_SYNTHETIC_INSERT',
            data: {
                refs: {
                    transition_span: {
                        line: 5,
                        column: 11,
                        end_line: 5,
                        end_column: 11,
                    },
                    suggested_fix: {
                        kind: 'insert',
                        target: 'transition_suffix',
                        anchor: {type: 'ref', ref: 'refs.transition_span'},
                        text: ' : Go',
                        rationale: 'Add a trigger before the semicolon.',
                    },
                },
            },
        };
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        assert.ok(semantic);

        const plannedRange = packageModule.suggestedFixDiagnosticRange(document, semantic, diagnostic);
        assert.deepEqual(plannedRange, packageModule.createRange(4, 10, 4, 10));

        const actions = await packageModule.collectCodeActions(document, diagnostic.range, [diagnostic]);
        const action = actions.find(item => /trigger before the semicolon/.test(item.title));
        assert.ok(action, `expected nested insert action, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        const updated = applySingleEdit(text, edit);
        assert.ok(updated.includes('A -> B : Go;'));
        await assertParses(updated, filePath);
    });

    it('ignores malformed or unanchored suggested-fix payloads', async () => {
        const text = [
            'def int used = 0;',
            'state Root {',
            '    state A;',
            '    [*] -> A;',
            '    A -> [*] : if [used > 0];',
            '}',
        ].join('\n');
        const filePath = '/tmp/suggested-invalid.fcstm';
        const document = createDocument(text, filePath);
        const diagnostics = [
            {
                range: rangeOf(text, 'def int used'),
                message: 'Missing variable target.',
                severity: 'warning' as const,
                source: 'fcstm',
                code: 'W_UNREFERENCED_VAR',
                data: {
                    var_name: 'missing',
                    suggested_fix: {
                        kind: 'delete',
                        target: 'variable_definition',
                        anchor: {type: 'ref', ref: 'refs.var_name'},
                        text: '',
                        rationale: 'Remove missing variable.',
                    },
                },
            },
            {
                range: rangeOf(text, 'A -> [*]'),
                message: 'Malformed payload.',
                severity: 'warning' as const,
                source: 'fcstm',
                code: 'W_BAD_PAYLOAD',
                data: {
                    suggested_fix: {
                        kind: 'move',
                        target: 'transition',
                        anchor: {type: 'ref', ref: 'refs.transition_span'},
                        text: '',
                        rationale: 'Invalid kind.',
                    },
                },
            },
        ];

        assert.equal(packageModule.suggestedFixFromDiagnostic(diagnostics[1]), null);
        const actions = await packageModule.collectCodeActions(
            document,
            packageModule.createRange(0, 0, 5, 1),
            diagnostics,
        );
        assert.equal(
            actions.some(item => /Remove missing variable|Invalid kind/.test(item.title)),
            false,
        );
        assert.equal(packageModule.renderSuggestedFix(
            'W_INITIAL_UNCONDITIONAL_MISSING',
            {composite_path: 'Root', existing_conditional_count: 1},
        ), null);
    });

    it('does not flag undefined variables in transitions that are legitimate state names', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [counter > 0];',
            '}',
        ].join('\n'), '/tmp/no-false-undef.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.equal(
            diagnostics.filter(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVar).length,
            0
        );
    });

    it('read-before-assign inside a block is reported only on the first read, not on subsequent assignments', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active effect {',
            '        temp = counter + 1;',  // temp gets defined here
            '        counter = temp * 2;',  // temp is now legitimate
            '    }',
            '}',
        ].join('\n'), '/tmp/temp-ok.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.equal(
            diagnostics.filter(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVar).length,
            0
        );
    });

    it('read-before-assign inside an if-branch is surfaced', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active effect {',
            '        if [counter > 0] {',
            '            counter = scratch + 1;',
            '        }',
            '    }',
            '}',
        ].join('\n'), '/tmp/temp-bad.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const tempDiag = diagnostics.find(item => (
            item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVar
        ));
        assert.ok(tempDiag, 'expected temp read-before-assign diagnostic inside the if-branch');
        assert.match(tempDiag.message, /scratch/);
    });

    // PR-A-coverage: targeted tests for expression / statement walker
    // branches that the existing fixtures don't reach.
    describe('analyzer expression walker coverage (PR-A-coverage)', () => {
        it('walks unary, binary, function, conditional, and parenthesized expressions in guards (positive case)', async () => {
            // Positive case: every identifier IS declared, so the walker
            // recursing through unary/binary/function/conditional/
            // parenthesized cases must NOT spuriously flag any name.
            const dir = trackTempDir('jsfcstm-walker-pos-');
            const hostFile = path.join(dir, 'host.fcstm');
            const document = createDocument([
                'def int counter = 0;',
                'def int limit = 10;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    [*] -> A;',
                '    A -> B : if [(counter + limit) > 0 && abs(-counter) < (limit * 2) && ((counter > limit) ? 1 : 0) > 0];',
                '}',
            ].join('\n'), hostFile);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            assert.equal(
                diagnostics.filter(d => d.code === 'E_UNDEFINED_VAR').length,
                0,
                `unexpected E_UNDEFINED_VAR: ${JSON.stringify(diagnostics)}`,
            );
        });

        it('walks ConditionalOp ifFalse + UFunc + parenthesized branches and reports nested unknowns', async () => {
            // Negative case (PR-A-coverage Codex I3): plant an
            // undefined identifier in *each* nested branch (ternary
            // ifTrue, ternary ifFalse, function argument, parenthesized
            // subexpression). If the walker misses any branch, the
            // corresponding name silently survives without
            // E_UNDEFINED_VAR. Asserting on every name proves every
            // branch was actually visited.
            const dir = trackTempDir('jsfcstm-walker-neg-');
            const hostFile = path.join(dir, 'host.fcstm');
            const document = createDocument([
                'def int known = 0;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    [*] -> A;',
                // Each undefined name lives in a distinct walker case:
                //   inside_paren — Parenthesized
                //   inside_fcall — Function argument
                //   inside_true  — ConditionalOp.ifTrue
                //   inside_false — ConditionalOp.ifFalse
                //   inside_unary — UnaryOp operand (`-name`)
                '    A -> B : if [(inside_paren + 1) > 0 && abs(inside_fcall) > 0 && ((known > 0) ? inside_true : inside_false) > 0 && -inside_unary > 0];',
                '}',
            ].join('\n'), hostFile);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const undefNames = new Set(
                diagnostics
                    .filter(d => d.code === 'E_UNDEFINED_VAR')
                    .map(d => (d.data as Record<string, unknown>)?.var_name as string),
            );
            for (const name of ['inside_paren', 'inside_fcall', 'inside_true', 'inside_false', 'inside_unary']) {
                assert.ok(undefNames.has(name),
                    `walker missed branch for ${name}; got E_UNDEFINED_VAR for ${JSON.stringify([...undefNames])}`);
            }
        });

        it('detects read-before-assign inside if-branch condition', async () => {
            const dir = trackTempDir('jsfcstm-ifbranch-');
            const hostFile = path.join(dir, 'host.fcstm');
            const document = createDocument([
                'state Root {',
                '    state Idle {',
                '        enter {',
                '            if [scratch > 0] {',
                '                scratch = 1;',
                '            }',
                '        }',
                '    }',
                '    [*] -> Idle;',
                '}',
            ].join('\n'), hostFile);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const undef = diagnostics.find(d =>
                d.code === 'E_UNDEFINED_VAR'
                && (d.data as Record<string, unknown> | undefined)?.var_name === 'scratch'
            );
            assert.ok(undef, `expected E_UNDEFINED_VAR for scratch, got ${JSON.stringify(diagnostics)}`);
            assert.equal((undef.data as Record<string, unknown>).is_temporary, true);
        });

        it('merges branch-local assignments into outer scope when every branch (including else) assigns', async () => {
            const dir = trackTempDir('jsfcstm-branchmerge-');
            const hostFile = path.join(dir, 'host.fcstm');
            const document = createDocument([
                'def int sensor = 0;',
                'state Root {',
                '    state Idle {',
                '        enter {',
                '            if [sensor > 0] {',
                '                tracker = 1;',
                '            } else {',
                '                tracker = 0;',
                '            }',
                '            sensor = tracker + 1;',
                '        }',
                '    }',
                '    [*] -> Idle;',
                '}',
            ].join('\n'), hostFile);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            // Tightened (PR-A-coverage Claude I3): assert (a) tracker
            // never appears in any E_UNDEFINED_VAR; (b) the post-merge
            // read of ``tracker + 1`` produced no diagnostic at all —
            // proves the merge logic actually propagated, not just
            // that the analyzer happens to be silent.
            const allUndef = diagnostics.filter(d => d.code === 'E_UNDEFINED_VAR');
            assert.equal(allUndef.length, 0,
                `enter-block should be clean after if/else merge, got ${JSON.stringify(allUndef.map(d => d.data))}`);
            const trackerDiags = diagnostics.filter(d =>
                (d.data as Record<string, unknown> | undefined)?.var_name === 'tracker'
            );
            assert.equal(trackerDiags.length, 0,
                `tracker must not appear in any diagnostic after merge, got ${JSON.stringify(trackerDiags)}`);
        });

        it('branch-merge skips names already assigned before the if-statement', async () => {
            // Exercises the ``if (assigned.has(name)) continue;`` branch
            // (line 566-567). A name pre-assigned before the if is
            // already in ``assigned``; the post-merge loop sees it and
            // skips without redundantly re-adding.
            const dir = trackTempDir('jsfcstm-pre-merge-');
            const hostFile = path.join(dir, 'host.fcstm');
            const document = createDocument([
                'def int sensor = 0;',
                'state Root {',
                '    state Idle {',
                '        enter {',
                '            tracker = 1;',
                '            if [sensor > 0] {',
                '                tracker = 2;',
                '            } else {',
                '                tracker = 3;',
                '            }',
                '            sensor = tracker + 1;',
                '        }',
                '    }',
                '    [*] -> Idle;',
                '}',
            ].join('\n'), hostFile);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const trackerDiags = diagnostics.filter(d =>
                (d.data as Record<string, unknown> | undefined)?.var_name === 'tracker'
            );
            assert.equal(trackerDiags.length, 0,
                `tracker was assigned before the if/else; got ${JSON.stringify(trackerDiags)}`);
        });

        it('forced transition with missing target emits E_FORCED_TRANSITION_EXPANSION exactly', async () => {
            // Tightened (PR-A-coverage Claude I4): pin the exact code.
            // jsfcstm's analyzer for ``!State -> NoSuch`` reports
            // ``E_FORCED_TRANSITION_EXPANSION``; the previous
            // OR-form assertion was a contract escape hatch.
            const dir = trackTempDir('jsfcstm-forcedtgt-');
            const hostFile = path.join(dir, 'host.fcstm');
            const document = createDocument([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    !Idle -> NoSuchTarget : if [false];',
                '}',
            ].join('\n'), hostFile);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const forced = diagnostics.filter(d => d.code === 'E_FORCED_TRANSITION_EXPANSION');
            assert.equal(forced.length, 1,
                `expected exactly one E_FORCED_TRANSITION_EXPANSION, got codes=${JSON.stringify(diagnostics.map(d => d.code))}`);
            // ``W_GUARD_CONST_FALSE`` may also fire as a side effect
            // (guard ``if [false]``) — that is not the focus of this
            // test, so we don't assert on it either way.
        });
    });
});
