#!/usr/bin/env node

const fs = require('fs');
const os = require('os');
const path = require('path');
const {spawnSync} = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const EXPECTED_ENTRIES = [
  '[Content_Types].xml',
  'extension.vsixmanifest',
  'extension/LICENSE.txt',
  'extension/README.md',
  'extension/dist/extension.js',
  'extension/dist/preview-webview.css',
  'extension/dist/preview-webview.js',
  'extension/dist/server.js',
  'extension/language-configuration.json',
  'extension/package.json',
  'extension/resources/icon.png',
  'extension/snippets/fcstm.code-snippets',
  'extension/syntaxes/fcstm.tmLanguage.json',
];
const FORBIDDEN_PATTERNS = [
  /^extension\/src\//,
  /^extension\/test\//,
  /^extension\/scripts\//,
  /^extension\/parser\//,
  /^extension\/out\//,
  /^extension\/node_modules\//,
  /^extension\/\.vscode\//,
  /^extension\/\.vscode-test\//,
  /^extension\/\.github\//,
  /^extension\/build\//,
  /^extension\/syntaxes\/fcstm-bmc-query\.tmLanguage\.json$/,
  /\.map$/,
  /(?:^|\/)README_acceptance\.md$/,
  /^extension\/(?:TODO|PARSER|DEPENDENCY-FIX|BUILD-IMPROVEMENTS)\.md$/,
  /^extension\/(?:Makefile|tsconfig\.json|esbuild\.config\.js|\.eslintrc\.json|package-lock\.json)$/,
  /^extension\/.*\.(?:vsix|whl|tar\.gz|pdf|exe)$/,
];

function fail(message) {
  throw new Error(message);
}

function run(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, ...options});
  if (result.status !== 0) {
    fail(`${cmd} ${args.join(' ')} failed: ${(result.stderr || result.stdout || '').trim()}`);
  }
  return result.stdout;
}

function zipEntries(vsixPath) {
  return run('unzip', ['-Z1', vsixPath]).split(/\r?\n/).filter(Boolean).sort();
}

function zipText(vsixPath, entry) {
  return run('unzip', ['-p', vsixPath, entry]);
}

function assertEntrySet(entries) {
  const expected = [...EXPECTED_ENTRIES].sort();
  const actual = [...entries].sort();
  if (actual.length !== expected.length || actual.some((entry, index) => entry !== expected[index])) {
    const missing = expected.filter(entry => !actual.includes(entry));
    const extra = actual.filter(entry => !expected.includes(entry));
    fail(`VSIX entries differ from acceptance contract. missing=${JSON.stringify(missing)} extra=${JSON.stringify(extra)} actual=${JSON.stringify(actual)}`);
  }
  for (const entry of actual) {
    const denied = FORBIDDEN_PATTERNS.find(pattern => pattern.test(entry));
    if (denied) {
      fail(`Forbidden VSIX entry ${entry} matched ${denied}`);
    }
  }
}

function assertManifest(vsixPath) {
  const packageJson = JSON.parse(zipText(vsixPath, 'extension/package.json'));
  if (packageJson.name !== 'fcstm-language-support') {
    fail(`Unexpected extension name ${packageJson.name}`);
  }
  if (packageJson.publisher !== 'hansbug') {
    fail(`Unexpected extension publisher ${packageJson.publisher}`);
  }
  if (packageJson.version !== '0.1.0') {
    fail(`Unexpected extension version ${packageJson.version}`);
  }
  if (packageJson.main !== './dist/extension.js') {
    fail(`Unexpected extension main ${packageJson.main}`);
  }
  const languages = packageJson.contributes && packageJson.contributes.languages || [];
  const fcstmLanguage = languages.find(item => item.id === 'fcstm');
  if (!fcstmLanguage || !Array.isArray(fcstmLanguage.extensions) || !fcstmLanguage.extensions.includes('.fcstm')) {
    fail('package.json does not contribute the .fcstm language');
  }
  const grammars = packageJson.contributes && packageJson.contributes.grammars || [];
  if (!grammars.some(item => item.language === 'fcstm' && item.path === './syntaxes/fcstm.tmLanguage.json')) {
    fail('package.json does not point to the packaged TextMate grammar');
  }
  const snippets = packageJson.contributes && packageJson.contributes.snippets || [];
  if (!snippets.some(item => item.language === 'fcstm' && item.path === './snippets/fcstm.code-snippets')) {
    fail('package.json does not point to the packaged snippets');
  }
  const commands = packageJson.contributes && packageJson.contributes.commands || [];
  for (const command of ['fcstm.preview.open', 'fcstm.preview.openAlone', 'fcstm.preview.toggle', 'fcstm.preview.export']) {
    if (!commands.some(item => item.command === command)) {
      fail(`package.json is missing preview command ${command}`);
    }
  }
  const manifest = zipText(vsixPath, 'extension.vsixmanifest');
  if (!manifest.includes('Id="fcstm-language-support"') || !manifest.includes('Publisher="hansbug"') || !manifest.includes('Version="0.1.0"')) {
    fail('extension.vsixmanifest does not expose hansbug/fcstm-language-support@0.1.0');
  }

  const assetPaths = Array.from(manifest.matchAll(/<Asset\b[^>]*\bPath="([^"]+)"/g), match => match[1]);
  const entries = new Set(zipEntries(vsixPath));
  for (const assetPath of assetPaths) {
    if (!entries.has(assetPath)) {
      fail(`extension.vsixmanifest Asset path does not match a packaged entry exactly: ${assetPath}`);
    }
  }
  const readme = zipText(vsixPath, 'extension/README.md');
  if (!readme.startsWith('# FCSTM VS Code 扩展验收版')) {
    fail('VSIX README is not the extension README');
  }
  for (const forbidden of ['BMC', 'SMT', 'LLM', 'node_modules', 'ANTLR', 'PyPI']) {
    if (readme.includes(forbidden)) {
      fail(`VSIX README contains forbidden maintenance/research term: ${forbidden}`);
    }
  }
}

function assertJavaScriptSyntax(vsixPath) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsix-js-'));
  try {
    for (const entry of ['extension/dist/extension.js', 'extension/dist/server.js', 'extension/dist/preview-webview.js']) {
      const target = path.join(tempDir, path.basename(entry));
      fs.writeFileSync(target, zipText(vsixPath, entry));
      run(process.execPath, ['--check', target]);
    }
  } finally {
    fs.rmSync(tempDir, {recursive: true, force: true});
  }
}

function assertBundleOffline(vsixPath) {
  for (const entry of ['extension/dist/extension.js', 'extension/dist/server.js', 'extension/dist/preview-webview.js']) {
    const text = zipText(vsixPath, entry);
    for (const needle of ["require(\"../src", "require('../src", "require(\"../node_modules", "require('../node_modules", "require(\"../../", "require('../../"]) {
      if (text.includes(needle)) {
        fail(`${entry} appears to require unpackaged runtime path ${needle}`);
      }
    }
  }
}

function checkVsix(vsixPath) {
  const resolved = path.resolve(vsixPath);
  if (!fs.existsSync(resolved)) {
    fail(`VSIX does not exist: ${resolved}`);
  }
  if (path.basename(resolved) !== 'fcstm-language-support-0.1.0.vsix') {
    fail(`Unexpected VSIX filename: ${path.basename(resolved)}`);
  }
  const magic = fs.readFileSync(resolved).subarray(0, 4).toString('hex');
  if (magic !== '504b0304') {
    fail(`VSIX does not start with ZIP magic: ${magic}`);
  }
  const siblings = fs.readdirSync(path.dirname(resolved)).filter(name => name.endsWith('.vsix'));
  if (siblings.length !== 1 || siblings[0] !== path.basename(resolved)) {
    fail(`VSIX output directory must contain exactly the target VSIX, found ${JSON.stringify(siblings)}`);
  }
  const entries = zipEntries(resolved);
  assertEntrySet(entries);
  assertManifest(resolved);
  assertJavaScriptSyntax(resolved);
  assertBundleOffline(resolved);
  console.log(`VSIX archive contract OK: ${resolved}`);
  console.log(`entries=${entries.length}`);
}

function createFixture(tempDir, entries, packageOverrides = {}) {
  const payloadDir = path.join(tempDir, 'payload');
  fs.mkdirSync(payloadDir, {recursive: true});
  for (const entry of entries) {
    const file = path.join(payloadDir, entry);
    fs.mkdirSync(path.dirname(file), {recursive: true});
    if (entry === 'extension/package.json') {
      const pkg = {
        name: 'fcstm-language-support',
        publisher: 'hansbug',
        version: '0.1.0',
        main: './dist/extension.js',
        contributes: {
          languages: [{id: 'fcstm', extensions: ['.fcstm'], configuration: './language-configuration.json'}],
          grammars: [{language: 'fcstm', scopeName: 'source.fcstm', path: './syntaxes/fcstm.tmLanguage.json'}],
          snippets: [{language: 'fcstm', path: './snippets/fcstm.code-snippets'}],
          commands: [
            {command: 'fcstm.preview.open', title: 'Open Preview'},
            {command: 'fcstm.preview.openAlone', title: 'Open Preview (Diagram Only)'},
            {command: 'fcstm.preview.toggle', title: 'Toggle Preview Layout'},
            {command: 'fcstm.preview.export', title: 'Export Preview Diagram'},
          ],
        },
        ...packageOverrides,
      };
      fs.writeFileSync(file, JSON.stringify(pkg, null, 2));
    } else if (entry === 'extension.vsixmanifest') {
      fs.writeFileSync(file, '<PackageManifest Version="2.0.0"><Metadata><Identity Id="fcstm-language-support" Version="0.1.0" Publisher="hansbug" /></Metadata></PackageManifest>');
    } else if (entry === 'extension/README.md') {
      fs.writeFileSync(file, '# FCSTM VS Code 扩展验收版\n\n本 VSIX 用于 项目验收。\n');
    } else if (entry.endsWith('.js')) {
      fs.writeFileSync(file, 'const acceptance = true;\n');
    } else {
      fs.writeFileSync(file, 'acceptance\n');
    }
  }
  const vsix = path.join(tempDir, 'fcstm-language-support-0.1.0.vsix');
  run('python3', ['-c', `import pathlib, zipfile\nroot=pathlib.Path(${JSON.stringify(payloadDir)})\nout=pathlib.Path(${JSON.stringify(vsix)})\nwith zipfile.ZipFile(out, 'w') as z:\n    for p in sorted(root.rglob('*')):\n        if p.is_file():\n            z.write(p, p.relative_to(root).as_posix())\n`]);
  return vsix;
}

function assertFails(label, fn) {
  try {
    fn();
  } catch (error) {
    console.log(`expected failure: ${label}: ${error.message.split('\n')[0]}`);
    return;
  }
  fail(`Expected failure did not occur: ${label}`);
}

function selfCheck() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsix-check-'));
  try {
    const good = createFixture(tempDir, EXPECTED_ENTRIES);
    checkVsix(good);

    const missingDir = fs.mkdtempSync(path.join(tempDir, 'missing-'));
    assertFails('missing server bundle', () => checkVsix(createFixture(missingDir, EXPECTED_ENTRIES.filter(entry => entry !== 'extension/dist/server.js'))));

    const extraDir = fs.mkdtempSync(path.join(tempDir, 'extra-'));
    assertFails('extra source file', () => checkVsix(createFixture(extraDir, [...EXPECTED_ENTRIES, 'extension/src/extension.ts'])));

    const bmcDir = fs.mkdtempSync(path.join(tempDir, 'bmc-'));
    assertFails('extra BMC grammar', () => checkVsix(createFixture(bmcDir, [...EXPECTED_ENTRIES, 'extension/syntaxes/fcstm-bmc-query.tmLanguage.json'])));

    const badPkgDir = fs.mkdtempSync(path.join(tempDir, 'badpkg-'));
    assertFails('wrong extension id', () => checkVsix(createFixture(badPkgDir, EXPECTED_ENTRIES, {name: 'wrong'})));

    console.log('VSIX checker self-check OK');
  } finally {
    fs.rmSync(tempDir, {recursive: true, force: true});
  }
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes('--check')) {
    selfCheck();
    return;
  }
  const vsixIndex = args.indexOf('--vsix');
  const vsixPath = vsixIndex >= 0 ? args[vsixIndex + 1] : args[0];
  if (!vsixPath) {
    console.error('Usage: node scripts/check-vsix.js --vsix <path> | --check');
    process.exit(2);
  }
  checkVsix(vsixPath);
}

try {
  main();
} catch (error) {
  console.error(`VSIX check failed: ${error.message}`);
  process.exit(1);
}
