import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "./mocks/server";

beforeAll(() => {
  server.listen({ onUnhandledRequest: "warn" });
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
  localStorage.clear();

  // Reset Zustand persisted state
  const profileKey = "regulahub-profile";
  localStorage.removeItem(profileKey);
});

afterAll(() => {
  server.close();
});

// Mock navigator.clipboard (not available in jsdom)
Object.defineProperty(navigator, "clipboard", {
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
    readText: vi.fn().mockResolvedValue(""),
  },
  writable: true,
});
