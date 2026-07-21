/*
 * Offline browser smoke/interaction gate for the standalone diagram viewer.
 * Uses Chrome DevTools Protocol directly so the repository does not need a
 * second browser-automation dependency. The command is a maintenance tool,
 * not part of the Python runtime.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const {spawn} = require('child_process');
const {createRequire} = require('module');
const requireFromVscode = createRequire(path.resolve(__dirname, '../../editors/vscode/package.json'));
const {WebSocket} = requireFromVscode('ws');

const htmlPath = process.argv[2];
const screenshotPath = process.argv[3];
const screenshotBeforeCollapsePath = process.env.VIEWER_SCREENSHOT_BEFORE_COLLAPSE;
const pdfOutputPath = process.env.VIEWER_PDF_OUTPUT;
const viewport = (process.env.VIEWER_VIEWPORT || '800x600').split('x').map(Number);
const viewportWidth = Number.isFinite(viewport[0]) && viewport[0] > 0 ? viewport[0] : 800;
const viewportHeight = Number.isFinite(viewport[1]) && viewport[1] > 0 ? viewport[1] : 600;
const startupWait = Number(process.env.VIEWER_STARTUP_WAIT || 2000);
if (!htmlPath) {
  console.error('usage: node check_viewer_browser.js VIEWER.html [SCREENSHOT.png]');
  process.exit(2);
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
async function waitForJson(url, attempts = 50) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
    } catch (_) { /* Chrome has not opened its debugging port yet. */ }
    await sleep(100);
  }
  throw new Error('Chrome DevTools endpoint did not start');
}

class Cdp {
  constructor(url) { this.socket = new WebSocket(url); this.next = 0; this.pending = new Map(); this.events = []; }
  async connect() {
    await new Promise((resolve, reject) => { this.socket.once('open', resolve); this.socket.once('error', reject); });
    this.socket.on('message', data => {
      const message = JSON.parse(String(data));
      if (message.id && this.pending.has(message.id)) {
        const {resolve, reject} = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message)); else resolve(message.result);
      } else if (message.method) this.events.push(message);
    });
  }
  call(method, params = {}) {
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.socket.send(JSON.stringify({id, method, params}));
    });
  }
  close() { this.socket.close(); }
}

async function evaluate(cdp, expression) {
  const result = await cdp.call('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'browser evaluation failed');
  return result.result && result.result.value;
}

(async () => {
  const userData = fs.mkdtempSync(path.join(os.tmpdir(), 'pyfcstm-viewer-'));
  const port = 9222 + Math.floor(Math.random() * 200);
  const chrome = spawn(process.env.CHROME_BIN || 'google-chrome', [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--no-first-run',
    '--no-default-browser-check', `--remote-debugging-port=${port}`,
    `--window-size=${viewportWidth},${viewportHeight}`,
    `--user-data-dir=${userData}`, 'about:blank',
  ], {stdio: 'ignore'});
  try {
    const targets = await waitForJson(`http://127.0.0.1:${port}/json`);
    const page = targets.find(item => item.type === 'page');
    if (!page) throw new Error('Chrome did not expose a page target');
    const cdp = new Cdp(page.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.call('Page.enable');
    await cdp.call('Runtime.enable');
    await cdp.call('Network.enable');
    await cdp.call('Security.enable');
    await cdp.call('Emulation.setDeviceMetricsOverride', {
      width: viewportWidth,
      height: viewportHeight,
      deviceScaleFactor: 1,
      mobile: viewportWidth < 700,
    });
    await cdp.call('Page.navigate', {url: `file://${path.resolve(htmlPath)}`});
    await sleep(startupWait);

    const initial = await evaluate(cdp, `({
      source: Boolean(document.querySelector('.fcstm-source-panel')),
      stage: Boolean(document.querySelector('.fcstm-stage svg')),
      error: (document.querySelector('.fcstm-stage__empty-title') || {}).textContent || '',
    })`);
    const sourceLayout = await evaluate(cdp, `(async () => {
      const rows = [...document.querySelectorAll('.fcstm-source-line')];
      const boxes = rows.map(row => row.getBoundingClientRect());
      const gaps = boxes.slice(1).map((box, index) => box.top - (boxes[index].bottom));
      const lineNumbers = rows.map(row => ({
        value: getComputedStyle(row, '::before').content,
        align: getComputedStyle(row, '::before').textAlign,
      }));
      const select = document.querySelector('.n-base-selection');
      select?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      await new Promise(resolve => setTimeout(resolve, 120));
      const menu = document.querySelector('.n-base-select-menu');
      const alpha = value => {
        const match = value.match(/^rgba\\([^)]*,\\s*([0-9.]+)\\)$/);
        return match ? Number(match[1]) : 1;
      };
      const menuStyle = menu ? getComputedStyle(menu) : null;
      const option = menu?.querySelector('.n-base-select-option');
      const optionStyle = option ? getComputedStyle(option) : null;
      const nativeSelect = document.querySelector('.fcstm-source-panel__header select');
      const nativeSelectStyle = nativeSelect ? getComputedStyle(nativeSelect) : null;
      document.body.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      return {
        lineCount: rows.length,
        textHasLineBreaks: rows.length < 2 || (document.querySelector('.fcstm-source-panel__code')?.textContent || '').includes('\\n'),
        lineNumbers,
        lineHeights: boxes.map(box => box.height),
        maxGap: Math.max(0, ...gaps),
        menuVisible: Boolean(menu),
        menuBackground: menuStyle?.backgroundColor || '',
        menuAlpha: menuStyle ? alpha(menuStyle.backgroundColor) : 0,
        optionBackground: optionStyle?.backgroundColor || '',
        optionAlpha: optionStyle ? alpha(optionStyle.backgroundColor) : 0,
        nativeSelectBackground: nativeSelectStyle?.backgroundColor || '',
        nativeSelectAlpha: nativeSelectStyle ? alpha(nativeSelectStyle.backgroundColor) : 1,
      };
    })()`);
    const states = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const buttons = [...document.querySelectorAll('.fcstm-standalone-mode button')];
      const click = label => buttons.find(button => button.textContent.includes(label))?.click();
      click('图形');
      setTimeout(() => resolve({diagramOnlySource: Boolean(document.querySelector('.fcstm-source-panel')), diagramOnlyStage: Boolean(document.querySelector('.fcstm-stage'))}), 120);
    }, 80))`);
    const compare = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const buttons = [...document.querySelectorAll('.fcstm-standalone-mode button')];
      buttons.find(button => button.textContent.includes('对比'))?.click();
      setTimeout(() => resolve({source: Boolean(document.querySelector('.fcstm-source-panel')), stage: Boolean(document.querySelector('.fcstm-stage'))}), 120);
    }, 80))`);
    const fcstmOnly = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const buttons = [...document.querySelectorAll('.fcstm-standalone-mode button')];
      buttons.find(button => button.textContent.includes('FCSTM'))?.click();
      setTimeout(() => resolve({source: Boolean(document.querySelector('.fcstm-source-panel')), stage: Boolean(document.querySelector('.fcstm-stage svg'))}), 120);
    }, 80))`);
    const backToCompare = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const buttons = [...document.querySelectorAll('.fcstm-standalone-mode button')];
      buttons.find(button => button.textContent.includes('对比'))?.click();
      setTimeout(() => resolve({source: Boolean(document.querySelector('.fcstm-source-panel')), stage: Boolean(document.querySelector('.fcstm-stage svg'))}), 120);
    }, 80))`);
    const importedSource = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const select = document.querySelector('.fcstm-source-panel__header select');
      const options = select ? [...select.options].map(option => option.value) : [];
      if (options.length < 2) {
        resolve({documents: options, selectedDocument: '', childText: false, selected: 0});
        return;
      }
      const beforeText = document.querySelector('.fcstm-source-panel__code')?.textContent || '';
      select.value = options.find(value => value !== (window.__FCSTM_INITIAL_STATE__?.sourceDocumentId || '')) || options[1];
      select.dispatchEvent(new Event('change', {bubbles: true}));
      setTimeout(() => {
        const selectedText = document.querySelector('.fcstm-source-panel__code')?.textContent || '';
        const childText = selectedText.trim().length > 0 && selectedText !== beforeText;
        const line = document.querySelector('.fcstm-source-line[data-line="0"]');
        line?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
        setTimeout(() => resolve({documents: options, selectedDocument: select.value, childText,
          selected: document.querySelectorAll('.fcstm-selected').length}), 220);
      }, 120);
    }, 80))`);
    const selection = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const target = document.querySelector('[data-fcstm-kind="state"]');
      target?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({selected: document.querySelectorAll('.fcstm-selected').length, target: target?.getAttribute('data-fcstm-id') || '', kind: target?.getAttribute('data-fcstm-kind') || ''}), 220);
    }, 220))`);
    const revealSource = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const button = [...document.querySelectorAll('.fcstm-details button')].find(item => item.textContent.includes('Reveal source'));
      button?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length}), 220);
    }, 180))`);
    const hover = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const target = document.querySelector('[data-fcstm-kind="state"]');
      target?.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, relatedTarget: null}));
      setTimeout(() => resolve({activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length}), 220);
    }, 220))`);
    const sourceHover = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const lineNumber = Object.keys(window.__FCSTM_INITIAL_STATE__?.sourceLineMap || {})[0];
      const line = lineNumber === undefined ? null : document.querySelector('.fcstm-source-line[data-line="' + lineNumber + '"]');
      line?.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, relatedTarget: null}));
      setTimeout(() => resolve({diagramHover: document.querySelectorAll('.fcstm-source-hover').length}), 220);
    }, 220))`);
    const sourceSelection = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const lineNumber = Object.keys(window.__FCSTM_INITIAL_STATE__?.sourceLineMap || {})[0];
      const line = lineNumber === undefined ? null : document.querySelector('.fcstm-source-line[data-line="' + lineNumber + '"]');
      line?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({selected: document.querySelectorAll('.fcstm-selected').length}), 220);
    }, 220))`);
    const sourceCycle = await evaluate(cdp, `(async () => {
      const entries = Object.entries(window.__FCSTM_INITIAL_STATE__?.sourceLineMap || {})
        .filter(([, value]) => Array.isArray(value) && value.length > 1);
      if (!entries.length) {
        return {candidateCount: 0, selectedIds: [], uniqueSelectedIds: 0};
      }
      const [key, value] = entries[0];
      const documentId = key.includes(':') ? key.slice(0, key.lastIndexOf(':')) : '';
      const lineNumber = key.includes(':') ? key.slice(key.lastIndexOf(':') + 1) : key;
      if (documentId) {
        const select = document.querySelector('.fcstm-source-panel__header select');
        if (select && select.value !== documentId) {
          select.value = documentId;
          select.dispatchEvent(new Event('change', {bubbles: true}));
          await new Promise(done => setTimeout(done, 80));
        }
      }
      const line = document.querySelector('.fcstm-source-line[data-line="' + lineNumber + '"]');
      const selectedIds = [];
      const waitForNextSelection = async previous => {
        const deadline = Date.now() + 1500;
        while (Date.now() < deadline) {
          const selected = document.querySelector('[data-fcstm-id].fcstm-selected');
          const id = selected?.getAttribute('data-fcstm-id') || '';
          if (id && id !== previous) return id;
          await new Promise(done => setTimeout(done, 20));
        }
        return '';
      };
      for (let index = 0; index < value.length; index += 1) {
        line?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
        selectedIds.push(await waitForNextSelection(selectedIds[selectedIds.length - 1] || ''));
      }
      return {candidateCount: value.length, selectedIds, uniqueSelectedIds: new Set(selectedIds.filter(Boolean)).size};
    })()`);
    const pdf = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      window.dispatchEvent(new CustomEvent('fcstm-export'));
      setTimeout(() => {
        const payload = window.__FCSTM_LAST_EXPORT__;
        const raw = payload?.pdfBase64 ? atob(payload.pdfBase64) : '';
        const pngRaw = payload?.pngBase64 ? atob(payload.pngBase64) : '';
        const hex = value => [...value].map(char => char.charCodeAt(0).toString(16).padStart(2, '0')).join('');
        const readU32 = (value, offset) => value.length >= offset + 4
          ? (((value.charCodeAt(offset) & 255) << 24) | ((value.charCodeAt(offset + 1) & 255) << 16) |
             ((value.charCodeAt(offset + 2) & 255) << 8) | (value.charCodeAt(offset + 3) & 255)) >>> 0 : 0;
        const pngHeader = hex(pngRaw.slice(0, 8));
        const pngWidth = readU32(pngRaw, 16);
        const pngHeight = readU32(pngRaw, 20);
        const image = new Image();
        image.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = image.naturalWidth;
          canvas.height = image.naturalHeight;
          const context = canvas.getContext('2d', {willReadFrequently: true});
          let nonBlankPixels = 0;
          if (context) {
            context.drawImage(image, 0, 0);
            const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
            for (let index = 0; index < pixels.length; index += 4) {
              if (pixels[index + 3] > 0 && (pixels[index] < 245 || pixels[index + 1] < 245 || pixels[index + 2] < 245)) {
                nonBlankPixels += 1;
                if (nonBlankPixels >= 10) break;
              }
            }
          }
          resolve({menu: Boolean(document.querySelector('#fcstm-standalone-export-menu')), base64: payload?.pdfBase64 || '', bytes: raw.length,
            header: raw.slice(0, 5), images: (raw.match(/\\/Subtype\\s*\\/Image\\b|\\/ImageMask\\b/g) || []).length,
            pages: (raw.match(/\\/Type \\/Page\\b/g) || []).length,
            pngBytes: pngRaw.length, pngHeader, pngWidth, pngHeight, pngDecodedWidth: image.naturalWidth,
            pngDecodedHeight: image.naturalHeight, pngNonBlankPixels: nonBlankPixels});
        };
        image.onerror = () => resolve({menu: Boolean(document.querySelector('#fcstm-standalone-export-menu')), base64: payload?.pdfBase64 || '', bytes: raw.length,
          header: raw.slice(0, 5), images: (raw.match(/\\/Subtype\\s*\\/Image\\b|\\/ImageMask\\b/g) || []).length,
          pages: (raw.match(/\\/Type \\/Page\\b/g) || []).length, pngBytes: pngRaw.length, pngHeader, pngWidth, pngHeight,
          pngDecodedWidth: 0, pngDecodedHeight: 0, pngNonBlankPixels: 0});
        image.src = pngRaw ? 'data:image/png;base64,' + payload.pngBase64 : '';
      }, 900);
    }, 120))`);
    if (pdfOutputPath && pdf.base64) fs.writeFileSync(pdfOutputPath, Buffer.from(pdf.base64, 'base64'));
    delete pdf.base64;
    const zoom = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const before = document.querySelector('.fcstm-stage__inner')?.style.transform || '';
      document.querySelector('.fcstm-stage__zoom button')?.click();
      setTimeout(() => resolve({before, after: document.querySelector('.fcstm-stage__inner')?.style.transform || ''}), 180);
    }, 120))`);
    if (screenshotBeforeCollapsePath) {
      const shot = await cdp.call('Page.captureScreenshot', {format: 'png'});
      fs.writeFileSync(screenshotBeforeCollapsePath, Buffer.from(shot.data, 'base64'));
    }
    const collapse = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const before = document.querySelectorAll('[data-fcstm-kind="state"]').length;
      const target = document.querySelector('[data-fcstm-kind="chevron"]');
      target?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({before, after: document.querySelectorAll('[data-fcstm-kind="state"]').length}), 260);
    }, 220))`);
    const layout = await evaluate(cdp, `(() => {
      const main = document.querySelector('.fcstm-main-view');
      const source = document.querySelector('.fcstm-source-panel');
      const stage = document.querySelector('.fcstm-stage');
      const shell = document.querySelector('.fcstm-preview-shell');
      const drawer = document.querySelector('.fcstm-bottom-drawer');
      const rect = el => el ? ({x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y, width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height}) : null;
      const style = el => el ? ({display: getComputedStyle(el).display, flex: getComputedStyle(el).flex, minHeight: getComputedStyle(el).minHeight, height: getComputedStyle(el).height, overflow: getComputedStyle(el).overflow}) : null;
      return {viewport: {width: innerWidth, height: innerHeight}, shell: rect(shell), drawer: rect(drawer), main: rect(main), source: rect(source), stage: rect(stage), stageCount: document.querySelectorAll('.fcstm-stage').length, sourceCount: document.querySelectorAll('.fcstm-source-panel').length, stageRects: [...document.querySelectorAll('.fcstm-stage')].map(rect), sourceRects: [...document.querySelectorAll('.fcstm-source-panel')].map(rect), svgRects: [...document.querySelectorAll('svg')].map(svg => ({className: svg.parentElement?.className || '', rect: rect(svg)})), bottomIconStyles: [...document.querySelectorAll('.fcstm-bottom .n-base-icon')].map(icon => ({rect: rect(icon), width: getComputedStyle(icon).width, height: getComputedStyle(icon).height, display: getComputedStyle(icon).display})), mainStyle: style(main), shellStyle: style(shell), drawerStyle: style(drawer), mainScrollHeight: main?.scrollHeight || 0, mainClientHeight: main?.clientHeight || 0, mainScrollWidth: main?.scrollWidth || 0, mainClientWidth: main?.clientWidth || 0};
    })()`);
    const network = cdp.events.filter(event => event.method === 'Network.requestWillBeSent').map(event => event.params.request.url).filter(url => !url.startsWith('file://') && !url.startsWith('data:') && !url.startsWith('blob:'));
    const cspViolations = cdp.events.filter(event => event.method === 'Security.securityPolicyViolationReported');
    const consoleErrors = cdp.events.filter(event => event.method === 'Runtime.exceptionThrown' || (event.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(event.params.type)));
    if (screenshotPath) {
      const shot = await cdp.call('Page.captureScreenshot', {format: 'png'});
      fs.writeFileSync(screenshotPath, Buffer.from(shot.data, 'base64'));
    }
    cdp.close();
    const consoleDetails = consoleErrors.map(event => event.method === 'Runtime.exceptionThrown'
      ? event.params.exceptionDetails?.text || event.params.exceptionDetails?.exception?.description || 'exception'
      : event.params.args?.map(arg => arg.value || arg.description || '').join(' '));
    const verticalOverflow = layout.main && layout.mainScrollHeight > layout.mainClientHeight + 1;
    const horizontalOverflow = layout.mainScrollWidth > layout.mainClientWidth + 1;
    const minimumPanelHeight = viewportHeight <= 700 ? 200 : 160;
    const comparisonSourceHeight = layout.source?.height || 0;
    const comparisonStageHeight = layout.stage?.height || 0;
    const comparisonTooShort = Boolean(compare.source && compare.stage &&
      (comparisonSourceHeight < minimumPanelHeight || comparisonStageHeight < minimumPanelHeight));
    const oversizedUiIcons = (layout.svgRects || []).filter(item => /n-(?:base-icon|icon|checkbox-icon)/.test(item.className))
      .some(item => item.rect.width > 64 || item.rect.height > 64);
    const report = {initial, sourceLayout, diagramOnly: states, fcstmOnly, compare, backToCompare, importedSource, selection, revealSource, hover, sourceHover, sourceSelection, sourceCycle, zoom, pdf, collapse, layout, minimumPanelHeight, comparisonTooShort, oversizedUiIcons, externalRequests: network, cspViolations, consoleErrors: consoleErrors.length, consoleDetails};
    console.log(JSON.stringify(report, null, 2));
    if (!initial.stage || initial.error || states.diagramOnlySource || !compare.source || !compare.stage ||
        fcstmOnly.source !== true || fcstmOnly.stage !== false || backToCompare.source !== true || backToCompare.stage !== true ||
        sourceLayout.lineCount < 1 || !sourceLayout.textHasLineBreaks || sourceLayout.lineNumbers.some(item => item.align !== 'right' || !/^"\\d+"$/.test(item.value)) || sourceLayout.maxGap > 1 ||
        !sourceLayout.menuVisible || sourceLayout.menuAlpha < 0.99 || sourceLayout.optionAlpha < 0.99 || sourceLayout.nativeSelectAlpha < 0.99 ||
        selection.selected < 1 || revealSource.activeSourceLines < 1 || hover.activeSourceLines < 1 || sourceHover.diagramHover < 1 || sourceSelection.selected < 1 ||
        zoom.before === zoom.after || pdf.menu !== true || pdf.header !== '%PDF-' || pdf.bytes < 100 || pdf.images !== 0 || pdf.pages !== 1 ||
        pdf.pngHeader !== '89504e470d0a1a0a' || pdf.pngBytes < 100 || pdf.pngWidth < 1 || pdf.pngHeight < 1 ||
        pdf.pngDecodedWidth !== pdf.pngWidth || pdf.pngDecodedHeight !== pdf.pngHeight || pdf.pngNonBlankPixels < 10 ||
        (sourceCycle.candidateCount > 1 && sourceCycle.uniqueSelectedIds < sourceCycle.candidateCount) ||
        (collapse.before > 1 && collapse.after >= collapse.before) || verticalOverflow || horizontalOverflow || comparisonTooShort || oversizedUiIcons || network.length || cspViolations.length || consoleErrors.length ||
        (importedSource.documents.length > 1 && (!importedSource.childText || importedSource.selected < 1))) process.exitCode = 1;
  } finally {
    chrome.kill('SIGTERM');
    fs.rmSync(userData, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
