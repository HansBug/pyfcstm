#!/usr/bin/env node

const fs = require('fs');
const os = require('os');
const path = require('path');
const {spawnSync} = require('child_process');

function fail(message) {
  throw new Error(message);
}

function which(name) {
  const result = spawnSync('which', [name], {encoding: 'utf8'});
  return result.status === 0 ? result.stdout.trim() : '';
}

function run(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, {encoding: 'utf8', stdio: 'pipe', ...options});
  if (result.status !== 0) {
    fail(`${cmd} ${args.join(' ')} failed with ${result.status}\nSTDOUT:\n${result.stdout}\nSTDERR:\n${result.stderr}`);
  }
  return result;
}

function parseArgs(argv) {
  const args = {vsix: process.env.VSIX_PATH, out: process.env.SMOKE_OUT, code: process.env.CODE_BIN || 'code'};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--vsix') args.vsix = argv[++i];
    else if (argv[i] === '--out') args.out = argv[++i];
    else if (argv[i] === '--code') args.code = argv[++i];
    else fail(`Unknown argument: ${argv[i]}`);
  }
  if (!args.vsix) fail('VSIX_PATH or --vsix is required');
  if (!args.out) args.out = fs.mkdtempSync(path.join(os.tmpdir(), 'vscode-smoke-'));
  return args;
}

function writeDriver(driverDir, resultPath) {
  fs.mkdirSync(driverDir, {recursive: true});
  fs.writeFileSync(path.join(driverDir, 'package.json'), JSON.stringify({
    name: 'vscode-smoke-driver',
    publisher: 'hansbug',
    version: '0.0.0',
    engines: {vscode: '^1.60.0'},
    activationEvents: ['*'],
    main: './extension.js',
  }, null, 2));
  fs.writeFileSync(path.join(driverDir, 'extension.js'), `
const fs = require('fs');
const path = require('path');
const vscode = require('vscode');

const resultPath = ${JSON.stringify(resultPath)};
const workspacePath = process.env.SMOKE_WORKSPACE;
const exportOut = process.env.SMOKE_EXPORT_OUT;
const installedExtensionPath = process.env.SMOKE_INSTALLED_EXTENSION_PATH;

function writeResult(data) {
  fs.mkdirSync(path.dirname(resultPath), {recursive: true});
  fs.writeFileSync(resultPath, JSON.stringify(data, null, 2));
}
function assert(condition, message) {
  if (!condition) throw new Error(message);
}
async function waitFor(label, fn, timeoutMs = 12000) {
  const started = Date.now();
  let last;
  while (Date.now() - started < timeoutMs) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (error) {
      last = error;
    }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Timed out waiting for ' + label + (last ? ': ' + last.message : ''));
}
async function openFcstm(name) {
  const uri = vscode.Uri.file(path.join(workspacePath, name));
  const doc = await vscode.workspace.openTextDocument(uri);
  if (doc.languageId !== 'fcstm') {
    await vscode.languages.setTextDocumentLanguage(doc, 'fcstm');
  }
  await vscode.window.showTextDocument(doc);
  return doc;
}
function diagnosticCount(doc) {
  return vscode.languages.getDiagnostics(doc.uri).length;
}
async function runSmoke() {
  const extension = vscode.extensions.getExtension('hansbug.fcstm-language-support');
  assert(extension, 'Installed extension was not found');
  assert(installedExtensionPath, 'SMOKE_INSTALLED_EXTENSION_PATH is required');
  assert(path.resolve(extension.extensionPath) === path.resolve(installedExtensionPath), 'Extension did not load from the isolated install dir: ' + extension.extensionPath);
  for (const rel of ['package.json', 'dist/extension.js', 'dist/server.js', 'dist/preview-webview.js', 'dist/preview-webview.css', 'syntaxes/fcstm.tmLanguage.json', 'snippets/fcstm.code-snippets']) {
    assert(fs.existsSync(path.join(extension.extensionPath, rel)), 'Installed extension missing runtime file: ' + rel);
  }
  await extension.activate();
  assert(extension.isActive, 'Installed extension did not activate');

  const good = await openFcstm('acceptance.fcstm');

  const bad = await openFcstm('broken.fcstm');
  const badDiagnostics = await waitFor('bad diagnostics', () => diagnosticCount(bad));
  assert(badDiagnostics > 0, 'Broken FCSTM file did not produce diagnostics');

  const edit = new vscode.WorkspaceEdit();
  edit.replace(bad.uri, new vscode.Range(new vscode.Position(0, 0), new vscode.Position(bad.lineCount, 0)), good.getText());
  await vscode.workspace.applyEdit(edit);
  await bad.save();
  try {
    await waitFor('diagnostics cleared after repair', () => diagnosticCount(bad) === 0);
  } catch (error) {
    const diagnostics = vscode.languages.getDiagnostics(bad.uri).map(item => ({
      message: item.message,
      severity: item.severity,
      source: item.source,
      range: item.range,
    }));
    throw new Error(error.message + '\\nDocument version: ' + bad.version + '\\nDocument text: ' + JSON.stringify(bad.getText()) + '\\nDiagnostics: ' + JSON.stringify(diagnostics));
  }

  await vscode.window.showTextDocument(good);
  const symbols = await vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider', good.uri);
  assert(Array.isArray(symbols) && symbols.length > 0, 'Document symbols/outline are empty');
  const completions = await vscode.commands.executeCommand('vscode.executeCompletionItemProvider', good.uri, new vscode.Position(1, 0));
  assert(completions && Array.isArray(completions.items) && completions.items.length > 0, 'Completion provider returned no items');
  const hovers = await vscode.commands.executeCommand('vscode.executeHoverProvider', good.uri, new vscode.Position(1, 6));
  assert(Array.isArray(hovers), 'Hover provider did not return an array');
  const formatted = await vscode.commands.executeCommand('vscode.executeFormatDocumentProvider', good.uri, {tabSize: 4, insertSpaces: true});
  assert(Array.isArray(formatted), 'Formatter did not return edits');
  const codeActions = await vscode.commands.executeCommand('vscode.executeCodeActionProvider', good.uri, new vscode.Range(new vscode.Position(0, 0), new vscode.Position(0, 1)));
  assert(Array.isArray(codeActions), 'Code action provider did not return an array');
  const semanticTokens = await vscode.commands.executeCommand('vscode.provideDocumentSemanticTokens', good.uri);
  assert(semanticTokens && semanticTokens.data && semanticTokens.data.length > 0, 'Semantic tokens are empty');

  await vscode.commands.executeCommand('fcstm.preview.openAlone', good.uri);
  await new Promise(resolve => setTimeout(resolve, 2200));

  const exportSummary = {};
  for (const [format, spec] of Object.entries({
    svg: {name: 'exported.svg', magic: '<svg'},
    png: {name: 'exported.png', magic: '89504e47'},
    pdf: {name: 'exported.pdf', magic: '%PDF'},
  })) {
    const file = path.join(exportOut, spec.name);
    const started = Date.now();
    const delivered = await vscode.commands.executeCommand('fcstm.preview.export', {
      format,
      destination: vscode.Uri.file(file),
    });
    assert(delivered === true, 'Preview export request was not delivered to the webview');
    await waitFor('preview export ' + spec.name, () => fs.existsSync(file) && fs.statSync(file).size > 16, 30000);
    const buf = fs.readFileSync(file);
    if (format === 'svg') assert(buf.toString('utf8', 0, Math.min(buf.length, 256)).includes(spec.magic), 'SVG export magic mismatch');
    if (format === 'png') assert(buf.subarray(0, 4).toString('hex') === spec.magic, 'PNG export magic mismatch');
    if (format === 'pdf') assert(buf.toString('utf8', 0, 4) === spec.magic, 'PDF export magic mismatch');
    exportSummary[spec.name] = {bytes: buf.length, durationMs: Date.now() - started};
  }

  return {
    extensionId: extension.id,
    extensionVersion: extension.packageJSON && extension.packageJSON.version,
    extensionPath: extension.extensionPath,
    diagnostics: {broken: badDiagnostics, repaired: diagnosticCount(bad), good: diagnosticCount(good)},
    language: good.languageId,
    symbols: symbols.length,
    completions: completions.items.length,
    hovers: hovers.length,
    formatEdits: formatted.length,
    codeActions: codeActions.length,
    semanticTokenIntegers: semanticTokens.data.length,
    exports: exportSummary,
  };
}
async function activate() {
  try {
    const summary = await runSmoke();
    writeResult({ok: true, summary});
  } catch (error) {
    writeResult({ok: false, error: error && error.stack ? error.stack : String(error)});
  } finally {
    setTimeout(() => vscode.commands.executeCommand('workbench.action.closeWindow'), 500);
  }
}
exports.activate = activate;
`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const vsix = path.resolve(args.vsix);
  if (!fs.existsSync(vsix)) fail(`VSIX does not exist: ${vsix}`);
  const out = path.resolve(args.out);
  fs.rmSync(out, {recursive: true, force: true});
  fs.mkdirSync(out, {recursive: true});

  const xvfb = which('xvfb-run');
  if (!xvfb) fail('xvfb-run is required for smoke-vscode on Linux; refusing to fake a green result');
  const codeBin = which(args.code) || args.code;
  if (!codeBin || !fs.existsSync(codeBin)) fail(`VS Code binary not found: ${args.code}`);

  const userData = path.join(out, 'user-data');
  const extensions = path.join(out, 'extensions');
  const workspace = path.join(out, 'workspace');
  const driver = path.join(out, 'driver-extension');
  const exportsDir = path.join(out, 'exports');
  const resultPath = path.join(out, 'result.json');
  fs.mkdirSync(userData, {recursive: true});
  fs.mkdirSync(extensions, {recursive: true});
  fs.mkdirSync(workspace, {recursive: true});
  fs.mkdirSync(exportsDir, {recursive: true});

  const good = `def int counter = 0;\nstate Root {\n    state Active {\n        during { counter = counter + 1; }\n    }\n    [*] -> Active;\n    Active -> [*] : if [counter >= 2];\n}\n`;
  fs.writeFileSync(path.join(workspace, 'acceptance.fcstm'), good);
  fs.writeFileSync(path.join(workspace, 'broken.fcstm'), good.replace('counter = counter + 1;', 'counter = ;'));
  writeDriver(driver, resultPath);
  run(process.execPath, ['--check', path.join(driver, 'extension.js')]);

  run(codeBin, [
    '--user-data-dir', userData,
    '--extensions-dir', extensions,
    '--install-extension', vsix,
    '--force',
  ]);
  const list = run(codeBin, ['--user-data-dir', userData, '--extensions-dir', extensions, '--list-extensions', '--show-versions']).stdout;
  fs.writeFileSync(path.join(out, 'extensions.txt'), list);
  if (!/^hansbug\.fcstm-language-support@0\.1\.0$/m.test(list)) {
    fail(`Installed extension list does not contain hansbug.fcstm-language-support@0.1.0:\n${list}`);
  }

  const installedExtensionPath = path.join(extensions, 'hansbug.fcstm-language-support-0.1.0');
  for (const rel of ['package.json', 'dist/extension.js', 'dist/server.js', 'dist/preview-webview.js', 'dist/preview-webview.css', 'syntaxes/fcstm.tmLanguage.json', 'snippets/fcstm.code-snippets']) {
    const file = path.join(installedExtensionPath, rel);
    if (!fs.existsSync(file)) fail(`Installed extension missing runtime file before smoke: ${file}`);
  }

  const env = {
    ...process.env,
    SMOKE_WORKSPACE: workspace,
    SMOKE_EXPORT_OUT: exportsDir,
    SMOKE_INSTALLED_EXTENSION_PATH: installedExtensionPath,
  };
  const codeArgs = [
    '-a', codeBin,
    '--user-data-dir', userData,
    '--extensions-dir', extensions,
    '--extensionDevelopmentPath', driver,
    '--disable-workspace-trust',
    '--skip-welcome',
    '--skip-release-notes',
    '--new-window',
    '--wait',
    workspace,
  ];
  run(xvfb, codeArgs, {env, timeout: 120000, cwd: out});
  if (!fs.existsSync(resultPath)) fail('VS Code smoke driver did not write result.json');
  const result = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
  if (!result.ok) fail(`VS Code smoke failed:\n${result.error}`);
  console.log(`VS Code smoke OK: ${out}`);
  console.log(JSON.stringify(result.summary, null, 2));
}

try {
  main();
} catch (error) {
  console.error(`VS Code smoke failed: ${error.message}`);
  process.exit(1);
}
