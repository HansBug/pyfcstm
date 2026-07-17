import { buildFcstmElkGraph } from "../../editors/jsfcstm/src/diagram/elk-graph";
import type {
  FcstmDiagram,
  FcstmDiagramPreviewOptionsInput,
} from "../../editors/jsfcstm/src/diagram/model";
import { resolveFcstmDiagramPreviewOptions } from "../../editors/jsfcstm/src/diagram/options";
import { smoothGraphEdges } from "../../editors/jsfcstm/src/diagram/render/edge-smoother";
import type {
  PaletteId,
  PaletteMode,
} from "../../editors/jsfcstm/src/diagram/render/palette";
import { renderSvg } from "../../editors/jsfcstm/src/diagram/render/svg";

interface RenderRequest {
  diagram: FcstmDiagram;
  options?: FcstmDiagramPreviewOptionsInput;
  palette?: PaletteId;
  mode?: PaletteMode;
}

interface RenderJob {
  status: "pending" | "done" | "error";
  svg?: string;
  error?: string;
}

interface RendererGlobal {
  global?: RendererGlobal;
  __pyfcstm_embedded_host?: boolean;
  setTimeout?: (
    callback: (...args: unknown[]) => void,
    delay?: number,
    ...args: unknown[]
  ) => number;
  clearTimeout?: (timerId: number) => void;
  __pyfcstm_render_start?: (requestJson: string, requestId: string) => string;
  __pyfcstm_render_poll?: (requestId: string) => string;
  __pyfcstm_render_drop?: (requestId: string) => boolean;
}

const rendererGlobal = globalThis as unknown as RendererGlobal;

// MiniRacer has no browser event loop. The embedded marker is deliberately
// explicit so a browser keeps its native timer and Promise scheduling.
if (rendererGlobal.__pyfcstm_embedded_host || !rendererGlobal.setTimeout) {
  let nextTimerId = 0;
  const cancelledTimers: Record<number, boolean> = Object.create(null);
  rendererGlobal.setTimeout = (callback, _delay, ...args) => {
    nextTimerId += 1;
    const timerId = nextTimerId;
    Promise.resolve().then(() => {
      if (!cancelledTimers[timerId]) {
        callback(...args);
      }
      delete cancelledTimers[timerId];
    });
    return timerId;
  };
  rendererGlobal.clearTimeout = (timerId) => {
    cancelledTimers[timerId] = true;
  };
}

const hadGlobal = Object.prototype.hasOwnProperty.call(
  rendererGlobal,
  "global",
);
const previousGlobal = rendererGlobal.global;
rendererGlobal.global = rendererGlobal;
const ELK =
  require("../../editors/jsfcstm/node_modules/elkjs/lib/elk-api.js").default;
const {
  Worker,
} = require("../../editors/jsfcstm/node_modules/elkjs/lib/elk-worker.min.js");
if (hadGlobal) {
  rendererGlobal.global = previousGlobal;
} else {
  delete rendererGlobal.global;
}
const elk = new ELK({ workerFactory: (url: string) => new Worker(url) });
const jobs: Record<string, RenderJob> = Object.create(null);

function errorText(error: unknown): string {
  if (error instanceof Error) {
    return error.stack || error.message;
  }
  return String(error);
}

function render(requestJson: string): Promise<string> {
  const request = JSON.parse(requestJson) as RenderRequest;
  const options = resolveFcstmDiagramPreviewOptions(request.options);
  const graph = buildFcstmElkGraph(request.diagram, options);
  return elk.layout(JSON.parse(JSON.stringify(graph))).then((laidOut) => {
    smoothGraphEdges(laidOut);
    return renderSvg(laidOut, options, {
      palette: request.palette || "default",
      mode: request.mode || "light",
    }).svg;
  });
}

rendererGlobal.__pyfcstm_render_start = (requestJson, requestId) => {
  if (jobs[requestId]) {
    throw new Error(`Render request already exists: ${requestId}`);
  }
  jobs[requestId] = { status: "pending" };
  render(requestJson).then(
    (svg) => {
      jobs[requestId] = { status: "done", svg };
    },
    (error) => {
      jobs[requestId] = { status: "error", error: errorText(error) };
    },
  );
  return requestId;
};

rendererGlobal.__pyfcstm_render_poll = (requestId) =>
  JSON.stringify(
    jobs[requestId] || {
      status: "error",
      error: `Unknown render request: ${requestId}`,
    },
  );

rendererGlobal.__pyfcstm_render_drop = (requestId) => {
  delete jobs[requestId];
  return true;
};
