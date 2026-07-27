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
});
