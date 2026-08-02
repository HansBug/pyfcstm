/*
 * Offline browser smoke/interaction gate for the standalone diagram viewer.
 * Uses Chrome DevTools Protocol directly so the repository does not need a
 * second browser-automation dependency. The command is a maintenance tool,
 * not part of the Python runtime.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const {spawn, spawnSync} = require('child_process');
const {createRequire} = require('module');
const requireFromVscode = createRequire(path.resolve(__dirname, '../../editors/vscode/package.json'));
const {WebSocket} = requireFromVscode('ws');

const htmlPath = process.argv[2];
const screenshotPath = process.argv[3];
const screenshotBeforeCollapsePath = process.env.VIEWER_SCREENSHOT_BEFORE_COLLAPSE;
const pdfOutputPath = process.env.VIEWER_PDF_OUTPUT;
const requestedFormats = new Set((process.env.VIEWER_FORMATS || 'svg,png,pdf').split(',').filter(Boolean));
// Zero external network traffic is an absolute contract of the self-contained
// viewer, so it is asserted on every run instead of behind an opt-in flag.
const requirePdfZeroImages = process.env.VIEWER_REQUIRE_PDF_ZERO_IMAGES === '1';
const requirePdfPageSize = process.env.VIEWER_REQUIRE_PDF_PAGE_SIZE === '1';
const requirePdfRerender = process.env.VIEWER_REQUIRE_PDF_RERENDER === '1';
const viewport = (process.env.VIEWER_VIEWPORT || '800x600').split('x').map(Number);
const viewportWidth = Number.isFinite(viewport[0]) && viewport[0] > 0 ? viewport[0] : 800;
const viewportHeight = Number.isFinite(viewport[1]) && viewport[1] > 0 ? viewport[1] : 600;
// Embedded WASM compilation can be slower on the first narrow viewport; keep
// the maintenance gate above that one-time initialization cost by default.
const startupWait = Number(process.env.VIEWER_STARTUP_WAIT || 4000);
// How many source documents the fixture was built with. The page's own
// document list cannot answer this: deleting `sourceDocuments` emptied both the
// list and the expectation, so the imported-source assertion retired itself on
// the one fixture that exists to exercise it.
const expectDocumentsRaw = process.env.VIEWER_EXPECT_DOCUMENTS;
const expectDocuments = expectDocumentsRaw === undefined ? 0 : Number(expectDocumentsRaw);
if (!Number.isInteger(expectDocuments) || expectDocuments < 0) {
  // NaN loses every comparison, so a typo in the value would have retired both
  // the count and the picker assertions without a word.
  console.error(`VIEWER_EXPECT_DOCUMENTS must be a non-negative integer, got ${JSON.stringify(expectDocumentsRaw)}`);
  process.exit(2);
}
// How many event / action rows the fixture's detail level should have put
// inside state bodies. The driver knows, because it chose the level and wrote
// the machine; the page saying "I drew what I meant to" would prove nothing.
// Absent means unchecked, so every existing case is unaffected.
const expectedStateRows = {
  'state-event': parseExpectedRows('VIEWER_EXPECT_STATE_EVENT_ROWS'),
  'state-action': parseExpectedRows('VIEWER_EXPECT_STATE_ACTION_ROWS'),
};

// Whether a transition effect should be drawn in a note pad of its own. Not a
// universal truth about a diagram: one detail preset writes effects inline
// instead, and requiring the pad everywhere made that preset unrenderable
// rather than different. Default on, so every existing case is unaffected.
const expectTransitionNotes = process.env.VIEWER_EXPECT_TRANSITION_NOTES !== '0';

function parseExpectedRows(name) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return null;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 0) {
    // NaN loses every comparison, so a typo would retire the assertion in
    // silence -- the failure mode this whole gate exists to avoid.
    console.error(`${name} must be a non-negative integer, got ${JSON.stringify(raw)}`);
    process.exit(2);
  }
  return value;
}

if (htmlPath === '--check') {
  selfCheckStreamTally();
  process.exit(0);
}
if (!htmlPath) {
  console.error('usage: node check_viewer_browser.js VIEWER.html [SCREENSHOT.png]');
  console.error('       node check_viewer_browser.js --check');
  process.exit(2);
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

// Walk the document once and hand back every stream with the dictionary that
// introduced it and the bytes it holds.
//
// Seven fail-opens in this gate came from one mistake: matching PDF syntax
// against bytes that were not syntax. Each was fixed where it broke -- a string
// holding `<<` fooled a bracket balancer, `(obj)` and then `(1 0 obj)` fooled an
// object-header anchor, `(/Length 5)` fooled the length -- and each fix taught
// one pattern to step over one decoy. But the *choice of where to look* was
// still made on raw text, by searching backwards from the keyword for the last
// object header, so a dictionary carrying `% 1 0 obj << /X 1 >>` in a comment
// still moved it, and the sanitiser, which ran on the span only after that
// choice was made, never saw the bytes that made it.
//
// There is no eighth guard here. A reader going forwards from byte zero knows
// whether it is inside a string or a comment because it read its way in, so
// decoy syntax is never syntax to begin with. Dictionary text is accumulated as
// it is lexed, with string and comment bytes arriving as spaces, which leaves
// the patterns below nothing to be fooled by.
//
// Payloads are stepped over rather than read: they are binary, and a stray `(`
// in one opens a literal that never closes. On a real 25-stream document an
// earlier balancer did exactly that and made every dictionary after the first
// unreadable, which -- because an unreadable dictionary is treated as filtered
// -- showed up only on the streams that had no filter.
function scanPdfStreams(raw) {
  const text = raw.toString('latin1');
  const streams = [];
  let dictionary = null;
  let building = null;
  let attached = false;
  let depth = 0;
  let i = 0;
  // Dictionary text is kept for the top level only, with nested dictionaries
  // arriving as blanks. `/DecodeParms << /Length 5 >>` describes the filter's
  // parameters, not the stream, and reading its `/Length` as the stream's own
  // recorded a mismatch on a document that stated its size perfectly well.
  const emit = (chunk) => {
    if (building === null) return;
    building += depth === 1 ? chunk : ' '.repeat(chunk.length);
  };
  while (i < text.length) {
    const ch = text[i];
    // A comment is whitespace to a reader. It reaches no pattern, and it does
    // not separate a dictionary from the stream it introduces.
    if (ch === '%') {
      const start = i;
      while (i < text.length && text[i] !== '\n' && text[i] !== '\r') i += 1;
      emit(' '.repeat(i - start));
      continue;
    }
    // A literal string's contents are data. Parentheses nest, and a backslash
    // escapes whatever byte follows it.
    if (ch === '(') {
      const start = i;
      let nesting = 0;
      while (i < text.length) {
        const c = text[i];
        if (c === '\\') { i += 2; continue; }
        if (c === '(') nesting += 1;
        else if (c === ')' && --nesting === 0) { i += 1; break; }
        i += 1;
      }
      emit(' '.repeat(Math.min(i, text.length) - start));
      attached = false;
      if (i >= text.length && nesting > 0) {
        // The literal ran to the end of the file, so everything after it went
        // unread -- including, if this is the syntax between two objects, a
        // whole stream and the halo it carried. The `total > 0` floor does not
        // catch that: an earlier stream has already been counted, and the
        // result looks exactly like a document with nothing left to read.
        // Recording the region keeps `decoded === total` honest about it.
        streams.push(unreadableRegion(start, text.length, 'UNCLOSED_STRING'));
        break;
      }
      continue;
    }
    // A hex string cannot spell `/Length` or `obj` in ASCII, but it holds `>`
    // and would otherwise close a dictionary early.
    if (ch === '<' && text[i + 1] !== '<') {
      const start = i;
      const stop = text.indexOf('>', i);
      i = stop < 0 ? text.length : stop + 1;
      emit(' '.repeat(i - start));
      attached = false;
      if (stop < 0) {
        streams.push(unreadableRegion(start, text.length, 'UNCLOSED_HEX_STRING'));
        break;
      }
      continue;
    }
    if (ch === '<' && text[i + 1] === '<') {
      if (depth === 0) building = '';
      depth += 1;
      emit('<<');
      i += 2;
      continue;
    }
    if (ch === '>' && text[i + 1] === '>' && depth > 0) {
      emit('>>');
      depth -= 1;
      i += 2;
      if (depth === 0) { dictionary = building; building = null; attached = true; }
      continue;
    }
    // The keyword only where it is one. `endstream` ends in the same six
    // letters, and a name such as `/streamish` starts with them.
    if (ch === 's' && text.startsWith('stream', i)
        && !isRegularChar(text[i - 1]) && !isRegularChar(text[i + 6])) {
      let dataStart = i + 6;
      // `stream` may be followed by LF or CRLF; keying on LF alone found nothing
      // at all in a CRLF document and reported a total of zero.
      if (text[dataStart] === '\r') dataStart += 1;
      if (text[dataStart] !== '\n') {
        // The spec requires LF or CRLF here and forbids a lone CR, so this is
        // not a stream. Skipping it in silence is what the rest of this scan
        // stopped doing: with one sound stream elsewhere the tally balances
        // over a file that had something here nobody read.
        streams.push(unreadableRegion(i, dataStart, 'STREAM_KEYWORD_WITHOUT_EOL'));
        i += 6;
        attached = false;
        continue;
      }
      dataStart += 1;
      // Only the dictionary that directly precedes the keyword introduces it.
      // Taking the last one seen regardless would read a `/Filter` off some
      // earlier object that this stream never declared.
      const own = attached ? dictionary : null;
      // A size the dictionary states outright, and failing that the object an
      // indirect reference points at. Nothing is guessed: a stream with neither
      // is recorded unread, because where its data stops could only be
      // estimated and both estimates were wrong the same way.
      //
      // The two are not equally trustworthy, which is why `indirectLength` is
      // strict where `declaredLength` need not be. A direct size comes from the
      // stream's own dictionary, so following it agrees with every reader --
      // if it is wrong, the document is wrong. An indirect one is a number this
      // side went looking for in the whole file, and a search that finds the
      // wrong object parts company with the reader over a file both can read.
      const size = declaredLength(own) ?? indirectLength(text, own);
      const end = resolveStreamEnd(text, dataStart, size);
      streams.push({keyword: i, dataStart, dictionary: own, ...end});
      i = end.resume;
      attached = false;
      continue;
    }
    // Anything else is an ordinary byte: dictionary syntax when one is open, and
    // otherwise the object headers and keywords between them. A non-blank byte
    // also means another token has come between a dictionary and any stream that
    // follows it.
    emit(ch);
    if (ch !== ' ' && ch !== '\n' && ch !== '\r' && ch !== '\t' && ch !== '\f' && ch !== '\0') {
      attached = false;
    }
    i += 1;
  }
  return streams;
}

// PDF's own division: whitespace and the delimiters `()<>[]{}/%` end a token,
// and every other byte continues one. Testing for letters and digits alone
// stopped `/end_stream` and `/x-stream` short of the keyword, and each would
// have started a stream in the middle of a dictionary.
function isRegularChar(ch) {
  return ch !== undefined && !/[\s\0()<>[\]{}/%]/.test(ch);
}

// A span of the file that could not be read, reported in the same currency as
// a stream so that `decoded === total` accounts for it. `dictionary` is never
// looked at -- a non-null `code` returns before it is reached -- and is here
// only so every entry has one shape.
function unreadableRegion(start, end, code) {
  return {keyword: start, dataStart: start, dataEnd: end, dictionary: null, code};
}

/**
 * The byte count a dictionary states directly, or null when it states none.
 *
 * `/Length 5 0 R` is an indirect reference whose value lives in another object;
 * reading `5` from it took five bytes of a forty-byte stream and the truncation
 * counted as a successful decode. The reference is matched as an optional
 * trailing group rather than excluded with a lookahead, because `(?!\s+\d+\s+R)`
 * let the engine backtrack `\d+` from `99` to `9` and then satisfy itself that
 * what remained was not a reference -- so `/Length 99 0 R` was read as nine.
 */
function declaredLength(dictionary) {
  const match = /\/Length\s+(\d+)(\s+\d+\s+R\b)?/.exec(dictionary || '');
  if (!match || match[2]) return null;
  return Number(match[1]);
}

/**
 * The size an indirect `/Length N M R` points at, or null when none is found.
 *
 * The object holding it may sit anywhere in the file, including after the
 * stream that names it, so it is looked up by shape rather than by position --
 * which means the search runs over payload bytes too, where the same shape can
 * occur without being an object.
 *
 * The landing check downstream does not make a wrong answer safe: it rejects a
 * size that misses `endstream`, and the documents that need this lookup are
 * exactly the ones carrying an `endstream` for it to hit. So the number is
 * taken only when the file holds one object with that number and nothing else
 * shaped like its header. Two of them is a file no reader could agree on, and
 * the second may be bytes inside a stream rather than an object at all.
 */
function indirectLength(text, dictionary) {
  const reference = /\/Length\s+(\d+)\s+(\d+)\s+R\b/.exec(dictionary || '');
  if (!reference) return null;
  const prefix = '(^|[^0-9A-Za-z])' + reference[1] + '\\s+' + reference[2] + '\\s+obj';
  const headers = text.match(new RegExp(prefix + '\\b', 'g'));
  if (!headers || headers.length !== 1) return null;
  const found = new RegExp(prefix + '\\s+(\\d+)\\s*endobj').exec(text);
  return found ? Number(found[2]) : null;
}

/**
 * Where one stream's payload stops, and where scanning picks up after it.
 *
 * `endstream` is nine ordinary bytes and an uncompressed payload may hold them
 * -- a state named `endstream` is enough. Taking the first match cut such a
 * stream in half and threw the rest away, halo and all, while the tally stayed
 * balanced.
 */
function resolveStreamEnd(text, dataStart, stated) {
  const first = text.indexOf('endstream', dataStart);
  if (first < 0) {
    // A stream with no terminator is still a stream. Reporting nothing here let
    // a truncated document end with one that nobody had to account for.
    return {dataEnd: text.length, resume: text.length, code: 'UNTERMINATED'};
  }
  if (stated === null) {
    // Nothing here says where the data stops, and this side does not guess.
    // Two rounds of guessing were wrong in the same direction: taking the first
    // `endstream` cut a payload that contained those nine bytes in half, and
    // requiring the keyword to be followed by the end of an object only moved
    // the guess -- a payload carrying `endstream endobj` satisfies that too.
    // Reading part of a stream and reporting the whole is the failure this gate
    // exists to catch, so an unreadable size is recorded as unread.
    //
    // `/Length` is required in a stream dictionary, so this is a malformed
    // document either way, and the writer this gate reads always states one.
    return {dataEnd: first, resume: first + 'endstream'.length, code: 'LENGTH_UNREADABLE'};
  }
  const end = dataStart + stated;
  if (/^[\r\n\s]*endstream/.test(text.slice(end, end + 20))) {
    const next = text.indexOf('endstream', end);
    return {dataEnd: end, resume: next + 'endstream'.length, code: null};
  }
  // A stated length that does not land on the keyword is not one this side can
  // act on. Recording the stream as unread is the honest answer; using the
  // number anyway sliced 5 bytes out of 41 and called the fragment a decode.
  return {dataEnd: first, resume: first + 'endstream'.length, code: 'LENGTH_MISMATCH'};
}

// Decode a PDF's content streams so the halo scan has something to read.
//
// Every stream in the file has to be accounted for. Reading only the ones that
// happened to inflate leaves a non-empty result, so a "did anything decode"
// guard stays quiet while the stream that carried the halo was skipped -- and a
// zero halo count then means "not read" while looking exactly like "no halos".
// The caller compares `decoded` against `total` instead.
//
// Returns {text, total, decoded, skipped} rather than just the text, because
// the counts are what the assertion needs.
function inflatePdfStreams(base64) {
  const raw = Buffer.from(String(base64 || ''), 'base64');
  const streams = scanPdfStreams(raw);
  const chunks = [];
  const skipped = [];
  let decoded = 0;
  for (const stream of streams) {
    if (stream.code !== null) {
      skipped.push({
        offset: stream.keyword,
        bytes: Math.max(0, stream.dataEnd - stream.dataStart),
        code: stream.code,
      });
      continue;
    }
    // The stated length is exact, and it is the only way a stream gets this far,
    // so there is no trailing EOL to peel and nothing to guess at. Peeling one
    // here took a byte off a well-formed stream and zlib reported `Z_BUF_ERROR`
    // for a document that was perfectly sound.
    const payload = raw.subarray(stream.dataStart, stream.dataEnd);
    // A stream that declares no filter is stored as-is and reading it needs no
    // decoder. Handing it to zlib anyway made a legal uncompressed document look
    // unreadable here while the Python check counted the same bytes as decoded
    // -- two gates claiming a shared invariant and disagreeing on one file.
    //
    // When the dictionary cannot be read the stream is treated as filtered, so
    // an unfamiliar shape becomes a loud skip rather than a silent pass.
    if (stream.dictionary !== null && !stream.dictionary.includes('/Filter')) {
      chunks.push(Buffer.from(payload));
      // And read them again as deflate if they will have it. A name may be
      // written `/#46ilter`, which is the same name to a reader and invisible
      // to a substring match, so the stored reading alone would scan compressed
      // bytes for operators and find none. Reading both ways costs one attempt
      // and does not turn on which spelling was meant -- deciding by whether
      // the bytes happen to inflate would instead hand a stored payload that
      // begins like a zlib header to the wrong reader.
      try {
        chunks.push(zlib.inflateSync(payload));
      } catch (error) {
        // Not deflate, which is the ordinary case for a stored stream.
        if (!(error instanceof Error) || typeof error.code !== 'string' || !error.code.startsWith('Z_')) {
          throw error;
        }
      }
      decoded += 1;
      continue;
    }
    try {
      chunks.push(zlib.inflateSync(payload));
      decoded += 1;
    } catch (error) {
      // zlib rejects a payload that is not deflate data, which is what a stream
      // using another filter looks like from here. Every other class -- a bad
      // argument, an allocation failure -- is a defect in this checker rather
      // than a property of the document, and must not be recorded as a skip.
      if (!(error instanceof Error) || typeof error.code !== 'string' || !error.code.startsWith('Z_')) {
        throw error;
      }
      skipped.push({offset: stream.keyword, bytes: payload.length, code: error.code});
    }
  }
  return {
    // Separated, because two payloads laid end to end can spell an operator
    // across the join that neither of them contains -- one ending in
    // `1.0 1.0 1.0 rg\n3. w\n1. ` and the next starting `G` reads as a halo
    // and fails a document that has none.
    //
    // Empty ones dropped first: a separator is a byte like any other, and two
    // streams that decoded to nothing at all still produced a one-byte result,
    // which satisfied the caller's `text.length > 0` -- the only part of the
    // verdict that says anything was read. Adding the separator had turned that
    // question from "was there content" into "were there chunks", and one empty
    // stream was rejected where two were not.
    text: chunks.filter((chunk) => chunk.length > 0).map((chunk) => chunk.toString('latin1')).join('\0'),
    total: streams.length,
    decoded,
    skipped,
  };
}

// Prove the stream tally reports what it exists to catch.
//
// The halo count alone cannot: it is a zero-count, so a stream that was never
// read looks exactly like a stream with no halos. This ran green for weeks
// against a document whose second stream was silently skipped, which is why it
// is now a checked invariant with a case that fails without it.
function selfCheckStreamTally() {
  const HALO = /[0-9.]+ [0-9.]+ [0-9.]+ rg\n3\. w\n1\. G/g;
  const halo = Buffer.from('1.0 1.0 1.0 rg\n3. w\n1. G\n0 0 m 10 10 l f\n');
  const flate = (payload) => {
    const body = zlib.deflateSync(payload);
    return Buffer.concat([
      Buffer.from('1 0 obj\n<< /Filter /FlateDecode /Length ' + body.length + ' >>\nstream\n'),
      body, Buffer.from('\nendstream\nendobj\n'),
    ]);
  };
  const unreadable = Buffer.from(
    '2 0 obj\n<< /Filter /LZWDecode /Length 12 >>\nstream\n\x80not-deflate\nendstream\nendobj\n');
  const accepted = (buf) => {
    const r = inflatePdfStreams(buf.toString('base64'));
    const halos = (r.text.match(HALO) || []).length;
    return r.text.length > 0 && r.total > 0 && r.decoded === r.total && halos === 0;
  };
  const cases = [
    ['a single readable stream with no halo', Buffer.concat([Buffer.from('%PDF-1.3\n'), flate(Buffer.from('BT ET\n'))]), true],
    // CRLF: keying the marker on LF alone found nothing and reported total 0,
    // which the old "did anything decode" guard would have passed as a zero.
    ['a CRLF document', (() => {
      const body = zlib.deflateSync(Buffer.from('BT ET\n'));
      return Buffer.concat([
        Buffer.from('%PDF-1.3\r\n1 0 obj\r\n<< /Filter /FlateDecode /Length ' + body.length + ' >>\r\nstream\r\n'),
        body, Buffer.from('\r\nendstream\r\nendobj\r\n')]);
    })(), true],
    ['a stream carrying a halo', Buffer.concat([Buffer.from('%PDF-1.3\n'), flate(halo)]), false],
    // The bypass this invariant exists for: one readable stream keeps the result
    // non-empty while the stream that carried the halo was skipped.
    ['a document whose second stream could not be read', Buffer.concat([
      Buffer.from('%PDF-1.3\n'), flate(Buffer.from('BT ET\n')), unreadable]), false],
    ['a document with no readable stream at all', Buffer.concat([Buffer.from('%PDF-1.3\n'), unreadable]), false],
    // `endstream` ends in `stream`. A scan that skipped a non-marker occurrence
    // could land on that tail and count what follows as another stream, which
    // now decides the verdict rather than just a statistic.
    ['a document with `stream` inside a word', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Type /Downstream >>\n'),
      flate(Buffer.from('BT ET\n')),
      Buffer.from('% upstream\nendstream trailing\n')]), true],
    // A stream with no filter is stored as-is. Reading it through zlib made a
    // legal document look unreadable here while the Python check counted the
    // same bytes as decoded -- the two gates claim one invariant and have to
    // agree on what satisfies it.
    ['an uncompressed stream', Buffer.from(
      '%PDF-1.3\n1 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'), true],
    // And it still has to be scanned: skipping the decode must not skip the halo.
    ['an uncompressed stream carrying a halo', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Length 40 >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // Both orderings, because taking the *last* `<<` found the inner dictionary
    // when `/DecodeParms` came second: the filter went unnoticed, the compressed
    // bytes were scanned as operators, and a document carrying a halo passed.
    // Only one of these two catches that, so both are here.
    ['a filter declared before nested parameters', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Filter /FlateDecode /DecodeParms << /X 1 >> >>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    ['a filter declared after nested parameters', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /DecodeParms << /X 1 >> /Filter /FlateDecode >>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    // A literal string may hold either bracket. Balancing without stepping over
    // one read `(a << b)` as a nested dictionary, landed on the wrong span, and
    // the filter went unseen -- so a compressed stream carrying a halo was
    // scanned as raw operators and passed.
    ['a filter beside a string holding brackets', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Filter /FlateDecode /Note (a << b) >>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    // An earlier object's dictionary used to sit in the look-back window of
    // every stream but the first. Two attempts at bracket balancing were
    // defeated by it, and on a real document that made every dictionary
    // unreadable at once. Reading forwards, this is simply the second object.
    ['a stream preceded by another object', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'),
      Buffer.from('2 0 obj\n<< /Length 5 >>\nstream\nBT ET\nendstream\nendobj\n')]), true],
    ['a preceded stream carrying a halo', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n2 0 obj\n<< /Length 40 >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // The payload's last byte is as likely to be 0x0A as anything else. A peel
    // before handing the bytes to zlib takes that byte off and calls a sound
    // document corrupt; the stated length already said where the data ends.
    ['a payload ending in a newline byte', (() => {
      // Deflating 3852 x's happens to end in 0x0A. Peeling every trailing
      // newline took that byte off and zlib called a sound document corrupt;
      // `/Length` says how much data there is, so nothing has to be guessed.
      const body = zlib.deflateSync(Buffer.from('x'.repeat(3852)));
      if (body[body.length - 1] !== 10) {
        console.error('the payload chosen for the newline case no longer ends in 0x0A');
        process.exit(1);
      }
      return Buffer.concat([
        Buffer.from('%PDF-1.3\n1 0 obj\n<< /Filter /FlateDecode /Length ' + body.length + ' >>\nstream\n'),
        body, Buffer.from('\nendstream\nendobj\n')]);
    })(), true],
    // A stream that states no size is not read. Where its data stops can only
    // be guessed at, and two rounds of guessing were wrong the same way -- a
    // payload holding `endstream`, then one holding `endstream endobj`, each cut
    // the stream short and dropped the halo in the tail while the tally
    // balanced. `/Length` is required in a stream dictionary, so a document
    // without one is malformed; reporting it unread is the honest answer.
    ['a stream that states no length', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Filter /FlateDecode >>\nstream\n'),
      zlib.deflateSync(Buffer.from('BT ET\n')), Buffer.from('\nendstream\nendobj\n')]), false],
    // Two fail-open shapes an earlier review found: an `obj` inside a string
    // literal moved the backwards search into the dictionary and cut the
    // `/Filter` off in front of it, and `/Length 5 0 R` names another object
    // rather than stating a size, so reading `5` from it truncated a forty-byte
    // stream and called that a successful decode. Each let a document carrying
    // a halo through.
    ['a string literal holding the word obj', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Filter /FlateDecode /Note (obj) /DecodeParms << /X 1 >> >>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    ['a length given as an indirect reference', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Length 5 0 R >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // The same reference wearing a comment. Comments are whitespace to a reader,
    // so the lookahead alone did not see this one and read `5` as the size.
    ['an indirect reference behind a comment', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Length 5%c\n0 R >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // `(1 0 obj)` reads as an object header to anything matching the shape
    // loosely: the span then starts mid-dictionary and the `/Filter` in front of
    // the nested one is cut off. Requiring the span to *begin* with `<<` is what
    // the surrounding comment always claimed and the code did not check.
    ['a string literal shaped like a header', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Filter /FlateDecode /Note (1 0 obj) /DecodeParms << /X 1 >> >>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    // `/Length` inside a string value. The pattern read the decoy, took 5 bytes
    // of 41, and reported a clean fragment. This is the branch a real document
    // takes -- every viewer PDF states its length directly -- so a guard that
    // lives only on the other side never runs where it matters.
    ['a decoy length inside a string value', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Note (/Length 5) /Length ' + halo.length + ' >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // A stated length that lands nowhere near the keyword is not one to act on.
    ['a stated length that does not reach the end', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Length 5 >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // A stream with no terminator is still a stream; breaking before counting it
    // let a truncated document end with one nobody had to account for.
    ['an unterminated final stream', Buffer.concat([
      Buffer.from('%PDF-1.3\n1 0 obj\n<< /Length 5 >>\nstream\n'), halo]), false],
    // The case above also fails the `total > 0` test, so on its own it lets the
    // count be deleted in silence. Here a readable stream supplies the total and
    // only counting the truncated one keeps its halo in the reckoning.
    ['an unterminated stream after a readable one', Buffer.concat([
      Buffer.from('%PDF-1.3\n'), flate(Buffer.from('BT ET\n')),
      Buffer.from('2 0 obj\n<< /Length 5 >>\nstream\n'), halo]), false],
    ['an indirect length beside an embedded end keyword', (() => {
      const body = Buffer.concat([Buffer.from('BT (endstream) Tj ET\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n4 0 obj\n<< /Length 5 0 R >>\nstream\n'),
        body,
        Buffer.from('\nendstream\nendobj\n5 0 obj\n' + body.length + '\nendobj\n')]);
    })(), false],
    ['a payload containing the end keyword', (() => {
      const body = Buffer.concat([Buffer.from('BT (endstream) Tj ET\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.3\n1 0 obj\n<< /Length ' + body.length + ' >>\nstream\n'),
        body, Buffer.from('\nendstream\nendobj\n')]);
    })(), false],
    // Where the dictionary is found, not just what is read out of it. Both of
    // these carry a whole fake object header -- one in a comment, one in a
    // string -- and both moved a backwards search for the last `N M obj`
    // forwards into the dictionary, so the span began after the `/Filter` and a
    // compressed halo was scanned as raw operators. Blanking the decoy could not
    // help: the choice of where to blank was made from the raw bytes that held
    // it. A reader going forwards is never inside either one by accident.
    ['a comment holding a whole object header', Buffer.concat([
      Buffer.from('%PDF-1.4\n1 0 obj\n<< /Filter /FlateDecode\n% 1 0 obj << /X 1 >>\n>>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    ['a string holding a whole object header', Buffer.concat([
      Buffer.from('%PDF-1.4\n1 0 obj\n<< /Filter /FlateDecode /Note (1 0 obj << /X 1 >>) >>\nstream\n'),
      zlib.deflateSync(halo), Buffer.from('\nendstream\nendobj\n')]), false],
    // Neither case above needs comments to be stepped over -- read as syntax
    // they still leave the `/Filter` where the scan can see it. Comments are
    // stepped over for the opposite reason, and this is the case that says so:
    // a `>>` inside one closes the dictionary early, and the stream is then left
    // with no dictionary it can call its own. That direction is safe -- an
    // unreadable dictionary counts as filtered, so this legal document is
    // reported unreadable rather than passed -- which is why it takes a document
    // that *should* be accepted to notice at all.
    ['a comment holding a closing bracket', Buffer.from(
      '%PDF-1.4\n1 0 obj\n<< /Length 6\n% a note >> here\n>>\nstream\nBT ET\nendstream\nendobj\n'), true],
    // A hex string is stepped over for the same reason and shows it the same
    // way: `<A1B2>` sits flush against the brackets that close the dictionary,
    // and read as ordinary bytes its own `>` pairs with one of them.
    ['a hex string flush against the closing brackets', Buffer.from(
      '%PDF-1.4\n1 0 obj\n<< /Length 6 /ID <A1B2>>>\nstream\nBT ET\nendstream\nendobj\n'), true],
    // `Downstream` ends in the keyword and a newline may follow it, which is all
    // the marker itself requires. Without a boundary the scan starts a stream
    // inside the dictionary and swallows the object that really has one.
    ['a name ending in the keyword before a newline', Buffer.from(
      '%PDF-1.4\n1 0 obj\n<< /Type /Downstream\n>>\nendobj\n'
      + '2 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'), true],
    // Payloads are stepped over, not read. This one shows a text operator with
    // an unbalanced `(` -- ordinary content for a drawing -- opening a literal
    // that runs to the end of the file and takes the next object's `stream`
    // keyword with it. That stream is then never found, never counted and never
    // searched, and the halo it carries goes with it while the tally balances.
    ['an unbalanced bracket in a payload before another stream', Buffer.concat([
      Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 5 >>\nstream\nBT (x\nendstream\nendobj\n'),
      Buffer.from('2 0 obj\n<< /Length ' + halo.length + ' >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n% ) closes it\n')]), false],
    // The same shape one level out, where the scan is reading syntax rather
    // than stepping over data. Nothing is left to find the second stream with,
    // and the `total > 0` floor does not notice because the first stream has
    // already been counted -- the tally balances over a file that was read to
    // the halfway point.
    ['an unbalanced bracket between two objects', Buffer.concat([
      Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'),
      Buffer.from('2 0 obj (unclosed\n<< /Length ' + halo.length + ' >>\nstream\n'),
      halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // A hex string with no `>` does the same as an unterminated literal, and
    // needs its own case: the literal is closed by the trailer comment in the
    // case above, so nothing there records an unread region.
    ['an unclosed hex string between two objects', Buffer.concat([
      Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'),
      Buffer.from('2 0 obj <A1B2\nstream\n'), halo, Buffer.from('\nendstream\nendobj\n')]), false],
    // An indirect length whose payload carries its own `endstream endobj`.
    // Guessing the end stops at the decoy, the tail goes missing with the halo
    // in it, and nothing about the tally looks wrong. Following the reference
    // to the object that states the size is what gets past it.
    ['an indirect length beside a decoy end keyword', (() => {
      const body = Buffer.concat([Buffer.from('BT ET\nendstream\nendobj\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 9 0 R >>\nstream\n'), body,
        Buffer.from('\nendstream\nendobj\n9 0 obj\n' + body.length + '\nendobj\n')]);
    })(), false],
    // A lone CR after the keyword is forbidden, so this is not a stream -- but
    // passing over it without a word is how a file gets read half way and
    // reported whole. One sound stream elsewhere is all it takes to balance.
    ['a keyword followed by a lone carriage return', Buffer.concat([
      Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'),
      Buffer.from('2 0 obj\n<< /Length ' + halo.length + ' >>\nstream\r'), halo,
      Buffer.from('\nendstream\nendobj\n')]), false],
    // Two payloads laid end to end spell an operator across the join that
    // neither of them contains. This document has no halo in it anywhere and
    // has to pass; a scan over the payloads run together fails it.
    ['two payloads whose join spells an operator', (() => {
      const first = Buffer.from('BT ET\n1.0 1.0 1.0 rg\n3. w\n1. ');
      const second = Buffer.from('G\nBT ET\n');
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length ' + first.length + ' >>\nstream\n'), first,
        Buffer.from('\nendstream\nendobj\n2 0 obj\n<< /Length ' + second.length + ' >>\nstream\n'),
        second, Buffer.from('\nendstream\nendobj\n')]);
    })(), true],
    // A second object wearing the same number. The lookup runs over the whole
    // file, payloads included, so this shape can turn up in a stream's bytes
    // without being an object; here it names a size that lands on an `endstream`
    // the payload carries, which the landing check cannot tell from a sound one.
    // One object with that number, or there is no size here to act on.
    ['two objects sharing the number a length points at', (() => {
      const body = Buffer.concat([Buffer.from('123456endstream\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n8 0 obj\n(9 0 obj 6 endobj)\nendobj\n'),
        Buffer.from('1 0 obj\n<< /Length 9 0 R >>\nstream\n'), body,
        Buffer.from('\nendstream\nendobj\n9 0 obj\n' + body.length + '\nendobj\n')]);
    })(), false],
    // Two streams that decode to nothing at all. The separator between payloads
    // is a byte like any other, so joining two empty ones produced a one-byte
    // result -- enough to satisfy the only part of the verdict that asks whether
    // anything was read. One empty stream was rejected and two were not.
    ['two streams that decode to nothing', Buffer.from(
      '%PDF-1.4\n1 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n'
      + '2 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n'), false],
    // A filter names itself with an escape. `/#46ilter` is `/Filter` to a
    // reader and nothing at all to a substring match, so the deflate payload
    // would be scanned for operators as though it were stored -- and compressed
    // bytes spell no halo. The stream is read both ways instead.
    ['a filter whose name is escaped', (() => {
      const body = zlib.deflateSync(halo);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /#46ilter /FlateDecode /Length ' + body.length + ' >>\nstream\n'),
        body, Buffer.from('\nendstream\nendobj\n')]);
    })(), false],
    // Following the reference is a capability, not a guard: without it this
    // sound document states no size this side can read and is reported unread,
    // which is safe but wrong about the file. So the case that holds it is one
    // that has to be accepted.
    ['an indirect length on a document with nothing to find', (() => {
      const body = zlib.deflateSync(Buffer.from('BT ET\n'));
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Filter /FlateDecode /Length 9 0 R >>\nstream\n'), body,
        Buffer.from('\nendstream\nendobj\n9 0 obj\n' + body.length + '\nendobj\n')]);
    })(), true],
    // `/DecodeParms` describes the filter, and its `/Length` is not the
    // stream's. Reading the first one found in the dictionary text recorded a
    // mismatch on a document that stated its own size perfectly well.
    ['a nested dictionary stating its own length', (() => {
      const body = zlib.deflateSync(Buffer.from('BT ET\n'));
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Filter /FlateDecode /DecodeParms << /Length 5 >> /Length '
          + body.length + ' >>\nstream\n'),
        body, Buffer.from('\nendstream\nendobj\n')]);
    })(), true],
    // `_` continues a name to a PDF reader, so `/end_stream` is one name and not
    // a keyword. Ending a token at letters and digits alone started a stream
    // inside this dictionary and swallowed the object that really has one.
    ['a name holding the keyword after an underscore', Buffer.from(
      '%PDF-1.4\n1 0 obj\n<< /Type /end_stream\n>>\nendobj\n'
      + '2 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'), true],
    // A reference whose object number has more than one digit. Excluding
    // `N M R` with a negative lookahead let the engine backtrack the length from
    // `99` to `9`, decide `9 0 R` was not a reference after all, and read nine
    // bytes of the stream -- stopping just before the halo.
    ['a multi-digit indirect length', (() => {
      const body = Buffer.concat([Buffer.from('123456789endstream\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 99 0 R >>\nstream\n'), body,
        Buffer.from('\nendstream\nendobj\n99 0 obj\n' + body.length + '\nendobj\n')]);
    })(), false],
    // The decoy-length case above is also caught by the mismatch guard, so it
    // does not pin string handling on its own. Here the decoy lands exactly on
    // an `endstream` the payload carries, so reading it looks entirely sound --
    // and the halo behind it disappears.
    ['a decoy length that lands on an embedded end keyword', (() => {
      const body = Buffer.concat([Buffer.from('123456789endstream\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Note (/Length 9) /Length ' + body.length + ' >>\nstream\n'),
        body, Buffer.from('\nendstream\nendobj\n')]);
    })(), false],
    // A dictionary introduces the stream that directly follows it and no other.
    // Reaching back for the last one seen would read this catalogue's absent
    // `/Filter` and hand a deflate payload to the scanner as raw operators.
    ['a stream whose own object states no dictionary', (() => {
      // The borrowed dictionary has to state a length that lands somewhere
      // plausible, or the mismatch guard stops this before attribution does.
      // Here the six bytes it names end on an `endstream` the payload carries,
      // so the borrowed size reads as sound and the halo behind it is dropped.
      const body = Buffer.concat([Buffer.from('123456endstream\n'), halo]);
      return Buffer.concat([
        Buffer.from('%PDF-1.4\n1 0 obj\n<< /Length 6 >>\nstream\nBT ET\nendstream\nendobj\n'),
        Buffer.from('2 0 obj\nstream\n'), body, Buffer.from('\nendstream\nendobj\n')]);
    })(), false],
  ];
  // Every failure, not the first. Which cases fail together is what says
  // whether a case still fails for its own reason or has quietly come to lean
  // on a guard added later for something else.
  const failures = cases
    .filter(([, buf, shouldAccept]) => accepted(buf) !== shouldAccept)
    .map(([label, , shouldAccept]) => `stream tally ${shouldAccept ? 'rejected' : 'accepted'} ${label}`);
  if (failures.length > 0) {
    for (const failure of failures) console.error(failure);
    process.exit(1);
  }
  console.log('viewer browser gate: stream tally self-check passed');
}
// Same candidate set as the VSCode preview verification scripts, so one
// CHROME_BIN works for every browser-backed maintenance gate in the repo.
// Google Chrome comes first because distributions increasingly ship
// /usr/bin/chromium as a snap wrapper, which cannot open a DevTools endpoint
// from a confined environment such as a CI runner.
const CHROME_CANDIDATES = ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'];

function locateChrome() {
  const envChrome = process.env.CHROME_BIN || process.env.PUPPETEER_EXECUTABLE_PATH;
  if (envChrome) {
    if (!fs.existsSync(envChrome)) {
      throw new Error(`CHROME_BIN points at a missing executable: ${envChrome}`);
    }
    return envChrome;
  }
  for (const name of CHROME_CANDIDATES) {
    const found = spawnSync('which', [name]);
    if (found.status === 0 && found.stdout.toString().trim()) {
      return found.stdout.toString().trim();
    }
  }
  throw new Error(
    `no Chromium-family browser found; tried CHROME_BIN, PUPPETEER_EXECUTABLE_PATH and ${CHROME_CANDIDATES.join(', ')}`,
  );
}

// A cold CI runner needs noticeably longer than a warm workstation to bring up
// the DevTools endpoint, so the budget is seconds rather than a few hundred
// milliseconds. Chrome's own stderr is reported when the budget runs out.
const DEVTOOLS_STARTUP_ATTEMPTS = Number(process.env.VIEWER_DEVTOOLS_ATTEMPTS || 300);

async function waitForJson(url, describeBrowser) {
  const attempts = DEVTOOLS_STARTUP_ATTEMPTS;
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
    } catch (_) { /* Chrome has not opened its debugging port yet. */ }
    await sleep(100);
  }
  throw new Error(`Chrome DevTools endpoint did not start${describeBrowser()}`);
}

// A browser that dies mid-run used to leave the awaiting call pending forever:
// neither the catch nor the finally ran and node exited 0 with no output, which
// is a false green in the likeliest CI failure of all — the renderer running out
// of memory on a 29 MB page. Every call is bounded and the socket's death fails
// the ones in flight. The budget covers the slowest legitimate step, the export,
// which waits up to 30s for a fresh payload.
const CALL_TIMEOUT_MS = Number(process.env.VIEWER_CALL_TIMEOUT_MS || 120000);

class Cdp {
  constructor(url) { this.socket = new WebSocket(url); this.next = 0; this.pending = new Map(); this.events = []; this.dead = null; }
  async connect() {
    await new Promise((resolve, reject) => {
      this.socket.once('open', resolve);
      this.socket.once('error', reject);
    });
    // The connect listener stays attached otherwise, so every later socket
    // error is delivered to an already-settled promise and vanishes.
    this.socket.removeAllListeners('error');
    this.socket.on('message', data => {
      const message = JSON.parse(String(data));
      if (message.id && this.pending.has(message.id)) {
        const {resolve, reject} = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message)); else resolve(message.result);
      } else if (message.method) this.events.push(message);
    });
    const fail = reason => {
      this.dead = this.dead || reason;
      for (const [id, {reject}] of [...this.pending]) {
        this.pending.delete(id);
        reject(new Error(reason));
      }
    };
    this.socket.on('close', code => fail(`DevTools connection closed (code ${code}); the browser died mid-run`));
    this.socket.on('error', error => fail(`DevTools connection error: ${error && error.message}`));
  }
  call(method, params = {}) {
    if (this.dead) return Promise.reject(new Error(`${method} after ${this.dead}`));
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} did not answer within ${CALL_TIMEOUT_MS}ms`));
      }, CALL_TIMEOUT_MS);
      this.pending.set(id, {
        resolve: value => { clearTimeout(timer); resolve(value); },
        reject: error => { clearTimeout(timer); reject(error); },
      });
      this.socket.send(JSON.stringify({id, method, params}));
    });
  }
  close() {
    // A normal WebSocket close may wait for Chrome's debugging endpoint;
    // terminate the maintenance connection so the checker can finish.
    this.socket.terminate();
  }
}

function stopChrome(child) {
  if (!child || !child.pid) return;
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], {stdio: 'ignore'});
    return;
  }
  try {
    process.kill(-child.pid, 'SIGTERM');
  } catch (error) {
    // ESRCH means Chrome already exited; any other cleanup failure is real.
    if (!error || typeof error !== 'object' || error.code !== 'ESRCH') throw error;
  }
}

function awaitChromeExit(child, timeoutMs = 5000) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return Promise.resolve();
  return new Promise(resolve => {
    const done = () => { clearTimeout(timer); resolve(); };
    const timer = setTimeout(done, timeoutMs);
    child.once('exit', done);
  });
}

async function realClick(cdp, x, y) {
  await cdp.call('Input.dispatchMouseEvent', {type: 'mouseMoved', x, y});
  await sleep(80);
  await cdp.call('Input.dispatchMouseEvent', {type: 'mousePressed', x, y, button: 'left', clickCount: 1});
  await sleep(60);
  await cdp.call('Input.dispatchMouseEvent', {type: 'mouseReleased', x, y, button: 'left', clickCount: 1});
}

/**
 * Open the first option-list control with a real input sequence and report how
 * its popup is actually painted, including the trigger width it should stay
 * anchored to. A popup that is invisible, unpainted, or far wider than its
 * trigger is a styling failure, not a passing run.
 */
async function openSelectMenu(cdp) {
  const box = await evaluate(cdp, `(() => {
    const el = document.querySelector('.n-base-selection');
    if (!el) return {found: false};
    const rect = el.getBoundingClientRect();
    return {found: true, x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2), triggerWidth: Math.round(rect.width)};
  })()`);
  if (!box.found) return {found: false};
  await realClick(cdp, box.x, box.y);
  await sleep(400);
  const menu = await evaluate(cdp, `(() => {
    const el = document.querySelector('.n-base-select-menu');
    if (!el || !el.getClientRects().length) return {menuVisible: false};
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const option = el.querySelector('.n-base-select-option');
    const optionStyle = option ? getComputedStyle(option) : null;
    const alpha = value => {
      // rgb() carries no alpha channel and is opaque; rgba() and color() carry
      // one. Anything else yields NaN so the verdict fails rather than reading
      // an unrecognised serialisation as fully opaque.
      const text = String(value);
      if (/^rgb\\([^)]*\\)$/.test(text)) return 1;
      const legacy = text.match(/^rgba\\([^)]*,\\s*([0-9.]+)\\)$/);
      if (legacy) return Number(legacy[1]);
      const modern = text.match(/^color\\([^)]*\\/\\s*([0-9.]+)\\s*\\)$/);
      if (modern) return Number(modern[1]);
      if (/^color\\([^/)]*\\)$/.test(text)) return 1;
      return NaN;
    };
    return {
      menuVisible: true,
      menuBackground: style.backgroundColor,
      menuAlpha: alpha(style.backgroundColor),
      menuBoxShadow: style.boxShadow,
      menuWidth: Math.round(rect.width),
      optionCount: el.querySelectorAll('.n-base-select-option').length,
      optionBackground: optionStyle ? optionStyle.backgroundColor : '',
      optionAlpha: optionStyle ? alpha(optionStyle.backgroundColor) : 0,
    };
  })()`);
  const escape = {key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27};
  await cdp.call('Input.dispatchKeyEvent', {type: 'keyDown', ...escape});
  await cdp.call('Input.dispatchKeyEvent', {type: 'keyUp', ...escape});
  await sleep(200);
  return {found: true, triggerWidth: box.triggerWidth, ...menu};
}

async function evaluate(cdp, expression) {
  const result = await cdp.call('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
  if (result.exceptionDetails) {
    // Carry the probe with the failure. Only a handful of steps record their
    // own outcome; the rest throw, and without this the operator sees a stack
    // that names this helper rather than the assertion that broke.
    const probe = expression.replace(/\s+/g, ' ').trim().slice(0, 140);
    throw new Error(`${result.exceptionDetails.text || 'browser evaluation failed'} [probe: ${probe}]`);
  }
  return result.result && result.result.value;
}

(async () => {
  const port = 9222 + Math.floor(Math.random() * 200);
  // Resolve first: a failure here must not leave a profile directory behind,
  // because the cleanup below only runs once the browser has been spawned.
  const chromeBinary = locateChrome();
  const userData = fs.mkdtempSync(path.join(os.tmpdir(), 'pyfcstm-viewer-'));
  const chrome = spawn(chromeBinary, [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--no-first-run',
    '--no-default-browser-check', `--remote-debugging-port=${port}`,
    `--window-size=${viewportWidth},${viewportHeight}`,
    `--user-data-dir=${userData}`, 'about:blank',
  ], {stdio: ['ignore', 'ignore', 'pipe'], detached: process.platform !== 'win32'});
  // Keep the browser's own diagnostics: without them a launch failure is
  // indistinguishable from a slow start once the port probe times out.
  let chromeStderr = '';
  chrome.stderr.on('data', chunk => { chromeStderr += String(chunk); });
  let chromeSpawnError = null;
  chrome.on('error', err => { chromeSpawnError = err; });
  let chromeExit = null;
  chrome.on('exit', (code, signal) => { chromeExit = signal ? `signal ${signal}` : `exit code ${code}`; });
  const describeBrowser = () => {
    const details = [`binary ${chromeBinary}`];
    if (chromeSpawnError) details.push(`spawn error ${chromeSpawnError.message}`);
    if (chromeExit !== null) details.push(`browser stopped with ${chromeExit}`);
    const stderrTail = chromeStderr.trim().split('\n').slice(-5).join('; ');
    if (stderrTail) details.push(`stderr ${stderrTail}`);
    return ` (${details.join('; ')})`;
  };
  // Declared out here so the catch below can still read the session's
  // events when a probe throws before the report is built.
  let cdp = null;
  try {
    const targets = await waitForJson(`http://127.0.0.1:${port}/json`, describeBrowser);
    const page = targets.find(item => item.type === 'page');
    if (!page) throw new Error('Chrome did not expose a page target');
    cdp = new Cdp(page.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.call('Page.enable');
    await cdp.call('Runtime.enable');
    await cdp.call('Network.enable');
    await cdp.call('Security.enable');
    // Inline-style CSP violations are only surfaced through Log.entryAdded;
    // Security.securityPolicyViolationReported never reports them, so relying
    // on that domain alone reports a clean policy for a page that has none.
    await cdp.call('Log.enable');
    await cdp.call('Emulation.setDeviceMetricsOverride', {
      width: viewportWidth,
      height: viewportHeight,
      deviceScaleFactor: 1,
      mobile: viewportWidth < 700,
    });
    await cdp.call('Page.navigate', {url: `file://${path.resolve(htmlPath)}`});
    await sleep(startupWait);

    // Counted in the page the reader actually looks at, and counted here --
    // before the run collapses a composite and its leaf states leave the DOM
    // with their rows. Every setting the detail presets disagree on used to
    // stop before the drawing, so the three levels produced one picture
    // between them, and nothing here noticed because nothing here looked.
    const stateRows = await evaluate(cdp, `(() => ({
      'state-event': document.querySelectorAll('[data-fcstm-kind="state-event"]').length,
      'state-action': document.querySelectorAll('[data-fcstm-kind="state-action"]').length,
    }))()`);

    const initial = await evaluate(cdp, `({
      source: Boolean(document.querySelector('.fcstm-source-panel')),
      stage: Boolean(document.querySelector('.fcstm-stage svg')),
      error: (document.querySelector('.fcstm-stage__empty-title') || {}).textContent || '',
      sourceAvailable: window.__FCSTM_INITIAL_STATE__?.sourceAvailable !== false,
      sourceUnavailableMessage: document.querySelector('.fcstm-source-panel__unavailable')?.textContent?.trim() || '',
      sourceCodePanel: Boolean(document.querySelector('.fcstm-source-panel__code')),
      fontFaces: [...(document.fonts || [])].map(font => ({family: font.family, weight: font.weight, status: font.status})),
    })`);
    const sourceLayout = await evaluate(cdp, `(async () => {
      const rows = [...document.querySelectorAll('.fcstm-source-line')];
      const boxes = rows.map(row => row.getBoundingClientRect());
      const gaps = boxes.slice(1).map((box, index) => box.top - (boxes[index].bottom));
      const lineNumbers = rows.map(row => ({
        value: getComputedStyle(row, '::before').content,
        align: getComputedStyle(row, '::before').textAlign,
      }));
      const nativeSelect = document.querySelector('.fcstm-source-panel__header select');
      const nativeSelectStyle = nativeSelect ? getComputedStyle(nativeSelect) : null;
      const alpha = value => {
        // Same fail-closed rule as openSelectMenu: an unrecognised colour
        // serialisation must not read as opaque.
        const text = String(value);
        if (/^rgb\\([^)]*\\)$/.test(text)) return 1;
        const legacy = text.match(/^rgba\\([^)]*,\\s*([0-9.]+)\\)$/);
        if (legacy) return Number(legacy[1]);
        const modern = text.match(/^color\\([^)]*\\/\\s*([0-9.]+)\\s*\\)$/);
        if (modern) return Number(modern[1]);
        if (/^color\\([^/)]*\\)$/.test(text)) return 1;
        return NaN;
      };
      return {
        lineCount: rows.length,
        textHasLineBreaks: rows.length < 2 || (document.querySelector('.fcstm-source-panel__code')?.textContent || '').includes('\\n'),
        lineNumbers,
        lineHeights: boxes.map(box => box.height),
        maxGap: Math.max(0, ...gaps),
        nativeSelectBackground: nativeSelectStyle?.backgroundColor || '',
        nativeSelectAlpha: nativeSelectStyle ? alpha(nativeSelectStyle.backgroundColor) : 1,
      };
    })()`);
    // The component library ignores synthesised MouseEvents, so the popup has
    // to be opened with a real input sequence or every assertion below it is
    // silently skipped on a null menu.
    const selectMenu = await openSelectMenu(cdp);
    // Mode buttons are selected through `data-fcstm-mode`, not their visible
    // label: matching display copy made a renamed button click nothing and the
    // resulting wrong-mode failure surfaced far away, in the export step. A
    // missing handle is reported as a field so the cause stays where the
    // problem is: throwing from a timer callback never rejects the promise at
    // all, and rejecting would abort before the report is printed.
    const clickMode = mode => `new Promise(resolve => setTimeout(() => {
      const button = document.querySelector('.fcstm-standalone-mode button[data-fcstm-mode="${mode}"]');
      if (!button) {
        resolve({buttonFound: false, source: false, stage: false, renderedStage: false});
        return;
      }
      button.click();
      setTimeout(() => resolve({
        buttonFound: true,
        source: Boolean(document.querySelector('.fcstm-source-panel')),
        stage: Boolean(document.querySelector('.fcstm-stage')),
        renderedStage: Boolean(document.querySelector('.fcstm-stage svg')),
      }), 120);
    }, 80))`;
    const diagramOnlyRaw = await evaluate(cdp, clickMode('diagram'));
    const states = {diagramOnlySource: diagramOnlyRaw.source, diagramOnlyStage: diagramOnlyRaw.stage, buttonFound: diagramOnlyRaw.buttonFound};
    const compare = await evaluate(cdp, clickMode('compare'));
    const fcstmOnlyRaw = await evaluate(cdp, clickMode('fcstm'));
    const fcstmOnly = {source: fcstmOnlyRaw.source, stage: fcstmOnlyRaw.renderedStage, buttonFound: fcstmOnlyRaw.buttonFound};
    const backToCompareRaw = await evaluate(cdp, clickMode('compare'));
    const backToCompare = {source: backToCompareRaw.source, stage: backToCompareRaw.renderedStage, buttonFound: backToCompareRaw.buttonFound};
    const importedSource = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const select = document.querySelector('.fcstm-source-panel__header select');
      const published = Object.keys(window.__FCSTM_INITIAL_STATE__?.sourceDocuments || {});
      const options = select ? [...select.options].map(option => option.value) : [];
      if (published.length < 2) {
        resolve({published, documents: options, pickerFound: Boolean(select), selectedDocument: '', childText: false, selected: 0});
        return;
      }
      if (!select) {
        resolve({published, documents: [], pickerFound: false, selectedDocument: '', childText: false, selected: 0});
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
        setTimeout(() => resolve({published, documents: options, pickerFound: true, selectedDocument: select.value, childText,
          selected: document.querySelectorAll('.fcstm-selected').length}), 220);
      }, 120);
    }, 80))`);
    // Every link assertion below measures a transition out of a cleared state
    // instead of a level. Sharing one page across steps meant the previous
    // step's selection or hover already satisfied the next assertion — four
    // source lines were active and one element was hovered before their own
    // actions ran — so breaking the behaviour under test left the gate green.
    const CLEAR_INTERACTION = `(async () => {
      for (const element of document.querySelectorAll('[data-fcstm-kind], .fcstm-source-line')) {
        element.dispatchEvent(new MouseEvent('mouseout', {bubbles: true, relatedTarget: null}));
      }
      document.querySelector('.fcstm-stage__viewport')
        ?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      await new Promise(resolve => setTimeout(resolve, 240));
      return {
        selected: document.querySelectorAll('.fcstm-selected').length,
        activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length,
        sourceHover: document.querySelectorAll('.fcstm-source-hover').length,
      };
    })()`;
    // The sidecar publishes a document-qualified key next to a legacy numeric
    // one, and api.py marks the numeric form as compatibility-only. Taking the
    // line from the qualified key survives that form being dropped; indexing
    // the raw key relied on JS enumerating integer-like keys first, and would
    // otherwise match no element and let these steps pass on residue.
    const sourceLineSelector = `(() => {
      const map = window.__FCSTM_INITIAL_STATE__?.sourceLineMap || {};
      const key = Object.keys(map)[0];
      if (key === undefined) return '';
      const line = key.includes(':') ? key.slice(key.lastIndexOf(':') + 1) : key;
      return '.fcstm-source-line[data-line="' + line + '"]';
    })()`;
    const selectionBefore = await evaluate(cdp, CLEAR_INTERACTION);
    const selection = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const target = document.querySelector('[data-fcstm-kind="state"]');
      target?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({selected: document.querySelectorAll('.fcstm-selected').length, activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length, target: target?.getAttribute('data-fcstm-id') || '', kind: target?.getAttribute('data-fcstm-kind') || ''}), 220);
    }, 220))`);
    selection.before = selectionBefore;
    // Details lives behind the drawer, which starts collapsed on short narrow
    // viewports, so the reveal control has to be brought on screen before it can
    // be required to exist.
    await evaluate(cdp, `new Promise(resolve => {
      const toggle = document.querySelector('[data-fcstm-action="toggle-details"]');
      if (toggle && toggle.getAttribute('aria-pressed') === 'false') toggle.click();
      setTimeout(resolve, 240);
    })`);
    // In the standalone host the reveal control re-applies the range that is
    // already selected, so there is no state transition to observe. The honest
    // assertion is that the control is present and leaves the source link
    // intact; a renamed or removed button now fails here instead of silently
    // skipping, which is how the mode buttons used to behave.
    // Ctrl/Cmd+click must reveal the element under the cursor. Resolving the
    // clicked line back to an element instead picked whichever one in any
    // source document had the smallest range covering it, so in a model built
    // from several files it selected something else entirely while the source
    // panel still highlighted the original line.
    const revealTarget = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const target = document.querySelector('[data-fcstm-kind="state"][data-fcstm-id]');
      const wanted = target?.getAttribute('data-fcstm-id') || '';
      target?.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0, ctrlKey: true}));
      setTimeout(() => resolve({
        wanted,
        selected: document.querySelector('[data-fcstm-id].fcstm-selected')?.getAttribute('data-fcstm-id') || '',
      }), 320);
    }, 200))`);
    const revealSource = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const button = [...document.querySelectorAll('.fcstm-details button')].find(item => item.textContent.includes('Reveal source'));
      if (!button) { resolve({buttonFound: false, activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length}); return; }
      button.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({buttonFound: true, activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length}), 220);
    }, 180))`);
    const hoverBefore = await evaluate(cdp, CLEAR_INTERACTION);
    const hover = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const target = document.querySelector('[data-fcstm-kind="state"]');
      target?.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, relatedTarget: null}));
      setTimeout(() => resolve({activeSourceLines: document.querySelectorAll('.fcstm-source-line--active').length}), 220);
    }, 220))`);
    hover.before = hoverBefore;
    const sourceHoverBefore = await evaluate(cdp, CLEAR_INTERACTION);
    const sourceHover = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const selector = ${sourceLineSelector};
      const line = selector ? document.querySelector(selector) : null;
      if (!line) { resolve({lineFound: false, diagramHover: 0}); return; }
      line.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, relatedTarget: null}));
      setTimeout(() => resolve({lineFound: true, diagramHover: document.querySelectorAll('.fcstm-source-hover').length}), 220);
    }, 220))`);
    sourceHover.before = sourceHoverBefore;
    const transitionHover = await evaluate(cdp, `(async () => {
      // Prefer a labelled transition: the first element ELK emits is often a
      // composite's initial transition, which carries no label, and the label
      // and note clauses below would then assert over an empty set.
      const labelled = new Set([...document.querySelectorAll('[data-fcstm-kind="transition-label"]')]
        .map(item => item.getAttribute('data-fcstm-id')));
      const transitions = [...document.querySelectorAll('[data-fcstm-kind="transition"][data-fcstm-id]')];
      const transition = transitions.find(item => labelled.has(item.getAttribute('data-fcstm-id')))
        || transitions[0] || null;
      const transitionId = transition?.getAttribute('data-fcstm-id') || '';
      transition?.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, relatedTarget: null}));
      await new Promise(resolve => setTimeout(resolve, 220));
      const label = [...document.querySelectorAll('[data-fcstm-kind="transition-label"]')]
        .find(item => item.getAttribute('data-fcstm-id') === transitionId);
      const noteParts = label ? [...label.children].filter(item => item.tagName.toLowerCase() === 'path') : [];
      const style = element => element ? getComputedStyle(element) : null;
      const transitionStyle = style(transition);
      const labelStyle = style(label);
      return {
        hasTransition: Boolean(transition),
        hasLabel: Boolean(label),
        noteCount: noteParts.length,
        transitionId,
        transitionClass: transition?.getAttribute('class') || '',
        transitionFilter: transitionStyle?.filter || '',
        transitionFill: transitionStyle?.fill || '',
        transitionStroke: transitionStyle?.stroke || '',
        transitionStrokeWidth: transitionStyle?.strokeWidth || '',
        labelClass: label?.getAttribute('class') || '',
        labelFilter: labelStyle?.filter || '',
        noteParts: noteParts.map(item => ({
          className: item.getAttribute('class') || '',
          filter: style(item)?.filter || '',
          stroke: style(item)?.stroke || '',
        })),
      };
    })()`);
    const sourceSelectionBefore = await evaluate(cdp, CLEAR_INTERACTION);
    const sourceSelection = await evaluate(cdp, `new Promise(resolve => setTimeout(() => {
      const selector = ${sourceLineSelector};
      const line = selector ? document.querySelector(selector) : null;
      if (!line) { resolve({lineFound: false, selected: 0}); return; }
      line.dispatchEvent(new MouseEvent('click', {bubbles: true, button: 0}));
      setTimeout(() => resolve({lineFound: true, selected: document.querySelectorAll('.fcstm-selected').length}), 220);
    }, 220))`);
    sourceSelection.before = sourceSelectionBefore;
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
    // Recorded rather than thrown, for the same reason as the handles above:
    // a missing export control or a payload that never arrives is a finding the
    // report should carry, not a reason to exit without one.
    let exportError = '';
    const pdfExpression = `(async () => {
      const formats = new Set(${JSON.stringify([...requestedFormats])});
      // Each export runs resvg twice (PNG/SVG once, vector PDF once more), so
      // wait for a fresh payload instead of a fixed delay: a fixed delay makes
      // the first export flaky and lets the rerender check silently compare the
      // previous payload with itself.
      const awaitFreshExport = previous => new Promise((resolve, reject) => {
        const deadline = Date.now() + 30000;
        // Click the control a user clicks rather than dispatching the internal
        // event it emits. Firing the event directly leaves the button, its
        // handler, and its wiring untested, so an export that no user can reach
        // still produced payloads and a green run.
        const button = document.querySelector('[data-fcstm-action="export"]');
        if (!button) return reject(new Error('export control not found'));
        button.click();
        const poll = () => {
          const current = window.__FCSTM_LAST_EXPORT__;
          if (current && current !== previous) return resolve(current);
          if (Date.now() > deadline) return reject(new Error('viewer export did not produce a payload'));
          setTimeout(poll, 50);
        };
        poll();
      });
      // Chain rather than nest: with a two-argument .then a synchronous throw
      // inside the body (atob, PDF parsing) escapes the reject handler, and the
      // untimed CDP evaluate above it would then hang for the whole job.
      const exportOnce = previous => awaitFreshExport(previous).then(fresh => new Promise(resolve => {
        const payload = fresh || {};
        const exportedSvg = String(payload?.svg || '');
        const raw = payload?.pdfBase64 ? atob(payload.pdfBase64) : '';
        const pngRaw = payload?.pngBase64 ? atob(payload.pngBase64) : '';
        // jsPDF intentionally varies document metadata for each export. Ignore
        // only those volatile fields so rerender checks still compare all
        // actual page/content bytes.
        const normalizePdfSignature = value => String(value)
          .replace(/\\/CreationDate\\s*\\([^)]*\\)/g, '/CreationDate (NORMALIZED)')
          .replace(/\\/ID\\s*\\[\\s*<[^>]+>\\s*<[^>]+>\\s*\\]/g, '/ID [ <NORMALIZED> <NORMALIZED> ]');
        const contentSignature = {svg: exportedSvg, png: payload?.pngBase64 || '', pdf: normalizePdfSignature(raw)};
        const hex = value => [...value].map(char => char.charCodeAt(0).toString(16).padStart(2, '0')).join('');
        const readU32 = (value, offset) => value.length >= offset + 4
          ? (((value.charCodeAt(offset) & 255) << 24) | ((value.charCodeAt(offset + 1) & 255) << 16) |
             ((value.charCodeAt(offset + 2) & 255) << 8) | (value.charCodeAt(offset + 3) & 255)) >>> 0 : 0;
        const pngHeader = hex(pngRaw.slice(0, 8));
        const pngWidth = readU32(pngRaw, 16);
        const pngHeight = readU32(pngRaw, 20);
        const mediaBox = raw.match(/\\/MediaBox\\s*\\[\\s*0\\s+0\\s+([0-9.]+)\\s+([0-9.]+)\\s*\\]/);
        const viewBox = exportedSvg.match(/\\bviewBox=["']\\s*0\\s+0\\s+([0-9.]+)\\s+([0-9.]+)\\s*["']/);
        const finish = (pngDecodedWidth, pngDecodedHeight, pngNonBlankPixels, pngOpaque) => resolve({
          menu: Boolean(document.querySelector('#fcstm-standalone-export-menu')),
          fatal: document.querySelector('[data-fcstm-fatal="true"]')?.textContent || '',
          base64: payload?.pdfBase64 || '',
          signature: {
            svgBytes: exportedSvg.length,
            pngBytes: pngRaw.length,
            pdfBytes: raw.length,
          },
          _contentSignature: contentSignature,
          bytes: raw.length,
          header: raw.slice(0, 5),
          images: (raw.match(/\\/Subtype\\s*\\/Image\\b|\\/ImageMask\\b/g) || []).length,
          pages: (raw.match(/\\/Type \\/Page\\b/g) || []).length,
          // The exported palette, so the parity checker can compare colour and
          // not only geometry. A presentation option that reaches one export
          // path and not the other produces a perfectly valid file of the
          // wrong colour, which every structural assertion waves through.
          svgFills: Array.from(new Set(
            (exportedSvg.match(/fill="[^"]+"/g) || [])
              .map(item => item.slice(6, -1).toLowerCase()),
          )).sort(),
          svgText: (exportedSvg.match(/<text\\b/g) || []).length,
          svgMarker: (exportedSvg.match(/<marker\\b/g) || []).length,
          svgFontFamily: (exportedSvg.match(/font-family[=:]/g) || []).length,
          pngBytes: pngRaw.length, pngHeader, pngWidth, pngHeight,
          pngDecodedWidth, pngDecodedHeight, pngNonBlankPixels, pngOpaque,
          pdfWidth: mediaBox ? Number(mediaBox[1]) : 0,
          pdfHeight: mediaBox ? Number(mediaBox[2]) : 0,
          svgWidth: viewBox ? Number(viewBox[1]) : 0,
          svgHeight: viewBox ? Number(viewBox[2]) : 0,
        });
        if (!formats.has('png') || !pngRaw) {
          finish(0, 0, 0, false);
          return;
        }
        const image = new Image();
        image.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = image.naturalWidth;
          canvas.height = image.naturalHeight;
          const context = canvas.getContext('2d', {willReadFrequently: true});
          let nonBlankPixels = 0;
          let opaque = true;
          if (context) {
            context.drawImage(image, 0, 0);
            const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
            for (let index = 0; index < pixels.length; index += 4) {
              if (pixels[index + 3] !== 255) opaque = false;
              if (pixels[index + 3] > 0 && (pixels[index] < 245 || pixels[index + 1] < 245 || pixels[index + 2] < 245)) {
                nonBlankPixels += 1;
                if (nonBlankPixels >= 10) break;
              }
            }
          }
          finish(image.naturalWidth, image.naturalHeight, nonBlankPixels, opaque);
        };
        image.onerror = () => finish(0, 0, 0, false);
        image.src = pngRaw ? 'data:image/png;base64,' + payload.pngBase64 : '';
      }));
      await new Promise(resolve => setTimeout(resolve, 120));
      const firstPayload = window.__FCSTM_LAST_EXPORT__;
      const first = await exportOnce(firstPayload);
      if (!${JSON.stringify(requirePdfRerender)}) {
        delete first._contentSignature;
        return first;
      }
      const second = await exportOnce(window.__FCSTM_LAST_EXPORT__);
      first.rerenderSame = JSON.stringify(first._contentSignature) === JSON.stringify(second._contentSignature);
      delete first._contentSignature;
      return first;
    })()`;
    let pdf;
    try {
      pdf = await evaluate(cdp, pdfExpression);
    } catch (error) {
      // Error: `evaluate` wraps every browser-side rejection in one, including
      // the export deadline and the missing-control guard. Anything that is not
      // an Error did not come from there and propagates.
      if (!(error instanceof Error)) throw error;
      exportError = error.message;
      pdf = {fatal: '', menu: false, signature: {}, base64: ''};
    }
    const pdfStreams = inflatePdfStreams(pdf.base64);
    const pdfStreamText = pdfStreams.text;
    // The halo check is a zero-count, so it passes trivially when no stream
    // inflates — a filter change or an object-stream layout would retire the
    // check without a word. Record the scanned size and the per-stream tally,
    // and assert below that every stream was read, not merely that one was.
    pdf.inflatedStreamBytes = pdfStreamText.length;
    pdf.pdfStreamsTotal = pdfStreams.total;
    pdf.pdfStreamsDecoded = pdfStreams.decoded;
    pdf.pdfStreamsSkipped = pdfStreams.skipped;
    pdf.whiteHaloOperators = (pdfStreamText.match(/[0-9.]+ [0-9.]+ [0-9.]+ rg\n3\. w\n1\. G/g) || []).length;
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
      const bottom = document.querySelector('.fcstm-bottom');
      const source = document.querySelector('.fcstm-source-panel');
      const stage = document.querySelector('.fcstm-stage');
      const shell = document.querySelector('.fcstm-preview-shell');
      const drawer = document.querySelector('.fcstm-bottom-drawer');
      const drawerBody = document.querySelector('.fcstm-bottom-drawer__body');
      const rect = el => el ? ({x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y, width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height}) : null;
      const style = el => el ? ({display: getComputedStyle(el).display, flex: getComputedStyle(el).flex, minHeight: getComputedStyle(el).minHeight, height: getComputedStyle(el).height, overflow: getComputedStyle(el).overflow}) : null;
      return {viewport: {width: innerWidth, height: innerHeight}, shell: rect(shell), drawer: rect(drawer), main: rect(main), source: rect(source), stage: rect(stage), stageCount: document.querySelectorAll('.fcstm-stage').length, sourceCount: document.querySelectorAll('.fcstm-source-panel').length, stageRects: [...document.querySelectorAll('.fcstm-stage')].map(rect), sourceRects: [...document.querySelectorAll('.fcstm-source-panel')].map(rect), svgRects: [...document.querySelectorAll('svg')].map(svg => ({className: svg.parentElement?.className || '', rect: rect(svg)})), bottomIconStyles: [...document.querySelectorAll('.fcstm-bottom .n-base-icon')].map(icon => ({rect: rect(icon), width: getComputedStyle(icon).width, height: getComputedStyle(icon).height, display: getComputedStyle(icon).display})), mainStyle: style(main), shellStyle: style(shell), drawerStyle: style(drawer), drawerBody: rect(drawerBody), mainScrollHeight: main?.scrollHeight || 0, mainClientHeight: main?.clientHeight || 0, mainScrollWidth: main?.scrollWidth || 0, mainClientWidth: main?.clientWidth || 0, bottomScrollWidth: bottom?.scrollWidth || 0, bottomClientWidth: bottom?.clientWidth || 0};
    })()`);
    const network = cdp.events.filter(event => event.method === 'Network.requestWillBeSent').map(event => event.params.request.url).filter(url => !url.startsWith('file://') && !url.startsWith('data:') && !url.startsWith('blob:'));
    const cspViolations = [
      ...cdp.events
        .filter(event => event.method === 'Security.securityPolicyViolationReported')
        .map(event => ({source: 'security', text: event.params.violatedDirective || 'violation'})),
      ...cdp.events
        .filter(event => event.method === 'Log.entryAdded')
        .filter(event => /Content Security Policy/i.test(event.params.entry.text || ''))
        .map(event => ({source: 'log', text: (event.params.entry.text || '').slice(0, 160)})),
    ];
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
    // The bottom panels are a sibling of .fcstm-main-view, so a card row that
    // pushes past its container sat entirely outside the probed subtree. It is
    // not visible at document level either: measured at a 320px viewport, a
    // 320px grid track inside a 266px container gives bottomScrollWidth 320 vs
    // clientWidth 266 while documentElement.scrollWidth stays at 305, because
    // the excess is clipped rather than scrolled. So the container itself is
    // what has to be measured.
    const horizontalOverflow = layout.mainScrollWidth > layout.mainClientWidth + 1
      || layout.bottomClientWidth <= 0
      || layout.bottomScrollWidth > layout.bottomClientWidth + 1;
    // The drawer is content-sized until a drag fixes it, so it needs a bound at
    // both ends: collapsed to nothing hides Details, and unbounded growth eats
    // the stage. The upper bound matches the CSS max-height of 70vh.
    const drawerHeight = layout.drawer?.height || 0;
    // A collapsed drawer is a ~12px handle, which cleared a bare `height > 0`.
    // The body is what has to be on screen, and the run expands the drawer
    // before it reaches here, so requiring it is not viewport-dependent.
    const drawerBodyHeight = layout.drawerBody?.height || 0;
    const drawerChecks = drawerBodyHeight > 0
      && drawerHeight > drawerBodyHeight
      && drawerHeight <= (layout.viewport?.height || 0) * 0.72;
    const minimumPanelHeight = viewportHeight <= 700 ? 200 : 160;
    const comparisonSourceHeight = layout.source?.height || 0;
    const comparisonStageHeight = layout.stage?.height || 0;
    const comparisonTooShort = Boolean(compare.source && compare.stage &&
      (comparisonSourceHeight < minimumPanelHeight || comparisonStageHeight < minimumPanelHeight));
    const stateRowChecks = Object.entries(expectedStateRows)
      .filter(([, expected]) => expected !== null)
      .map(([kind, expected]) => ({kind, expected, actual: (stateRows || {})[kind]}))
      .filter(entry => entry.actual !== entry.expected);

    const oversizedUiIcons = (layout.svgRects || []).filter(item => /n-(?:base-icon|icon|checkbox-icon)/.test(item.className))
      .some(item => item.rect.width > 64 || item.rect.height > 64);
    const sourceLayoutChecks = !initial.sourceAvailable || (
      sourceLayout.lineCount >= 1 && sourceLayout.textHasLineBreaks &&
      sourceLayout.lineNumbers.every(item => item.align === 'right' && /^"\d+"$/.test(item.value)) &&
      sourceLayout.maxGap <= 1 &&
      // Rows must be painted. Every other clause here holds for a hidden panel:
      // the elements exist, textContent still reads, ::before still resolves,
      // and the gap between zero-height rects is zero.
      sourceLayout.lineHeights.length === sourceLayout.lineCount &&
      sourceLayout.lineHeights.every(height => height > 4)
    );
    // Every sample renders the option controls, so a missing trigger is a
    // rendering regression rather than a reason to skip these assertions. An
    // unstyled popup is transparent, shadowless, and grows far past its
    // trigger instead of staying anchored to it.
    const selectMenuChecks = (
      selectMenu.found === true &&
      selectMenu.menuVisible === true &&
      selectMenu.optionCount >= 1 &&
      selectMenu.menuAlpha === 1 &&
      selectMenu.menuBoxShadow !== 'none' &&
      selectMenu.menuWidth <= selectMenu.triggerWidth * 3
    );
    // A model without source must say so and must not present a code view.
    // Asserting the sentence itself would tie the gate to display copy, which
    // is how a renamed mode button turned into a silent no-op above.
    const sourceUnavailableChecks = initial.sourceAvailable || (
      initial.sourceUnavailableMessage.length > 0 && initial.sourceCodePanel === false
    );
    const sourceChecks = !initial.sourceAvailable || (
      selection.before.selected === 0 && selection.selected >= 1 &&
      selection.before.activeSourceLines === 0 && selection.activeSourceLines >= 1 &&
      revealSource.buttonFound === true && revealSource.activeSourceLines >= 1 &&
      revealTarget.wanted !== '' && revealTarget.selected === revealTarget.wanted &&
      hover.before.activeSourceLines === 0 && hover.activeSourceLines >= 1 &&
      sourceHover.lineFound === true &&
      sourceHover.before.sourceHover === 0 && sourceHover.diagramHover >= 1 &&
      sourceSelection.lineFound === true &&
      sourceSelection.before.selected === 0 && sourceSelection.selected >= 1
    );
    // The embedded faces are the only reason layout and every export agree
    // across machines, and a decode failure is reported as a banner rather than
    // an exception, so nothing else in this run would notice it.
    const fontChecks = initial.fontFaces.length > 0
      && initial.fontFaces.every(face => face.status === 'loaded')
      && pdf.fatal === '';
    // Every sample renders transitions, so a missing transition element is a
    // rendering regression rather than a reason to skip the hover assertions.
    const transitionChecks = (
      transitionHover.hasTransition === true &&
      Boolean(transitionHover.transitionId) && transitionHover.transitionFilter === 'none' &&
      transitionHover.transitionFill === 'none' &&
      // Require the label and its note geometry rather than treating their
      // absence as a pass: an unlabelled target made the halo clauses vacuous,
      // which is the behaviour the transition-hover work was about.
      transitionHover.hasLabel === true && transitionHover.labelFilter === 'none' &&
      (expectTransitionNotes ? transitionHover.noteCount >= 1 : transitionHover.noteCount === 0) &&
      transitionHover.noteParts.every(item => item.filter === 'none') &&
      transitionHover.transitionStroke === 'rgb(45, 106, 168)'
    );
    // Mirrors renderVectorPdf: the largest scale at or below 1 that keeps both
    // sides within jsPDF's cap, clamped after multiplying so the product cannot
    // land a couple of ulps above it.
    const expectedPdfPage = pdf.svgWidth > 0 && pdf.svgHeight > 0
      ? (() => {
          const cap = 14400;
          const fit = Math.min(1, cap / Math.max(pdf.svgWidth, pdf.svgHeight));
          return {
            width: Math.min(cap, pdf.svgWidth * fit),
            height: Math.min(cap, pdf.svgHeight * fit),
          };
        })()
      : null;
    const pdfChecks = !exportError && (!requestedFormats.has('pdf') || (
      pdf.menu === true && pdf.header === '%PDF-' && pdf.bytes >= 100 &&
      (!requirePdfZeroImages || pdf.images === 0) && pdf.pages === 1 &&
      // The page must be exactly what correct scaling produces, not merely
      // proportional to the drawing. jsPDF caps a page at 14400 units, so a
      // diagram past that is scaled to fit and legitimately stops matching the
      // SVG one-for-one — but a page that is proportional *and* clipped passes
      // a ratio test, which is how a build clipping 69% of the drawing stayed
      // green. Recomputing the expected page pins both dimensions.
      (!requirePdfPageSize || (pdf.pdfWidth > 0 && pdf.pdfHeight > 0 &&
        expectedPdfPage !== null &&
        Math.abs(pdf.pdfWidth - expectedPdfPage.width) < 0.01 &&
        Math.abs(pdf.pdfHeight - expectedPdfPage.height) < 0.01)) &&
      pdf.inflatedStreamBytes > 0 && pdf.pdfStreamsTotal > 0 &&
      pdf.pdfStreamsDecoded === pdf.pdfStreamsTotal && pdf.whiteHaloOperators === 0 &&
      (!requirePdfRerender || pdf.rerenderSame === true)
    ));
    const pngChecks = !requestedFormats.has('png') || (
      pdf.pngHeader === '89504e470d0a1a0a' && pdf.pngBytes >= 100 && pdf.pngWidth >= 1 && pdf.pngHeight >= 1 &&
      pdf.pngDecodedWidth === pdf.pngWidth && pdf.pngDecodedHeight === pdf.pngHeight &&
      pdf.pngNonBlankPixels >= 10 && pdf.pngOpaque === true
    );
    const svgChecks = !requestedFormats.has('svg') || (
      // The three clauses below count absences, so an empty export scores a
      // perfect zero on all of them. Require a payload first.
      pdf.signature.svgBytes > 0 &&
      pdf.svgText === 0 && pdf.svgMarker === 0 && pdf.svgFontFamily === 0
    );
    const modeButtonsFound = states.buttonFound === true && compare.buttonFound === true
      && fcstmOnly.buttonFound === true && backToCompare.buttonFound === true;
    const report = {initial, sourceLayout, sourceLayoutChecks, selectMenu, selectMenuChecks, sourceUnavailableChecks, sourceChecks, fontChecks, revealTarget, transitionChecks, pdfChecks, pngChecks, svgChecks, diagramOnly: states, fcstmOnly, compare, backToCompare, importedSource, selection, revealSource, hover, sourceHover, transitionHover, sourceSelection, sourceCycle, zoom, pdf, collapse, layout, minimumPanelHeight, comparisonTooShort, drawerChecks, modeButtonsFound, exportError, expectedPdfPage, oversizedUiIcons, stateRows, stateRowChecks, externalRequests: network, cspViolations, consoleErrors: consoleErrors.length, consoleDetails};
    console.log(JSON.stringify(report, null, 2));
    // The interaction and panel assertions below describe this file's own
    // fixture: a machine with labelled transitions, composite children and more
    // than one source document. Driving an arbitrary corpus layout through them
    // fails for reasons that have nothing to do with the export -- a leaf-only
    // machine has no transition to hover and no child to collapse. Export-only
    // mode keeps the format, security and console assertions, which are the ones
    // that mean anything for a layout the fixture never covered.
    const exportOnly = process.env.VIEWER_EXPORT_ONLY === '1';
    if ((!exportOnly && (
        !initial.stage || initial.error || !modeButtonsFound ||
        states.diagramOnlySource || !states.diagramOnlyStage ||
        !compare.source || !compare.stage ||
        fcstmOnly.source !== true || fcstmOnly.stage !== false || backToCompare.source !== true || backToCompare.stage !== true ||
        !sourceLayoutChecks || !sourceUnavailableChecks ||
        !(sourceLayout.nativeSelectAlpha >= 0.99) ||
        !sourceChecks || !fontChecks ||
        !transitionChecks || !selectMenuChecks ||
        zoom.before === zoom.after)) ||
        (exportOnly && (!initial.stage || initial.error)) ||
        !pdfChecks || !pngChecks ||
        (process.env.VIEWER_REQUIRE_EXPANDED_SVG === '1' && !svgChecks) ||
        (!exportOnly && (
          (sourceCycle.candidateCount > 1 && sourceCycle.uniqueSelectedIds < sourceCycle.candidateCount) ||
          (collapse.before > 1 && collapse.after >= collapse.before) ||
          verticalOverflow || horizontalOverflow || comparisonTooShort ||
          !drawerChecks || oversizedUiIcons ||
          stateRowChecks.length ||
          (expectDocuments > 0 && importedSource.published.length !== expectDocuments) ||
          (Math.max(importedSource.published.length, expectDocuments) > 1 && (
            !importedSource.pickerFound
            || importedSource.documents.length !== importedSource.published.length
            || !importedSource.childText
            || importedSource.selected < 1
          ))
        )) ||
        network.length || cspViolations.length || consoleErrors.length) process.exitCode = 1;
  } catch (error) {
    // Most probes throw rather than recording an outcome, and a throw leaves
    // the report unbuildable. Emit what the session did observe so a red run
    // is a diagnostic rather than a bare stack trace.
    const events = (cdp && cdp.events) || [];
    console.log(JSON.stringify({
      failed: String((error && error.message) || error),
      externalRequests: events
        .filter(event => event.method === 'Network.requestWillBeSent')
        .map(event => event.params.request.url)
        .filter(url => !url.startsWith('file://') && !url.startsWith('data:') && !url.startsWith('blob:')),
      cspViolations: events
        .filter(event => event.method === 'Log.entryAdded')
        .filter(event => /Content Security Policy/i.test(event.params.entry.text || ''))
        .map(event => (event.params.entry.text || '').slice(0, 160)),
      consoleDetails: events
        .filter(event => event.method === 'Runtime.exceptionThrown' || (event.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(event.params.type)))
        .map(event => event.method === 'Runtime.exceptionThrown'
          ? (event.params.exceptionDetails?.text || event.params.exceptionDetails?.exception?.description || 'exception')
          : event.params.args?.map(arg => arg.value || arg.description || '').join(' ')),
    }, null, 2));
    console.error(error.stack || error);
    process.exitCode = 1;
  } finally {
    stopChrome(chrome);
    // Chrome keeps flushing its profile after SIGTERM, so removing the
    // directory before it exits races with those writes and raises ENOTEMPTY.
    await awaitChromeExit(chrome);
    try {
      fs.rmSync(userData, {recursive: true, force: true, maxRetries: 5, retryDelay: 200});
    } catch (error) {
      // The gate's verdict is about the viewer, not about our own cleanup, so
      // a leftover directory under the OS temp dir is reported rather than
      // turned into a failure. Anything that is not a removal race re-throws.
      if (!['ENOTEMPTY', 'EBUSY', 'EPERM'].includes(error && error.code)) throw error;
      console.error(`warning: left ${userData} behind (${error.code})`);
    }
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
