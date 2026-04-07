import assert from 'node:assert/strict';

import {packageJson, packageModule} from './support';

describe('jsfcstm package metadata', () => {
    it('exports package metadata', () => {
        const info = packageModule.getJsFcstmPackageInfo();

        assert.equal(info.name, packageJson.name);
        assert.equal(info.version, packageJson.version);
        assert.equal(info.description, packageJson.description);
        assert.equal(packageModule.JSFCSTM_PACKAGE_NAME, packageJson.name);
        assert.equal(packageModule.JSFCSTM_PACKAGE_VERSION, packageJson.version);
    });
});
