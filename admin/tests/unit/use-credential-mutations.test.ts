import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { useCreateCredential, useUpdateCredential, useDeleteCredential } from "@/hooks/use-credential-mutations";

import { server } from "../mocks/server";

import { createWrapper } from "./hook-test-utils";

const BASE = "http://localhost:8000";

describe("useCreateCredential", () => {
  it("creates a credential and resolves", async () => {
    const { result } = renderHook(() => useCreateCredential(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({
        username: "new-user",
        password: "pass123",
        profile_type: "videofonista",
        system: "SISREG",
        state: "AM",
        state_name: "Amazonas",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("handles create error", async () => {
    server.use(
      http.post(`${BASE}/api/admin/credentials`, () => {
        return HttpResponse.json({ detail: "Duplicate" }, { status: 409 });
      }),
    );

    const { result } = renderHook(() => useCreateCredential(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({
        username: "dup-user",
        password: "pass",
        profile_type: "videofonista",
        system: "SISREG",
        state: "AM",
        state_name: "Amazonas",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateCredential", () => {
  it("updates a credential", async () => {
    const { result } = renderHook(() => useUpdateCredential(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: "cred-1", data: { username: "updated-user" } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useDeleteCredential", () => {
  it("deletes a credential", async () => {
    const { result } = renderHook(() => useDeleteCredential(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate("cred-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
