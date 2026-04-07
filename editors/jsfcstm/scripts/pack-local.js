const {execFileSync} = require('child_process');
const fs = require('fs');
const path = require('path');

const packageDir = path.resolve(__dirname, '..');
const localTarball = path.join(packageDir, 'jsfcstm.tgz');

function main() {
    const output = execFileSync('npm', ['pack', '--json'], {
        cwd: packageDir,
        encoding: 'utf8',
    });
    const result = JSON.parse(output);
    if (!Array.isArray(result) || !result[0] || !result[0].filename) {
        throw new Error('Unable to resolve npm pack output for jsfcstm.');
    }

    const generatedTarball = path.join(packageDir, result[0].filename);
    fs.copyFileSync(generatedTarball, localTarball);
    console.log(`Created ${path.basename(localTarball)} from ${result[0].filename}`);
}

main();
