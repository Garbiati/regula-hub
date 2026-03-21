import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useCredentials } from "@/hooks/use-credentials";

import { createWrapper } from "./hook-test-utils";

describe("useCredentials", () => {
  it("fetches credentials for a given system", async () => {
    const { result } = renderHook(() => useCredentials("SISREG"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.total).toBe(2);
  });

  it("returns loading state initially", () => {
    const { result } = renderHook(() => useCredentials("SISREG"), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
  });
});
