const assert = require('assert');
const path = require('path');
const {pathToFileURL} = require('url');
const {getParser, FcstmLanguageServerCore} = require('..');

async function main() {
    const text = [
        'state Root {',
        'event Next;',
        'state A { enter ref Missing; }',
        'state B;',
        '[*] -> A;',
        'A -> B : Next;',
        '}',
    ].join('\n');
    assert.strictEqual((await getParser().parse(text)).errors.length, 0);
    const publications = [];
    const core = new FcstmLanguageServerCore({
        onDiagnostics: publication => publications.push(publication),
    });
    const uri = pathToFileURL(path.join(__dirname, 'runtime-check.fcstm')).href;
    await core.openTextDocument({uri, languageId: 'fcstm', version: 1, text});
    assert(publications.some(publication => publication.diagnostics.some(
        diagnostic => diagnostic.code === 'E_NAMED_FUNCTION_REF_NOT_FOUND'
    )));
    const references = await core.provideReferences(uri, {line: 1, character: 7}, true);
    assert.deepStrictEqual(references.map(reference => reference.range.start.line).sort(), [1, 5]);
    console.log(`Public package parser, diagnostics and references passed on ${process.version}`);
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
