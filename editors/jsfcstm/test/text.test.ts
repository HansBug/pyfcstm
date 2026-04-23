import assert from 'node:assert/strict';

import {createDocument, createToken, packageModule} from './support';

describe('jsfcstm text helpers', () => {
    it('builds and clones ranges', () => {
        const range = packageModule.createRange(1, 2, 3, 4);
        const clone = packageModule.cloneRange(range);

        assert.deepEqual(clone, range);
        assert.notEqual(clone, range);
    });

    it('resolves document file paths from filePath, uri, or empty input', () => {
        const directDocument = createDocument('state Root;', '/tmp/direct.fcstm');
        assert.equal(packageModule.getDocumentFilePath(directDocument), '/tmp/direct.fcstm');

        const uriOnlyDocument = {
            getText() {
                return 'state Root;';
            },
            lineCount: 1,
            lineAt() {
                return {text: 'state Root;'};
            },
            uri: {
                fsPath: '/tmp/from-uri.fcstm',
            },
        };
        assert.equal(packageModule.getDocumentFilePath(uriOnlyDocument), '/tmp/from-uri.fcstm');

        const emptyDocument = {
            getText() {
                return '';
            },
            lineCount: 1,
            lineAt() {
                return {text: ''};
            },
        };
        assert.equal(packageModule.getDocumentFilePath(emptyDocument), '');
    });

    it('handles token and node ranges, including clamping and empty token text', () => {
        const document = createDocument('state Root;', '/tmp/range.fcstm');

        assert.equal(packageModule.tokenText(undefined), '');
        assert.equal(packageModule.tokenText(createToken('Root', 1, 6)), 'Root');
        assert.equal(packageModule.makeTokenRange(undefined, document), undefined);
        assert.equal(packageModule.makeNodeRange({}, document), undefined);

        const tokenRange = packageModule.makeTokenRange(createToken('Root', 1, 6), document);
        assert.deepEqual(tokenRange, packageModule.createRange(0, 6, 0, 10));

        const clampedRange = packageModule.makeTokenRange(createToken('', 99, 99), document);
        assert.deepEqual(clampedRange, packageModule.createRange(0, 11, 0, 12));

        const nodeRange = packageModule.makeNodeRange({
            start: createToken('state', 1, 0),
            stop: createToken('Root', 1, 6),
        }, document);
        assert.deepEqual(nodeRange, packageModule.createRange(0, 0, 0, 10));

        const nodeRangeWithoutStopText = packageModule.makeNodeRange({
            start: createToken('state', 1, 0),
            stop: {
                line: 1,
                column: 10,
            },
        }, document);
        assert.deepEqual(nodeRangeWithoutStopText, packageModule.createRange(0, 0, 0, 11));
    });

    it('finds fallback ranges with start line control', () => {
        const text = [
            'def int counter = 0;',
            'state Root;',
            'event Start;',
        ].join('\n');
        const document = createDocument(text, '/tmp/fallback.fcstm');

        const found = packageModule.fallbackRangeFromText(document, text, 'counter');
        assert.deepEqual(found, packageModule.createRange(0, 8, 0, 15));

        const foundFromLaterLine = packageModule.fallbackRangeFromText(document, text, 'Start', 1);
        assert.deepEqual(foundFromLaterLine, packageModule.createRange(2, 6, 2, 11));

        const fallback = packageModule.fallbackRangeFromText(document, text, 'missing');
        assert.deepEqual(fallback, packageModule.createRange(0, 0, 0, 1));
    });

    it('checks range containment boundaries', () => {
        const range = packageModule.createRange(1, 2, 1, 5);

        assert.equal(packageModule.rangeContains(range, {line: 1, character: 2}), true);
        assert.equal(packageModule.rangeContains(range, {line: 1, character: 5}), true);
        assert.equal(packageModule.rangeContains(range, {line: 1, character: 1}), false);
        assert.equal(packageModule.rangeContains(range, {line: 1, character: 6}), false);
        assert.equal(packageModule.rangeContains(range, {line: 0, character: 3}), false);
        assert.equal(packageModule.rangeContains(range, {line: 2, character: 3}), false);
    });
});
