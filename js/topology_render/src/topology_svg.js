// Topology verification result renderer.
//
// Consumes a JSON payload built by pyfcstm.topology.render._build_payload
// and produces an SVG string. The renderer is overlay-aware: the same
// macro graph can be rendered with reachability / finiteness /
// inevitability decorations, all driven by the ``overlay`` dict in the
// payload.
//
// Layout is delegated to elkjs (compound-graph layered routing). The
// SVG renderer is pure: it walks the ELK output and emits geometry +
// style straight to a string. Each SVG element carries data-* attributes
// so downstream tools can identify nodes / edges / overlay decorations.

import ELK from "elkjs/lib/elk.bundled.js";

export const RENDERER_VERSION = "0.1.0";

// Visual tokens. The base colour palette mirrors editors/jsfcstm so the
// topology viz reads as a sibling to the VSCode preview rather than an
// alien second pipeline.
const STYLE = {
  // canvas
  canvasPadding: 32,
  bannerHeight: 56,
  bannerFontSize: 14,
  // base state colours (from jsfcstm svg-renderer STYLE)
  leafFill: "#ffffff",
  leafStroke: "#5a92c4",
  leafStrokeWidth: 1.4,
  leafRadius: 10,
  pseudoFill: "#fdf3e1",
  pseudoStroke: "#b07a36",
  pseudoStrokeWidth: 1.4,
  pseudoDash: "6 3",
  endFill: "#2d6aa8",
  endRingFill: "#ffffff",
  endRingStroke: "#2d6aa8",
  // edges
  edgeStroke: "#3470a8",
  edgeStrokeWidth: 1.4,
  edgeLabelColor: "#1e476e",
  edgeLabelHalo: "#ffffff",
  // typography
  titleColor: "#183b61",
  fontFamily:
    '"Noto Sans CJK SC","Noto Sans CJK","Source Han Sans","PingFang SC","Microsoft YaHei","Droid Sans Fallback","DejaVu Sans","JetBrains Mono","Fira Code",Consolas,sans-serif',
  fontSize: 13,
  smallFontSize: 11,
  // overlay decorations
  reachOk: {
    nodeFill: "#e5f5e0",
    nodeStroke: "#2d8e58",
    nodeStrokeWidth: 2.0,
    pathStroke: "#1d7c45",
    pathStrokeWidth: 3.4,
    targetRingFill: "none",
    targetRingStroke: "#1d7c45",
    targetRingExtra: 6,
    sourceMarker: "#1d7c45",
  },
  reachUnreach: {
    nodeFill: "#f1f3f5",
    nodeStroke: "#8a9097",
    nodeStrokeWidth: 1.2,
    nodeDash: "4 3",
    textOpacity: 0.55,
  },
  trapCycle: {
    nodeFill: "#fce4e4",
    nodeStroke: "#b62a2a",
    nodeStrokeWidth: 2.4,
    cycleStroke: "#b62a2a",
    cycleStrokeWidth: 3.4,
  },
  trapRegion: {
    nodeFill: "#fdebeb",
    nodeStroke: "#c97a7a",
    nodeStrokeWidth: 1.6,
  },
  deadlock: {
    nodeFill: "#fff1f1",
    nodeStroke: "#b62a2a",
    nodeStrokeWidth: 2.4,
    crossStroke: "#b62a2a",
    pathStroke: "#d97757",
    pathStrokeWidth: 3.2,
    pathDash: "8 4",
  },
  inevAvoid: {
    nodeFill: "#fbe6dc",
    nodeStroke: "#cc5a2a",
    nodeStrokeWidth: 2.0,
    pathStroke: "#cc5a2a",
    pathStrokeWidth: 3.2,
    pathDash: "8 4",
    targetRingStroke: "#cc5a2a",
    targetRingDash: "5 3",
    targetRingExtra: 6,
  },
  bannerOk: { fill: "#1d7c45", textFill: "#ffffff" },
  bannerWarn: { fill: "#9a6a1f", textFill: "#ffffff" },
  bannerErr: { fill: "#b62a2a", textFill: "#ffffff" },
};

// ELK layout options. Mirror the values used by jsfcstm with light
// changes for the more compact topology view (smaller spacing because we
// only have a single layer of leaves, not nested composites in v0).
const ELK_LAYOUT_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "DOWN",
  "elk.hierarchyHandling": "INCLUDE_CHILDREN",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.spacing.nodeNode": "60",
  "elk.layered.spacing.nodeNodeBetweenLayers": "82",
  "elk.spacing.edgeNode": "32",
  "elk.spacing.edgeEdge": "28",
  "elk.spacing.edgeLabel": "16",
  "elk.spacing.componentComponent": "48",
  "elk.spacing.nodeSelfLoop": "28",
  "elk.layered.spacing.baseValue": "40",
  "elk.edgeLabels.placement": "CENTER",
  "elk.layered.nodePlacement.favorStraightEdges": "true",
  "elk.layered.unnecessaryBendpoints": "true",
  "elk.padding": "[top=20,left=20,bottom=20,right=20]",
};

const CHAR_WIDTH = 7.8;
const LINE_HEIGHT = 16;
const NODE_MIN_WIDTH = 110;
const NODE_MIN_HEIGHT = 48;
const NODE_LABEL_PAD_X = 18;
const NODE_LABEL_PAD_Y = 12;

function measureNodeLabel(label) {
  const lines = String(label || "").split("\n");
  const longest = Math.max(1, ...lines.map((l) => l.length));
  const width = Math.ceil(longest * CHAR_WIDTH + NODE_LABEL_PAD_X * 2);
  const height = Math.ceil(lines.length * LINE_HEIGHT + NODE_LABEL_PAD_Y * 2);
  return {
    width: Math.max(NODE_MIN_WIDTH, width),
    height: Math.max(NODE_MIN_HEIGHT, height),
  };
}

function measureEdgeLabel(label) {
  if (!label) return { width: 0, height: 0 };
  const lines = String(label).split("\n");
  const longest = Math.max(1, ...lines.map((l) => l.length));
  return {
    width: Math.ceil(longest * 6.5 + 12),
    height: Math.ceil(lines.length * 14 + 6),
  };
}

function escapeXml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function quote(attr, value) {
  return `${attr}="${escapeXml(value)}"`;
}

const COMPOSITE_TITLE_HEIGHT = 26;
const COMPOSITE_PADDING_TOP = 38;
const COMPOSITE_PADDING_SIDE = 18;
const COMPOSITE_PADDING_BOTTOM = 18;

function buildElkInput(payload) {
  // Compound graph: leaves and composites are nested under their
  // parents. Composites with no leaf descendants are skipped on the
  // Python side, so every composite that arrives here has children.
  const nodes = payload.nodes || [];
  const edges = payload.edges || [];

  // First pass: build ELK nodes by id, keep parent_id reference.
  const elkNodes = new Map();
  for (const n of nodes) {
    if (n.kind === "composite") {
      const titleDims = measureNodeLabel(n.label || n.id);
      elkNodes.set(n.id, {
        id: n.id,
        labels: [{ text: n.label || n.id, width: titleDims.width, height: COMPOSITE_TITLE_HEIGHT }],
        meta: n,
        layoutOptions: {
          "elk.padding": `[top=${COMPOSITE_PADDING_TOP},left=${COMPOSITE_PADDING_SIDE},bottom=${COMPOSITE_PADDING_BOTTOM},right=${COMPOSITE_PADDING_SIDE}]`,
        },
        children: [],
        edges: [],
      });
    } else {
      const labelDims = measureNodeLabel(n.label || n.id);
      const isEnd = n.kind === "end";
      elkNodes.set(n.id, {
        id: n.id,
        width: isEnd ? 50 : labelDims.width,
        height: isEnd ? 50 : labelDims.height,
        labels: [{ text: n.label || n.id, width: labelDims.width, height: labelDims.height }],
        meta: n,
      });
    }
  }

  // Second pass: attach to parents.
  const rootChildren = [];
  for (const n of nodes) {
    const elkNode = elkNodes.get(n.id);
    if (!elkNode) continue;
    if (n.parent_id && elkNodes.has(n.parent_id)) {
      const parent = elkNodes.get(n.parent_id);
      parent.children = parent.children || [];
      parent.children.push(elkNode);
    } else {
      rootChildren.push(elkNode);
    }
  }

  // Place each edge at its lowest common ancestor composite. The
  // Python side computes ``container_id`` for every edge; null means
  // canvas-level. Edges placed at their LCA route cleanly through
  // composite boundaries; canvas-level edges that cross between
  // composites are routed via the canvas exterior.
  const rootEdges = [];
  for (const e of edges) {
    const elkEdge = {
      id: e.id,
      sources: [e.source],
      targets: [e.target],
      meta: e,
    };
    if (e.label) {
      const dims = measureEdgeLabel(e.label);
      elkEdge.labels = [{ text: e.label, width: dims.width, height: dims.height }];
    }
    if (e.container_id && elkNodes.has(e.container_id)) {
      const container = elkNodes.get(e.container_id);
      container.edges = container.edges || [];
      container.edges.push(elkEdge);
    } else {
      rootEdges.push(elkEdge);
    }
  }

  return {
    id: "__canvas__",
    layoutOptions: { ...ELK_LAYOUT_OPTIONS, "elk.direction": payload.direction || "DOWN" },
    children: rootChildren,
    edges: rootEdges,
  };
}

function classifyNode(node, overlay) {
  const meta = node.meta;
  const id = node.id;
  const kind = (overlay && overlay.kind) || "";
  const verdict = (overlay && overlay.verdict) || "";

  // END sentinel renders as a small bull's-eye regardless of overlay.
  if (meta && meta.kind === "end") {
    return { variant: "end" };
  }
  if (meta && meta.kind === "pseudo") {
    return { variant: "pseudo" };
  }

  if (kind === "reach") {
    // Source / target markers are drawn separately in renderNode so
    // their fill follows the reach-vs-unreach palette here.
    const reachSet = new Set(overlay.reach_set || []);
    if (reachSet.has(id)) return { variant: "reach", overlay: "reachOk" };
    return { variant: "unreach", overlay: "reachUnreach" };
  }

  if (kind === "finite") {
    const reachSet = new Set(overlay.reach_set || []);
    if (verdict === "ok") {
      // Reachable-from-source nodes go green; everything else grays
      // out so the user can immediately see "what would this run
      // actually touch from this starting point".
      if (reachSet.has(id)) return { variant: "reach", overlay: "reachOk" };
      return { variant: "unreach", overlay: "reachUnreach" };
    }
    // verdict === "fail": cycle / deadlock / trap_region get progressively
    // darker reds; prefix path uses orange; reachable-but-outside-trap
    // nodes stay neutral so the trap stands out.
    const cycleSet = new Set(overlay.cycle || []);
    if (cycleSet.has(id)) return { variant: "cycle", overlay: "trapCycle" };
    if (id === overlay.deadlock_leaf) return { variant: "deadlock", overlay: "deadlock" };
    const prefixSet = new Set(overlay.prefix || []);
    if (prefixSet.has(id)) return { variant: "prefix", overlay: "deadlock" };
    const trapSet = new Set(overlay.trap_region || []);
    if (trapSet.has(id)) return { variant: "trap_region", overlay: "trapRegion" };
    return { variant: "neutral" };
  }

  if (kind === "inev") {
    if (verdict === "ok") {
      // OK: highlight reach(source). Source/target markers drawn
      // separately in renderNode.
      const reachSet = new Set(overlay.reach_set || []);
      if (reachSet.has(id)) return { variant: "reach", overlay: "reachOk" };
      return { variant: "neutral" };
    }
    // verdict === "fail"
    const cexKind = overlay.cex_kind || "";
    if (cexKind === "cycle") {
      const cycleSet = new Set(overlay.cycle || []);
      if (cycleSet.has(id)) return { variant: "cycle", overlay: "trapCycle" };
    }
    if (cexKind === "deadlock" && id === overlay.deadlock_leaf) {
      return { variant: "deadlock", overlay: "deadlock" };
    }
    const cexPathSet = new Set(overlay.cex_path || []);
    if (cexPathSet.has(id)) return { variant: "cex_path", overlay: "inevAvoid" };
    return { variant: "neutral" };
  }

  return { variant: "neutral" };
}

function classifyEdge(edge, overlay) {
  const kind = (overlay && overlay.kind) || "";
  const verdict = (overlay && overlay.verdict) || "";

  function isOnPath(pathArr) {
    if (!Array.isArray(pathArr) || pathArr.length < 2) return false;
    for (let i = 0; i < pathArr.length - 1; i++) {
      if (pathArr[i] === edge.meta.source && pathArr[i + 1] === edge.meta.target) return true;
    }
    return false;
  }
  function isOnCycle(cycleArr) {
    if (!Array.isArray(cycleArr) || cycleArr.length < 2) return false;
    for (let i = 0; i < cycleArr.length - 1; i++) {
      if (cycleArr[i] === edge.meta.source && cycleArr[i + 1] === edge.meta.target) return true;
    }
    return false;
  }

  if (kind === "reach" && verdict === "ok" && isOnPath(overlay.witness_path)) {
    return { variant: "witness", overlay: "reachOk" };
  }
  if (kind === "finite" && verdict === "fail") {
    if (isOnCycle(overlay.cycle)) return { variant: "cycle", overlay: "trapCycle" };
    if (isOnPath(overlay.prefix_path)) return { variant: "prefix", overlay: "deadlock" };
  }
  if (kind === "inev") {
    if (verdict === "ok" && isOnPath(overlay.witness_path)) {
      return { variant: "witness", overlay: "reachOk" };
    }
    if (verdict === "fail") {
      if (overlay.cex_kind === "cycle" && isOnCycle(overlay.cycle)) {
        return { variant: "cycle", overlay: "trapCycle" };
      }
      if (isOnPath(overlay.cex_path)) return { variant: "cex_path", overlay: "inevAvoid" };
    }
  }
  return { variant: "normal" };
}

function renderDefs(out) {
  out.push(
    `<defs>` +
      `<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.edgeStroke}"/></marker>` +
      `<marker id="arrow-witness" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.reachOk.pathStroke}"/></marker>` +
      `<marker id="arrow-cycle" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.trapCycle.cycleStroke}"/></marker>` +
      `<marker id="arrow-avoid" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.inevAvoid.pathStroke}"/></marker>` +
      `<marker id="arrow-deadlock" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.deadlock.pathStroke}"/></marker>` +
      `</defs>`
  );
}

function bannerStyleForOverlay(overlay) {
  if (!overlay) return STYLE.bannerOk;
  if (overlay.verdict === "ok") return STYLE.bannerOk;
  if (overlay.kind === "reach") return STYLE.bannerErr;
  if (overlay.kind === "inev") return STYLE.bannerWarn;
  return STYLE.bannerErr;
}

function renderBanner(payload, width, out) {
  const overlay = payload.overlay || null;
  const styleBlock = bannerStyleForOverlay(overlay);
  const text = (overlay && overlay.banner) || payload.title || "";
  if (!text) return 0;
  const y = STYLE.canvasPadding / 2;
  const h = STYLE.bannerHeight;
  const x = STYLE.canvasPadding / 2;
  const w = width - STYLE.canvasPadding;
  out.push(
    `<g ${quote("data-fcstm-topology", "banner")}>` +
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="${styleBlock.fill}"/>` +
      `<text x="${x + 18}" y="${y + h / 2 + 5}" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.bannerFontSize}" fill="${styleBlock.textFill}">${escapeXml(text)}</text>` +
      `</g>`
  );
  return STYLE.bannerHeight + STYLE.canvasPadding;
}

function renderComposite(node, dx, dy, payload, overlay, out) {
  // Composite states are drawn as tinted boxes with a title strip.
  // Children are recursively rendered with this composite as the new
  // coordinate origin.
  const x = (node.x || 0) + dx;
  const y = (node.y || 0) + dy;
  const w = node.width || 0;
  const h = node.height || 0;
  const meta = node.meta || {};
  const label = (node.labels && node.labels[0] && node.labels[0].text) || meta.label || node.id;

  // Composite styling (mirrors jsfcstm's STYLE.composite* tokens but
  // tuned lighter so the overlay colors on child leaves remain
  // dominant).
  const fill = "#edf4fb";
  const titleFill = "#dce9f5";
  const stroke = "#2d6aa8";
  const strokeWidth = 1.6;
  const radius = 14;
  const titleH = 26;

  out.push(
    `<g ${quote("data-fcstm-topology-composite", node.id)}>` +
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>` +
      `<path d="M ${x} ${y + titleH} L ${x + w} ${y + titleH}" stroke="${stroke}" stroke-width="${strokeWidth}" fill="none"/>` +
      `<rect x="${x}" y="${y}" width="${w}" height="${titleH}" rx="${radius}" fill="${titleFill}" stroke="none" clip-path="inset(0 0 ${Math.max(0, h - titleH - radius)}px 0)"/>` +
      `<text x="${x + 14}" y="${y + 18}" text-anchor="start" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.fontSize}" font-weight="600" fill="${STYLE.titleColor}">${escapeXml(label)}</text>` +
      `</g>`
  );

  // Recurse into children — their coords are local to this composite.
  for (const child of node.children || []) {
    if (child.meta && child.meta.kind === "composite") {
      renderComposite(child, x, y, payload, overlay, out);
    } else {
      renderNode(child, x, y, payload, overlay, out);
    }
  }
}


function renderNode(node, dx, dy, payload, overlay, out) {
  const x = (node.x || 0) + dx;
  const y = (node.y || 0) + dy;
  const w = node.width || 0;
  const h = node.height || 0;
  const cls = classifyNode(node, overlay);
  const meta = node.meta || {};

  // END sentinel = bull's-eye.
  if (cls.variant === "end") {
    const r = Math.min(w, h) / 2;
    const cx = x + w / 2;
    const cy = y + h / 2;
    out.push(
      `<g ${quote("data-fcstm-topology-node", node.id)} ${quote("data-kind", "end")}>` +
        `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${STYLE.endRingFill}" stroke="${STYLE.endRingStroke}" stroke-width="1.6"/>` +
        `<circle cx="${cx}" cy="${cy}" r="${Math.max(0, r - 6)}" fill="${STYLE.endFill}"/>` +
        `</g>`
    );
    return;
  }

  // Base fill/stroke
  let fill = STYLE.leafFill;
  let stroke = STYLE.leafStroke;
  let strokeWidth = STYLE.leafStrokeWidth;
  let dasharray = "";
  let textOpacity = 1;
  if (cls.variant === "pseudo") {
    fill = STYLE.pseudoFill;
    stroke = STYLE.pseudoStroke;
    strokeWidth = STYLE.pseudoStrokeWidth;
    dasharray = STYLE.pseudoDash;
  }
  // Overlay coloring
  if (cls.overlay) {
    const ov = STYLE[cls.overlay];
    if (ov.nodeFill) fill = ov.nodeFill;
    if (ov.nodeStroke) stroke = ov.nodeStroke;
    if (ov.nodeStrokeWidth) strokeWidth = ov.nodeStrokeWidth;
    if (ov.nodeDash) dasharray = ov.nodeDash;
    if (ov.textOpacity !== undefined) textOpacity = ov.textOpacity;
  }

  const radius = STYLE.leafRadius;
  out.push(
    `<g ${quote("data-fcstm-topology-node", node.id)} ${quote("data-variant", cls.variant)}>` +
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"` +
      (dasharray ? ` stroke-dasharray="${dasharray}"` : "") +
      `/>`
  );

  // Title
  const label = (node.labels && node.labels[0] && node.labels[0].text) || node.id;
  const titleY = y + h / 2 + 5;
  out.push(
    `<text x="${x + w / 2}" y="${titleY}" text-anchor="middle" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.fontSize}" fill="${STYLE.titleColor}" opacity="${textOpacity}">${escapeXml(label)}</text>`
  );

  // Source ▶ marker: drawn whenever this node is the verification
  // source, regardless of which trap / reach / cex region also
  // colors it. The marker color follows the verdict so it reads as
  // "start" rather than "warning" inside a red trap region.
  if (overlay && node.id === overlay.source) {
    const mx = x - 16;
    const my = y + h / 2;
    let markerColor = STYLE.reachOk.sourceMarker;
    if (overlay.verdict === "fail") {
      if (overlay.kind === "reach") markerColor = "#b62a2a";
      else if (overlay.kind === "finite") markerColor = STYLE.trapCycle.cycleStroke;
      else if (overlay.kind === "inev") markerColor = STYLE.inevAvoid.pathStroke;
    }
    out.push(
      `<polygon points="${mx},${my - 9} ${mx + 13},${my} ${mx},${my + 9}" fill="${markerColor}" ${quote("data-fcstm-topology", "source-marker")}/>`
    );
    out.push(
      `<text x="${mx - 4}" y="${my + 4}" text-anchor="end" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.smallFontSize}" font-weight="600" fill="${markerColor}">src</text>`
    );
  }
  // Target ring: drawn whenever this node is the verification target
  // (only relevant for reach / inev kinds — finite has no target).
  if (overlay && node.id === overlay.target && overlay.kind !== "finite") {
    let ringStroke;
    let ringDash = "";
    let ringExtra = STYLE.reachOk.targetRingExtra;
    if (overlay.verdict === "ok") {
      ringStroke = STYLE.reachOk.targetRingStroke;
    } else if (overlay.kind === "reach") {
      ringStroke = "#b62a2a";
      ringDash = "4 3";
      ringExtra = 6;
    } else {
      ringStroke = STYLE.inevAvoid.targetRingStroke;
      ringDash = STYLE.inevAvoid.targetRingDash;
      ringExtra = STYLE.inevAvoid.targetRingExtra;
    }
    out.push(
      `<rect x="${x - ringExtra}" y="${y - ringExtra}" width="${w + ringExtra * 2}" height="${h + ringExtra * 2}" rx="${radius + ringExtra}" fill="none" stroke="${ringStroke}" stroke-width="2.4"` +
        (ringDash ? ` stroke-dasharray="${ringDash}"` : "") +
        ` ${quote("data-fcstm-topology", "target-ring")}/>`
    );
    // "dst" label above the ring, mirroring the "src" label on source.
    out.push(
      `<text x="${x + w + ringExtra + 6}" y="${y + h / 2 + 4}" text-anchor="start" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.smallFontSize}" font-weight="600" fill="${ringStroke}">dst</text>`
    );
  }
  if (cls.variant === "deadlock") {
    // big red X
    const pad = 8;
    out.push(
      `<g ${quote("data-fcstm-topology", "deadlock-mark")}>` +
        `<line x1="${x + pad}" y1="${y + pad}" x2="${x + w - pad}" y2="${y + h - pad}" stroke="${STYLE.deadlock.crossStroke}" stroke-width="3.6" stroke-linecap="round"/>` +
        `<line x1="${x + w - pad}" y1="${y + pad}" x2="${x + pad}" y2="${y + h - pad}" stroke="${STYLE.deadlock.crossStroke}" stroke-width="3.6" stroke-linecap="round"/>` +
        `</g>`
    );
  }

  out.push(`</g>`);
}

function buildEdgePathD(sections) {
  if (!sections || sections.length === 0) return null;
  const parts = [];
  for (const section of sections) {
    if (!section.startPoint) continue;
    parts.push(`M ${section.startPoint.x} ${section.startPoint.y}`);
    for (const bp of section.bendPoints || []) {
      parts.push(`L ${bp.x} ${bp.y}`);
    }
    parts.push(`L ${section.endPoint.x} ${section.endPoint.y}`);
  }
  return parts.join(" ");
}

function renderEdge(edge, dx, dy, overlay, out) {
  if (!edge.sections || edge.sections.length === 0) return;
  // ELK puts edge geometry in absolute coordinates relative to the
  // edge's "container" (the canvas in our flat graph). Offset by dx/dy
  // for completeness, though dx/dy are 0 at canvas level.
  const sections = edge.sections.map((s) => ({
    startPoint: { x: (s.startPoint.x || 0) + dx, y: (s.startPoint.y || 0) + dy },
    endPoint: { x: (s.endPoint.x || 0) + dx, y: (s.endPoint.y || 0) + dy },
    bendPoints: (s.bendPoints || []).map((b) => ({ x: (b.x || 0) + dx, y: (b.y || 0) + dy })),
  }));
  const d = buildEdgePathD(sections);
  if (!d) return;

  const cls = classifyEdge(edge, overlay);
  let stroke = STYLE.edgeStroke;
  let strokeWidth = STYLE.edgeStrokeWidth;
  let dasharray = "";
  let marker = "url(#arrow)";
  if (cls.overlay) {
    const ov = STYLE[cls.overlay];
    if (cls.variant === "witness") {
      stroke = ov.pathStroke;
      strokeWidth = ov.pathStrokeWidth;
      marker = "url(#arrow-witness)";
    } else if (cls.variant === "cycle") {
      stroke = ov.cycleStroke;
      strokeWidth = ov.cycleStrokeWidth;
      marker = "url(#arrow-cycle)";
    } else if (cls.variant === "prefix") {
      stroke = ov.pathStroke;
      strokeWidth = ov.pathStrokeWidth;
      dasharray = ov.pathDash;
      marker = "url(#arrow-deadlock)";
    } else if (cls.variant === "cex_path") {
      stroke = ov.pathStroke;
      strokeWidth = ov.pathStrokeWidth;
      dasharray = ov.pathDash;
      marker = "url(#arrow-avoid)";
    }
  }
  out.push(
    `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${strokeWidth}"` +
      (dasharray ? ` stroke-dasharray="${dasharray}"` : "") +
      ` marker-end="${marker}" ${quote("data-fcstm-topology-edge", edge.id)} ${quote("data-variant", cls.variant)}/>`
  );

  // Edge label
  if (edge.labels && edge.labels.length > 0) {
    for (const lbl of edge.labels) {
      const lx = (lbl.x || 0) + dx;
      const ly = (lbl.y || 0) + dy;
      const lw = lbl.width || 0;
      const lh = lbl.height || 0;
      out.push(
        `<g ${quote("data-fcstm-topology-edge-label", edge.id)}>` +
          `<rect x="${lx}" y="${ly}" width="${lw}" height="${lh}" fill="${STYLE.edgeLabelHalo}" opacity="0.92" rx="3"/>` +
          `<text x="${lx + lw / 2}" y="${ly + lh / 2 + 4}" text-anchor="middle" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.smallFontSize}" fill="${STYLE.edgeLabelColor}">${escapeXml(lbl.text || "")}</text>` +
          `</g>`
      );
    }
  }
}

export async function renderTopologySvg(payload, options) {
  options = options || {};
  const elk = new ELK();
  const input = buildElkInput(payload);
  const laidOut = await elk.layout(input);
  const overlay = payload.overlay || null;

  const baseWidth = Math.ceil(laidOut.width || 0);
  const baseHeight = Math.ceil(laidOut.height || 0);
  const bannerText = (overlay && overlay.banner) || payload.title || "";
  const bannerSpace = bannerText ? STYLE.bannerHeight + STYLE.canvasPadding / 2 : 0;
  // Banner text width: roughly char count * font-size factor + side
  // padding. Take the larger of graph width and banner width so the
  // banner is never visually clipped.
  const bannerTextWidth = Math.ceil(bannerText.length * (STYLE.bannerFontSize * 0.55) + 64);
  const contentWidth = Math.max(baseWidth, bannerTextWidth);
  const width = contentWidth + STYLE.canvasPadding * 2;
  const height = baseHeight + STYLE.canvasPadding * 2 + bannerSpace;
  const out = [];
  out.push(
    `<?xml version="1.0" encoding="UTF-8"?>` +
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.fontSize}" data-fcstm-topology-canvas="true">`
  );
  renderDefs(out);
  out.push(`<rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"/>`);

  let bannerAdvance = 0;
  if (bannerSpace) {
    bannerAdvance = renderBanner(payload, width, out);
  }
  const dx = STYLE.canvasPadding;
  const dy = STYLE.canvasPadding + bannerAdvance - STYLE.canvasPadding;
  // dy adjustment: canvas padding at top, banner offsets graph downward.

  // Render composites first so their backgrounds sit BEHIND leaf
  // nodes and edges. Within each composite, leaves render on top of
  // its tinted box.
  const originX = dx;
  const originY = dy + STYLE.canvasPadding;
  for (const node of laidOut.children || []) {
    if (node.meta && node.meta.kind === "composite") {
      renderComposite(node, originX, originY, payload, overlay, out);
    } else {
      renderNode(node, originX, originY, payload, overlay, out);
    }
  }
  // All macro edges declared at canvas level — ELK reports their
  // geometry in global coordinates regardless of which composites
  // they traverse.
  for (const edge of laidOut.edges || []) {
    renderEdge(edge, originX, originY, overlay, out);
  }
  // Edges declared within composites (we don't currently do this,
  // but defensively recurse) carry their own local coordinates that
  // ELK does not flatten to canvas.
  function walkInnerEdges(node, dx2, dy2) {
    if (!node) return;
    const cx = (node.x || 0) + dx2;
    const cy = (node.y || 0) + dy2;
    for (const edge of node.edges || []) {
      renderEdge(edge, cx, cy, overlay, out);
    }
    for (const child of node.children || []) {
      walkInnerEdges(child, cx, cy);
    }
  }
  for (const node of laidOut.children || []) {
    walkInnerEdges(node, originX, originY);
  }

  out.push(`</svg>`);
  return out.join("");
}
