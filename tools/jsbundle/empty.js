// Stub used by the bundle build to satisfy `fs` / `path` / `node:url`
// imports inside jsfcstm/workspace and jsfcstm/editor — pyfcstm only
// renders single-file inputs, so the workspace import-resolution code
// path is never actually executed.
module.exports = new Proxy({}, {get: () => () => undefined});
