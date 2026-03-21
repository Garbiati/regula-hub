"use client";

import { useSelectionSync } from "@/hooks/use-selection-sync";

export function SelectionSyncProvider({ children }: { children: React.ReactNode }) {
  useSelectionSync();
  return <>{children}</>;
}
