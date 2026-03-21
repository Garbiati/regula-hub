"use client";

import { Edit, Loader2, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useProfileUsers } from "@/hooks/use-profile-users";
import { useCredentialStates } from "@/hooks/use-credential-states";
import { useValidateBatch } from "@/hooks/use-validate-batch";
import { useProfileStore } from "@/stores/profile-store";
import type { Credential } from "@/types/credential";

import { CredentialEditDialog } from "./credential-edit-dialog";
import { DeleteCredentialDialog } from "./delete-credential-dialog";

function ValidationStatusBadge({ isValid }: { isValid: boolean | null }) {
  const t = useTranslations();
  if (isValid === true) {
    return <Badge className="bg-[var(--status-success)] text-white">{t("settings.status_valid")}</Badge>;
  }
  if (isValid === false) {
    return <Badge className="bg-[var(--status-danger)] text-white">{t("settings.status_invalid")}</Badge>;
  }
  return <Badge variant="outline" className="text-[var(--text-tertiary)]">{t("settings.status_unknown")}</Badge>;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "\u2014";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "\u2014";
  }
}

export function UnifiedCredentialsSection() {
  const t = useTranslations();
  const profile = useProfileStore((s) => s.profile);
  const system = useProfileStore((s) => s.system);
  const selectedUsers = useProfileStore((s) => s.selectedUsers);
  const setSelectedUsers = useProfileStore((s) => s.setSelectedUsers);
  const setState = useProfileStore((s) => s.setState);
  const { data: users, isLoading } = useProfileUsers();
  const { data: states } = useCredentialStates(system);
  const [stateFilter, setStateFilter] = useState("");
  const validateBatch = useValidateBatch();
  const [editTarget, setEditTarget] = useState<Credential | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Credential | null>(null);

  // Reconcile stale selections
  const reconciledRef = useRef(false);
  useEffect(() => {
    reconciledRef.current = false;
  }, [system, profile]);
  useEffect(() => {
    if (!users || users.length === 0 || reconciledRef.current) return;
    reconciledRef.current = true;
    const hasUnitsLocal = users.some((u) => u.unitCnes);
    const validKeys = new Set(
      users.map((u) => (hasUnitsLocal ? (u.unitCnes ?? u.username) : u.username)),
    );
    const stale = selectedUsers.filter((key) => !validKeys.has(key));
    if (stale.length > 0) {
      setSelectedUsers(selectedUsers.filter((key) => validKeys.has(key)));
    }
  }, [users, selectedUsers, setSelectedUsers]);

  const hasUnits = useMemo(() => users?.some((u) => u.unitCnes) ?? false, [users]);

  const getKey = useMemo(() => {
    return hasUnits ? (u: Credential) => u.unitCnes ?? u.username : (u: Credential) => u.username;
  }, [hasUnits]);

  const stateOptions = useMemo(() => {
    if (states && states.length > 0) {
      return states.map((s) => ({ value: s.state, label: `${s.state} — ${s.stateName.toUpperCase()}` }));
    }
    if (!users) return [];
    const map = new Map<string, string>();
    for (const u of users) {
      if (u.state && !map.has(u.state)) map.set(u.state, u.stateName || u.state);
    }
    return Array.from(map, ([value, label]) => ({ value, label }));
  }, [states, users]);

  const filteredItems = useMemo(() => {
    if (!users) return [];
    if (!stateFilter || stateFilter === "all") return users;
    return users.filter((u) => u.state === stateFilter);
  }, [users, stateFilter]);

  const toggleItem = (key: string) => {
    if (selectedUsers.includes(key)) {
      setSelectedUsers(selectedUsers.filter((k) => k !== key));
    } else {
      setSelectedUsers([...selectedUsers, key]);
    }
  };

  const selectAll = () => setSelectedUsers(filteredItems.map(getKey));
  const deselectAll = () => setSelectedUsers([]);

  const handleSave = () => {
    const selected = users?.filter((u) => selectedUsers.includes(getKey(u))) ?? [];
    if (selected.length > 0 && selected[0]) {
      setState(selected[0].state ?? "", selected[0].stateName ?? "");
    }
    toast.success(t("settings.operators_saved", { count: selectedUsers.length }));
  };

  const handleValidateBatch = () => {
    validateBatch.mutate(
      { system, profileType: profile },
      { onSuccess: () => toast.success(t("settings.validate_batch_success")) },
    );
  };

  if (isLoading) return <p className="text-sm text-[var(--text-secondary)]">{t("settings.operators_loading")}</p>;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {stateOptions.length > 0 && (
          <div className="space-y-1">
            <label className="text-xs text-[var(--text-secondary)]">{t("settings.state_filter")}</label>
            <Select value={stateFilter || undefined} onValueChange={(v) => setStateFilter(v ?? "")}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder={t("common.all")}>
                  {stateFilter ? stateOptions.find((o) => o.value === stateFilter)?.label : undefined}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {stateOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Bulk actions */}
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={selectAll}>
          {t("settings.operators_select_all")}
        </Button>
        <Button variant="outline" size="sm" onClick={deselectAll}>
          {t("settings.operators_deselect_all")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleValidateBatch}
          disabled={validateBatch.isPending || !users?.length}
        >
          {validateBatch.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t("settings.validate_credentials")}
        </Button>
        <Button size="sm" onClick={handleSave} disabled={selectedUsers.length === 0}>
          {t("settings.operators_save")}
        </Button>
      </div>

      {/* Table */}
      <div className="max-h-[500px] overflow-auto glass-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10" />
              <TableHead>{t("credentials.col_username")}</TableHead>
              {hasUnits && <TableHead>{t("credentials.col_unit")}</TableHead>}
              {hasUnits && <TableHead>{t("common.cnes")}</TableHead>}
              <TableHead>{t("settings.col_state")}</TableHead>
              <TableHead>{t("settings.validate_col_status")}</TableHead>
              <TableHead>{t("settings.col_last_validated")}</TableHead>
              <TableHead className="w-20">{t("credentials.col_actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={hasUnits ? 8 : 6} className="text-center text-[var(--text-tertiary)] py-8">
                  {t("credentials.no_credentials")}
                </TableCell>
              </TableRow>
            )}
            {filteredItems.map((cred) => {
              const key = getKey(cred);
              const checked = selectedUsers.includes(key);
              return (
                <TableRow key={cred.id} className="cursor-pointer" onClick={() => toggleItem(key)}>
                  <TableCell>
                    <Checkbox checked={checked} onCheckedChange={() => toggleItem(key)} />
                  </TableCell>
                  <TableCell className="font-mono text-sm">{cred.username}</TableCell>
                  {hasUnits && <TableCell>{cred.unitName ?? "\u2014"}</TableCell>}
                  {hasUnits && <TableCell>{cred.unitCnes ?? "\u2014"}</TableCell>}
                  <TableCell>{cred.stateName ? `${cred.state} — ${cred.stateName.toUpperCase()}` : cred.state}</TableCell>
                  <TableCell><ValidationStatusBadge isValid={cred.isValid} /></TableCell>
                  <TableCell><span className="text-sm text-[var(--text-secondary)]">{formatDate(cred.lastValidatedAt)}</span></TableCell>
                  <TableCell>
                    <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon" onClick={() => setEditTarget(cred)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(cred)}>
                        <Trash2 className="h-4 w-4 text-[var(--status-danger)]" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-[var(--text-secondary)]">
        {selectedUsers.length} / {filteredItems.length} {t("credentials.selected_label")}
      </p>

      {editTarget && (
        <CredentialEditDialog open onClose={() => setEditTarget(null)} credential={editTarget} />
      )}
      {deleteTarget && (
        <DeleteCredentialDialog open onClose={() => setDeleteTarget(null)} credential={deleteTarget} />
      )}
    </div>
  );
}
