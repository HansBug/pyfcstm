/*
 * jsPDF imports an optional raster image decoder. The standalone viewer never
 * calls that API: PNG export uses the browser canvas and PDF export uses
 * svg2pdf.js. Keep jsPDF initialisation valid without shipping a second
 * raster decoder; an accidental use fails loudly.
 */
export function decode() {
  throw new Error('optional raster decoding is not available in the standalone viewer');
}
