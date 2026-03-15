export const locales = ["pt-BR", "en-US", "es-AR"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "pt-BR";

export function isValidLocale(value: unknown): value is Locale {
  return typeof value === "string" && (locales as readonly string[]).includes(value);
}

export function getStoredLocale(): Locale {
  if (typeof window === "undefined") return defaultLocale;
  const stored = localStorage.getItem("regulahub-locale");
  return isValidLocale(stored) ? stored : defaultLocale;
}
