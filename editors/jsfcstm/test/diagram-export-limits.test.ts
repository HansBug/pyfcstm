import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {DOMParser as XmlDomParser} from '@xmldom/xmldom';

import {
    DiagramExportLimitError,
    EXPORT_MAX_EDGE_PX,
    EXPORT_MAX_PIXELS,
    EXPORT_MAX_SCALE,
    PDF_MAX_UNITS,
    RASTER_MAX_AREA,
    RASTER_MAX_SIDE,
    assertExportLimitsAreStricterThanHostLimits,
    assertWithinExportLimits,
    expandSvgForExport,
    rasterScaleWithinLimits,
} from '../src/diagram/export';

describe('diagram export size limits', () => {
    it('leaves ordinary diagrams at the requested scale', () => {
        // A typical diagram is nowhere near any limit, so the clamp must not
        // quietly reduce its raster quality.
        assert.equal(rasterScaleWithinLimits(440, 642, 2), 2);
        assert.equal(rasterScaleWithinLimits(1, 1, 2), 2);
    });

    it('keeps a tall diagram inside the browser side limit', () => {
        // Chrome's canvas stops at 65535 per side and `toBlob` then returns
        // null with no error, which used to leave a tall diagram with no PNG.
        const height = 34874;
        const scale = rasterScaleWithinLimits(296, height, 2);
        assert.ok(scale < 2, 'a diagram past the limit has to be scaled down');
        assert.ok(Math.ceil(height * scale) <= RASTER_MAX_SIDE);
        assert.ok(Math.ceil(296 * scale) <= RASTER_MAX_SIDE);
    });

    it('keeps a wide diagram inside the same limit', () => {
        const width = 40000;
        const scale = rasterScaleWithinLimits(width, 662, 2);
        assert.ok(Math.ceil(width * scale) <= RASTER_MAX_SIDE);
    });

    it('keeps a large square diagram inside the area limit', () => {
        // Both sides can be legal while their product is not.
        const side = 20000;
        const scale = rasterScaleWithinLimits(side, side, 2);
        const pixels = Math.ceil(side * scale) * Math.ceil(side * scale);
        assert.ok(pixels <= RASTER_MAX_AREA + Math.ceil(side * scale) * 2);
        assert.ok(Math.ceil(side * scale) <= RASTER_MAX_SIDE);
    });

    it('never scales up past what was asked for', () => {
        assert.equal(rasterScaleWithinLimits(10, 10, 1), 1);
        assert.ok(rasterScaleWithinLimits(10, 10, 0.5) <= 0.5);
    });

    it('states the page limit jsPDF enforces', () => {
        // The constant exists so the scaling maths and the gate agree on the
        // number jsPDF clamps to silently.
        assert.equal(PDF_MAX_UNITS, 14400);
    });

    it('pins the raster limits to the lowest a browser enforces', () => {
        // Every bound above compares against these constants, so widening one
        // to Chrome's own 65535 would re-green the suite while reintroducing the
        // Firefox and Safari failures they exist to prevent. Measured in Chrome:
        // 592x65535 rasterises, 592x65536 does not; 16384x16384 does,
        // 16384x16385 does not. Firefox stops at 32767, Safari at 16384.
        assert.equal(RASTER_MAX_SIDE, 32767);
        assert.equal(RASTER_MAX_AREA, 268435456);
    });

    it('returns the largest acceptable scale, not merely an acceptable one', () => {
        // Without this, an implementation that returns a fraction of the legal
        // scale passes every bound above while destroying raster quality.
        // The first three sit exactly on 32767 after rounding. They passed
        // while the side bound was computed against the exact size rather than
        // the rounded one, which overflowed for one tall diagram in seven --
        // 600x33154 and its neighbours below are three of the 6311 heights
        // that did, which start at 16577 rather than at the limit itself.
        const cases: Array<[number, number]> = [
            [296, 34874],
            [40000, 662],
            [20000, 20000],
            [600, 33154],
            [296, 33154],
            [1000, 33296],
        ];
        for (const [width, height] of cases) {
            const scale = rasterScaleWithinLimits(width, height, 2);
            const grow = scale * 1.02;
            const legal = (factor: number) => {
                const w = Math.ceil(width * factor);
                const h = Math.ceil(height * factor);
                return w <= RASTER_MAX_SIDE && h <= RASTER_MAX_SIDE
                    && w * h <= RASTER_MAX_AREA;
            };
            assert.ok(legal(scale), `${width}x${height}: own result must be legal`);
            assert.ok(
                !legal(grow),
                `${width}x${height}: 2% more must not also fit, or the scale is too small`,
            );
        }
    });

    it('keeps the rounded canvas inside the area cap', () => {
        // The call site rounds each side up, so a scale that fits before
        // rounding can exceed the cap after it. Browsers enforce the area
        // exactly and `toBlob` then yields null with no error.
        for (const side of [16385, 17000, 20000, 21185, 30000, 40000]) {
            const scale = rasterScaleWithinLimits(side, side, 2);
            const pixels = Math.ceil(side * scale) * Math.ceil(side * scale);
            assert.ok(
                pixels <= RASTER_MAX_AREA,
                `${side}x${side}: rounded canvas is ${pixels} px, cap is ${RASTER_MAX_AREA}`,
            );
        }
    });

    it('rejects degenerate bounds instead of returning NaN', () => {
        for (const [w, h] of [[0, 0], [-10, 500], [500, -10], [0, 34874]]) {
            const scale = rasterScaleWithinLimits(w, h, 2);
            assert.ok(Number.isFinite(scale) && scale > 0, `${w}x${h} -> ${scale}`);
        }
    });

    it('keeps the rounded canvas inside the side cap across the whole range', () => {
        // Three hand-picked sizes cannot show that a bound holds. Sweeping the
        // tall, wide and square axes does, and it is what caught the side
        // overflow the area budget had already been fixed for.
        const offenders: Array<string> = [];
        const check = (w: number, h: number, requested: number) => {
            const scale = rasterScaleWithinLimits(w, h, requested);
            const W = Math.ceil(w * scale);
            const H = Math.ceil(h * scale);
            if (W > RASTER_MAX_SIDE || H > RASTER_MAX_SIDE || W * H > RASTER_MAX_AREA) {
                if (offenders.length < 5) offenders.push(`${w}x${h} -> ${W}x${H}`);
            }
        };
        for (let h = 1; h <= 60000; h += 1) check(600, h, 2);
        for (let w = 1; w <= 60000; w += 1) check(w, 662, 2);
        for (let side = 1; side <= 40000; side += 1) check(side, side, 2);
        assert.deepEqual(offenders, [], 'rounded canvas must stay inside both caps');
    });
});

describe('diagram export product limits', () => {
    it('leaves an ordinary diagram alone', () => {
        assert.deepEqual(assertWithinExportLimits(440, 642, 2), {
            width: 880,
            height: 1284,
        });
    });

    it('accepts the documented scale ceiling and refuses anything above it', () => {
        assert.doesNotThrow(() => assertWithinExportLimits(100, 100, EXPORT_MAX_SCALE));
        assert.throws(
            () => assertWithinExportLimits(100, 100, EXPORT_MAX_SCALE + 0.0001),
            RangeError,
        );
    });

    it('refuses an oversized edge rather than quietly scaling it down', () => {
        // This is the behaviour that used to differ between the two export paths:
        // the browser clamped and said nothing, while Python refused. A caller who
        // picked a scale is told when it was not honoured.
        try {
            assertWithinExportLimits(5000, 100, 4);
            assert.fail('an export past the edge limit has to be refused');
        } catch (error) {
            assert.equal((error as DiagramExportLimitError).limitName, 'edge');
            const message = (error as Error).message;
            assert.ok(message.includes(String(EXPORT_MAX_EDGE_PX)));
            // The original size, the scaled size and the remedy.
            assert.ok(message.includes('5000x100'));
            assert.ok(message.includes('lower scale'));
        }
    });

    it('refuses a shape no single edge would catch', () => {
        // 4096 x 4096 is exactly the pixel limit and neither edge is near its own,
        // so an edge-only check would wave one pixel more straight through.
        assert.doesNotThrow(() => assertWithinExportLimits(4096, 4096, 1));
        try {
            assertWithinExportLimits(4097, 4096, 1);
            assert.fail('an export past the pixel limit has to be refused');
        } catch (error) {
            assert.equal((error as DiagramExportLimitError).limitName, 'pixels');
        }
    });

    it('keeps every product limit stricter than the host limit it shadows', () => {
        // The refusal must always fire before the clamp, or the two paths start
        // disagreeing again -- silently, because a clamped export still succeeds.
        assert.doesNotThrow(assertExportLimitsAreStricterThanHostLimits);
        assert.ok(EXPORT_MAX_EDGE_PX < RASTER_MAX_SIDE);
        assert.ok(EXPORT_MAX_PIXELS < RASTER_MAX_AREA);
    });
});

describe('diagram export product limits are actually called', () => {
    it('is reachable from the viewer export path', () => {
        // The refusal existed for one commit with no call site at all: the
        // function, its tests and its documentation were in place while the
        // browser still clamped silently. A test that only calls the function
        // proves nothing about that, so this one reads the export component.
        // Resolved from the package root rather than the module URL, because the
        // suite is compiled to CommonJS and `import.meta` is unavailable there.
        const stage = readFileSync(
            join(
                process.cwd(),
                '..',
                'vscode',
                'src',
                'preview-webview',
                'components',
                'Stage.vue',
            ),
            'utf8',
        );
        assert.ok(
            /assertWithinExportLimits\(/.test(stage),
            'the viewer export path must call the refusal, not only import it',
        );
        // Both formats, because wiring one and forgetting the other is the same
        // defect one step smaller.
        const calls = stage.match(/assertWithinExportLimits\(/g) || [];
        assert.ok(
            calls.length >= 2,
            `expected the PNG and PDF paths to check limits, found ${calls.length} call(s)`,
        );
        assert.ok(
            /EXPORT_PNG_SCALE/.test(stage),
            'the download scale must come from the shared constant',
        );
    });
});

describe('unexpanded exports are not presented as self-contained', () => {
    it('returns the canonical form unchanged when no expander is given', async () => {
        // The contract the docstring states: an absent expander is not an error,
        // so the caller gets the canonical document back and has to say so.
        //
        // The helper parses what it is given, and Node has no `DOMParser`. The
        // build dependency that supplies one to the embedded PDF host supplies it
        // here too, rather than the assertion being skipped for want of a DOM.
        const host = globalThis as unknown as {DOMParser?: unknown};
        const installed = host.DOMParser === undefined;
        if (installed) host.DOMParser = XmlDomParser;
        try {
            const canonical =
                '<svg xmlns="http://www.w3.org/2000/svg"><text>a</text></svg>';
            assert.equal(await expandSvgForExport(canonical), canonical);
        } finally {
            if (installed) delete host.DOMParser;
        }
    });

    it('is reported by the export path rather than passed off silently', () => {
        // With no expander the helper does not throw, which left the export handler
        // shipping a font-dependent document under a variable named `expanded`.
        // The host has to be told, because the file itself looks fine.
        const stage = readFileSync(
            join(
                process.cwd(),
                '..',
                'vscode',
                'src',
                'preview-webview',
                'components',
                'Stage.vue',
            ),
            'utf8',
        );
        assert.ok(
            /if \(!expander\) \{/.test(stage),
            'the export handler must detect an absent expander',
        );
        assert.ok(
            /not self-contained/.test(stage),
            'and must say why the document cannot be treated as an export',
        );
    });
});
