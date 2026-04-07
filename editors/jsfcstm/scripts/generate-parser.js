const {execFileSync} = require('child_process');
const fs = require('fs');
const path = require('path');

const packageDir = path.resolve(__dirname, '..');
const outputDir = path.join(packageDir, 'parser');
const projectRoot = path.resolve(packageDir, '..', '..');
const antlrJar = path.join(projectRoot, 'antlr-4.9.3.jar');
const lexerGrammar = path.join(projectRoot, 'pyfcstm', 'dsl', 'grammar', 'GrammarLexer.g4');
const parserGrammar = path.join(projectRoot, 'pyfcstm', 'dsl', 'grammar', 'GrammarParser.g4');

function ensureFile(filePath) {
    if (!fs.existsSync(filePath)) {
        throw new Error(`Required file not found: ${filePath}`);
    }
}

function cleanOutputDir() {
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, {recursive: true});
        return;
    }

    for (const name of fs.readdirSync(outputDir)) {
        fs.rmSync(path.join(outputDir, name), {recursive: true, force: true});
    }
}

function main() {
    ensureFile(antlrJar);
    ensureFile(lexerGrammar);
    ensureFile(parserGrammar);
    cleanOutputDir();

    execFileSync(
        'java',
        [
            '-jar',
            antlrJar,
            '-Dlanguage=JavaScript',
            '-o',
            outputDir,
            '-Xexact-output-dir',
            '-no-listener',
            lexerGrammar,
            parserGrammar,
        ],
        {
            cwd: packageDir,
            stdio: 'inherit',
        }
    );
}

main();
