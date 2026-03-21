import { describe, expect, it } from "vitest";

import { SIDEBAR_ITEMS, SYSTEM_PAGES, ALL_SYSTEMS } from "@/lib/constants";

describe("constants", () => {
  describe("SIDEBAR_ITEMS", () => {
    it("has dashboard, credentials and settings entries", () => {
      const paths = SIDEBAR_ITEMS.map((i) => i.path);
      expect(paths).toContain("/");
      expect(paths).toContain("/credentials");
      expect(paths).toContain("/settings");
    });

    it("has exactly 3 items", () => {
      expect(SIDEBAR_ITEMS).toHaveLength(3);
    });
  });

  describe("SYSTEM_PAGES", () => {
    it("has entries for all systems", () => {
      for (const sys of ALL_SYSTEMS) {
        expect(SYSTEM_PAGES[sys]).toBeDefined();
        expect(SYSTEM_PAGES[sys].children).toBeDefined();
      }
    });
  });
});
