/**
 * esbuild configuration for FCSTM VSCode Extension
 *
 * This configuration bundles all TypeScript sources and dependencies
 * (including antlr4 runtime and generated parser) into a single extension.js file.
 */

const esbuild = require('esbuild');
const path = require('path');

const production = process.argv.includes('--production');
const watch = process.argv.includes('--watch');

/**
 * @type {esbuild.BuildOptions}
 */
const buildOptions = {
  entryPoints: ['src/extension.ts'],
  bundle: true,
  outfile: 'dist/extension.js',

  // VSCode extension configuration
  external: ['vscode'], // VSCode API must be external
  format: 'cjs',        // CommonJS format required by VSCode
  platform: 'node',     // Node.js environment
  target: 'node16',     // VSCode 1.60+ uses Node 16

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
};

async function build() {
  try {
    console.log(`Building extension (${production ? 'production' : 'development'} mode)...`);

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
