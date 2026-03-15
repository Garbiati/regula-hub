// Route segment → system code
export const ROUTE_SYSTEM_MAP: Record<string, string> = {
  sisreg: "SISREG",
  "esus-regulacao": "ESUS",
  "siga-saude": "SIGA",
  "care-parana": "CARE",
  "ser-rj": "SER",
};

// ── Sidebar ──────────────────────────────────────────────────────────

export const SIDEBAR_ITEMS = [
  { labelKey: "nav.dashboard", path: "/", icon: "LayoutDashboard" },
  { labelKey: "nav.credentials_page", path: "/credentials", icon: "KeyRound" },
  { labelKey: "nav.settings", path: "/settings", icon: "Settings" },
] as const;

// System-specific pages — shown in sidebar for the active system only
// Route segment, i18n keys for label and children
const SYSTEM_META: Record<string, { route: string; navKey: string; childKey: string }> = {
  SISREG: { route: "sisreg", navKey: "sisreg", childKey: "sisreg" },
  ESUS: { route: "esus-regulacao", navKey: "esus_regulacao", childKey: "esus" },
  SIGA: { route: "siga-saude", navKey: "siga_saude", childKey: "siga" },
  CARE: { route: "care-parana", navKey: "care_parana", childKey: "care" },
  SER: { route: "ser-rj", navKey: "ser_rj", childKey: "ser" },
};

function systemChildren(code: string): { labelKey: string; path: string; icon: string }[] {
  const meta = SYSTEM_META[code];
  if (!meta) return [];
  const children = [
    { labelKey: `nav.${meta.childKey}_consulta`, path: `/${meta.route}/consulta`, icon: "Search" },
  ];
  if (code === "SISREG") {
    children.push({
      labelKey: "nav.sisreg_agendamentos",
      path: `/${meta.route}/agendamentos`,
      icon: "Calendar",
    });
  }
  return children;
}

export const SYSTEM_PAGES: Record<
  string,
  { labelKey: string; icon: string; children: { labelKey: string; path: string; icon: string }[] }
> = {
  SISREG: {
    labelKey: "nav.sisreg",
    icon: "Monitor",
    children: systemChildren("SISREG"),
  },
  ESUS: {
    labelKey: "nav.esus_regulacao",
    icon: "ArrowLeftRight",
    children: systemChildren("ESUS"),
  },
  SIGA: {
    labelKey: "nav.siga_saude",
    icon: "Hospital",
    children: systemChildren("SIGA"),
  },
  CARE: {
    labelKey: "nav.care_parana",
    icon: "Heart",
    children: systemChildren("CARE"),
  },
  SER: {
    labelKey: "nav.ser_rj",
    icon: "Landmark",
    children: systemChildren("SER"),
  },
};

// All system codes (for rendering tabs) — static fallback
export const ALL_SYSTEMS = ["SISREG", "ESUS", "SIGA", "CARE", "SER"] as const;

// Display labels for system codes — static fallback
export const SYSTEM_LABELS: Record<string, string> = {
  SISREG: "SisReg",
  ESUS: "e-SUS Regulação",
  SIGA: "SIGA Saúde",
  CARE: "Care Paraná",
  SER: "SER (RJ)",
};

// ── Dynamic helpers (from API data) ─────────────────────────────────

import type { RegulationSystem } from "@/types/regulation-system";

export interface SystemPageConfig {
  labelKey: string;
  icon: string;
  children: { labelKey: string; path: string; icon: string }[];
}

export function buildSystemLabels(systems: RegulationSystem[]): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const s of systems) {
    labels[s.code] = s.name;
  }
  return labels;
}

export function buildSystemPages(systems: RegulationSystem[]): Record<string, SystemPageConfig> {
  const pages: Record<string, SystemPageConfig> = {};
  for (const s of systems) {
    if (!s.routeSegment) continue;
    const meta = SYSTEM_META[s.code];
    const navKey = meta?.navKey ?? s.routeSegment.replace(/-/g, "_");
    const childKey = meta?.childKey ?? s.code.toLowerCase();
    const pageChildren = [
      { labelKey: `nav.${childKey}_consulta`, path: `/${s.routeSegment}/consulta`, icon: "Search" },
    ];
    if (s.code === "SISREG") {
      pageChildren.push({
        labelKey: "nav.sisreg_agendamentos",
        path: `/${s.routeSegment}/agendamentos`,
        icon: "Calendar",
      });
    }
    pages[s.code] = {
      labelKey: `nav.${navKey}`,
      icon: s.icon ?? "Circle",
      children: pageChildren,
    };
  }
  return pages;
}
