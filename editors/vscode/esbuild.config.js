/**
 * esbuild configuration for FCSTM VSCode Extension.
 *
 * Produces three bundles in ``dist/``:
 *   1. ``preview-webview.js`` — browser bundle for the Vue-powered webview
 *      (Vue 3 + Naive UI + the local SVG renderer).
 *   2. ``extension.js`` — the VSCode extension host entry. Inlines the
 *      webview bundle + the elkjs runtime via esbuild plugins so the
 *      webview HTML shell can drop them straight into ``<script>`` tags.
 *   3. ``server.js`` — the language server entry (unchanged).
 */

const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');
const vuePlugin = require('unplugin-vue/esbuild');

const production = process.argv.includes('--production');
const watch = process.argv.includes('--watch');

function prepareOutputDirectory() {
  const outputDir = path.resolve(__dirname, 'dist');
  fs.rmSync(outputDir, {recursive: true, force: true});
  fs.mkdirSync(outputDir, {recursive: true});
}

function loadElkRuntimeSource() {
  const sourceFile = path.resolve(__dirname, 'node_modules', 'elkjs', 'lib', 'elk.bundled.js');

  if (!fs.existsSync(sourceFile)) {
    throw new Error(`Missing ELK runtime source: ${sourceFile}`);
  }
  return fs.readFileSync(sourceFile, 'utf8');
}

function loadPreviewWebviewSource() {
  const jsFile = path.resolve(__dirname, 'dist', 'preview-webview.js');
  const cssFile = path.resolve(__dirname, 'dist', 'preview-webview.css');
  if (!fs.existsSync(jsFile)) {
    throw new Error(`Missing preview-webview bundle: ${jsFile}. Did the webview build run?`);
  }
  const js = fs.readFileSync(jsFile, 'utf8');
  const css = fs.existsSync(cssFile) ? fs.readFileSync(cssFile, 'utf8') : '';
  // Prepend a tiny bootstrap that injects the component styles at runtime
  // so the single-script inline path carries both JS and CSS together.
  if (!css) return js;
  const injector = `(function(){var s=document.createElement('style');s.setAttribute('data-fcstm-preview','true');s.textContent=${JSON.stringify(css)};document.head.appendChild(s);})();\n`;
  return injector + js;
}

const elkInlinePlugin = {
  name: 'elk-inline',
  setup(build) {
    const elkSource = loadElkRuntimeSource();

    build.onResolve({filter: /^@fcstm\/elk-inline$/}, args => ({
      path: args.path,
      namespace: 'fcstm-elk-inline',
    }));

    build.onLoad({filter: /.*/, namespace: 'fcstm-elk-inline'}, () => ({
      contents: `export default ${JSON.stringify(elkSource)};`,
      loader: 'js',
    }));
  },
};

const previewWebviewInlinePlugin = {
  name: 'preview-webview-inline',
  setup(build) {
    build.onResolve({filter: /^@fcstm\/preview-webview-inline$/}, args => ({
      path: args.path,
      namespace: 'fcstm-preview-webview-inline',
    }));

    build.onLoad({filter: /.*/, namespace: 'fcstm-preview-webview-inline'}, () => {
      const src = loadPreviewWebviewSource();
      return {contents: `export default ${JSON.stringify(src)};`, loader: 'js'};
    });
  },
};

/**
 * Browser bundle for the Vue webview.
 * @type {esbuild.BuildOptions}
 */
const webviewOptions = {
  entryPoints: {
    'preview-webview': 'src/preview-webview/main.ts',
  },
  bundle: true,
  outdir: 'dist',
  entryNames: '[name]',
  format: 'iife',
  platform: 'browser',
  target: 'es2019',
  // unplugin-vue's inline style loading trips on esbuild's sourcemap
  // comments; keep source maps linked / off for the webview bundle.
  sourcemap: production ? false : 'linked',
  minify: production,
  keepNames: true,
  treeShaking: true,
  metafile: true,
  logLevel: 'info',
  define: {
    'process.env.NODE_ENV': production ? '"production"' : '"development"',
    '__VUE_OPTIONS_API__': 'true',
    '__VUE_PROD_DEVTOOLS__': 'false',
    '__VUE_PROD_HYDRATION_MISMATCH_DETAILS__': 'false',
  },
  // unplugin-vue's PostCSS path trips on esbuild's inline sourcemap
  // comments inside <style>. Disabling SFC sourcemaps works around it.
  plugins: [vuePlugin({sourceMap: false})],
};

/**
 * Extension host bundle. Depends on preview-webview.js being built first.
 * @type {esbuild.BuildOptions}
 */
const extensionOptions = {
  entryPoints: {
    extension: 'src/extension.ts',
    server: 'src/server.ts',
  },
  bundle: true,
  outdir: 'dist',
  entryNames: '[name]',
  external: ['vscode'],
  format: 'cjs',
  platform: 'node',
  target: 'es2015',
  sourcemap: production ? false : 'inline',
  minify: production,
  keepNames: true,
  treeShaking: true,
  metafile: true,
  logLevel: 'info',
  define: {
    'process.env.NODE_ENV': production ? '"production"' : '"development"',
  },
  plugins: [elkInlinePlugin, previewWebviewInlinePlugin],
};

async function build() {
  try {
    console.log(`Building FCSTM extension (${production ? 'production' : 'development'} mode)...`);
    prepareOutputDirectory();

    if (watch) {
      // Watch mode builds webview once, then watches extension;
      // re-watching Vue SFCs needs manual retrigger via ``npm run watch``.
      console.log('Building preview webview bundle...');
      const webviewCtx = await esbuild.context(webviewOptions);
      await webviewCtx.watch();
      console.log('Preview webview bundle watching.');

      const extCtx = await esbuild.context(extensionOptions);
      await extCtx.watch();
      console.log('Extension bundle watching.');
    } else {
      console.log('Building preview webview bundle...');
      const webviewResult = await esbuild.build(webviewOptions);
      if (webviewResult.metafile) {
        console.log('\nPreview webview bundle analysis:');
        console.log(await esbuild.analyzeMetafile(webviewResult.metafile, {verbose: false}));
      }

      console.log('Building extension bundle...');
      const extResult = await esbuild.build(extensionOptions);
      if (extResult.metafile) {
        console.log('\nExtension bundle analysis:');
        console.log(await esbuild.analyzeMetafile(extResult.metafile, {verbose: false}));
      }

      console.log('Build complete!');
    }
  } catch (error) {
    console.error('Build failed:', error);
    process.exit(1);
  }
}

build();
