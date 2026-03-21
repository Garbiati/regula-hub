import { describe, expect, it } from "vitest";

import { computeDagLayout } from "@/lib/pipeline-layout";

describe("computeDagLayout", () => {
  it("returns correct node count for 1 operator", () => {
    const layout = computeDagLayout(["op1"]);
    // 1 operator × 4 step nodes + merge + filter + final = 7
    expect(layout.nodes).toHaveLength(7);
  });

  it("returns correct node count for 3 operators", () => {
    const layout = computeDagLayout(["op1", "op2", "op3"]);
    // 3 operators × 4 + merge + filter + final = 15
    expect(layout.nodes).toHaveLength(15);
  });

  it("returns correct node count for 5 operators", () => {
    const layout = computeDagLayout(["a", "b", "c", "d", "e"]);
    // 5 × 4 + 3 = 23
    expect(layout.nodes).toHaveLength(23);
  });

  it("returns correct edge count for 1 operator", () => {
    const layout = computeDagLayout(["op1"]);
    // 3 intra-row + 1 fan-in + 1 merge→filter + 1 filter→final = 6
    expect(layout.edges).toHaveLength(6);
  });

  it("returns correct edge count for 3 operators", () => {
    const layout = computeDagLayout(["op1", "op2", "op3"]);
    // 3×3 intra-row + 3 fan-in + 1 merge→filter + 1 filter→final = 14
    expect(layout.edges).toHaveLength(14);
  });

  it("has no overlapping nodes", () => {
    const layout = computeDagLayout(["op1", "op2", "op3"]);
    for (let i = 0; i < layout.nodes.length; i++) {
      for (let j = i + 1; j < layout.nodes.length; j++) {
        const a = layout.nodes[i];
        const b = layout.nodes[j];
        const overlapX = a.x < b.x + b.w && a.x + a.w > b.x;
        const overlapY = a.y < b.y + b.h && a.y + a.h > b.y;
        if (overlapX && overlapY) {
          throw new Error(`Nodes ${a.id} and ${b.id} overlap`);
        }
      }
    }
  });

  it("centers merge node vertically among operator rows", () => {
    const layout = computeDagLayout(["op1", "op2", "op3"]);
    const merge = layout.nodes.find((n) => n.id === "merge")!;
    const opNodes = layout.nodes.filter((n) => n.type === "operator");
    const minY = Math.min(...opNodes.map((n) => n.y));
    const maxY = Math.max(...opNodes.map((n) => n.y + n.h));
    const centerOfRows = (minY + maxY) / 2;
    const mergeCenter = merge.y + merge.h / 2;
    expect(Math.abs(mergeCenter - centerOfRows)).toBeLessThan(20);
  });

  it("assigns correct column indices", () => {
    const layout = computeDagLayout(["op1"]);
    const cols = layout.nodes.map((n) => ({ id: n.id, col: n.col }));
    expect(cols.find((c) => c.id === "op1-operator")?.col).toBe(0);
    expect(cols.find((c) => c.id === "op1-login")?.col).toBe(1);
    expect(cols.find((c) => c.id === "op1-search")?.col).toBe(2);
    expect(cols.find((c) => c.id === "op1-results")?.col).toBe(3);
    expect(cols.find((c) => c.id === "merge")?.col).toBe(4);
    expect(cols.find((c) => c.id === "filter")?.col).toBe(5);
    expect(cols.find((c) => c.id === "final")?.col).toBe(6);
  });

  it("totalWidth and totalHeight are positive", () => {
    const layout = computeDagLayout(["op1", "op2"]);
    expect(layout.totalWidth).toBeGreaterThan(0);
    expect(layout.totalHeight).toBeGreaterThan(0);
  });

  it("handles large operator count (15)", () => {
    const ops = Array.from({ length: 15 }, (_, i) => `op${i}`);
    const layout = computeDagLayout(ops);
    // 15 × 4 step nodes + merge + filter + final = 63
    expect(layout.nodes).toHaveLength(15 * 4 + 3);
    // 15×3 intra-row + 15 fan-in + merge→filter + filter→final = 62
    expect(layout.edges).toHaveLength(15 * 3 + 15 + 2);
    expect(layout.totalHeight).toBeGreaterThan(0);
  });

  it("edges connect right-center to left-center of nodes", () => {
    const layout = computeDagLayout(["op1"]);
    for (const edge of layout.edges) {
      const from = layout.nodes.find((n) => n.id === edge.from)!;
      const to = layout.nodes.find((n) => n.id === edge.to)!;
      expect(edge.fromX).toBe(from.x + from.w);
      expect(edge.fromY).toBe(from.y + from.h / 2);
      expect(edge.toX).toBe(to.x);
      expect(edge.toY).toBe(to.y + to.h / 2);
    }
  });

  // ── Adaptive sizing tier tests ──

  it("uses large sizing tier for 1 operator", () => {
    const layout = computeDagLayout(["op1"]);
    expect(layout.nodeW).toBe(140);
    expect(layout.nodeH).toBe(56);
    const opNode = layout.nodes.find((n) => n.id === "op1-operator")!;
    expect(opNode.w).toBe(140);
    expect(opNode.h).toBe(56);
  });

  it("uses medium sizing tier for 3-6 operators", () => {
    const layout = computeDagLayout(["a", "b", "c", "d"]);
    expect(layout.nodeW).toBe(130);
    expect(layout.nodeH).toBe(46);
  });

  it("uses compact sizing tier for 7+ operators", () => {
    const ops = Array.from({ length: 7 }, (_, i) => `op${i}`);
    const layout = computeDagLayout(ops);
    expect(layout.nodeW).toBe(110);
    expect(layout.nodeH).toBe(38);
  });

  it("totalHeight equals raw content height (no artificial minimum)", () => {
    const layout = computeDagLayout(["op1"]);
    // n=1: single row height = nodeH (56), merge/filter height = 68, max = 68
    expect(layout.totalHeight).toBe(68);
  });

  it("different tier counts produce different node sizes", () => {
    const layout1 = computeDagLayout(["op1"]);
    const layout7 = computeDagLayout(Array.from({ length: 7 }, (_, i) => `op${i}`));
    expect(layout1.nodeW).toBeGreaterThan(layout7.nodeW);
    expect(layout1.nodeH).toBeGreaterThan(layout7.nodeH);
  });

  it("no overlapping nodes with many operators (11)", () => {
    const ops = Array.from({ length: 11 }, (_, i) => `op${i}`);
    const layout = computeDagLayout(ops);
    for (let i = 0; i < layout.nodes.length; i++) {
      for (let j = i + 1; j < layout.nodes.length; j++) {
        const a = layout.nodes[i];
        const b = layout.nodes[j];
        const overlapX = a.x < b.x + b.w && a.x + a.w > b.x;
        const overlapY = a.y < b.y + b.h && a.y + a.h > b.y;
        if (overlapX && overlapY) {
          throw new Error(`Nodes ${a.id} and ${b.id} overlap`);
        }
      }
    }
  });

  // ── Total width fits in typical canvas widths ──

  it("totalWidth for 1 operator fits in canvas (<1200px)", () => {
    const layout = computeDagLayout(["op1"]);
    // n≤2: 4×140 + 120 + 120 + 100 + 6×28 = 1048
    expect(layout.totalWidth).toBeLessThanOrEqual(1200);
  });

  it("totalWidth for 3 operators fits in medium canvas (<1100px)", () => {
    const layout = computeDagLayout(["a", "b", "c"]);
    // n≤6: 4×130 + 110 + 110 + 90 + 6×28 = 998
    expect(layout.totalWidth).toBeLessThanOrEqual(1100);
  });

  it("totalWidth for 11 operators fits in small canvas (<1000px)", () => {
    const ops = Array.from({ length: 11 }, (_, i) => `op${i}`);
    const layout = computeDagLayout(ops);
    // n>6: 4×110 + 100 + 100 + 80 + 6×24 = 864
    expect(layout.totalWidth).toBeLessThanOrEqual(1000);
  });
});
