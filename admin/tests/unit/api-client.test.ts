import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-error";

// We need a fresh module for each test since apiClient is a singleton
// that reads env at construction time. The vitest.config env vars handle that.

describe("ApiClient", () => {
  let apiClient: typeof import("@/lib/api-client").apiClient;

  beforeEach(async () => {
    vi.restoreAllMocks();
    // Dynamic import to get the singleton that was constructed with test env vars
    const mod = await import("@/lib/api-client");
    apiClient = mod.apiClient;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("get()", () => {
    it("builds URL and sends X-API-Key header", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: "test" }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const result = await apiClient.get("/test/endpoint");

      expect(mockFetch).toHaveBeenCalledOnce();
      const [url, options] = mockFetch.mock.calls[0]!;
      expect(url).toBe("http://localhost:8000/test/endpoint");
      expect(options.method).toBe("GET");
      expect(options.headers["X-API-Key"]).toBe("test-api-key");
      expect(result).toEqual({ data: "test" });
    });

    it("appends query params and filters undefined values", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      });
      vi.stubGlobal("fetch", mockFetch);

      await apiClient.get("/search", { date: "2026-03-12", status: undefined, q: "" });

      const [url] = mockFetch.mock.calls[0]!;
      expect(url).toContain("date=2026-03-12");
      expect(url).not.toContain("status");
      expect(url).not.toContain("q=");
    });
  });

  describe("post()", () => {
    it("sends JSON body", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: "123" }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const result = await apiClient.post("/sync/trigger", { date: "2026-03-12" });

      const [, options] = mockFetch.mock.calls[0]!;
      expect(options.method).toBe("POST");
      expect(options.body).toBe(JSON.stringify({ date: "2026-03-12" }));
      expect(result).toEqual({ id: "123" });
    });
  });

  describe("getBlob()", () => {
    it("returns a Blob", async () => {
      const blob = new Blob(["pdf-content"], { type: "application/pdf" });
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(blob),
      });
      vi.stubGlobal("fetch", mockFetch);

      const result = await apiClient.getBlob("/export/pdf");

      expect(result).toBe(blob);
      const [, options] = mockFetch.mock.calls[0]!;
      // getBlob should NOT send Content-Type header
      expect(options.headers["Content-Type"]).toBeUndefined();
    });
  });

  describe("error handling", () => {
    it("throws ApiError with status and detail for non-OK response", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Not found" }),
      });
      vi.stubGlobal("fetch", mockFetch);

      await expect(apiClient.get("/missing")).rejects.toThrow(ApiError);

      try {
        await apiClient.get("/missing");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).status).toBe(404);
        expect((err as ApiError).detail).toBe("Not found");
      }
    });

    it("throws ApiError even when response body parse fails", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("invalid json")),
      });
      vi.stubGlobal("fetch", mockFetch);

      await expect(apiClient.get("/broken")).rejects.toThrow(ApiError);

      try {
        await apiClient.get("/broken");
      } catch (err) {
        expect((err as ApiError).status).toBe(500);
        expect((err as ApiError).detail).toBeUndefined();
      }
    });
  });
});
