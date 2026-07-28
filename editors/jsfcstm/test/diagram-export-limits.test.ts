import assert from 'node:assert/strict';

import {
    PDF_MAX_UNITS,
    RASTER_MAX_AREA,
    RASTER_MAX_SIDE,
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
        // 600x33154 and its neighbours below are three of the 3775 heights
        // between 32768 and 60000 that did.
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
