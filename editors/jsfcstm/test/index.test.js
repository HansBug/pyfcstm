const assert = require('node:assert/strict');

const packageJson = require('../package.json');
const packageModule = require('../dist/index.js');

function main() {
    const info = packageModule.getJsFcstmPackageInfo();

    assert.equal(info.name, packageJson.name);
    assert.equal(info.version, packageJson.version);
    assert.equal(info.description, packageJson.description);

    assert.equal(packageModule.JSFCSTM_PACKAGE_NAME, packageJson.name);
    assert.equal(packageModule.JSFCSTM_PACKAGE_VERSION, packageJson.version);

    console.log('jsfcstm unit tests passed');
}

main();
