import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "fs";
import { join, extname } from "path";

const LOCALES_DIR = join(__dirname, "../../public/locales");
const SRC_DIR = join(__dirname, "../../src");

function loadLocale(lang: string): Record<string, string> {
  const raw = readFileSync(join(LOCALES_DIR, `${lang}.json`), "utf-8");
  return JSON.parse(raw);
}

function walkDir(dir: string, exts: string[]): string[] {
  const results: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      results.push(...walkDir(full, exts));
    } else if (exts.includes(extname(full))) {
      results.push(full);
    }
  }
  return results;
}

function extractI18nKeysFromSource(): Set<string> {
  const keys = new Set<string>();
  const files = walkDir(SRC_DIR, [".ts", ".tsx"]);

  // Match t("key"), t('key'), t(`key`), and labelKey: "key" patterns
  const patterns = [
    /\bt\(\s*["'`]([a-zA-Z_][a-zA-Z0-9_.]+)["'`]\s*\)/g,
    /labelKey:\s*["']([a-zA-Z_][a-zA-Z0-9_.]+)["']/g,
  ];

  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    // Strip block comments (/* ... */) and line comments (// ...)
    const stripped = content
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/.*$/gm, "");
    for (const pattern of patterns) {
      pattern.lastIndex = 0;
      let match;
      while ((match = pattern.exec(stripped)) !== null) {
        keys.add(match[1]);
      }
    }
  }

  return keys;
}

describe("i18n key integrity", () => {
  const locales = readdirSync(LOCALES_DIR)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(".json", ""));

  const localeData: Record<string, Record<string, string>> = {};
  for (const lang of locales) {
    localeData[lang] = loadLocale(lang);
  }

  const ptBR = localeData["pt-BR"]!;
  const keysInCode = extractI18nKeysFromSource();

  it("has at least pt-BR, en-US, and es-AR locales", () => {
    expect(locales).toContain("pt-BR");
    expect(locales).toContain("en-US");
    expect(locales).toContain("es-AR");
  });

  it("all locale files have the same keys", () => {
    const ptKeys = Object.keys(ptBR).sort();

    for (const lang of locales) {
      if (lang === "pt-BR") continue;
      const langKeys = Object.keys(localeData[lang]!).sort();
      const missingInLang = ptKeys.filter((k) => !langKeys.includes(k));
      const extraInLang = langKeys.filter((k) => !ptKeys.includes(k));

      expect(missingInLang, `Keys in pt-BR but missing in ${lang}`).toEqual([]);
      expect(extraInLang, `Keys in ${lang} but missing in pt-BR`).toEqual([]);
    }
  });

  it("every i18n key used in source code exists in all locales", () => {
    const localeKeys = new Set(Object.keys(ptBR));

    // Filter to keys that look like i18n (contain a dot separator)
    const i18nKeys = [...keysInCode].filter((k) => k.includes("."));

    const missing: string[] = [];
    for (const key of i18nKeys) {
      if (!localeKeys.has(key)) {
        missing.push(key);
      }
    }

    expect(missing, "i18n keys used in code but missing from locale files").toEqual([]);
  });

  it("no locale value is empty", () => {
    for (const lang of locales) {
      const emptyKeys = Object.entries(localeData[lang]!)
        .filter(([, v]) => v.trim() === "")
        .map(([k]) => k);

      expect(emptyKeys, `Empty values in ${lang}`).toEqual([]);
    }
  });
});
