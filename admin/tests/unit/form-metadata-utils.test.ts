import { describe, expect, it } from "vitest";
import { filterSituationsBySearchType, resolveLabel } from "@/lib/form-metadata-utils";
import type { FormOptionItem } from "@/types/form-metadata";

describe("resolveLabel", () => {
  const mockT = (key: string) => {
    const translations: Record<string, string> = {
      "consulta.sit_sol_scheduled": "Scheduled",
      "consulta.items_all": "ALL",
    };
    return translations[key] ?? key;
  };

  it("returns translated label when labelKey resolves", () => {
    const option: FormOptionItem = {
      value: "7",
      labelKey: "consulta.sit_sol_scheduled",
      canonicalLabel: "Solicitação / Agendada",
    };
    expect(resolveLabel(mockT, option)).toBe("Scheduled");
  });

  it("falls back to canonicalLabel when labelKey does not resolve", () => {
    const option: FormOptionItem = {
      value: "99",
      labelKey: "consulta.unknown_key",
      canonicalLabel: "Fallback Label",
    };
    expect(resolveLabel(mockT, option)).toBe("Fallback Label");
  });

  it("falls back to label when no labelKey or canonicalLabel", () => {
    const option: FormOptionItem = { value: "20", label: "20" };
    expect(resolveLabel(mockT, option)).toBe("20");
  });

  it("falls back to value when nothing else is available", () => {
    const option: FormOptionItem = { value: "50" };
    expect(resolveLabel(mockT, option)).toBe("50");
  });

  it("prefers labelKey over canonicalLabel when both resolve", () => {
    const option: FormOptionItem = {
      value: "0",
      labelKey: "consulta.items_all",
      canonicalLabel: "TODOS",
    };
    expect(resolveLabel(mockT, option)).toBe("ALL");
  });
});

describe("filterSituationsBySearchType", () => {
  const situations: FormOptionItem[] = [
    { value: "1", appliesTo: ["solicitacao"] },
    { value: "7", appliesTo: ["solicitacao", "agendamento", "execucao"] },
    { value: "11", appliesTo: ["solicitacao", "agendamento", "execucao", "confirmacao"] },
    { value: "99" }, // no appliesTo — included in all
  ];

  it("filters to solicitacao", () => {
    const result = filterSituationsBySearchType(situations, "solicitacao");
    expect(result.map((s) => s.value)).toEqual(["1", "7", "11", "99"]);
  });

  it("filters to agendamento", () => {
    const result = filterSituationsBySearchType(situations, "agendamento");
    expect(result.map((s) => s.value)).toEqual(["7", "11", "99"]);
  });

  it("filters to confirmacao", () => {
    const result = filterSituationsBySearchType(situations, "confirmacao");
    expect(result.map((s) => s.value)).toEqual(["11", "99"]);
  });

  it("includes items without appliesTo in any search type", () => {
    const result = filterSituationsBySearchType(situations, "unknown_type");
    expect(result.map((s) => s.value)).toEqual(["99"]);
  });

  it("returns empty array for empty input", () => {
    expect(filterSituationsBySearchType([], "solicitacao")).toEqual([]);
  });
});
