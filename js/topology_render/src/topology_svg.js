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
    '"DejaVu Sans","JetBrains Mono","Fira Code",Consolas,"Microsoft YaHei",sans-serif',
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

function buildElkInput(payload) {
  // Flat compound graph: every node is a top-level child of __canvas__.
  // v0 does not preserve composite outlines; revisit if users ask.
  const nodes = payload.nodes || [];
  const edges = payload.edges || [];
  const elkNodes = nodes.map((n) => {
    const labelDims = measureNodeLabel(n.label || n.id);
    const isPseudoLike = n.kind === "pseudo" || n.kind === "end";
    return {
      id: n.id,
      width: isPseudoLike && n.kind === "end" ? 50 : labelDims.width,
      height: isPseudoLike && n.kind === "end" ? 50 : labelDims.height,
      labels: [{ text: n.label || n.id, width: labelDims.width, height: labelDims.height }],
      meta: n,
    };
  });
  const elkEdges = edges.map((e, idx) => {
    const edge = {
      id: e.id || `e${idx}`,
      sources: [e.source],
      targets: [e.target],
      meta: e,
    };
    if (e.label) {
      const dims = measureEdgeLabel(e.label);
      edge.labels = [{ text: e.label, width: dims.width, height: dims.height }];
    }
    return edge;
  });
  return {
    id: "__canvas__",
    layoutOptions: { ...ELK_LAYOUT_OPTIONS, "elk.direction": payload.direction || "DOWN" },
    children: elkNodes,
    edges: elkEdges,
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
    const reachSet = new Set(overlay.reach_set || []);
    if (id === overlay.source) return { variant: "source", overlay: "reachOk" };
    if (id === overlay.target && verdict === "ok") return { variant: "target", overlay: "reachOk" };
    if (id === overlay.target && verdict === "fail") return { variant: "target_missed", overlay: "reachUnreach" };
    if (reachSet.has(id)) return { variant: "reach", overlay: "reachOk" };
    return { variant: "unreach", overlay: "reachUnreach" };
  }

  if (kind === "finite") {
    if (verdict === "ok") return { variant: "reach", overlay: "reachOk" };
    const cycleSet = new Set(overlay.cycle || []);
    if (cycleSet.has(id)) return { variant: "cycle", overlay: "trapCycle" };
    if (id === overlay.deadlock_leaf) return { variant: "deadlock", overlay: "deadlock" };
    const prefixSet = new Set(overlay.prefix || []);
    if (prefixSet.has(id)) return { variant: "prefix", overlay: "deadlock" };
    if (id === overlay.source) return { variant: "source" };
    return { variant: "neutral" };
  }

  if (kind === "inev") {
    if (verdict === "ok") {
      if (id === overlay.target) return { variant: "target", overlay: "reachOk" };
      if (id === overlay.source) return { variant: "source", overlay: "reachOk" };
      const reachSet = new Set(overlay.reach_set || []);
      if (reachSet.has(id)) return { variant: "reach", overlay: "reachOk" };
      return { variant: "neutral" };
    }
    const cexKind = overlay.cex_kind || "";
    if (id === overlay.target) return { variant: "target_missed", overlay: "inevAvoid" };
    if (id === overlay.source) return { variant: "source", overlay: "inevAvoid" };
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
      `<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.edgeStroke}"/></marker>` +
      `<marker id="arrow-witness" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.reachOk.pathStroke}"/></marker>` +
      `<marker id="arrow-cycle" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.trapCycle.cycleStroke}"/></marker>` +
      `<marker id="arrow-avoid" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse" markerUnits="userSpaceOnUse">` +
      `<path d="M0,0 L10,5 L0,10 Z" fill="${STYLE.inevAvoid.pathStroke}"/></marker>` +
      `<marker id="arrow-deadlock" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse" markerUnits="userSpaceOnUse">` +
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
      `<text x="${x + 18}" y="${y + h / 2 + 5}" ${quote("font-family", STYLE.fontFamily)} font-size="${STYLE.bannerFontSize}" font-weight="700" fill="${styleBlock.textFill}">${escapeXml(text)}</text>` +
      `</g>`
  );
  return STYLE.bannerHeight + STYLE.canvasPadding;
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

  // Special markers
  if (cls.variant === "source") {
    // ▶ marker on the left side
    const mx = x - 16;
    const my = y + h / 2;
    const color = (cls.overlay && STYLE[cls.overlay] && STYLE[cls.overlay].sourceMarker) || STYLE.reachOk.sourceMarker;
    out.push(
      `<polygon points="${mx},${my - 8} ${mx + 12},${my} ${mx},${my + 8}" fill="${color}" ${quote("data-fcstm-topology", "source-marker")}/>`
    );
  }
  if (cls.variant === "target" && cls.overlay === "reachOk") {
    const cx = x + w / 2;
    const cy = y + h / 2;
    const r = Math.max(w, h) / 2 + STYLE.reachOk.targetRingExtra;
    out.push(
      `<rect x="${x - STYLE.reachOk.targetRingExtra}" y="${y - STYLE.reachOk.targetRingExtra}" width="${w + STYLE.reachOk.targetRingExtra * 2}" height="${h + STYLE.reachOk.targetRingExtra * 2}" rx="${radius + STYLE.reachOk.targetRingExtra}" fill="none" stroke="${STYLE.reachOk.targetRingStroke}" stroke-width="2.4"/>`
    );
  }
  if (cls.variant === "target_missed") {
    const ringExtra = (overlay && overlay.kind === "reach") ? 6 : (STYLE.inevAvoid.targetRingExtra || 6);
    const ringStroke = (overlay && overlay.kind === "reach") ? "#b62a2a" : STYLE.inevAvoid.targetRingStroke;
    const ringDash = (overlay && overlay.kind === "reach") ? "4 3" : STYLE.inevAvoid.targetRingDash;
    out.push(
      `<rect x="${x - ringExtra}" y="${y - ringExtra}" width="${w + ringExtra * 2}" height="${h + ringExtra * 2}" rx="${radius + ringExtra}" fill="none" stroke="${ringStroke}" stroke-width="2.4" stroke-dasharray="${ringDash}"/>`
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

  // Render nodes first (so edges go on top to be more visible)
  for (const node of laidOut.children || []) {
    renderNode(node, dx, dy + STYLE.canvasPadding, payload, overlay, out);
  }
  for (const edge of laidOut.edges || []) {
    renderEdge(edge, dx, dy + STYLE.canvasPadding, overlay, out);
  }

  out.push(`</svg>`);
  return out.join("");
}
