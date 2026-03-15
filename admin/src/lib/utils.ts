import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

function snakeToCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

export function deduplicateByCode<T extends { code: string }>(items: T[]): T[] {
  const seen = new Set<string>();
  const result: T[] = [];
  for (const item of items) {
    if (!seen.has(item.code)) {
      seen.add(item.code);
      result.push(item);
    }
  }
  return result;
}

export function camelizeKeys<T>(obj: unknown): T {
  if (Array.isArray(obj)) return obj.map((item) => camelizeKeys(item)) as T;
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [snakeToCamel(k), camelizeKeys(v)]),
    ) as T;
  }
  return obj as T;
}

function camelToSnake(s: string): string {
  return s.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

export function snakelizeKeys<T>(obj: unknown): T {
  if (Array.isArray(obj)) return obj.map((item) => snakelizeKeys(item)) as T;
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [camelToSnake(k), snakelizeKeys(v)]),
    ) as T;
  }
  return obj as T;
}
