"use client";

import { useEffect, useRef } from "react";

import { useUpsertSelection, useUserSelections } from "@/hooks/use-user-selections";
import { useUsers } from "@/hooks/use-users";
import { useProfileStore } from "@/stores/profile-store";

const DEBOUNCE_MS = 500;

export function useSelectionSync() {
  const userId = useProfileStore((s) => s.userId);
  const setUserId = useProfileStore((s) => s.setUserId);
  const hydrateFromServer = useProfileStore((s) => s.hydrateFromServer);
  const selections = useProfileStore((s) => s.selections);

  const { data: users } = useUsers();
  const { data: serverSelections } = useUserSelections(userId);
  const upsertMutation = useUpsertSelection(userId);

  const hydratedRef = useRef(false);
  const prevSelectionsRef = useRef<string>("");

  // Step 1: If no userId, pick the first active operator
  useEffect(() => {
    if (!userId && users && users.length > 0) {
      setUserId(users[0]!.id);
    }
  }, [userId, users, setUserId]);

  // Step 2: Hydrate store from server on initial load
  useEffect(() => {
    if (serverSelections && !hydratedRef.current) {
      hydrateFromServer(serverSelections);
      hydratedRef.current = true;
      prevSelectionsRef.current = JSON.stringify(
        useProfileStore.getState().selections,
      );
    }
  }, [serverSelections, hydrateFromServer]);

  // Step 3: Debounced sync store → backend on changes
  useEffect(() => {
    if (!userId || !hydratedRef.current) return;

    const serialized = JSON.stringify(selections);
    if (serialized === prevSelectionsRef.current) return;

    const timer = setTimeout(() => {
      prevSelectionsRef.current = serialized;

      for (const [key, sel] of Object.entries(selections)) {
        const [system, profileType] = key.split("::");
        if (!system || !profileType) continue;

        upsertMutation.mutate({
          system,
          profile_type: profileType,
          state: sel.state,
          state_name: sel.stateName,
          selected_users: sel.selectedUsers,
        });
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [userId, selections, upsertMutation]);
}
