"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Toaster } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { IntegrationSystemCards } from "@/components/integrations/integration-system-cards";
import { IntegrationTriggerForm } from "@/components/integrations/integration-trigger-form";
import { IntegrationExecutionStatus } from "@/components/integrations/integration-execution-status";
import { IntegrationExecutionHistory } from "@/components/integrations/integration-execution-history";

export default function SisregIntegrationsPage() {
  const t = useTranslations();
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader title={t("nav.sisreg_integrations")} />

      <div className="animate-fadeInUp-2">
        <IntegrationSystemCards />
      </div>

      <div className="animate-fadeInUp-3">
        <IntegrationTriggerForm onExecutionStarted={setActiveExecutionId} />
      </div>

      {activeExecutionId && (
        <div className="animate-fadeInUp-4">
          <IntegrationExecutionStatus executionId={activeExecutionId} />
        </div>
      )}

      <div className="animate-fadeInUp-5">
        <IntegrationExecutionHistory />
      </div>

      <Toaster />
    </div>
  );
}
