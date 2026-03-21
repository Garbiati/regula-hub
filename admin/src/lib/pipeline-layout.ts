// Pure layout engine for the Pipeline DAG visualization.
// No React — easy to test.

export interface LayoutNode {
  id: string;
  type: "operator" | "login" | "search" | "results" | "merge" | "filter" | "cache" | "persist" | "enrich" | "final";
  /** Row index for operator-scoped nodes, -1 for shared nodes */
  row: number;
  x: number;
  y: number;
  w: number;
  h: number;
  /** Column index for stagger animations */
  col: number;
  /** Associated operator username (empty for shared nodes) */
  operator: string;
}

export interface LayoutEdge {
  id: string;
  from: string;
  to: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
}

export interface DagLayout {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  totalWidth: number;
  totalHeight: number;
  /** Node width for the current tier (used by node components for font sizing) */
  nodeW: number;
  /** Node height for the current tier (used by node components for font sizing) */
  nodeH: number;
}

// ── Adaptive sizing by operator count ──

interface SizingTier {
  nodeW: number;
  nodeH: number;
  mergeW: number;
  mergeH: number;
  finalW: number;
  finalH: number;
  colGap: number;
  rowGap: number;
}

function getSizingTier(n: number): SizingTier {
  if (n <= 2) return { nodeW: 140, nodeH: 56, mergeW: 120, mergeH: 68, finalW: 100, finalH: 56, colGap: 28, rowGap: 24 };
  if (n <= 6) return { nodeW: 130, nodeH: 46, mergeW: 110, mergeH: 56, finalW: 90, finalH: 46, colGap: 28, rowGap: 16 };
  return { nodeW: 110, nodeH: 38, mergeW: 100, mergeH: 46, finalW: 80, finalH: 38, colGap: 24, rowGap: 10 };
}

function colX(col: number, colWidths: number[], colGap: number): number {
  let x = 0;
  for (let i = 0; i < col; i++) {
    x += (colWidths[i] ?? 0) + colGap;
  }
  return x;
}

function nodeHeight(type: LayoutNode["type"], tier: SizingTier): number {
  if (type === "merge" || type === "enrich" || type === "filter" || type === "cache" || type === "persist") return tier.mergeH;
  if (type === "final") return tier.finalH;
  return tier.nodeH;
}

function nodeWidth(type: LayoutNode["type"], tier: SizingTier): number {
  if (type === "merge" || type === "enrich" || type === "filter" || type === "cache" || type === "persist") return tier.mergeW;
  if (type === "final") return tier.finalW;
  return tier.nodeW;
}

/**
 * Compute a full DAG layout given N operator usernames.
 *
 * Base layout (cols):
 *   Operator → Login → Search → Results → Merge+Dedup → Filter → [Persist] → [Enrich] → Final
 *
 * When cacheEnabled, a Cache node is placed above operators with an edge into Merge.
 * When cacheEnabled, a Persist node appears after Filter.
 * When enrichEnabled, an Enrich node appears after Persist (or Filter).
 *
 * Merge, Filter, Persist, Enrich, Cache and Final nodes are vertically centered against operator rows.
 */
export function computeDagLayout(usernames: string[], enrichEnabled = false, cacheEnabled = false): DagLayout {
  const n = usernames.length;
  const tier = getSizingTier(n);
  const nodes: LayoutNode[] = [];
  const edges: LayoutEdge[] = [];

  // ── Build column widths dynamically ──
  // Cols 0-3: operator steps, Col 4: merge, then filter, [persist], [enrich], final
  const colWidthsList: number[] = [
    tier.nodeW, // 0: operator
    tier.nodeW, // 1: login
    tier.nodeW, // 2: search
    tier.nodeW, // 3: results
    tier.mergeW, // 4: merge
    tier.mergeW, // 5: filter (always present)
  ];

  let nextCol = 6;
  const enrichCol = enrichEnabled ? nextCol++ : -1;
  if (enrichEnabled) colWidthsList.push(tier.mergeW);

  const persistCol = cacheEnabled ? nextCol++ : -1;
  if (cacheEnabled) colWidthsList.push(tier.mergeW);

  const finalCol = nextCol;
  colWidthsList.push(tier.finalW);

  const mergeCol = 4;
  const filterCol = 5;

  const rowHeight = tier.nodeH + tier.rowGap;
  // When cache enabled, add an extra row above for the cache node
  const cacheRowOffset = cacheEnabled ? 1 : 0;
  const operatorRowsHeight = n * tier.nodeH + (n - 1) * tier.rowGap;
  const totalRowsHeight = cacheEnabled
    ? operatorRowsHeight + tier.mergeH + tier.rowGap
    : operatorRowsHeight;

  // ── Cache node (above operators, col 0) ──
  if (cacheEnabled) {
    const cacheX = colX(0, colWidthsList, tier.colGap);
    const cacheY = 0;
    nodes.push({ id: "cache", type: "cache", row: -1, x: cacheX, y: cacheY, w: tier.mergeW, h: tier.mergeH, col: 0, operator: "" });
  }

  // ── Per-operator rows (cols 0–3) ──
  const opStartY = cacheEnabled ? tier.mergeH + tier.rowGap : 0;

  for (let i = 0; i < n; i++) {
    const username = usernames[i]!;
    const y = opStartY + i * rowHeight;

    const steps: Array<{ type: LayoutNode["type"]; col: number }> = [
      { type: "operator", col: 0 },
      { type: "login", col: 1 },
      { type: "search", col: 2 },
      { type: "results", col: 3 },
    ];

    for (const step of steps) {
      const w = nodeWidth(step.type, tier);
      const h = nodeHeight(step.type, tier);
      const x = colX(step.col, colWidthsList, tier.colGap);
      const nodeId = `${username}-${step.type}`;

      nodes.push({ id: nodeId, type: step.type, row: i + cacheRowOffset, x, y, w, h, col: step.col, operator: username });
    }

    // Edges within the row: operator → login → search → results
    for (let c = 0; c < 3; c++) {
      const fromType = steps[c]!.type;
      const toType = steps[c + 1]!.type;
      const fromId = `${username}-${fromType}`;
      const toId = `${username}-${toType}`;
      const fromNode = nodes.find((nd) => nd.id === fromId)!;
      const toNode = nodes.find((nd) => nd.id === toId)!;

      edges.push({
        id: `${fromId}->${toId}`,
        from: fromId,
        to: toId,
        fromX: fromNode.x + fromNode.w,
        fromY: fromNode.y + fromNode.h / 2,
        toX: toNode.x,
        toY: toNode.y + toNode.h / 2,
      });
    }
  }

  // ── Merge node (col 4), vertically centered against operator rows ──
  const mergeX = colX(mergeCol, colWidthsList, tier.colGap);
  const mergeCenterBase = opStartY + (operatorRowsHeight - tier.mergeH) / 2;
  const mergeY = Math.max(0, mergeCenterBase);

  nodes.push({ id: "merge", type: "merge", row: -1, x: mergeX, y: mergeY, w: tier.mergeW, h: tier.mergeH, col: mergeCol, operator: "" });

  // ── Fan-in edges: each results → merge ──
  const mergeNode = nodes.find((nd) => nd.id === "merge")!;
  for (let i = 0; i < n; i++) {
    const username = usernames[i];
    const resultsId = `${username}-results`;
    const resultsNode = nodes.find((nd) => nd.id === resultsId)!;
    edges.push({
      id: `${resultsId}->merge`,
      from: resultsId,
      to: "merge",
      fromX: resultsNode.x + resultsNode.w,
      fromY: resultsNode.y + resultsNode.h / 2,
      toX: mergeNode.x,
      toY: mergeNode.y + mergeNode.h / 2,
    });
  }

  // ── Cache → Merge edge ──
  if (cacheEnabled) {
    const cacheNode = nodes.find((nd) => nd.id === "cache")!;
    edges.push({
      id: "cache->merge",
      from: "cache",
      to: "merge",
      fromX: cacheNode.x + cacheNode.w,
      fromY: cacheNode.y + cacheNode.h / 2,
      toX: mergeNode.x,
      toY: mergeNode.y + mergeNode.h / 2,
    });
  }

  // ── Filter node (col 5) ──
  const filterX = colX(filterCol, colWidthsList, tier.colGap);
  const filterY = mergeY;
  nodes.push({ id: "filter", type: "filter", row: -1, x: filterX, y: filterY, w: tier.mergeW, h: tier.mergeH, col: filterCol, operator: "" });

  const filterNode = nodes.find((nd) => nd.id === "filter")!;
  edges.push({
    id: "merge->filter",
    from: "merge",
    to: "filter",
    fromX: mergeNode.x + mergeNode.w,
    fromY: mergeNode.y + mergeNode.h / 2,
    toX: filterNode.x,
    toY: filterNode.y + filterNode.h / 2,
  });

  // ── Chain: filter → [enrich] → [persist] → final ──
  let prevNodeId = "filter";

  // Enrich node (only when enrichEnabled)
  if (enrichEnabled) {
    const enrichX = colX(enrichCol, colWidthsList, tier.colGap);
    const enrichY = mergeY;
    nodes.push({ id: "enrich", type: "enrich", row: -1, x: enrichX, y: enrichY, w: tier.mergeW, h: tier.mergeH, col: enrichCol, operator: "" });

    const prevNode = nodes.find((nd) => nd.id === prevNodeId)!;
    const enrichNode = nodes.find((nd) => nd.id === "enrich")!;
    edges.push({
      id: `${prevNodeId}->enrich`,
      from: prevNodeId,
      to: "enrich",
      fromX: prevNode.x + prevNode.w,
      fromY: prevNode.y + prevNode.h / 2,
      toX: enrichNode.x,
      toY: enrichNode.y + enrichNode.h / 2,
    });
    prevNodeId = "enrich";
  }

  // Persist node (only when cache enabled) — AFTER enrich so enriched data is persisted
  if (cacheEnabled) {
    const persistX = colX(persistCol, colWidthsList, tier.colGap);
    const persistY = mergeY;
    nodes.push({ id: "persist", type: "persist", row: -1, x: persistX, y: persistY, w: tier.mergeW, h: tier.mergeH, col: persistCol, operator: "" });

    const prevNode = nodes.find((nd) => nd.id === prevNodeId)!;
    const persistNode = nodes.find((nd) => nd.id === "persist")!;
    edges.push({
      id: `${prevNodeId}->persist`,
      from: prevNodeId,
      to: "persist",
      fromX: prevNode.x + prevNode.w,
      fromY: prevNode.y + prevNode.h / 2,
      toX: persistNode.x,
      toY: persistNode.y + persistNode.h / 2,
    });
    prevNodeId = "persist";
  }

  // ── Final node ──
  const finalX = colX(finalCol, colWidthsList, tier.colGap);
  const finalY = mergeY + (tier.mergeH - tier.finalH) / 2;
  nodes.push({ id: "final", type: "final", row: -1, x: finalX, y: finalY, w: tier.finalW, h: tier.finalH, col: finalCol, operator: "" });

  const prevFinal = nodes.find((nd) => nd.id === prevNodeId)!;
  const finalNode = nodes.find((nd) => nd.id === "final")!;
  edges.push({
    id: `${prevNodeId}->final`,
    from: prevNodeId,
    to: "final",
    fromX: prevFinal.x + prevFinal.w,
    fromY: prevFinal.y + prevFinal.h / 2,
    toX: finalNode.x,
    toY: finalNode.y + finalNode.h / 2,
  });

  // ── Total dimensions ──
  const rawHeight = Math.max(totalRowsHeight, mergeY + tier.mergeH);
  const totalWidth = finalX + tier.finalW;
  const totalHeight = rawHeight;

  return { nodes, edges, totalWidth, totalHeight, nodeW: tier.nodeW, nodeH: tier.nodeH };
}
