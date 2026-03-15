/**
 * Converts flat dot-notation message keys to nested objects.
 *
 * next-intl resolves t("appt.title") as messages.appt.title (nested),
 * but our JSON files use flat keys: { "appt.title": "Appointments" }.
 * This function bridges the gap.
 */
export function flatToNested(flat: Record<string, string>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split(".");
    let current = result;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i]!;
      if (!(part in current) || typeof current[part] !== "object") {
        current[part] = {};
      }
      current = current[part] as Record<string, unknown>;
    }
    current[parts[parts.length - 1]!] = value;
  }
  return result;
}
