import { describe, expect, it } from "vitest";

import { PlaceholderPage } from "@/components/shared/placeholder-page";

import { render, screen } from "../test-utils";

describe("PlaceholderPage", () => {
  it("renders system name", () => {
    render(<PlaceholderPage systemName="SIGA Saúde" icon="Hospital" />);
    expect(screen.getByText("SIGA Saúde")).toBeTruthy();
  });

  it("shows placeholder message from i18n", () => {
    render(<PlaceholderPage systemName="Care Paraná" icon="Heart" />);
    // en-US: "This integration is under development."
    expect(screen.getByText("This integration is under development.")).toBeTruthy();
  });

  it("renders icon (svg element present)", () => {
    const { container } = render(<PlaceholderPage systemName="Test" icon="Monitor" />);
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
