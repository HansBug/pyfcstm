// Self-rendering sequence-diagram engine for SysDeSim timelines.
//
// The renderer takes a JSON object built by the Python side (see
// pyfcstm.convert.sysdesim.render._build_timeline_json) and produces an SVG
// string visually compatible with the SysDeSim XMI tooling's own export, so
// modelers see a familiar layout regardless of where the diagram comes from.

export const RENDERER_VERSION = "0.1.0";

const DEFAULT_THEME = {
  fontFamily: "DejaVu Sans, Microsoft YaHei, Arial, sans-serif",
  fontSize: 12,
  smallFontSize: 11,
  titleFontSize: 14,
  // Colors mirror the SysDeSim reference PNGs (light green actor headers,
  // gray dashed lifelines, dark text).
  actorFill: "#d8efd8",
  actorStroke: "#6f9f6f",
  lifelineStroke: "#9ea7ad",
  activationFill: "#bcdfbc",
  activationStroke: "#6f9f6f",
  arrowStroke: "#1f1f1f",
  arrowAsyncStroke: "#1f1f1f",
  textColor: "#1f1f1f",
  noteFill: "#fff8c4",
  noteStroke: "#bda030",
  bracketStroke: "#1f1f1f",
  bracketTextColor: "#1f1f1f",
  selfBracketStroke: "#1f1f1f",
  selfBracketTextColor: "#1f1f1f",
  varAssignmentFill: "#eef3ff",
  varAssignmentStroke: "#6779bf",
  diagramBackground: "#ffffff",
  panelStroke: "#5c727f",
};

const LAYOUT = {
  paddingTop: 60,
  paddingLeft: 110, // room for variable-assignment pills on the left
  paddingRight: 160, // room for time brackets on the right
  paddingBottom: 60,
  actorBoxHeight: 36,
  actorBoxMinWidth: 90,
  actorBoxPadX: 18,
  actorGap: 220,
  stepHeight: 38,
  stepFirstOffset: 30,
  varPillHeight: 22,
  varPillPadding: 12,
  bracketGap: 14, // distance between adjacent bracket lanes on the right
  bracketWidth: 24, // bracket horizontal extent within a single lane
  selfMessageWidth: 28,
  selfMessageHeight: 22,
  arrowHead: 7,
  invariantBoxPadX: 8,
  invariantBoxHeight: 20,
};

function escapeXml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function approxTextWidth(text, fontSize) {
  // Heuristic glyph width for monospace-ish fallback. This is good enough for
  // box auto-sizing; real width comes from the SVG renderer at display time.
  if (!text) return 0;
  let width = 0;
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    if (code < 128) {
      width += fontSize * 0.55;
    } else {
      // CJK characters render roughly square at this font size.
      width += fontSize * 1.1;
    }
  }
  return width;
}

function buildLifelinePositions(lifelines, theme) {
  const fontSize = theme.fontSize;
  const positions = [];
  let cursorX = LAYOUT.paddingLeft;
  for (const lifeline of lifelines) {
    const labelWidth = approxTextWidth(lifeline.display_name || lifeline.id, fontSize);
    const boxWidth = Math.max(
      LAYOUT.actorBoxMinWidth,
      labelWidth + LAYOUT.actorBoxPadX * 2
    );
    positions.push({
      id: lifeline.id,
      displayName: lifeline.display_name || lifeline.id,
      isMachineInternal: !!lifeline.is_machine_internal,
      boxWidth: boxWidth,
      centerX: cursorX + boxWidth / 2,
      boxLeft: cursorX,
      boxRight: cursorX + boxWidth,
    });
    cursorX += boxWidth + LAYOUT.actorGap;
  }
  return positions;
}

function lifelineCenterById(positions, id) {
  for (const p of positions) {
    if (p.id === id) return p.centerX;
  }
  return null;
}

function lifelineByIndex(positions, index) {
  return positions[Math.max(0, Math.min(index, positions.length - 1))];
}

function classifyMessage(message) {
  const sourceId = message.source_lifeline_id;
  const targetId = message.target_lifeline_id;
  if (!sourceId || !targetId) return "external";
  if (sourceId === targetId) return "self";
  return "cross";
}

function assignBracketLanes(constraints, stepIndexById) {
  // Each temporal constraint occupies a vertical lane on the right margin.
  // Constraints with disjoint Y-ranges share a lane; overlapping ones get
  // bumped to a new lane.
  const sorted = constraints
    .map(function (c) {
      const li = stepIndexById[c.left_step_id];
      const ri = stepIndexById[c.right_step_id];
      if (li === undefined || ri === undefined) return null;
      return {
        constraint: c,
        topIndex: Math.min(li, ri),
        bottomIndex: Math.max(li, ri),
      };
    })
    .filter(Boolean)
    .sort(function (a, b) {
      if (a.topIndex !== b.topIndex) return a.topIndex - b.topIndex;
      return a.bottomIndex - b.bottomIndex;
    });

  const lanes = []; // each lane: array of {topIndex, bottomIndex}
  const result = [];
  for (const item of sorted) {
    let placed = false;
    for (let lane = 0; lane < lanes.length; lane++) {
      const occupants = lanes[lane];
      let conflicts = false;
      for (const occ of occupants) {
        if (!(item.bottomIndex < occ.topIndex || item.topIndex > occ.bottomIndex)) {
          conflicts = true;
          break;
        }
      }
      if (!conflicts) {
        occupants.push(item);
        result.push({ constraint: item.constraint, lane: lane, topIndex: item.topIndex, bottomIndex: item.bottomIndex });
        placed = true;
        break;
      }
    }
    if (!placed) {
      lanes.push([item]);
      result.push({
        constraint: item.constraint,
        lane: lanes.length - 1,
        topIndex: item.topIndex,
        bottomIndex: item.bottomIndex,
      });
    }
  }
  return { laneAssignments: result, laneCount: lanes.length };
}

function _normalizeSecondsText(text) {
  if (text === null || text === undefined) return null;
  const trimmed = String(text).trim();
  if (!trimmed) return null;
  // Append an explicit ``s`` suffix when the imported literal is a bare
  // number, so bracket labels stay readable across raster renderers.
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return trimmed + "s";
  return trimmed;
}

function formatBracketLabel(constraint) {
  const minText = _normalizeSecondsText(constraint.min_seconds_text);
  const maxText = _normalizeSecondsText(constraint.max_seconds_text);
  if (minText && maxText) {
    if (minText === maxText && !constraint.strict_lower) return minText;
    return minText + ".." + maxText;
  }
  if (minText) return constraint.strict_lower ? "> " + minText : ">= " + minText;
  if (maxText) return "<= " + maxText;
  return "?";
}

function formatStepLeftAnnotation(step) {
  const parts = [];
  for (const action of step.actions || []) {
    if (action.kind === "set_input") {
      parts.push((action.input_name || "?") + "=" + (action.value_text || "?"));
    }
  }
  return parts;
}

function buildSvgChildren(timeline, theme, lifelinePositions, opts) {
  const children = [];
  const stepHeight = LAYOUT.stepHeight;
  const startY = LAYOUT.paddingTop + LAYOUT.actorBoxHeight + LAYOUT.stepFirstOffset;
  const stepCount = timeline.steps.length;
  const stepIndexById = {};
  for (let i = 0; i < stepCount; i++) {
    stepIndexById[timeline.steps[i].step_id] = i;
  }
  const totalLifelineHeight = startY + stepCount * stepHeight + 30;

  // Compute per-step assignment text once so the StateInvariant rendering can
  // skip redundant ``name=value`` invariants that duplicate an in-row SetInput.
  const stepAssignmentTextByIndex = [];
  for (let i = 0; i < stepCount; i++) {
    stepAssignmentTextByIndex.push(formatStepLeftAnnotation(timeline.steps[i]));
  }
  // Pre-compute single-step or "inferred-duration" constraint labels keyed by
  // their right step index so we can render them inline next to the message
  // (the SysDeSim PNG attaches ``{0s..1s}`` directly to the self-message it
  // belongs to, instead of as a separate right-margin bracket).
  const inlineSelfBracketByStepIndex = {};
  for (const c of timeline.temporal_constraints || []) {
    const li = stepIndexById[c.left_step_id];
    const ri = stepIndexById[c.right_step_id];
    if (li === undefined || ri === undefined) continue;
    const isInferred = c.kind === "inferred_duration_constraint";
    const isSingleStep = li === ri;
    if (isInferred || isSingleStep) {
      const arr = inlineSelfBracketByStepIndex[ri] || [];
      arr.push(formatBracketLabel(c));
      inlineSelfBracketByStepIndex[ri] = arr;
    }
  }
  // Bracket lanes only carry multi-step plain DurationConstraints now that
  // inferred / single-step ones render inline.
  const multiStepConstraints = (timeline.temporal_constraints || []).filter(function (c) {
    const li = stepIndexById[c.left_step_id];
    const ri = stepIndexById[c.right_step_id];
    if (li === undefined || ri === undefined) return false;
    if (c.kind === "inferred_duration_constraint") return false;
    return li !== ri;
  });

  // Numbering: only steps that draw a visible arrow get a number. SetInput- and
  // StateInvariant-only rows borrow no number, mirroring the SysDeSim PNG.
  const messageNumberByIndex = [];
  let runningNumber = 0;
  for (let i = 0; i < stepCount; i++) {
    const step = timeline.steps[i];
    const isVisibleArrow =
      !!step.message ||
      (step.outbound_signals && step.outbound_signals.length > 0);
    if (isVisibleArrow) {
      runningNumber += 1;
      messageNumberByIndex.push(runningNumber);
    } else {
      messageNumberByIndex.push(null);
    }
  }

  // Title.
  if (timeline.title) {
    children.push(svgText({
      x: LAYOUT.paddingLeft,
      y: 28,
      text: timeline.title,
      fill: theme.textColor,
      fontFamily: theme.fontFamily,
      fontSize: theme.titleFontSize,
      fontWeight: "bold",
    }));
  }

  // Actor boxes + lifelines.
  for (const pos of lifelinePositions) {
    children.push(svgRect({
      x: pos.boxLeft,
      y: LAYOUT.paddingTop,
      width: pos.boxWidth,
      height: LAYOUT.actorBoxHeight,
      rx: 6,
      ry: 6,
      fill: theme.actorFill,
      stroke: theme.actorStroke,
      strokeWidth: 1,
    }));
    children.push(svgText({
      x: pos.centerX,
      y: LAYOUT.paddingTop + LAYOUT.actorBoxHeight / 2 + 4,
      text: pos.displayName,
      fill: theme.textColor,
      fontFamily: theme.fontFamily,
      fontSize: theme.fontSize,
      anchor: "middle",
      fontWeight: "bold",
    }));
    children.push(svgLine({
      x1: pos.centerX,
      y1: LAYOUT.paddingTop + LAYOUT.actorBoxHeight,
      x2: pos.centerX,
      y2: totalLifelineHeight,
      stroke: theme.lifelineStroke,
      strokeWidth: 1,
      strokeDasharray: "4 4",
    }));
  }

  // Bracket lane assignment for temporal constraints (right margin).
  const { laneAssignments, laneCount } = assignBracketLanes(
    multiStepConstraints,
    stepIndexById
  );
  const rightmostX = lifelinePositions.length > 0
    ? lifelinePositions[lifelinePositions.length - 1].centerX
    : LAYOUT.paddingLeft;
  const bracketBaseX = rightmostX + 36; // distance from rightmost lifeline

  // Steps.
  for (let i = 0; i < stepCount; i++) {
    const step = timeline.steps[i];
    const stepY = startY + i * stepHeight;

    // Left-side variable assignment annotation.
    const varTexts = formatStepLeftAnnotation(step);
    if (varTexts.length > 0) {
      const leftmostX = lifelinePositions.length > 0
        ? lifelinePositions[0].centerX
        : LAYOUT.paddingLeft;
      const pillPadding = 6;
      const text = varTexts.join(", ");
      const pillWidth = approxTextWidth(text, theme.smallFontSize) + pillPadding * 2;
      const pillX = Math.max(8, leftmostX - 28 - pillWidth);
      const pillY = stepY - LAYOUT.varPillHeight / 2;
      children.push(svgRect({
        x: pillX,
        y: pillY,
        width: pillWidth,
        height: LAYOUT.varPillHeight,
        rx: 4,
        ry: 4,
        fill: theme.varAssignmentFill,
        stroke: theme.varAssignmentStroke,
        strokeWidth: 1,
      }));
      children.push(svgText({
        x: pillX + pillWidth / 2,
        y: pillY + LAYOUT.varPillHeight / 2 + 4,
        text: text,
        fill: theme.textColor,
        fontFamily: theme.fontFamily,
        fontSize: theme.smallFontSize,
        anchor: "middle",
      }));
    }

    // Step body: depends on whether it has a message, an invariant, or
    // outbound notes only.
    if (step.message) {
      const messageKind = classifyMessage(step.message);
      const sourceX = lifelineCenterById(lifelinePositions, step.message.source_lifeline_id);
      const targetX = lifelineCenterById(lifelinePositions, step.message.target_lifeline_id);
      const stepNumber = messageNumberByIndex[i];
      const signalLabel = step.message.label || step.message.signal_name || "";
      const labelText = (stepNumber !== null ? stepNumber + ":" : "") + signalLabel;
      const inlineBrackets = inlineSelfBracketByStepIndex[i] || [];

      if (messageKind === "self" && sourceX !== null) {
        const loopWidth = LAYOUT.selfMessageWidth;
        const loopHeight = LAYOUT.selfMessageHeight;
        const path = [
          "M", sourceX, stepY,
          "L", sourceX + loopWidth, stepY,
          "L", sourceX + loopWidth, stepY + loopHeight,
          "L", sourceX + 4, stepY + loopHeight,
        ].join(" ");
        children.push(svgPath({
          d: path,
          fill: "none",
          stroke: theme.arrowStroke,
          strokeWidth: 1,
        }));
        children.push(svgArrowHead(sourceX, stepY + loopHeight, "left", theme));
        // Inline ``{0s..1s}`` style bracket annotations rendered alongside
        // the self-loop, matching the reference SysDeSim PNG style.
        const inlineText = inlineBrackets.length
          ? "{" + inlineBrackets.join(", ") + "} " + labelText
          : labelText;
        children.push(svgText({
          x: sourceX + loopWidth + 6,
          y: stepY + loopHeight / 2 + 4,
          text: inlineText,
          fill: theme.textColor,
          fontFamily: theme.fontFamily,
          fontSize: theme.smallFontSize,
          anchor: "start",
        }));
      } else if (sourceX !== null && targetX !== null) {
        const dir = targetX > sourceX ? "right" : "left";
        children.push(svgLine({
          x1: sourceX,
          y1: stepY,
          x2: targetX,
          y2: stepY,
          stroke: theme.arrowStroke,
          strokeWidth: 1,
        }));
        children.push(svgArrowHead(targetX, stepY, dir, theme));
        children.push(svgText({
          x: (sourceX + targetX) / 2,
          y: stepY - 5,
          text: labelText,
          fill: theme.textColor,
          fontFamily: theme.fontFamily,
          fontSize: theme.smallFontSize,
          anchor: "middle",
        }));
      } else {
        // Fallback: orphan message attached to the internal lifeline.
        const fallback = lifelinePositions.length > 0 ? lifelinePositions[0].centerX : LAYOUT.paddingLeft;
        children.push(svgText({
          x: fallback,
          y: stepY,
          text: labelText,
          fill: theme.textColor,
          fontFamily: theme.fontFamily,
          fontSize: theme.smallFontSize,
          anchor: "middle",
        }));
      }
    } else if (step.invariant) {
      // State invariant box on its lifeline. Skip if the row already shows
      // a SetInput pill with the same ``name=value`` text, since the SysDeSim
      // PNG only renders one annotation per assignment row.
      const text = (step.invariant.text || "").trim();
      const assignmentParts = stepAssignmentTextByIndex[i] || [];
      const assignmentSet = {};
      for (const a of assignmentParts) {
        assignmentSet[a.replace(/\s+/g, "")] = true;
      }
      const normalized = text.replace(/\s+/g, "");
      const isRedundant = !!assignmentSet[normalized];
      if (!isRedundant) {
        const lifelineX = lifelineCenterById(lifelinePositions, step.invariant.lifeline_id);
        if (lifelineX !== null) {
          const boxWidth =
            approxTextWidth(text, theme.smallFontSize) + LAYOUT.invariantBoxPadX * 2;
          children.push(svgRect({
            x: lifelineX - boxWidth / 2,
            y: stepY - LAYOUT.invariantBoxHeight / 2,
            width: boxWidth,
            height: LAYOUT.invariantBoxHeight,
            fill: theme.noteFill,
            stroke: theme.noteStroke,
            strokeWidth: 1,
          }));
          children.push(svgText({
            x: lifelineX,
            y: stepY + 4,
            text: text,
            fill: theme.textColor,
            fontFamily: theme.fontFamily,
            fontSize: theme.smallFontSize,
            anchor: "middle",
          }));
        }
      }
    } else if ((step.outbound_signals || []).length > 0) {
      // Outbound-only step: signal sent off-stage (no machine consumer).
      const lifelinePos = lifelineByIndex(lifelinePositions, 0);
      if (lifelinePos) {
        const stepNumber = messageNumberByIndex[i];
        const text =
          (stepNumber !== null ? stepNumber + ":" : "") +
          "-->" +
          step.outbound_signals.join(", ");
        children.push(svgLine({
          x1: lifelinePos.centerX,
          y1: stepY,
          x2: lifelinePos.centerX + 80,
          y2: stepY,
          stroke: theme.arrowStroke,
          strokeWidth: 1,
          strokeDasharray: "4 3",
        }));
        children.push(svgArrowHead(lifelinePos.centerX + 80, stepY, "right", theme));
        children.push(svgText({
          x: lifelinePos.centerX + 6,
          y: stepY - 5,
          text: text,
          fill: theme.textColor,
          fontFamily: theme.fontFamily,
          fontSize: theme.smallFontSize,
          anchor: "start",
        }));
      }
    }
  }

  // Time-duration markers on the right side. Each multi-step constraint draws
  // dashed leader lines from the right-most lifeline column to a shared
  // vertical lane, capped by a double-headed arrow so the visual semantics
  // matches the SysDeSim reference: "the gap between these two events is X".
  // When the overlay flags a constraint_id as part of an UNSAT diagnostic,
  // the bracket is drawn in red instead of black and the label gets a
  // second line ("UNSAT" by default) directly under the bound expression.
  const overlayUnsatById = {};
  for (const a of ((timeline.overlay && timeline.overlay.constraint_arrows) || [])) {
    if (!a || !a.constraint_id) continue;
    overlayUnsatById[a.constraint_id] = a;
  }
  const headPad = LAYOUT.arrowHead + 1;
  for (const lane of laneAssignments) {
    const constraint = lane.constraint;
    const topIndex = lane.topIndex;
    const bottomIndex = lane.bottomIndex;
    const yTop = startY + topIndex * stepHeight;
    const yBottom = startY + bottomIndex * stepHeight;
    const tipX = bracketBaseX + lane.lane * (LAYOUT.bracketWidth + LAYOUT.bracketGap);
    const unsatArrow = overlayUnsatById[constraint.constraint_id];
    const unsat = !!unsatArrow;
    const sev = unsat ? (unsatArrow.severity || "error") : null;
    const lineStroke = unsat ? _severityFg(sev) : theme.bracketStroke;
    const labelFill = unsat ? _severityFg(sev) : theme.bracketTextColor;
    const lineWidth = unsat ? 2 : 1;
    const arrowTheme = unsat
      ? Object.assign({}, theme, { arrowStroke: lineStroke })
      : theme;
    // Dashed leader lines from the rightmost lifeline to the lane tip.
    children.push(svgLine({
      x1: rightmostX,
      y1: yTop,
      x2: tipX,
      y2: yTop,
      stroke: lineStroke,
      strokeWidth: unsat ? 1.2 : 0.7,
      strokeDasharray: "2 3",
    }));
    children.push(svgLine({
      x1: rightmostX,
      y1: yBottom,
      x2: tipX,
      y2: yBottom,
      stroke: lineStroke,
      strokeWidth: unsat ? 1.2 : 0.7,
      strokeDasharray: "2 3",
    }));
    // Vertical double-arrow segment between the two row endpoints.
    children.push(svgLine({
      x1: tipX,
      y1: yTop + headPad,
      x2: tipX,
      y2: yBottom - headPad,
      stroke: lineStroke,
      strokeWidth: lineWidth,
    }));
    children.push(svgArrowHead(tipX, yTop, "up", arrowTheme));
    children.push(svgArrowHead(tipX, yBottom, "down", arrowTheme));
    // Label rendered next to the double-arrow midpoint. When the bracket
    // is flagged UNSAT, append a second-line UNSAT sub-label so the user
    // sees the diagnostic right next to the offending bound.
    const labelMidY = (yTop + yBottom) / 2 + 4;
    children.push(svgText({
      x: tipX + 6,
      y: unsat ? labelMidY - 6 : labelMidY,
      text: formatBracketLabel(constraint),
      fill: labelFill,
      fontFamily: theme.fontFamily,
      fontSize: theme.smallFontSize,
      anchor: "start",
      fontWeight: unsat ? "bold" : null,
    }));
    if (unsat) {
      const subLabel = unsatArrow.violation_text
        || unsatArrow.label
        || "UNSAT";
      children.push(svgText({
        x: tipX + 6,
        y: labelMidY + 9,
        text: subLabel,
        fill: labelFill,
        fontFamily: theme.fontFamily,
        fontSize: theme.smallFontSize - 1,
        anchor: "start",
        fontWeight: "bold",
      }));
    }
  }

  // Document border (light frame). When the overlay attaches a state-column
  // table on the right we need to widen the canvas accordingly, so do this
  // computation after we know what the overlay payload looks like.
  const overlayForLayout = timeline.overlay || {};
  const totalWidth = computeWidth(lifelinePositions, laneCount, overlayForLayout);
  const totalHeight = totalLifelineHeight + LAYOUT.paddingBottom;
  children.unshift(svgRect({
    x: 0,
    y: 0,
    width: totalWidth,
    height: totalHeight,
    fill: theme.diagramBackground,
    stroke: theme.panelStroke,
    strokeWidth: 0.6,
  }));

  // Overlay layer: optional, additive. Diagnostics / coexistence facts
  // travel through ``timeline.overlay`` so the same layout pipeline can
  // be used both for plain sequence diagrams and for diagnostics-decorated
  // ones. Each overlay element is bounded-and-best-effort: when it
  // references an unknown id we silently skip it rather than break the
  // whole render.
  const overlay = timeline.overlay || {};
  const bandChildren = renderOverlayStepBands(
    overlay.step_bands || [], stepIndexById, startY, stepHeight, totalWidth, theme,
  );
  // Bands sit *below* the message arrows and lifelines so they read as
  // background tinting; insert them just after the diagram-border rect
  // (which is at index 0 after the unshift above).
  for (let i = 0; i < bandChildren.length; i++) {
    children.splice(1 + i, 0, bandChildren[i]);
  }
  // Marker text / icons are decorative top-layer elements - the user
  // wants to be able to spot them at a glance regardless of what is
  // already drawn underneath.
  const markerChildren = renderOverlayMarkers(
    overlay,
    timeline,
    lifelinePositions,
    stepIndexById,
    startY,
    stepHeight,
    totalWidth,
    laneCount,
    multiStepConstraints,
    theme,
  );
  for (const mc of markerChildren) {
    children.push(mc);
  }
  return {
    children: children,
    width: totalWidth,
    height: totalHeight,
  };
}


// =============================================================================
// Overlay rendering — diagnostic / coexistence markers added on top of the
// base sequence diagram. Overlay payload schema (v2):
//
//   timeline.overlay = {
//     "banner":             {severity, lines: []},
//
//     "step_bands":         [{step_id|start/end, severity, kind, label}, ...],
//
//     "message_drops":      [{message_id, severity, code,
//                             label, detail, active_state, expected_states}, ...],
//
//     "constraint_arrows":  [{constraint_id, severity, code,
//                             left_step_id, right_step_id,
//                             label, violation_text}, ...],
//
//     "state_columns":      [{header, kind: "machine"|"co"|"action"}, ...],
//     "step_states":        [{step_id, cells: ["F", "J", "yes"],
//                             highlight: "first_coexistence"|null}, ...],
//
//     // (legacy schema, still honored for backward-compat:)
//     "message_markers":    [{message_id, severity, code, label}, ...],
//     "constraint_markers": [{constraint_id, severity, code, label}, ...],
//   }
//
// All elements are bounded-and-best-effort: references to unknown step /
// message / constraint ids are silently skipped instead of failing the
// render.
// =============================================================================


const _SEVERITY_FG = {
  error: "#cc3030",
  warning: "#cc7700",
  info: "#3070cc",
  good: "#1f8b3a",
};

const _SEVERITY_BG = {
  error: "#fbe3e3",
  warning: "#fff0d6",
  info: "#e1ebfa",
  good: "#dff5e3",
};

function _severityFg(sev) {
  return _SEVERITY_FG[sev] || _SEVERITY_FG.info;
}

function _severityBg(sev) {
  return _SEVERITY_BG[sev] || _SEVERITY_BG.info;
}

const STATE_COL_WIDTH = 78;
const STATE_COL_GAP = 4;
const STATE_COL_HEADER_HEIGHT = 18;

function overlayStateColumnsWidth(overlay) {
  const cols = (overlay && overlay.state_columns) || [];
  if (cols.length === 0) return 0;
  return STATE_COL_GAP + cols.length * (STATE_COL_WIDTH + STATE_COL_GAP);
}

function computeBannerHeight(overlay) {
  const banner = overlay && overlay.banner;
  if (!banner) return 0;
  const lines = banner.lines || [];
  if (lines.length === 0) return 0;
  return 12 + lines.length * 18 + 8;
}

function renderBanner(overlay, theme, width) {
  const banner = overlay && overlay.banner;
  if (!banner) return [];
  const lines = banner.lines || [];
  if (lines.length === 0) return [];
  const sev = banner.severity || "info";
  const fg = _severityFg(sev);
  const bg = _severityBg(sev);
  const height = computeBannerHeight(overlay);
  const out = [];
  out.push(svgRect({
    x: 8, y: 6,
    width: Math.max(0, width - 16),
    height: height - 8,
    fill: bg, stroke: fg, strokeWidth: 1,
    rx: 4, ry: 4,
  }));
  const tag = "[" + sev.toUpperCase() + "]";
  out.push(svgText({
    x: 16, y: 22,
    text: tag,
    fill: fg, fontFamily: theme.fontFamily,
    fontSize: theme.smallFontSize, fontWeight: "bold",
  }));
  for (let i = 0; i < lines.length; i++) {
    out.push(svgText({
      x: 16 + 4 * 11, y: 22 + i * 18,
      text: lines[i],
      fill: fg, fontFamily: theme.fontFamily,
      fontSize: theme.smallFontSize,
      fontWeight: i === 0 ? "bold" : null,
    }));
  }
  return out;
}

function renderOverlayStepBands(bands, stepIndexById, startY, stepHeight, totalWidth, theme) {
  const out = [];
  for (const band of bands) {
    let topIdx, bottomIdx;
    if (band == null) continue;
    if (band.step_id != null) {
      const idx = stepIndexById[band.step_id];
      if (idx === undefined) continue;
      topIdx = idx;
      bottomIdx = idx;
    } else if (band.start_step_id != null && band.end_step_id != null) {
      const a = stepIndexById[band.start_step_id];
      const b = stepIndexById[band.end_step_id];
      if (a === undefined || b === undefined) continue;
      topIdx = Math.min(a, b);
      bottomIdx = Math.max(a, b);
    } else {
      continue;
    }
    const yT = startY + topIdx * stepHeight - stepHeight / 2 + 6;
    const yB = startY + bottomIdx * stepHeight + stepHeight / 2 - 2;
    const sev = band.severity || "info";
    const bg = _severityBg(sev);
    out.push(svgRect({
      x: 2, y: yT,
      width: totalWidth - 4,
      height: yB - yT,
      fill: bg, stroke: "none",
      opacity: "0.45",
    }));
    if (band.label) {
      out.push(svgText({
        x: 8, y: yT + 14,
        text: band.label,
        fill: _severityFg(sev),
        fontFamily: theme.fontFamily,
        fontSize: theme.smallFontSize,
        fontWeight: "bold",
      }));
    }
  }
  return out;
}

function _markerArrowHeadPolygon(x, y, dir, fill) {
  // Filled triangle arrow head, larger and bolder than the base
  // bracketArrowHead so it reads at a glance.
  const size = 9;
  let points;
  if (dir === "up") {
    points = (x - size / 2) + "," + (y + size) + " " +
             (x + size / 2) + "," + (y + size) + " " +
             x + "," + y;
  } else if (dir === "down") {
    points = (x - size / 2) + "," + (y - size) + " " +
             (x + size / 2) + "," + (y - size) + " " +
             x + "," + y;
  } else {
    points = (x - size) + "," + (y - size / 2) + " " +
             (x - size) + "," + (y + size / 2) + " " +
             x + "," + y;
  }
  return "<polygon points=\"" + points + "\" fill=\"" + fill +
         "\" stroke=\"" + fill + "\" stroke-width=\"1\"/>";
}

function _drawRedX(centerX, centerY, halfSize, color) {
  // Two crossing strokes form the strikethrough X over a dropped message.
  return [
    svgLine({
      x1: centerX - halfSize, y1: centerY - halfSize,
      x2: centerX + halfSize, y2: centerY + halfSize,
      stroke: color, strokeWidth: 2.5, strokeLinecap: "round",
    }),
    svgLine({
      x1: centerX - halfSize, y1: centerY + halfSize,
      x2: centerX + halfSize, y2: centerY - halfSize,
      stroke: color, strokeWidth: 2.5, strokeLinecap: "round",
    }),
  ];
}

function renderOverlayConstraintArrows(
  overlay, timeline, stepIndexById, startY, stepHeight,
  rightmostX, laneCount, multiStepConstraints, theme,
) {
  // Most ``constraint_arrows`` entries are now rendered by the base bracket
  // pass (it paints those brackets red and adds a second-line UNSAT label).
  // We only emit a separate marker when the constraint did NOT make it onto
  // a multi-step bracket lane — single-step / inferred / unknown
  // constraint_id cases. In those situations a small horizontal red
  // double-arrow + label keeps the diagnostic visible.
  const out = [];
  const arrows = (overlay && overlay.constraint_arrows) || [];
  if (arrows.length === 0) return out;

  const onLane = {};
  if (multiStepConstraints && multiStepConstraints.length > 0) {
    for (const c of multiStepConstraints) {
      if (c && c.constraint_id) onLane[c.constraint_id] = true;
    }
  }

  for (const arrow of arrows) {
    if (!arrow) continue;
    if (onLane[arrow.constraint_id]) continue; // base render already paints it red
    if (arrow.left_step_id == null || arrow.right_step_id == null) continue;
    const li = stepIndexById[arrow.left_step_id];
    const ri = stepIndexById[arrow.right_step_id];
    if (li === undefined || ri === undefined) continue;
    const topIndex = Math.min(li, ri);
    const bottomIndex = Math.max(li, ri);
    const tipX = rightmostX + 36 + laneCount * (LAYOUT.bracketWidth + LAYOUT.bracketGap) + 8;
    const sev = arrow.severity || "error";
    const fg = _severityFg(sev);
    if (topIndex === bottomIndex) {
      const yMid = startY + topIndex * stepHeight;
      out.push(svgLine({
        x1: tipX - 16, y1: yMid, x2: tipX + 16, y2: yMid,
        stroke: fg, strokeWidth: 2.5,
      }));
      out.push(_markerArrowHeadPolygon(tipX - 16, yMid, "left", fg));
      out.push(_markerArrowHeadPolygon(tipX + 16, yMid, "right", fg));
      out.push(svgText({
        x: tipX, y: yMid - 8,
        text: arrow.violation_text || arrow.label || "UNSAT",
        fill: fg, fontFamily: theme.fontFamily,
        fontSize: theme.smallFontSize, fontWeight: "bold",
        anchor: "middle",
      }));
      continue;
    }
    const yTop = startY + topIndex * stepHeight;
    const yBottom = startY + bottomIndex * stepHeight;
    out.push(svgLine({
      x1: tipX, y1: yTop + 6, x2: tipX, y2: yBottom - 6,
      stroke: fg, strokeWidth: 2.5,
    }));
    out.push(_markerArrowHeadPolygon(tipX, yTop, "up", fg));
    out.push(_markerArrowHeadPolygon(tipX, yBottom, "down", fg));
    out.push(svgText({
      x: tipX + 6, y: (yTop + yBottom) / 2 + 4,
      text: arrow.violation_text || arrow.label || "UNSAT",
      fill: fg, fontFamily: theme.fontFamily,
      fontSize: theme.smallFontSize, fontWeight: "bold",
      anchor: "start",
    }));
  }
  return out;
}

function renderOverlayMessageDrops(
  overlay, timeline, lifelinePositions, stepIndexById,
  startY, stepHeight, theme,
) {
  const out = [];
  const drops = (overlay && overlay.message_drops) || [];
  if (drops.length === 0) return out;

  const stepIndexByMessageId = {};
  for (let i = 0; i < timeline.steps.length; i++) {
    const m = timeline.steps[i].message;
    if (m && m.message_id) stepIndexByMessageId[m.message_id] = i;
  }
  const lastX = lifelinePositions.length > 0
    ? lifelinePositions[lifelinePositions.length - 1].centerX
    : LAYOUT.paddingLeft;

  for (const drop of drops) {
    if (!drop) continue;
    const idx = stepIndexByMessageId[drop.message_id];
    if (idx === undefined) continue;
    const step = timeline.steps[idx];
    const stepY = startY + idx * stepHeight;
    const sev = drop.severity || "warning";
    const fg = _severityFg(sev);
    const bg = _severityBg(sev);
    // Locate the message arrow midpoint so we can draw a red X right on
    // top of it (the arrow itself is rendered by the base layer).
    let crossX = (LAYOUT.paddingLeft + lastX) / 2;
    if (step && step.message && step.message.source_lifeline_id != null
        && step.message.target_lifeline_id != null) {
      const sx = lifelineCenterById(lifelinePositions, step.message.source_lifeline_id);
      const tx = lifelineCenterById(lifelinePositions, step.message.target_lifeline_id);
      if (sx !== null && tx !== null) {
        crossX = (sx + tx) / 2;
      }
    }
    // Red strikethrough X on the message arrow.
    const xs = _drawRedX(crossX, stepY, 7, fg);
    for (const s of xs) out.push(s);
    // Detail badge at the right margin: "✗ Sig4 dropped @ Idle (expects Run)"
    const detailLine = drop.detail
      || (drop.label || "DROPPED")
         + (drop.active_state ? " @ " + drop.active_state : "")
         + (drop.expected_states ? " (expects " + drop.expected_states + ")" : "");
    const badgeX = lastX + 14;
    const badgeWidth = Math.max(120, approxTextWidth(detailLine, theme.smallFontSize) + 24);
    out.push(svgRect({
      x: badgeX, y: stepY - 10,
      width: badgeWidth, height: 20, rx: 3, ry: 3,
      fill: bg, stroke: fg, strokeWidth: 1,
    }));
    out.push(svgText({
      x: badgeX + 6, y: stepY + 4,
      text: "✗ " + detailLine,
      fill: fg, fontFamily: theme.fontFamily,
      fontSize: theme.smallFontSize, fontWeight: "bold",
      anchor: "start",
    }));
  }
  return out;
}

function renderOverlayStateTable(
  overlay, timeline, stepIndexById, startY, stepHeight, totalWidth, theme,
) {
  const out = [];
  const cols = (overlay && overlay.state_columns) || [];
  const rows = (overlay && overlay.step_states) || [];
  if (cols.length === 0 || rows.length === 0) return out;

  const tableLeft = totalWidth - overlayStateColumnsWidth(overlay) + STATE_COL_GAP;
  // Column headers, drawn just above the first step row.
  const headerY = startY - 28;
  for (let i = 0; i < cols.length; i++) {
    const col = cols[i] || {};
    const cellX = tableLeft + i * (STATE_COL_WIDTH + STATE_COL_GAP);
    out.push(svgRect({
      x: cellX, y: headerY,
      width: STATE_COL_WIDTH, height: STATE_COL_HEADER_HEIGHT,
      fill: "#eef0f2", stroke: "#9ea7ad", strokeWidth: 0.6, rx: 2, ry: 2,
    }));
    out.push(svgText({
      x: cellX + STATE_COL_WIDTH / 2, y: headerY + 13,
      text: col.header || "",
      fill: theme.textColor,
      fontFamily: theme.fontFamily,
      fontSize: theme.smallFontSize, fontWeight: "bold",
      anchor: "middle",
    }));
  }
  // Per-step rows.
  for (const row of rows) {
    if (!row) continue;
    const idx = stepIndexById[row.step_id];
    if (idx === undefined) continue;
    const stepY = startY + idx * stepHeight;
    const cellTop = stepY - 12;
    const isFirstCoex = row.highlight === "first_coexistence";
    const isCoex = row.highlight === "coexistence";
    const rowBg = isFirstCoex ? _severityBg("good")
                  : isCoex ? "#eaf6ed"
                  : "#fafbfc";
    const rowStroke = isFirstCoex ? _severityFg("good") : "#cbd1d6";
    for (let i = 0; i < cols.length; i++) {
      const cellX = tableLeft + i * (STATE_COL_WIDTH + STATE_COL_GAP);
      out.push(svgRect({
        x: cellX, y: cellTop,
        width: STATE_COL_WIDTH, height: 22,
        fill: rowBg, stroke: rowStroke,
        strokeWidth: isFirstCoex ? 1.4 : 0.6, rx: 2, ry: 2,
      }));
      const text = (row.cells || [])[i];
      if (text == null || text === "") continue;
      const col = cols[i] || {};
      let textColor = theme.textColor;
      let weight = null;
      if (col.kind === "co") {
        if (text === "start" || isFirstCoex) {
          textColor = _severityFg("good");
          weight = "bold";
        } else if (text === "yes") {
          textColor = _severityFg("good");
        } else if (text === "initial") {
          textColor = _severityFg("info");
        }
      }
      out.push(svgText({
        x: cellX + STATE_COL_WIDTH / 2, y: cellTop + 15,
        text: String(text),
        fill: textColor, fontFamily: theme.fontFamily,
        fontSize: theme.smallFontSize,
        fontWeight: weight,
        anchor: "middle",
      }));
    }
  }
  return out;
}

function renderOverlayMarkers(
  overlay, timeline, lifelinePositions, stepIndexById,
  startY, stepHeight, totalWidth, laneCount, multiStepConstraints, theme,
) {
  const out = [];
  const lastX = lifelinePositions.length > 0
    ? lifelinePositions[lifelinePositions.length - 1].centerX
    : LAYOUT.paddingLeft;

  // Build a step-index lookup keyed by message_id so markers can find
  // the row their referenced message sits on.
  const stepIndexByMessageId = {};
  for (let i = 0; i < timeline.steps.length; i++) {
    const m = timeline.steps[i].message;
    if (m && m.message_id) stepIndexByMessageId[m.message_id] = i;
  }

  // ---- v2: red X strikethrough + detail badge for message_drops --------
  const dropChildren = renderOverlayMessageDrops(
    overlay, timeline, lifelinePositions, stepIndexById,
    startY, stepHeight, theme,
  );
  for (const c of dropChildren) out.push(c);

  // ---- v2: red double-arrow for constraint_arrows ----------------------
  const arrowChildren = renderOverlayConstraintArrows(
    overlay, timeline, stepIndexById, startY, stepHeight,
    lastX, laneCount, multiStepConstraints, theme,
  );
  for (const c of arrowChildren) out.push(c);

  // ---- v2: per-step state cells for validate-style overlays ------------
  const stateChildren = renderOverlayStateTable(
    overlay, timeline, stepIndexById, startY, stepHeight, totalWidth, theme,
  );
  for (const c of stateChildren) out.push(c);

  // ---- legacy v1 schema: small "!" badge + "UNSAT" text label ----------
  // Kept so older callers / saved overlay JSONs keep rendering, even if
  // they no longer get the v2 visual treatment.
  for (const marker of (overlay.message_markers || [])) {
    if (marker == null) continue;
    const idx = stepIndexByMessageId[marker.message_id];
    if (idx === undefined) continue;
    const stepY = startY + idx * stepHeight;
    const sev = marker.severity || "warning";
    const fg = _severityFg(sev);
    const iconX = lastX + 16;
    out.push(svgRect({
      x: iconX - 6, y: stepY - 7,
      width: 12, height: 14, rx: 2, ry: 2,
      fill: fg, stroke: fg, strokeWidth: 1,
    }));
    out.push(svgText({
      x: iconX, y: stepY + 4,
      text: "!",
      fill: "#ffffff",
      fontFamily: theme.fontFamily,
      fontSize: theme.fontSize, fontWeight: "bold",
      anchor: "middle",
    }));
    if (marker.label) {
      out.push(svgText({
        x: iconX + 10, y: stepY + 4,
        text: marker.label,
        fill: fg, fontFamily: theme.fontFamily,
        fontSize: theme.smallFontSize, fontWeight: "bold",
        anchor: "start",
      }));
    }
  }
  const laneXByConstraintId = {};
  if (multiStepConstraints && multiStepConstraints.length > 0) {
    const { laneAssignments } = assignBracketLanes(
      multiStepConstraints, stepIndexById,
    );
    const bracketBaseX = lastX + 36;
    for (const lane of laneAssignments) {
      const cid = lane.constraint && lane.constraint.constraint_id;
      if (!cid) continue;
      laneXByConstraintId[cid] = {
        tipX: bracketBaseX + lane.lane * (LAYOUT.bracketWidth + LAYOUT.bracketGap),
        topIndex: lane.topIndex,
      };
    }
  }
  for (const marker of (overlay.constraint_markers || [])) {
    if (marker == null) continue;
    const lane = laneXByConstraintId[marker.constraint_id];
    if (!lane) continue;
    const sev = marker.severity || "error";
    const fg = _severityFg(sev);
    const yLabel = startY + lane.topIndex * stepHeight - 14;
    out.push(svgText({
      x: lane.tipX, y: yLabel,
      text: (marker.code === "temporal_constraints_unsat" ? "UNSAT" : (marker.label || "ISSUE")),
      fill: fg, fontFamily: theme.fontFamily,
      fontSize: theme.smallFontSize, fontWeight: "bold",
      anchor: "middle",
    }));
  }

  return out;
}

function computeWidth(lifelinePositions, bracketLaneCount, overlay) {
  const lastX = lifelinePositions.length > 0
    ? lifelinePositions[lifelinePositions.length - 1].centerX
    : LAYOUT.paddingLeft;
  const bracketsRightExtent =
    bracketLaneCount > 0
      ? 70 + bracketLaneCount * (LAYOUT.bracketWidth + LAYOUT.bracketGap) + 80
      : LAYOUT.paddingRight;
  const overlayExtent = overlayStateColumnsWidth(overlay);
  // When state_columns are present we also reserve space for the inline
  // detail badge a message_drops marker emits next to the rightmost
  // lifeline; bump the extent a bit so badges don't collide with the
  // first state column.
  const dropExtent = (overlay && (overlay.message_drops || []).length > 0) ? 200 : 0;
  return lastX + bracketsRightExtent + overlayExtent + dropExtent;
}

// =============================================================================
// SVG primitive helpers
// =============================================================================

function svgRect(attrs) {
  return (
    "<rect" +
    Object.keys(attrs)
      .map(function (k) { return " " + svgAttrName(k) + "=\"" + escapeXml(attrs[k]) + "\""; })
      .join("") +
    "/>"
  );
}

function svgLine(attrs) {
  return (
    "<line" +
    Object.keys(attrs)
      .map(function (k) { return " " + svgAttrName(k) + "=\"" + escapeXml(attrs[k]) + "\""; })
      .join("") +
    "/>"
  );
}

function svgPath(attrs) {
  return (
    "<path" +
    Object.keys(attrs)
      .map(function (k) { return " " + svgAttrName(k) + "=\"" + escapeXml(attrs[k]) + "\""; })
      .join("") +
    "/>"
  );
}

function svgText(opts) {
  const attrs = [
    "x=\"" + escapeXml(opts.x) + "\"",
    "y=\"" + escapeXml(opts.y) + "\"",
    "fill=\"" + escapeXml(opts.fill) + "\"",
    "font-family=\"" + escapeXml(opts.fontFamily) + "\"",
    "font-size=\"" + escapeXml(opts.fontSize) + "\"",
  ];
  if (opts.anchor) attrs.push("text-anchor=\"" + escapeXml(opts.anchor) + "\"");
  if (opts.fontWeight) attrs.push("font-weight=\"" + escapeXml(opts.fontWeight) + "\"");
  return "<text " + attrs.join(" ") + ">" + escapeXml(opts.text) + "</text>";
}

function svgArrowHead(x, y, dir, theme) {
  const size = LAYOUT.arrowHead;
  let points;
  if (dir === "left") {
    points = (x + size) + "," + (y - size / 2) + " " +
             (x + size) + "," + (y + size / 2) + " " +
             x + "," + y;
  } else if (dir === "up") {
    points = (x - size / 2) + "," + (y + size) + " " +
             (x + size / 2) + "," + (y + size) + " " +
             x + "," + y;
  } else if (dir === "down") {
    points = (x - size / 2) + "," + (y - size) + " " +
             (x + size / 2) + "," + (y - size) + " " +
             x + "," + y;
  } else {
    points = (x - size) + "," + (y - size / 2) + " " +
             (x - size) + "," + (y + size / 2) + " " +
             x + "," + y;
  }
  return "<polygon points=\"" + points + "\" fill=\"" + theme.arrowStroke + "\" stroke=\"" + theme.arrowStroke + "\"/>";
}

function svgAttrName(name) {
  // Convert camelCase to kebab-case for SVG attribute spelling.
  if (name === "rx" || name === "ry" || name === "x" || name === "y") return name;
  if (name === "x1" || name === "y1" || name === "x2" || name === "y2") return name;
  if (name === "d") return name;
  if (name === "fill" || name === "stroke" || name === "width" || name === "height") return name;
  return name.replace(/[A-Z]/g, function (ch) { return "-" + ch.toLowerCase(); });
}

// =============================================================================
// Public entry
// =============================================================================

export function renderSequenceSvg(timeline, options) {
  const theme = Object.assign({}, DEFAULT_THEME, (options && options.theme) || {});
  const lifelinePositions = buildLifelinePositions(timeline.lifelines || [], theme);
  const built = buildSvgChildren(timeline, theme, lifelinePositions, options || {});

  // Top banner (overlay summary) sits above the diagram and shifts the
  // base layout down by ``bannerOffset``. We render the banner directly
  // (it lives in the outer SVG coordinate space) and wrap the base
  // children in a ``<g transform=translate(0, bannerOffset)>`` so we do
  // not have to thread the offset through every ``y`` computation.
  const overlay = timeline.overlay || {};
  const bannerOffset = computeBannerHeight(overlay);
  const totalHeight = built.height + bannerOffset;

  const bannerSvg = bannerOffset > 0
    ? renderBanner(overlay, theme, built.width).join("\n") + "\n"
    : "";
  const baseSvg = bannerOffset > 0
    ? "<g transform=\"translate(0, " + bannerOffset + ")\">\n"
        + built.children.join("\n")
        + "\n</g>"
    : built.children.join("\n");
  return (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
    "<svg xmlns=\"http://www.w3.org/2000/svg\" " +
    "viewBox=\"0 0 " + built.width + " " + totalHeight + "\" " +
    "width=\"" + built.width + "\" height=\"" + totalHeight + "\" " +
    "font-family=\"" + escapeXml(theme.fontFamily) + "\">\n" +
    bannerSvg +
    baseSvg +
    "\n</svg>"
  );
}
