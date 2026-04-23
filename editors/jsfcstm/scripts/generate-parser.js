const {execFileSync} = require('child_process');
const fs = require('fs');
const path = require('path');

const packageDir = path.resolve(__dirname, '..');
const outputDir = path.join(packageDir, 'src', 'dsl', 'grammar');
const legacyOutputDir = path.join(packageDir, 'parser');
const projectRoot = path.resolve(packageDir, '..', '..');
const antlrJar = path.join(projectRoot, 'antlr-4.9.3.jar');
const lexerGrammar = path.join(projectRoot, 'pyfcstm', 'dsl', 'grammar', 'GrammarLexer.g4');
const parserGrammar = path.join(projectRoot, 'pyfcstm', 'dsl', 'grammar', 'GrammarParser.g4');

function ensureFile(filePath) {
    if (!fs.existsSync(filePath)) {
        throw new Error(`Required file not found: ${filePath}`);
    }
}

function cleanOutputDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, {recursive: true});
        return;
    }

    for (const name of fs.readdirSync(dirPath)) {
        fs.rmSync(path.join(dirPath, name), {recursive: true, force: true});
    }
}

function main() {
    ensureFile(antlrJar);
    ensureFile(lexerGrammar);
    ensureFile(parserGrammar);
    cleanOutputDir(outputDir);
    fs.rmSync(legacyOutputDir, {recursive: true, force: true});

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
