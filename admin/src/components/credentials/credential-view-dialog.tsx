"use client";

import {
  Loader2,
  Pencil,
  RefreshCw,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MetadataField } from "@/components/shared/metadata-field";
import { StatusBadge } from "@/components/shared/status-badge";
import type { ValidationStatus } from "@/components/shared/status-badge";
import { useValidateCredential } from "@/hooks/use-validate-credential";
import type { Credential } from "@/types/credential";

interface CredentialViewDialogProps {
  open: boolean;
  onClose: () => void;
  onEdit: () => void;
  credential: Credential;
}

export function CredentialViewDialog({ open, onClose, onEdit, credential }: CredentialViewDialogProps) {
  const t = useTranslations();
  const validateCredential = useValidateCredential();
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>("idle");

  const handleVerify = () => {
    setValidationStatus("checking");
    validateCredential.mutate(credential.id, {
      onSuccess: (result) => {
        setValidationStatus(result.valid ? "valid" : "invalid");
      },
      onError: () => {
        setValidationStatus("error");
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("credentials.detail_title")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--text-secondary)]">
              {t("credentials.col_username")}
            </label>
            <p className="text-sm font-mono font-medium text-[var(--text-primary)] break-all">{credential.username}</p>
          </div>

          <div className="rounded-[var(--radius-input)] bg-[rgba(120,120,128,0.06)] p-4 space-y-3">
            <p className="text-xs font-medium text-[var(--text-secondary)]">
              {t("credentials.sisreg_info")}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
              <MetadataField label={t("credentials.col_profile")} value={credential.profileName ?? "—"} />
              <MetadataField
                label={t("credentials.col_state")}
                value={`${credential.state}${credential.stateName ? ` — ${credential.stateName}` : ""}`}
              />
              {credential.unitCnes && (
                <MetadataField label={t("common.cnes")} value={credential.unitCnes} />
              )}
              {credential.unitName && (
                <MetadataField label={t("credentials.col_unit")} value={credential.unitName} />
              )}
            </div>
          </div>

          <div className="rounded-[var(--radius-input)] border border-[var(--glass-border-subtle)] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-[var(--text-secondary)]">
                {t("credentials.validation_section")}
              </p>
              <StatusBadge
                status={validationStatus}
                labels={{
                  notVerified: t("credentials.not_verified"),
                  verifying: t("credentials.verifying"),
                  valid: t("credentials.credential_valid"),
                  invalid: t("credentials.credential_invalid"),
                  error: t("credentials.credential_error"),
                }}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleVerify}
              disabled={validationStatus === "checking"}
            >
              {validationStatus === "checking" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              {t("credentials.verify_credential")}
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.close")}
          </Button>
          <Button variant="secondary" onClick={onEdit}>
            <Pencil className="mr-2 h-4 w-4" />
            {t("credentials.edit_button")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
