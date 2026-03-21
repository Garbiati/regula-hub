"use client";

import { useEffect, useMemo, useRef } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, Loader2, User, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useAvailableProfiles } from "@/hooks/use-available-profiles";
import { useProfileUsers } from "@/hooks/use-profile-users";
import { useProfileStore } from "@/stores/profile-store";

export function OperatorContextBar() {
  const t = useTranslations();
  const profile = useProfileStore((s) => s.profile);
  const selectedUsers = useProfileStore((s) => s.selectedUsers);
  const state = useProfileStore((s) => s.state);
  const stateName = useProfileStore((s) => s.stateName);
  const setProfile = useProfileStore((s) => s.setProfile);
  const setSelectedUsers = useProfileStore((s) => s.setSelectedUsers);
  const setState = useProfileStore((s) => s.setState);

  const system = useProfileStore((s) => s.system);
  const { data: profileNames } = useAvailableProfiles();
  const { data: operators, isLoading: operatorsLoading } = useProfileUsers();

  const hasUnits = useMemo(() => operators?.some((u) => u.unitCnes) ?? false, [operators]);

  // Reconcile stale selections when operators change (profile/system switch)
  const reconciledRef = useRef(false);
  useEffect(() => {
    reconciledRef.current = false;
  }, [system, profile]);
  useEffect(() => {
    if (!operators || operators.length === 0 || reconciledRef.current) return;
    reconciledRef.current = true;
    const validKeys = new Set(operators.map((u) => u.username));
    const stale = selectedUsers.filter((key) => !validKeys.has(key));
    if (stale.length > 0) {
      setSelectedUsers(selectedUsers.filter((key) => validKeys.has(key)));
    }
  }, [operators, selectedUsers, setSelectedUsers]);

  const primaryUser = selectedUsers[0] ?? "";
  const extraCount = selectedUsers.length > 1 ? selectedUsers.length - 1 : 0;

  const handleProfileChange = (value: string | null) => {
    if (value) setProfile(value.toLowerCase());
  };

  const toggleOperator = (key: string) => {
    const next = selectedUsers.includes(key)
      ? selectedUsers.filter((k) => k !== key)
      : [...selectedUsers, key];
    setSelectedUsers(next);

    // Update state from the first selected operator
    if (next.length > 0 && operators) {
      const first = operators.find((u) => u.username === next[0]);
      if (first) setState(first.state ?? "", first.stateName ?? "");
    }
  };

  const selectAll = () => {
    if (!operators) return;
    const all = operators.map((u) => u.username);
    setSelectedUsers(all);
    if (operators[0]) setState(operators[0].state ?? "", operators[0].stateName ?? "");
  };

  const deselectAll = () => setSelectedUsers([]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* ── Operator selector (popover) ── */}
      <Popover>
        <PopoverTrigger className="flex items-center gap-2 text-sm text-[var(--text-secondary)] rounded-lg px-2 py-1 -mx-2 transition-colors hover:bg-[var(--glass-surface)] cursor-pointer">
          {selectedUsers.length > 1 ? <Users className="h-4 w-4" /> : <User className="h-4 w-4" />}
          <span className="font-medium">{t("consulta.operator")}:</span>
          <span className="font-mono text-xs">{primaryUser || "\u2014"}</span>
          {extraCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-[var(--accent-indigo)] px-1.5 py-px text-[10px] font-semibold text-white tabular-nums">
              +{extraCount}
            </span>
          )}
          <ChevronDown className="h-3 w-3 opacity-50" />
        </PopoverTrigger>
        <PopoverContent side="bottom" align="start" className="w-80">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)]">
                {t("consulta.select_operators")}
              </span>
              <span className="text-[10px] text-[var(--text-tertiary)] tabular-nums">
                {selectedUsers.length}/{operators?.length ?? 0}
              </span>
            </div>
            <Separator />
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-6 text-[10px] px-2" onClick={selectAll}>
                {t("settings.operators_select_all")}
              </Button>
              <Button variant="outline" size="sm" className="h-6 text-[10px] px-2" onClick={deselectAll}>
                {t("settings.operators_deselect_all")}
              </Button>
            </div>
            <div className="max-h-52 overflow-y-auto -mx-1 px-1 space-y-0.5">
              {operatorsLoading && (
                <div className="flex items-center gap-2 py-4 justify-center text-[var(--text-tertiary)]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-xs">{t("settings.operators_loading")}</span>
                </div>
              )}
              {operators?.map((op) => {
                const key = op.username;
                const checked = selectedUsers.includes(key);
                return (
                  <label
                    key={op.id}
                    className="flex items-center gap-2.5 rounded-md px-2 py-1.5 cursor-pointer transition-colors hover:bg-[var(--glass-surface)]"
                  >
                    <Checkbox checked={checked} onCheckedChange={() => toggleOperator(key)} />
                    <div className="flex flex-col min-w-0">
                      <span className="font-mono text-xs truncate">{op.username}</span>
                      {hasUnits && op.unitName && (
                        <span className="text-[10px] text-[var(--text-tertiary)] truncate">
                          {op.unitName} {op.unitCnes ? `(${op.unitCnes})` : ""}
                        </span>
                      )}
                    </div>
                    {op.state && (
                      <span className="ml-auto text-[10px] text-[var(--text-tertiary)] shrink-0">{op.state}</span>
                    )}
                  </label>
                );
              })}
              {!operatorsLoading && operators?.length === 0 && (
                <p className="text-xs text-center text-[var(--text-tertiary)] py-4">
                  {t("credentials.no_credentials")}
                </p>
              )}
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* ── Profile switcher ── */}
      <Select value={profile.toUpperCase()} onValueChange={handleProfileChange}>
        <SelectTrigger className="h-7 w-auto min-w-0 gap-1 rounded-full border-[var(--accent-indigo)]/30 bg-[var(--accent-indigo)]/10 px-3 text-xs font-semibold text-[var(--accent-indigo)]">
          <SelectValue>{profile.charAt(0).toUpperCase() + profile.slice(1)}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {profileNames?.map((name) => (
            <SelectItem key={name} value={name}>
              {name.charAt(0) + name.slice(1).toLowerCase()}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* ── State badge ── */}
      {state && (
        <Badge variant="outline">
          {state}{stateName ? ` \u2014 ${stateName}` : ""}
        </Badge>
      )}
    </div>
  );
}
