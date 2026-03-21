import { act } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import { useProfileStore } from "@/stores/profile-store";

describe("useProfileStore", () => {
  beforeEach(() => {
    const { setState } = useProfileStore;
    act(() => {
      setState({
        userId: null,
        system: "SISREG",
        state: "",
        stateName: "",
        profile: "videofonista",
        selectedUsers: [],
        selections: {},
      });
    });
  });

  it("has correct default state", () => {
    const state = useProfileStore.getState();
    expect(state.profile).toBe("videofonista");
    expect(state.system).toBe("SISREG");
    expect(state.selectedUsers).toEqual([]);
    expect(state.userId).toBeNull();
    expect(state.selections).toEqual({});
  });

  it("setProfile updates profile and syncs derived fields", () => {
    // Set up a selection for solicitante
    act(() => {
      useProfileStore.getState().setProfile("solicitante");
      useProfileStore.getState().setSelectedUsers(["user1"]);
    });
    // Switch back to videofonista — selectedUsers should restore from selections map
    act(() => {
      useProfileStore.getState().setProfile("videofonista");
    });
    expect(useProfileStore.getState().profile).toBe("videofonista");
    expect(useProfileStore.getState().selectedUsers).toEqual([]);
    // Switch to solicitante — selections should be restored
    act(() => {
      useProfileStore.getState().setProfile("solicitante");
    });
    expect(useProfileStore.getState().selectedUsers).toEqual(["user1"]);
  });

  it("setProfile does NOT clear selections when switching profiles", () => {
    act(() => {
      useProfileStore.getState().setSelectedUsers(["vf1", "vf2"]);
    });
    act(() => {
      useProfileStore.getState().setProfile("solicitante");
    });
    // Switch back
    act(() => {
      useProfileStore.getState().setProfile("videofonista");
    });
    expect(useProfileStore.getState().selectedUsers).toEqual(["vf1", "vf2"]);
  });

  it("setSystem updates system", () => {
    act(() => {
      useProfileStore.getState().setSystem("ESUS");
    });
    expect(useProfileStore.getState().system).toBe("ESUS");
  });

  it("setState updates state and stateName and stores in selections", () => {
    act(() => {
      useProfileStore.getState().setState("AM", "Amazonas");
    });
    expect(useProfileStore.getState().state).toBe("AM");
    expect(useProfileStore.getState().stateName).toBe("Amazonas");
    expect(useProfileStore.getState().selections["SISREG::videofonista"]?.state).toBe("AM");
  });

  it("setSelectedUsers updates selected users and stores in selections", () => {
    act(() => {
      useProfileStore.getState().setSelectedUsers(["user1", "user2"]);
    });
    expect(useProfileStore.getState().selectedUsers).toEqual(["user1", "user2"]);
    expect(useProfileStore.getState().selections["SISREG::videofonista"]?.selectedUsers).toEqual(["user1", "user2"]);
  });

  it("setUserId sets the user id", () => {
    act(() => {
      useProfileStore.getState().setUserId("test-id");
    });
    expect(useProfileStore.getState().userId).toBe("test-id");
  });

  it("hydrateFromServer populates selections map", () => {
    act(() => {
      useProfileStore.getState().hydrateFromServer([
        {
          id: "sel-1",
          userId: "user-1",
          system: "SISREG",
          profileType: "videofonista",
          state: "AM",
          stateName: "Amazonas",
          selectedUsers: ["vf1", "vf2"],
          createdAt: "",
          updatedAt: null,
        },
        {
          id: "sel-2",
          userId: "user-1",
          system: "SISREG",
          profileType: "solicitante",
          state: "AM",
          stateName: "Amazonas",
          selectedUsers: ["sol1"],
          createdAt: "",
          updatedAt: null,
        },
      ]);
    });
    const state = useProfileStore.getState();
    // Active profile is videofonista, so derived fields should match
    expect(state.selectedUsers).toEqual(["vf1", "vf2"]);
    expect(state.state).toBe("AM");
    // Solicitante selections should be stored
    expect(state.selections["SISREG::solicitante"]?.selectedUsers).toEqual(["sol1"]);
  });

  it("persists to localStorage under regulahub-profile key", () => {
    act(() => {
      useProfileStore.getState().setProfile("solicitante");
    });
    const stored = localStorage.getItem("regulahub-profile");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.state.profile).toBe("solicitante");
  });

  it("persist config includes version 2", () => {
    const stored = localStorage.getItem("regulahub-profile");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.version).toBe(2);
  });
});
