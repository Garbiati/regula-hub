import { describe, expect, it, vi } from "vitest";

import { ProfileSelector } from "@/components/profile-settings/profile-selector";
import { useProfileStore } from "@/stores/profile-store";

import { act, fireEvent, render, screen } from "../test-utils";

// Mock useAvailableProfiles to return known profiles
vi.mock("@/hooks/use-available-profiles", () => ({
  useAvailableProfiles: () => ({
    data: ["videofonista", "solicitante"],
    isLoading: false,
  }),
}));

describe("ProfileSelector", () => {
  beforeEach(() => {
    act(() => {
      useProfileStore.setState({ profile: "videofonista" });
    });
  });

  it("renders both profile cards", () => {
    render(<ProfileSelector />);
    expect(screen.getByText("Videofonista")).toBeTruthy();
    expect(screen.getByText("Solicitante")).toBeTruthy();
  });

  it("videofonista is active by default", () => {
    render(<ProfileSelector />);
    expect(useProfileStore.getState().profile).toBe("videofonista");
  });

  it("clicking solicitante card updates store", () => {
    render(<ProfileSelector />);
    fireEvent.click(screen.getByText("Solicitante"));
    expect(useProfileStore.getState().profile).toBe("solicitante");
  });

  it("active card shows check mark", () => {
    render(<ProfileSelector />);

    const cards = document.querySelectorAll("[class*='cursor-pointer']");
    expect(cards.length).toBe(2);

    fireEvent.click(screen.getByText("Solicitante"));
    expect(useProfileStore.getState().profile).toBe("solicitante");
  });
});
