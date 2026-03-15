const MODULE_PREFIXES = {
  credentials: "RH-CRED",
  profile: "RH-PROF",
  general: "RH-GEN",
} as const;

type ErrorModule = keyof typeof MODULE_PREFIXES;

const counters: Record<string, number> = {};

export function getErrorCode(module: ErrorModule, seq?: number): string {
  const prefix = MODULE_PREFIXES[module];
  if (seq !== undefined) {
    return `${prefix}-${String(seq).padStart(3, "0")}`;
  }
  const key = prefix;
  counters[key] = (counters[key] ?? 0) + 1;
  return `${prefix}-${String(counters[key]).padStart(3, "0")}`;
}

export const ERROR_CODES = {
  CRED_LIST_FAILED: getErrorCode("credentials", 1),
  CRED_CREATE_FAILED: getErrorCode("credentials", 2),
  CRED_DELETE_FAILED: getErrorCode("credentials", 3),
  CRED_UPDATE_FAILED: getErrorCode("credentials", 4),
  CRED_VALIDATE_FAILED: getErrorCode("credentials", 5),
  PROF_LIST_FAILED: getErrorCode("profile", 1),
  PROF_USER_LIST_FAILED: getErrorCode("profile", 2),
  GEN_UNEXPECTED: getErrorCode("general", 1),
  GEN_NETWORK: getErrorCode("general", 2),
} as const;

export function formatErrorMessage(code: string, message: string): string {
  return `${code}: ${message}`;
}
