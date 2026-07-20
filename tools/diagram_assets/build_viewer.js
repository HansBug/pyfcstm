const path = require('path');
const fs = require('fs');
const {createRequire} = require('module');
const vscodeRoot = path.resolve(__dirname, '../../editors/vscode');
const requireFromVscode = createRequire(path.join(vscodeRoot, 'package.json'));
const esbuild = requireFromVscode('esbuild');
const vuePlugin = requireFromVscode('unplugin-vue/esbuild');
const fastPngStub = path.resolve(__dirname, 'fast-png-stub.js');

const output = process.argv[2];
if (!output) throw new Error('viewer output directory is required');

esbuild.build({
  entryPoints: {
    viewer: path.resolve(__dirname, '../../editors/vscode/src/preview-webview/standalone.ts'),
  },
  bundle: true,
  outdir: output,
  entryNames: '[name]',
  format: 'iife',
  platform: 'browser',
  target: 'es2019',
  minify: true,
  sourcemap: false,
  metafile: true,
  // jsPDF exposes an optional ``html()`` raster route through dynamic
  // imports. The standalone viewer never calls that API: PNG uses the
  // browser canvas path and PDF uses svg2pdf.js. Leave those optional modules
  // external so they cannot be shipped accidentally or become a hidden
  // network fallback in the self-contained file viewer.
  external: ['canvg', 'html2canvas', 'fast-png', 'dompurify'],
  alias: {'fast-png': fastPngStub},
  define: {
    'process.env.NODE_ENV': '"production"',
    '__VUE_OPTIONS_API__': 'true',
    '__VUE_PROD_DEVTOOLS__': 'false',
    '__VUE_PROD_HYDRATION_MISMATCH_DETAILS__': 'false',
  },
  plugins: [vuePlugin({sourceMap: false})],
}).then(result => {
  fs.writeFileSync(path.join(output, 'viewer.meta.json'), JSON.stringify(result.metafile || {}));
}).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
