'use strict';

const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const esbuild = require('esbuild');

const entry = path.resolve(__dirname, 'verify-preview-geometry.ts');
const output = path.join(os.tmpdir(), `fcstm-preview-geometry-${process.pid}.cjs`);
try {
    esbuild.buildSync({
        entryPoints: [entry],
        bundle: true,
        platform: 'node',
        format: 'cjs',
        target: 'node16',
        outfile: output,
        external: ['vscode'],
        logLevel: 'warning',
    });
    require(output);
} finally {
    fs.rmSync(output, {force: true});
}
