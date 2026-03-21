"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Toaster } from "sonner";

import { CredentialFormDialog } from "@/components/credentials/credential-form-dialog";
import { SystemTabs } from "@/components/credentials/system-tabs";
import { UnifiedCredentialsSection } from "@/components/credentials/unified-credentials-section";
import { ProfileSelector } from "@/components/profile-settings/profile-selector";
import { Button } from "@/components/ui/button";
import { useProfileStore } from "@/stores/profile-store";

export default function CredentialsPage() {
  const t = useTranslations();
  const system = useProfileStore((s) => s.system);
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("nav.credentials_page")}</h1>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("credentials.add_button")}
        </Button>
      </div>

      <SystemTabs />
      <ProfileSelector />
      <UnifiedCredentialsSection />

      {showCreate && (
        <CredentialFormDialog open onClose={() => setShowCreate(false)} system={system} />
      )}
      <Toaster />
    </div>
  );
}
