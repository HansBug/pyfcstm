import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

async function parse(source: string, filePath = '/tmp/element-documentation.fcstm') {
    return packageModule.parseAstDocument(createDocument(source, filePath));
}

function format(source: string): string {
    const document = createDocument(source, '/tmp/element-documentation-format.fcstm');
    const edits = packageModule.formatDocumentText(document);
    return edits.length === 0 ? source : edits[0].newText;
}

describe('element documentation contracts', () => {
    it('keeps documentation on its owning definition and excludes it from declaration ranges', async () => {
        const source = [
            '/* variable documentation */',
            'def int counter = 0;',
            '/** Root state',
            ' * owns the following declarations',
            ' */',
            'state Root {',
            '    /* event documentation */ event Tick;',
            '    /* abstract documentation */ enter abstract Boot;',
            '    /* transition documentation */ A -> B : Tick;',
            '    state A;',
            '    state B;',
            '}',
        ].join('\n');
        const ast = await parse(source);
        const root = ast.rootState!;
        const event = root.events[0];
        const action = root.enters[0];
        const transition = root.transitions[0];

        assert.equal(ast.variables[0].doc, 'variable documentation');
        assert.equal(root.doc, 'Root state\nowns the following declarations');
        assert.equal(event.doc, 'event documentation');
        assert.equal(action.doc, 'abstract documentation');
        assert.equal(transition.doc, 'transition documentation');
        assert.equal(root.range.start.line, 5);
        assert.equal(ast.variables[0].range.start.line, 1);
        assert.equal(event.range.start.character, 30);
        assert.equal(action.range.start.character, 33);
        assert.equal(transition.range.start.character, 35);
    });

    it('reports duplicate leading and trailing documentation on abstract actions', async () => {
        const source = [
            'state Root {',
            '    /* leading */ enter abstract Before;',
            '    /* leading */ enter abstract After /* trailing */',
            '}',
        ].join('\n');
        const ast = await parse(source);
        assert.equal(ast.rootState!.enters[0].doc, 'leading');
        assert.equal(ast.rootState!.enters[1].doc, 'leading');
        assert.equal(ast.rootState!.enters[0].mode, 'abstract');
        assert.equal(ast.rootState!.enters[1].mode, 'abstract');
        const diagnostics = await packageModule.collectDocumentDiagnostics(
            createDocument(source, '/tmp/duplicate-documentation.fcstm'),
        );
        assert.ok(diagnostics.some((item: {severity?: string; message: string}) =>
            item.severity === 'error' && /Duplicate model documentation/.test(item.message)));
    });

    it('distinguishes absent, empty, and star-prefixed documentation', async () => {
        const ast = await parse([
            'state Root {',
            '    enter abstract None;',
            '    enter abstract Empty /**/;',
            '    enter abstract Star /**',
            '     * first',
            '     * second',
            '     */;',
            '}',
        ].join('\n'));
        assert.equal(ast.rootState!.enters[0].doc, undefined);
        assert.equal(ast.rootState!.enters[1].doc, '');
        assert.equal(ast.rootState!.enters[2].doc, 'first\nsecond');
    });

    it('normalizes CRLF and star margins without changing content', async () => {
        const ast = await parse('state Root {\r\n    /**\r\n     * first\r\n     * second\r\n     */ enter abstract Boot;\r\n}', '/tmp/crlf.fcstm');
        assert.equal(ast.rootState!.enters[0].doc, 'first\nsecond');
    });

    it('matches the documentation golden for meaningful trailing spaces', async () => {
        const ast = await parse([
            'state Root {',
            '    enter abstract Golden /*',
            '     * A  ',
            '     * B',
            '     */;',
            '}',
        ].join('\n'));
        assert.equal(ast.rootState!.enters[0].doc, 'A  \nB');
        const formatted = format([
            'state Root {',
            '    enter abstract Golden /*',
            '     * A  ',
            '     * B',
            '     */;',
            '}',
        ].join('\n'));
        assert.match(formatted, /\* A  \n/);
    });

    it('preserves owner documentation trailing spaces for leading state and event blocks', () => {
        const formatted = format([
            '/*',
            ' * State line  ',
            ' * State second line',
            ' */ state Root {',
            '    /*',
            '     * Event line  ',
            '     * Event second line',
            '     */ event Tick;',
            '}',
        ].join('\n'));
        assert.match(formatted, /\* State line  \n/);
        assert.match(formatted, /\* Event line  \n/);
    });

    it('moves trailing abstract docs before the terminated action', () => {
        const formatted = format('state Root { enter abstract Boot /* docs */; }');
        assert.ok(formatted.includes('*/\n    enter abstract Boot;'), formatted);
        assert.ok(!formatted.includes('*/ ;'), formatted);
    });

    it('does not associate a same-line comment with a preceding abstract action', () => {
        const formatted = format('state Root { enter abstract Boot; state Child /* state docs */; }');
        assert.ok(formatted.includes('enter abstract Boot;'), formatted);
        assert.ok(formatted.indexOf('state Child') < formatted.indexOf('state docs'), formatted);
        assert.ok(!formatted.includes('state docs */\n    enter abstract Boot;'), formatted);
    });

    it('terminates a trailing abstract action before a same-line next declaration', () => {
        const formatted = format('state Root { enter abstract Boot /* docs */ state Child; }');
        assert.ok(formatted.includes('*/\n    enter abstract Boot;'), formatted);
        assert.ok(formatted.includes('state Child;'), formatted);
    });

    it('moves newline-separated trailing abstract docs before the action', () => {
        const formatted = format([
            'state Root { enter abstract Boot',
            '/* docs */ }',
        ].join('\n'));
        assert.ok(formatted.includes('    /*\n     * docs\n     */\n    enter abstract Boot;'), formatted);
        assert.equal(format(formatted), formatted);
    });

    it('reports malformed documentation through diagnostics instead of throwing', async () => {
        const source = 'state Root { enter abstract Broken /* unclosed; }';
        const document = createDocument(source, '/tmp/malformed-documentation.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.ok(diagnostics.some((item: {severity?: string; message: string}) =>
            item.severity === 'error' && /Invalid syntax/.test(item.message)));
        const ast = await packageModule.parseAstDocument(document);
        assert.ok(ast);
    });

    it('preserves documentation while formatting repeatedly', () => {
        const source = [
            '/* state docs */ state Root {',
            '/* action docs */ enter abstract Boot /** trailing docs */;',
            '}',
        ].join('\n');
        const once = format(source);
        assert.equal(format(once), once);
        assert.match(once, /state Root/);
        assert.match(once, /action docs/);
        assert.match(once, /trailing docs/);
    });

    it('keeps docs on forced and combo transitions and ref actions', async () => {
        const ast = await parse([
            'state Root {',
            '    /* forced docs */ !* -> Error :: Fatal;',
            '    /* combo docs */ Idle -> Active :: E1 + E2;',
            '    state Parent {',
            '        /* target docs */ enter Boot {}',
            '    }',
            '    state Child {',
            '        /* ref docs */ enter ref /Root.Parent.Boot;',
            '    }',
            '    state Error;',
            '    state Idle;',
            '    state Active;',
            '}',
        ].join('\n'));
        const root = ast.rootState!;
        assert.equal(root.forceTransitions[0].doc, 'forced docs');
        assert.equal(root.transitions[0].doc, 'combo docs');
        assert.equal(root.substates[0].enters[0].doc, 'target docs');
        assert.equal(root.substates[1].enters[0].doc, 'ref docs');
        assert.equal(root.substates[1].enters[0].mode, 'ref');
    });

    it('does not attach documentation to import declarations', async () => {
        const source = [
            'state Root {',
            '    /* import docs */ import "./worker.fcstm" as Worker;',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/import-documentation.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.ok(diagnostics.some((item: {severity?: string; message: string}) =>
            item.severity === 'error'));
        const ast = await packageModule.parseAstDocument(document);
        assert.equal('doc' in (ast.rootState!.imports[0] as object), false);
    });
});
