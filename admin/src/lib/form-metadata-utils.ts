import type { FormOptionItem } from "@/types/form-metadata";

/**
 * Resolve the display label for a form option, using i18n when available.
 *
 * Priority: translated label_key > canonical_label > label > value
 */
export function resolveLabel(t: (key: string) => string, option: FormOptionItem): string {
  if (option.labelKey) {
    const translated = t(option.labelKey);
    if (translated !== option.labelKey) return translated;
  }
  return option.canonicalLabel ?? option.label ?? option.value;
}

/**
 * Filter situations that apply to the given search type.
 * If a situation has no `appliesTo`, it is included in all types.
 */
export function filterSituationsBySearchType(situations: FormOptionItem[], searchType: string): FormOptionItem[] {
  return situations.filter((s) => !s.appliesTo || s.appliesTo.includes(searchType));
}
