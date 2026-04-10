/**
 * esbuild configuration for FCSTM VSCode Extension
 *
 * This configuration bundles the VSCode client entry point and the bundled
 * Node-based language server entry point into dist/.
 */

const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const production = process.argv.includes('--production');
const watch = process.argv.includes('--watch');

function prepareOutputDirectory() {
  const outputDir = path.resolve(__dirname, 'dist');
  fs.rmSync(outputDir, {recursive: true, force: true});
}

function loadMermaidRuntimeSource() {
  const sourceFile = path.resolve(__dirname, 'node_modules', 'mermaid', 'dist', 'mermaid.min.js');

  if (!fs.existsSync(sourceFile)) {
    throw new Error(`Missing Mermaid runtime source: ${sourceFile}`);
  }
  return fs.readFileSync(sourceFile, 'utf8');
}

const mermaidInlinePlugin = {
  name: 'mermaid-inline',
  setup(build) {
    const mermaidSource = loadMermaidRuntimeSource();

    build.onResolve({filter: /^@fcstm\/mermaid-inline$/}, args => {
      return {
        path: args.path,
        namespace: 'fcstm-mermaid-inline',
      };
    });

    build.onLoad({filter: /.*/, namespace: 'fcstm-mermaid-inline'}, () => {
      return {
        contents: `export default ${JSON.stringify(mermaidSource)};`,
        loader: 'js',
      };
    });
  },
};

/**
 * @type {esbuild.BuildOptions}
 */
const buildOptions = {
  entryPoints: {
    extension: 'src/extension.ts',
    server: 'src/server.ts',
  },
  bundle: true,
  outdir: 'dist',
  entryNames: '[name]',

  // VSCode extension configuration
  external: ['vscode'], // VSCode API must stay external to the bundle
  format: 'cjs',        // CommonJS format required by VSCode
  platform: 'node',     // Node.js environment
  target: 'es2015',    // Prefer broad compatibility with older VSCode extension hosts

  // Source maps for debugging
  sourcemap: production ? false : 'inline',

  // Minification for production
  minify: production,

  // Keep names for better stack traces
  keepNames: true,

  // Tree shaking
  treeShaking: true,

  // Metadata for analysis
  metafile: true,

  // Log level
  logLevel: 'info',

  // Define environment variables
  define: {
    'process.env.NODE_ENV': production ? '"production"' : '"development"'
  },

  plugins: [mermaidInlinePlugin],
};

async function build() {
  try {
    console.log(`Building extension (${production ? 'production' : 'development'} mode)...`);
    prepareOutputDirectory();

    if (watch) {
      const context = await esbuild.context(buildOptions);
      await context.watch();
      console.log('Watching for changes...');
    } else {
      const result = await esbuild.build(buildOptions);

      // Print bundle size
      if (result.metafile) {
        const text = await esbuild.analyzeMetafile(result.metafile, {
          verbose: false,
        });
        console.log('\nBundle analysis:');
        console.log(text);
      }

      console.log('Build complete!');
    }
  } catch (error) {
    console.error('Build failed:', error);
    process.exit(1);
  }
}

build();
