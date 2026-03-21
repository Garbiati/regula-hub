import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useRegulationSystems } from "@/hooks/use-regulation-systems";

import { createWrapper } from "./hook-test-utils";

describe("useRegulationSystems", () => {
  it("fetches regulation systems", async () => {
    const { result } = renderHook(() => useRegulationSystems(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(5);
    expect(result.current.data?.total).toBe(5);
    expect(result.current.data?.items[0].code).toBe("SISREG");
  });

  it("returns loading state initially", () => {
    const { result } = renderHook(() => useRegulationSystems(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
  });
});
