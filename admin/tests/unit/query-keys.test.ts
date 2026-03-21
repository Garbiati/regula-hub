import { describe, expect, it } from "vitest";

import { queryKeys } from "@/lib/query-keys";

describe("queryKeys", () => {
  it("admin credentials keys are namespaced correctly", () => {
    expect(queryKeys.admin.credentials.all).toEqual(["admin", "credentials"]);
    expect(queryKeys.admin.credentials.list("SISREG")).toEqual(["admin", "credentials", "list", "SISREG"]);
    expect(queryKeys.admin.credentials.states("SISREG")).toEqual(["admin", "credentials", "states", "SISREG"]);
    expect(queryKeys.admin.credentials.profiles("SISREG")).toEqual(["admin", "credentials", "profiles", "SISREG"]);
    expect(queryKeys.admin.credentials.byProfile("SISREG", "videofonista")).toEqual([
      "admin",
      "credentials",
      "byProfile",
      "SISREG",
      "videofonista",
    ]);
  });

  it("health key is static", () => {
    expect(queryKeys.health).toEqual(["health"]);
  });

  it("credential list keys with different systems are different", () => {
    const key1 = queryKeys.admin.credentials.list("SISREG");
    const key2 = queryKeys.admin.credentials.list("ESUS");
    expect(key1).not.toEqual(key2);
  });
});
