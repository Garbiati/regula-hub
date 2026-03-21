"use client";

import { Loader2 } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MetadataField } from "@/components/shared/metadata-field";
import { ValidationResult } from "@/components/shared/validation-result";
import { useCreateCredential } from "@/hooks/use-credential-mutations";
import { useAvailableProfiles } from "@/hooks/use-available-profiles";
import { useValidateLogin } from "@/hooks/use-validate-login";
import { BRAZILIAN_STATES } from "@/lib/brazilian-states";
import { useProfileStore } from "@/stores/profile-store";

interface CredentialFormDialogProps {
  open: boolean;
  onClose: () => void;
  system: string;
}

export function CredentialFormDialog({ open, onClose, system }: CredentialFormDialogProps) {
  const t = useTranslations();
  const createMutation = useCreateCredential();
  const validateLogin = useValidateLogin();
  const { data: profiles } = useAvailableProfiles();
  const userId = useProfileStore((s) => s.userId);

  const [form, setForm] = useState({
    username: "",
    password: "",
    profile_id: "",
    profile_display: "",
    state: "",
    state_name: "",
    unit_name: "",
    unit_cnes: "",
  });
  const [validated, setValidated] = useState(false);

  const handleSubmit = () => {
    const { profile_display: _display, ...payload } = form;
    createMutation.mutate({ ...payload, user_id: userId ?? "" }, { onSuccess: onClose });
  };

  const handleValidate = () => {
    if (form.username && form.password) {
      setValidated(false);
      validateLogin.mutate(
        { username: form.username, password: form.password },
        {
          onSuccess: (result) => {
            if (result.valid) {
              setValidated(true);
              setForm((prev) => ({
                ...prev,
                ...(result.unitCnes ? { unit_cnes: result.unitCnes } : {}),
                ...(result.unitName ? { unit_name: result.unitName } : {}),
                ...(result.profileType ? { profile_id: result.profileType, profile_display: result.profileType } : {}),
                ...(result.state ? { state: result.state } : {}),
                ...(result.stateName ? { state_name: result.stateName } : {}),
              }));
            }
          },
        },
      );
    }
  };

  const needsProfile = validated && !form.profile_id;
  const needsState = validated && !form.state;
  const isValid = validated && form.username && form.password && form.profile_id && form.state && userId;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("credentials.add_title")}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-primary)]">{t("credentials.col_username")}</label>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                autoComplete="off"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-primary)]">{t("credentials.col_password")}</label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="new-password"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              onClick={handleValidate}
              disabled={!form.username || !form.password || validateLogin.isPending}
            >
              {validateLogin.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("credentials.validate_login")}
            </Button>
            {validateLogin.data && (
              <ValidationResult
                valid={validateLogin.data.valid}
                validLabel={t("credentials.login_valid")}
                invalidLabel={t("credentials.login_invalid")}
              />
            )}
            {!validateLogin.data && !validateLogin.isPending && (
              <span className="text-xs text-[var(--text-tertiary)]">{t("credentials.validate_first")}</span>
            )}
          </div>

          {validated && (
            <>
              <div className="rounded-[var(--radius-input)] bg-[rgba(120,120,128,0.06)] p-4 space-y-3">
                <p className="text-xs font-medium text-[var(--text-secondary)]">{t("credentials.auto_filled")}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
                  {form.profile_display && (
                    <MetadataField label={t("credentials.col_profile")} value={form.profile_display} />
                  )}
                  {form.state && (
                    <MetadataField
                      label={t("credentials.col_state")}
                      value={`${form.state}${form.state_name ? ` — ${form.state_name}` : ""}`}
                    />
                  )}
                  {form.unit_cnes && (
                    <MetadataField label={t("common.cnes")} value={form.unit_cnes} />
                  )}
                  {form.unit_name && (
                    <MetadataField label={t("credentials.col_unit")} value={form.unit_name} />
                  )}
                </div>
              </div>

              {needsProfile && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-primary)]">{t("credentials.col_profile")}</label>
                  <Select value={form.profile_id} onValueChange={(v) => setForm({ ...form, profile_id: v ?? "", profile_display: v ?? "" })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("credentials.select_profile")}>
                        {form.profile_id || undefined}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {(profiles ?? []).map((p) => (
                        <SelectItem key={p} value={p}>{p}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {needsState && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-primary)]">{t("credentials.col_state")}</label>
                  <Select value={form.state} onValueChange={(v) => {
                    const st = BRAZILIAN_STATES.find((s) => s.code === v);
                    setForm({ ...form, state: v ?? "", state_name: st?.name ?? "" });
                  }}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("credentials.select_state")}>
                        {form.state ? (() => {
                          const st = BRAZILIAN_STATES.find((s) => s.code === form.state);
                          return st ? `${st.code} — ${st.name}` : undefined;
                        })() : undefined}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {BRAZILIAN_STATES.map((s) => (
                        <SelectItem key={s.code} value={s.code}>
                          {s.code} — {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("common.close")}</Button>
          <Button onClick={handleSubmit} disabled={createMutation.isPending || !isValid}>
            {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("credentials.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

