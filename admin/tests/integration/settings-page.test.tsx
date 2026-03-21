import { describe, expect, it, vi } from "vitest";

import SettingsPage from "@/app/settings/page";

import { render, screen } from "../test-utils";

// Mock setAppLocale to prevent page reload
vi.mock("@/providers/i18n-provider", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/providers/i18n-provider")>();
  return {
    ...original,
    setAppLocale: vi.fn(),
  };
});

describe("SettingsPage", () => {
  it("renders main sections", () => {
    render(<SettingsPage />);

    expect(screen.getByText("Language")).toBeTruthy();
    expect(screen.getByText("API Connection")).toBeTruthy();
    expect(screen.getByText("About")).toBeTruthy();
  });

  it("renders page title", () => {
    render(<SettingsPage />);

    expect(screen.getByRole("heading", { name: "Settings" })).toBeTruthy();
  });

  it("shows language selector with 3 options", () => {
    render(<SettingsPage />);

    const select = screen.getAllByRole("combobox")[0]!;
    expect(select).toBeTruthy();
    expect(select.querySelectorAll("option")).toHaveLength(3);
  });

  it("shows API URL", () => {
    render(<SettingsPage />);

    expect(screen.getByText("http://localhost:8000")).toBeTruthy();
  });

  it("shows test connection button", () => {
    render(<SettingsPage />);

    expect(screen.getByRole("button", { name: "Test Connection" })).toBeTruthy();
  });

  it("shows version info", () => {
    render(<SettingsPage />);

    expect(screen.getByText("0.1.0")).toBeTruthy();
  });
});
