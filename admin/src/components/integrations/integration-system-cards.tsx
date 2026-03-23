"use client";

import { useTranslations } from "next-intl";
import { Globe, Plug, Loader2 } from "lucide-react";

import { useIntegrationSystems } from "@/hooks/use-integration-systems";
import type { IntegrationSystem } from "@/types/integration";

function EndpointBadge({ method, path }: { method: string | null; path: string }) {
  const methodColors: Record<string, string> = {
    GET: "bg-emerald-500/10 text-emerald-400",
    POST: "bg-blue-500/10 text-blue-400",
    PUT: "bg-amber-500/10 text-amber-400",
    DELETE: "bg-red-500/10 text-red-400",
  };
  const color = methodColors[(method || "GET").toUpperCase()] ?? "bg-gray-500/10 text-gray-400";

  return (
    <div className="flex items-center gap-2 text-xs font-mono">
      <span className={`px-1.5 py-0.5 rounded ${color} font-semibold`}>{method || "GET"}</span>
      <span className="text-[var(--text-tertiary)]">{path}</span>
    </div>
  );
}

function SystemCard({ system }: { system: IntegrationSystem }) {
  const t = useTranslations();
  return (
    <div className="glass-card rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-[var(--accent-indigo-bg)]">
          <Globe className="w-5 h-5 text-[var(--accent-indigo)]" />
        </div>
        <div>
          <h3 className="font-semibold text-[var(--text-primary)]">{system.name}</h3>
          <p className="text-xs text-[var(--text-tertiary)]">{system.code}</p>
        </div>
      </div>

      {system.baseUrl && (
        <p className="text-xs text-[var(--text-secondary)] font-mono truncate">{system.baseUrl}</p>
      )}

      {system.endpoints.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            {t("integrations.endpoints_title")} ({system.endpoints.length})
          </p>
          {system.endpoints.map((ep) => (
            <EndpointBadge key={ep.id} method={ep.httpMethod} path={ep.path} />
          ))}
        </div>
      )}
    </div>
  );
}

export function IntegrationSystemCards() {
  const { data, isLoading, isError } = useIntegrationSystems();
  const t = useTranslations();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-[var(--text-tertiary)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        {t("integrations.loading")}
      </div>
    );
  }

  if (isError || !data?.items?.length) {
    return (
      <div className="glass-card rounded-xl p-6 text-center">
        <Plug className="w-8 h-8 mx-auto mb-2 text-[var(--text-tertiary)]" />
        <p className="text-[var(--text-secondary)]">{t("integrations.no_systems")}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.items.map((system) => (
        <SystemCard key={system.id} system={system} />
      ))}
    </div>
  );
}
