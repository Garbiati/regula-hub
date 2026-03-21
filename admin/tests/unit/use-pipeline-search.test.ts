import { describe, expect, it } from "vitest";

import { deduplicateByCode } from "@/lib/utils";
import type { AppointmentListing } from "@/types/appointment";

function makeItem(code: string, patientName = "Patient"): AppointmentListing {
  return {
    code,
    requestDate: "01/01/2026",
    risk: 0,
    patientName,
    phone: "",
    municipality: "",
    age: "",
    procedure: "",
    cid: "",
    deptSolicitation: "",
    deptExecute: "",
    executionDate: "",
    status: "",
  };
}

describe("deduplicateByCode", () => {
  it("removes duplicates by code", () => {
    const items = [makeItem("A"), makeItem("B"), makeItem("A", "Other"), makeItem("C")];
    const result = deduplicateByCode(items);
    expect(result).toHaveLength(3);
    expect(result.map((r) => r.code)).toEqual(["A", "B", "C"]);
  });

  it("preserves first occurrence", () => {
    const items = [makeItem("A", "First"), makeItem("A", "Second")];
    const result = deduplicateByCode(items);
    expect(result).toHaveLength(1);
    expect(result[0].patientName).toBe("First");
  });

  it("returns empty for empty input", () => {
    expect(deduplicateByCode([])).toEqual([]);
  });

  it("returns all items when no duplicates", () => {
    const items = [makeItem("A"), makeItem("B"), makeItem("C")];
    const result = deduplicateByCode(items);
    expect(result).toHaveLength(3);
  });
});
