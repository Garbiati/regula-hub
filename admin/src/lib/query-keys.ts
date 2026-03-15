export const queryKeys = {
  admin: {
    credentials: {
      all: ["admin", "credentials"] as const,
      list: (system: string) => ["admin", "credentials", "list", system] as const,
      states: (system: string) => ["admin", "credentials", "states", system] as const,
      profiles: (system: string) => ["admin", "credentials", "profiles", system] as const,
      byProfile: (system: string, profile: string) => ["admin", "credentials", "byProfile", system, profile] as const,
    },
    regulationSystems: {
      list: ["admin", "regulation-systems"] as const,
      profiles: (code: string) => ["admin", "regulation-systems", "profiles", code] as const,
    },
    formMetadata: (system: string, endpoint: string) =>
      ["admin", "form-metadata", system, endpoint] as const,
    users: {
      all: ["admin", "users"] as const,
      selections: (userId: string) => ["admin", "users", "selections", userId] as const,
    },
  },
  sisreg: {
    search: (filters: string) => ["admin", "sisreg", "search", filters] as const,
    searchOperator: (username: string) => ["admin", "sisreg", "search-operator", username] as const,
    detail: (code: string) => ["admin", "sisreg", "detail", code] as const,
    scheduleExport: (filters: string) => ["admin", "sisreg", "schedule-export", filters] as const,
  },
  health: ["health"] as const,
} as const;
