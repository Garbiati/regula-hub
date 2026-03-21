import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useValidateCredential } from "@/hooks/use-validate-credential";

import { createWrapper } from "./hook-test-utils";

describe("useValidateCredential", () => {
  it("validates a credential by id", async () => {
    const { result } = renderHook(() => useValidateCredential(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate("cred-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.valid).toBe(true);
    expect(result.current.data?.username).toBe("op1");
  });
});
