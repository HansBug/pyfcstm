/*
 * Stand-in for the raster packages jsPDF reaches only through its optional
 * ``html()`` route.
 *
 * The vector PDF path never calls them, but esbuild follows the import and
 * compiles them in: `canvg`, `html2canvas` and `dompurify` together account for
 * most of the writer bundle's weight, and the umbrella contract forbids shipping
 * any raster fallback inside the published asset.
 *
 * Every export throws rather than returning something empty. A stub that quietly
 * returned `undefined` would turn "this route is unavailable" into a confusing
 * failure somewhere further along, and the point of the stub is that reaching it
 * at all is a defect.
 */
function unavailable() {
    throw new Error(
        'the optional raster route is not part of the embedded PDF writer; '
            + 'vector output uses the expanded SVG path',
    );
}

export default unavailable;
export const Canvg = unavailable;
export const presets = undefined;
export const sanitize = unavailable;
export const decode = unavailable;
export const encode = unavailable;
