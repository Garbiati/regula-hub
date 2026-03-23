"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Globe, Plug, Loader2, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useIntegrationSystems } from "@/hooks/use-integration-systems";
import type { IntegrationSystem } from "@/types/integration";

function EndpointBadge({ method, path, name }: { method: string | null; path: string; name: string }) {
  const methodColors: Record<string, string> = {
    GET: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    POST: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    PUT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    DELETE: "bg-red-500/10 text-red-400 border-red-500/20",
  };
  const color = methodColors[(method || "GET").toUpperCase()] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20";

  return (
    <div className="flex items-center gap-2 py-1.5 px-2 rounded-lg bg-[var(--bg-secondary)]/50 hover:bg-[var(--bg-secondary)] transition-colors">
      <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${color}`}>
        {method || "GET"}
      </span>
      <span className="text-xs text-[var(--text-secondary)] truncate">{name}</span>
      <span className="text-[10px] text-[var(--text-tertiary)] font-mono truncate ml-auto hidden sm:block">{path}</span>
    </div>
  );
}

function SystemCard({ system }: { system: IntegrationSystem }) {
  const t = useTranslations();
  const [expanded, setExpanded] = useState(false);
  const activeEndpoints = system.endpoints.filter((ep) => ep.isActive);

  return (
    <Card className="glass-specular">
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[var(--accent-indigo-bg)] ring-1 ring-[var(--accent-indigo)]/20">
            <Globe className="w-5 h-5 text-[var(--accent-indigo)]" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle>{system.name}</CardTitle>
            <CardDescription>
              <span className="font-mono text-[11px]">{system.code}</span>
              {system.state && (
                <span className="ml-2 text-[11px]">
                  {system.stateName || system.state}
                </span>
              )}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {system.baseUrl && (
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--bg-secondary)]/60">
            <ExternalLink className="w-3 h-3 text-[var(--text-tertiary)] shrink-0" />
            <span className="text-[11px] text-[var(--text-secondary)] font-mono truncate">{system.baseUrl}</span>
          </div>
        )}

        {activeEndpoints.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--accent-indigo)] transition-colors w-full"
            >
              <span className="px-1.5 py-0.5 rounded-full bg-[var(--accent-indigo-bg)] text-[var(--accent-indigo)] text-[10px] font-bold">
                {activeEndpoints.length}
              </span>
              <span>{t("integrations.endpoints_title")}</span>
              {expanded ? (
                <ChevronUp className="w-3.5 h-3.5 ml-auto" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 ml-auto" />
              )}
            </button>

            {expanded && (
              <div className="mt-2 space-y-1">
                {activeEndpoints.map((ep) => (
                  <EndpointBadge key={ep.id} method={ep.httpMethod} path={ep.path} name={ep.name} />
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function IntegrationSystemCards() {
  const { data, isLoading, isError } = useIntegrationSystems();
  const t = useTranslations();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-[var(--text-tertiary)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        {t("integrations.loading")}
      </div>
    );
  }

  if (isError || !data?.items?.length) {
    return (
      <Card className="glass-specular">
        <CardContent className="py-10 text-center">
          <Plug className="w-10 h-10 mx-auto mb-3 text-[var(--text-tertiary)] opacity-50" />
          <p className="text-sm text-[var(--text-secondary)]">{t("integrations.no_systems")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {data.items.map((system) => (
        <SystemCard key={system.id} system={system} />
      ))}
    </div>
  );
}
