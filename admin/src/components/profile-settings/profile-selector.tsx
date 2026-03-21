"use client";

import { Check, User } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import { useAvailableProfiles } from "@/hooks/use-available-profiles";
import { cn } from "@/lib/utils";
import { useProfileStore } from "@/stores/profile-store";

export function ProfileSelector() {
  const t = useTranslations();
  const activeProfile = useProfileStore((s) => s.profile);
  const system = useProfileStore((s) => s.system);
  const setProfile = useProfileStore((s) => s.setProfile);
  const selections = useProfileStore((s) => s.selections);
  const { data: profiles, isLoading } = useAvailableProfiles();

  if (isLoading) return <p className="text-sm text-[var(--text-secondary)]">{t("settings.operators_loading")}</p>;

  const profileList = profiles && profiles.length > 0 ? profiles : [activeProfile];

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-[var(--text-primary)]">{t("settings.choose_profile")}</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {profileList.map((profileName) => {
          const isActive = activeProfile === profileName;
          const displayName = profileName.charAt(0).toUpperCase() + profileName.slice(1);
          const key = `${system}::${profileName}`;
          const count = selections[key]?.selectedUsers?.length ?? 0;
          return (
            <Card
              key={profileName}
              className={cn(
                "cursor-pointer transition-all",
                isActive && "ring-2 ring-[var(--accent-indigo)] shadow-md",
              )}
              onClick={() => setProfile(profileName)}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full transition-colors",
                    isActive
                      ? "bg-[var(--accent-indigo)] text-white"
                      : "bg-[rgba(120,120,128,0.08)] text-[var(--text-tertiary)]",
                  )}
                >
                  <User className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-[var(--text-primary)]">{displayName}</p>
                  {count > 0 && (
                    <p className="text-xs text-[var(--text-secondary)]">
                      {t("settings.profile_users_selected", { count })}
                    </p>
                  )}
                </div>
                {isActive && <Check className="h-5 w-5 text-[var(--accent-indigo)]" />}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
