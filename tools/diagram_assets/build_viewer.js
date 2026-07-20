const path = require('path');
const fs = require('fs');
const {createRequire} = require('module');
const vscodeRoot = path.resolve(__dirname, '../../editors/vscode');
const requireFromVscode = createRequire(path.join(vscodeRoot, 'package.json'));
const esbuild = requireFromVscode('esbuild');
const vuePlugin = requireFromVscode('unplugin-vue/esbuild');
const fastPngStub = path.resolve(__dirname, 'fast-png-stub.js');

const forbiddenOptionalPackages = ['canvg', 'html2canvas', 'dompurify'];
const disabledOptionalPackageNames = new Map(
  forbiddenOptionalPackages.map((name, index) => [name, `__pyfcstm_disabled_optional_${index}__`]),
);

function stripOptionalJspdfDependencies() {
  return {
    name: 'strip-optional-jspdf-dependencies',
    setup(build) {
      build.onLoad({filter: /jspdf\.es\.min\.js$/}, async args => {
        let contents = await fs.promises.readFile(args.path, 'utf8');
        for (const packageName of forbiddenOptionalPackages) {
          // jsPDF only reaches these imports through its optional ``html`` or
          // raster-image APIs. The standalone viewer never calls those APIs;
          // replacing the package literals prevents a hidden network/import
          // fallback while leaving the vector PDF API intact.
          contents = contents.split(packageName).join(disabledOptionalPackageNames.get(packageName));
        }
        return {contents, loader: 'js'};
      });
    },
  };
}

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
  external: [
    'canvg', 'html2canvas', 'fast-png', 'dompurify',
    '__pyfcstm_disabled_optional_0__',
    '__pyfcstm_disabled_optional_1__',
    '__pyfcstm_disabled_optional_2__',
  ],
  alias: {'fast-png': fastPngStub},
  define: {
    'process.env.NODE_ENV': '"production"',
    '__VUE_OPTIONS_API__': 'true',
    '__VUE_PROD_DEVTOOLS__': 'false',
    '__VUE_PROD_HYDRATION_MISMATCH_DETAILS__': 'false',
  },
  plugins: [vuePlugin({sourceMap: false}), stripOptionalJspdfDependencies()],
}).then(result => {
  fs.writeFileSync(path.join(output, 'viewer.meta.json'), JSON.stringify(result.metafile || {}));
}).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
