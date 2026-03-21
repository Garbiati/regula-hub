"use client";

import {
  Loader2,
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
import { Input } from "@/components/ui/input";
import { MetadataField } from "@/components/shared/metadata-field";
import { ValidationResult } from "@/components/shared/validation-result";
import { useUpdateCredential } from "@/hooks/use-credential-mutations";
import { useValidateLogin } from "@/hooks/use-validate-login";
import type { Credential } from "@/types/credential";

interface CredentialEditDialogProps {
  open: boolean;
  onClose: () => void;
  credential: Credential;
}

export function CredentialEditDialog({ open, onClose, credential }: CredentialEditDialogProps) {
  const t = useTranslations();
  const updateMutation = useUpdateCredential();
  const validateLogin = useValidateLogin();

  const [username, setUsername] = useState(credential.username);
  const [password, setPassword] = useState("");
  const [editValidated, setEditValidated] = useState(false);
  const [editMetadata, setEditMetadata] = useState<{
    profileName: string | null;
    state: string | null;
    stateName: string | null;
    unitCnes: string | null;
    unitName: string | null;
  } | null>(null);

  const handleValidateEdit = () => {
    if (!username || !password) return;
    validateLogin.mutate(
      { username, password },
      {
        onSuccess: (result) => {
          if (result.valid) {
            setEditValidated(true);
            setEditMetadata({
              profileName: result.profileType,
              state: result.state,
              stateName: result.stateName,
              unitCnes: result.unitCnes,
              unitName: result.unitName,
            });
          } else {
            setEditValidated(false);
            setEditMetadata(null);
          }
        },
      },
    );
  };

  const handleSave = () => {
    const data: Record<string, string> = {};
    if (username !== credential.username) data.username = username;
    if (password) data.password = password;
    if (editMetadata?.profileName && editMetadata.profileName !== credential.profileName) {
      // TODO: resolve profile_id from profileName via profiles endpoint
      data.profile_id = editMetadata.profileName;
    }
    if (editMetadata?.state && editMetadata.state !== credential.state) {
      data.state = editMetadata.state;
      data.state_name = editMetadata.stateName ?? "";
    }
    if (editMetadata?.unitName && editMetadata.unitName !== credential.unitName) {
      data.unit_name = editMetadata.unitName;
    }
    if (editMetadata?.unitCnes && editMetadata.unitCnes !== credential.unitCnes) {
      data.unit_cnes = editMetadata.unitCnes;
    }
    updateMutation.mutate(
      { id: credential.id, data },
      { onSuccess: onClose },
    );
  };

  const displayProfile = editMetadata?.profileName ?? credential.profileName;
  const displayState = editMetadata?.state ?? credential.state;
  const displayStateName = editMetadata?.stateName ?? credential.stateName;
  const displayUnitCnes = editMetadata?.unitCnes ?? credential.unitCnes;
  const displayUnitName = editMetadata?.unitName ?? credential.unitName;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("credentials.edit_title")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                {t("credentials.col_username")}
              </label>
              <Input
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  setEditValidated(false);
                }}
                autoComplete="off"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">
                {t("credentials.new_password")}
              </label>
              <Input
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setEditValidated(false);
                }}
                autoComplete="new-password"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleValidateEdit}
                disabled={!username || !password || validateLogin.isPending}
              >
                {validateLogin.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                {t("credentials.validate_changes")}
              </Button>
              {validateLogin.data && (
                <ValidationResult
                  valid={validateLogin.data.valid}
                  validLabel={t("credentials.login_valid")}
                  invalidLabel={t("credentials.login_invalid")}
                />
              )}
            </div>
          </div>

          <div className="rounded-[var(--radius-input)] bg-[rgba(120,120,128,0.06)] p-4 space-y-3">
            <p className="text-xs font-medium text-[var(--text-secondary)]">
              {t("credentials.sisreg_info")}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
              <MetadataField label={t("credentials.col_profile")} value={displayProfile ?? "—"} />
              <MetadataField
                label={t("credentials.col_state")}
                value={`${displayState}${displayStateName ? ` — ${displayStateName}` : ""}`}
              />
              {displayUnitCnes && (
                <MetadataField label={t("common.cnes")} value={displayUnitCnes} />
              )}
              {displayUnitName && (
                <MetadataField label={t("credentials.col_unit")} value={displayUnitName} />
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleSave}
            disabled={!editValidated || updateMutation.isPending}
          >
            {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("credentials.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
