"use client";

import { useRegulationSystems } from "@/hooks/use-regulation-systems";
import { ALL_SYSTEMS, buildSystemLabels, SYSTEM_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useProfileStore } from "@/stores/profile-store";

export function SystemTabs() {
  const system = useProfileStore((s) => s.system);
  const setSystem = useProfileStore((s) => s.setSystem);
  const { data } = useRegulationSystems();

  const systems = data?.items.map((s) => s.code) ?? [...ALL_SYSTEMS];
  const labels = data?.items ? buildSystemLabels(data.items) : SYSTEM_LABELS;

  return (
    <div className="flex flex-wrap gap-2">
      {systems.map((sys) => {
        const isActive = system === sys;
        return (
          <button
            key={sys}
            onClick={() => setSystem(sys)}
            className={cn(
              "rounded-full px-4 py-1.5 text-sm font-medium transition-all",
              isActive
                ? "bg-[var(--accent-indigo)] text-white shadow-sm"
                : "bg-[rgba(120,120,128,0.08)] text-[var(--text-secondary)] hover:bg-[rgba(120,120,128,0.16)]",
            )}
          >
            {labels[sys] ?? sys}
          </button>
        );
      })}
    </div>
  );
}
