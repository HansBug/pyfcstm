/**
 * ESLint flat configuration for the FCSTM VSCode extension.
 *
 * ESLint 9 made ``eslint.config.js`` the default configuration format and
 * ESLint 10 dropped ``.eslintrc.*`` support entirely, so the previous
 * ``.eslintrc.json`` is replaced by this file. The rule set is the flat-config
 * equivalent of the old one: ``eslint:recommended`` plus the recommended
 * TypeScript rules, with the same two local overrides.
 */

const js = require('@eslint/js');
const tsParser = require('@typescript-eslint/parser');
const tsPlugin = require('@typescript-eslint/eslint-plugin');

module.exports = [
  // Replaces the old ``ignorePatterns``. Generated parser output, compiled
  // artifacts and plain JS tooling files are not linted.
  {
    ignores: [
      'out/**',
      'parser/**',
      'dist/**',
      'build/**',
      '**/*.js',
      '**/*.mjs',
      '**/*.cjs',
    ],
  },
  js.configs.recommended,
  // ``flat/recommended`` also disables the base rules that the TypeScript
  // versions supersede, so it must come after ``js.configs.recommended``.
  ...tsPlugin.configs['flat/recommended'],
  {
    // Matches every TypeScript file the old config covered. Scoping this to
    // ``src`` would make the overrides below narrower than ``.eslintrc.json``
    // was, so a direct ``eslint .`` would grade differently from ``npm run
    // lint``.
    files: ['**/*.ts'],
    languageOptions: {
      // ``ecmaVersion`` and ``sourceType`` belong on ``languageOptions`` in flat
      // config; nesting them only under ``parserOptions`` would leave the core
      // rules running at the flat default instead of the previous ES2020.
      ecmaVersion: 2020,
      sourceType: 'module',
      parser: tsParser,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['warn', {argsIgnorePattern: '^_'}],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
];
