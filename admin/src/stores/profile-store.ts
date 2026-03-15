import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { UserSelection } from "@/types/user";

interface ProfileSelections {
  selectedUsers: string[];
  state: string;
  stateName: string;
}

interface ProfileState {
  // RegulaHub user ID
  userId: string | null;

  // Active context
  system: string;
  profile: string;

  // Per-(system, profile) selections map — key: "SYSTEM::profile"
  selections: Record<string, ProfileSelections>;

  // Derived from selections map (consumers read these — kept in sync)
  selectedUsers: string[];
  state: string;
  stateName: string;

  // Actions
  setUserId: (id: string) => void;
  setSystem: (s: string) => void;
  setProfile: (p: string) => void;
  setState: (state: string, stateName: string) => void;
  setSelectedUsers: (users: string[]) => void;
  hydrateFromServer: (selections: UserSelection[]) => void;
}

function selectionKey(system: string, profile: string): string {
  return `${system}::${profile}`;
}

function deriveFromSelections(
  selections: Record<string, ProfileSelections>,
  system: string,
  profile: string,
): Pick<ProfileState, "selectedUsers" | "state" | "stateName"> {
  const key = selectionKey(system, profile);
  const sel = selections[key];
  return {
    selectedUsers: sel?.selectedUsers ?? [],
    state: sel?.state ?? "",
    stateName: sel?.stateName ?? "",
  };
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set, get) => ({
      userId: null,
      system: "SISREG",
      profile: "videofonista",
      selections: {},
      selectedUsers: [],
      state: "",
      stateName: "",

      setUserId: (userId) => set({ userId }),

      setSystem: (system) => {
        const { selections, profile } = get();
        set({
          system,
          ...deriveFromSelections(selections, system, profile),
        });
      },

      setProfile: (profile) => {
        const { selections, system } = get();
        set({
          profile,
          ...deriveFromSelections(selections, system, profile),
        });
      },

      setState: (state, stateName) => {
        const { system, profile, selections, selectedUsers } = get();
        const key = selectionKey(system, profile);
        const updated = {
          ...selections,
          [key]: {
            selectedUsers: selections[key]?.selectedUsers ?? selectedUsers,
            state,
            stateName,
          },
        };
        set({ state, stateName, selections: updated });
      },

      setSelectedUsers: (users) => {
        const { system, profile, selections, state, stateName } = get();
        const key = selectionKey(system, profile);
        const updated = {
          ...selections,
          [key]: {
            selectedUsers: users,
            state: selections[key]?.state ?? state,
            stateName: selections[key]?.stateName ?? stateName,
          },
        };
        set({ selectedUsers: users, selections: updated });
      },

      hydrateFromServer: (serverSelections) => {
        const { system, profile } = get();
        const newSelections: Record<string, ProfileSelections> = {};
        for (const sel of serverSelections) {
          const key = selectionKey(sel.system, sel.profileType);
          newSelections[key] = {
            selectedUsers: sel.selectedUsers,
            state: sel.state,
            stateName: sel.stateName,
          };
        }
        set({
          selections: newSelections,
          ...deriveFromSelections(newSelections, system, profile),
        });
      },
    }),
    {
      name: "regulahub-profile",
      version: 2,
      migrate: (persisted, version) => {
        const state = persisted as Record<string, unknown>;

        // v0/v1 cleanup
        delete state.userList;
        delete state.setUserList;

        if (version < 2) {
          // Migrate flat selectedUsers/state/stateName into selections map
          const system = (state.system as string) || "SISREG";
          const profile = (state.profile as string) || "videofonista";
          const selectedUsers = (state.selectedUsers as string[]) || [];
          const stateVal = (state.state as string) || "";
          const stateNameVal = (state.stateName as string) || "";
          const key = selectionKey(system, profile);

          state.selections = selectedUsers.length > 0
            ? { [key]: { selectedUsers, state: stateVal, stateName: stateNameVal } }
            : {};
          state.userId = null;
        }

        return state as unknown as ProfileState;
      },
    },
  ),
);
